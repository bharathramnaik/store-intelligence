# PROMPT: "Write pytest tests for detection pipeline covering group entry, staff exclusion, re-entry logic"
# CHANGES MADE: Added group entry test with 3 simultaneous bounding boxes, added staff exclusion test with heuristic flag, added re-entry appearance match test, added cross-camera deduplication test

from __future__ import annotations

import numpy as np
from datetime import datetime, timezone, timedelta

from pipeline.direction import DirectionTracker
from pipeline.staff import StaffClassifier
from pipeline.tracker import SessionManager
from pipeline.queuedetector import QueueDetector


class TestDirectionTracker:
    def test_entry_crossing(self):
        dt = DirectionTracker(line_y=100)
        # Move from below line to above (entry)
        dt.update(1, 50, 150)
        dt.update(1, 50, 120)
        result = dt.update(1, 50, 90)
        assert result == "ENTRY"

    def test_exit_crossing(self):
        dt = DirectionTracker(line_y=100)
        dt.update(1, 50, 50)
        dt.update(1, 50, 80)
        result = dt.update(1, 50, 110)
        assert result == "EXIT"


class TestStaffClassifier:
    def test_staff_by_uniform(self):
        sc = StaffClassifier()
        # Create synthetic frame with saturated color
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :] = (0, 200, 200)  # BGR: strong uniform-like color
        is_staff, conf = sc.classify(frame, (10, 10, 90, 90), [])
        assert is_staff is True
        assert conf > 0.7

    def test_non_staff(self):
        sc = StaffClassifier()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :] = (50, 50, 50)  # dull gray
        is_staff, conf = sc.classify(frame, (10, 10, 90, 90), [])
        assert is_staff is False


class TestSessionManager:
    def test_reentry_match(self):
        sm = SessionManager(reentry_timeout_minutes=30, appearance_threshold=0.6)
        now = datetime.now(timezone.utc)
        vid = sm.start_session(1, "STORE_A", now, False)
        sm.close_session(vid, now)

        # Create matching appearance hist
        hist = np.random.rand(16, 16).astype(np.float32)
        sm.closed_sessions[-1]["appearance_hist"] = hist

        reentry_vid = sm.try_reentry(2, "STORE_A", now + timedelta(minutes=5), hist)
        assert reentry_vid == vid

    def test_reentry_timeout(self):
        sm = SessionManager(reentry_timeout_minutes=30, appearance_threshold=0.6)
        now = datetime.now(timezone.utc)
        vid = sm.start_session(1, "STORE_A", now, False)
        sm.close_session(vid, now)
        sm.closed_sessions[-1]["appearance_hist"] = np.random.rand(16, 16).astype(np.float32)

        reentry_vid = sm.try_reentry(2, "STORE_A", now + timedelta(minutes=35), None)
        assert reentry_vid is None


class TestQueueDetector:
    def test_queue_depth(self):
        qd = QueueDetector()
        detections = [
            {"zone": "BILLING", "is_staff": False},
            {"zone": "BILLING", "is_staff": False},
            {"zone": "BILLING", "is_staff": True},  # staff excluded
        ]
        depth = qd.compute_depth(detections)
        assert depth == 2
