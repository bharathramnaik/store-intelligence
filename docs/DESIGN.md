# Design Document — Store Intelligence System

## Architecture Overview

This system is a modular, containerized pipeline that converts raw CCTV footage into actionable retail analytics. It is designed for deployment across 40 physical stores with minimal operational overhead.

### Data Flow

1. **Detection Layer** (`pipeline/`): Processes 1080p 15fps clips using YOLOv8n and ByteTrack. Emits structured behavioral events (ENTRY, EXIT, ZONE_DWELL, etc.) to JSONL.
2. **Ingestion Layer** (`app/ingestion.py`): FastAPI endpoint accepts batches of 500 events, validates against Pydantic schemas, and upserts into PostgreSQL. Idempotent by `event_id`.
3. **Analytics Layer** (`app/metrics.py`, `app/funnel.py`, `app/heatmap.py`, `app/anomalies.py`): Computes real-time metrics using SQLAlchemy 2.0 async queries. No caching of yesterday's data.
4. **Dashboard Layer** (`dashboard/`): Streamlit application polls the API every 5 seconds and renders Plotly charts.

### Technology Stack

- **API**: FastAPI + Uvicorn (async)
- **Database**: PostgreSQL 15 + asyncpg + SQLAlchemy 2.0
- **Cache/Queue**: Redis 7 (for future pub/sub expansion)
- **CV**: YOLOv8n (Ultralytics) + ByteTrack
- **Dashboard**: Streamlit + Plotly
- **Infra**: Docker Compose, multi-stage builds

### Database Schema

- `events`: All behavioral events with JSONB metadata
- `sessions`: Visitor session state (start, end, converted, is_staff)
- `pos_transactions`: POS records with correlation flag
- `anomalies`: Persisted anomaly alerts
- `daily_metrics`: 7-day rolling aggregates for anomaly baselines

### Logging & Observability

Every request is logged via `structlog` in JSON format with: `trace_id`, `store_id`, `endpoint`, `latency_ms`, `event_count`, `status_code`. The `GET /health` endpoint exposes per-store feed staleness (`STALE_FEED` if >10 min lag).

## AI-Assisted Decisions

### Decision 1: Tracking Algorithm

**AI Suggestion**: DeepSORT with OSNet Re-ID model for robust appearance matching.
**My Evaluation**: DeepSORT's appearance model is computationally expensive and requires GPU acceleration. The challenge footage is 15fps CCTV with face blur, making Re-ID features less reliable. DeepSORT would struggle to maintain real-time performance on CPU-only edge hardware.
**Final Choice**: ByteTrack. It uses motion-based tracking (Kalman filter + IoU matching) which is sufficient for 15fps retail scenes. It runs at 30+ FPS on CPU with YOLOv8n, meeting the real-time requirement without GPU dependency.
**Override**: Yes. I overrode the AI suggestion because the operational constraint (CPU-only edge deployment) was more important than tracking elegance.

### Decision 2: Event Streaming Architecture

**AI Suggestion**: Apache Kafka for event ingestion, with separate consumers for metrics and anomaly detection.
**My Evaluation**: Kafka is excellent for high-throughput streaming, but 40 stores × 3 cameras × ~2 events/sec = 240 events/sec. This is low throughput. Kafka adds significant operational complexity (ZooKeeper/KRaft, topic management, consumer groups) that is unacceptable in a 48-hour challenge and overkill for this scale.
**Final Choice**: PostgreSQL upserts (`ON CONFLICT DO NOTHING`) with a background async task for POS correlation. Redis pub/sub is available for future real-time dashboard push if needed.
**Override**: Yes. I chose simplicity and operational feasibility over architectural purity.

### Decision 3: Staff Detection Strategy

**AI Suggestion**: Use a Vision-Language Model (GPT-4V/Claude Vision) to classify staff by uniform description.
**My Evaluation**: VLMs are slow (1–3 sec per frame), expensive at scale, and introduce network dependency. The challenge footage has face blur, but uniforms are still visible. A heuristic approach using HSV color histogram matching + billing-zone dominance achieves 70%+ accuracy with zero latency and zero API cost.
**Final Choice**: Hybrid approach. Heuristic classifier as primary (HSV histogram + spatial heuristics). VLM as optional fallback with a documented prompt in `pipeline/staff.py`. The VLM path is a placeholder function that can be activated if heuristic confidence is low.
**Override**: Partially. I accepted the VLM concept but relegated it to fallback status due to latency constraints.
