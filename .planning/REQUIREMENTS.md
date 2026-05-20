# Requirements: Vision — Cycling Form & Performance Analyzer

**Defined:** 2026-05-20
**Core Value:** Given a video of a ride and its FIT file, produce explainable per-stroke pose-vs-telemetry correlations that a cyclist could plausibly act on.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Bootstrap

- [x] **BOOT-01**: Repo is initialized with Python 3.12 toolchain (`pyproject.toml`, `uv.lock`, `ruff`, `mypy`, `pytest`)
- [ ] **BOOT-02**: GCP project is created with a billing budget capped at $20/month and alerts at 50/90/100%
- [ ] **BOOT-03**: A Pub/Sub → Cloud Function billing kill switch is deployed and tested (disables billing if budget is exceeded)
- [ ] **BOOT-04**: All GCP resources are pinned to a single region with the choice documented
- [ ] **BOOT-05**: A filming protocol is documented (`docs/filming-protocol.md`) covering camera height, fiducial, 60fps, CFR, framing
- [ ] **BOOT-06**: A README skeleton exists with a JD-bullet → code mapping table that downstream phases fill in
- [ ] **BOOT-07**: `.gitignore` excludes credentials, env files, and FIT files containing GPS

### Ingestion

- [ ] **ING-01**: User can place a single `(video.mp4, activity.fit)` pair in a configured input location and the pipeline picks it up
- [ ] **ING-02**: Ingestion writes a `manifest.json` containing ride_id, hashes, source filenames, and indoor/outdoor flag
- [ ] **ING-03**: Ingestion detects Variable Frame Rate (VFR) video via `ffprobe` and rejects or warns on VFR input
- [ ] **ING-04**: At least 3 fixture rides (real or synthetic) are committed for end-to-end testing

### Pose Extraction

- [ ] **POSE-01**: System extracts 2D body-pose keypoints per frame using MediaPipe Pose Landmarker (Tasks API) — knee, hip, ankle, shoulder, both sides
- [ ] **POSE-02**: Keypoint coordinates are smoothed with a One-Euro filter to reduce jitter
- [ ] **POSE-03**: Each keypoint carries a visibility/confidence score, persisted alongside coordinates
- [ ] **POSE-04**: Bilateral metrics are gated on far-side visibility ≥ a documented threshold; below-threshold strokes fall back to single-leg analysis
- [ ] **POSE-05**: Pose output is persisted in a flat-schema Parquet artifact (one row per (frame, landmark))

### Telemetry Parsing

- [ ] **TEL-01**: System parses FIT files using the official Garmin FIT Python SDK into a normalized timeseries (timestamp, power, speed, cadence, heart rate)
- [ ] **TEL-02**: Parser handles paused-ride records (`event/timer_paused`) without producing duplicate or null-gap rows
- [ ] **TEL-03**: Parser detects indoor-mode rides (no GPS, no speed) and tags the ride accordingly
- [ ] **TEL-04**: System computes a per-second gear estimate from cadence/speed ratio with a documented `±1 cog` uncertainty band (skipped for indoor)
- [ ] **TEL-05**: For outdoor rides only, system fetches matching environmental data (temperature, humidity, wind) from Open-Meteo and attaches it to telemetry

### Pedal Stroke Segmentation

- [ ] **STROKE-01**: System detects pedal-stroke boundaries from the video pose alone (peak-finding on ankle y-position), without using telemetry cadence
- [ ] **STROKE-02**: Each stroke is assigned a stroke_index, start_frame, end_frame, and TDC/BDC markers where detectable

### Time Alignment

- [ ] **ALIGN-01**: System aligns video frames to FIT timestamps by cross-correlating video-derived cadence against FIT-reported cadence
- [ ] **ALIGN-02**: Alignment is implemented as a pure, unit-testable function and passes a synthetic-offset recovery test (offset injected, alignment recovers it within tolerance)
- [ ] **ALIGN-03**: The per-ride alignment offset (and any linear drift coefficient) is stored as ride metadata
- [ ] **ALIGN-04**: Time-alignment is applied at query time via a BigQuery SQL view (`fused_timeline`), not in compute jobs

### Per-Stroke Metrics

- [ ] **METR-01**: System computes per-stroke knee angle range (min, max, range) from hip-knee-ankle keypoints
- [ ] **METR-02**: System computes per-stroke knee-over-pedal-spindle (KOPS) horizontal drift in 2D
- [ ] **METR-03**: System computes per-stroke hip rock (vertical hip-position range)
- [ ] **METR-04**: System computes per-stroke left/right asymmetry when bilateral visibility permits (gated by POSE-04)
- [ ] **METR-05**: System computes per-stroke telemetry aggregates (mean power, mean cadence, mean HR, gear distribution)

