from __future__ import annotations



class QueueDetector:
    """Detects queue depth in billing zone based on y-centroid ordering."""

    def __init__(self, zone_name: str = "BILLING"):
        self.zone_name = zone_name
        self.prev_depth = 0

    def compute_depth(self, detections: list[dict]) -> int:
        # Sort by y-centroid descending (assuming queue goes back-to-front in frame)
        people = [d for d in detections if d.get("zone") == self.zone_name and not d.get("is_staff", False)]
        if not people:
            self.prev_depth = 0
            return 0
        # Simple count-based depth; could be enhanced with spatial clustering
        depth = len(people)
        self.prev_depth = depth
        return depth
