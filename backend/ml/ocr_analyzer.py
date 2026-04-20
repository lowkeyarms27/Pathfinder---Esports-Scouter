"""
HUD OCR Analyzer — reads kill feed, scoreboard, and timer text from key frames using EasyOCR.
"""
import logging
import re
import cv2
import numpy as np

logger = logging.getLogger(__name__)

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr
        logger.info("  [OCR] Loading EasyOCR (en)...")
        _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        logger.info("  [OCR] EasyOCR ready")
    return _reader


def _extract_frames(clip_path: str, count: int = 6) -> list:
    cap = cv2.VideoCapture(clip_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    duration = total / fps
    frames = []
    for i in range(count):
        ts = duration * (i + 0.5) / count
        cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
        ret, frame = cap.read()
        if ret:
            frames.append((round(ts, 1), frame))
    cap.release()
    return frames


def _classify_detection(bbox, text: str, conf: float, h: int, w: int) -> tuple:
    """Return (category, position_ratio) for a detected text box."""
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    cx = sum(xs) / 4 / w
    cy = sum(ys) / 4 / h

    if re.match(r"^\d{1,2}:\d{2}$", text) and cy < 0.15 and 0.3 < cx < 0.7:
        return "timer", (cx, cy)
    if re.match(r"^\d+\s*[-:]\s*\d+$", text) and cy < 0.2:
        return "score", (cx, cy)
    if cx > 0.55 and cy < 0.35 and len(text) > 2:
        return "kill_feed", (cx, cy)
    if cy < 0.12 and len(text) >= 2:
        return "top_hud", (cx, cy)
    return "misc", (cx, cy)


def analyze_hud(clip_path: str, n_frames: int = 6) -> dict:
    """Extract and parse HUD information from key frames using OCR."""
    try:
        reader = _get_reader()
        frames = _extract_frames(clip_path, count=n_frames)

        kills, scores, timers = [], [], []
        seen = set()

        for ts, frame in frames:
            h, w = frame.shape[:2]
            if w > 1280:
                scale = 1280 / w
                frame = cv2.resize(frame, (1280, int(h * scale)))
                h, w = frame.shape[:2]

            detections = reader.readtext(frame)
            for bbox, text, conf in detections:
                if conf < 0.45 or not text.strip():
                    continue
                text = text.strip()
                key = text.lower()
                category, pos = _classify_detection(bbox, text, conf, h, w)

                if category == "timer" and key not in seen:
                    seen.add(key)
                    timers.append({"text": text, "timestamp": ts, "conf": round(conf, 2)})
                elif category == "score" and key not in seen:
                    seen.add(key)
                    scores.append({"text": text, "timestamp": ts, "conf": round(conf, 2)})
                elif category == "kill_feed" and key not in seen:
                    seen.add(key)
                    kills.append({"text": text, "timestamp": ts, "conf": round(conf, 2)})

        parts = []
        if kills:
            parts.append(f"{len(kills)} kill-feed entries: {'; '.join(k['text'] for k in kills[:5])}")
        if scores:
            parts.append(f"scores: {', '.join(s['text'] for s in scores[:4])}")
        if timers:
            parts.append(f"timers: {', '.join(t['text'] for t in timers[:4])}")

        summary = "; ".join(parts) if parts else "No HUD text detected"
        return {
            "summary": summary,
            "kills": kills[:15],
            "scores": scores[:8],
            "timers": timers[:8],
        }
    except Exception as e:
        logger.warning(f"HUD OCR failed: {e}")
        return {"summary": "OCR unavailable", "kills": [], "scores": [], "timers": []}
