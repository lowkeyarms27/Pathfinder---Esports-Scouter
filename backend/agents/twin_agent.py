"""
Twin Agent — finds the closest pro player match for an amateur's style vector.

Uses cosine similarity against the pro archetype library (DB + JSON file).
Returns the best match + similarity score + a narrative comparison.
"""
import json
import logging
import numpy as np
from pathlib import Path
from backend.database import get_all_pro_archetypes
from backend.agents.profiler import _STYLE_DIMENSIONS
from backend.config import ARCHETYPES_PATH

logger = logging.getLogger(__name__)

# Dims that sixstats.cc populates with real tournament data.
# The other 5 (utility_priority, flank_frequency, comms_density,
# position_variance, operator_diversity) stay at role-template defaults.
_SIXSTATS_DIMS = frozenset({
    "aggression", "reaction_speed", "entry_success_rate", "clutch_rate",
    "first_duel_rate", "utility_enable_rate", "trade_efficiency",
    "site_presence", "calm_under_pressure", "info_play_rate",
})


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a, b = np.array(a), np.array(b)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def _vector_to_list(v: dict, dims: list[str]) -> list[float]:
    return [float(v.get(dim, 0.5)) for dim in dims]


def _get_comparison_dims(events: int) -> list[str]:
    """Use only real-data dims for enriched pros; fall back to all 15 for template-only."""
    if events >= 2:
        return [d for d in _STYLE_DIMENSIONS if d in _SIXSTATS_DIMS]
    return list(_STYLE_DIMENSIONS)


def _event_confidence(events: int) -> float:
    """0.70 for template-only pros, scaling to 1.0 at 10+ events."""
    return 0.70 + 0.30 * min(events / 10.0, 1.0)


def _normalize_role(role: str) -> str:
    role = (role or "").strip().title()
    for key, canonical in [
        ("Entry", "Entry Fragger"), ("Fragger", "Entry Fragger"),
        ("Anchor", "Anchor"), ("Roam", "Roamer"),
        ("Hard Breach", "Hard Breach"), ("Breach", "Hard Breach"),
        ("Support", "Support"), ("Igl", "IGL"), ("Flex", "Flex"),
    ]:
        if key in role:
            return canonical
    return role


class TwinAgent:
    def __init__(self, client=None):
        self.client = client

    def run(self, profile: dict) -> dict:
        style_vector = profile.get("style_vector", {})
        archetype    = profile.get("archetype", "")

        pros = self._load_pros()
        if not pros:
            logger.warning("  [TwinAgent] No pro archetypes loaded — returning empty match")
            return {"best_match": None, "alternatives": [], "similarity_score": 0.0}

        scored = []
        for pro in pros:
            events   = pro.get("events", 0)
            dims     = _get_comparison_dims(events)
            ama_vec  = _vector_to_list(style_vector, dims)
            pro_vec  = _vector_to_list(pro.get("style_vector", {}), dims)
            score    = _cosine_similarity(ama_vec, pro_vec)
            confidence  = _event_confidence(events)
            role_match  = _normalize_role(pro.get("role", "")) == _normalize_role(archetype)
            adjusted    = score * confidence * (1.15 if role_match else 1.0)
            scored.append({
                **pro,
                "_score":      score,
                "_adjusted":   adjusted,
                "_role_match": role_match,
                "_events":     events,
            })

        scored.sort(key=lambda x: (x["_adjusted"], x["_score"]), reverse=True)

        # Rank: position in sorted list
        for i, s in enumerate(scored):
            s["_rank"] = i + 1

        # Normalize display score across actual score range so differences are visible
        raw_scores  = [s["_score"] for s in scored]
        lo, hi      = min(raw_scores), max(raw_scores)
        score_range = (hi - lo) or 1.0
        for s in scored:
            s["_display_score"] = round((s["_score"] - lo) / score_range * 100, 1)

        best         = scored[0]
        alternatives = scored[1:4]
        n            = len(scored)

        # Dimension-level diff for the best match (use all 15 dims for narrative)
        all_dims = list(_STYLE_DIMENSIONS)
        ama_full = _vector_to_list(style_vector, all_dims)
        pro_full = _vector_to_list(best.get("style_vector", {}), all_dims)
        diff = {dim: round(ama_full[i] - pro_full[i], 3) for i, dim in enumerate(all_dims)}

        key_similarities = [dim for dim, delta in diff.items() if abs(delta) < 0.15][:5]
        key_gaps         = [dim for dim, delta in diff.items() if delta < -0.25][:3]

        result = {
            "best_match": {
                "handle":      best.get("handle"),
                "team":        best.get("team"),
                "role":        best.get("role"),
                "nationality": best.get("nationality"),
                "source_url":  best.get("source_url"),
                "events":      best.get("_events", 0),
            },
            "similarity_score": round(best["_score"] * 100, 1),   # raw cosine × 100
            "display_score":    best["_display_score"],             # normalized 0–100 across library
            "rank":             best["_rank"],
            "total_pros":       n,
            "role_match":       best.get("_role_match", False),
            "key_similarities": key_similarities,
            "key_gaps":         key_gaps,
            "dimension_diff":   diff,
            "alternatives": [
                {
                    "handle":           a.get("handle"),
                    "team":             a.get("team"),
                    "role":             a.get("role"),
                    "similarity_score": round(a["_score"] * 100, 1),
                    "display_score":    a["_display_score"],
                    "rank":             a["_rank"],
                }
                for a in alternatives
            ],
            "narrative": self._build_narrative(profile, best, key_similarities, key_gaps),
        }

        logger.info(
            f"  [TwinAgent] Best match: {best.get('handle')} ({best.get('team')}) "
            f"— #{best['_rank']} of {n} | raw={result['similarity_score']}% | "
            f"display={result['display_score']}% | events={best.get('_events', 0)}"
        )
        return result

    def _load_pros(self) -> list[dict]:
        pros = get_all_pro_archetypes()
        if pros:
            return pros
        try:
            if ARCHETYPES_PATH.exists():
                with open(ARCHETYPES_PATH) as f:
                    data = json.load(f)
                return [p for p in data if isinstance(p, dict)]
        except Exception as e:
            logger.warning(f"  [TwinAgent] Could not load archetypes JSON: {e}")
        return []

    def _build_narrative(self, profile: dict, best_pro: dict,
                         similarities: list[str], gaps: list[str]) -> str:
        handle     = profile.get("player_handle", "This player")
        archetype  = profile.get("archetype", "player")
        pro_handle = best_pro.get("handle", "an unknown pro")
        pro_team   = best_pro.get("team", "")
        pro_role   = best_pro.get("role", "")

        sim_str = ", ".join(s.replace("_", " ") for s in similarities[:3]) if similarities else "general style"
        gap_str = ", ".join(g.replace("_", " ") for g in gaps[:2]) if gaps else None

        narrative = (
            f"{handle} plays as a {archetype.lower()}, showing strong stylistic alignment "
            f"with {pro_handle} ({pro_team}, {pro_role}). "
            f"Shared strengths: {sim_str}."
        )
        if gap_str:
            narrative += f" Areas where the pro pulls ahead: {gap_str}."

        traits = profile.get("traits", [])
        if traits:
            narrative += f" Scout note: {traits[0]}"

        return narrative
