# Store Intelligence API

End-to-end store analytics pipeline from raw CCTV footage to live REST API and dashboard.

## Quick Start (5 Commands)

```bash
# 1. Clone repository
git clone <repo-url> && cd store-intelligence

# 2. Copy environment config
cp .env.example .env

# 3. Start all services
docker compose up -d

# 4. Verify tests
docker compose exec api pytest

# 5. Ingest sample events
docker compose exec api python -m scripts.ingest_events
```

## Architecture

```
Raw CCTV Clips
    ↓
Detection Pipeline (YOLOv8n + ByteTrack)
    ↓
JSONL Event Stream
    ↓
POST /events/ingest  →  PostgreSQL + Redis
    ↓
GET /stores/{id}/metrics      → Real-time KPIs
GET /stores/{id}/funnel       → Conversion funnel
GET /stores/{id}/heatmap      → Zone frequency
GET /stores/{id}/anomalies    → Operational alerts
GET /health                   → Feed staleness
    ↓
Streamlit Dashboard (localhost:8501)
```

## End-to-End Pipeline: CCTV → API

### Step 1: Run detection on CCTV clips
Place clips in `./data/clips/` and ensure `./data/store_layout.json` exists.

```bash
docker compose exec api python -m pipeline.run \
    --clips-dir /data/clips \
    --output-dir /data/events \
    --store-layout /data/store_layout.json \
    --workers 2
```

Events are written to `/data/events/*.jsonl`.

### Step 2: Ingest events into the API

```bash
docker compose exec api python -m scripts.ingest_events --events-dir /data/events
```

### Step 3: Ingest POS transactions & correlate

```bash
docker compose cp data/pos_transactions.csv api:/data/pos_transactions.csv
docker compose exec api python /app/ingest_pos.py
```

The correlation background task runs every 60 seconds and matches billing-zone visitors to transactions within a 5-minute window.

### Step 4: Cross-camera deduplication

The entry camera (CAM_ENTRY_01) and floor cameras (CAM_FLOOR_01, CAM_FLOOR_02) have overlapping fields of view. Without deduplication, a single person walking between zones gets multiple `visitor_id`s, inflating visitor counts.

```bash
docker compose exec api python /app/merge_duplicates.py
```

This merges sessions from overlapping cameras with time-overlapping windows (>5s), keeping the earliest session as canonical. Deployed as a post-ingestion step.

### One-command runner

```bash
bash pipeline/run.sh
```

This processes all clips, ingests events, loads POS transactions, and runs deduplication.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /events/ingest` | Ingest up to 500 events per batch. Idempotent. |
| `GET /stores/{id}/metrics` | Today: visitors, conversion, dwell, queue, abandonment. |
| `GET /stores/{id}/funnel` | Entry → Zone → Billing → Purchase with drop-off %. |
| `GET /stores/{id}/heatmap` | Zone visit frequency + avg dwell, normalized 0–100. |
| `GET /stores/{id}/anomalies` | Active anomalies with severity + suggested action. |
| `GET /health` | Service status + per-store feed staleness. |

## Dashboard

### Option 1: React Elite Dashboard (Recommended)
Open http://localhost:3000 after `docker compose up`.

Features:
- Glassmorphism UI with dark theme
- Animated metric cards with live pulse indicators
- Interactive funnel visualization with drop-off tracking
- Zone heatmap with confidence badges
- Real-time anomaly alerts with severity gradients
- System health monitoring with feed staleness detection
- Auto-refreshing charts with smooth animations
- Responsive sidebar navigation

### Option 2: Streamlit Dashboard (Fallback)
Open http://localhost:8501 after `docker compose up`.


## Testing

```bash
docker compose exec api pytest --cov=app --cov=pipeline --cov-report=term-missing
```

Target coverage: >70%.

## Project Structure

```
store-intelligence/
├── app/              # FastAPI application
├── pipeline/         # YOLOv8 + ByteTrack detection
├── dashboard/        # Streamlit live dashboard
├── tests/            # pytest suite
├── docs/             # DESIGN.md + CHOICES.md
└── docker-compose.yml
```

## License
Challenge use only.
