"""
r6.tracker.network scraper — ranked/casual stats for R6 players.

Uses the public Tracker.gg API (no key needed for basic stats).
Fetches K/D, win rate, headshot %, kills per match for style vector enrichment.

Usage:
  python -m backend.scrapers.tracker_network --player Beaulo
  python -m backend.scrapers.tracker_network --all
"""
import argparse
import json
import time
import sys
from pathlib import Path

import requests

BASE    = "https://api.tracker.gg/api/v2/r6siege/standard/profile/uplay"
HEADERS = {
    "User-Agent":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer":     "https://r6.tracker.network/",
    "Accept":      "application/json",
}
_DELAY = 3.0   # tracker.gg rate limits hard — be conservative

# Stat keys we extract and their style dimension mappings
_STAT_MAP = {
    "kdRatio":         "kd",
    "killsPerMatch":   "kpm",
    "headshotPct":     "headshot_pct",
    "wlRatio":         "win_rate",
    "matchesPlayed":   "matches",
}


def fetch_player_stats(username: str) -> dict | None:
    url = f"{BASE}/{username}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 429:
            print(f"  Rate limited on {username} — waiting 30s")
            time.sleep(30)
            r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"  {username}: HTTP {r.status_code}")
            return None
        data = r.json()
    except Exception as e:
        print(f"  {username}: {e}")
        return None

    try:
        segments = data.get("data", {}).get("segments", [])
        overview = next((s for s in segments if s.get("type") == "overview"), None)
        if not overview:
            return None

        stats = overview.get("stats", {})
        extracted = {"handle": username}
        for api_key, our_key in _STAT_MAP.items():
            entry = stats.get(api_key)
            if entry:
                extracted[our_key] = entry.get("value")

        # Derive style vector partials from tracker stats
        kd          = extracted.get("kd", 1.0) or 1.0
        kpm         = extracted.get("kpm", 0.7) or 0.7
        hs_pct      = extracted.get("headshot_pct", 40) or 40
        win_rate    = extracted.get("win_rate", 0.5) or 0.5

        extracted["style_vector_partial"] = {
            "aggression":       min(1.0, kpm / 1.2),
            "reaction_speed":   min(1.0, hs_pct / 60),     # high HS% → precise/fast aim
            "trade_efficiency": min(1.0, kd / 1.5),
            "entry_success_rate": min(1.0, (kd - 0.7) / 0.8),
        }

        return extracted

    except Exception as e:
        print(f"  {username} parse error: {e}")
        return None


def enrich_archetypes(handles: list[str] = None):
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from backend.database import get_all_pro_archetypes, upsert_pro_archetype

    if handles is None:
        handles = [p["handle"] for p in get_all_pro_archetypes()]

    updated = 0
    pros = {p["handle"].lower(): p for p in get_all_pro_archetypes()}

    for i, handle in enumerate(handles):
        print(f"[{i+1}/{len(handles)}] Fetching {handle}...")
        stats = fetch_player_stats(handle)
        if not stats:
            time.sleep(_DELAY)
            continue

        pro = pros.get(handle.lower())
        if not pro:
            time.sleep(_DELAY)
            continue

        partial = stats.get("style_vector_partial", {})
        merged  = {**pro.get("style_vector", {}), **partial}
        pro["style_vector"] = merged
        upsert_pro_archetype(handle, pro)

        kd  = stats.get("kd", "?")
        kpm = stats.get("kpm", "?")
        print(f"  Updated {handle} — kd={kd}, kpm={kpm}")
        updated += 1

        if i < len(handles) - 1:
            time.sleep(_DELAY)

    print(f"\nEnriched {updated} archetypes via tracker.network")
    return updated


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--player", help="Single player username")
    parser.add_argument("--all",    action="store_true")
    args = parser.parse_args()

    if args.player:
        result = fetch_player_stats(args.player)
        print(json.dumps(result, indent=2))
    elif args.all:
        enrich_archetypes()
    else:
        # Quick test
        result = fetch_player_stats("Beaulo")
        if result:
            print(json.dumps(result, indent=2))
        else:
            print("Could not fetch — tracker.gg may require login for this player")
