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

# 5. Run detection pipeline on clips
python -m pipeline.run --clips-dir ./data/clips --output-dir ./data/events --store-layout ./data/store_layout.json
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

## Running the Detection Pipeline

Place your CCTV clips in `./data/clips/` and `store_layout.json` in `./data/`.

```bash
docker compose exec api bash
python -m pipeline.run \
    --clips-dir /data/clips \
    --output-dir /data/events \
    --store-layout /data/store_layout.json \
    --workers 2
```

Events are written to `/data/events/*.jsonl`.

## Ingesting Events into the API

```bash
# Batch ingest
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  -d @./data/events/STORE_X_CAM_Y.jsonl
```

Or use the provided runner script that pipes pipeline output directly to the API.

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
