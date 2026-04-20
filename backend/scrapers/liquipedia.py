"""
Liquipedia R6 Siege scraper — full archetype builder.

Scrapes player pages to build the pro archetype library.
Stores results in both the DB (pro_archetypes table) and data/pro_archetypes.json.

Usage:
  python -m backend.scrapers.liquipedia                      # scrape default roster
  python -m backend.scrapers.liquipedia --player Alem4o     # single player
  python -m backend.scrapers.liquipedia --all               # all known pros
"""
import argparse
import json
import time
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

LIQUIPEDIA_BASE = "https://liquipedia.net/rainbowsix"
HEADERS = {
    "User-Agent": "PathfinderScout/1.0 (esports talent research)",
    "Accept-Language": "en-US,en;q=0.9",
}
_REQUEST_DELAY = 2.5  # seconds between requests — respect Liquipedia rate limits

# Known pros with role hints — used when Liquipedia role field is absent
_ROLE_HINTS = {
    # ── NAL (North American League) ──────────────────────────────────────────
    # G2 Esports
    "Alem4o":       "IGL",
    "Doki":         "Entry Fragger",
    "Stompn":       "Flex",
    "BlaZ":         "Roamer",
    "Virtue":       "Anchor",
    # Team Liquid / Soniqs
    "Canadian":     "Entry Fragger",
    "Necrox":       "Anchor",
    "Ivy":          "Hard Breach",
    "Peres":        "Roamer",
    "Lash":         "Support",
    "Parabellum":   "IGL",
    "Mav":          "Entry Fragger",
    # Team Falcons / FaZe
    "BriD":         "Entry Fragger",
    "Astro":        "Hard Breach",
    "Pino":         "Anchor",
    "KRWN":         "Roamer",
    "Surtr":        "Support",
    # Ninjas in Pyjamas
    "Helbee":       "Anchor",
    "Renshiro":     "Roamer",
    "Jonka":        "Hard Breach",
    "Fabian":       "IGL",
    "Slebben":      "Entry Fragger",
    # Spacestation Gaming
    "Rampy":        "Anchor",
    "Beaulo":       "Entry Fragger",
    "Retro":        "Roamer",
    "Ecl9pse":      "Hard Breach",
    "Achieved":     "Support",
    # DarkZero
    "Hyena":        "Entry Fragger",
    "Revan":        "IGL",
    "Fenrir":       "Anchor",
    "Ranger":       "Roamer",
    "BC":           "Hard Breach",
    "Njr":          "Entry Fragger",
    # Shopify Rebellion / Wildcard
    "Hotancold":    "IGL",
    "Supr":         "Anchor",
    "Easierthenu":  "Entry Fragger",
    "Lycan":        "Roamer",
    "Keenan":       "Hard Breach",
    "Lagonis":      "Hard Breach",
    # M80
    "Geo":          "Entry Fragger",
    "Skys":         "IGL",
    "Fultz":        "Roamer",
    "Yung":         "Hard Breach",
    "Yeti":         "Anchor",
    # Wolves Esports / Elevate
    "Xapco":        "IGL",
    "Pantera":      "Entry Fragger",
    "Knoxx":        "Roamer",
    "Merc":         "Anchor",
    "Gibbs":        "Support",
    "Kendrew":      "Anchor",
    "Twitchyy":     "Entry Fragger",
    "Risze":        "Entry Fragger",
    "Korey":        "IGL",
    "Mango":        "Anchor",
    "Valco":        "Hard Breach",
    "Bosco":        "Roamer",
    "Mav":          "Entry Fragger",
    # Team Empire (NAL)
    "JoyStiCK":     "IGL",
    "Destyn":       "Entry Fragger",
    "FoxA":         "Anchor",
    "Scream":       "Roamer",
    "Goga":         "Hard Breach",
    # Oxygen Esports / other NAL
    "Beastly":      "Entry Fragger",
    "Kvam":         "IGL",
    "Mint":         "Anchor",
    "Kryptic":      "Roamer",
    "Macie":        "Support",

    # ── EUL (European League) ────────────────────────────────────────────────
    # Team BDS
    "Shaiiko":      "IGL",
    "GobuGi":       "Entry Fragger",
    "Meechy":       "Hard Breach",
    "RaFaLe":       "Roamer",
    "Hydrak":       "Anchor",
    # Team Secret
    "Mowwwgli":     "IGL",
    "Elemzje":      "IGL",
    "Moizy":        "Entry Fragger",
    "Pengu":        "IGL",
    "Kantoraketti": "Entry Fragger",
    # Natus Vincere (EUL)
    "Saves":        "Roamer",
    "Mango":        "Anchor",
    "Paluh":        "Entry Fragger",
    # Rogue
    "Rampage":      "Entry Fragger",
    "Kizzy":        "Support",
    # Rebels Gaming
    "Szpero":       "IGL",
    "Gomfi":        "IGL",
    "Dpj":          "Entry Fragger",
    # Additional EUL
    "w1nkz":        "Entry Fragger",
    "Dpj":          "Entry Fragger",
    "Grizz":        "Anchor",
    "Hayz":         "Entry Fragger",
    "Shas":         "IGL",

    # ── Brazil League ────────────────────────────────────────────────────────
    # Team oNe / Fluxo W7M
    "Muzi":         "IGL",
    "Bullet1":      "Hard Breach",
    "R4re":         "Roamer",
    # FURIA Esports
    "Nesk":         "IGL",
    "Pley":         "Entry Fragger",
    "Dino":         "Roamer",
    "Silk":         "Hard Breach",
    "lowei":        "Entry Fragger",
    # NiP Brazil / other Brazil
    "Nak":          "Anchor",
    "GodBr":        "Support",
    "Peres":        "Roamer",
    # Vince Seven / other Brazil
    "Lagonis":      "Hard Breach",
    "R4re":         "Roamer",
    "Alem4o":       "IGL",
    # Black Dragons / Fluxo
    "Stk":          "Entry Fragger",
    "nzr":          "Entry Fragger",
    "MagixZ":       "IGL",
    "Cameram4n":    "Anchor",

    # ── APAC ─────────────────────────────────────────────────────────────────
    # Global Esports / SEA
    "Hungry":       "Entry Fragger",
    "Aerox":        "Roamer",
    "Thibo":        "IGL",
    "Phoebe":       "Entry Fragger",
    "Wokka":        "IGL",
    # Australia / Oceania
    "SolidFrames":  "IGL",
    "Gunba":        "IGL",
    "Brokenshore":  "Hard Breach",
    # Japan / Korea
    "Cyclops":      "Hard Breach",
    "Kvi":          "Entry Fragger",
}

