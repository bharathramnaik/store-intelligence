#!/bin/bash
set -euo pipefail

# Store Intelligence — One-command Pipeline Runner
# Usage:  bash pipeline/run.sh
# Prerequisites: docker compose up -d  (API, DB, Redis must be running)

CLIPS_DIR="${CLIPS_DIR:-data/clips}"
OUTPUT_DIR="${OUTPUT_DIR:-data/events}"
STORE_LAYOUT="${STORE_LAYOUT:-data/store_layout.json}"
POS_CSV="${POS_CSV:-data/pos_transactions.csv}"
API_URL="${API_URL:-http://localhost:8000}"
WORKERS="${WORKERS:-2}"

echo "=== Step 1: Detection Pipeline ==="
python -m pipeline.run \
    --clips-dir "$CLIPS_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --store-layout "$STORE_LAYOUT" \
    --workers "$WORKERS"

echo ""
echo "=== Step 2: Ingest Events into API ==="
python scripts/ingest_events.py \
    --events-dir "$OUTPUT_DIR" \
    --api-url "$API_URL"

echo ""
echo "=== Step 3: Ingest POS Transactions ==="
if [ -f "$POS_CSV" ]; then
    docker compose exec -T api python /app/ingest_pos.py
    echo "POS transactions ingested via API container."
else
    echo "No POS CSV found at $POS_CSV — skipping."
fi

echo ""
echo "=== Step 4: Cross-Camera Deduplication ==="
docker compose exec -T api python /app/merge_duplicates.py

echo ""
echo "=== Done ==="
echo "API:       $API_URL"
echo "Dashboard: http://localhost:8501"
echo "Frontend:  http://localhost:3000"
