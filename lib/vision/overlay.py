"""Render a pose-overlay MP4 alongside the source video for visual verification.

This is intentionally simple — the goal is "did the tracker lock onto the rider"
not pixel-perfect skeleton art. Phase 5's Streamlit viewer is where the polished
annotated frame strip lives (VIEW-02). Here we just want the operator to be
able to play the file and confirm sensible keypoints.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

# Pairs of (landmark_name, landmark_name) drawn as line segments. Restricted to
# the lower body + torso because that is the region cycling form analysis cares
# about and a sparse skeleton is more legible than the full 33-point mesh.
SKELETON_EDGES: tuple[tuple[str, str], ...] = (
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("right_hip", "right_knee"),
    ("left_knee", "left_ankle"),
    ("right_knee", "right_ankle"),
    ("left_ankle", "left_heel"),
    ("right_ankle", "right_heel"),
    ("left_heel", "left_foot_index"),
    ("right_heel", "right_foot_index"),
)


def render_overlay(
    video_path: Path,
    keypoints: pl.DataFrame,
    out_path: Path,
    *,
    visibility_threshold: float = 0.5,
) -> Path:
    """Read `video_path`, draw keypoints+edges from `keypoints`, write `out_path`."""
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter.fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    by_frame: dict[int, dict[str, tuple[float, float, float]]] = {}
    for row in keypoints.iter_rows(named=True):
        frame_idx = int(row["frame_index"])
        by_frame.setdefault(frame_idx, {})[str(row["landmark_name"])] = (
            float(row["x"]),
            float(row["y"]),
            float(row["visibility"]),
        )

    frame_index = 0
    try:
        while True:
            ok, image = cap.read()
            if not ok:
                break
            pts = by_frame.get(frame_index, {})

            for a_name, b_name in SKELETON_EDGES:
                a = pts.get(a_name)
                b = pts.get(b_name)
                if (
                    a is not None
                    and b is not None
                    and a[2] >= visibility_threshold
                    and b[2] >= visibility_threshold
                ):
                    pt_a = (int(a[0] * width), int(a[1] * height))
                    pt_b = (int(b[0] * width), int(b[1] * height))
                    cv2.line(image, pt_a, pt_b, (0, 255, 0), 2)

            for _name, (x, y, vis) in pts.items():
                if vis >= visibility_threshold:
                    cv2.circle(image, (int(x * width), int(y * height)), 4, (0, 0, 255), -1)

            writer.write(image)
            frame_index += 1
    finally:
        cap.release()
        writer.release()

    return out_path
