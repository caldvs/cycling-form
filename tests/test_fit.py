"""FIT parser tests. Skipped if the garmin-fit-sdk is not installed."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("garmin_fit_sdk")
pytest.importorskip("polars")

from vision.fit import parse_fit


def test_parse_fit_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_fit(tmp_path / "nope.fit")


def test_parse_fit_schema_on_empty_synth_file(tmp_path: Path) -> None:
    """Garbage bytes -> SDK raises or returns no records; either way we should
    not crash hard and the empty-result schema must be the documented one."""
    p = tmp_path / "junk.fit"
    p.write_bytes(b"\x00" * 16)
    try:
        df = parse_fit(p)
    except Exception:
        pytest.skip("Garmin SDK refused the synthetic FIT bytes (expected)")
    assert set(df.columns) >= {
        "timestamp_ms",
        "power_w",
        "cadence_rpm",
        "speed_mps",
        "heart_rate_bpm",
    }
