from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class EventEmitter:
    def __init__(self, output_path: str | Path):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._buffer: list[dict] = []
        self._flush_every = 100

    def emit(self, event: dict) -> None:
        event["event_id"] = event.get("event_id") or str(uuid.uuid4())
        if isinstance(event.get("timestamp"), datetime):
            event["timestamp"] = event["timestamp"].isoformat().replace("+00:00", "Z")
        self._buffer.append(event)
        if len(self._buffer) >= self._flush_every:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        with open(self.output_path, "a", encoding="utf-8") as f:
            for evt in self._buffer:
                f.write(json.dumps(evt) + "\n")
        self._buffer.clear()

    def close(self) -> None:
        self.flush()
