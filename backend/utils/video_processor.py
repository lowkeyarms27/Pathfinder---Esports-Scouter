import subprocess
import os
import json
import base64
import tempfile


def get_clip_duration(video_path: str) -> float:
    """Return duration in seconds using ffprobe. Returns 0.0 on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", video_path
            ],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 0.0


def extract_frame_b64(video_path: str, timestamp: float) -> str | None:
    """Extract a single frame at timestamp as a base64-encoded JPEG string."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-ss", str(timestamp), "-i", video_path,
             "-vframes", "1", "-q:v", "2", tmp_path],
            check=True, capture_output=True, timeout=15
        )
        with open(tmp_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        os.unlink(tmp_path)
        return data
    except Exception:
        return None


def extract_key_frames_b64(video_path: str, count: int = 6) -> list[str]:
    """
    Extract `count` evenly-spaced frames from the clip as base64 JPEGs.
    Used to give vision models a representative sample of the full clip.
    """
    duration = get_clip_duration(video_path)
    if duration <= 0:
        return []
    interval = duration / (count + 1)
    frames = []
    for i in range(1, count + 1):
        ts = interval * i
        frame = extract_frame_b64(video_path, ts)
        if frame:
            frames.append(frame)
    return frames


def extract_clip(video_path: str, start_seconds: float, end_seconds: float, output_path: str, from_vod: bool = True) -> str:
    duration = max(1, end_seconds - start_seconds)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if from_vod:
        # Fast seek before input (keyframe-accurate, slight drift possible)
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", str(start_seconds), "-i", video_path, "-t", str(duration), "-c", "copy", output_path]
    else:
        # Seek after input (frame-accurate, slower) — used when clipping within a clip
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", video_path, "-ss", str(start_seconds), "-t", str(duration), "-c", "copy", output_path]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed to extract clip: {e}")
