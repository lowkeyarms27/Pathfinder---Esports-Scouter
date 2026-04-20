"""
Pathfinder Orchestrator — runs the scouting pipeline.

Pipeline:
  1. Observer     → 9 parallel ML sources → scouting event log
  2. Profiler     → stylistic DNA + style vector
  3. TwinAgent    → pro comparison via cosine similarity
  4. ValueCritic  → market value + recommendation
"""
import os
import json
import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from google import genai

# Load .env here so the key is available regardless of how uvicorn was launched
_env = Path(__file__).resolve().parent.parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ[_k.strip()] = _v.strip()

from backend.agents.observer import ObserverAgent
from backend.agents.profiler import ProfilerAgent, _STYLE_DIMENSIONS
from backend.agents.twin_agent import TwinAgent
from backend.agents.value_critic import ValueCriticAgent

logger = logging.getLogger(__name__)


@dataclass
class ScoutingState:
    context:        dict
    uploaded_file:  object     = None
    cache_name:     str | None = None
    event_log:      dict       = field(default_factory=dict)
    profile:        dict       = field(default_factory=dict)
    twin_result:    dict       = field(default_factory=dict)
    value_result:   dict       = field(default_factory=dict)
    agent_log:      list       = field(default_factory=list)
    sensors_active: int        = 0
    sensors_total:  int        = 9
    sensor_status:  dict       = field(default_factory=dict)

    def record(self, agent: str, action: str, detail: str = ""):
        entry = {
            "agent":  agent,
            "action": action,
            "detail": detail,
            "ts":     time.time(),
        }
        self.agent_log.append(entry)
        logger.info(f"  [{agent.upper()}] {action}" + (f" — {detail}" if detail else ""))
        return entry


