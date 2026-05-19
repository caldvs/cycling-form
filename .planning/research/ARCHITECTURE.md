# Architecture Research

**Domain:** GCP-hosted batch ML pipeline — video pose estimation fused with sport telemetry (single-user analytical tool)
**Researched:** 2026-05-20
**Confidence:** HIGH (component choices and patterns are well-documented GCP idioms; fusion specifics drawn from cycling-domain references)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  CLIENT / DEVELOPER                                                  │
│  ┌──────────────────────────┐    ┌──────────────────────────────┐    │
│  │ gcloud / make upload     │    │  Viewer (Streamlit / Next.js │    │
│  │ pushes .mp4 + .fit       │    │  / Observable notebook)      │    │
│  └────────────┬─────────────┘    └──────────────┬───────────────┘    │
└───────────────┼──────────────────────────────────┼───────────────────┘
                │                                  │ reads
                ▼                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│  STORAGE LAYER (Cloud Storage + BigQuery)                            │
│  ┌─────────────────────────┐  ┌────────────────────────────────────┐ │
│  │ GCS bucket: raw/        │  │ BigQuery dataset: vision           │ │
│  │  ride_id/video.mp4      │  │  - telemetry_raw (per-second)      │ │
│  │  ride_id/activity.fit   │  │  - pose_keypoints (per-frame)      │ │
│  │ GCS bucket: derived/    │  │  - stroke_features (per-stroke)    │ │
│  │  ride_id/pose.parquet   │  │  - fused_timeline (joined view)    │ │
│  └─────────────────────────┘  │  - correlations (per-ride summary) │ │
│                               └────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
                ▲                  ▲                  ▲
                │ writes pose      │ writes telemetry │ writes features
                │                  │                  │
┌──────────────────────────────────────────────────────────────────────┐
│  COMPUTE LAYER (Cloud Run Jobs, orchestrated)                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │ pose-job     │ │ fit-job      │ │ feature-job  │ │ correlate-job│ │
│  │ (MediaPipe   │ │ (fitparse,   │ │ (per-stroke  │ │ (rolling     │ │
│  │  on video)   │ │  resample 1Hz│ │  angles, KOPS│ │  Pearson/    │ │
│  │              │ │  enrich env) │ │  drift, sym) │ │  DTW)        │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ │
│         └────────────────┴───────┬────────┴────────────────┘         │
│                                  │ orchestrated by                   │
│                       ┌──────────▼──────────┐                        │
│                       │  Cloud Workflows    │                        │
│                       │  (or Makefile for   │                        │
│                       │  local dev parity)  │                        │
│                       └──────────▲──────────┘                        │
└──────────────────────────────────┼───────────────────────────────────┘
                                   │ triggered by Eventarc
                                   │ on GCS object finalize
                  ┌────────────────┴────────────────┐
                  │ Eventarc: bucket=raw/ → workflow │
                  └─────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Ingestion** | Land raw `.mp4` and `.fit` together under a `ride_id/` prefix; emit a "ride ready" signal | `gsutil cp` from a local CLI script; manifest file written last (`manifest.json` with both blob hashes) to trigger the workflow only when both inputs are present |