### Correlations

- [ ] **CORR-01**: System computes top-N Pearson and/or Spearman correlations between pose metrics and performance metrics across the ride
- [ ] **CORR-02**: Each reported correlation includes sample size (n), p-value, and 95% confidence interval
- [ ] **CORR-03**: System computes a rolling-window form-drift metric (e.g., knee-angle range over the last K strokes vs the first K) for fatigue detection — directly supports the PROJECT.md headline example

### Storage

- [ ] **STOR-01**: Raw artifacts (video, FIT, manifest) are persisted in Cloud Storage at `gs://vision-raw/{ride_id}/`
- [ ] **STOR-02**: Derived artifacts (Parquet outputs of each stage) are persisted to `gs://vision-derived/{ride_id}/`
- [ ] **STOR-03**: Analytical tables live in BigQuery dataset `vision`: `rides`, `telemetry_raw`, `pose_keypoints`, `stroke_features`, `correlations`
- [ ] **STOR-04**: BigQuery tables are partitioned by `ride_date` and clustered by `ride_id`
- [ ] **STOR-05**: A BigQuery view `fused_timeline` returns aligned per-frame data joining pose and telemetry through the per-ride offset

### GCP Deployment

- [ ] **GCP-01**: Each of the four pipeline stages (pose, fit, features, correlate) has its own Dockerfile, multi-stage, image size <500 MB
- [ ] **GCP-02**: All four stages are deployed as Cloud Run Jobs with `--min-instances=0` and `--no-allow-unauthenticated`
- [ ] **GCP-03**: Cloud Workflows orchestrates the pipeline (pose + fit in parallel → features → correlate → mark ride ready)
- [ ] **GCP-04**: Eventarc triggers the Workflow on `manifest.json` GCS-finalize events only (not on video/FIT blob writes)
- [ ] **GCP-05**: `make upload` script uploads video and FIT first, then writes manifest.json last (avoids upload-race triggers)

### Viewer

- [ ] **VIEW-01**: For Phase 1, system produces a Jupyter / Quarto notebook with: fused timeline plot (pose metric overlaid on power), top-N correlations table, one annotated pedal stroke
- [ ] **VIEW-02**: For Phase 5, system serves a Streamlit viewer on Cloud Run Service rendering the fused timeline, top correlations, an annotated frame strip, and a visibility-timeline overlay
- [ ] **VIEW-03**: Streamlit container is <500 MB, `--min-instances=0`, with a `/warmup` endpoint, and cold-starts in under 15 seconds

### Portfolio Narrative

- [ ] **PORT-01**: README explicitly maps each JD-area nice-to-have (CV/pose, GCP ML, sport telemetry, CS/Eng practices) to specific modules, files, or tests in this repo
- [ ] **PORT-02**: README contains a "What this does NOT do" section listing the explicit anti-features (no coaching prescriptions, no real-time, no custom-trained model, etc.)
- [ ] **PORT-03**: A one-ride markdown analysis writeup (1–2 pages) is committed, walking through inputs → outputs → one specific insight surfaced for that ride
- [ ] **PORT-04**: An architecture diagram is rendered (mermaid or static image) and embedded in the README
- [ ] **PORT-05**: GitHub Actions CI runs `ruff`, `mypy`, and `pytest` on every push, and builds + pushes the four pipeline images on tagged releases
- [ ] **PORT-06**: A run manifest (commit SHA, model version, lib versions) is persisted alongside each ride's outputs for reproducibility

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Pose

- **POSE-V2-01**: Compare MoveNet Thunder side-by-side against MediaPipe `model_complexity=2` and pick the empirically better one
- **POSE-V2-02**: Optional 3D pose via MMPose or a multi-camera setup
- **POSE-V2-03**: Saddle-pressure / IMU integration

### Advanced Correlations

- **CORR-V2-01**: Partial correlations and multivariate regression with explainability (SHAP)
- **CORR-V2-02**: Sensitivity analysis across alignment offset perturbations

### Vertex AI Pipelines

- **GCP-V2-01**: Wrap the four Cloud Run Jobs in a Vertex AI Pipelines KFP-v2 DAG as a resume flourish
- **GCP-V2-02**: Register a "pose model artifact" in Vertex AI Model Registry for resume legibility

### Multi-Ride Analytics

