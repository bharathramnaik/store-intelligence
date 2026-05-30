export interface MetricData {
  store_id: string;
  unique_visitors: number;
  conversion_rate: number;
  avg_dwell_per_zone: Record<string, number>;
  queue_depth: number;
  abandonment_rate: number;
  computed_at: string;
}

export interface FunnelStage {
  stage: string;
  count: number;
  drop_off_pct: number | null;
}

export interface FunnelData {
  store_id: string;
  stages: FunnelStage[];
  total_sessions: number;
}

export interface HeatmapZone {
  zone_id: string;
  visit_frequency: number;
  avg_dwell_ms: number;
  normalized_score: number;
}

export interface HeatmapData {
  store_id: string;
  zones: HeatmapZone[];
  data_confidence: 'LOW' | 'HIGH';
}

export interface AnomalyData {
  store_id: string;
  anomaly_type: string;
  severity: 'INFO' | 'WARN' | 'CRITICAL';
  message: string;
  suggested_action: string;
  created_at: string;
}

export interface HealthStore {
  store_id: string;
  last_event_timestamp: string | null;
  status: 'ACTIVE' | 'STALE_FEED';
}

export interface HealthData {
  service: 'healthy' | 'degraded';
  stores: HealthStore[];
  timestamp: string;
}

export interface IngestResponse {
  ingested: number;
  failed: number;
  errors: Array<{ event_id: string; reason: string }>;
}