| **Orchestrator** | Sequence the four jobs, retry transient failures, surface status | Cloud Workflows YAML triggered by Eventarc on `manifest.json` finalize; locally mirrored by a Makefile target so dev iteration doesn't require GCP |
| **Pose service (pose-job)** | Read video from GCS, run MediaPipe Pose per frame, write keypoints + frame timestamps to `derived/ride_id/pose.parquet` and load into BigQuery | Cloud Run **Job** (not Service) — task-driven, no 60-minute HTTP timeout, CPU-only; container has Python + mediapipe + opencv |
| **Telemetry parser (fit-job)** | Parse FIT to a normalized 1Hz schema; enrich with environmental data (temp/humidity/wind via Open-Meteo for outdoor metadata if available); load to `telemetry_raw` | Cloud Run Job, Python with `fitparse` |
| **Feature computation (feature-job)** | Detect pedal strokes from pose, compute per-stroke metrics (knee angle range, KOPS drift, hip rock, L/R asymmetry); load to `stroke_features` | Cloud Run Job, Python with numpy/scipy — runs after pose-job |
| **Time alignment** | Reconcile video-clock and FIT-clock onto a shared timeline | **Downstream SQL view** (`fused_timeline`) joins `pose_keypoints` and `telemetry_raw` on a per-ride offset stored in `rides` metadata table. See ADR-2. |
| **Correlation analyzer (correlate-job)** | Compute rolling Pearson / lagged correlation between stroke-feature streams and telemetry streams; write top-N correlations | Cloud Run Job; can be replaced by a BigQuery scheduled query for v2 |
| **Viewer** | Render fused timeline (video frame + pose overlay + telemetry traces) and the correlations table | Streamlit on Cloud Run Service (request-driven, scales to zero) OR a static Observable / Quarto notebook regenerated per ride. MVP: notebook. |

## Recommended Project Structure

```
vision/
├── pipeline/
│   ├── pose/                # pose-job container source
│   │   ├── Dockerfile
│   │   ├── main.py          # entry: reads GCS_URI, writes pose.parquet, loads BQ
│   │   └── stroke_detect.py # pure functions, unit-tested locally
│   ├── fit/                 # fit-job container source
│   │   ├── Dockerfile
│   │   ├── main.py
│   │   └── enrich.py        # environmental data fetcher (Open-Meteo)
│   ├── features/            # feature-job container source
│   │   ├── Dockerfile
│   │   └── main.py
│   └── correlate/           # correlate-job container source
│       ├── Dockerfile
│       └── main.py
├── infra/
│   ├── workflows/
│   │   └── ride.yaml        # Cloud Workflows definition
│   ├── eventarc/
│   │   └── trigger.yaml
│   ├── bigquery/
│   │   ├── schemas/         # JSON schemas per table
│   │   └── views/           # fused_timeline.sql, correlations_view.sql
│   └── terraform/           # optional: GCS buckets, BQ dataset, IAM
├── viewer/
│   └── notebook.qmd         # or app.py for Streamlit
├── lib/
│   └── vision/              # shared Python package: schemas, GCS helpers, BQ loaders
├── tests/                   # pytest — pose stroke-detect, FIT parser, alignment math
├── data/
│   └── samples/             # one tiny sample ride for local dev (gitignored if large)
├── Makefile                 # local-parity targets: make pose RIDE=2026-05-20-test
└── .planning/
```

### Structure Rationale

- **`pipeline/*/` mirrors the four Cloud Run Jobs one-to-one.** Each subdirectory is independently deployable, with its own Dockerfile. This makes the JD-claim "I deployed four containerized ML pipeline stages on GCP" trivially true.
- **`lib/vision/` is shared code** (BigQuery schemas, GCS path helpers, ride-ID conventions). It is imported by every container, ensuring schema drift can't happen between writers.
- **`infra/` is reviewable separately** from application code. A hiring manager can read `infra/workflows/ride.yaml` and understand the entire pipeline shape in 30 lines.
- **`Makefile` provides local-parity targets.** `make pose RIDE=...` runs the same `main.py` against local files. This is critical for the cost story (see ADR-1).
- **`viewer/` is intentionally separate from `pipeline/`.** It is a read-only consumer of BigQuery. It has zero coupling to the compute layer.

## Architectural Patterns

### Pattern 1: Manifest-triggered batch pipeline

**What:** The producer (upload CLI) writes both `video.mp4` and `activity.fit` to GCS, then writes a third file `manifest.json` containing checksums and the desired processing config. Eventarc subscribes only to `manifest.json` finalize events. The workflow reads the manifest to know which inputs belong to this ride.

