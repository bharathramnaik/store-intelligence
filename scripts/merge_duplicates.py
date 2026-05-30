"""Cross-camera visitor deduplication.

The challenge spec identifies camera angle overlap as a known challenge:
- Floor camera partially overlaps with entry camera field of view
- Same person = same physical person, two visitor_ids, double-counted

This script merges sessions from overlapping cameras when their
time windows overlap significantly, meaning they represent the same
physical person who walked between camera views.

Overlapping camera pairs (from store_layout.json zone assignments):
  CAM_ENTRY_01 (ENTRY zone)  ↔  CAM_FLOOR_01 (SKINCARE zone)
  CAM_FLOOR_01 (SKINCARE)    ↔  CAM_FLOOR_02 (MAKEUP zone)
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone, timedelta

import asyncpg

# Cameras whose fields of view overlap in the physical store layout
# (determined from zone/camera assignments in store_layout.json)
OVERLAPPING_CAMERAS: list[tuple[str, str]] = [
    ("CAM_ENTRY_01", "CAM_FLOOR_01"),
    ("CAM_FLOOR_01", "CAM_FLOOR_02"),
]

MIN_OVERLAP_SECONDS = 5  # minimum time overlap to consider same person


async def main() -> None:
    dsn = "postgresql://postgres:postgres@db:5432/store_intelligence"
    conn = await asyncpg.connect(dsn)

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Load all non-staff sessions with their camera event counts
    rows = await conn.fetch(
        """SELECT s.visitor_id, s.store_id, s.start_time, s.end_time, s.is_staff,
                  e.camera_id,
                  MIN(e.timestamp) AS first_event,
                  MAX(e.timestamp) AS last_event
           FROM sessions s
           JOIN events e ON e.visitor_id = s.visitor_id
           WHERE s.is_staff = false AND s.start_time >= $1
           GROUP BY s.visitor_id, s.store_id, s.start_time, s.end_time, s.is_staff, e.camera_id
           ORDER BY s.start_time ASC""",
        today,
    )

    if not rows:
        print("No non-staff sessions found")
        await conn.close()
        return

    # 2. Build sessions grouped by visitor_id
    # Each entry: {visitor_id, store_id, start_time, end_time, cameras: {camera_id: (first_event, last_event)}}
    sessions: dict[str, dict] = {}
    for r in rows:
        vid = r["visitor_id"]
        if vid not in sessions:
            sessions[vid] = {
                "visitor_id": vid,
                "store_id": r["store_id"],
                "start_time": r["start_time"],
                "end_time": r["end_time"],
                "cameras": {},
            }
        sessions[vid]["cameras"][r["camera_id"]] = (r["first_event"], r["last_event"])

    print(f"Loaded {len(sessions)} unique non-staff visitor sessions")

    # 3. Find duplicate pairs (sessions from overlapping cameras with time overlap)
    session_list = list(sessions.values())
    dup_pairs: list[tuple[str, str, str, str]] = []  # (keep_vid, remove_vid, cam_a, cam_b)

    for i in range(len(session_list)):
        for j in range(i + 1, len(session_list)):
            sa, sb = session_list[i], session_list[j]

            # Check if sessions have different camera sets
            cams_a = set(sa["cameras"].keys())
            cams_b = set(sb["cameras"].keys())

            # Check each overlapping camera pair
            for cam_x, cam_y in OVERLAPPING_CAMERAS:
                # Check forward match: cam_x in session A, cam_y in session B
                fwd = cam_x in cams_a and cam_y in cams_b
                # Check reverse match: cam_y in session A, cam_x in session B
                rev = cam_y in cams_a and cam_x in cams_b
                if not (fwd or rev):
                    continue

                if fwd:
                    cam_left, cam_right = cam_x, cam_y
                    s_left, s_right = sa, sb
                else:
                    cam_left, cam_right = cam_y, cam_x
                    s_left, s_right = sa, sb

                # Check time overlap between the two sessions from these cameras
                ev_left = s_left["cameras"][cam_left]
                ev_right = s_right["cameras"][cam_right]

                # Overlap = two intervals intersect
                left_start, left_end = ev_left
                right_start, right_end = ev_right

                # If end_time is NULL (session still open), use last_event
                if left_end is None:
                    left_end = left_start + timedelta(minutes=5)
                if right_end is None:
                    right_end = right_start + timedelta(minutes=5)

                overlap_start = max(left_start, right_start)
                overlap_end = min(left_end, right_end)
                overlap_secs = (overlap_end - overlap_start).total_seconds()

                if overlap_secs >= MIN_OVERLAP_SECONDS:
                    # Same physical person — merge into the earlier session
                    if sa["start_time"] <= sb["start_time"]:
                        keep_vid = sa["visitor_id"]
                        remove_vid = sb["visitor_id"]
                    else:
                        keep_vid = sb["visitor_id"]
                        remove_vid = sa["visitor_id"]

                    dup_pairs.append((keep_vid, remove_vid, cam_left, cam_right))

    # 4. Merge duplicates (keep first occurrence, remove later)
    # Build a mapping: remove_vid -> keep_vid
    remove_map: dict[str, str] = {}
    for keep_vid, remove_vid, cam_left, cam_right in dup_pairs:
        # If remove_vid is already scheduled for removal, skip nested chains for safety
        if remove_vid in remove_map:
            continue
        # Don't merge if the keep_vid is also scheduled for removal
        if keep_vid in remove_map:
            keep_vid = remove_map[keep_vid]
        remove_map[remove_vid] = keep_vid

    print(f"Found {len(dup_pairs)} duplicate pairs, {len(remove_map)} unique visitors to merge")

    if not remove_map:
        await conn.close()
        return

    # 5. Execute merges in a transaction
    async with conn.transaction():
        merged_count = 0
        for remove_vid, keep_vid in remove_map.items():
            # Reassign all events from the duplicate visitor to the canonical visitor
            update_events = await conn.execute(
                "UPDATE events SET visitor_id = $1 WHERE visitor_id = $2",
                keep_vid,
                remove_vid,
            )

            # Get the duplicate session's start/end to merge into canonical
            dup_session = await conn.fetchrow(
                "SELECT start_time, end_time FROM sessions WHERE visitor_id = $1",
                remove_vid,
            )
            if dup_session:
                # Update canonical session's end_time if duplicate ends later
                await conn.execute(
                    """UPDATE sessions
                       SET end_time = GREATEST(
                           COALESCE(end_time, start_time),
                           $1
                       )
                       WHERE visitor_id = $2 AND ($1 > COALESCE(end_time, start_time) OR end_time IS NULL)""",
                    dup_session["end_time"] or dup_session["start_time"],
                    keep_vid,
                )

            # Delete the duplicate session
            await conn.execute(
                "DELETE FROM sessions WHERE visitor_id = $1",
                remove_vid,
            )
            merged_count += 1

        # 6. Drop the daily_metrics cache so it recomputes fresh
        await conn.execute(
            "DELETE FROM daily_metrics WHERE metric_date >= $1",
            today,
        )
        # Also clear anomalies so they recompute
        await conn.execute("DELETE FROM anomalies")

    print(f"Merged {merged_count} duplicate visitors into canonical sessions")
    print(f"Before: {len(sessions)} unique visitors")
    print(f"After:  {len(sessions) - len(remove_map)} unique visitors")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
