from __future__ import annotations

import uuid
from datetime import datetime, timedelta
import numpy as np
import cv2


class SessionManager:
    def __init__(self, reentry_timeout_minutes: int = 30, appearance_threshold: float = 0.65):
        self.sessions: dict[str, dict] = {}  # visitor_id -> session data
        self.closed_sessions: list[dict] = []  # for re-entry matching
        self.reentry_timeout = timedelta(minutes=reentry_timeout_minutes)
        self.appearance_threshold = appearance_threshold

    def start_session(self, track_id: int, store_id: str, timestamp: datetime, is_staff: bool) -> str:
        visitor_id = f"VIS_{uuid.uuid4().hex[:6]}"
        self.sessions[visitor_id] = {
            "visitor_id": visitor_id,
            "track_id": track_id,
            "store_id": store_id,
            "start_time": timestamp,
            "end_time": None,
            "is_staff": is_staff,
            "history": [],
            "appearance_hist": None,
            "seq": 0,
        }
        return visitor_id

    def close_session(self, visitor_id: str, timestamp: datetime) -> None:
        if visitor_id in self.sessions:
            self.sessions[visitor_id]["end_time"] = timestamp
            self.closed_sessions.append(self.sessions.pop(visitor_id))

    def try_reentry(self, track_id: int, store_id: str, timestamp: datetime, appearance: np.ndarray | None) -> str | None:
        now = timestamp
        candidates = [
            s for s in self.closed_sessions
            if s["store_id"] == store_id
            and s["end_time"] is not None
            and (now - s["end_time"]) < self.reentry_timeout
        ]

        best_match = None
        best_score = 0.0
        for sess in candidates:
            if sess["appearance_hist"] is not None and appearance is not None:
                score = cv2.compareHist(sess["appearance_hist"], appearance, cv2.HISTCMP_CORREL)
                if score > best_score and score > self.appearance_threshold:
                    best_score = score
                    best_match = sess

        if best_match:
            # Reuse visitor_id but create new session entry
            vid = best_match.get("visitor_id")
            if vid:
                self.sessions[vid] = {
                    "visitor_id": vid,
                    "track_id": track_id,
                    "store_id": store_id,
                    "start_time": timestamp,
                    "end_time": None,
                    "is_staff": best_match["is_staff"],
                    "history": [],
                    "appearance_hist": best_match["appearance_hist"],
                    "seq": best_match.get("seq", 0),
                }
                return vid
        return None

    def update_appearance(self, visitor_id: str, appearance: np.ndarray | None) -> None:
        if visitor_id in self.sessions and appearance is not None:
            self.sessions[visitor_id]["appearance_hist"] = appearance

    def get_session_seq(self, visitor_id: str) -> int:
        if visitor_id in self.sessions:
            self.sessions[visitor_id]["seq"] += 1
            return self.sessions[visitor_id]["seq"]
        return 0

    def get_visitor_history(self, visitor_id: str) -> list[dict]:
        return self.sessions.get(visitor_id, {}).get("history", [])

    def add_history(self, visitor_id: str, cx: float, cy: float, zone: str | None) -> None:
        if visitor_id in self.sessions:
            self.sessions[visitor_id]["history"].append({"cx": cx, "cy": cy, "zone": zone})
