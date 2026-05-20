"""Stroke segmentation against a known-period synthetic signal."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("scipy")
pytest.importorskip("polars")
pytest.importorskip("numpy")

import numpy as np
import polars as pl
from vision.strokes import segment_strokes, segment_strokes_from_signal


def test_segment_detects_expected_stroke_count() -> None:
    # Simulate 10 seconds at 30 fps of an 80 rpm pedal stroke.
    fps = 30.0
    seconds = 10.0
    cadence_rpm = 80.0
    n = int(fps * seconds)
    t_s = np.arange(n) / fps
    omega = 2 * math.pi * cadence_rpm / 60.0
    signal = np.sin(omega * t_s)  # one cycle = one stroke

    out = segment_strokes_from_signal(
        timestamps_ms=(t_s * 1000).astype(int).tolist(),
        values=signal.tolist(),
        frame_indices=list(range(n)),
    )
    # 10 s * 80 rpm / 60 = 13.33 → expect ~12-13 detected strokes.
    assert 11 <= out.height <= 14
    median_cadence = float(np.median(out["cadence_rpm"].to_numpy()))
    assert abs(median_cadence - cadence_rpm) < 2.0


def test_segment_strokes_from_angles_df() -> None:
    fps = 30.0
    n = 90
    t_s = np.arange(n) / fps
    omega = 2 * math.pi * 1.0
    angles = pl.DataFrame(
        {
            "frame_index": list(range(n)),
            "timestamp_ms": (t_s * 1000).astype(int).tolist(),
            "left_knee_angle": np.sin(omega * t_s).tolist(),
            "right_knee_angle": np.sin(omega * t_s).tolist(),
            "left_hip_angle": [0.0] * n,
            "right_hip_angle": [0.0] * n,
            "trunk_angle": [0.0] * n,
        }
    )
    out = segment_strokes(angles, signal_col="left_knee_angle")
    assert out.height >= 1
    # 1 Hz signal = 60 rpm.
    assert abs(float(out["cadence_rpm"][0]) - 60.0) < 2.0


def test_segment_returns_empty_on_short_input() -> None:
    out = segment_strokes_from_signal([0, 33], [0.0, 1.0], [0, 1])
    assert out.is_empty()
