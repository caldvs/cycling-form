"""Garmin FIT file parser → Polars DataFrame.

Uses Garmin's official `garmin-fit-sdk` (replaces the dormant `python-fitparse`
per CLAUDE.md). Returns a tidy record-level table indexed by `timestamp_ms`
since the start of the ride, so it can be joined to pose-derived strokes by
applying a single scalar offset.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl


def _empty_schema() -> dict[str, type[pl.DataType] | pl.DataType]:
    import polars as pl

    return {
        "timestamp_ms": pl.Int64,
        "power_w": pl.Float64,
        "cadence_rpm": pl.Float64,
        "speed_mps": pl.Float64,
        "heart_rate_bpm": pl.Float64,
        "distance_m": pl.Float64,
    }


def parse_fit(fit_path: Path) -> pl.DataFrame:
    """Parse a `.fit` file's record messages.

    Returns columns: timestamp_ms (elapsed since first record), power_w,
    cadence_rpm, speed_mps, heart_rate_bpm, distance_m. Missing fields are NaN.
    """
    import polars as pl
    from garmin_fit_sdk import Decoder, Stream  # type: ignore[import-untyped]

    if not fit_path.exists():
        raise FileNotFoundError(f"FIT file not found: {fit_path}")

    stream = Stream.from_file(str(fit_path))
    decoder = Decoder(stream)
    messages, _errors = decoder.read()

    records = messages.get("record_mesgs", [])
    if not records:
        return pl.DataFrame(schema=_empty_schema())

    timestamps = [r.get("timestamp") for r in records if r.get("timestamp") is not None]
    if not timestamps:
        return pl.DataFrame(schema=_empty_schema())
    start = min(timestamps)

    def _f(rec: dict[str, object], field: str) -> float:
        v = rec.get(field)
        return float(v) if v is not None else float("nan")  # type: ignore[arg-type]

    rows: list[dict[str, object]] = []
    for r in records:
        ts = r.get("timestamp")
        if ts is None:
            continue
        elapsed_ms = int((ts - start).total_seconds() * 1000)
        speed = _f(r, "speed") if r.get("speed") is not None else _f(r, "enhanced_speed")
        rows.append(
            {
                "timestamp_ms": elapsed_ms,
                "power_w": _f(r, "power"),
                "cadence_rpm": _f(r, "cadence"),
                "speed_mps": speed,
                "heart_rate_bpm": _f(r, "heart_rate"),
                "distance_m": _f(r, "distance"),
            }
        )

    return pl.DataFrame(rows, schema=_empty_schema()).sort("timestamp_ms")
