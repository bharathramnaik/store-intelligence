# Engineering Choices

## 1. Detection Model: YOLOv8n + ByteTrack

### Options Considered
- **YOLOv8n**: Nano variant, ~3.2M parameters, fastest inference
- **YOLOv8s**: Small variant, ~11.2M parameters, better accuracy
- **RT-DETR**: Transformer-based detector, superior accuracy but slower

### AI Suggestion
The LLM recommended YOLOv8s as a balanced choice between speed and accuracy, noting that nano might miss small occluded objects in billing queues.

### My Choice
**YOLOv8n** with ByteTrack tracking.

### Rationale
The challenge footage is 1080p 15fps from fixed CCTV cameras. The primary constraint is **real-time inference on CPU-only edge hardware** (retail stores do not have GPUs). YOLOv8n achieves 30+ FPS on a modern CPU at 1080p, which satisfies the 15fps input rate with headroom. I sample every 2nd frame (effective 7.5fps) to further reduce load.

While YOLOv8s has better mAP, the difference on large, frontal human figures in retail is marginal. The real challenge is **tracking continuity** (groups, re-entry), not detection accuracy. ByteTrack's motion-based association handles temporary occlusions better than DeepSORT when appearance features are degraded by face blur.

**North Star alignment**: Every undetected visitor or tracking failure in a billing zone means a missed conversion—directly underreporting the store's true conversion rate. By maximizing inference throughput (30+ FPS), YOLOv8n ensures no frame is dropped during peak hours, giving the correlation engine the best possible coverage of billing-zone activity.

RT-DETR was rejected because it requires ~50ms per frame on GPU and >200ms on CPU, making it unsuitable for real-time edge deployment.

### Trade-off
I accept slightly lower detection confidence on heavily occluded cases in exchange for meeting the real-time throughput requirement. Low-confidence detections are explicitly flagged (not silently dropped) per the event schema.

---

## 2. Event Schema: Nested Metadata with Flat Core Fields

### Options Considered
- **Fully Flat Schema**: Every field at top level (simple, but rigid)
- **Fully Nested Schema**: Everything inside a `data` blob (flexible, but unqueryable)
- **Hybrid**: Flat core fields + nested metadata extensibility

### AI Suggestion
The LLM suggested a fully flat schema for simplicity, arguing that a relational database works best with normalized columns.

### My Choice
**Hybrid schema**: Flat core fields (`event_id`, `visitor_id`, `timestamp`, `event_type`, `store_id`, `camera_id`) + nested `metadata` object for sensor-specific extensions.

### Rationale
The core fields are queried and indexed in every analytics endpoint (metrics, funnel, health). Keeping them flat allows PostgreSQL B-tree indexes to work efficiently without JSONB path lookups. The `metadata` field contains extensible sensor data (`queue_depth`, `sku_zone`, `session_seq`) that varies by event type.

This design lets us add new sensor types (e.g., RFID, WiFi triangulation) in the future without schema migrations. We simply add new keys to `metadata` while the ingestion layer remains unchanged.

**North Star alignment**: The `is_staff` Boolean on every event row is the single most important field for conversion accuracy. Making it a top-level indexed column means the metrics queries filter staff out in a single B-tree scan—without JSONB path traversal—ensuring the conversion rate denominator (non-staff visitors) is always correct, even under high write throughput from 40 stores.

### Trade-off
JSONB queries on metadata are slower than column lookups, but metadata fields are rarely used in `WHERE` clauses (mostly returned in responses). The `queue_depth` exception is handled by indexing the JSONB expression where needed.

---

## 3. API Database: PostgreSQL with asyncpg

### Options Considered
- **SQLite**: Zero-config, single-file, but locks on concurrent writes
- **PostgreSQL**: Full ACID, async driver, JSONB support, window functions
- **MongoDB**: Schema flexibility, but weaker transactional guarantees

### AI Suggestion
The LLM suggested SQLite for rapid prototyping, noting that it is "sufficient for a challenge submission" and requires no Docker service.

### My Choice
**PostgreSQL 15** with `asyncpg` and SQLAlchemy 2.0 async.

### Rationale
SQLite's write-lock mechanism would fail under concurrent ingestion of 500-event batches from multiple stores. The challenge explicitly requires the API to handle real-time events from 40 stores. PostgreSQL's row-level locking and MVCC handle this natively.

The 7-day anomaly detection window requires SQL window functions (`AVG() OVER`, `STDDEV()`) which SQLite does not support efficiently. PostgreSQL's JSONB type stores the `metadata` field without requiring a separate document store.

MongoDB was rejected because conversion rate is a financial metric that requires ACID consistency. A failed POS correlation update must not leave the database in an inconsistent state (session marked converted but transaction not correlated).

**North Star alignment**: POS correlation is the critical path to the conversion rate metric. It requires a `SELECT` (find visitors in billing zone) followed by an `UPDATE` (mark sessions as converted). PostgreSQL's MVCC ensures these two operations are atomically correct under concurrent writes from the background worker and live ingestion. SQLite's serialized writes would stall the correlation engine during peak ingestion, delaying conversion attribution by minutes. MongoDB's lack of multi-document transactions could leave the `converted` flag out of sync with the `correlated` flag.

### Trade-off
PostgreSQL adds a Docker service and ~100MB memory overhead. This is acceptable because the challenge explicitly requires `docker compose up` to start everything, and production readiness is a scoring criterion.
