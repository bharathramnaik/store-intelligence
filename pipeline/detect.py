from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
import json

import cv2
import numpy as np
from ultralytics import YOLO

from pipeline.direction import DirectionTracker
from pipeline.zones import ZoneMapper
from pipeline.staff import StaffClassifier
from pipeline.tracker import SessionManager
from pipeline.queue import QueueDetector
from pipeline.emit import EventEmitter


class DetectionPipeline:
    def __init__(
        self,
        store_id: str,
        camera_id: str,
        clip_path: str | Path,
        store_layout_path: str | Path,
        output_dir: str | Path,
        model_name: str = "yolov8n.pt",
        sample_every: int = 2,
    ):
        self.store_id = store_id
        self.camera_id = camera_id
        self.clip_path = Path(clip_path)
        self.output_dir = Path(output_dir)
        self.sample_every = sample_every

        self.model = YOLO(self._resolve_model_path(model_name))
        self.model.fuse()

        self.zone_mapper = ZoneMapper(store_layout_path)
        self.staff_classifier = StaffClassifier()
        self.session_manager = SessionManager()
        self.queue_detector = QueueDetector()
        self.direction_tracker: DirectionTracker | None = None

        # Determine camera role
        camera_meta = self.zone_mapper.get_camera(self.store_id, self.camera_id)
        cam_lower = camera_id.lower()
        self.camera_role = camera_meta.get("type")
        if not self.camera_role:
            if "entry" in cam_lower or "exit" in cam_lower:
                self.camera_role = "entry"
            elif "billing" in cam_lower or "counter" in cam_lower:
                self.camera_role = "billing"
            elif "staff" in cam_lower:
                self.camera_role = "staff"
            else:
                self.camera_role = "floor"

        self.emitter = EventEmitter(
            self.output_dir / f"{store_id}_{camera_id}_{self.clip_path.stem}.jsonl"
        )

        # Track state per person
        self.track_visitor_map: dict[int, str] = {}  # track_id -> visitor_id
        self.track_zone: dict[int, str | None] = {}
        self.track_dwell_start: dict[int, datetime] = {}
        self.track_in_queue: dict[int, bool] = {}

    def _resolve_model_path(self, model_name: str) -> str:
        explicit = Path(model_name)
        if explicit.exists():
            return str(explicit)

        models_dir = Path(os.getenv("MODEL_PATH", "/models"))
        fallback = models_dir / model_name
        if fallback.exists():
            return str(fallback)

        return model_name

    def _compute_appearance_hist(self, frame: np.ndarray, bbox: tuple[int, ...]) -> np.ndarray | None:
        x1, y1, x2, y2 = map(int, bbox)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [16, 16], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        return hist

    def _make_event(
        self,
        event_type: str,
        visitor_id: str,
        timestamp: datetime,
        zone_id: str | None = None,
        dwell_ms: int = 0,
        is_staff: bool = False,
        confidence: float = 0.0,
        metadata: dict | None = None,
    ) -> dict:
        seq = self.session_manager.get_session_seq(visitor_id)
        return {
            "event_id": str(uuid.uuid4()),
            "store_id": self.store_id,
            "camera_id": self.camera_id,
            "visitor_id": visitor_id,
            "event_type": event_type,
            "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            "zone_id": zone_id,
            "dwell_ms": dwell_ms,
            "is_staff": is_staff,
            "confidence": confidence,
            "metadata": metadata or {"queue_depth": None, "sku_zone": zone_id, "session_seq": seq},
        }

    def process(self) -> None:
        cap = cv2.VideoCapture(str(self.clip_path), cv2.CAP_FFMPEG)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(str(self.clip_path))
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {self.clip_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Set direction line at center for entry cameras
        if self.camera_role == "entry" and self.direction_tracker is None:
            self.direction_tracker = DirectionTracker(line_y=height // 2)

        clip_start = datetime.now(timezone.utc) - timedelta(seconds=int(frame_count / fps))
        frame_idx = 0
        processed = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            if frame_idx % self.sample_every != 0:
                continue

            timestamp = clip_start + timedelta(seconds=frame_idx / fps)
            results = self.model.track(frame, persist=True, tracker="bytetrack.yaml", verbose=False)

            detections: list[dict] = []
            if results and results[0].boxes is not None:
                boxes = results[0].boxes
                for i, box in enumerate(boxes):
                    if box.id is None:
                        continue
                    track_id = int(box.id.item())
                    x1, y1, x2, y2 = map(float, box.xyxy[0].tolist())
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    conf = float(box.conf.item()) if box.conf is not None else 0.5

                    zone = self.zone_mapper.get_zone(
                        self.store_id,
                        self.camera_id,
                        cx,
                        cy,
                        frame_size=(width, height),
                    )
                    appearance = self._compute_appearance_hist(frame, (x1, y1, x2, y2))

                    # Staff classification
                    history = self.session_manager.get_visitor_history(self.track_visitor_map.get(track_id, ""))
                    is_staff, staff_conf = self.staff_classifier.classify(frame, (x1, y1, x2, y2), history)
                    if self.camera_role == "staff":
                        is_staff = True
                        staff_conf = max(staff_conf, 0.95)
                    final_conf = round(conf * staff_conf, 2) if is_staff else round(conf, 2)

                    detections.append({
                        "track_id": track_id,
                        "bbox": (x1, y1, x2, y2),
                        "cx": cx,
                        "cy": cy,
                        "confidence": final_conf,
                        "zone": zone,
                        "is_staff": is_staff,
                        "appearance": appearance,
                    })

            # Queue depth for billing camera
            queue_depth = None
            if self.camera_role == "billing":
                queue_depth = self.queue_detector.compute_depth(detections)

            # Process each detection
            for det in detections:
                track_id = det["track_id"]
                appearance = det.pop("appearance")

                # Assign or recover visitor_id
                if track_id not in self.track_visitor_map:
                    # Try re-entry first
                    reentry_vid = self.session_manager.try_reentry(
                        track_id, self.store_id, timestamp, appearance
                    )
                    if reentry_vid:
                        self.track_visitor_map[track_id] = reentry_vid
                        self.emitter.emit(self._make_event(
                            "REENTRY", reentry_vid, timestamp,
                            is_staff=det["is_staff"], confidence=det["confidence"]
                        ))
                    else:
                        vid = self.session_manager.start_session(
                            track_id, self.store_id, timestamp, det["is_staff"]
                        )
                        self.track_visitor_map[track_id] = vid
                        self.emitter.emit(self._make_event(
                            "ENTRY", vid, timestamp,
                            is_staff=det["is_staff"], confidence=det["confidence"]
                        ))

                visitor_id = self.track_visitor_map[track_id]
                self.session_manager.update_appearance(visitor_id, appearance)
                self.session_manager.add_history(visitor_id, det["cx"], det["cy"], det["zone"])

                # Direction detection for entry camera
                if self.camera_role == "entry" and self.direction_tracker:
                    direction = self.direction_tracker.update(track_id, det["cx"], det["cy"])
                    if direction == "EXIT":
                        self.emitter.emit(self._make_event(
                            "EXIT", visitor_id, timestamp,
                            is_staff=det["is_staff"], confidence=det["confidence"]
                        ))
                        self.session_manager.close_session(visitor_id, timestamp)
                        self.track_visitor_map.pop(track_id, None)
                        continue

                # Zone transitions
                prev_zone = self.track_zone.get(track_id)
                curr_zone = det["zone"]
                if curr_zone != prev_zone:
                    if prev_zone is not None:
                        # ZONE_EXIT with dwell
                        dwell_start = self.track_dwell_start.get(track_id, timestamp)
                        dwell_ms = int((timestamp - dwell_start).total_seconds() * 1000)
                        self.emitter.emit(self._make_event(
                            "ZONE_EXIT", visitor_id, timestamp, zone_id=prev_zone,
                            dwell_ms=dwell_ms, is_staff=det["is_staff"], confidence=det["confidence"]
                        ))
                    if curr_zone is not None:
                        self.emitter.emit(self._make_event(
                            "ZONE_ENTER", visitor_id, timestamp, zone_id=curr_zone,
                            is_staff=det["is_staff"], confidence=det["confidence"]
                        ))
                        self.track_dwell_start[track_id] = timestamp
                    self.track_zone[track_id] = curr_zone
                else:
                    # Dwell tracking
                    if curr_zone and track_id in self.track_dwell_start:
                        elapsed = (timestamp - self.track_dwell_start[track_id]).total_seconds()
                        if elapsed >= 30:
                            self.emitter.emit(self._make_event(
                                "ZONE_DWELL", visitor_id, timestamp, zone_id=curr_zone,
                                dwell_ms=int(elapsed * 1000), is_staff=det["is_staff"],
                                confidence=det["confidence"]
                            ))
                            self.track_dwell_start[track_id] = timestamp

                # Billing queue logic
                if self.camera_role == "billing" and curr_zone == "BILLING":
                    if queue_depth and queue_depth > 0 and not self.track_in_queue.get(track_id, False):
                        self.track_in_queue[track_id] = True
                        meta = {"queue_depth": queue_depth, "sku_zone": curr_zone, "session_seq": 0}
                        self.emitter.emit(self._make_event(
                            "BILLING_QUEUE_JOIN", visitor_id, timestamp, zone_id=curr_zone,
                            is_staff=det["is_staff"], confidence=det["confidence"], metadata=meta
                        ))

            processed += 1
            if processed % 100 == 0:
                print(f"Processed {processed} frames for {self.camera_id}")

        cap.release()
        self.emitter.close()
        print(f"Done: {self.camera_id} -> {self.emitter.output_path}")
