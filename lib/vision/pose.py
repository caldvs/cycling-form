"""MediaPipe Pose Landmarker (Tasks API) wrapper.

Given a video file, runs pose inference per frame and returns a flat Polars
DataFrame with one row per (frame_index, landmark_index). The schema is
deliberately flat (not JSON-blob) so downstream BigQuery writes in Phase 3 can
partition + cluster cleanly — see .planning/research/ARCHITECTURE.md ADR-2.

Uses the Tasks API (`mediapipe.tasks.vision.PoseLandmarker`) as mandated by
CLAUDE.md — the legacy `mp.solutions.pose` is in maintenance.

Heavy deps (mediapipe, cv2, polars) are imported lazily inside `extract_pose`
so this module can be imported in environments that only have the base
dependency group (e.g. CI lint/type passes without the `pose` extra).
"""

from __future__ import annotations

import logging
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

logger = logging.getLogger(__name__)

# 33 landmarks emitted by MediaPipe Pose Landmarker — name lookup is hard-coded
# rather than relying on the mediapipe enum so this module's public schema is
# stable across mediapipe minor versions.
LANDMARK_NAMES: tuple[str, ...] = (
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
)

# Public URL for the "full" pose landmarker model (~9 MB, float16, balanced
# speed/accuracy). The "lite" and "heavy" variants are at sibling paths.
DEFAULT_MODEL_URL: str = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)
DEFAULT_MODEL_FILENAME: str = "pose_landmarker_full.task"


@dataclass(frozen=True)
class PoseExtractResult:
    """Return type of `extract_pose` — keypoints + the video metadata they came from."""

    keypoints: pl.DataFrame
    frame_count: int
    fps: float
    width: int
    height: int


def ensure_model(model_path: Path | None, models_dir: Path) -> Path:
    """Resolve a model path. If `model_path` is None, download the default model
    into `models_dir` on first use and return its path.
    """
    if model_path is not None:
        if not model_path.exists():
            raise FileNotFoundError(f"Pose model file not found: {model_path}")
        return model_path

    models_dir.mkdir(parents=True, exist_ok=True)
    target = models_dir / DEFAULT_MODEL_FILENAME
    if target.exists():
        return target

    logger.info("Downloading pose model from %s -> %s", DEFAULT_MODEL_URL, target)
    with urllib.request.urlopen(DEFAULT_MODEL_URL) as response:
        target.write_bytes(response.read())
    return target


def extract_pose(
    video_path: Path,
    model_path: Path | None = None,
    *,
    ride_id: str = "unknown",
    models_dir: Path = Path("models"),
) -> PoseExtractResult:
    """Run MediaPipe Pose Landmarker over every frame of `video_path`.

    Returns a `PoseExtractResult` whose `.keypoints` is a Polars DataFrame with
    one row per (frame_index, landmark_index) — 33 rows per processed frame.
    """
    # Lazy imports so this module is importable without the pose+data extras.
    import cv2
    import mediapipe as mp  # type: ignore[import-untyped]
    import polars as pl
    from mediapipe.tasks import python as mp_python  # type: ignore[import-untyped]
    from mediapipe.tasks.python import vision as mp_vision  # type: ignore[import-untyped]

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    resolved_model = ensure_model(model_path, models_dir)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV could not open video: {video_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    base_options = mp_python.BaseOptions(model_asset_path=str(resolved_model))
    options = mp_vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_poses=1,
        output_segmentation_masks=False,
    )

    rows: list[dict[str, object]] = []
    frame_index = 0

    try:
        with mp_vision.PoseLandmarker.create_from_options(options) as landmarker:
            while True:
                ok, frame_bgr = cap.read()
                if not ok:
                    break
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                timestamp_ms = int(round(frame_index * 1000.0 / fps))

                result = landmarker.detect_for_video(mp_image, timestamp_ms)
                landmarks_list = result.pose_landmarks if result is not None else []

                if landmarks_list:
                    for landmark_index, lm in enumerate(landmarks_list[0]):
                        rows.append(
                            {
                                "ride_id": ride_id,
                                "frame_index": frame_index,
                                "timestamp_ms": timestamp_ms,
                                "landmark_index": landmark_index,
                                "landmark_name": LANDMARK_NAMES[landmark_index]
                                if landmark_index < len(LANDMARK_NAMES)
                                else f"landmark_{landmark_index}",
                                "x": float(lm.x),
                                "y": float(lm.y),
                                "z": float(lm.z),
                                "visibility": float(getattr(lm, "visibility", 0.0)),
                                "presence": float(getattr(lm, "presence", 0.0)),
                            }
                        )
                # Frames with no detected pose contribute zero rows — visibility
                # gating downstream (Phase 1 POSE-04) handles gaps explicitly.
                frame_index += 1
    finally:
        cap.release()

    schema: dict[str, type[pl.DataType] | pl.DataType] = {
        "ride_id": pl.Utf8,
        "frame_index": pl.Int64,
        "timestamp_ms": pl.Int64,
        "landmark_index": pl.Int32,
        "landmark_name": pl.Utf8,
        "x": pl.Float64,
        "y": pl.Float64,
        "z": pl.Float64,
        "visibility": pl.Float64,
        "presence": pl.Float64,
    }
    df = pl.DataFrame(rows, schema=schema) if rows else pl.DataFrame(schema=schema)

    return PoseExtractResult(
        keypoints=df,
        frame_count=frame_index,
        fps=fps,
        width=width,
        height=height,
    )
