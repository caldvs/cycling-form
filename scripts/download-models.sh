#!/usr/bin/env bash
# Download the MediaPipe Pose Landmarker model into ./models/.
#
# The Python CLI auto-downloads on first run too, but this script is handy
# for offline-first setups and for verifying the model URL is reachable
# from the operator's network before kicking off a long batch.
#
# Variants (pass as first arg, default: full):
#   lite   — ~5.5 MB, fastest
#   full   — ~9 MB,   balanced (default)
#   heavy  — ~26 MB,  most accurate
set -euo pipefail

VARIANT="${1:-full}"
case "$VARIANT" in
  lite|full|heavy) ;;
  *) echo "usage: $0 [lite|full|heavy]" >&2; exit 2 ;;
esac

DEST_DIR="${MODELS_DIR:-models}"
mkdir -p "$DEST_DIR"

URL="https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_${VARIANT}/float16/latest/pose_landmarker_${VARIANT}.task"
DEST="$DEST_DIR/pose_landmarker_${VARIANT}.task"

if [[ -f "$DEST" ]]; then
  echo "$DEST already exists; skipping download."
  exit 0
fi

echo "Downloading $URL -> $DEST"
curl -fsSL --output "$DEST" "$URL"
echo "OK"
