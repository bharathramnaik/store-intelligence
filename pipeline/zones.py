from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from shapely.geometry import Point, Polygon


class ZoneMapper:
    def __init__(self, layout_path: str | Path):
        self.layout_path = Path(layout_path)
        self.store_layout: dict[str, Any] = {}
        self.zones: dict[str, dict[str, Polygon]] = {}  # store -> zone_name -> polygon
        self.camera_zones: dict[str, list[str]] = {}  # camera_id -> list of zone names
        self.camera_meta: dict[str, dict[str, dict[str, Any]]] = {}
        self.load()

    def load(self) -> None:
        if not self.layout_path.exists():
            return
        with open(self.layout_path) as f:
            self.store_layout = json.load(f)

        for store_id, store_data in self.store_layout.items():
            self.zones[store_id] = {}
            self.camera_meta[store_id] = {
                camera["id"]: camera for camera in store_data.get("cameras", [])
            }
            for zone in store_data.get("zones", []):
                poly = Polygon(zone["polygon"])
                self.zones[store_id][zone["name"]] = poly
                for cam in zone.get("cameras", []):
                    self.camera_zones.setdefault(cam, []).append(zone["name"])

    def get_camera(self, store_id: str, camera_id: str) -> dict[str, Any]:
        return self.camera_meta.get(store_id, {}).get(camera_id, {})

    def get_zone(
        self,
        store_id: str,
        camera_id: str,
        cx: float,
        cy: float,
        frame_size: tuple[int, int] | None = None,
    ) -> str | None:
        if store_id not in self.zones:
            return None

        camera_meta = self.get_camera(store_id, camera_id)
        if frame_size and camera_meta.get("resolution"):
            layout_width, layout_height = camera_meta["resolution"]
            frame_width, frame_height = frame_size
            if layout_width and layout_height and (layout_width, layout_height) != (frame_width, frame_height):
                cx = cx * layout_width / frame_width
                cy = cy * layout_height / frame_height

        point = Point(cx, cy)
        candidates = []
        for zone_name, poly in self.zones[store_id].items():
            if poly.contains(point):
                candidates.append(zone_name)

        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        # Prefer zone covered by current camera
        cam_zones = self.camera_zones.get(camera_id, [])
        for c in candidates:
            if c in cam_zones:
                return c

        # Fallback: smallest area zone
        return min(candidates, key=lambda z: self.zones[store_id][z].area)
