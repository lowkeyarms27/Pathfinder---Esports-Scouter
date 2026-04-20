"""
NVIDIA NIM client for ASC.

Wraps three NVIDIA models accessed via the OpenAI-compatible NIM API:
  - cosmos-reason2-8b    → spatial/physical world reasoning from video frames
  - nemotron-nano-12b-v2-vl → multi-image visual Q&A for Critic verification
  - cosmos-predict1-5b   → future-frame prediction for Scenario Agent

All models require NVIDIA_API_KEY in the environment.
Install dependency: pip install openai
"""
import os
import logging
import requests as _requests

logger = logging.getLogger(__name__)

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"

COSMOS_REASON  = "nvidia/cosmos-reason2-8b"
NEMOTRON_NANO  = "nvidia/nemotron-nano-12b-v2-vl"
COSMOS_PREDICT = "nvidia/cosmos-predict1-5b"


def _get_client():
    from openai import OpenAI
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY not set")
    return OpenAI(base_url=NIM_BASE_URL, api_key=api_key)


def _image_content(b64_jpeg: str) -> dict:
    return {
        "type":      "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{b64_jpeg}"}
    }


def analyze_spatial(frames_b64: list[str], prompt: str) -> str | None:
    """
    cosmos-reason2-8b — spatial/physical world reasoning over video frames.
    Frames are evenly-spaced samples from the clip.
    Returns: structured spatial analysis text, or None on failure.
    """
    if not frames_b64:
        return None
    try:
        client = _get_client()
        content = [_image_content(f) for f in frames_b64]
        content.append({"type": "text", "text": prompt})
        response = client.chat.completions.create(
            model=COSMOS_REASON,
            messages=[{"role": "user", "content": content}],
            max_tokens=1024,
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"[NVIDIA cosmos-reason2-8b] Failed: {e}")
        return None


def verify_frame(frames_b64: list[str], question: str) -> str | None:
    """
    nemotron-nano-12b-v2-vl — multi-image visual Q&A.
    Used by Critic to visually verify contested findings at specific timestamps.
    Returns: factual answer to the question, or None on failure.
    """
    if not frames_b64:
        return None
    try:
        client = _get_client()
        content = [_image_content(f) for f in frames_b64]
        content.append({"type": "text", "text": question})
        response = client.chat.completions.create(
            model=NEMOTRON_NANO,
            messages=[{"role": "user", "content": content}],
            max_tokens=512,
            temperature=0.1,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.warning(f"[NVIDIA nemotron-nano] Failed: {e}")
        return None


def predict_scenario(clip_path: str, correction_prompt: str) -> str | None:
    """
    cosmos-predict1-5b — physics-aware future-frame prediction.
    Given the moment of a mistake, predicts what the alternative would look like.
    Returns: description of predicted outcome, or None on failure.

    Note: cosmos-predict1-5b uses a multipart REST endpoint (not chat).
    The response is a text description of the predicted world state.
    """
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        return None
    try:
        with open(clip_path, "rb") as f:
            video_bytes = f.read()

        # cosmos-predict1-5b REST endpoint
        resp = _requests.post(
            "https://ai.api.nvidia.com/v1/cv/nvidia/cosmos-predict1-5b",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept":        "application/json",
            },
            json={
                "input":  {"video": clip_path},
                "prompt": correction_prompt,
            },
            timeout=120
        )
        if resp.ok:
            data = resp.json()
            return data.get("output", {}).get("description") or data.get("text", "")
        logger.warning(f"[NVIDIA cosmos-predict] HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        logger.warning(f"[NVIDIA cosmos-predict1-5b] Failed: {e}")
        return None
