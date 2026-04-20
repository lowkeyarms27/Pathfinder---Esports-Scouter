"""
CLIP Visual Analyzer — zero-shot tactical concept detection and temporal action
recognition using OpenAI CLIP (via HuggingFace Transformers).

Also serves as the VideoMAE/TimeSformer stand-in: CLIP applied across a frame
sequence gives temporal action classification without requiring a fine-tuned
video model on game footage.
"""
import logging
import cv2
import numpy as np
from collections import Counter

logger = logging.getLogger(__name__)

_model = None
_processor = None

# Zero-shot tactical situation labels
TACTICAL_CONCEPTS = [
    "team fight with multiple players engaged simultaneously",
    "single player clutch 1v1 or 1vN situation",
    "players holding static defensive position",
    "aggressive push or rush attack through chokepoint",
    "players rotating or repositioning to new area",
    "utility usage grenade smoke flashbang ability activation",
    "player death or elimination event",
    "calm setup phase no active combat",
    "players splitting across multiple locations",
    "players grouped and stacking together",
]

# Temporal action phase labels (TimeSformer-style action recognition)
ACTION_PHASES = [
    "attacking pushing aggressively into enemy territory",
    "defending holding position passively waiting",
    "rotating repositioning moving to different area of map",
    "actively engaging in combat firefight shooting",
    "setup phase slow methodical preparation before fight",
    "objective secured post-plant execution",
    "endgame low player count final moments clutch",
]


def _get_model():
    global _model, _processor
    if _model is None:
        from transformers import CLIPModel, CLIPProcessor
        import torch
        logger.info("  [CLIP] Loading openai/clip-vit-base-patch32...")
        _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _model.eval()
        if torch.cuda.is_available():
            _model = _model.cuda()
            logger.info("  [CLIP] Model loaded (GPU)")
        else:
            logger.info("  [CLIP] Model loaded (CPU)")
    return _model, _processor


def _extract_frames(clip_path: str, count: int = 8) -> list:
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
            # BGR -> RGB for PIL
            frames.append((round(ts, 1), cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
    cap.release()
    return frames


def _score_frame(pil_img, texts: list, model, processor, device) -> np.ndarray:
    import torch
    inputs = processor(text=texts, images=pil_img, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)[0].cpu().numpy()
    return probs


def analyze_clip_concepts(clip_path: str, n_frames: int = 8) -> dict:
    """
    Run CLIP across key frames for:
    1. Zero-shot tactical concept detection per frame
    2. Temporal action phase classification (TimeSformer-style via frame sequence)
    """
    try:
        from PIL import Image
        model, processor = _get_model()
        device = next(model.parameters()).device
        frames = _extract_frames(clip_path, count=n_frames)

        if not frames:
            return {"summary": "No frames for CLIP analysis", "frame_concepts": [], "dominant_actions": []}

        frame_concepts = []
        action_sequence = []

        for ts, frame_rgb in frames:
            pil_img = Image.fromarray(frame_rgb)

            concept_probs = _score_frame(pil_img, TACTICAL_CONCEPTS, model, processor, device)
            action_probs  = _score_frame(pil_img, ACTION_PHASES,     model, processor, device)

            top_c_idx  = int(np.argmax(concept_probs))
            top_a_idx  = int(np.argmax(action_probs))

            frame_concepts.append({
                "timestamp":          ts,
                "top_concept":        TACTICAL_CONCEPTS[top_c_idx],
                "concept_confidence": round(float(concept_probs[top_c_idx]), 3),
                "top_action":         ACTION_PHASES[top_a_idx],
                "action_confidence":  round(float(action_probs[top_a_idx]), 3),
            })
            action_sequence.append((ts, ACTION_PHASES[top_a_idx]))

        # Temporal narrative: emit action label only when it changes
        timeline = []
        prev = None
        for ts, action in action_sequence:
            short = action.split()[0].capitalize()
            if action != prev:
                timeline.append(f"{ts}s:{short}")
                prev = action

        dominant = Counter(a for _, a in action_sequence).most_common(3)

        summary = (
            f"CLIP temporal analysis — {' → '.join(timeline)}. "
            f"Dominant phase: {dominant[0][0].split()[0] if dominant else 'unknown'}"
        )

        return {
            "summary": summary,
            "frame_concepts": frame_concepts,
            "dominant_actions": [{"action": a, "frame_count": c} for a, c in dominant],
            "action_timeline": timeline,
        }
    except Exception as e:
        logger.warning(f"CLIP analysis failed: {e}")
        return {"summary": "CLIP analysis unavailable", "frame_concepts": [], "dominant_actions": []}
