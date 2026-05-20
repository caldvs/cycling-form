# CLAUDE.md

A portfolio computer-vision pipeline that analyzes indoor-trainer cycling video. Single MediaPipe pose model (BlazePose / `pose_landmarker_full.task`) + classical signal processing + Streamlit dashboard.

## Stack

- **Python 3.12** via `uv` (`pyproject.toml` + `uv.lock`). No `requirements.txt`. MediaPipe wheels don't yet support 3.13.
- **Pose**: `mediapipe` 0.10.x (Tasks API — `mediapipe.tasks.vision.PoseLandmarker`, not the legacy `mp.solutions.pose`), `opencv-python` 4.10.x.
- **DataFrames**: Polars 1.x. Convert to pandas only at boundaries (e.g. Streamlit `st.dataframe`).
- **Signal/stats**: `scipy.signal.find_peaks`, `scipy.stats.pearsonr`, manual One-Euro filter.
- **Telemetry**: `garmin-fit-sdk` (official Garmin); never use `python-fitparse` (dormant).
- **Viewer**: Streamlit 1.55+ with a custom `streamlit.components.v1.html` iframe that hosts `<video>` + `<canvas>` skeleton overlay + Plotly chart sharing one `requestAnimationFrame` loop.
- **Quality gates**: `ruff` (lint) + `mypy --strict` (`files = ["lib", "tests"]` — `viewer/` is intentionally outside mypy scope) + `pytest`.

## Run

```bash
uv sync --extra pose --extra data --extra cli --extra viewer
uv run streamlit run viewer/app.py
uv run pytest -q
```

## Conventions

- Pipeline modules under `lib/vision/`. Heavy deps imported lazily inside functions so the module imports cheaply.
- Tests use `pytest.importorskip(...)` BEFORE module-level imports of optional extras; ruff `E402` is suppressed under `tests/` for this pattern.
- Per-`(frame, landmark)` flat schema for keypoints — do NOT switch to nested-JSON storage.
- Strict types everywhere except deliberately shimmed third-party imports (use `# type: ignore[import-untyped]` for `mediapipe.tasks.*`, `scipy.*`, `garmin_fit_sdk`).

## Architecture

See `docs/architecture.md`.
