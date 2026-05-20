"""One-Euro filter (Casiez et al. 2012) + visibility gating for pose keypoints.

The One-Euro filter is a low-pass on x with an adaptive cutoff that depends on
|dx/dt| via a coefficient β. At rest it removes jitter; during fast motion the
cutoff rises and lag drops — which is exactly what pose smoothing wants on a
pedalling rider whose feet move fast at the bottom of a stroke and slow at top.

Reference: https://gery.casiez.net/1euro/
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl


def _alpha(cutoff_hz: float, dt_s: float) -> float:
    tau = 1.0 / (2.0 * math.pi * cutoff_hz)
    return 1.0 / (1.0 + tau / dt_s)


@dataclass
class OneEuroFilter:
    """Stateful 1-D One-Euro filter. Construct one per channel.

    Parameters:
        min_cutoff_hz: cutoff at zero speed (lower = more smoothing at rest).
        beta:          speed coefficient (higher = less lag during fast motion).
        d_cutoff_hz:   cutoff of the derivative low-pass (rarely tweaked).
    """

    min_cutoff_hz: float = 1.0
    beta: float = 0.05
    d_cutoff_hz: float = 1.0
    _x_prev: float = field(default=math.nan, init=False, repr=False)
    _dx_prev: float = field(default=0.0, init=False, repr=False)
    _t_prev: float = field(default=math.nan, init=False, repr=False)

    def __call__(self, t_s: float, x: float) -> float:
        if math.isnan(self._t_prev) or math.isnan(self._x_prev):
            self._t_prev = t_s
            self._x_prev = x
            self._dx_prev = 0.0
            return x

        dt = t_s - self._t_prev
        if dt <= 0:
            return self._x_prev

        dx_raw = (x - self._x_prev) / dt
        alpha_d = _alpha(self.d_cutoff_hz, dt)
        dx_hat = alpha_d * dx_raw + (1.0 - alpha_d) * self._dx_prev

        cutoff = self.min_cutoff_hz + self.beta * abs(dx_hat)
        alpha = _alpha(cutoff, dt)
        x_hat = alpha * x + (1.0 - alpha) * self._x_prev

        self._x_prev = x_hat
        self._dx_prev = dx_hat
        self._t_prev = t_s
        return x_hat


def smooth_keypoints(
    df: pl.DataFrame,
    *,
    min_cutoff_hz: float = 1.0,
    beta: float = 0.05,
    visibility_threshold: float = 0.0,
) -> pl.DataFrame:
    """Apply One-Euro smoothing to x/y/z per landmark; low-visibility rows are
    NaN'd before filtering so noisy detections don't drag the smoothed trace.

    Default `visibility_threshold=0.0` disables gating — MediaPipe's visibility
    score drops below 0.5 during normal cycling motion (motion blur, far-side
    occlusion by the frame), and aggressive gating leaves the angle chart
    mostly empty. The One-Euro filter alone handles in-band noise; gating
    is opt-in for callers that want a stricter trace.

    Returns a new DataFrame with the same schema; visibility is preserved as the
    *raw* score so downstream gating still has it available.
    """
    import math as _math

    import polars as pl

    if df.is_empty():
        return df

    # Cast x/y/z to float so we can stamp NaN where visibility is too low.
    gated = df.with_columns(
        [
            pl.when(pl.col("visibility") >= visibility_threshold)
            .then(pl.col(c))
            .otherwise(float("nan"))
            .alias(c)
            for c in ("x", "y", "z")
        ]
    )

    out_rows: list[dict[str, object]] = []
    # One filter triple (x, y, z) per landmark, persistent across frames for that landmark.
    filters: dict[str, tuple[OneEuroFilter, OneEuroFilter, OneEuroFilter]] = {}

    for row in gated.sort(["landmark_name", "frame_index"]).iter_rows(named=True):
        lm = str(row["landmark_name"])
        if lm not in filters:
            filters[lm] = (
                OneEuroFilter(min_cutoff_hz, beta),
                OneEuroFilter(min_cutoff_hz, beta),
                OneEuroFilter(min_cutoff_hz, beta),
            )
        fx, fy, fz = filters[lm]
        t_s = float(row["timestamp_ms"]) / 1000.0

        smoothed: dict[str, float] = {}
        for axis, filt in (("x", fx), ("y", fy), ("z", fz)):
            v = float(row[axis])
            smoothed[axis] = v if _math.isnan(v) else filt(t_s, v)

        out_rows.append(
            {
                "ride_id": row["ride_id"],
                "frame_index": row["frame_index"],
                "timestamp_ms": row["timestamp_ms"],
                "landmark_index": row["landmark_index"],
                "landmark_name": lm,
                "x": smoothed["x"],
                "y": smoothed["y"],
                "z": smoothed["z"],
                "visibility": row["visibility"],
                "presence": row["presence"],
            }
        )

    return pl.DataFrame(out_rows, schema=df.schema).sort(["frame_index", "landmark_index"])
