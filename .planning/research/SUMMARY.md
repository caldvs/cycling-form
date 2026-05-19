# Project Research Summary

**Project:** Vision — Cycling Form & Performance Analyzer
**Domain:** Single-user batch ML pipeline — CV pose estimation + sport telemetry fusion on GCP, built as portfolio evidence for an endurance-sport performance role
**Researched:** 2026-05-20
**Confidence:** HIGH

## Executive Summary

Vision is a portfolio-grade analytical tool that fuses indoor-trainer cycling video (MediaPipe pose) with FIT-file telemetry (power/cadence/HR) on GCP, surfacing per-stroke pose↔performance correlations. All four research dimensions converged on the same shape: **a four-stage batch pipeline (pose → fit → features → correlate) running as Cloud Run Jobs, with GCS as the durable artifact bus and BigQuery as the analytical sink, fronted by a Streamlit or notebook viewer.** This is the smallest stack that credibly demonstrates all four JD bullets (CS/engineering, CV/pose, GCP ML, sport telemetry) without inviting scope creep into MLOps, multi-user, or real-time territory that PROJECT.md explicitly rules out.

The recommended approach is a **time-boxed, vertically-sliced build**: ship a local thin slice end-to-end before any GCP code is written, then containerize, then move storage to GCS+BigQuery, then add Workflows/Eventarc orchestration only if budget allows. The single biggest analytical risk is **time alignment between the video clock and FIT clock** — both Architecture (ADR-2) and Pitfalls (#3) flag it as the linchpin that must be solved cleanly or every downstream correlation is noise. The single biggest operational risk is **GCP cost runaway** from forgotten `min-instances ≥ 1` or scheduler loops; Pitfall #4 mandates a Pub/Sub → Cloud Function billing kill switch deployed in Phase 0 before any inference service goes live.

Confidence is HIGH on stack, features, architecture, and the major pitfalls — every choice is grounded in current (May 2026) official documentation or peer-reviewed research. The only MEDIUM-confidence calls are (a) whether to add a Vertex AI Pipelines wrapper as a resume flourish (defer to Phase 6+ at earliest) and (b) the exact threshold above which leg-occlusion gating should drop bilateral metrics (must be calibrated on the first real ride). Everything else is well-trodden ground: this is **a deliberately boring stack executed with discipline**, not a research project.

## Key Findings

### Recommended Stack

A single Python 3.12 stack handles pose, telemetry, and GCP clients end-to-end. The compute substrate is **Cloud Run Jobs** (not Services, not Vertex AI Endpoints) — task-driven, scale-to-zero, no 60-minute HTTP timeout cliff, idle cost ≈ $0. Storage splits cleanly: **GCS** for raw artifacts and intermediate Parquet (the durable inter-stage bus), **BigQuery** for analytical tables (partitioned by `ride_date`, clustered by `ride_id`). Viewer is **Streamlit on Cloud Run Service** (or, for the absolute thin slice, a Quarto/Jupyter notebook regenerated per ride).

**Core technologies:**
- **Python 3.12** — single stack for pose + telemetry + GCP clients; max MediaPipe wheel compatibility (no 3.13 wheels yet)
- **MediaPipe Pose Landmarker (Tasks API)** `mediapipe==0.10.35` — Google-maintained, CPU-friendly, 33 landmarks; use Tasks API, NOT the legacy `mp.solutions.pose`
- **OpenCV** `opencv-python==4.10.*` — video decode and overlay rendering
- **Garmin FIT Python SDK** `garmin-fit-sdk==21.205.*` — officially maintained, replaces dormant `python-fitparse`
- **Polars 1.40** (+ pandas 2.2 interop) — Arrow-native time-bucket and asof-join primitives for fusing 30fps video with 1Hz FIT
- **google-cloud-storage 3.10**, **google-cloud-bigquery 3.x** — standard GCP idioms
- **Cloud Run Jobs** — batch compute, scale-to-zero (ADR-1: explicitly NOT Vertex AI Endpoint, which would bust the $20/month budget alone)
- **BigQuery** — partitioned `telemetry_raw`, `pose_keypoints`, `stroke_features`, `correlations`, plus a `fused_timeline` SQL view that applies the per-ride alignment offset
- **Streamlit 1.55** + **Plotly** — viewer; one Python process, embeds video, plots, and pose overlays
- **uv** + `pyproject.toml` + `uv.lock` — modern 2026 dep management
- **Open-Meteo** (`openmeteo-requests`) — free historical weather, no API key; skip-on-indoor (Pitfall #12)
- **One-Euro filter** for keypoint smoothing; **scipy.signal** for cadence peak detection

**What NOT to use:** `mp.solutions.pose` (legacy), `python-fitparse` (dormant), Vertex AI Endpoint (idle cost), GKE/Composer/Dataflow (over-engineered), Firestore/Cloud SQL for telemetry (wrong shape), Next.js viewer (yak-shaving), GPU for v1.

### Expected Features

The feature landscape is calibrated on three axes: analytical legitimacy, JD-bullet evidence, resume legibility. Per-stroke pose↔telemetry correlation is the analytical differentiator — no commercial tool (Retul, Leomo, MyVeloFit) does this well, and it's exactly what PROJECT.md declares as the core value.

**Must have (table stakes):**
- Ingest single local video + FIT file pair
- FIT → normalized timeseries with gear inference (cadence/speed)
- MediaPipe 2D pose extraction per frame (knee/hip/ankle/shoulder)
- Pedal stroke segmentation from video alone (peak-finding on ankle y)
- Video↔FIT time alignment via cadence cross-correlation
- Per-stroke metrics: knee angle range, KOPS drift, hip rock, L/R asymmetry
- Per-stroke telemetry aggregation
- Top-N Pearson/Spearman correlations with n, p, 95% CI
- BigQuery persistence (partitioned); raw artifacts in GCS
- Pose inference deployed as Cloud Run Job
- Streamlit or notebook viewer
- README with JD-bullet → code mapping table

**Should have (differentiators, choose 2–4):**
- One-Euro temporal smoothing
- Visibility-gating + confidence-weighted keypoints
- BDC/TDC detection
- Fatigue / rolling-window form-drift detection (PROJECT.md headline example)
- L/R balance from FIT cross-checked against pose asymmetry (two-source validation)
- One-ride markdown analysis writeup (highest narrative leverage)
- GitHub Actions CI/CD to Cloud Run
- Run manifest / reproducibility metadata
- Annotated frame strip in viewer

**Defer (anti-features per PROJECT.md):** coaching prescriptions, multi-user/auth, real-time, custom pose model, outdoor video, 3D pose, saddle-pressure/IMU, Strava/TrainingPeaks API, React/Vue dashboard, LLM "AI coach", sensitivity analysis.

### Architecture Approach

A **manifest-triggered batch pipeline**: upload writes `video.mp4` + `activity.fit` + `manifest.json` (last, with hashes) to `gs://vision-raw/{ride_id}/`. Eventarc subscribes only to `manifest.json` finalize. Cloud Workflows orchestrates four Cloud Run Jobs (pose+fit in parallel, then feature, then correlate). Each stage reads from GCS/BQ and writes to BQ; pose-job knows nothing about FIT and vice versa. **Time alignment is a SQL view** (ADR-2): per-ride scalar offset stored in `rides` metadata, `fused_timeline` view applies it on JOIN.

**Major components:**
1. **Ingestion** — `make upload` CLI; manifest-last pattern avoids upload races
2. **Orchestrator** — Cloud Workflows YAML + Eventarc; Makefile mirror for local dev parity
3. **pose-job** — Cloud Run Job; MediaPipe Tasks API → `pose.parquet` → `BQ.pose_keypoints` (flat schema, not JSON)
4. **fit-job** — Cloud Run Job; Garmin FIT SDK → `BQ.telemetry_raw`; Open-Meteo for outdoor only
5. **feature-job** — stroke detection + per-stroke metrics → `BQ.stroke_features`
6. **correlate-job** — rolling Pearson → `BQ.correlations`
7. **`fused_timeline` BQ view** — alignment as SQL
8. **Viewer** — Streamlit on Cloud Run Service (or notebook for thin slice)
9. **`lib/vision/`** — shared schemas/helpers; prevents writer/reader schema drift

Project layout mirrors the four jobs one-to-one (`pipeline/pose/`, `pipeline/fit/`, `pipeline/features/`, `pipeline/correlate/`), each with its own Dockerfile — resume claim "deployed four containerized ML stages on GCP" is trivially visible.

### Critical Pitfalls

Top pitfalls cluster into **analytical risks** (pipeline produces wrong answers that look right) and **operational risks** (cost runaway, fat-image cold starts, viewer scope eating the project).

1. **GCP cost runaway** (Pitfall #4) — Phase 0 deploys Pub/Sub → Cloud Function billing kill switch; $20/mo budget alerts at 50/90/100%; default `--min-instances=0`. GCP has no native hard cap. Non-negotiable before any deploy.
2. **Video↔FIT clock alignment treated as "zero both timelines"** (Pitfall #3, ADR-2) — independent clocks drift 50ms/hr; after 60min the pose-cadence is 2–4s out of phase, breaking the headline correlation. Built as unit-testable module with synthetic-offset recovery test in Phase 1.
3. **Leg-crossing occlusion silently corrupts the far-side leg** (Pitfall #2) — MediaPipe emits coordinates anyway; bilateral asymmetry reflects model behavior not biomechanics. Treat side-on as single-leg-analyzer for v1; gate bilateral metrics on visibility ≥ threshold with timeline plot in viewer.
4. **Side-view camera-rig sloppiness** (Pitfall #1) — Phase 1 ships a filming protocol doc (camera at BB height, fiducial in frame, 35mm-equiv, tripod-only).
5. **FPS aliasing + Variable Frame Rate phone video** (Pitfall #8) — 60fps capture mandate + `ffprobe` VFR detection at ingest.
6. **Cloud Run cold start on fat ML container** (Pitfall #5) — multi-stage Docker, slim base, model bundled, <500MB, `/warmup` endpoint.
7. **Aspirational README claims** (Pitfall #6) — every claim must link to a specific module + test; `CAPABILITIES.md` "what this does NOT do" section.
8. **Viewer framework eats the project** (Pitfall #7) — strict budget: ≤300 LOC, ≤1 weekend, notebook-first.

Honourable mention: FIT-file edge cases (#9–#11) require a fixture suite of ≥6 edge-case files; gear inference must be `±1 cog` or a distribution, never a single integer.

## Implications for Roadmap

All four research streams independently arrived at the same build order: **local thin slice → containerize → GCP storage → orchestrate → viewer → polish.** Where dimensions reinforce each other, that's the recommended path. Where they nominally disagree (notebook vs Streamlit), the disagreement is sequencing-only.

### Phase 0: Project Bootstrap & Cost Guardrails [LOAD-BEARING]

**Rationale:** Pitfall #4 (cost runaway) and #13 (region mismatch) demand Phase-0 attention before any service is deployed. **Non-negotiable.**
**Delivers:**
- `pyproject.toml` + `uv.lock` with pinned stack (Python 3.12)
- Dockerfile skeletons for four pipeline stages
- GCP project with $20/mo budget + alerts at 50/90/100%
- **Pub/Sub → Cloud Function billing kill switch deployed and tested** (per `Cyclenerd/poweroff-google-cloud-cap-billing`)
- All resources pinned to one region via documented `gcloud` setup or Terraform
- `.gitignore` covers `*.json`, `.env`, raw FIT with GPS
- README skeleton with JD-bullet → code mapping placeholder
- `docs/filming-protocol.md` (camera height, fiducial, 60fps, CFR)

**Addresses:** Pitfalls #4, #13, #1, #8.
**Research flag:** No.

### Phase 1: Local Thin Slice (No GCP) [LOAD-BEARING — ANALYTICAL DE-RISKING]

**Rationale:** Architecture: "the real risks are pose-on-cycling, FIT parsing, alignment, stroke detection — cloud is easy." Build these locally first. Pitfall #19 requires ≥3 fixture rides.
**Delivers:**
- Four local Python scripts (Typer CLI) producing a notebook output
- MediaPipe Tasks API extraction with One-Euro + visibility-gating
- Garmin FIT SDK with fixture suite (≥6 edge-case files)
- Pedal stroke segmentation (`scipy.signal.find_peaks`)
- Video↔FIT cadence cross-correlation alignment as unit-tested module with synthetic-offset test
- Per-stroke knee angle, KOPS (2D — Pitfall #20), hip rock, asymmetry (single-leg fallback if visibility <70%)
- Top-N Pearson with n, p, 95% CI
- VFR detection at ingest via `ffprobe`
- Notebook: fused timeline + correlations + one annotated stroke

**Avoids:** Pitfalls #2, #3, #8, #15, #20, #11.
**Research flag:** **YES** — time-alignment signal processing (linear-fit drift correction, residual thresholds, synthetic-test patterns) + MediaPipe Tasks API specifics.

### Phase 1 Exit Criterion (the thin-slice MVP)

> Given one carefully-shot ride, locally (no GCP): MediaPipe pose with One-Euro + visibility gating; parsed FIT with gear inference (±1 cog framing); cadence-based time alignment with synthetic-offset test passing; per-stroke knee/KOPS/hip-rock/asymmetry; Top-N Pearson with confidence intervals; notebook with fused chart + correlations list + one annotated stroke. Against ≥3 fixture rides.

### Phase 2: Containerize Each Stage

**Rationale:** Same code, four Dockerfiles, runs locally via `make`. Cloud parity established before cost is incurred.
**Delivers:** Four Dockerfiles (`pipeline/pose|fit|features|correlate/`), multi-stage, `python:3.12-slim`, `libgl1 libglib2.0-0`, all <500MB, MediaPipe weights bundled, `lib/vision/` shared package, same notebook output from containers.
**Avoids:** Pitfall #5.
**Research flag:** No.

### Phase 3: GCP Storage & Manual Job Invocation

**Rationale:** Move storage to GCS + BigQuery before orchestration. JD claim "deployed on GCP" becomes literally true here.
**Delivers:**
- GCS buckets: `vision-raw/`, `vision-derived/`
- BigQuery dataset `vision` with `rides`, `telemetry_raw`, `pose_keypoints` (flat schema), `stroke_features`, `correlations`
- BQ SQL view `fused_timeline` applying per-ride offset (ADR-2)
- Containers read GCS URIs from env, load BQ on completion
- Cloud Run Jobs deployed (`--min-instances=0`, `--no-allow-unauthenticated`)
- Schema source-of-truth in `lib/vision/schemas/`
- Clapperboard sync workflow documented

**Avoids:** Pitfalls #4, #14, #18.
**Research flag:** Light — BQ partitioning best-practices.

### Phase 4: Orchestration (Workflows + Eventarc)

**Rationale:** Manifest-triggered pipeline eliminates upload races; resume bullet "event-driven GCP pipeline."
**Delivers:** `infra/workflows/ride.yaml` (pose+fit parallel → feature → correlate → `rides.status=ready`); Eventarc on `manifest.json` finalize; `make upload` writes manifest-last; Makefile mirror for local.
**Research flag:** **YES** — Eventarc + Workflows + Cloud Run Jobs coupling.

### Phase 5: Viewer (Streamlit) + Deployment Polish

**Rationale:** Upgrade notebook to clickable Streamlit on Cloud Run Service. Pitfall #7 strict budget.
**Delivers:** Streamlit (fused timeline, top correlations with effect sizes, annotated frame strip, visibility-timeline); Cloud Run Service `--min-instances=0` + `/warmup`; BQ materialized view per ride; ≤300 LOC; <500MB image; <15s cold start.
**Avoids:** Pitfalls #5, #7.
**Research flag:** No.

### Phase 6: Portfolio Polish & Narrative

**Rationale:** README + one-ride writeup is the highest-leverage feature; hiring managers click before they read. Pitfall #6.
**Delivers:** README with JD-bullet mapping + screenshots + "what this does NOT do"; one-ride markdown analysis (1–2 pages); GitHub Actions CI (ruff/pytest/build/push); run manifest per analysis; architecture diagram; ≥3 fixture rides exercised; cost dashboard screenshot.
**Avoids:** Pitfalls #6, #19.
**Research flag:** No.

### Phase 7 (Optional Stretch): Vertex AI Pipelines Wrapper

**Rationale:** Resume flourish only after v1 ships clean. Wrap Cloud Run Jobs in KFP v2 DAG; cost near-zero.
**Research flag:** **YES** — KFP v2 + Vertex AI Pipelines specifics.

### Phase Ordering Rationale

- Phase 0 first, non-negotiably — GCP has no spending cap (Pitfall #4)
- Local thin slice before any GCP — real risks are analytical (Architecture Build Order; Features MVP; Pitfalls phase-mapping)
- Containerize before deploying — cloud-parity pattern
- Storage before orchestration — easier to wire Workflows to existing GCS+BQ
- Viewer after pipeline — Pitfall #7 demands it
- Polish last — README against real code (Pitfall #6)
- Stretch only if v1 ships clean

### Where Research Dimensions Agree vs Disagree

**Strong agreement (all four):** build order; Cloud Run Jobs (not Endpoints/Services); off-the-shelf MediaPipe; time alignment as load-bearing analytical risk; Phase 0 cost kill switch precedence; BQ for aggregates + GCS for raw.

**Mild sequencing tension (resolved):** notebook (P1) vs Streamlit (P5); manual clapperboard vs auto cross-correlation (auto module in P1, manual override remains); Vertex AI Pipelines (deferred to optional P7).

**No fundamental disagreements surfaced.**

### Research Flags

Needs `/gsd-research-phase`:
- **Phase 1:** time-alignment signal processing + MediaPipe Tasks API specifics
- **Phase 4:** Eventarc + Workflows + Cloud Run Jobs coupling
- **Phase 7:** Vertex AI Pipelines (KFP v2) if pursued

Standard patterns (skip): Phase 0, 2, 3, 5, 6.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI May 2026; official docs cross-checked. MEDIUM only on Vertex AI Pipelines (Phase 7). |
| Features | HIGH | Competitor matrix + PROJECT.md core-value directly informs. MEDIUM on which 2–4 differentiators best signal to unknown hiring manager. |
| Architecture | HIGH | Cloud Run Jobs + GCS + BQ + Workflows is documented GCP idiom; ADR-1 and ADR-2 backed by cost data + signal-processing patterns. FusionPose paper confirms MediaPipe viable for cyclists. |
| Pitfalls | HIGH on GCP cost/portfolio/FIT traps; MEDIUM on cycling-specific pose-occlusion and VFR timing in pose pipelines (less-documented). |

**Overall confidence:** HIGH.

### Gaps to Address

- Hiring manager profile unknown — differentiator selection revisit if JD text surfaces
- Bilateral-metric viability — calibrate against first 1–3 real rides in Phase 1
- Manual vs auto alignment in v1 — decide during Phase 1 synthetic-offset test
- Notebook (P1) vs Streamlit (P5) viewer reconciled by phase boundary
- Garmin FIT fixture acquisition (≥6 edge-cases needed) — flag for early collection

## Sources

### Primary (HIGH confidence)
- [PyPI: mediapipe](https://pypi.org/project/mediapipe/) — 0.10.35
- [MediaPipe Pose Landmarker guide](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker)
- [Garmin FIT Python SDK](https://github.com/garmin/fit-python-sdk) — 21.205, May 2026
- [Polars releases](https://github.com/pola-rs/polars/releases) — 1.40
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
- [Cloud Run Jobs vs Cloud Batch](https://medium.com/google-cloud/cloud-run-jobs-vs-cloud-batch-choosing-your-engine-for-run-to-completion-workloads-8590a8e3a3b1)
- [Reduce ML model inference costs on GCP](https://medium.com/google-cloud/how-to-reduce-your-ml-model-inference-costs-on-google-cloud-e3d5e043980f)
- [BigQuery time-series guidance](https://cloud.google.com/bigquery/docs/working-with-time-series)
- [Execute a Cloud Run job using Workflows](https://cloud.google.com/workflows/docs/tutorials/execute-cloud-run-jobs)
- [Optimize Python applications for Cloud Run](https://cloud.google.com/run/docs/tips/python)
- [Automated GCP Killswitch — Cyclenerd](https://github.com/Cyclenerd/poweroff-google-cloud-cap-billing)
- [Streamlit release notes](https://docs.streamlit.io/develop/quick-reference/release-notes) — 1.55
- [uv docs (Astral)](https://docs.astral.sh/uv/)
- [FusionPose cyclist pose estimation](https://www.sciencedirect.com/science/article/pii/S1474034625009073)
- [labstreaminglayer time synchronization](https://labstreaminglayer.readthedocs.io/info/time_synchronization.html)

### Secondary (MEDIUM confidence)
- [Retul Fit](https://www.retul.com/retul-fit), [Leomo Type-R](https://www.leomo.io/), [MyVeloFit](https://www.myvelofit.com/)
- [TrainingPeaks pedaling asymmetry](https://www.trainingpeaks.com/coach-blog/diagnosing-correcting-pedaling-asymmetry-using-wko4/)
- [Bike fitting biomechanics review (2024)](https://www.researchgate.net/publication/381495046)
- [PoseSync video synchronization (arXiv)](https://arxiv.org/pdf/2308.12600)
- [One-Euro filter for pose smoothing](https://mohamedalirashad.github.io/FreeFaceMoCap/2021-12-25-filters-for-stability/)
- [Event-driven architecture on GCP](https://oneuptime.com/blog/post/2026-02-17-how-to-build-an-event-driven-architecture-on-gcp-using-eventarc-workflows-and-cloud-run/view)
- [Cadence detection in road cycling (MDPI Sensors)](https://www.mdpi.com/1424-8220/22/16/6140)
- [Garmin FIT Cookbook](https://developer.garmin.com/fit/cookbook/decoding-activity-files/)
- [VFR Detector](https://www.timebolt.io/VFR-Detector), [OpenCV VFR check](https://forum.opencv.org/t/vfr-variable-frame-rate-check/20612)
- [Bicycle gear ratio calculator](https://cyclingroad.com/bicycle-gear-ratio-cadence-and-speed-calculator/)

### Tertiary (LOW confidence)
- [Cyclemetry](https://github.com/walkersutton/cyclemetry), [Telemetry Studio](https://telemetrystudio.com/), [MetricFlix](https://metricflix.app/)
- [DeepKalPose (arXiv)](https://arxiv.org/html/2404.16558v1)

---
*Research completed: 2026-05-20*
*Ready for roadmap: yes*
