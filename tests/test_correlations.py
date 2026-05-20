"""Per-stroke fusion + Pearson correlation tests."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("polars")
pytest.importorskip("scipy")
pytest.importorskip("numpy")

import numpy as np
import polars as pl
from vision.correlations import (
    attach_per_stroke_angle_summary,
    correlate_metrics,
    per_stroke_telemetry,
)


def _make_strokes(n: int = 10) -> pl.DataFrame:
    rows = []
    t = 0
    for i in range(n):
        d = 1000
        rows.append(
            {
                "stroke_index": i,
                "frame_start": i * 30,
                "frame_end": (i + 1) * 30,
                "timestamp_start_ms": t,
                "timestamp_end_ms": t + d,
                "duration_ms": d,
                "cadence_rpm": 60.0 + i,  # 60..69
            }
        )
        t += d
    return pl.DataFrame(rows)


def test_per_stroke_telemetry_fuses_means() -> None:
    strokes = _make_strokes(n=5)
    telem = pl.DataFrame(
        {
            "timestamp_ms": [0, 500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500],
            "power_w": [100, 200, 150, 250, 175, 275, 200, 300, 225, 325],
            "cadence_rpm": [80.0] * 10,
            "speed_mps": [10.0] * 10,
            "heart_rate_bpm": [150.0] * 10,
            "distance_m": list(range(10)),
        }
    )
    out = per_stroke_telemetry(strokes, telem, offset_ms=0)
    assert out.height == 5
    assert "mean_power_w" in out.columns


def test_correlate_metrics_perfect_correlation_is_r_one() -> None:
    # Stroke cadence_rpm goes 60..69; we manufacture a duration_ms that's a
    # strict linear function of cadence_rpm — Pearson r should be ±1.
    strokes = _make_strokes(n=10)
    enriched = strokes.with_columns(
        (pl.col("cadence_rpm") * 2.0).alias("mean_power_w"),
    )
    r = correlate_metrics(enriched, metrics=("cadence_rpm", "mean_power_w"))
    assert r.height == 1
    assert abs(r["r"][0] - 1.0) < 1e-9
    assert r["n"][0] == 10


def test_attach_per_stroke_angle_summary() -> None:
    strokes = _make_strokes(n=2)
    angles = pl.DataFrame(
        {
            "frame_index": list(range(60)),
            "timestamp_ms": [i * 33 for i in range(60)],
            "left_knee_angle": list(np.linspace(80, 160, 60)),
            "right_knee_angle": [math.nan] * 60,
            "left_hip_angle": [math.nan] * 60,
            "right_hip_angle": [math.nan] * 60,
            "trunk_angle": [math.nan] * 60,
        }
    )
    out = attach_per_stroke_angle_summary(strokes, angles)
    assert "mean_knee_angle_min" in out.columns
    assert out["mean_knee_angle_min"][0] <= out["mean_knee_angle_max"][0]
