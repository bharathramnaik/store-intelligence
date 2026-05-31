"""Process first N frames from each remaining clip to get representative events."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.detect import DetectionPipeline

CLIPS_DIR = Path("data/clips")
OUTPUT_DIR = Path("data/events_real")
LAYOUT_PATH = Path("data/store_layout.json")
MAX_FRAMES = 3000  # ~200 seconds per clip

existing = {f.stem for f in OUTPUT_DIR.glob("*.jsonl")}
layout = json.loads(LAYOUT_PATH.read_text())
clip_map = layout.get("STORE_BLR_002", {}).get("clip_map", {})

for clip_path in sorted(CLIPS_DIR.glob("*.mp4")):
    mapped = clip_map.get(clip_path.name)
    if mapped:
        store_id, camera_id = "STORE_BLR_002", mapped
    else:
        parts = clip_path.stem.split("_")
        store_id = "_".join(parts[:3]) if len(parts) >= 4 else "STORE_BLR_002"
        camera_id = "_".join(parts[3:]) if len(parts) >= 4 else clip_path.stem
    out_name = f"{store_id}_{camera_id}_{clip_path.stem}.jsonl"
    if out_name.replace(".jsonl", "") in existing:
        print(f"Skipping {camera_id} — already processed")
        continue
    print(f"\nProcessing {camera_id} ({clip_path.name})...")
    p = DetectionPipeline(
        store_id=store_id,
        camera_id=camera_id,
        clip_path=str(clip_path),
        store_layout_path=str(LAYOUT_PATH),
        output_dir=str(OUTPUT_DIR),
    )
    p.process(max_frames=MAX_FRAMES)
    print(f"Done: {camera_id}")
