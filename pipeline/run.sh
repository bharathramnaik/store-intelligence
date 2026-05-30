#!/usr/bin/env bash
set -euo pipefail

CLIPS_DIR="${CLIPS_DIR:-/data/clips}"
OUTPUT_DIR="${OUTPUT_DIR:-/data/events}"
STORE_LAYOUT="${STORE_LAYOUT_PATH:-/data/store_layout.json}"
WORKERS="${WORKERS:-2}"

echo "Starting detection pipeline..."
echo "Clips: $CLIPS_DIR"
echo "Output: $OUTPUT_DIR"
echo "Layout: $STORE_LAYOUT"

python -m pipeline.run \
    --clips-dir "$CLIPS_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --store-layout "$STORE_LAYOUT" \
    --workers "$WORKERS"

echo "Pipeline complete. Events written to $OUTPUT_DIR"
