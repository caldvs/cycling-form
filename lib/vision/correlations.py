"""Per-stroke fusion (pose x telemetry) and Pearson correlations with CIs.

Given the stroke table (timestamps + cadence_rpm derived from pose) and the
FIT telemetry (per-record power/cadence/HR), we compute the mean of each
telemetry channel within every stroke window and emit a fused per-stroke
table. From that table we compute Pearson r, p, n, and the 95% Fisher-z CI
for every interesting pair of metrics — exactly the artifact PROJECT.md
needs to make defensible "X correlates with Y" statements.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

DEFAULT_METRICS: tuple[str, ...] = (
    "cadence_rpm",
    "duration_ms",
    "mean_power_w",
    "mean_cadence_fit_rpm",
    "mean_heart_rate_bpm",
    "mean_knee_angle_min",
    "mean_knee_angle_max",
)


def _safe_mean(window: pl.DataFrame, col: str) -> float:
    import numpy as np

    if not window.height:
        return math.nan
    return float(np.nanmean(window[col].to_numpy()))


def per_stroke_telemetry(
    strokes: pl.DataFrame,
    telemetry: pl.DataFrame,
    *,
    offset_ms: int = 0,
) -> pl.DataFrame:
    """Add `mean_power_w`, `mean_cadence_fit_rpm`, `mean_heart_rate_bpm` columns
    by averaging telemetry within each stroke's [start, end] window (after
    applying `offset_ms` to telemetry timestamps to align clocks).
    """
    import polars as pl

    if strokes.is_empty():
        return strokes

    telem = telemetry
    if not telem.is_empty():
        telem = telem.with_columns(
            (pl.col("timestamp_ms") + offset_ms).alias("aligned_ms")
        )

    out_rows = []
    for s in strokes.iter_rows(named=True):
        t_start = int(s["timestamp_start_ms"])
        t_end = int(s["timestamp_end_ms"])
        row = dict(s)
        if telem.is_empty():
            row.update(
                mean_power_w=math.nan,
                mean_cadence_fit_rpm=math.nan,
                mean_heart_rate_bpm=math.nan,
            )
        else:
            window = telem.filter(
                (pl.col("aligned_ms") >= t_start) & (pl.col("aligned_ms") <= t_end)
            )
            row["mean_power_w"] = _safe_mean(window, "power_w")
            row["mean_cadence_fit_rpm"] = _safe_mean(window, "cadence_rpm")
            row["mean_heart_rate_bpm"] = _safe_mean(window, "heart_rate_bpm")
        out_rows.append(row)

    return pl.DataFrame(out_rows)


def attach_per_stroke_angle_summary(
    strokes: pl.DataFrame, angles: pl.DataFrame
) -> pl.DataFrame:
    """For each stroke, take the min and max of left_knee_angle within the
    stroke's frame window. Yields `mean_knee_angle_min` / `_max` columns.
    """
    import numpy as np
    import polars as pl

    if strokes.is_empty():
        return strokes

    if angles.is_empty() or "left_knee_angle" not in angles.columns:
        return strokes.with_columns(
            [
                pl.lit(math.nan).alias("mean_knee_angle_min"),
                pl.lit(math.nan).alias("mean_knee_angle_max"),
            ]
        )

    rows = []
    for s in strokes.iter_rows(named=True):
        f0 = int(s["frame_start"])
        f1 = int(s["frame_end"])
        window = angles.filter(
            (pl.col("frame_index") >= f0) & (pl.col("frame_index") <= f1)
        )
        knee = window["left_knee_angle"].to_numpy() if window.height else np.array([])
        row = dict(s)
        row["mean_knee_angle_min"] = float(np.nanmin(knee)) if knee.size else math.nan
        row["mean_knee_angle_max"] = float(np.nanmax(knee)) if knee.size else math.nan
        rows.append(row)
    return pl.DataFrame(rows)


def correlate_metrics(
    per_stroke: pl.DataFrame,
    metrics: tuple[str, ...] = DEFAULT_METRICS,
) -> pl.DataFrame:
    """Pearson r + p + 95% CI (Fisher-z) for every pair of named metrics that
    exists in `per_stroke`. Sorted ascending by p-value.
    """
    import numpy as np
    import polars as pl
    from scipy import stats  # type: ignore[import-untyped]

    present = [m for m in metrics if m in per_stroke.columns]
    rows = []
    for i, a in enumerate(present):
        for b in present[i + 1 :]:
            sub = per_stroke.select([a, b]).drop_nulls()
            xs = sub[a].to_numpy()
            ys = sub[b].to_numpy()
            # Drop NaNs that polars left in (since drop_nulls only catches null, not NaN floats).
            mask = ~(np.isnan(xs) | np.isnan(ys))
            xs = xs[mask]
            ys = ys[mask]
            n = int(xs.size)
            if n < 3 or xs.std() < 1e-9 or ys.std() < 1e-9:
                continue
            r, p = stats.pearsonr(xs, ys)
            z = math.atanh(max(-0.999999, min(0.999999, float(r))))
            se = 1.0 / math.sqrt(n - 3) if n > 3 else math.nan
            r_lo = math.tanh(z - 1.96 * se) if not math.isnan(se) else math.nan
            r_hi = math.tanh(z + 1.96 * se) if not math.isnan(se) else math.nan
            rows.append(
                {
                    "metric_a": a,
                    "metric_b": b,
                    "n": n,
                    "r": float(r),
                    "p_value": float(p),
                    "ci_low": float(r_lo),
                    "ci_high": float(r_hi),
                }
            )
    if not rows:
        return pl.DataFrame(
            schema={
                "metric_a": pl.Utf8,
                "metric_b": pl.Utf8,
                "n": pl.Int64,
                "r": pl.Float64,
                "p_value": pl.Float64,
                "ci_low": pl.Float64,
                "ci_high": pl.Float64,
            }
        )
    return pl.DataFrame(rows).sort("p_value")
