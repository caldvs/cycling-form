# Vision — Cycling Form & Performance Analyzer

[![CI](https://github.com/caldvs/cycling-form/actions/workflows/ci.yaml/badge.svg)](https://github.com/caldvs/cycling-form/actions/workflows/ci.yaml)

Cycling form & performance analyzer pairing **MediaPipe BlazePose** on indoor-trainer video with **Garmin FIT** telemetry, with per-stroke Pearson correlations between joint angles and power/cadence/heart-rate.

![Dashboard — synced video with skeleton overlay, joint-angle chart, per-stroke correlations](docs/dashboard.png)

## What it does

Given a video of an indoor-trainer ride (and optionally a `.fit` file), it:

1. Runs **MediaPipe Pose Landmarker** (`pose_landmarker_full.task` — BlazePose) over every frame; emits a flat per-`(frame, landmark)` Polars DataFrame.
2. Smooths the landmark traces with a **One-Euro filter** and optional visibility gating.
3. Computes per-frame **joint angles** at knee / hip / elbow / shoulder / ankle / trunk.
4. **Segments pedal strokes** via `scipy.signal.find_peaks` on a chosen joint-angle signal.
5. Parses the FIT file with the official **Garmin FIT Python SDK** into a per-second telemetry frame.
6. **Cross-correlates** pose-derived cadence with FIT cadence on a 1 Hz grid (per-lag Pearson over valid overlap) to recover the clock offset.
7. **Fuses** per-stroke pose metrics with mean telemetry within each stroke window, then computes **Pearson r / n / p / 95 % Fisher-z CI** between every pair of metrics.
8. Renders it all in a **Streamlit dashboard** with a synced video + skeleton overlay + multi-axis chart, with tabs for per-stroke metrics, correlations, and diagnostics.

## Quick start

```bash
# 1. Install uv if you don't have it.
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Sync the runtime stack (pose + data + cli + viewer extras).
uv sync --extra pose --extra data --extra cli --extra viewer

# 3. Launch the dashboard.
uv run streamlit run viewer/app.py
# -> http://localhost:8501
```

Drop a `.mp4` (and optionally a `.fit`) into the uploaders, hit Run analysis. The MediaPipe pose model (~9 MB) auto-downloads to `./models/` on first run.

### CLI (alternative)

```bash
uv run vision pose-extract path/to/ride.mp4 --out keypoints.parquet --overlay overlay.mp4
```

### Sample data

A 60-second synthetic FIT (no GPS, ramp 150→220 W, cadence with a deliberate bump) lives at `samples/sample-ride.fit`. Regenerate with:

```bash
uv run --with fit-tool python scripts/generate-sample-fit.py
```

## Repo layout

```
lib/vision/           # pipeline modules
  pose.py             #   MediaPipe + OpenCV → flat keypoints
  smoothing.py        #   One-Euro filter + visibility gate
  angles.py           #   knee / hip / elbow / shoulder / ankle / trunk
  strokes.py          #   scipy.signal.find_peaks → per-stroke table
  fit.py              #   garmin-fit-sdk → telemetry frame
  align.py            #   pose × FIT cadence cross-correlation
  correlations.py     #   per-stroke fusion + Pearson r/n/p/CI
  cli.py              #   typer CLI
  overlay.py          #   skeleton-MP4 renderer (CLI flag)

viewer/app.py         # Streamlit dashboard (custom HTML component)
tests/                # pytest suite — 23 tests
scripts/              # download-models.sh, generate-sample-fit.py
samples/              # sample-ride.fit fixture
docs/                 # architecture.md, dashboard.png
```

## Development

```bash
uv sync
uv run ruff check lib tests viewer
uv run mypy lib tests
uv run pytest -q
```

## What this does NOT do

- No coaching prescriptions — it reports correlations, not advice.
- No real-time analysis — batch only.
- No custom-trained pose model — uses MediaPipe out of the box.
- No outdoor / helmet-cam video — indoor-trainer side-on only.
- No multi-user / auth — local single-user.
- No 3D pose — 2D landmarks (z is MediaPipe's estimate, used loosely).

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for a mermaid + ASCII diagram and a walkthrough of the data flow.

## License

MIT — see `pyproject.toml`.
