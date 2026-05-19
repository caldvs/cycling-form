<!-- GSD:project-start source:PROJECT.md -->
## Project

**Vision — Cycling Form & Performance Analyzer**

A portfolio project that ingests indoor cycling video alongside a ride's telemetry file (FIT/TCX), extracts pedal-stroke pose metrics with computer vision, fuses them with power/speed/cadence/gear data and environmental inputs, and surfaces correlations like "knee-over-pedal-spindle drift correlates with power drop after minute 20." It's built for one user (the project owner), but designed to demonstrate end-to-end production thinking — pose estimation pipeline + GCP ML deployment + sport telemetry data engineering — as resume evidence for an endurance-sport performance role.

**Core Value:** Given a video of a ride and its FIT file, produce explainable per-stroke pose-vs-telemetry correlations that a cyclist could plausibly act on. Everything else (auth, multi-user, fancy UI) is optional — the analytical insight is the product.

### Constraints

- **Tech stack — pose:** Off-the-shelf 2D pose estimator (MediaPipe Pose or MoveNet Thunder) — chosen for accuracy/speed tradeoff and zero model-training cost
- **Tech stack — telemetry:** Python with `fitparse` (or equivalent) for FIT parsing — standard library for cycling FIT files
- **Tech stack — storage/compute:** Google Cloud Platform — Cloud Run for stateless inference, BigQuery for telemetry storage, Cloud Storage for video/FIT artifacts — directly maps to the "GCP-based ML workloads" JD bullet
- **Tech stack — language:** Python end-to-end — keeps pose + telemetry + GCP client code in one stack
- **Budget:** GCP free tier and small spend (target: under $20/month total). No GPU instances for v1; CPU inference acceptable for batch
- **Timeline:** Designed for ~4-8 weekends of focused work; favor end-to-end thin slice over deep specialization
- **Portfolio:** All work in a public repo; commits, README, and a short write-up are part of the deliverable
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack at a Glance
| Layer | Choice | Why (JD signal) |
|------|--------|-----------------|
| Language | Python 3.12 | One stack for pose + telemetry + GCP clients (PROJECT.md constraint) |
| Pose estimation | MediaPipe Pose Landmarker (Tasks API), `mediapipe` 0.10.35 | Off-the-shelf, CPU-friendly, 33 landmarks, Google-maintained — demonstrates CV/pose-estimation bullet without training a model |
| Video I/O | `opencv-python` 4.10+ | De facto for frame extraction; pairs naturally with MediaPipe `mp.Image` inputs |
| FIT parsing | `garmin-fit-sdk` 21.x (official Garmin) | Officially maintained; modern; ships with Profile.xlsx field definitions — demonstrates familiarity with the canonical sport-telemetry format |
| DataFrames | Polars 1.x (with pandas 2.x interop) | Apache Arrow native; fast on per-frame keypoint timelines; pyarrow round-trip to BigQuery is clean |
| Environmental data | Open-Meteo Historical Weather API via `openmeteo-requests` | Free, no API key, ERA5 historical back to 1940 — covers the "environmental inputs" JD bullet at $0 |
| Elevation | `srtm.py` (or skip in v1) | Indoor-trainer rides have no GPS track; only relevant if you ever ingest outdoor rides |
| Inference compute | Cloud Run Jobs (CPU, scale-to-zero) | Batch, run-to-completion, scales to zero — perfect fit for solo budget and the JD's "GCP-based ML workloads" bullet. NOT a Vertex AI Endpoint (that keeps a node hot 24/7) |
| Orchestration | Cloud Run Jobs triggered by a manual `gcloud run jobs execute` or Eventarc on GCS object create | No Airflow / no Composer / no Dagster — overkill for one user |
| Object storage | Cloud Storage (GCS), `google-cloud-storage` 3.x | Video + FIT artifacts; the obvious GCP idiom |
| Telemetry warehouse | BigQuery (partitioned by `ride_date`, clustered by `ride_id`) | Native time-series support, free-tier-friendly at this volume; demonstrates the "GCP" + "data engineering" angle |
| Loader | `google-cloud-bigquery` 3.x + `pandas-gbq` OR direct Arrow load via Storage Write API | Storage Write API for any production-feel; `load_table_from_dataframe` is fine for v1 |
| Viewer | Streamlit 1.55+ | Single Python process renders the timeline + correlations; pose-overlay videos embed via `st.video`; Cloud Run hosts it. Resume-legible without spending the weekend on a Next.js shell |
| Charts | Plotly (via `st.plotly_chart`) | Interactive zoom on a 60+ min ride timeline; pose-keypoint scatter on a still frame |
| Containerization | Docker, base image `python:3.12-slim` | Cloud Run requires a container; standard idiom |
| Dependency mgmt | `uv` + `pyproject.toml` + `uv.lock` | 10–100× faster than pip; lockfile reproducibility; standard 2026 setup |
| Testing | `pytest` 8.x + `pytest-cov` | Standard |
| Lint / type | `ruff` (lint + format) + `mypy` or `pyright` | Standard 2026 stack |
| CI | GitHub Actions | Public repo lives there anyway |
## Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12 | Runtime | MediaPipe wheels published for 3.9–3.12; 3.13 not yet supported by MediaPipe. 3.12 maximizes lifetime without painting into a corner. |
| MediaPipe Pose Landmarker | `mediapipe==0.10.35` | 2D/3D body landmark extraction per video frame | Google-maintained, actively released through April 2026, free, CPU-runnable, 33 landmarks suffice for knee/hip/ankle/shoulder geometry. Use the **Tasks API** (`mediapipe.tasks.vision.PoseLandmarker`), not the older `mp.solutions.pose` (legacy, in maintenance). |
| OpenCV | `opencv-python==4.10.*` | Video decode, frame iteration, optional pose-overlay rendering | Universal Python video toolkit; faster frame extraction than MoviePy (~3-4× per published benchmarks). |
| Garmin FIT Python SDK | `garmin-fit-sdk==21.205.*` | Parse `.FIT` files into records | Officially maintained by Garmin (last release 2026-05-19); ships with the current Profile.xlsx field map so newer Garmin/Wahoo files Just Work. Replaces the dormant `python-fitparse`. |
| Polars | `polars==1.40.*` | Fused timeline DataFrame (per-frame pose × per-second telemetry) | Arrow-native columnar engine, time bucket / asof-join primitives are first-class — critical for time-aligning 30fps video with 1Hz FIT records. |
| pandas | `pandas==2.2.*` | Interop with `pandas-gbq` and MediaPipe examples | Keep around for the ecosystem; convert to/from Polars on the boundary. |
| google-cloud-storage | `google-cloud-storage==3.10.*` | Upload/download video & FIT artifacts | Standard GCP client; v3 integrated `google-resumable-media`, auto-CRC32C checksums. |
| google-cloud-bigquery | `google-cloud-bigquery==3.x` | Load and query the telemetry warehouse | Standard GCP client. |
| google-cloud-aiplatform | `google-cloud-aiplatform==1.x` | (Optional) Vertex AI Python SDK if a Pipelines demo is desired later | Pulling this in makes the project legible as "Vertex AI" even if the actual inference runs on Cloud Run — see "Resume-legibility" note below. |
| Streamlit | `streamlit==1.55.*` | Viewer | Lowest-effort path from Python pandas/Polars to a hosted web app; runs on Cloud Run; embeds video, plots, and pose overlays. |
| Plotly | `plotly==5.24.*` | Interactive ride-timeline + correlation charts in Streamlit | Pan/zoom on long rides; `st.plotly_chart` integration is one line. |
## Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `openmeteo-requests` | 1.x | Historical weather (temp, humidity, wind, pressure) | Always — even indoor rides log ambient room temp inferred from device; outdoor rides need real weather. Free, no API key. |
| `pyarrow` | 17.x | Polars ↔ BigQuery zero-copy transport | Required as a transitive of Polars; explicit dependency makes BigQuery Storage Write API loads cleaner. |
| `pandas-gbq` | 0.24.x | `df.to_gbq()` one-liner for v1 loads | Quick BigQuery uploads from a notebook during prototyping. Replace with Storage Write API when you want a "production" talking point. |
| `pydantic` | 2.x | Typed config + telemetry record schemas | Validates parsed FIT records before they hit BigQuery; helps catch schema drift between Garmin firmware versions. |
| `typer` | 0.12.x | CLI entrypoints (`vision ingest`, `vision infer`, `vision fuse`) | Cleaner than argparse for a multi-command pipeline; pairs nicely with Cloud Run Jobs invocation. |
| `scipy` | 1.14.x | Signal processing for stroke detection (peak finding on knee-angle series) | `scipy.signal.find_peaks` is the right tool for cadence/stroke segmentation from a pose-derived joint-angle timeseries. |
| `numpy` | 2.0+ | Vector math on keypoints | Transitive; pin a minor to avoid MediaPipe wheel incompatibilities. |
| `fitdecode` | 0.10.x | (Optional alternative to Garmin SDK) | Only if Garmin SDK shows a bug for your specific device files. Skip otherwise. |
| `python-fitparse` | — | DO NOT USE | Dormant for years; replaced by Garmin's official SDK. |
| `pytest` | 8.x | Unit tests | Standard. |
| `pytest-cov` | 5.x | Coverage in CI | Resume-legibility — non-zero coverage badge. |
| `ruff` | 0.6.x | Lint + format | Replaces black + isort + flake8; standard 2026. |
| `mypy` or `pyright` | latest | Type checking | Pyright is faster; mypy has wider ecosystem. Either is fine. |
## Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Package + venv manager | `uv sync` creates `.venv` and `uv.lock` from `pyproject.toml`; 10–100× faster than pip. Standard for new 2026 Python projects. |
| Docker | Container image for Cloud Run | Base on `python:3.12-slim`; copy `pyproject.toml` + `uv.lock` then `uv sync --frozen`. |
| `gcloud` CLI | Deploy to Cloud Run, manage BQ datasets, upload to GCS | Service-account auth via `gcloud auth application-default login` for local dev. |
| `pre-commit` | Run ruff/mypy on commit | Keeps the public repo clean — JD evaluators *will* look at the repo. |
| GitHub Actions | CI: lint, test, build image, push to Artifact Registry | One workflow file; resume-legible. |
| Jupyter / `marimo` | Exploratory analysis | Use marimo if you want a notebook that also ships as a script — useful for the optional "notebook dashboard" alternative path. |
## Installation
# Bootstrap the project (no requirements.txt — uv + pyproject.toml only)
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| MediaPipe Pose Landmarker | MoveNet Thunder (TFLite) | If you specifically want a TensorFlow Hub talking point; MoveNet is single-person-only and faster, MediaPipe is more featureful and equally accurate for side-on cycling. |
| MediaPipe Pose Landmarker | MMPose (RTMPose) | If pose-estimation depth is the demonstration's *primary* selling point. MMPose is research-grade and gives a wider model zoo, but adds PyTorch + a heavier install. For a portfolio project that needs to *finish*, MediaPipe wins. |
| Garmin FIT SDK | `fitdecode` | If a specific FIT-format quirk breaks Garmin's parser; fitdecode is somewhat faster but unofficial. |
| Cloud Run Jobs | Vertex AI Batch Prediction | If your model were a registered Vertex AI Model artifact (e.g. a fine-tuned TFLite model) and you wanted a one-click "AI Platform" line on your resume. For an off-the-shelf MediaPipe pipeline, this is a Vertex-AI-for-Vertex-AI's-sake decision and adds operational complexity. **Note:** you can still add a Vertex AI Pipelines wrapper later as a portfolio flourish without changing the inference engine. |
| Cloud Run Jobs | Cloud Batch | If a single inference run needed >24h, GPU pools, or MPI-style worker coordination. Solo cycling-video pipelines don't. |
| Cloud Run Jobs | Vertex AI Endpoint | NEVER for batch — an endpoint keeps one node hot 24/7 ($ continuously) and offers no batch advantage for this workload. |
| BigQuery | DuckDB + Parquet on GCS | If you wanted zero GCP spend. But the JD says "GCP-based ML workloads" — DuckDB undermines that signal. Use BigQuery; the free tier (1 TB query/month, 10 GB storage) covers a hobby workload. |
| BigQuery | Cloud SQL Postgres + TimescaleDB | More OLTP-shaped; wrong tool. Cyclist telemetry is OLAP/read-mostly. |
| Streamlit | Next.js + FastAPI | If you also want to demonstrate frontend chops. Costs you 2–4 weekends and adds zero JD-signal beyond the CV/GCP/telemetry triad. Skip. |
| Streamlit | Jupyter / `marimo` notebook hosted as HTML | Lower polish, but acceptable if the hiring manager will read code more than they'll click a URL. Streamlit is the safer choice. |
| Streamlit | Dash (Plotly) | Slightly more customizable; substantially more code. Not worth it. |
| Polars | pandas-only | Fine for a v1 if you're more comfortable; you'll regret it on the 30fps × 60min × N-keypoints frame table. Use Polars. |
| `uv` | Poetry | Poetry works; uv is faster and is now the de facto 2026 choice. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Training a custom pose model (PyTorch / MMPose from scratch) | Burns 4+ weekends on a problem already solved by MediaPipe; adds rewrite risk; the JD asks for *applied* CV, not model R&D. Explicitly out of scope in PROJECT.md. | MediaPipe Pose Landmarker out-of-the-box |
| `mp.solutions.pose` (legacy MediaPipe Solutions API) | In maintenance mode; Google has shifted documentation effort to the Tasks API. Newer features (image segmentation outputs, model selector) only land on the Tasks API. | `mediapipe.tasks.vision.PoseLandmarker` |
| `python-fitparse` (original `dtcooper` repo) | Dormant for years; the maintainer publicly asked for help; doesn't track new Garmin Profile.xlsx fields. | `garmin-fit-sdk` (official) |
| Vertex AI Online Prediction Endpoint for this workload | Idle compute cost burns your $20/month budget; batch workloads don't benefit from a hot endpoint. | Cloud Run Jobs (CPU, scale-to-zero) |
| Kubernetes / GKE | Massive operational tax for one user; nothing here justifies it. | Cloud Run Jobs |
| Cloud Composer (managed Airflow) | $300+/month minimum; orchestration overkill for a 3-step pipeline. | A shell script, or `Typer` CLI commands chained in a Cloud Run Job, or Eventarc on GCS object creation. |
| Cloud Dataflow / Apache Beam | Streaming/large-batch engine; you have one video and one FIT file per run. | Plain Python in a Cloud Run Job. |
| Cloud Functions (gen 1) for inference | 540s timeout, 8GB RAM cap, cold-start unfriendly to MediaPipe model load. | Cloud Run Jobs (no timeout for jobs, plenty of RAM, model load amortized across input frames). |
| Firestore for telemetry | Document store; wrong shape for analytical scans across a ride. | BigQuery |
| Cloud SQL for telemetry | OLTP database; wrong shape. | BigQuery |
| Building a Next.js viewer | Pure frontend yak-shaving; doesn't move the JD-signal needle. | Streamlit |
| `mediapipe-silicon` fork on macOS | Outdated; the upstream `mediapipe` package now publishes Apple Silicon wheels. | `mediapipe` (mainline) |
| `pip install -r requirements.txt` | Slow, no lockfile, no env management. | `uv sync` |
| GPU instances for v1 | MediaPipe CPU inference handles a 60-min 1080p video in minutes; GPU would blow the budget. | CPU Cloud Run Jobs |
## Stack Patterns by Variant
### If you stay strictly inside the v1 scope (indoor-only, single video + FIT)
- Use **Cloud Run Jobs** for inference; trigger manually via `gcloud run jobs execute`
- Use **Streamlit** hosted on Cloud Run for the viewer
- Use **BigQuery** with a single partitioned table `rides` and a row per (frame_index, second)
- Skip elevation / SRTM entirely (indoor rides have no GPS)
- Wire weather data from Open-Meteo using the ride's `start_time` and a hardcoded "training location" lat/lon
### If you want a Vertex AI talking point on the resume
- Wrap the Cloud Run Job invocation inside a **Vertex AI Pipelines** (KFP v2) DAG with three components: `extract_pose`, `parse_fit`, `fuse_and_load_bq`
- Cost is near-zero (Pipelines bills per component-run), and the resume can say "Vertex AI Pipelines orchestrating Cloud Run Jobs"
- Confidence: MEDIUM — only do this once the v1 thin slice ships
### If outdoor rides are added later (currently out of scope)
- Switch elevation source to **`srtm.py`** for sea-level corrections on outdoor power curves
- Add `gpxpy` if you also want raw GPX support; the Garmin FIT SDK already handles FIT files for outdoor rides
- Do **not** add outdoor *video* pose estimation (helmet-cam) — explicitly out of scope
### If real-time becomes a requirement (currently out of scope)
- Replace Cloud Run Jobs with Cloud Run Services + WebSockets
- Add `mediapipe.tasks.vision.RunningMode.LIVE_STREAM`
- Re-evaluate everything — this is a different product
## Version Compatibility
| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `mediapipe==0.10.35` | `python>=3.9,<3.13` | No 3.13 wheels yet (as of May 2026). Pin Python to 3.12. |
| `mediapipe==0.10.35` | `protobuf<5,>=4` | MediaPipe pins protobuf; this can collide with `google-cloud-*` libs that want newer protobuf. Resolve by letting `uv` pick the SAT-solved version — usually `protobuf==4.x` works for both. |
| `polars==1.40` | `pyarrow>=14,<18` | Arrow round-trip stable. |
| `streamlit==1.55` | `python>=3.9` | OK on 3.12. |
| `opencv-python==4.10` | `numpy>=1.21,<3` | NumPy 2.x supported as of OpenCV 4.10. |
| `google-cloud-storage==3.10` | `python>=3.8` | OK on 3.12. |
| `garmin-fit-sdk==21.205` | `python>=3.6,<=3.13` | OK on 3.12. |
| Cloud Run container | base image `python:3.12-slim` | Add `libgl1 libglib2.0-0` apt packages — required by `opencv-python` and `mediapipe` at runtime. Skipping these is the #1 first-deploy footgun. |
## JD Signal Mapping (resume-legibility check)
| JD bullet | This stack's evidence |
|-----------|----------------------|
| Computer vision / pose estimation | MediaPipe Pose Landmarker Tasks API + OpenCV pipeline + per-stroke metric extraction (`scipy.signal`) |
| GCP-based ML workloads | Cloud Run Jobs (container-based ML inference), GCS (artifact storage), BigQuery (warehouse), optionally Vertex AI Pipelines wrapper |
| Sport/performance telemetry (power/speed/gear) | Official Garmin FIT SDK + Polars time-series + gear inference from cadence/speed + environmental enrichment from Open-Meteo |
| CS/Engineering background | uv + pyproject.toml + ruff + mypy + pytest + GitHub Actions + Dockerfile — modern 2026 Python engineering hygiene |
## Sources
- [PyPI: mediapipe](https://pypi.org/project/mediapipe/) — verified 0.10.35 latest, Python 3.9–3.12 wheels — HIGH confidence
- [PyPI: garmin-fit-sdk](https://pypi.org/project/garmin-fit-sdk/) — verified 21.205.0 released 2026-05-19 — HIGH confidence
- [MediaPipe Pose Landmarker official guide](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker) — Tasks API is the current path — HIGH confidence
- [Garmin FIT Python SDK repo](https://github.com/garmin/fit-python-sdk) — actively maintained, official — HIGH confidence
- [Polars releases](https://github.com/pola-rs/polars/releases) — 1.40.1 (April 2026) latest — HIGH confidence
- [Cloud Run Jobs vs Cloud Batch comparison (GCP community)](https://medium.com/google-cloud/cloud-run-jobs-vs-cloud-batch-choosing-your-engine-for-run-to-completion-workloads-8590a8e3a3b1) — run-to-completion design rationale — MEDIUM confidence
- [Vertex AI Batch Prediction docs](https://cloud.google.com/vertex-ai/docs/predictions/get-predictions) — confirms it's overkill for a non-registered-model workload — HIGH confidence
- [BigQuery time-series guidance](https://cloud.google.com/bigquery/docs/working-with-time-series) — partitioning + clustering best practices — HIGH confidence
- [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) — free, ERA5 since 1940, no key — HIGH confidence
- [google-cloud-storage 3.x docs](https://cloud.google.com/python/docs/reference/storage/latest) — v3.10 latest — HIGH confidence
- [Streamlit release notes](https://docs.streamlit.io/develop/quick-reference/release-notes) — 1.55 current as of March 2026 — HIGH confidence
- [uv + FastAPI/general project setup](https://docs.astral.sh/uv/guides/integration/fastapi/) — modern Python dep mgmt pattern — HIGH confidence
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
