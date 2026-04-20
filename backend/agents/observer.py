"""
Observer Agent — generates a scouting-focused event log from video.
Runs all 9 ML sources in parallel, fuses into an outlier-tagged event log.
Identical pipeline to ASC but Gemini prompt is retuned: find exceptional plays, not mistakes.
"""
import time
import logging
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from google.genai import types
from backend.agents.game_config import get_config

_TOTAL_TIMEOUT = 90

logger = logging.getLogger(__name__)


class ObserverAgent:
    def __init__(self, client, model="gemini-2.5-flash"):
        self.client = client
        self.model = model

    def run(self, clip_path: str, context: dict) -> dict:
        logger.info("  [Observer] Uploading clip to Gemini Files API...")
        uploaded = self.client.files.upload(file=clip_path, config={"mime_type": "video/mp4"})
        for _ in range(30):
            f = self.client.files.get(name=uploaded.name)
            if f.state.name == "ACTIVE":
                break
            if f.state.name == "FAILED":
                raise RuntimeError("Gemini file upload failed")
            time.sleep(3)
        else:
            raise RuntimeError("Gemini file upload timed out")

        cache_name = None
        try:
            cache = self.client.caches.create(
                model=self.model,
                config=types.CreateCachedContentConfig(
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part(
                                file_data=types.FileData(
                                    file_uri=uploaded.uri,
                                    mime_type="video/mp4"
                                )
                            )]
                        )
                    ],
                    ttl="3600s",
                    display_name=f"pf-video-{uploaded.name.split('/')[-1]}",
                )
            )
            cache_name = cache.name
            logger.info(f"  [Observer] Context cache created: {cache_name}")
        except Exception as e:
            logger.warning(f"  [Observer] Context caching unavailable ({e})")

        game_cfg = get_config(context.get("game", "r6siege"))
        player   = context.get("player_handle", "the player")

        from backend.utils.twelvelabs_client import analyze_with_pegasus
        from backend.ml.yolo_analyzer import analyze_frames
        from backend.ml.whisper_transcriber import transcribe_clip
        from backend.ml.ocr_analyzer import analyze_hud
        from backend.ml.player_tracker import track_players
        from backend.ml.audio_analyzer import analyze_audio_events
        from backend.ml.clip_analyzer import analyze_clip_concepts

        # Spatial observer reused from ASC utils
        try:
            from backend.utils.nvidia_client import analyze_spatial
            has_spatial = True
        except Exception:
            has_spatial = False

        executor = ThreadPoolExecutor(max_workers=9)
        fs = {
            'gemini':  executor.submit(self._gemini_observe, uploaded, player, game_cfg, cache_name),
            'pegasus': executor.submit(analyze_with_pegasus, clip_path, context),
            'yolo':    executor.submit(analyze_frames, clip_path),
            'whisper': executor.submit(transcribe_clip, clip_path),
            'ocr':     executor.submit(analyze_hud, clip_path),
            'tracker': executor.submit(track_players, clip_path),
            'audio':   executor.submit(analyze_audio_events, clip_path),
            'clip':    executor.submit(analyze_clip_concepts, clip_path),
        }
        if has_spatial:
            fs['spatial'] = executor.submit(analyze_spatial, clip_path, context)

        concurrent.futures.wait(fs.values(), timeout=_TOTAL_TIMEOUT)
        executor.shutdown(wait=False)

        def _get(key):
            f = fs.get(key)
            if not f:
                return None
            try:
                return f.result(timeout=0) if f.done() and not f.cancelled() else None
            except Exception:
                return None

        gemini_log     = _get('gemini')
        pegasus_result = _get('pegasus')
        spatial_log    = _get('spatial')
        yolo_result    = _get('yolo')
        whisper_result = _get('whisper')
        ocr_result     = _get('ocr')
        tracker_result = _get('tracker')
        audio_result   = _get('audio')
        clip_result    = _get('clip')

        # Track which sensors actually returned usable data
        sensor_status = {
            'gemini':  bool(gemini_log),
            'pegasus': bool(isinstance(pegasus_result, dict) and pegasus_result.get('summary')),
            'yolo':    bool(yolo_result and yolo_result.get('frames')),
            'whisper': bool(whisper_result and whisper_result.get('available')),
            'ocr':     bool(ocr_result and (ocr_result.get('kills') or ocr_result.get('summary'))),
            'tracker': bool(tracker_result and tracker_result.get('summary')),
            'audio':   bool(audio_result and audio_result.get('events')),
            'clip':    bool(clip_result and clip_result.get('summary')),
            'spatial': bool(spatial_log),
        }
        sensors_active = sum(sensor_status.values())
        sensors_total  = len(sensor_status)

        yolo_summary = ""
        if yolo_result and yolo_result.get("frames"):
            hints = yolo_result.get("event_hints", [])
            peak  = yolo_result.get("peak_player_count", 0)
            yolo_summary = (
                f"Peak players detected in single frame: {peak}\n"
                + ("\n".join(f"- {h}" for h in hints) if hints else "- No notable patterns detected")
            )

        whisper_summary = ""
        if whisper_result and whisper_result.get("available"):
            transcript = whisper_result.get("transcript", "")
            lang       = whisper_result.get("language", "")
            whisper_summary = f"[Language: {lang}]\n{transcript}" if transcript else ""

        event_log = {
            "gemini_log":         gemini_log or "",
            "pegasus_summary":    pegasus_result.get("summary", "") if isinstance(pegasus_result, dict) else "",
            "spatial_log":        spatial_log or "",
            "yolo_summary":       yolo_summary,
            "yolo_frames":        yolo_result.get("frames", []) if yolo_result else [],
            "whisper_transcript": whisper_summary,
            "ocr_summary":        ocr_result.get("summary", "") if ocr_result else "",
            "ocr_kills":          ocr_result.get("kills", []) if ocr_result else [],
            "ocr_scores":         ocr_result.get("scores", []) if ocr_result else [],
            "tracker_summary":    tracker_result.get("summary", "") if tracker_result else "",
            "tracker_events":     tracker_result.get("movement_events", []) if tracker_result else [],
            "audio_summary":      audio_result.get("summary", "") if audio_result else "",
            "audio_events":       audio_result.get("events", []) if audio_result else [],
            "clip_summary":       clip_result.get("summary", "") if clip_result else "",
            "clip_concepts":      clip_result.get("frame_concepts", []) if clip_result else [],
            "clip_actions":       clip_result.get("dominant_actions", []) if clip_result else [],
            "player_handle":      player,
            "game":               context.get("game", "r6siege"),
            "sensor_status":      sensor_status,
            "sensors_active":     sensors_active,
            "sensors_total":      sensors_total,
        }

        active_names = [k for k, v in sensor_status.items() if v]
        failed_names = [k for k, v in sensor_status.items() if not v]
        logger.info(
            f"  [Observer] {sensors_active}/{sensors_total} sensors active — "
            f"OK: {', '.join(active_names) or 'none'} | "
            f"Failed: {', '.join(failed_names) or 'none'}"
        )

        return {"uploaded_file": uploaded, "cache_name": cache_name, "event_log": event_log}

    def _gemini_observe(self, uploaded_file, player: str, game_cfg: dict,
                        cache_name: str | None) -> str:
        scouting_context = game_cfg.get("scouting_context", "")
        prompt = (
            f"{scouting_context}\n\n"
            f"You are watching footage of player '{player}'.\n\n"
            f"Produce a timestamped event log focused on EXCEPTIONAL plays.\n"
            f"For each notable moment include:\n"
            f"- [Xs] What happened (factual description)\n"
            f"- [OUTLIER] tag if this play is statistically rare or particularly skilled\n"
            f"- The action category: KILL / UTILITY / CLUTCH / POSITIONING / CALLOUT\n\n"
            f"Rules:\n"
            f"- Do NOT flag routine plays\n"
            f"- Do NOT assign blame or note mistakes\n"
            f"- Flag only plays that would make a scout take notice\n"
            f"- Use format: [Xs] [CATEGORY] [OUTLIER?] <description>"
        )
        cfg = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=1024)
        )
        if cache_name:
            cfg = types.GenerateContentConfig(
                cached_content=cache_name,
                thinking_config=types.ThinkingConfig(thinking_budget=1024)
            )
            response = self.client.models.generate_content(
                model=self.model, contents=[prompt], config=cfg
            )
        else:
            response = self.client.models.generate_content(
                model=self.model, contents=[uploaded_file, prompt], config=cfg
            )
        return response.text
