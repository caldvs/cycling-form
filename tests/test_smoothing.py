"""Tests for One-Euro smoothing + visibility gating."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("polars")
pytest.importorskip("numpy")

import numpy as np
import polars as pl
from vision.smoothing import OneEuroFilter, smooth_keypoints


def test_oneeuro_passes_constant_signal_through() -> None:
    f = OneEuroFilter(min_cutoff_hz=1.0, beta=0.05)
    out = [f(t / 30.0, 0.5) for t in range(60)]
    assert all(abs(v - 0.5) < 1e-9 for v in out)


def test_oneeuro_attenuates_high_frequency_noise() -> None:
    rng = np.random.default_rng(seed=42)
    fps = 60.0
    n = 600
    t = np.arange(n) / fps
    signal = 0.5 + 0.05 * np.sin(2 * math.pi * 1.0 * t)  # 1 Hz sine
    noisy = signal + 0.03 * rng.standard_normal(n)  # high-freq white noise

    f = OneEuroFilter(min_cutoff_hz=1.0, beta=0.0)
    smoothed = np.array([f(ti, vi) for ti, vi in zip(t, noisy, strict=True)])

    # The MSE vs the clean signal must drop after smoothing.
    err_before = float(np.mean((noisy - signal) ** 2))
    err_after = float(np.mean((smoothed - signal) ** 2))
    assert err_after < err_before, f"smoother did not reduce error: {err_before} -> {err_after}"


def test_smooth_keypoints_gates_low_visibility() -> None:
    df = pl.DataFrame(
        {
            "ride_id": ["r"] * 4,
            "frame_index": [0, 1, 2, 3],
            "timestamp_ms": [0, 33, 66, 100],
            "landmark_index": [0, 0, 0, 0],
            "landmark_name": ["left_knee"] * 4,
            "x": [0.5, 0.51, 0.52, 0.53],
            "y": [0.5, 0.9, 0.52, 0.53],  # frame 1 = noisy outlier
            "z": [0.0, 0.0, 0.0, 0.0],
            "visibility": [0.9, 0.1, 0.9, 0.9],  # frame 1 = low visibility
            "presence": [0.9, 0.9, 0.9, 0.9],
        }
    )
    out = smooth_keypoints(df, visibility_threshold=0.5)
    # The outlier frame had its x/y/z NaN'd, so it must not contaminate the smoothed series.
    y_at_3 = out.filter(pl.col("frame_index") == 3)["y"].to_list()[0]
    assert abs(y_at_3 - 0.53) < 0.05
