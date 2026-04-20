"""
Player Tracker — tracks individual entities across frames using YOLO + ByteTrack.
Builds per-entity movement paths and detects rapid position changes.
"""
import logging
import cv2
import numpy as np

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        logger.info("  [Tracker] Loading YOLOv8n for tracking...")
        _model = YOLO("yolov8n.pt")
        logger.info("  [Tracker] Model ready")
    return _model


def track_players(clip_path: str, max_seconds: int = 90) -> dict:
    """Track players/entities across video frames using YOLO + ByteTrack."""
    try:
        model = _get_model()

        cap = cv2.VideoCapture(clip_path)
        fps = max(1.0, cap.get(cv2.CAP_PROP_FPS) or 30)
        cap.release()

        max_frames = int(fps * max_seconds)
        tracks = {}   # track_id -> list of {frame, ts, x, y}
        frame_idx = 0

        try:
            tracker = "bytetrack.yaml"
            results_iter = model.track(
                source=clip_path,
                stream=True,
                persist=True,
                tracker=tracker,
                conf=0.25,
                verbose=False,
                imgsz=640,
            )
        except Exception:
            tracker = "botsort.yaml"
            results_iter = model.track(
                source=clip_path,
                stream=True,
                persist=True,
                tracker=tracker,
                conf=0.25,
                verbose=False,
                imgsz=640,
            )

        for r in results_iter:
            if frame_idx >= max_frames:
                break
            if r.boxes is not None and r.boxes.id is not None:
                ts = round(frame_idx / fps, 1)
                ids = r.boxes.id.cpu().numpy().astype(int)
                boxes = r.boxes.xyxy.cpu().numpy()
                for tid, box in zip(ids, boxes):
                    cx = round(float((box[0] + box[2]) / 2))
                    cy = round(float((box[1] + box[3]) / 2))
                    if tid not in tracks:
                        tracks[tid] = []
                    tracks[tid].append({"frame": frame_idx, "ts": ts, "x": cx, "y": cy})
            frame_idx += 1

        if not tracks:
            return {"summary": "No entities tracked", "player_count": 0, "movement_events": [], "track_summaries": []}

        track_summaries = []
        movement_events = []

        for tid, positions in tracks.items():
            if len(positions) < 3:
                continue
            xs = [p["x"] for p in positions]
            ys = [p["y"] for p in positions]
            dist = round(((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5)

            track_summaries.append({
                "entity_id": int(tid),
                "start_ts": positions[0]["ts"],
                "end_ts": positions[-1]["ts"],
                "total_distance_px": dist,
                "frames_tracked": len(positions),
            })

            # Detect rapid jumps (likely kills / sudden repositioning)
            for i in range(1, len(positions)):
                ddx = positions[i]["x"] - positions[i - 1]["x"]
                ddy = positions[i]["y"] - positions[i - 1]["y"]
                jump = (ddx ** 2 + ddy ** 2) ** 0.5
                if jump > 180:
                    movement_events.append({
                        "entity_id": int(tid),
                        "timestamp": positions[i]["ts"],
                        "event": "rapid_position_change",
                        "distance_px": round(jump),
                    })

        track_summaries.sort(key=lambda x: x["frames_tracked"], reverse=True)

        summary = (
            f"{len(tracks)} entities tracked over {frame_idx / fps:.0f}s. "
            + " | ".join(
                f"Entity {s['entity_id']}: {s['start_ts']}s-{s['end_ts']}s "
                f"({s['total_distance_px']}px total movement)"
                for s in track_summaries[:6]
            )
        )

        return {
            "summary": summary,
            "player_count": len(tracks),
            "movement_events": movement_events[:20],
            "track_summaries": track_summaries[:10],
        }
    except Exception as e:
        logger.warning(f"Player tracking failed: {e}")
        return {"summary": "Player tracking unavailable", "player_count": 0,
                "movement_events": [], "track_summaries": []}
