"""Time-alignment tests on synthetic stroke / telemetry signals."""

from __future__ import annotations

import pytest

pytest.importorskip("polars")
pytest.importorskip("numpy")

import numpy as np
import polars as pl
from vision.align import estimate_offset_ms


def _make_aligned_signals(
    n_seconds: int = 60,
    offset_ms: int = 5000,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Build a strokes table and a telemetry table whose cadence series share a
    common ramp 60→100 rpm; the telemetry timestamps are shifted by `-offset_ms`
    so the alignment algorithm must recover `+offset_ms` to align them.
    """
    # Strokes: ramp cadence from 60 to 100 rpm across n_seconds.
    cadence_ramp = np.linspace(60.0, 100.0, n_seconds)
    rows = []
    t = 0
    for i, c in enumerate(cadence_ramp):
        d = int(60000.0 / c)
        rows.append(
            {
                "stroke_index": i,
                "frame_start": i,
                "frame_end": i + 1,
                "timestamp_start_ms": t,
                "timestamp_end_ms": t + d,
                "duration_ms": d,
                "cadence_rpm": float(c),
            }
        )
        t += d
    strokes = pl.DataFrame(rows)

    # Telemetry: same per-second cadence at the same wall-clock time, but with
    # the offset baked into its timestamps (telemetry clock runs ahead by offset).
    telem_rows = []
    for sec in range(n_seconds):
        c = float(np.interp(sec * 1000, [r["timestamp_start_ms"] for r in rows], cadence_ramp))
        telem_rows.append(
            {
                "timestamp_ms": sec * 1000 - offset_ms,
                "power_w": 200.0,
                "cadence_rpm": c,
                "speed_mps": 10.0,
                "heart_rate_bpm": 150.0,
                "distance_m": 0.0,
            }
        )
    telemetry = pl.DataFrame(telem_rows)
    return strokes, telemetry


def test_recover_injected_offset_5_seconds() -> None:
    strokes, telemetry = _make_aligned_signals(n_seconds=60, offset_ms=5000)
    offset_ms, score = estimate_offset_ms(strokes, telemetry, search_range_s=30)
    assert abs(offset_ms - 5000) <= 2000, f"recovered {offset_ms} ms (score={score:.2f})"
    assert score > 0.5


def test_recover_zero_offset_when_aligned() -> None:
    strokes, telemetry = _make_aligned_signals(n_seconds=60, offset_ms=0)
    offset_ms, score = estimate_offset_ms(strokes, telemetry, search_range_s=30)
    assert abs(offset_ms) <= 2000
    assert score > 0.5


def test_returns_zero_on_empty_inputs() -> None:
    empty = pl.DataFrame()
    assert estimate_offset_ms(empty, empty) == (0, 0.0)
