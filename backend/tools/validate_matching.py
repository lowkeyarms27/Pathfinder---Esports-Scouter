"""
Ground-truth validation for the Twin Agent.

For each enriched pro, runs their own style vector through TwinAgent and
checks whether they appear as their own top match or at least match
their correct role in the top 3. Reports accuracy stats.

Usage:
  python -m backend.tools.validate_matching
  python -m backend.tools.validate_matching --min-events 5
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database import get_all_pro_archetypes
from backend.agents.twin_agent import (
    TwinAgent, _cosine_similarity, _vector_to_list,
    _get_comparison_dims, _event_confidence, _normalize_role,
    _SIXSTATS_DIMS,
)
from backend.agents.profiler import _STYLE_DIMENSIONS


def validate(min_events: int = 2):
    pros = get_all_pro_archetypes()
    enriched = [p for p in pros if (p.get("events") or 0) >= min_events]

    if not enriched:
        print(f"No pros with >= {min_events} events found.")
        return

    print(f"Validating {len(enriched)} pros (>= {min_events} events) against {len(pros)} total in library\n")

    agent = TwinAgent()

    self_match   = 0   # pro matched to themselves
    role_top1    = 0   # role correct in rank #1
    role_top3    = 0   # role correct anywhere in top 3
    rank_sum     = 0   # sum of own rank across all pros

    rows = []
    for pro in enriched:
        # Synthetic profile using the pro's own stats
        profile = {
            "player_handle": pro["handle"],
            "archetype":     pro.get("role", ""),
            "style_vector":  pro.get("style_vector", {}),
        }

        result = agent.run(profile)
        best   = result.get("best_match") or {}
        alts   = result.get("alternatives", [])

        # Find self-rank: scan all alternatives to find where this pro appears
        top_handles = [best.get("handle")] + [a.get("handle") for a in alts]
        own_rank    = result.get("rank")   # rank of best match — we need self rank

        # Re-rank manually: run twin against all pros and find this pro's own position
        # (the twin already sorted scored list, so we look at the returned result)
        # Approximate: check if self is in top 3 returned
        self_in_top3 = pro["handle"].lower() in [h.lower() for h in top_handles if h]
        matched_self = best.get("handle", "").lower() == pro["handle"].lower()

        best_role = _normalize_role(best.get("role", ""))
        own_role  = _normalize_role(pro.get("role", ""))
        role_ok_1 = best_role == own_role
        role_ok_3 = role_ok_1 or any(
            _normalize_role((a.get("role") or "")) == own_role for a in alts
        )

        if matched_self:    self_match += 1
        if role_ok_1:       role_top1  += 1
        if role_ok_3:       role_top3  += 1

        status = "SELF" if matched_self else ("ROLE" if role_ok_1 else ("ROLE-T3" if role_ok_3 else "MISS"))
        rows.append((pro["handle"], pro.get("role"), pro.get("events", 0),
                     best.get("handle"), best.get("role"),
                     result.get("display_score"), status))

    n = len(enriched)
    print(f"{'Handle':<18} {'Role':<16} {'Ev':>3}  {'Best Match':<18} {'Match Role':<16} {'Score':>6}  Status")
    print("-" * 95)
    for handle, role, events, match, mrole, score, status in rows:
        flag = "  " if status in ("SELF", "ROLE") else "! "
        print(f"{flag}{handle:<16} {(role or '?'):<16} {events:>3}  {(match or '?'):<18} {(mrole or '?'):<16} {(str(score) if score is not None else '?'):>6}%  {status}")

    print("-" * 95)
    print(f"\nResults across {n} enriched pros:")
    print(f"  Self-match (rank #1 = themselves): {self_match}/{n} = {self_match/n:.0%}")
    print(f"  Role correct at rank #1:           {role_top1}/{n} = {role_top1/n:.0%}")
    print(f"  Role correct in top 3:             {role_top3}/{n} = {role_top3/n:.0%}")
    print()

    if role_top1 / n < 0.5:
        print("WARNING: Role accuracy < 50%. The style vectors are not discriminating enough.")
        print("  -> Consider increasing the role-match bonus or re-tuning _stats_to_vector()")
    elif role_top1 / n < 0.7:
        print("CAUTION: Role accuracy 50-70%. Matching is directionally correct but noisy.")
    else:
        print("OK: Role accuracy >= 70%. Twin Agent is functioning well.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-events", type=int, default=2,
                        help="Minimum events for a pro to be included (default 2)")
    args = parser.parse_args()
    validate(min_events=args.min_events)
