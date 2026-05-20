"""Joint angle computation from 2D pose keypoints.

The clinically-meaningful biomechanical signal from a single side-on camera is
the *joint angle* at hip / knee, not the raw landmark coordinate. We compute
angles in degrees with the joint as vertex.

Schema returned: one row per frame.
    frame_index, timestamp_ms,
    left_knee_angle, right_knee_angle,
    left_hip_angle,  right_hip_angle,
    trunk_angle  (shoulder-mid → hip-mid, measured from vertical)
Missing landmarks (NaN x/y from visibility gating) propagate to NaN angles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl


def angle_at(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    """Return the interior angle at vertex `b`, in degrees, formed by rays b→a and b→c."""
    import math

    if any(math.isnan(v) for v in (*a, *b, *c)):
        return math.nan
    ax, ay = a
    bx, by = b
    cx, cy = c
    v1 = (ax - bx, ay - by)
    v2 = (cx - bx, cy - by)
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    n1 = math.hypot(*v1)
    n2 = math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return math.nan
    cos = max(-1.0, min(1.0, dot / (n1 * n2)))
    return math.degrees(math.acos(cos))


def trunk_angle_from_vertical(
    shoulder_mid: tuple[float, float], hip_mid: tuple[float, float]
) -> float:
    """Angle of the trunk axis from vertical, signed: leans forward = +, back = -."""
    import math

    if any(math.isnan(v) for v in (*shoulder_mid, *hip_mid)):
        return math.nan
    dx = shoulder_mid[0] - hip_mid[0]
    dy = shoulder_mid[1] - hip_mid[1]
    # In image coords y grows downward, so the trunk axis pointing UP has dy < 0.
    # Angle measured from the upward vertical (0, -1).
    return math.degrees(math.atan2(dx, -dy))


def compute_angles(keypoints: pl.DataFrame) -> pl.DataFrame:
    """Pivot keypoints into one row per frame and emit joint angles."""
    import math as _math

    import polars as pl

    if keypoints.is_empty():
        return pl.DataFrame(
            schema={
                "frame_index": pl.Int64,
                "timestamp_ms": pl.Int64,
                "left_knee_angle": pl.Float64,
                "right_knee_angle": pl.Float64,
                "left_hip_angle": pl.Float64,
                "right_hip_angle": pl.Float64,
                "left_elbow_angle": pl.Float64,
                "right_elbow_angle": pl.Float64,
                "left_shoulder_angle": pl.Float64,
                "right_shoulder_angle": pl.Float64,
                "left_ankle_angle": pl.Float64,
                "right_ankle_angle": pl.Float64,
                "trunk_angle": pl.Float64,
            }
        )

    def _mid(p: tuple[float, float], q: tuple[float, float]) -> tuple[float, float]:
        return ((p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0)

    def _angles_for_frame(
        frame_idx: int, ts_ms: int, pts: dict[str, tuple[float, float]]
    ) -> dict[str, object]:
        nan_pt = (_math.nan, _math.nan)

        def get(n: str) -> tuple[float, float]:
            return pts.get(n, nan_pt)

        return {
            "frame_index": frame_idx,
            "timestamp_ms": ts_ms,
            "left_knee_angle": angle_at(get("left_hip"), get("left_knee"), get("left_ankle")),
            "right_knee_angle": angle_at(
                get("right_hip"), get("right_knee"), get("right_ankle")
            ),
            "left_hip_angle": angle_at(
                get("left_shoulder"), get("left_hip"), get("left_knee")
            ),
            "right_hip_angle": angle_at(
                get("right_shoulder"), get("right_hip"), get("right_knee")
            ),
            "left_elbow_angle": angle_at(
                get("left_shoulder"), get("left_elbow"), get("left_wrist")
            ),
            "right_elbow_angle": angle_at(
                get("right_shoulder"), get("right_elbow"), get("right_wrist")
            ),
            "left_shoulder_angle": angle_at(
                get("left_elbow"), get("left_shoulder"), get("left_hip")
            ),
            "right_shoulder_angle": angle_at(
                get("right_elbow"), get("right_shoulder"), get("right_hip")
            ),
            "left_ankle_angle": angle_at(
                get("left_knee"), get("left_ankle"), get("left_foot_index")
            ),
            "right_ankle_angle": angle_at(
                get("right_knee"), get("right_ankle"), get("right_foot_index")
            ),
            "trunk_angle": trunk_angle_from_vertical(
                _mid(get("left_shoulder"), get("right_shoulder")),
                _mid(get("left_hip"), get("right_hip")),
            ),
        }

    out: list[dict[str, object]] = []
    for (frame_idx,), group in keypoints.group_by(["frame_index"], maintain_order=True):
        pts: dict[str, tuple[float, float]] = {}
        ts_ms = 0
        for r in group.iter_rows(named=True):
            pts[str(r["landmark_name"])] = (float(r["x"]), float(r["y"]))
            ts_ms = int(r["timestamp_ms"])
        out.append(_angles_for_frame(int(frame_idx), ts_ms, pts))

    return pl.DataFrame(out).sort("frame_index")