- **MULTI-V2-01**: Compare across rides (e.g., "knee-angle range trended down by 2° across 5 sessions")
- **MULTI-V2-02**: Multi-ride correlation aggregation with proper cross-ride statistical treatment

### Other Deferrals

- **STRAVA-V2-01**: Strava / TrainingPeaks API integration to skip local FIT-file step
- **OUTDOOR-V2-01**: Support outdoor video sources (helmet-cam, follow-cam, drone)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-user accounts and authentication | Single-user analytical tool; auth is portfolio noise |
| Real-time / live analysis during a ride | Batch-only post-ride processing; real-time has no JD-bullet payoff for the cost |
| Outdoor video pose estimation | v1 is indoor-trainer side-on only; outdoor camera rigs are a separate problem class |
| Native mobile app | Web viewer / notebook only |
| Coaching prescriptions ("change saddle height by X mm") | Surface correlations, do not prescribe — avoids medical / safety claims |
| Training a custom pose model | Use off-the-shelf (MediaPipe); engineering effort should go to the pipeline |
| Sport-mode beyond cycling (running, rowing, ski) | Scope tightness; JD signal is cycling-specific |
| Strava / TrainingPeaks API integration | Local FIT-file ingestion fully demonstrates the JD bullets |
| LLM-driven "AI coach" commentary | Hallucination risk; not the JD signal |
| 3D pose from a single side-on camera | Methodologically dubious; misleads more than informs |
| Saddle-pressure mapping or IMU integration | Hardware-dependent; out of scope for a software portfolio piece |
| Sub-second latency targets | Batch pipeline — latency is irrelevant |
| Kubernetes / GKE / Cloud Composer | Cloud Run Jobs + Workflows is sufficient and lower-cost |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| BOOT-01 | Phase 0 | Complete |
| BOOT-02 | Phase 0 | Pending |
| BOOT-03 | Phase 0 | Pending |
| BOOT-04 | Phase 0 | Pending |
| BOOT-05 | Phase 0 | Pending |
| BOOT-06 | Phase 0 | Pending |
| BOOT-07 | Phase 0 | Pending |
| ING-01 | Phase 1 | Pending |
| ING-02 | Phase 1 | Pending |
| ING-03 | Phase 1 | Pending |
| ING-04 | Phase 1 | Pending |
| POSE-01 | Phase 1 | Pending |
| POSE-02 | Phase 1 | Pending |
| POSE-03 | Phase 1 | Pending |
| POSE-04 | Phase 1 | Pending |
| POSE-05 | Phase 1 | Pending |
| TEL-01 | Phase 1 | Pending |
| TEL-02 | Phase 1 | Pending |
| TEL-03 | Phase 1 | Pending |
| TEL-04 | Phase 1 | Pending |
| TEL-05 | Phase 1 | Pending |
| STROKE-01 | Phase 1 | Pending |
| STROKE-02 | Phase 1 | Pending |
| ALIGN-01 | Phase 1 | Pending |
| ALIGN-02 | Phase 1 | Pending |
| ALIGN-03 | Phase 1 | Pending |
| ALIGN-04 | Phase 3 | Pending |
| METR-01 | Phase 1 | Pending |
| METR-02 | Phase 1 | Pending |
| METR-03 | Phase 1 | Pending |
| METR-04 | Phase 1 | Pending |
| METR-05 | Phase 1 | Pending |
| CORR-01 | Phase 1 | Pending |
| CORR-02 | Phase 1 | Pending |
| CORR-03 | Phase 1 | Pending |
| STOR-01 | Phase 3 | Pending |
| STOR-02 | Phase 3 | Pending |
| STOR-03 | Phase 3 | Pending |
| STOR-04 | Phase 3 | Pending |
| STOR-05 | Phase 3 | Pending |
| GCP-01 | Phase 2 | Pending |
| GCP-02 | Phase 3 | Pending |
| GCP-03 | Phase 4 | Pending |
| GCP-04 | Phase 4 | Pending |
| GCP-05 | Phase 4 | Pending |
| VIEW-01 | Phase 1 | Pending |
| VIEW-02 | Phase 5 | Pending |
| VIEW-03 | Phase 5 | Pending |
| PORT-01 | Phase 6 | Pending |
| PORT-02 | Phase 6 | Pending |
| PORT-03 | Phase 6 | Pending |
| PORT-04 | Phase 6 | Pending |
| PORT-05 | Phase 6 | Pending |
| PORT-06 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 53 total
- Mapped to phases: 53
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-20*
*Last updated: 2026-05-20 after initial definition*