# Role-based default style vectors — grounded in the 15 Profiler dimensions
_ROLE_STYLE_TEMPLATES = {
    "Entry Fragger": {
        "aggression": 0.9, "utility_priority": 0.3, "clutch_rate": 0.5,
        "reaction_speed": 0.85, "flank_frequency": 0.4, "first_duel_rate": 0.85,
        "comms_density": 0.5, "position_variance": 0.5, "trade_efficiency": 0.6,
        "site_presence": 0.7, "operator_diversity": 0.5, "info_play_rate": 0.4,
        "entry_success_rate": 0.8, "utility_enable_rate": 0.4, "calm_under_pressure": 0.6,
    },
    "Anchor": {
        "aggression": 0.2, "utility_priority": 0.6, "clutch_rate": 0.75,
        "reaction_speed": 0.65, "flank_frequency": 0.1, "first_duel_rate": 0.2,
        "comms_density": 0.6, "position_variance": 0.2, "trade_efficiency": 0.7,
        "site_presence": 0.9, "operator_diversity": 0.5, "info_play_rate": 0.6,
        "entry_success_rate": 0.5, "utility_enable_rate": 0.5, "calm_under_pressure": 0.85,
    },
    "Roamer": {
        "aggression": 0.75, "utility_priority": 0.35, "clutch_rate": 0.45,
        "reaction_speed": 0.8, "flank_frequency": 0.9, "first_duel_rate": 0.65,
        "comms_density": 0.65, "position_variance": 0.9, "trade_efficiency": 0.5,
        "site_presence": 0.1, "operator_diversity": 0.6, "info_play_rate": 0.45,
        "entry_success_rate": 0.65, "utility_enable_rate": 0.3, "calm_under_pressure": 0.6,
    },
    "Hard Breach": {
        "aggression": 0.55, "utility_priority": 0.85, "clutch_rate": 0.4,
        "reaction_speed": 0.6, "flank_frequency": 0.2, "first_duel_rate": 0.45,
        "comms_density": 0.55, "position_variance": 0.4, "trade_efficiency": 0.65,
        "site_presence": 0.75, "operator_diversity": 0.7, "info_play_rate": 0.75,
        "entry_success_rate": 0.55, "utility_enable_rate": 0.85, "calm_under_pressure": 0.65,
    },
    "Support": {
        "aggression": 0.35, "utility_priority": 0.9, "clutch_rate": 0.4,
        "reaction_speed": 0.55, "flank_frequency": 0.25, "first_duel_rate": 0.3,
        "comms_density": 0.8, "position_variance": 0.45, "trade_efficiency": 0.6,
        "site_presence": 0.65, "operator_diversity": 0.8, "info_play_rate": 0.8,
        "entry_success_rate": 0.45, "utility_enable_rate": 0.9, "calm_under_pressure": 0.75,
    },
    "IGL": {
        "aggression": 0.4, "utility_priority": 0.75, "clutch_rate": 0.55,
        "reaction_speed": 0.6, "flank_frequency": 0.3, "first_duel_rate": 0.4,
        "comms_density": 0.95, "position_variance": 0.5, "trade_efficiency": 0.7,
        "site_presence": 0.6, "operator_diversity": 0.75, "info_play_rate": 0.85,
        "entry_success_rate": 0.5, "utility_enable_rate": 0.7, "calm_under_pressure": 0.9,
    },
    "Flex": {
        "aggression": 0.6, "utility_priority": 0.6, "clutch_rate": 0.55,
        "reaction_speed": 0.7, "flank_frequency": 0.5, "first_duel_rate": 0.55,
        "comms_density": 0.65, "position_variance": 0.65, "trade_efficiency": 0.65,
        "site_presence": 0.55, "operator_diversity": 0.85, "info_play_rate": 0.65,
        "entry_success_rate": 0.6, "utility_enable_rate": 0.6, "calm_under_pressure": 0.7,
    },
}


