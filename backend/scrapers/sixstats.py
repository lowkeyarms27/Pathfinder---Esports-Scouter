"""
sixstats.cc scraper — real per-player performance stats from R6 esports events.

Scrapes Rating, K/D, KPR, KOST%, Entry diff, 1vX clutch across all 200+ event pages.
These stats are converted directly into style vector dimensions.

Usage:
  python -m backend.scrapers.sixstats                    # aggregate all events
  python -m backend.scrapers.sixstats --event nalstage124stats  # single event
"""
import argparse
import json
import time
import re
import sys
from pathlib import Path
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

BASE = "https://sixstats.cc"
HEADERS = {"User-Agent": "PathfinderScout/1.0 (esports research)"}
_DELAY = 1.5

# How raw stats map to our 15 style dimensions (all normalized 0–1)
# Done via min-max scaling with sensible esports bounds
_STAT_BOUNDS = {
    "rating":         (0.7, 1.4),    # pro range
    "kd":             (0.7, 1.6),
    "kpr":            (0.5, 1.1),
    "kost":           (45,  75),     # percentage
    "entry_diff":     (-10, 15),     # entry kills - entry deaths per tournament
    "entry_rate":     (0.0, 0.6),    # entry attempts per round
    "clutch_1vx":     (0,   8),      # clutches per tournament
    "plants":         (0,   15),     # defuser plants per tournament
}


