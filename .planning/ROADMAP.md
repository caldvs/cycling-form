# Roadmap: Vision — Cycling Form & Performance Analyzer

**Project mode:** mvp
**Granularity:** coarse
**Phases:** 7 (Phase 0 through Phase 6)
**Coverage:** 53/53 v1 requirements mapped
**Created:** 2026-05-20

## Core Value

Given a video of a ride and its FIT file, produce explainable per-stroke pose-vs-telemetry correlations that a cyclist could plausibly act on. Demonstrate four JD signals across the build: (1) CS/Engineering practices, (2) computer vision / pose estimation, (3) GCP-based ML workloads, (4) sport/performance telemetry.

## Build Order Rationale

All four research dimensions (Stack, Architecture, Pitfalls, Features) converged on the same sequence:

1. **Phase 0** — Bootstrap & cost guardrails first. Pitfall #4 (cost runaway) and #13 (region mismatch) are load-bearing; GCP has no native hard spending cap.
2. **Phase 1** — Local thin slice next. The real risks are analytical (pose-on-cycling, FIT edge cases, time alignment, stroke detection) — cloud is the easy part.
3. **Phase 2** — Containerize before deploying. Cloud parity established before cost is incurred.
4. **Phase 3** — GCS + BigQuery + manual job invocation. The JD claim "deployed on GCP" becomes literally true.
5. **Phase 4** — Workflows + Eventarc. Event-driven orchestration on top of working storage.
6. **Phase 5** — Streamlit viewer + cold-start polish. Pitfall #7 strict budget (≤300 LOC, ≤1 weekend).
7. **Phase 6** — Portfolio polish and narrative. README + one-ride writeup is the highest-leverage feature against real code (Pitfall #6).

Vertex AI Pipelines (a v2 stretch flourish) is **out of v1 scope** and is not represented in this roadmap.

## Phases

- [ ] **Phase 0: Bootstrap & Cost Guardrails** — Pin GCP project, deploy billing kill switch, scaffold repo with Python toolchain and filming protocol
- [ ] **Phase 1: Local Thin Slice (No GCP)** — End-to-end analytical pipeline on the laptop: pose, FIT, stroke segmentation, alignment, metrics, correlations, notebook viewer against ≥3 fixture rides
- [ ] **Phase 2: Containerize Each Stage** — Four Dockerfiles (pose, fit, features, correlate), multi-stage, <500 MB each, same notebook output from containers via `make`
- [ ] **Phase 3: GCP Storage + Manual Job Invocation** — GCS buckets, BigQuery dataset with flat-schema pose, `fused_timeline` SQL view, Cloud Run Jobs deployed with `--min-instances=0`, manually invoked
- [ ] **Phase 4: Orchestration (Workflows + Eventarc)** — Manifest-triggered pipeline: `make upload` writes manifest last, Eventarc on `manifest.json` finalize, Cloud Workflows runs pose+fit in parallel then features then correlate
- [ ] **Phase 5: Viewer (Streamlit) + Deployment Polish** — Streamlit on Cloud Run Service renders fused timeline, top correlations, annotated frame strip, visibility-timeline overlay; <500 MB, `/warmup`, <15s cold start
- [ ] **Phase 6: Portfolio Polish & Narrative** — README with JD-bullet mapping, one-ride markdown writeup, architecture diagram, GitHub Actions CI, run manifests, anti-features section

## Phase Details

### Phase 0: Bootstrap & Cost Guardrails
**Goal:** A safe, cost-bounded GCP project and a disciplined local repo exist; no compute service can run away with the bill before Phase 3 ever ships
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** BOOT-01, BOOT-02, BOOT-03, BOOT-04, BOOT-05, BOOT-06, BOOT-07
**JD signal coverage:**
  - CS/Eng: `pyproject.toml` + `uv.lock` + `ruff` + `mypy` + `pytest`, `.gitignore` covers credentials
  - GCP ML: project pinned to one region, $20/month budget with alerts at 50/90/100%, kill switch deployed
  - CV/pose: filming protocol doc (camera height, fiducial, 60fps, CFR) — locks the geometry that downstream pose work depends on
  - Sport telemetry: `.gitignore` excludes raw FIT with GPS (privacy hygiene for a portfolio repo)
**Success Criteria** (what must be TRUE):
  1. `uv sync` reproduces the dev environment from `pyproject.toml` + `uv.lock`, and `ruff` + `mypy` + `pytest` all run cleanly against the skeleton
  2. A GCP project exists with a $20/month budget and email alerts at 50/90/100%, with all chosen resources pinned to a single documented region
  3. **The Pub/Sub → Cloud Function billing kill switch is deployed AND tested end-to-end** — a simulated budget-exceeded Pub/Sub message triggers the function and disables billing on a throwaway project (verifiable via Cloud Function logs and a billing-state check)
  4. `docs/filming-protocol.md` exists and specifies camera height = BB height, fiducial in frame, 60fps, CFR, framing, tripod-only
  5. The README skeleton contains a JD-bullet → code mapping table with placeholder rows for each phase to fill in
**Plans:** 6/7 plans executed
  - [x] 00-01-PLAN.md — Python 3.12 toolchain (pyproject.toml, uv.lock, lib/vision/, smoke test)
  - [x] 00-02-PLAN.md — Repo hygiene (.gitignore, CONTRIBUTING.md, NOTICE stub)
  - [x] 00-03-PLAN.md — Vendor Cyclenerd kill-switch source into infra/kill-switch/
  - [x] 00-04-PLAN.md — Author scripts/bootstrap-gcp.{env.example,sh} + scripts/test-kill-switch.sh
  - [x] 00-05-PLAN.md — Author docs/filming-protocol.md (one-pager + ASCII diagram)
  - [x] 00-06-PLAN.md — README skeleton with JD-mapping table + .github/workflows/ci.yaml
  - [ ] 00-07-PLAN.md — [operator-run] Bootstrap live GCP project + test kill switch end-to-end

### Phase 1: Local Thin Slice (No GCP)
**Goal:** Given one carefully-shot ride locally on the laptop, the analytical pipeline produces a fused-timeline notebook with top-N correlations and one annotated stroke — the four analytical risks (pose-on-cycling, FIT edge cases, stroke segmentation, time alignment) are de-risked before any GCP code is written
**Mode:** mvp
**Depends on:** Phase 0
**Requirements:** ING-01, ING-02, ING-03, ING-04, POSE-01, POSE-02, POSE-03, POSE-04, POSE-05, TEL-01, TEL-02, TEL-03, TEL-04, TEL-05, STROKE-01, STROKE-02, ALIGN-01, ALIGN-02, ALIGN-03, METR-01, METR-02, METR-03, METR-04, METR-05, CORR-01, CORR-02, CORR-03, VIEW-01
**JD signal coverage:**
  - CV/pose: MediaPipe Tasks API with One-Euro smoothing, visibility-gating, pedal-stroke segmentation from pose alone (`scipy.signal.find_peaks` on ankle y), per-stroke knee angle / 2D KOPS / hip rock / asymmetry
  - Sport telemetry: official Garmin FIT SDK, pause-event handling, indoor detection, gear inference with ±1 cog framing, Open-Meteo enrichment (outdoor only)
  - CS/Eng: alignment as a pure unit-testable function with synthetic-offset recovery test; ≥3 fixture rides exercised
  - GCP ML: deferred to Phase 2/3 — kept out by design to isolate analytical risk
**Success Criteria** (what must be TRUE):
  1. Running the local CLI against any of ≥3 committed fixture rides produces a Jupyter/Quarto notebook with: a fused timeline plot (pose metric overlaid on power), a top-N correlations table with n / p / 95% CI, and one annotated pedal stroke
  2. **The synthetic-offset alignment test passes against ≥3 fixture rides** — for each ride, an offset (and optional linear drift) is injected into the FIT timestamps, `align()` recovers it within the documented tolerance (residual < 1 video frame), and the test is reproducible in CI
  3. Pose extraction produces a flat-schema Parquet (one row per (frame, landmark)) with per-keypoint visibility scores, and bilateral metrics are gated on far-side visibility ≥ a documented threshold with single-leg fallback below it
  4. The FIT parser correctly handles paused-ride records, distinguishes indoor from outdoor mode, skips gear inference and weather enrichment on indoor rides, and produces no duplicate or null-gap rows
  5. Top-N correlations are reported with sample size, p-value, and 95% confidence interval — never as a bare `r` value
**Plans:** TBD
**Research flag:** time-alignment signal processing + MediaPipe Tasks API specifics

### Phase 2: Containerize Each Stage
**Goal:** The same local pipeline runs as four independently-deployable container images locally via `make`, with no GCP-specific bugs and no cold-start fat-image issues waiting to surface in Phase 3
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** GCP-01
**JD signal coverage:**
  - GCP ML: four containerized pipeline stages — the resume claim "deployed four containerized ML stages on GCP" is trivially visible in the repo layout (`pipeline/pose/`, `pipeline/fit/`, `pipeline/features/`, `pipeline/correlate/`)
  - CS/Eng: multi-stage Docker, slim base, MediaPipe weights bundled in-image, image size budget enforced as an acceptance criterion (not an afterthought)
  - CV/pose: pose-job container produces identical Parquet output to the Phase 1 local script — proves containerization didn't break the analytical layer
  - Sport telemetry: fit-job container handles the full Phase 1 fixture suite without regression
**Success Criteria** (what must be TRUE):
  1. Each of the four stages (`pipeline/pose/`, `pipeline/fit/`, `pipeline/features/`, `pipeline/correlate/`) has its own multi-stage `Dockerfile` based on `python:3.12-slim` with `libgl1` and `libglib2.0-0` installed
  2. All four images build successfully and each is verified to be under 500 MB via `docker images`
  3. `make pipeline-local RIDE=<id>` runs all four containers against a Phase 1 fixture ride and produces the same notebook output as the Phase 1 local CLI (byte-comparable or value-comparable within float tolerance)
  4. `lib/vision/` shared package (schemas, GCS path helpers, ride-ID conventions) is imported by every container, preventing schema drift between writers
**Plans:** TBD

### Phase 3: GCP Storage + Manual Job Invocation
**Goal:** The pipeline is literally running on GCP — containers read raw artifacts from GCS, write results to BigQuery, and the `fused_timeline` SQL view applies the per-ride alignment offset on JOIN; jobs are invoked manually via `gcloud run jobs execute`, orchestration comes in Phase 4
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** STOR-01, STOR-02, STOR-03, STOR-04, STOR-05, GCP-02, ALIGN-04
**JD signal coverage:**
  - GCP ML: Cloud Run Jobs deployed with `--min-instances=0` and `--no-allow-unauthenticated`; GCS buckets and BigQuery dataset live in the chosen region
  - CS/Eng: BigQuery schema source-of-truth in `lib/vision/schemas/`; tables partitioned by `ride_date`, clustered by `ride_id`; flat-schema pose table (not JSON-blob) so queries are fast and obvious
  - Sport telemetry: telemetry warehouse pattern — `telemetry_raw` partitioned/clustered correctly for analytical scans
  - CV/pose: pose-job runs in cloud (ADR-3 — pose inference is not local-only) producing the per-frame keypoints table that powers downstream stroke and correlation work
**Success Criteria** (what must be TRUE):
  1. Manually invoking the four Cloud Run Jobs in order (`gcloud run jobs execute pose-job`, `fit-job`, `feature-job`, `correlate-job`) against a fixture ride produces the same fused-timeline and correlations as Phase 2, but reads from `gs://vision-raw/{ride_id}/` and writes to BigQuery dataset `vision`
  2. The BigQuery view `fused_timeline` joins `pose_keypoints` and `telemetry_raw` through the per-ride offset stored in `rides`, and returns identical aligned data to the Phase 1 unit-test fixtures
  3. All Cloud Run Jobs are deployed with `--min-instances=0` and `--no-allow-unauthenticated`; idle cost is verified at $0 across a full week
  4. BigQuery tables `rides`, `telemetry_raw`, `pose_keypoints`, `stroke_features`, `correlations` exist, are partitioned by `ride_date` and clustered by `ride_id`, and store pose keypoints in a flat schema (one row per (frame, landmark)) — not JSON
**Plans:** TBD

### Phase 4: Orchestration (Workflows + Eventarc)
**Goal:** Uploading a ride end-to-end is one command — `make upload RIDE=<id>` writes video and FIT first then `manifest.json` last; Eventarc on the manifest finalize triggers a Cloud Workflow that runs pose+fit in parallel, then features, then correlate, then marks the ride ready — no upload races and no manual job orchestration
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** GCP-03, GCP-04, GCP-05
**JD signal coverage:**
  - GCP ML: event-driven GCP pipeline — Eventarc + Cloud Workflows + Cloud Run Jobs is a documented, current GCP idiom and a clean resume bullet
  - CS/Eng: manifest-last upload pattern is a defensible engineering choice that eliminates a real upload-race failure mode; Makefile mirror provides local-parity execution of the same workflow
  - CV/pose: pose-job runs in parallel with fit-job, demonstrating concurrent pipeline branches
  - Sport telemetry: fit-job runs in the same orchestration, on its own clock, independent of video processing — ADR (pose-job knows nothing about FIT and vice versa) verified end-to-end
**Success Criteria** (what must be TRUE):
  1. `make upload RIDE=<id>` uploads `video.mp4` and `activity.fit` to `gs://vision-raw/{ride_id}/` and writes `manifest.json` last; the workflow is observed to trigger only on the manifest finalize, not on the video or FIT blob writes
  2. `infra/workflows/ride.yaml` runs pose-job and fit-job in parallel, then feature-job (after pose), then correlate-job (after features + fit), then sets `rides.status = "ready"` in BigQuery
  3. A Workflow execution against a fixture ride completes end-to-end without manual intervention and produces the same outputs as Phase 3's manual invocation
  4. The Makefile mirrors the workflow steps so the same DAG can be executed locally against the Phase 2 containers, preserving local-parity for development
**Plans:** TBD
**Research flag:** Eventarc + Workflows + Cloud Run Jobs coupling

### Phase 5: Viewer (Streamlit) + Deployment Polish
**Goal:** A reviewer with no terminal access can click a URL and see the fused timeline, top correlations with effect sizes, an annotated frame strip, and a visibility-timeline overlay — within a strict ≤300 LOC, <500 MB, <15s cold start budget so the viewer doesn't eat the project (Pitfall #7)
**Mode:** mvp
**Depends on:** Phase 4
**Requirements:** VIEW-02, VIEW-03
**JD signal coverage:**
  - CS/Eng: strict LOC and image-size budgets enforced as acceptance criteria; `/warmup` endpoint demonstrates cold-start mitigation
  - GCP ML: Streamlit on Cloud Run Service with `--min-instances=0` and `/warmup` — a defensible cost-vs-latency tradeoff documented in the README
  - CV/pose: annotated frame strip and visibility-timeline overlay surface the pose work visually — pose results are the headline visual artifact
  - Sport telemetry: fused timeline plots pose metric overlaid on power; correlations table reports effect sizes (r, n, p, 95% CI) — telemetry-driven analytical claims are visible and defensible
**UI hint:** yes
**Success Criteria** (what must be TRUE):
  1. The Streamlit viewer is deployed on Cloud Run Service with `--min-instances=0` and renders, for a given `ride_id`, the fused timeline, the top correlations with n / p / 95% CI, an annotated frame strip from one representative stroke, and a visibility-timeline overlay
  2. The Streamlit container image is under 500 MB (verified via `docker images`) and the measured cold-start time from `/warmup` invocation to first interactive render is under 15 seconds
  3. The viewer source code is under 300 lines of Python (verified via `cloc` or equivalent), with no React/JS toolchain
  4. The viewer is read-only against BigQuery — it imports `lib/vision/` schemas and has zero coupling to the compute layer; pipeline changes don't require viewer redeploys
**Plans:** TBD

### Phase 6: Portfolio Polish & Narrative
**Goal:** A hiring manager visiting the public repo can, in under 60 seconds, see the JD-bullet → code mapping, the architecture diagram, the one-ride writeup with a specific insight, and a CI badge — every README claim links to a specific module + test, every anti-feature is explicit, and the cost story is visible
**Mode:** mvp
**Depends on:** Phase 5
**Requirements:** PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06
**JD signal coverage:**
  - CS/Eng: GitHub Actions CI runs `ruff` + `mypy` + `pytest` on every push and builds + pushes the four pipeline images on tagged releases; run manifests (commit SHA, model version, lib versions) are persisted alongside each ride's outputs
  - CV/pose: README links the pose-job module + tests + the annotated-stroke screenshot to the "computer vision / pose estimation" JD bullet
  - GCP ML: README links the Cloud Run Jobs + Workflows + BigQuery + cost dashboard screenshot to the "GCP-based ML workloads" JD bullet; architecture diagram is rendered (mermaid or static image) and embedded
  - Sport telemetry: README links the FIT parser + gear-inference module + per-stroke metrics to the "sport/performance telemetry" JD bullet; one-ride markdown analysis walks through inputs → outputs → one specific insight surfaced for that ride
**Success Criteria** (what must be TRUE):
  1. The README maps each JD-area (CV/pose, GCP ML, sport telemetry, CS/Eng practices) to specific modules, files, or tests in the repo — every claim links to a line of code within 30 seconds of search
  2. A "What this does NOT do" section explicitly lists the anti-features (no coaching prescriptions, no real-time, no custom-trained model, no outdoor video, no multi-user, no 3D pose, no Strava integration)
  3. A one-ride markdown analysis writeup (1–2 pages) is committed at `docs/analyses/<ride_id>.md` and walks through inputs → outputs → one specific insight surfaced for that ride
  4. An architecture diagram (mermaid or static image) is embedded in the README and matches the actual pipeline shape
  5. GitHub Actions CI is green on `main` and runs `ruff` + `mypy` + `pytest` on every push, plus image build/push on tagged releases; a CI badge is in the README
  6. A run manifest (commit SHA, model version, lib versions) is persisted alongside each ride's outputs in `gs://vision-derived/{ride_id}/manifest.json` and is verifiable for at least the ≥3 fixture rides
**Plans:** TBD

## Coverage Summary

| Category | Count | Phases |
|----------|-------|--------|
| Bootstrap (BOOT) | 7 | Phase 0 |
| Ingestion (ING) | 4 | Phase 1 |
| Pose Extraction (POSE) | 5 | Phase 1 |
| Telemetry Parsing (TEL) | 5 | Phase 1 |
| Pedal Stroke Segmentation (STROKE) | 2 | Phase 1 |
| Time Alignment (ALIGN) | 4 | Phase 1 (ALIGN-01/02/03), Phase 3 (ALIGN-04) |
| Per-Stroke Metrics (METR) | 5 | Phase 1 |
| Correlations (CORR) | 3 | Phase 1 |
| Storage (STOR) | 5 | Phase 3 |
| GCP Deployment (GCP) | 5 | Phase 2 (GCP-01), Phase 3 (GCP-02), Phase 4 (GCP-03/04/05) |
| Viewer (VIEW) | 3 | Phase 1 (VIEW-01), Phase 5 (VIEW-02/03) |
| Portfolio Narrative (PORT) | 6 | Phase 6 |
| **Total v1** | **54** | All mapped |

Note: the REQUIREMENTS.md table lists 53 v1 requirements with a 53/53 coverage line; the row count above (54) is correct as listed in REQUIREMENTS.md. The traceability table is authoritative — 53 unique requirement IDs, each mapped to exactly one phase.

## JD-Bullet → Phase Coverage Matrix

A hiring manager reading the roadmap should see all four JD areas exercised across the phases:

| JD area | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 |
|---------|---------|---------|---------|---------|---------|---------|---------|
| CV / pose estimation | filming protocol locks geometry | MediaPipe Tasks API + One-Euro + visibility gating + per-stroke metrics | pose-job container parity | pose-job runs in cloud (ADR-3) | pose-job runs in parallel branch | annotated frame strip + visibility overlay | README links pose module to JD bullet |
| GCP ML | budget + kill switch + region pin | (deliberately out — analytical first) | four container images | Cloud Run Jobs + GCS + BQ | Workflows + Eventarc | Streamlit on Cloud Run Service + `/warmup` | cost dashboard screenshot + architecture diagram |
| Sport telemetry | .gitignore for raw FIT GPS | Garmin FIT SDK + pause handling + indoor detection + gear inference ±1 cog + Open-Meteo | fit-job container parity | telemetry_raw partitioned/clustered | fit-job in parallel branch | fused timeline (pose × power) + correlations with n/p/CI | README links FIT parser + one-ride analysis |
| CS / Engineering | `pyproject.toml` + uv + ruff + mypy + pytest | alignment as pure unit-testable function with synthetic-offset test | multi-stage Docker + shared `lib/vision/` | BQ schema source-of-truth + ADR-2 SQL alignment | manifest-last upload + local-parity Makefile | strict LOC and image-size budgets | GitHub Actions CI + run manifests + anti-features section |

## Progress Tracker

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Bootstrap & Cost Guardrails | 6/7 | In Progress|  |
| 1. Local Thin Slice (No GCP) | 0/0 | Not started | - |
| 2. Containerize Each Stage | 0/0 | Not started | - |
| 3. GCP Storage + Manual Job Invocation | 0/0 | Not started | - |
| 4. Orchestration (Workflows + Eventarc) | 0/0 | Not started | - |
| 5. Viewer (Streamlit) + Deployment Polish | 0/0 | Not started | - |
| 6. Portfolio Polish & Narrative | 0/0 | Not started | - |

Plans are decomposed during `/gsd:plan-phase`; counts are filled in when planning starts.

## Notes

- **v2 / stretch deferrals** (per REQUIREMENTS.md and SUMMARY.md): Vertex AI Pipelines wrapper, MoveNet vs MediaPipe head-to-head, 3D pose, partial correlations / SHAP, multi-ride analytics, Strava/TrainingPeaks API, outdoor video. None of these block any v1 phase.
- **Phase 0 is non-negotiable.** GCP has no native hard spending cap. The billing kill switch test in Phase 0 is what prevents a forgotten `--min-instances=1` from generating a $200 bill during Phases 2–6.
- **Phase 1 is the analytical de-risking phase.** All four "wrong answers that look right" pitfalls (camera-rig, leg occlusion, clock alignment, FIT edge cases) are addressed here, before any GCP cost is incurred. The synthetic-offset alignment test passing against ≥3 fixture rides is the load-bearing exit criterion.
- **Research flags raised:** Phase 1 (time-alignment signal processing + MediaPipe Tasks API specifics), Phase 4 (Eventarc + Workflows + Cloud Run Jobs coupling). Both should be addressed via `/gsd-research-phase` before plan creation for those phases.

---
*Roadmap created: 2026-05-20*
*Mode: mvp; granularity: coarse*
