from __future__ import annotations

from collections import deque
from typing import Literal

import numpy as np


class DirectionTracker:
    """Tracks centroid history to determine ENTRY vs EXIT across a virtual line."""

    def __init__(self, line_y: int | None = None, history: int = 10):
        self.line_y = line_y
        self.history = history
        self.centroids: dict[int, deque[tuple[float, float]]] = {}
        self.crossed: set[int] = set()

    def update(self, track_id: int, cx: float, cy: float) -> Literal["ENTRY", "EXIT", None]:
        if track_id not in self.centroids:
            self.centroids[track_id] = deque(maxlen=self.history)
        self.centroids[track_id].append((cx, cy))

        if len(self.centroids[track_id]) < 3 or self.line_y is None:
            return None

        # Compute average direction vector
        pts = list(self.centroids[track_id])
        dy = pts[-1][1] - pts[0][1]

        # Simple logic: if crossing line from below to above = EXIT (outbound), above to below = ENTRY (inbound)
        # Adjust based on camera orientation; default: entering store = moving downward (toward interior)
        prev_y = pts[0][1]
        curr_y = pts[-1][1]

        if prev_y > self.line_y and curr_y <= self.line_y and track_id not in self.crossed:
            self.crossed.add(track_id)
            return "ENTRY"
        elif prev_y < self.line_y and curr_y >= self.line_y and track_id not in self.crossed:
            self.crossed.add(track_id)
            return "EXIT"
        return None

    def reset_crossed(self, track_id: int) -> None:
        self.crossed.discard(track_id)
