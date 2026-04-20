"""
Audio Event Analyzer — detects non-speech game audio events (gunshots, explosions,
ability sounds) using librosa onset detection and spectral analysis.
"""
import logging
import os
import tempfile
import subprocess
import numpy as np

logger = logging.getLogger(__name__)


def _extract_audio(clip_path: str, tmp_path: str) -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", clip_path,
             "-ac", "1", "-ar", "22050", "-vn", tmp_path],
            capture_output=True, timeout=120,
        )
        return result.returncode == 0 and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0
    except Exception as e:
        logger.warning(f"Audio extraction failed: {e}")
        return False


def analyze_audio_events(clip_path: str) -> dict:
    """Detect timestamped audio events in a game clip using librosa."""
    try:
        import librosa
    except ImportError:
        logger.warning("librosa not installed — audio analysis unavailable")
        return {"summary": "Audio analysis unavailable (librosa missing)", "events": []}

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        if not _extract_audio(clip_path, tmp_path):
            return {"summary": "Could not extract audio track", "events": []}

        y, sr = librosa.load(tmp_path, sr=22050, mono=True)
        if len(y) == 0:
            return {"summary": "No audio content found", "events": []}

        duration = len(y) / sr

        # Onset strength — measures rate of energy increase (sharp transients = gunshots etc.)
        hop = 512
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
        times = librosa.times_like(onset_env, sr=sr, hop_length=hop)

        # Adaptive threshold: mean + 2σ
        threshold = float(np.mean(onset_env) + 2.0 * np.std(onset_env))

        # Peak detection using local maxima
        peaks = _find_peaks(onset_env, threshold=threshold, min_distance_frames=int(sr / hop * 0.25))

        # Spectral centroid — distinguishes sharp (high Hz = gunshot) from low (explosion)
        spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop)[0]
        cent_times = librosa.times_like(spec_centroid, sr=sr, hop_length=hop)

        # RMS energy for loudness context
        rms = librosa.feature.rms(y=y, hop_length=hop)[0]
        rms_times = librosa.times_like(rms, sr=sr, hop_length=hop)

        events = []
        for peak_idx in peaks:
            ts = float(times[peak_idx])
            energy = float(onset_env[peak_idx])

            # Nearest centroid and rms values
            ci = int(np.argmin(np.abs(cent_times - ts)))
            ri = int(np.argmin(np.abs(rms_times - ts)))
            centroid = float(spec_centroid[ci])
            loudness = float(rms[ri])

            if centroid > 3500:
                label = "sharp_transient"      # gunshot / click
            elif centroid > 1500:
                label = "mid_transient"        # ability / impact
            else:
                label = "low_transient"        # explosion / bass event

            events.append({
                "timestamp": round(ts, 1),
                "energy": round(energy, 2),
                "spectral_centroid_hz": round(centroid),
                "rms_loudness": round(loudness, 4),
                "label": label,
            })

        sharp = sum(1 for e in events if e["label"] == "sharp_transient")
        mid   = sum(1 for e in events if e["label"] == "mid_transient")
        low   = sum(1 for e in events if e["label"] == "low_transient")

        summary = (
            f"{len(events)} audio events in {duration:.0f}s: "
            f"{sharp} sharp (gunshots?), {mid} mid-impact (abilities?), {low} low-rumble (explosions?)"
            if events else f"No significant audio events in {duration:.0f}s clip"
        )

        return {
            "summary": summary,
            "events": events[:30],
            "duration_s": round(duration, 1),
            "total_spikes": len(events),
        }
    except Exception as e:
        logger.warning(f"Audio event analysis failed: {e}")
        return {"summary": "Audio analysis failed", "events": []}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def _find_peaks(array: np.ndarray, threshold: float, min_distance_frames: int) -> list:
    """Simple local-maxima peak finder without scipy dependency."""
    peaks = []
    n = len(array)
    last_peak = -min_distance_frames
    for i in range(1, n - 1):
        if array[i] > threshold and array[i] >= array[i - 1] and array[i] >= array[i + 1]:
            if i - last_peak >= min_distance_frames:
                peaks.append(i)
                last_peak = i
    return peaks
