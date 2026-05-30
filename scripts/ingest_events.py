from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx


def ingest_file(file_path: Path, api_url: str, batch_size: int = 500) -> None:
    events = []
    with open(file_path) as f:
        for line in f:
            events.append(json.loads(line))
            if len(events) >= batch_size:
                _send_batch(api_url, events)
                events.clear()
    if events:
        _send_batch(api_url, events)


def _send_batch(api_url: str, events: list) -> None:
    r = httpx.post(f"{api_url}/events/ingest", json=events, timeout=30.0)
    r.raise_for_status()
    data = r.json()
    print(f"Ingested {data['ingested']}, failed {data['failed']}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events-dir", required=True)
    parser.add_argument("--api-url", default="http://localhost:8000")
    args = parser.parse_args()

    events_dir = Path(args.events_dir)
    for jsonl in events_dir.glob("*.jsonl"):
        print(f"Ingesting {jsonl.name}...")
        ingest_file(jsonl, args.api_url)


if __name__ == "__main__":
    main()
