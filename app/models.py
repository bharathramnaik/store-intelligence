from __future__ import annotations

from datetime import datetime
from typing import Literal, Any
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


class EventMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    queue_depth: int | None = None
    sku_zone: str | None = None
    session_seq: int = 0


class EventIngest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: Literal[
        "ENTRY", "EXIT", "ZONE_ENTER", "ZONE_EXIT", "ZONE_DWELL",
        "BILLING_QUEUE_JOIN", "BILLING_QUEUE_ABANDON", "REENTRY"
    ]
    timestamp: datetime
    zone_id: str | None = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: EventMetadata = Field(default_factory=EventMetadata)


class IngestResponse(BaseModel):
    ingested: int
    failed: int
    errors: list[dict[str, Any]]


class MetricOut(BaseModel):
    store_id: str
    unique_visitors: int
    conversion_rate: float
    avg_dwell_per_zone: dict[str, float]
    queue_depth: int
    abandonment_rate: float
    data_confidence: Literal["LOW", "HIGH"]
    computed_at: datetime


class FunnelStage(BaseModel):
    stage: str
    count: int
    drop_off_pct: float | None


class FunnelOut(BaseModel):
    store_id: str
    stages: list[FunnelStage]
    total_sessions: int
    data_confidence: Literal["LOW", "HIGH"]


class HeatmapZone(BaseModel):
    zone_id: str
    visit_frequency: int
    avg_dwell_ms: float
    normalized_score: float


class HeatmapOut(BaseModel):
    store_id: str
    zones: list[HeatmapZone]
    data_confidence: Literal["LOW", "HIGH"]


class AnomalyOut(BaseModel):
    store_id: str
    anomaly_type: str
    severity: Literal["INFO", "WARN", "CRITICAL"]
    message: str
    suggested_action: str
    created_at: datetime


class HealthStoreStatus(BaseModel):
    store_id: str
    last_event_timestamp: datetime | None
    status: Literal["ACTIVE", "STALE_FEED"]


class HealthOut(BaseModel):
    service: Literal["healthy", "degraded"]
    stores: list[HealthStoreStatus]
    timestamp: datetime
