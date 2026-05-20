"""Joint-angle tests on known triangles."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("polars")

import polars as pl
from vision.angles import angle_at, compute_angles, trunk_angle_from_vertical


def test_angle_at_right_angle() -> None:
    a = (1.0, 0.0)
    b = (0.0, 0.0)
    c = (0.0, 1.0)
    assert abs(angle_at(a, b, c) - 90.0) < 1e-6


def test_angle_at_straight_line() -> None:
    a = (-1.0, 0.0)
    b = (0.0, 0.0)
    c = (1.0, 0.0)
    assert abs(angle_at(a, b, c) - 180.0) < 1e-6


def test_angle_propagates_nan() -> None:
    a = (math.nan, 0.0)
    b = (0.0, 0.0)
    c = (1.0, 0.0)
    assert math.isnan(angle_at(a, b, c))


def test_trunk_angle_vertical() -> None:
    # Shoulder above hip → trunk is vertical → angle 0°.
    assert abs(trunk_angle_from_vertical((0.5, 0.2), (0.5, 0.6))) < 1e-6
    # Shoulder leaning forward (+x) by 1, up by 1 → 45°.
    assert abs(trunk_angle_from_vertical((1.0, 0.0), (0.0, 1.0)) - 45.0) < 1e-6


def test_compute_angles_one_frame() -> None:
    # A trivial "stick figure" with a 90° knee.
    df = pl.DataFrame(
        {
            "ride_id": ["r"] * 4,
            "frame_index": [0, 0, 0, 0],
            "timestamp_ms": [0, 0, 0, 0],
            "landmark_index": [23, 25, 27, 11],
            "landmark_name": ["left_hip", "left_knee", "left_ankle", "left_shoulder"],
            "x": [0.5, 0.5, 0.6, 0.5],  # hip directly above knee; ankle to the right
            "y": [0.5, 0.6, 0.6, 0.3],
            "z": [0.0, 0.0, 0.0, 0.0],
            "visibility": [0.9, 0.9, 0.9, 0.9],
            "presence": [0.9, 0.9, 0.9, 0.9],
        }
    )
    out = compute_angles(df)
    assert out.height == 1
    assert abs(out["left_knee_angle"][0] - 90.0) < 1e-6
