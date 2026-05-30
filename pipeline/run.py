from __future__ import annotations

import argparse
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from pipeline.detect import DetectionPipeline


def process_clip(store_id: str, camera_id: str, clip_path: Path, layout_path: Path, output_dir: Path) -> None:
    pipeline = DetectionPipeline(
        store_id=store_id,
        camera_id=camera_id,
        clip_path=clip_path,
        store_layout_path=layout_path,
        output_dir=output_dir,
    )
    pipeline.process()


def load_clip_mapping(layout_path: Path) -> dict[str, tuple[str, str]]:
    if not layout_path.exists():
        return {}

    data = json.loads(layout_path.read_text(encoding="utf-8"))
    mapping: dict[str, tuple[str, str]] = {}
    for store_id, store in data.items():
        for filename, camera_id in store.get("clip_map", {}).items():
            mapping[filename] = (store_id, camera_id)
        for camera in store.get("cameras", []):
            for source_file in camera.get("source_files", []):
                mapping.setdefault(source_file, (store_id, camera["id"]))
    return mapping


def main() -> None:
    parser = argparse.ArgumentParser(description="Store Intelligence Detection Pipeline")
    parser.add_argument("--clips-dir", required=True, help="Directory containing CCTV clips")
    parser.add_argument("--output-dir", required=True, help="Directory for JSONL event output")
    parser.add_argument("--store-layout", required=True, help="Path to store_layout.json")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers")
    args = parser.parse_args()

    clips_dir = Path(args.clips_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    clip_mapping = load_clip_mapping(Path(args.store_layout))

    # Expected naming: STORE_ID_CAM_ENTRY_01.mp4 or similar
    clips = list(clips_dir.glob("*.mp4")) + list(clips_dir.glob("*.avi")) + list(clips_dir.glob("*.mkv"))

    tasks = []
    for clip in clips:
        mapped = clip_mapping.get(clip.name)
        if mapped:
            store_id, camera_id = mapped
        else:
            parts = clip.stem.split("_")
            if len(parts) >= 4:
                store_id = "_".join(parts[:3])
                camera_id = "_".join(parts[3:])
            else:
                store_id = "STORE_UNKNOWN"
                camera_id = clip.stem.replace(" ", "_").upper()
        tasks.append((store_id, camera_id, clip))

    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(process_clip, sid, cid, cp, Path(args.store_layout), output_dir): (sid, cid)
            for sid, cid, cp in tasks
        }
        for future in as_completed(futures):
            sid, cid = futures[future]
            try:
                future.result()
                print(f"Completed: {sid} / {cid}")
            except Exception as exc:
                print(f"Failed: {sid} / {cid} -> {exc}")


if __name__ == "__main__":
    main()
