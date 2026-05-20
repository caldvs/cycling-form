"""Typer entry point for the local pipeline.

Run via either:
    uv run vision pose-extract path/to/ride.mp4 --out keypoints.parquet
    python -m vision pose-extract path/to/ride.mp4 --out keypoints.parquet
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    help="Vision — local pose + telemetry pipeline (Phase 1 MVP).",
    no_args_is_help=True,
)


@app.command("pose-extract")
def pose_extract(
    video: Annotated[
        Path,
        typer.Argument(exists=True, readable=True, help="Input video file."),
    ],
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Output Parquet path for keypoints."),
    ] = Path("keypoints.parquet"),
    model: Annotated[
        Path | None,
        typer.Option(
            "--model",
            "-m",
            help="Path to a .task MediaPipe Pose Landmarker model. "
            "Downloads pose_landmarker_full.task to ./models/ if omitted.",
        ),
    ] = None,
    overlay: Annotated[
        Path | None,
        typer.Option("--overlay", help="If set, render an MP4 with the skeleton drawn."),
    ] = None,
    ride_id: Annotated[
        str,
        typer.Option("--ride-id", help="Tag every emitted row with this ride identifier."),
    ] = "unknown",
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="DEBUG logging.")] = False,
) -> None:
    """Extract pose keypoints from a video and write a flat Parquet table."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    from vision.pose import extract_pose

    typer.echo(f"Extracting pose from {video} ...")
    result = extract_pose(video, model_path=model, ride_id=ride_id)

    out.parent.mkdir(parents=True, exist_ok=True)
    result.keypoints.write_parquet(out)
    typer.echo(
        f"Wrote {len(result.keypoints)} rows "
        f"({result.frame_count} frames @ {result.fps:.2f} fps, "
        f"{result.width}x{result.height}) -> {out}"
    )

    if overlay is not None:
        from vision.overlay import render_overlay

        typer.echo(f"Rendering overlay -> {overlay} ...")
        render_overlay(video, result.keypoints, overlay)
        typer.echo(f"Wrote overlay -> {overlay}")


@app.command("version")
def version() -> None:
    """Print the installed package version."""
    from vision import __version__

    typer.echo(__version__)


def main() -> None:
    """Console-script entry point (`vision` command, wired in pyproject.toml)."""
    app()


if __name__ == "__main__":
    main()
