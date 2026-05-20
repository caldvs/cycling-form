"""Time alignment between pose-derived strokes and FIT telemetry.

Pose-stroke cadence and FIT cadence are two noisy 1-D signals of the same
underlying physical phenomenon. We resample both onto a uniform 1-second grid,
mark gaps as NaN, and at each candidate lag compute Pearson correlation over
the overlapping valid region. The lag maximizing Pearson is the offset in ms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

DEFAULT_SEARCH_RANGE_S = 60


def _resample_pose_cadence_nan(
    strokes: pl.DataFrame, grid_ms: list[int]
) -> list[float]:
    """Per-grid-point cadence taken from the covering stroke; NaN outside strokes."""
    import math

    out = [math.nan] * len(grid_ms)
    for s in strokes.iter_rows(named=True):
        start = int(s["timestamp_start_ms"])
        end = int(s["timestamp_end_ms"])
        cad = float(s["cadence_rpm"])
        for i, t in enumerate(grid_ms):
            if start <= t <= end:
                out[i] = cad
    return out


def estimate_offset_ms(
    strokes: pl.DataFrame,
    telemetry: pl.DataFrame,
    *,
    search_range_s: int = DEFAULT_SEARCH_RANGE_S,
) -> tuple[int, float]:
    """Estimate the offset to apply to telemetry timestamps for best alignment.

    Returns (offset_ms, score). `score` is the peak Pearson r over the
    overlapping valid samples; ~0.5+ is usable, near 0 means alignment failed
    (e.g. constant cadence on one side).
    """
    import numpy as np

    if strokes.is_empty() or telemetry.is_empty():
        return 0, 0.0
    if "cadence_rpm" not in telemetry.columns:
        return 0, 0.0

    def _as_int(v: object) -> int:
        return int(v) if v is not None else 0  # type: ignore[call-overload]

    t_pose_max = _as_int(strokes["timestamp_end_ms"].max())
    t_fit_min = _as_int(telemetry["timestamp_ms"].min())
    t_fit_max = _as_int(telemetry["timestamp_ms"].max())
    t_max = max(t_pose_max, t_fit_max)
    if t_max <= 0:
        return 0, 0.0

    grid_ms = list(range(0, t_max + 1, 1000))
    pose_cad = np.asarray(_resample_pose_cadence_nan(strokes, grid_ms), dtype=float)

    fit_ts = telemetry["timestamp_ms"].to_numpy().astype(float)
    fit_cad_raw = telemetry["cadence_rpm"].fill_null(np.nan).to_numpy().astype(float)
    grid_np = np.asarray(grid_ms, dtype=float)
    fit_cad = np.interp(grid_np, fit_ts, fit_cad_raw, left=np.nan, right=np.nan)
    # Beyond either end of fit_ts is NaN so it doesn't pollute correlation.
    fit_cad = np.where((grid_np < t_fit_min) | (grid_np > t_fit_max), np.nan, fit_cad)

    n = len(grid_ms)
    max_lag = int(search_range_s)
    best_score = -2.0
    best_lag = 0

    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            if lag >= n:
                continue
            p_slice = pose_cad[lag:]
            f_slice = fit_cad[: n - lag]
        else:
            k = -lag
            if k >= n:
                continue
            p_slice = pose_cad[:-k]
            f_slice = fit_cad[k:]

        valid = ~(np.isnan(p_slice) | np.isnan(f_slice))
        if valid.sum() < 5:
            continue
        pv = p_slice[valid]
        fv = f_slice[valid]
        if pv.std() < 1e-6 or fv.std() < 1e-6:
            continue
        r = float(np.corrcoef(pv, fv)[0, 1])
        if r > best_score:
            best_score = r
            best_lag = lag

    if best_score <= -1.5:  # nothing scored
        return 0, 0.0
    return best_lag * 1000, best_score
