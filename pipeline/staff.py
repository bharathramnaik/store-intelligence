from __future__ import annotations

import numpy as np
import cv2


class StaffClassifier:
    """Heuristic staff detection based on uniform color and billing zone dominance."""

    def __init__(self, uniform_hsv_range: tuple[tuple[int, int, int], tuple[int, int, int]] | None = None):
        # Default generic uniform color range (saturated, medium brightness)
        self.uniform_hsv_range = uniform_hsv_range or ((0, 50, 50), (180, 255, 200))

    def classify(self, frame: np.ndarray, bbox: tuple[int, int, int, int], track_history: list[dict]) -> tuple[bool, float]:
        x1, y1, x2, y2 = map(int, bbox)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return False, 0.0

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        lower, upper = self.uniform_hsv_range
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        uniform_ratio = np.count_nonzero(mask) / mask.size

        # Heuristic 1: high uniform color coverage
        if uniform_ratio > 0.45:
            return True, round(min(uniform_ratio + 0.2, 0.95), 2)

        # Heuristic 2: spends >60% in billing zone with low movement variance
        if track_history:
            billing_ratio = sum(1 for h in track_history if h.get("zone") == "BILLING") / len(track_history)
            if billing_ratio > 0.6 and len(track_history) > 30:
                # Low movement variance
                cxs = [h["cx"] for h in track_history]
                cys = [h["cy"] for h in track_history]
                if np.var(cxs) < 100 and np.var(cys) < 100:
                    return True, 0.75

        return False, round(uniform_ratio, 2)

    def classify_vlm(self, frame: np.ndarray, bbox: tuple[int, int, int, int]) -> tuple[bool, float]:
        """Placeholder for VLM-based staff detection. Document prompt in DESIGN.md."""
        # PROMPT (for DESIGN.md):
        # "Analyze this cropped person image. Is this person wearing a store staff uniform?
        #  Respond with JSON: {'is_staff': bool, 'confidence': float 0-1}"
        return False, 0.0
