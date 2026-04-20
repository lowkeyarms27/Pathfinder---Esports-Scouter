"""
Aggregator — runs all scrapers and merges into the archetype DB.

Order:
  1. Liquipedia  — player identity, team, role, operators
  2. sixstats    — real tournament stats (Rating, KD, KPR, KOST, Entry, 1vX)
  3. tracker.gg  — casual/ranked stats (KD, KPM, headshot%)

Each source enriches the style_vector without overwriting what others set.
Later sources only fill in dimensions the earlier ones missed.

Usage:
  python -m backend.scrapers.aggregator          # full pipeline
  python -m backend.scrapers.aggregator --quick  # liquipedia + sixstats only
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def run_full_pipeline(quick: bool = False):
    print("=" * 60)
    print("PATHFINDER ARCHETYPE BUILDER — FULL PIPELINE")
    print("=" * 60)

    # Step 1: Liquipedia — identity + role + operators
    print("\n[1/3] Liquipedia — identity, role, operators")
    print("-" * 40)
    from backend.scrapers.liquipedia import build_archetype_library
    players = build_archetype_library()
    print(f"Liquipedia: {len(players)} players scraped")

    # Step 2: sixstats — real tournament performance stats
    print("\n[2/3] sixstats.cc — tournament stats (Rating, KD, Entry, 1vX)")
    print("-" * 40)
    from backend.scrapers.sixstats import aggregate_player_stats, update_archetype_vectors
    max_ev = 15 if quick else 40
    agg = aggregate_player_stats(max_events=max_ev)
    updated = update_archetype_vectors(agg)
    print(f"sixstats: {updated} archetypes enriched with real stats")

    # Step 3: tracker.network — ranked stats (optional, often rate-limited)
    if not quick:
        print("\n[3/3] tracker.network — ranked/casual stats")
        print("-" * 40)
        try:
            from backend.scrapers.tracker_network import enrich_archetypes
            enriched = enrich_archetypes()
            print(f"tracker.gg: {enriched} archetypes enriched")
        except Exception as e:
            print(f"tracker.gg skipped: {e}")
    else:
        print("\n[3/3] tracker.network — skipped (--quick mode)")

    # Final summary
    print("\n" + "=" * 60)
    from backend.database import get_all_pro_archetypes
    pros = get_all_pro_archetypes()
    print(f"DONE — {len(pros)} pro archetypes in DB")
    by_role = {}
    for p in pros:
        role = p.get("role") or "Unknown"
        by_role[role] = by_role.get(role, 0) + 1
    for role, count in sorted(by_role.items()):
        print(f"  {role:<20} {count} players")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pathfinder full archetype builder")
    parser.add_argument("--quick", action="store_true",
                        help="Liquipedia + sixstats only (skip tracker.gg)")
    args = parser.parse_args()
    run_full_pipeline(quick=args.quick)