class Orchestrator:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set")
        self.client       = genai.Client(api_key=api_key)
        self.observer     = ObserverAgent(self.client)
        self.profiler     = ProfilerAgent(self.client)
        self.twin         = TwinAgent(self.client)
        self.value_critic = ValueCriticAgent()

    def run(self, clip_path: str, context: dict,
            log_callback=None) -> dict:
        state  = ScoutingState(context=context)
        player = context.get("player_handle", "Unknown")
        game   = context.get("game", "r6siege")
        logger.info(f"[Orchestrator] Scouting '{player}' — {game}")

        def _notify(agent, action, detail=""):
            entry = state.record(agent, action, detail)
            if log_callback:
                try:
                    log_callback(state.agent_log)
                except Exception:
                    pass
            return entry

        # Phase 1: Observe
        _notify("orchestrator", "dispatch", "ObserverAgent — building scouting event log")
        obs = self.observer.run(clip_path, context)
        state.uploaded_file  = obs["uploaded_file"]
        state.cache_name     = obs.get("cache_name")
        state.event_log      = obs["event_log"]
        state.sensors_active = state.event_log.get("sensors_active", 0)
        state.sensors_total  = state.event_log.get("sensors_total", 9)
        state.sensor_status  = state.event_log.get("sensor_status", {})
        _notify("observer", "complete",
                f"{state.sensors_active}/{state.sensors_total} sensors active | "
                f"Gemini: {len(state.event_log.get('gemini_log', ''))} chars | "
                f"Cache: {'active' if state.cache_name else 'none'}")

        # Phase 2: Profile
        _notify("orchestrator", "dispatch", "ProfilerAgent — building stylistic DNA")
        state.profile = self.profiler.run(
            state.uploaded_file, state.event_log, context,
            cache_name=state.cache_name
        )
        _notify("profiler", "complete",
                f"Archetype: {state.profile.get('archetype')} | "
                f"Highlights: {len(state.profile.get('highlight_timestamps', []))}")

        # Phase 3: Twin match
        _notify("orchestrator", "dispatch", "TwinAgent — finding pro match")
        state.twin_result = self.twin.run(state.profile)
        best = state.twin_result.get("best_match") or {}
        _notify("twin", "complete",
                f"Match: {best.get('handle')} ({best.get('team')}) — "
                f"{state.twin_result.get('similarity_score')}%")

        # Phase 4: Market value
        _notify("orchestrator", "dispatch", "ValueCritic — estimating market value")
        state.value_result = self.value_critic.run(state.profile, state.twin_result)
        _notify("value_critic", "complete",
                f"${state.value_result.get('market_value', 0):,} | "
                f"Risk: {state.value_result.get('risk_tier')} | "
                f"{state.value_result.get('recommendation')}")

        # Cleanup
        if state.uploaded_file:
            try:
                self.client.files.delete(name=state.uploaded_file.name)
            except Exception:
                pass
        if state.cache_name:
            try:
                self.client.caches.delete(name=state.cache_name)
            except Exception:
                pass

        result = self._build_result(
            context, state.profile, state.twin_result, state.value_result,
            agent_log=state.agent_log,
            sensors_active=state.sensors_active,
            sensors_total=state.sensors_total,
            sensor_status=state.sensor_status,
        )

        logger.info(
            f"[Orchestrator] Done — {player} | {result['archetype']} | "
            f"Match: {(result['pro_match'] or {}).get('handle')} | "
            f"${result['market_value']:,}"
        )
        return result

    def run_multi(self, clip_paths: list[str], context: dict,
                  log_callback=None) -> dict:
        """
        Run Observer+Profiler on each clip independently, average the style vectors,
        then run Twin+Value once on the merged profile.
        """
        state  = ScoutingState(context=context)
        player = context.get("player_handle", "Unknown")

        def _notify(agent, action, detail=""):
            entry = state.record(agent, action, detail)
            if log_callback:
                try:
                    log_callback(state.agent_log)
                except Exception:
                    pass
            return entry

        profiles = []
        all_sensors_active = []
        all_sensor_status  = {}
        for i, clip_path in enumerate(clip_paths):
            pfx = f"Clip {i+1}/{len(clip_paths)}"
            _notify("orchestrator", "dispatch", f"{pfx} — Observer")
            obs = self.observer.run(clip_path, context)
            sa = obs["event_log"].get("sensors_active", 0)
            st = obs["event_log"].get("sensors_total", 9)
            all_sensors_active.append(sa)
            for k, v in obs["event_log"].get("sensor_status", {}).items():
                all_sensor_status[k] = all_sensor_status.get(k, False) or v
            _notify("observer", "complete", f"{pfx} — {sa}/{st} sensors active")

            _notify("orchestrator", "dispatch", f"{pfx} — Profiler")
            profile = self.profiler.run(
                obs["uploaded_file"], obs["event_log"], context,
                cache_name=obs.get("cache_name")
            )
            profiles.append(profile)
            _notify("profiler", "complete", f"{pfx} — {profile.get('archetype')}")

            # Clean up Gemini resources for this clip
            try:
                self.client.files.delete(name=obs["uploaded_file"].name)
            except Exception:
                pass
            if obs.get("cache_name"):
                try:
                    self.client.caches.delete(name=obs["cache_name"])
                except Exception:
                    pass

        # Average style vectors across all clips
        merged_vector = {
            dim: round(
                sum(p.get("style_vector", {}).get(dim, 0.5) for p in profiles) / len(profiles),
                4
            )
            for dim in _STYLE_DIMENSIONS
        }

        # Archetype by majority vote
        archetype = Counter(p.get("archetype", "Unknown") for p in profiles).most_common(1)[0][0]

        merged_profile = {
            **profiles[0],
            "style_vector":   merged_vector,
            "archetype":      archetype,
            "clips_analyzed": len(profiles),
        }

        _notify("orchestrator", "dispatch", f"TwinAgent — merged profile ({len(profiles)} clips)")
        twin_result = self.twin.run(merged_profile)
        best = twin_result.get("best_match") or {}
        _notify("twin", "complete",
                f"Match: {best.get('handle')} — {twin_result.get('similarity_score')}%")

        _notify("orchestrator", "dispatch", "ValueCritic — market value")
        value_result = self.value_critic.run(merged_profile, twin_result)
        _notify("value_critic", "complete",
                f"${value_result.get('market_value', 0):,} | {value_result.get('recommendation')}")

        result = self._build_result(
            context, merged_profile, twin_result, value_result,
            agent_log=state.agent_log,
            sensors_active=round(sum(all_sensors_active) / max(len(all_sensors_active), 1)),
            sensors_total=9,
            sensor_status=all_sensor_status,
        )
        logger.info(
            f"[Orchestrator] Multi done — {player} | {len(profiles)} clips | "
            f"{result['archetype']} | Match: {(result['pro_match'] or {}).get('handle')}"
        )
        return result

    def _build_result(self, context: dict, profile: dict, twin: dict,
                      value: dict, agent_log: list = None,
                      sensors_active: int = 0, sensors_total: int = 9,
                      sensor_status: dict = None) -> dict:
        player = context.get("player_handle", "Unknown")
        game   = context.get("game", "r6siege")
        return {
            "player_handle":    player,
            "game":             game,
            "clips_analyzed":   profile.get("clips_analyzed", 1),
            "archetype":        profile.get("archetype"),
            "style_vector":     profile.get("style_vector", {}),
            "traits":           profile.get("traits", []),
            "highlights":       profile.get("highlight_timestamps", []),
            "raw_analysis":     profile.get("raw_analysis", ""),
            "pro_match":        twin.get("best_match"),
            "similarity_score": twin.get("similarity_score"),
            "display_score":    twin.get("display_score"),
            "rank":             twin.get("rank"),
            "total_pros":       twin.get("total_pros"),
            "key_similarities": twin.get("key_similarities", []),
            "key_gaps":         twin.get("key_gaps", []),
            "alternatives":     twin.get("alternatives", []),
            "twin_narrative":   twin.get("narrative", ""),
            "market_value":     value.get("market_value"),
            "market_value_low": value.get("market_value_low"),
            "market_value_high": value.get("market_value_high"),
            "risk_tier":        value.get("risk_tier"),
            "recommendation":   value.get("recommendation"),
            "value_confidence": value.get("confidence"),
            "value_reasoning":  value.get("reasoning", ""),
            "value_breakdown":  value.get("value_breakdown", {}),
            "sensors_active":   sensors_active,
            "sensors_total":    sensors_total,
            "sensor_status":    sensor_status or {},
            "_agent_log":       agent_log or [],
        }