def _normalize_role(role: str) -> str:
    role = role.strip().title()
    for key, canonical in [
        ("Entry", "Entry Fragger"), ("Fragger", "Entry Fragger"),
        ("Anchor", "Anchor"), ("Roam", "Roamer"),
        ("Hard Breach", "Hard Breach"), ("Breach", "Hard Breach"),
        ("Support", "Support"), ("Igl", "IGL"),
        ("Flex", "Flex"),
    ]:
        if key in role:
            return canonical
    return "Flex"


def _fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return BeautifulSoup(resp.text, "html.parser")
        print(f"  HTTP {resp.status_code}: {url}")
        return None
    except Exception as e:
        print(f"  Request failed: {e}")
        return None


def _parse_player_page(soup: BeautifulSoup, handle: str) -> dict | None:
    infobox = soup.find("div", class_="fo-nttax-infobox-wrapper")
    if not infobox:
        return None

    data = {
        "handle":      handle,
        "team":        None,
        "role":        _ROLE_HINTS.get(handle),
        "nationality": None,
        "real_name":   None,
        "operators":   [],
        "source_url":  f"{LIQUIPEDIA_BASE}/{handle}",
    }

    for cell in infobox.find_all("div", class_="infobox-description"):
        label     = cell.get_text(strip=True).lower()
        value_div = cell.find_next_sibling("div")
        if not value_div:
            continue
        value = value_div.get_text(strip=True)

        if "name" in label and "ign" not in label and not data["real_name"]:
            data["real_name"] = value
        elif "nationality" in label:
            data["nationality"] = value
        elif "role" in label and not data["role"]:
            data["role"] = value
        elif "team" in label and not data["team"]:
            data["team"] = value
        elif "operator" in label and "signature" in label:
            ops = [
                a.get("title", a.get_text(strip=True))
                for a in value_div.find_all("a")
                if a.get("title") or a.get_text(strip=True)
            ]
            if not ops:
                ops = [o.strip() for o in value.split(",") if o.strip()]
            data["operators"] = ops[:5]

    role_key = _normalize_role(data.get("role") or "Flex")
    data["style_vector"] = _ROLE_STYLE_TEMPLATES.get(role_key, _ROLE_STYLE_TEMPLATES["Flex"])
    return data


def scrape_player(handle: str) -> dict | None:
    print(f"Scraping {handle}...")
    soup = _fetch(f"{LIQUIPEDIA_BASE}/{handle}")
    if not soup:
        return None
    data = _parse_player_page(soup, handle)
    if data:
        print(f"  Team: {data.get('team')} | Role: {data.get('role')} | "
              f"Operators: {data.get('operators')}")
    return data


def build_archetype_library(player_list: list[str] = None,
                             save_path: str = None) -> list[dict]:
    if player_list is None:
        player_list = list(_ROLE_HINTS.keys())

    results = []
    for i, handle in enumerate(player_list):
        if i > 0:
            time.sleep(_REQUEST_DELAY)
        data = scrape_player(handle)
        if not data:
            continue
        results.append(data)
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from backend.database import upsert_pro_archetype
            upsert_pro_archetype(handle, data)
            print(f"  Saved {handle} to DB")
        except Exception as e:
            print(f"  DB save failed for {handle}: {e}")

    out_path = save_path or str(Path(__file__).parent.parent.parent / "data" / "pro_archetypes.json")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(results)} archetypes -> {out_path}")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pathfinder Liquipedia Archetype Builder")
    parser.add_argument("--player", help="Scrape a single player by handle")
    parser.add_argument("--all",    action="store_true", help="Scrape all known pros")
    args = parser.parse_args()

    if args.player:
        result = scrape_player(args.player)
        if result:
            print(json.dumps(result, indent=2))
    elif args.all:
        build_archetype_library()
    else:
        # Default: 5-player prototype
        build_archetype_library(["Alem4o", "Doki", "Canadian", "BriD", "Fabian"])
