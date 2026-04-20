"""
YOLO Frame Analyzer — uses YOLOv8n (PyTorch) to extract structured
object-detection data from key frames in a clip.

Detects game-relevant objects (people, screens, HUD elements) and returns
a structured event list that the ObserverAgent injects into its event log.
This gives downstream agents ground-truth bounding-box data rather than
relying solely on Gemini's textual description of what it sees.
"""
import logging
import base64
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Model is loaded once and cached for the process lifetime
_model = None


def _get_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        logger.info("  [YOLO] Loading YOLOv8n model...")
        _model = YOLO("yolov8n.pt")   # downloads ~6 MB on first run
        logger.info("  [YOLO] Model ready.")
    return _model


def analyze_frames(clip_path: str, timestamps: list[float] | None = None,
                   max_frames: int = 8) -> dict:
    """
    Extract frames at key timestamps and run YOLOv8 detection on each.

    Returns:
        {
          "frames": [
            {
              "timestamp": 5.0,
              "detections": [
                {"label": "person", "confidence": 0.91, "bbox": [x1,y1,x2,y2]},
                ...
              ],
              "people_count": 3,
              "summary": "3 people visible at 5s"
            },
            ...
          ],
          "peak_player_count": 5,
          "event_hints": ["5 players visible at 10s — likely engagement",
                          "1 player at 45s — potential clutch situation"]
        }
    """
    import subprocess, tempfile, os

    try:
        model = _get_model()
    except Exception as e:
        logger.warning(f"  [YOLO] Model load failed: {e}")
        return {"frames": [], "peak_player_count": 0, "event_hints": []}

    # Get clip duration
    from backend.utils.video_processor import get_clip_duration, extract_frame_b64
    duration = get_clip_duration(clip_path)
    if duration <= 0:
        return {"frames": [], "peak_player_count": 0, "event_hints": []}

    # Build timestamps if not provided — evenly spaced
    if timestamps is None:
        step = duration / (max_frames + 1)
        timestamps = [round(step * i, 1) for i in range(1, max_frames + 1)]
    timestamps = [t for t in timestamps if 0 < t < duration][:max_frames]

    results = []
    peak = 0

    for ts in timestamps:
        frame_b64 = extract_frame_b64(clip_path, ts)
        if not frame_b64:
            continue
        try:
            # Decode b64 → temp file → YOLO
            img_bytes = base64.b64decode(frame_b64)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(img_bytes)
                tmp_path = tmp.name

            preds = model(tmp_path, verbose=False)[0]
            os.unlink(tmp_path)

            detections = []
            for box in preds.boxes:
                label = model.names[int(box.cls[0])]
                conf  = float(box.conf[0])
                if conf < 0.35:
                    continue
                x1, y1, x2, y2 = [round(float(v), 1) for v in box.xyxy[0]]
                detections.append({"label": label, "confidence": round(conf, 2),
                                   "bbox": [x1, y1, x2, y2]})

            people = sum(1 for d in detections if d["label"] == "person")
            peak   = max(peak, people)
            summary = f"{people} player(s) visible" if people else f"{len(detections)} object(s) detected"

            results.append({
                "timestamp":   ts,
                "detections":  detections,
                "people_count": people,
                "summary":     f"{summary} at {ts}s",
            })

        except Exception as e:
            logger.debug(f"  [YOLO] Frame {ts}s failed: {e}")

    # Build event hints from notable frames
    hints = []
    for r in results:
        p = r["people_count"]
        if p >= 4:
            hints.append(f"{p} players visible at {r['timestamp']}s — likely team fight")
        elif p == 1:
            hints.append(f"Only 1 player visible at {r['timestamp']}s — possible clutch/isolated position")
        elif p == 0 and r["detections"]:
            hints.append(f"No players but {len(r['detections'])} object(s) at {r['timestamp']}s — check HUD/environment")

    logger.info(f"  [YOLO] {len(results)} frames analysed | peak players: {peak} | {len(hints)} hints")
    return {"frames": results, "peak_player_count": peak, "event_hints": hints}