**When to use:** Any time a pipeline needs two-or-more correlated inputs that arrive separately. Subscribing to the video upload alone would race against the FIT upload; the manifest is an explicit "all inputs ready" signal.

**Trade-offs:**
- (+) Eliminates upload-race conditions
- (+) Manifest doubles as a config envelope (model version, expected duration, ride metadata)
- (-) Two-step upload (CLI must write manifest last); easy if encapsulated in `make upload`

### Pattern 2: GCS as the durable inter-stage bus, BigQuery as the analytical sink

**What:** Each Cloud Run Job reads its inputs from GCS, writes intermediate artifacts (Parquet) to GCS *and* loads final tables into BigQuery. Downstream jobs read from BigQuery, not from the GCS Parquet directly.

**When to use:** Batch pipelines where you want both reprocessability (GCS Parquet is the ground truth — you can rebuild BQ tables anytime) and queryability (BQ is fast for the viewer and correlation analysis).

**Trade-offs:**
- (+) BQ load failures don't lose the work; the Parquet on GCS is the source of truth
- (+) Schema migrations are easy: rebuild the table from Parquet with a new schema
- (-) Slight duplication of storage cost; trivial at portfolio-project volume

### Pattern 3: Cloud Run **Jobs** for batch compute (not Cloud Run Services)

**What:** Each pipeline stage is a Cloud Run **Job**, not a Service. Jobs are task-driven, lack the HTTP request/response wrapper, and have task timeouts up to 168 hours vs the 60-minute request timeout on services.

**When to use:** Any work that completes on a schedule or event and doesn't serve interactive traffic. Pose inference over a 60-minute video at 5 fps could exceed a Service's hard timeout on cold-start retries.

**Trade-offs:**
- (+) No HTTP boilerplate inside the container
- (+) Long timeouts and parallelism (10k tasks max)
- (-) Slightly less common in tutorials; most "Cloud Run" blog content is about Services. Worth flagging in the README for resume legibility.

### Pattern 4: Time alignment as a SQL view, not a service

**What:** The pose-job records frame timestamps relative to the video's t=0. The fit-job records sample timestamps relative to the FIT file's recorded start time. A separate `rides` table holds a per-ride `video_to_fit_offset_seconds` value. The `fused_timeline` view does `ON pose.frame_t + r.offset = telemetry.t`.

