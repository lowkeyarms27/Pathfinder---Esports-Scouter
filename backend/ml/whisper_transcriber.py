"""
Whisper Transcriber — uses OpenAI Whisper (PyTorch) to transcribe
audio from gameplay clips.

Extracts the audio track via ffmpeg then runs Whisper tiny for fast
CPU inference. The transcript is injected into the ObserverAgent's
event log so downstream agents can cross-reference callouts, reactions,
and communication patterns with the visual analysis.
"""
import os
import logging
import tempfile
import subprocess

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        import whisper
        logger.info("  [Whisper] Loading tiny model...")
        _model = whisper.load_model("tiny")
        logger.info("  [Whisper] Model ready.")
    return _model


def transcribe_clip(clip_path: str) -> dict:
    """
    Extract audio from clip and transcribe with Whisper tiny.

    Returns:
        {
          "transcript": "full text",
          "segments": [{"start": 0.0, "end": 2.4, "text": "rotate now"}],
          "language": "en",
          "available": True
        }
    On failure returns {"available": False, "transcript": "", "segments": []}
    """
    audio_path = None
    try:
        model = _get_model()
    except Exception as e:
        logger.warning(f"  [Whisper] Model load failed: {e}")
        return {"available": False, "transcript": "", "segments": []}

    try:
        # Extract audio to a temp WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_path = tmp.name

        result = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", clip_path, "-vn", "-ar", "16000", "-ac", "1",
             "-f", "wav", audio_path],
            capture_output=True, timeout=60
        )
        if result.returncode != 0 or not os.path.exists(audio_path):
            return {"available": False, "transcript": "", "segments": []}

        # Check audio has actual content (>10KB)
        if os.path.getsize(audio_path) < 10_000:
            return {"available": False, "transcript": "", "segments": []}

        logger.info("  [Whisper] Transcribing audio...")
        output = model.transcribe(audio_path, fp16=False, language=None,
                                  condition_on_previous_text=False)

        segments = [
            {"start": round(s["start"], 1), "end": round(s["end"], 1),
             "text": s["text"].strip()}
            for s in output.get("segments", [])
            if s["text"].strip()
        ]

        transcript = output.get("text", "").strip()
        language   = output.get("language", "unknown")

        logger.info(f"  [Whisper] Transcribed {len(segments)} segment(s) [{language}]")
        return {"available": True, "transcript": transcript,
                "segments": segments, "language": language}

    except Exception as e:
        logger.warning(f"  [Whisper] Transcription failed: {e}")
        return {"available": False, "transcript": "", "segments": []}

    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except Exception:
                pass
