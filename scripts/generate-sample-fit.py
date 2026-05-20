"""Generate a synthetic indoor-cycling FIT file for testing the pipeline.

Usage:
    uv run --with fit-tool python scripts/generate-sample-fit.py [--duration_s 60] [--out samples/sample-ride.fit]

The output FIT mimics what a Wahoo/Garmin head unit would record on an indoor
trainer: per-second records with realistic power, cadence, and heart-rate
curves, no GPS, sport=cycling/indoor_cycling.

`fit-tool` is intentionally NOT a project dependency — it is only required to
generate fixtures. Use `uv run --with` to bring it in for one invocation.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import math
import random
from pathlib import Path


def build_fit_bytes(duration_s: int, seed: int = 1234) -> bytes:
    """Build a synthetic indoor-ride FIT file and return its bytes."""
    from fit_tool.fit_file_builder import FitFileBuilder
    from fit_tool.profile.messages.file_id_message import FileIdMessage
    from fit_tool.profile.messages.record_message import RecordMessage
    from fit_tool.profile.messages.session_message import SessionMessage
    from fit_tool.profile.profile_type import (
        Event,
        EventType,
        FileType,
        Manufacturer,
        Sport,
        SubSport,
    )

    rng = random.Random(seed)
    start = _dt.datetime(2026, 5, 20, 9, 0, 0, tzinfo=_dt.UTC)

    builder = FitFileBuilder(auto_define=True, min_string_size=50)

    file_id = FileIdMessage()
    file_id.type = FileType.ACTIVITY
    file_id.manufacturer = Manufacturer.DEVELOPMENT.value
    file_id.product = 0
    file_id.time_created = round(start.timestamp() * 1000)
    file_id.serial_number = 0x12345678
    builder.add(file_id)

    cumulative_distance_m = 0.0
    speed_mps = 10.5

    for sec in range(duration_s):
        t = start + _dt.timedelta(seconds=sec)
        # Power: 150 W ramp to 220 W with small jitter
        ramp = 150.0 + (220.0 - 150.0) * (sec / max(1, duration_s - 1))
        # Add a deliberate cadence bump in the middle so alignment has signal.
        cad_base = 85.0 + 8.0 * math.sin(2 * math.pi * sec / 30.0)
        if 25 <= sec < 35:
            cad_base += 6.0
        cadence = cad_base + rng.uniform(-2.0, 2.0)
        power = ramp + rng.uniform(-15.0, 15.0)
        # Heart rate slow ramp.
        hr = 130.0 + (155.0 - 130.0) * (sec / max(1, duration_s - 1)) + rng.uniform(-2.0, 2.0)
        cumulative_distance_m += speed_mps

        rec = RecordMessage()
        rec.timestamp = round(t.timestamp() * 1000)
        rec.power = int(round(power))
        rec.cadence = int(round(cadence))
        rec.heart_rate = int(round(hr))
        rec.speed = speed_mps
        rec.distance = cumulative_distance_m
        builder.add(rec)

    session = SessionMessage()
    session.start_time = round(start.timestamp() * 1000)
    session.total_elapsed_time = float(duration_s)
    session.total_timer_time = float(duration_s)
    session.sport = Sport.CYCLING
    session.sub_sport = SubSport.INDOOR_CYCLING
    session.event = Event.SESSION
    session.event_type = EventType.STOP
    session.total_distance = cumulative_distance_m
    builder.add(session)

    return builder.build().to_bytes()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--duration_s", type=int, default=60)
    p.add_argument("--out", type=Path, default=Path("samples/sample-ride.fit"))
    args = p.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    data = build_fit_bytes(args.duration_s)
    args.out.write_bytes(data)
    print(f"Wrote {len(data)} bytes -> {args.out}")


if __name__ == "__main__":
    main()
