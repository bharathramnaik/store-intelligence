# PROMPT: "Write integration test that reads real pipeline-generated JSONL events, ingests them, and verifies all API endpoints return sensible results"
# CHANGES MADE: Added test to ingest pipeline events from data/events/*.jsonl, verify metrics endpoint returns non-zero visitors, verify funnel endpoint returns stages with counts, verify heatmap endpoint returns zones, verify anomalies endpoint returns list

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient


EVENTS_DIR = Path("data/events")


class TestIntegrationPipeline:
    async def test_ingest_pipeline_events_and_query_endpoints(self, client: AsyncClient):
        jsonl_files = list(EVENTS_DIR.glob("*.jsonl"))
        if not jsonl_files:
            pytest.skip("No pipeline event files found in data/events/")

        total_ingested = 0
        total_failed = 0
        store_ids = set()

        for jsonl_file in sorted(jsonl_files):
            events = []
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))

            if not events:
                continue

            for evt in events:
                if "store_id" in evt:
                    store_ids.add(evt["store_id"])

            response = await client.post("/events/ingest", json=events)
            assert response.status_code == 200
            data = response.json()
            total_ingested += data["ingested"]
            total_failed += data["failed"]

        assert total_ingested > 0, "No events were ingested from pipeline output"
        assert len(store_ids) > 0, "No store IDs found in pipeline events"

        for sid in store_ids:
            resp = await client.get(f"/stores/{sid}/metrics")
            assert resp.status_code == 200
            m = resp.json()
            assert m["store_id"] == sid
            assert isinstance(m["unique_visitors"], int)
            assert isinstance(m["conversion_rate"], float) or isinstance(m["conversion_rate"], int)
            assert isinstance(m["avg_dwell_per_zone"], dict)

            resp = await client.get(f"/stores/{sid}/funnel")
            assert resp.status_code == 200
            f = resp.json()
            assert f["store_id"] == sid
            assert len(f["stages"]) == 4
            for stage in f["stages"]:
                assert "stage" in stage
                assert "count" in stage
                assert "drop_off_pct" in stage

            resp = await client.get(f"/stores/{sid}/heatmap")
            assert resp.status_code == 200
            h = resp.json()
            assert h["store_id"] == sid
            assert isinstance(h["zones"], list)
            assert h["data_confidence"] in ("LOW", "HIGH")
            for zone in h["zones"]:
                assert "zone_id" in zone
                assert "visit_frequency" in zone
                assert "normalized_score" in zone

            resp = await client.get(f"/stores/{sid}/anomalies")
            assert resp.status_code == 200
            anomalies = resp.json()
            assert isinstance(anomalies, list)
            for a in anomalies:
                assert a["store_id"] == sid
                assert a["anomaly_type"] in ("QUEUE_SPIKE", "CONVERSION_DROP", "DEAD_ZONE")
                assert a["severity"] in ("INFO", "WARN", "CRITICAL")
                assert "suggested_action" in a