def _normalize(val: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.5
    return max(0.0, min(1.0, (val - lo) / (hi - lo)))


def _stats_to_vector(stats: dict) -> dict:
    """Convert raw tournament stats into a partial style vector (0–1 per dim)."""
    rating    = stats.get("rating", 1.0)
    kd        = stats.get("kd", 1.0)
    kpr       = stats.get("kpr", 0.7)
    kost      = stats.get("kost", 55.0)
    entry_diff = stats.get("entry_diff", 0)
    entry_rate = stats.get("entry_rate", 0.2)
    clutch    = stats.get("clutch_1vx", 0)
    plants    = stats.get("plants", 3)
    rounds    = max(stats.get("rounds", 100), 1)

    entry_per_round = entry_rate / rounds if entry_rate > 1 else entry_rate
    clutch_per_round = clutch / rounds

    return {
        "aggression":          _normalize(kpr, *_STAT_BOUNDS["kpr"]),
        "reaction_speed":      _normalize(kpr * kd, 0.4, 1.5),
        "entry_success_rate":  _normalize(max(entry_diff, 0) / max(entry_rate, 1), -0.5, 1.0),
        "clutch_rate":         _normalize(clutch_per_round, 0, 0.06),
        "first_duel_rate":     _normalize(entry_per_round, 0, 0.25),
        "utility_enable_rate": _normalize(kost / 100, 0.45, 0.75),
        "trade_efficiency":    _normalize(kd, *_STAT_BOUNDS["kd"]),
        "site_presence":       _normalize(plants / rounds, 0, 0.12),
        "calm_under_pressure": _normalize(kost / 100 * (1 + clutch_per_round * 5), 0.4, 0.85),
        "info_play_rate":      _normalize(kost / 100, 0.45, 0.75),
    }


def _parse_event_tables(html: str) -> list[dict]:
    """Parse all player stat rows from a sixstats event page."""
    soup    = BeautifulSoup(html, "html.parser")
    players = []

    for table in soup.find_all("table"):
        headers = [th.text.strip().lower() for th in table.find_all("th")]
        if "name" not in headers or "rating" not in headers:
            continue
        if "loading..." in table.get_text().lower():
            continue

        col = {h: i for i, h in enumerate(headers)}
        for row in table.find_all("tr")[1:]:
            cells = [td.text.strip() for td in row.find_all("td")]
            if len(cells) < 4:
                continue
            try:
                name = cells[col.get("name", 0)]
                if not name or name.lower() == "loading...":
                    continue

                rating = float(cells[col["rating"]]) if "rating" in col else 1.0
                kd_str = cells[col.get("k/d", col.get("kd", -1))] if ("k/d" in col or "kd" in col) else "1.0"
                kd     = float(kd_str) if kd_str else 1.0
                kpr    = float(cells[col["kpr"]]) if "kpr" in col else 0.7
                kost_s = cells[col.get("kost%", col.get("kost", -1))] if ("kost%" in col or "kost" in col) else "55"
                kost   = float(kost_s.replace("%", "")) if kost_s else 55.0

                # Entry: "10 - 11 (-1)" format or just a number
                entry_raw  = cells[col["entry"]] if "entry" in col else "0"
                entry_diff = 0
                entry_attempts = 0
                em = re.search(r"(\d+)\s*-\s*(\d+)", entry_raw)
                if em:
                    entry_attempts = int(em.group(1))
                    entry_diff     = int(em.group(1)) - int(em.group(2))
                elif entry_raw.lstrip("-").isdigit():
                    entry_diff = int(entry_raw)

                clutch = int(cells[col["1vx"]]) if "1vx" in col else 0
                plants = int(cells[col["plants"]]) if "plants" in col else 0
                rounds = int(cells[col.get("rounds", -1)]) if "rounds" in col and cells[col["rounds"]].isdigit() else 100

                # Operator list
                ops = []
                if "operators" in col:
                    ops = [o.strip() for o in cells[col["operators"]].split(",") if o.strip()]

                players.append({
                    "handle":       name,
                    "rating":       rating,
                    "kd":           kd,
                    "kpr":          kpr,
                    "kost":         kost,
                    "entry_diff":   entry_diff,
                    "entry_rate":   entry_attempts,
                    "clutch_1vx":   clutch,
                    "plants":       plants,
                    "rounds":       rounds,
                    "operators":    ops,
                })
            except (ValueError, IndexError, KeyError):
                continue

    return players


def _fetch(url: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return r.text if r.status_code == 200 else None
    except Exception as e:
        print(f"  Fetch failed {url}: {e}")
        return None


def get_event_list() -> list[str]:
    html = _fetch(f"{BASE}/sitemap3.php")
    if not html:
        return []
    return re.findall(r"eventspage\.php\?name=([^<\s]+)", html)


def scrape_event(event_name: str) -> list[dict]:
    html = _fetch(f"{BASE}/eventspage.php?name={event_name}")
    if not html:
        return []
    return _parse_event_tables(html)


def aggregate_player_stats(events: list[str] = None,
                            max_events: int = 50) -> dict[str, dict]:
    """
    Scrape multiple events and average stats per player.
    Returns {handle: aggregated_stats_dict}
    """
    if events is None:
        events = get_event_list()
    events = events[:max_events]

    # Accumulate: {handle: [stat_dicts]}
    accumulator: dict[str, list] = defaultdict(list)

    for i, ev in enumerate(events):
        print(f"[{i+1}/{len(events)}] Scraping {ev}...")
        rows = scrape_event(ev)
        for row in rows:
            accumulator[row["handle"]].append(row)
        if i < len(events) - 1:
            time.sleep(_DELAY)

    # Average stats per player
    aggregated = {}
    for handle, rows in accumulator.items():
        if len(rows) < 2:
            continue  # skip players seen in only one event
        avg = {
            "handle":     handle,
            "events":     len(rows),
            "rating":     sum(r["rating"] for r in rows) / len(rows),
            "kd":         sum(r["kd"] for r in rows) / len(rows),
            "kpr":        sum(r["kpr"] for r in rows) / len(rows),
            "kost":       sum(r["kost"] for r in rows) / len(rows),
            "entry_diff": sum(r["entry_diff"] for r in rows) / len(rows),
            "entry_rate": sum(r["entry_rate"] for r in rows) / len(rows),
            "clutch_1vx": sum(r["clutch_1vx"] for r in rows) / len(rows),
            "plants":     sum(r["plants"] for r in rows) / len(rows),
            "operators":  list({op for r in rows for op in r.get("operators", [])}),
        }
        avg["style_vector_partial"] = _stats_to_vector(avg)
        aggregated[handle] = avg

    return aggregated


def update_archetype_vectors(aggregated: dict[str, dict]):
    """Merge real stats into existing pro_archetypes DB records."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from backend.database import get_all_pro_archetypes, upsert_pro_archetype

    pros = {p["handle"].lower(): p for p in get_all_pro_archetypes()}
    updated = 0

    for handle, stats in aggregated.items():
        # Case-insensitive match
        pro = pros.get(handle.lower())
        if not pro:
            continue

        partial = stats["style_vector_partial"]
        existing = pro.get("style_vector", {})

        # Merge: real stats override template values for covered dimensions
        merged = {**existing, **partial}

        # Update operators if we have richer data
        if stats.get("operators") and not pro.get("operators"):
            pro["operators"] = stats["operators"][:5]

        pro["style_vector"] = merged
        pro["events"] = stats["events"]
        upsert_pro_archetype(handle, pro)
        print(f"  Updated {handle} ({pro.get('role')}) — {stats['events']} events, "
              f"rating={stats['rating']:.2f}, kd={stats['kd']:.2f}")
        updated += 1

    print(f"\nUpdated {updated} pro archetypes with real stats.")
    return updated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="sixstats.cc scraper")
    parser.add_argument("--event", help="Scrape a single event by name")
    parser.add_argument("--max-events", type=int, default=30,
                        help="Max events to aggregate (default 30)")
    args = parser.parse_args()

    if args.event:
        rows = scrape_event(args.event)
        print(json.dumps(rows[:5], indent=2))
    else:
        print(f"Aggregating stats across up to {args.max_events} events...")
        agg = aggregate_player_stats(max_events=args.max_events)
        print(f"\nPlayers with 2+ events: {len(agg)}")
        update_archetype_vectors(agg)
