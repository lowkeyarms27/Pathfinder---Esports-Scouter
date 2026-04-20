"""
Value Critic Agent — estimates market value and acquisition risk for a player.

Heuristic model (v1): weighted scoring on style dimensions + pro similarity.
ML model can replace this later once we accumulate real transfer data.

Output: {
    market_value:    int,      # USD estimate
    risk_tier:       str,      # "Low" | "Medium" | "High"
    confidence:      float,    # 0–1
    value_breakdown: dict,
    recommendation:  str,      # "Acquire Now" | "Monitor" | "Pass"
    reasoning:       str,
}
"""
import logging

logger = logging.getLogger(__name__)

# Weight each dimension's contribution to market value (sums to 1.0)
_VALUE_WEIGHTS = {
    "aggression":           0.08,
    "utility_priority":     0.07,
    "clutch_rate":          0.12,   # high weight — clutch wins rounds
    "reaction_speed":       0.10,   # high weight — measurable mechanical skill
    "flank_frequency":      0.05,
    "first_duel_rate":      0.09,
    "comms_density":        0.06,
    "position_variance":    0.04,
    "trade_efficiency":     0.07,
    "site_presence":        0.04,
    "operator_diversity":   0.05,
    "info_play_rate":       0.06,
    "entry_success_rate":   0.10,   # high weight — core combat metric
    "utility_enable_rate":  0.04,
    "calm_under_pressure":  0.03,
}

# Base salary range for Tier 2 R6 players (2026 market estimate)
_TIER2_BASE = 18_000
_TIER1_BASE = 85_000


class ValueCriticAgent:
    def run(self, profile: dict, twin_result: dict) -> dict:
        style_vector    = profile.get("style_vector", {})
        similarity      = twin_result.get("similarity_score", 0.0) / 100.0
        archetype       = profile.get("archetype", "Unknown")
        best_match      = twin_result.get("best_match") or {}

        # Weighted performance score (0–1)
        perf_score = sum(
            style_vector.get(dim, 0.5) * weight
            for dim, weight in _VALUE_WEIGHTS.items()
        )

        # Similarity bonus: closer to a top pro = higher ceiling
        similarity_bonus = similarity * 0.3

        # Combined score (0–1.3 range, clamp to 1.0)
        combined = min(perf_score + similarity_bonus, 1.0)

        # Scale to dollar value between Tier 2 base and Tier 1 base
        market_value = int(_TIER2_BASE + combined * (_TIER1_BASE - _TIER2_BASE))

        # Risk assessment
        key_gaps    = twin_result.get("key_gaps", [])
        risk_score  = len(key_gaps) * 0.2 + (1 - similarity) * 0.4
        risk_tier   = "Low" if risk_score < 0.3 else ("Medium" if risk_score < 0.6 else "High")

        # Recommendation
        if combined >= 0.75 and risk_tier == "Low":
            recommendation = "Acquire Now"
        elif combined >= 0.55:
            recommendation = "Monitor"
        else:
            recommendation = "Pass"

        # Confidence: anchored to how much real tournament data backs the pro match
        pro_events     = best_match.get("events", 0)
        data_quality   = 0.35 + 0.65 * min(pro_events / 10.0, 1.0)
        confidence     = round(data_quality * 0.6 + similarity * 0.3 + perf_score * 0.1, 2)

        # Value breakdown for UI display
        top_contributing = sorted(
            [(dim, style_vector.get(dim, 0.5) * weight)
             for dim, weight in _VALUE_WEIGHTS.items()],
            key=lambda x: x[1], reverse=True
        )[:5]

        reasoning = self._build_reasoning(
            profile, twin_result, market_value, risk_tier, recommendation,
            perf_score, similarity, key_gaps
        )

        result = {
            "market_value":      market_value,
            "market_value_low":  int(market_value * 0.72),
            "market_value_high": int(market_value * 1.32),
            "risk_tier":         risk_tier,
            "confidence":        confidence,
            "recommendation":    recommendation,
            "value_breakdown": {
                "performance_score":  round(perf_score, 3),
                "similarity_bonus":   round(similarity_bonus, 3),
                "combined_score":     round(combined, 3),
                "top_contributors":   [(d, round(v, 4)) for d, v in top_contributing],
            },
            "reasoning": reasoning,
        }

        logger.info(
            f"  [ValueCritic] ${market_value:,} | Risk: {risk_tier} | "
            f"Recommendation: {recommendation} | Confidence: {confidence:.0%}"
        )
        return result

    def _build_reasoning(self, profile: dict, twin_result: dict, market_value: int,
                          risk_tier: str, recommendation: str,
                          perf_score: float, similarity: float, key_gaps: list) -> str:
        player     = profile.get("player_handle", "This player")
        archetype  = profile.get("archetype", "player")
        pro_handle = (twin_result.get("best_match") or {}).get("handle", "a top pro")
        pro_team   = (twin_result.get("best_match") or {}).get("team", "")

        r = (
            f"{player} is estimated at ${market_value:,}/year as a {archetype.lower()}. "
            f"Performance score: {perf_score:.0%}. "
            f"Style alignment with {pro_handle} ({pro_team}): {similarity:.0%}. "
            f"Risk tier: {risk_tier}."
        )
        if key_gaps:
            r += f" Development areas: {', '.join(g.replace('_', ' ') for g in key_gaps[:2])}."
        r += f" Recommendation: {recommendation}."
        return r