**When to use:** When alignment is a metadata problem (offset) more than a signal-processing problem (resync). For indoor trainer rides with a clapperboard sync (one hard pedal at video start that's visible in both pose and power), the offset is recoverable; once stored, alignment is a free join.

**Trade-offs:**
- (+) Alignment failures are easy to debug — change one row in `rides`, the view updates instantly
- (+) Reprocessing pose or FIT doesn't require re-running an alignment service
- (-) For complex resync (clock drift, dropped frames), this isn't enough — would need a proper signal-alignment job. See ADR-2.

## Data Flow

### Per-Ride Request Flow

```
1. User: make upload RIDE=2026-05-20-z2
       ↓ gsutil cp video.mp4 + activity.fit → gs://vision-raw/2026-05-20-z2/
       ↓ gsutil cp manifest.json (last)     → gs://vision-raw/2026-05-20-z2/
                                                                ↓
2. Eventarc: object finalize on manifest.json triggers Cloud Workflows
                                                                ↓
3. Workflows: parallel branches
       ├─ pose-job   → GCS reads video.mp4 → mediapipe → pose.parquet → BQ.pose_keypoints
       └─ fit-job    → GCS reads activity.fit → fitparse → telemetry.parquet → BQ.telemetry_raw
                                                                ↓
4. Workflows: serial after pose-job
       └─ feature-job → BQ.pose_keypoints → stroke detection → BQ.stroke_features
                                                                ↓
5. Workflows: serial after feature-job + fit-job
       └─ correlate-job → BQ.stroke_features + BQ.telemetry_raw → BQ.correlations
                                                                ↓
6. Workflows: insert row into BQ.rides with status="ready"
                                                                ↓
7. Viewer: queries BQ.fused_timeline + BQ.correlations for the ride_id
```

### Key Data Flows

1. **Raw → derived:** Raw blobs in `gs://vision-raw/` never change after upload. All derived artifacts go to `gs://vision-derived/` and BQ tables. This separation lets you nuke and rebuild derived data without re-uploading.
2. **Per-frame pose → per-stroke features:** `pose_keypoints` is wide (33 landmarks × N frames). `stroke_features` is narrow (one row per detected pedal stroke, ~80 strokes/min × ride length). The feature job is the only thing that reads pose at frame granularity; everything downstream reads strokes.
3. **Stroke features × telemetry → correlations:** The correlate-job joins on `(ride_id, t)` after alignment, computes rolling-window correlations, picks top-N, writes a small `correlations` table that the viewer renders directly.

## Build Order (de-risking)

This is the recommended order. Each step is shippable and useful on its own.

| # | Step | De-risks | Time est |
|---|------|----------|----------|
| **1** | **Local thin slice end-to-end** (no GCP at all): one ride's video + FIT processed by four local Python scripts, output a Quarto notebook with the fused chart + a couple of correlations. | Pose-on-cycling-video actually works at acceptable quality. FIT parsing works for your specific device. Time alignment is feasible with a clapperboard. Pedal-stroke detection from pose is achievable. — These are the *real* risks; cloud is the easy part. | 2 weekends |
| **2** | Containerize each script (4 Dockerfiles). Run all four containers locally with `make`. Same notebook output. | The code runs in a container, same as it will on Cloud Run. No GCP-specific bugs at this stage. | 1 weekend |
| **3** | GCS buckets + BigQuery dataset + schemas. Modify each container to read from GCS / write to BQ instead of local files. Still trigger manually with `gcloud run jobs execute`. | GCP IAM, BigQuery schemas, GCS path conventions. The pipeline is now "on GCP" — the JD claim is true. | 1 weekend |
| **4** | Cloud Workflows YAML + Eventarc trigger on `manifest.json`. Upload triggers full pipeline. | Orchestration, event-driven trigger. | 1 weekend |
| **5** | Viewer (Streamlit on Cloud Run Service or static notebook regen). README + write-up. | Resume legibility — the demo someone can click on. | 1 weekend |
| **6** | Polish: second ride, second analysis (e.g., fatigue-vs-symmetry), test suite, cost dashboard screenshot. | Generalizability — "it works for one ride" → "it works for any ride." | 1-2 weekends |

**Total: 6-8 weekends, matches the constraint.** Steps 1-3 are the minimum to claim all four JD areas; 4-5 turn it into a defensible portfolio piece.

## Thin-Slice MVP Definition

**The smallest end-to-end version that touches all four JD areas:**

> Given one specific ride (one video + one FIT), the pipeline:
> 1. Runs **MediaPipe Pose** on the video and produces a per-frame keypoints Parquet **[JD: pose/CV]**
> 2. Parses the FIT file into a normalized timeseries Parquet **[JD: sport telemetry]**
> 3. Runs both stages as **Cloud Run Jobs** writing to **Cloud Storage** and loading into **BigQuery** **[JD: GCP ML workloads]**
> 4. Produces a single chart — knee-angle range overlaid on power, with one computed correlation value — viewable as a Quarto notebook served from a GCS bucket **[JD: software engineering — the whole thing is shipped, documented, reproducible]**

This MVP deliberately skips: Workflows orchestration (use `gcloud run jobs execute` manually), Eventarc triggers (manual upload), feature-job and correlate-job as separate stages (fold into a single "analysis" job), Streamlit viewer (Quarto render is enough), environmental enrichment, asymmetry/hip-rock metrics, multi-ride support.

**Acceptance criterion:** A hiring manager visits the repo README, sees a screenshot of the fused chart, clicks a "view on GCS" link, sees the notebook with their browser. They can read four Dockerfiles and one BigQuery schema and understand the system in under 10 minutes.

## Architecture Decision Records

### ADR-1: Cloud Run Jobs vs Vertex AI Endpoints for pose inference

**Decision:** Cloud Run Jobs.

**Context:** Pose inference can run on (a) Vertex AI Endpoint (persistent prediction service), (b) Cloud Run Service (request-driven), or (c) Cloud Run Job (task-driven, ephemeral). The pipeline runs maybe 1-2 times per week.

**Forces:**
- Vertex AI Endpoints bill per node-hour for as long as the endpoint exists, regardless of traffic. The cheapest n1-standard-4 endpoint is ~$160/month idle — that alone busts the <$20/month budget.
- Cloud Run Service scales to zero, but has a 60-minute hard request timeout; a 90-minute Z2 ride at 5 fps could exceed that on retries.
- Cloud Run Jobs scale to zero, have 7-day task timeouts, and don't need HTTP boilerplate. Cold start latency (~30s) is irrelevant for batch.
- MediaPipe Pose is CPU-friendly; no GPU needed for v1.

**Decision:** Cloud Run Job per pipeline stage. Vertex AI is the obvious wrong choice on cost; Cloud Run Service is the right shape for an interactive inference API the project doesn't need.

**Consequences:**
- (+) Idle cost ≈ $0
- (+) Single mental model across all four stages
- (-) Slightly less "ML platform" sounding on the resume than "Vertex AI" — mitigated by writing a paragraph in the README explaining the choice (which itself demonstrates GCP fluency).
- (-) If real-time inference is ever needed, swap pose-job for a Vertex AI Endpoint behind the same orchestration. Migration is local to one container.

### ADR-2: Time alignment in BigQuery view, not in a service

**Decision:** Per-ride scalar offset stored in `rides` table; alignment is a SQL join.

**Context:** Indoor-trainer rides have two independent clocks: the camera's frame timestamps and the FIT file's record timestamps. Without explicit sync, they can drift by 5-30 seconds at ride start. Approaches: (a) clock sync at recording time (NTP both devices — impractical), (b) signal-based alignment (cross-correlate cadence-from-pose with cadence-from-FIT), (c) clapperboard sync (do one hard pedal stroke at the start of the video, manually note the offset).

**Forces:**
- For a portfolio v1 with the project owner as the sole user, the clapperboard approach is fine — one manual offset value per ride, written into `rides` at upload time.
- The "real" approach (cross-correlation of pose-cadence vs FIT-cadence) is a great v2 — it's a nice signal-processing demo to add later and shows progression.
- Doing alignment as a SQL view means changes are instant and reversible; doing it inside a service means re-running compute.

**Decision:** Phase 1 stores a manual offset in the `rides` metadata table. The `fused_timeline` view applies the offset in SQL. Phase 2+ can replace manual offset with an auto-aligned offset computed by an alignment-job that writes to the same column.

**Consequences:**
- (+) Trivial to implement, instant to debug
- (+) Migration path to automated alignment is clean — same schema
- (-) Onboarding a second user later would require teaching them the clapperboard convention; acceptable for v1 since there is no second user.

### ADR-3: Pose inference always in cloud (not local-only) for the final shipped version

**Decision:** Pose-job runs both locally (dev iteration) and on Cloud Run (the shipped pipeline), same Docker image both places.

**Context:** MediaPipe Pose on CPU runs comfortably on a developer laptop. The temptation is to develop locally and never deploy. But the JD bullet is "GCP-based ML workloads"; pose running only on a laptop doesn't satisfy it.

**Decision:** Build the container, run it locally during dev (`docker run -v $PWD/data:/data`), deploy it as a Cloud Run Job for the shipped pipeline. Identical image, identical behavior. Local iteration is fast; the cloud version exists and is documented for the resume claim.

**Consequences:**
- (+) Best of both worlds — fast dev, real deploy
- (+) Pose inference dollars are negligible (a 90-minute ride processes in ~10-15 minutes of CPU on a 4-vCPU Cloud Run Job → cents per ride)
- (-) Marginal extra setup work (Artifact Registry, IAM for the job's service account) — once per project.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1 user, 1-2 rides/week (v1) | Current design as-is. Total cost ~$5/month including BQ idle + GCS storage. |
| 1 user, 1-2 rides/day | No structural change. Cloud Run Jobs scale linearly per ride. |
| 10-100 users | Add per-user partitioning to all BQ tables (`PARTITION BY ride_date, CLUSTER BY user_id`), add lightweight auth in front of the viewer (Identity Platform / IAP). Pipeline shape is unchanged. |
| 1000+ users | Reconsider pose inference — at this scale, a Vertex AI Endpoint with batching becomes cheaper than per-ride Cloud Run Jobs. Move correlation analysis into BigQuery scheduled queries with a UDF. Likely need GPU for pose-job at sub-10-minute latency expectations. |

### Scaling Priorities

1. **First bottleneck (v1 → moderate use):** BigQuery query cost on the viewer if `fused_timeline` view recomputes per click. Mitigate with a materialized view per ride after correlate-job finishes.
2. **Second bottleneck (moderate use → 100s of users):** Pose-job duration becomes the user-visible "how long until I see my analysis." At that point, parallelize within a single ride (Cloud Run Jobs supports task indices — split video into 5-minute chunks, process in parallel, concat keypoints).

## Anti-Patterns

### Anti-Pattern 1: Inference behind an HTTP service the rest of the pipeline calls

**What people do:** Wrap MediaPipe Pose in a FastAPI service deployed as Cloud Run Service. The orchestration job POSTs the GCS URI and waits for keypoints.

**Why it's wrong:** Adds HTTP serialization overhead, a 60-minute timeout cliff, and a synchronous wait inside the orchestrator. Provides no benefit because there's no second caller of the pose API.

**Do this instead:** Cloud Run **Job** with the GCS URI as an environment variable. Job reads, processes, writes Parquet + loads BQ, exits. Orchestrator just checks for the next stage's input.

### Anti-Pattern 2: Storing pose keypoints as JSON blobs in BigQuery

**What people do:** Treat the 33-landmark-per-frame structure as one JSON column per frame row.

**Why it's wrong:** JSON columns are unindexable, expensive to query, and force every downstream consumer to know the JSON schema. Stroke-detection queries become slow.

**Do this instead:** Flat table with `ride_id, frame_idx, frame_t_seconds, landmark_name, x, y, z, visibility`. Yes it's tall (33× the row count). BQ doesn't care. Queries like `WHERE landmark_name = 'right_knee'` are fast and obvious. Alternative: STRUCT-ARRAY with `landmarks ARRAY<STRUCT<name STRING, x FLOAT64, ...>>` if you really want one row per frame.

### Anti-Pattern 3: Doing time alignment inside the pose-job

**What people do:** Pose-job reads both the video and the FIT file, aligns them, writes a pre-fused timeline.

**Why it's wrong:** Couples two stages that have nothing to do with each other. Reprocessing the FIT now requires re-running pose inference. Changing the alignment offset requires re-running pose inference. Schema changes ripple.

**Do this instead:** Pose-job knows nothing about FIT. FIT-job knows nothing about video. They each write into their own table on their own clock. Alignment happens at query time via the `fused_timeline` view (ADR-2).

### Anti-Pattern 4: One giant Cloud Run Job that does everything

**What people do:** A single container that does pose + FIT + features + correlations because it's "easier."

**Why it's wrong:** Every change (try a new pose model, try a different stroke-detection algorithm, add a new correlation) requires rebuilding and redeploying the monolith. The resume story collapses to one bullet instead of four. Failures are coarse-grained.

**Do this instead:** Four jobs, four containers, four bullets. Each stage is independently improvable. Shared code lives in `lib/vision/` and is `pip install`-ed into each container.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| MediaPipe (pose model) | `pip install mediapipe`, model weights bundled in image | No external API; runs entirely in-container |
| Open-Meteo / weather (env enrichment) | HTTP GET in fit-job, cached per (lat, lon, date) | Free tier sufficient; only relevant if FIT contains GPS (indoor rides won't) — make this optional |
| FIT parsing | `pip install fitparse`, library reads bytes from GCS-downloaded file | Some Garmin/Wahoo FIT files have device-specific quirks; build a small fixture suite |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Upload CLI ↔ Pipeline | GCS object events via Eventarc → Workflows | Manifest pattern (Pattern 1) avoids upload races |
| Pipeline stages ↔ each other | BigQuery tables + GCS Parquet (never direct in-process calls) | Each stage is independently runnable given its input table(s) |
| Pipeline ↔ Viewer | BigQuery views, read-only | Viewer can be swapped (Quarto → Streamlit → Next.js) without touching pipeline |
| Code ↔ Schema | `lib/vision/schemas/` Python module is the single source of truth, BigQuery DDL generated from it | Prevents drift between writer and reader expectations |

## Sources

- [Cloud Run Jobs vs Cloud Batch: Choosing Your Engine](https://medium.com/google-cloud/cloud-run-jobs-vs-cloud-batch-choosing-your-engine-for-run-to-completion-workloads-8590a8e3a3b1) — confirms Cloud Run Jobs (not Services) for batch video processing, 7-day timeouts vs 60-min request timeout
- [How to reduce your ML model inference costs on GCP](https://medium.com/google-cloud/how-to-reduce-your-ml-model-inference-costs-on-google-cloud-e3d5e043980f) — establishes Vertex AI Endpoint ~$160/month idle cost vs Cloud Run scale-to-zero, drives ADR-1
- [How to Build an Event-Driven Architecture on GCP Using Eventarc + Workflows + Cloud Run](https://oneuptime.com/blog/post/2026-02-17-how-to-build-an-event-driven-architecture-on-gcp-using-eventarc-workflows-and-cloud-run/view) — canonical pattern for GCS-trigger → Workflows → Cloud Run, MEDIUM confidence (community source) but pattern is well-established
- [Execute a Cloud Run job using Workflows (GCP docs)](https://cloud.google.com/workflows/docs/tutorials/execute-cloud-run-jobs) — official source for Workflows-driven Cloud Run Job orchestration
- [Specify nested and repeated columns in BigQuery table schemas (GCP docs)](https://cloud.google.com/bigquery/docs/nested-repeated) — confirms STRUCT/ARRAY support for pose keypoint schema design
- [Batch loading data (BigQuery docs)](https://docs.cloud.google.com/bigquery/docs/batch-loading-data) — confirms Parquet from GCS as the standard load path
- [FusionPose: cyclist pose estimation accuracy](https://www.sciencedirect.com/science/article/pii/S1474034625009073) — confirms MediaPipe Pose is viable for cyclist joint-angle prediction (97.68% reported), MEDIUM confidence
- [PoseSync: Robust pose-based video synchronization (arXiv)](https://arxiv.org/pdf/2308.12600) — establishes DTW on pose features as the upgrade path for auto-alignment, referenced in ADR-2 as v2 work
- [MetricFlix: FIT file → video overlay](https://metricflix.app/) — confirms the broader pattern (FIT + video fusion) is a real product space; the project's analytical-correlation framing is a defensible differentiator
- [The Weekly ETL: How Do You "Thin Slice" A Data Pipeline?](https://www.montecarlodata.com/blog-the-weekly-etl-how-do-you-thin-slice-a-data-pipeline/) — drives the "slice the data, not the solution" framing in Build Order

---
*Architecture research for: GCP-hosted batch video+telemetry analytics pipeline (Vision project)*
*Researched: 2026-05-20*
