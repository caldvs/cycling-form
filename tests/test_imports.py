"""Smoke test: prove the toolchain and shared `vision` namespace are wired up.

This is the gatekeeper test for Phase 0 BOOT-01. It fails loudly if:
- Python is not 3.12.x (later phases assume MediaPipe wheels, which are 3.12-only).
- The `vision` package under `lib/vision/` is not importable from the test env.
"""

from __future__ import annotations

import sys

import vision


def test_python_is_312() -> None:
    """Phase 0 pins Python to 3.12 because MediaPipe (Phase 2+) has no 3.13 wheels."""
    assert sys.version_info[:2] == (3, 12), (
        f"Expected Python 3.12.x, got {sys.version_info[:3]}. "
        "Re-create the venv with `uv sync` (pyproject.toml pins 3.12)."
    )


def test_vision_importable() -> None:
    """The shared `vision` namespace package must be importable and version-tagged."""
    assert vision.__version__ == "0.1.0"
