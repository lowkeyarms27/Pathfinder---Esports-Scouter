"""
Profiler Agent — fuses the 9 ML sources into a Stylistic DNA profile.

Input:  raw event_log from Observer
Output: {
    archetype: str,
    style_vector: dict[str, float],   # 15 normalized dimensions
    highlight_timestamps: list[float],
    traits: list[str],
    raw_analysis: str
}
"""
import json
import logging
from google.genai import types
from backend.agents.game_config import get_config
from backend.utils.gemini_client import _extract_json

logger = logging.getLogger(__name__)

_STYLE_DIMENSIONS = [
    "aggression",           # 0=passive anchor, 1=entry fragger
    "utility_priority",     # 0=ignores utility, 1=utility-first
    "clutch_rate",          # frequency of 1vX attempts (from ocr/gemini)
    "reaction_speed",       # sub-200ms engagements (audio spike → yolo kill)
    "flank_frequency",      # roamer behavior (tracker movement events)
    "first_duel_rate",      # takes first contact in round
    "comms_density",        # callout volume per round (whisper)
    "position_variance",    # how often player holds different angles (tracker)
    "trade_efficiency",     # kills that are trades vs. solo picks
    "site_presence",        # time spent in objective zone (tracker)
    "operator_diversity",   # breadth of operator pool (gemini/ocr)
    "info_play_rate",       # plays driven by drone/callout intel (gemini)
    "entry_success_rate",   # first-duel win rate (yolo + gemini)
    "utility_enable_rate",  # utility that directly precedes a kill (spatial + gemini)
    "calm_under_pressure",  # comms density stays high in 1vX (whisper + audio)
]


class ProfilerAgent:
    def __init__(self, client, model="gemini-2.5-flash"):
        self.client = client
        self.model = model

    def run(self, uploaded_file, event_log: dict, context: dict,
            cache_name: str | None = None) -> dict:
        game_cfg  = get_config(context.get("game", "r6siege"))
        player    = event_log.get("player_handle", "the player")
        archetypes = game_cfg["archetypes"]

        # Build a compact summary of all ML sources for the LLM
        ml_summary = self._build_ml_summary(event_log)

        prompt = (
            f"{game_cfg['role_knowledge']}\n\n"
            f"You are profiling player '{player}' for talent scouting.\n\n"
            f"=== ML SENSOR DATA ===\n{ml_summary}\n\n"
            f"=== EVENT LOG (Gemini observation) ===\n{event_log.get('gemini_log', '')}\n\n"
            f"Tasks:\n"
            f"1. Assign the player ONE primary archetype from: {', '.join(archetypes)}\n"
            f"2. Score each of the 15 style dimensions 0.0–1.0:\n"
            f"   {chr(10).join(f'   - {d}' for d in _STYLE_DIMENSIONS)}\n"
            f"3. List the 3 most notable highlight timestamps from the event log\n"
            f"4. Write 3–5 one-sentence scouting traits (e.g. 'Wins first duels at 63% on aggressive angles')\n\n"
            f"Respond ONLY with valid JSON:\n"
            f'{{\n'
            f'  "archetype": "Entry Fragger",\n'
            f'  "style_vector": {{"aggression": 0.9, "utility_priority": 0.3, ...}},\n'
            f'  "highlight_timestamps": [12.5, 47.0, 89.3],\n'
            f'  "traits": ["Takes first duels proactively", ...],\n'
            f'  "raw_analysis": "2-3 sentence summary for scouts"\n'
            f'}}'
        )

        cfg = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=4000)
        )
        if cache_name:
            cfg = types.GenerateContentConfig(
                cached_content=cache_name,
                thinking_config=types.ThinkingConfig(thinking_budget=4000)
            )
            response = self.client.models.generate_content(
                model=self.model, contents=[prompt], config=cfg
            )
        else:
            response = self.client.models.generate_content(
                model=self.model, contents=[uploaded_file, prompt], config=cfg
            )

        parsed = _extract_json(response.text)
        if not isinstance(parsed, dict):
            logger.warning("  [Profiler] Could not parse JSON — using fallback profile")
            parsed = {}

        # Normalize style_vector to ensure all 15 dimensions are present
        raw_vector = parsed.get("style_vector", {})
        style_vector = {dim: float(raw_vector.get(dim, 0.5)) for dim in _STYLE_DIMENSIONS}

        result = {
            "archetype":             parsed.get("archetype", "Unknown"),
            "style_vector":          style_vector,
            "highlight_timestamps":  parsed.get("highlight_timestamps", []),
            "traits":                parsed.get("traits", []),
            "raw_analysis":          parsed.get("raw_analysis", ""),
        }

        logger.info(
            f"  [Profiler] Archetype: {result['archetype']} | "
            f"Highlights: {len(result['highlight_timestamps'])} | "
            f"Traits: {len(result['traits'])}"
        )
        return result

    def _build_ml_summary(self, event_log: dict) -> str:
        parts = []
        if event_log.get("yolo_summary"):
            parts.append(f"YOLO (object detection):\n{event_log['yolo_summary']}")
        if event_log.get("tracker_summary"):
            parts.append(f"ByteTrack (movement):\n{event_log['tracker_summary']}")
        if event_log.get("whisper_transcript"):
            parts.append(f"Whisper (comms):\n{event_log['whisper_transcript'][:500]}")
        if event_log.get("audio_summary"):
            parts.append(f"Librosa (audio events):\n{event_log['audio_summary']}")
        if event_log.get("ocr_summary"):
            parts.append(f"OCR (HUD):\n{event_log['ocr_summary']}")
        if event_log.get("clip_summary"):
            parts.append(f"CLIP (visual concepts):\n{event_log['clip_summary']}")
        if event_log.get("spatial_log"):
            parts.append(f"NVIDIA Cosmos (spatial):\n{str(event_log['spatial_log'])[:300]}")
        if event_log.get("pegasus_summary"):
            parts.append(f"Twelve Labs Pegasus:\n{event_log['pegasus_summary']}")
        return "\n\n".join(parts) if parts else "No ML sensor data available."
