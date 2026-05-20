"""Pedal-stroke segmentation from a 1-D pose signal.

We use `scipy.signal.find_peaks` on a periodic signal (knee angle by default
because it has the cleanest TDC/BDC extrema; ankle y is the fallback). One
revolution = the interval between consecutive matched extrema.

Returns per-stroke metrics: indices, timestamps, duration, cadence (rpm).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

# Cadence is gated to a reasonable cycling band; anything outside is detected
# noise (e.g. high-frequency landmark jitter, or a stationary rider).
MIN_CADENCE_RPM = 30.0
MAX_CADENCE_RPM = 140.0


def _strokes_empty_schema() -> dict[str, type[pl.DataType] | pl.DataType]:
    import polars as pl

    return {
        "stroke_index": pl.Int64,
        "frame_start": pl.Int64,
        "frame_end": pl.Int64,
        "timestamp_start_ms": pl.Int64,
        "timestamp_end_ms": pl.Int64,
        "duration_ms": pl.Int64,
        "cadence_rpm": pl.Float64,
    }


def segment_strokes_from_signal(
    timestamps_ms: list[int] | tuple[int, ...],
    values: list[float] | tuple[float, ...],
    frame_indices: list[int] | tuple[int, ...],
    *,
    min_cadence_rpm: float = MIN_CADENCE_RPM,
    max_cadence_rpm: float = MAX_CADENCE_RPM,
) -> pl.DataFrame:
    """Find peaks on a 1-D `values` series and emit one stroke between consecutive peaks."""

    import numpy as np
    import polars as pl
    from scipy.signal import find_peaks  # type: ignore[import-untyped]

    if len(values) < 3:
        return pl.DataFrame(schema=_strokes_empty_schema())

    ts = np.asarray(timestamps_ms, dtype=float)
    vs = np.asarray(values, dtype=float)
    frames = np.asarray(frame_indices, dtype=int)

    # Replace NaNs with the column mean so find_peaks doesn't choke; the gating
    # below filters out implausible cadences anyway.
    if np.isnan(vs).any():
        mean = float(np.nanmean(vs)) if np.isfinite(np.nanmean(vs)) else 0.0
        vs = np.where(np.isnan(vs), mean, vs)

    diffs_ms = np.diff(ts)
    fps = 1000.0 / float(np.median(diffs_ms)) if diffs_ms.size and np.median(diffs_ms) > 0 else 30.0
    min_dist = max(1, int(round(fps * 60.0 / max_cadence_rpm)))

    peaks, _ = find_peaks(vs, distance=min_dist)
    if peaks.size < 2:
        return pl.DataFrame(schema=_strokes_empty_schema())

    rows: list[dict[str, object]] = []
    for i in range(len(peaks) - 1):
        a, b = int(peaks[i]), int(peaks[i + 1])
        duration_ms = int(ts[b] - ts[a])
        if duration_ms <= 0:
            continue
        cadence = 60000.0 / duration_ms
        if not (min_cadence_rpm <= cadence <= max_cadence_rpm):
            continue
        rows.append(
            {
                "stroke_index": len(rows),
                "frame_start": int(frames[a]),
                "frame_end": int(frames[b]),
                "timestamp_start_ms": int(ts[a]),
                "timestamp_end_ms": int(ts[b]),
                "duration_ms": duration_ms,
                "cadence_rpm": float(cadence),
            }
        )

    if not rows:
        return pl.DataFrame(schema=_strokes_empty_schema())
    return pl.DataFrame(rows, schema=_strokes_empty_schema())


def segment_strokes(
    angles: pl.DataFrame,
    *,
    signal_col: str = "left_knee_angle",
) -> pl.DataFrame:
    """Convenience: read the chosen signal column off a per-frame angle DataFrame."""
    import polars as pl

    if angles.is_empty() or signal_col not in angles.columns:
        return pl.DataFrame(schema=_strokes_empty_schema())

    sub = angles.sort("frame_index")
    return segment_strokes_from_signal(
        timestamps_ms=sub["timestamp_ms"].to_list(),
        values=sub[signal_col].to_list(),
        frame_indices=sub["frame_index"].to_list(),
    )
