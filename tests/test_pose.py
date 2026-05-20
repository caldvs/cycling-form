"""Smoke test for the pose extraction module.

Skips automatically if the optional `pose` / `data` extras are not installed,
so the base CI pipeline (which only installs the dev group) stays green.

When the extras *are* available, we:
  1. Synthesize a tiny 10-frame video to a temp directory.
  2. Run `extract_pose` against it (no real human present, so we expect zero or
     near-zero detections — the assertion is on schema correctness, not on
     pose-detection quality).
  3. Verify the returned DataFrame either is empty *or* matches the documented
     flat schema exactly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("cv2", reason="opencv-python not installed (run uv sync --extra pose)")
pytest.importorskip("mediapipe", reason="mediapipe not installed (run uv sync --extra pose)")
pytest.importorskip("polars", reason="polars not installed (run uv sync --extra data)")


EXPECTED_SCHEMA: dict[str, str] = {
    "ride_id": "String",
    "frame_index": "Int64",
    "timestamp_ms": "Int64",
    "landmark_index": "Int32",
    "landmark_name": "String",
    "x": "Float64",
    "y": "Float64",
    "z": "Float64",
    "visibility": "Float64",
    "presence": "Float64",
}


def _make_synthetic_video(path: Path, n_frames: int = 10, fps: int = 30) -> None:
    import cv2
    import numpy as np

    height, width = 240, 320
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    try:
        for i in range(n_frames):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            # A drifting bright rectangle — keeps the file decodable, but no human
            # body so MediaPipe will (correctly) detect no poses.
            x0 = (i * 10) % (width - 40)
            frame[80:160, x0 : x0 + 40] = (0, 200, 200)
            writer.write(frame)
    finally:
        writer.release()


def test_extract_pose_schema(tmp_path: Path) -> None:
    """extract_pose returns a DataFrame whose column types match the contract."""
    from vision.pose import extract_pose

    video = tmp_path / "synthetic.mp4"
    _make_synthetic_video(video)

    models_dir = tmp_path / "models"
    result = extract_pose(video, models_dir=models_dir)

    df = result.keypoints
    assert set(df.columns) == set(EXPECTED_SCHEMA.keys()), (
        f"columns mismatch: got {df.columns}, want {list(EXPECTED_SCHEMA.keys())}"
    )
    for col, want in EXPECTED_SCHEMA.items():
        got = str(df.schema[col])
        assert got == want, f"column {col}: dtype {got} != expected {want}"

    # We don't assert on row count — synthetic frames may legitimately produce
    # zero detected poses. We DO assert that the extractor processed all frames.
    assert result.frame_count == 10
    assert result.fps == pytest.approx(30.0, abs=1.0)


def test_extract_pose_missing_video(tmp_path: Path) -> None:
    """A missing input file should raise FileNotFoundError immediately."""
    from vision.pose import extract_pose

    with pytest.raises(FileNotFoundError):
        extract_pose(tmp_path / "does-not-exist.mp4", models_dir=tmp_path / "models")
