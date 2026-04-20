"""
Twelve Labs Pegasus client for independent tactical analysis.
Uploads clip, indexes with Pegasus, generates a full tactical coaching analysis
as structured JSON, then deletes the indexed video to avoid storage costs.
"""
import os
import time
import json
import re
import requests

BASE_URL   = "https://api.twelvelabs.io/v1.3"
INDEX_NAME = "asc-pegasus"


def _headers() -> dict:
    api_key = os.environ.get("TWELVELABS_API_KEY")
    if not api_key:
        raise ValueError("TWELVELABS_API_KEY not set")
    return {"x-api-key": api_key}


def _get_or_create_index() -> str:
    headers = _headers()
    resp = requests.get(f"{BASE_URL}/indexes", headers=headers)
    resp.raise_for_status()
    for idx in resp.json().get("data", []):
        if idx.get("index_name") == INDEX_NAME:
            return idx["_id"]

    payload = {
        "index_name": INDEX_NAME,
        "models": [
            {"model_name": "pegasus1.2", "model_options": ["visual", "audio"]}
        ]
    }
    resp = requests.post(f"{BASE_URL}/indexes", headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["_id"]


def _game_focus(game: str) -> str:
    """Return game-specific tactical focus areas for Pegasus to watch."""
    if game == "r6siege":
        return (
            "Game-specific focus for Rainbow Six Siege:\n"
            "- Drone phase: did attackers gather sufficient intel before committing? Where did defenders shoot drones?\n"
            "- Reinforcements: which walls were reinforced, were they the right choices for the site being attacked?\n"
            "- Roamer vs anchor decisions: did roamers trade efficiently or waste time and get picked for free?\n"
            "- Operator gadget usage: what gadgets were deployed, at what moment, and did they create value?\n"
            "- Site control: when did attackers first establish presence on site? Was it too slow or rushed?\n"
            "- Plant/defuse: was the plant position safe? Were defuse attempts well-covered?"
        )
    elif game == "valorant":
        return (
            "Game-specific focus for Valorant:\n"
            "- Economy: was this a buy round, eco, or force buy? Did both teams spend appropriately?\n"
            "- Ability setups: were flashes, smokes, and mollies used to enable or deny site entries?\n"
            "- Ultimate usage: were ultimates used at the right moments or wasted?\n"
            "- Site exec: was the push coordinated or did players enter one at a time?\n"
            "- Spike plant/post-plant: was the plant position safe? How was the retake defended?\n"
            "- Positioning: were players holding expected angles or were there unconventional plays?"
        )
    elif game == "football":
        return (
            "Game-specific focus for Football:\n"
            "- Formation shape: did both teams maintain their intended structure in and out of possession?\n"
            "- Pressing triggers: when did teams press high, and were the triggers correct?\n"
            "- Transition moments: how quickly did teams switch between attack and defense?\n"
            "- Defensive line height: was the line too deep, too high, or appropriate for the situation?\n"
            "- Width and depth in possession: did the attacking team stretch the defense effectively?\n"
            "- Set pieces: how were corners, free kicks, and throw-ins executed?"
        )
    return ""


def _extract_json(text: str):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r'```(?:json)?\s*([\[{][\s\S]*?[\]}])\s*```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r'(\{[\s\S]*\})', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return None


def analyze_with_pegasus(clip_path: str, context: dict) -> dict | None:
    """
    Upload clip to Twelve Labs, index with Pegasus, generate a full tactical
    coaching analysis as structured JSON, then delete the video from the index.

    Returns a dict matching the Gemini analysis schema, or None if anything fails.
    """
    headers = _headers()

    try:
        index_id = _get_or_create_index()
    except Exception as e:
        print(f"    [TL] Could not get/create index: {e}")
        return None

    # Upload clip
    print(f"    [TL] Uploading {os.path.basename(clip_path)} for Pegasus analysis...")
    filename = os.path.basename(clip_path)
    with open(clip_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/tasks",
            headers=headers,
            data={"index_id": index_id},
            files={"video_file": (filename, f, "video/mp4")}
        )
    resp.raise_for_status()
    task_id = resp.json()["_id"]

    # Wait for indexing
    video_id = None
    for _ in range(72):  # up to 6 minutes
        task_resp = requests.get(f"{BASE_URL}/tasks/{task_id}", headers=headers)
        task_resp.raise_for_status()
        task_data = task_resp.json()
        status = task_data.get("status")
        print(f"    [TL] Indexing: {status}")
        if status == "ready":
            video_id = task_data.get("video_id")
            break
        elif status == "failed":
            print(f"    [TL] Indexing failed: {task_data}")
            return None
        time.sleep(5)

    if not video_id:
        print("    [TL] Indexing timed out")
        return None

    atk      = context.get("attacking_team", "Attackers")
    defn     = context.get("defending_team", "Defenders")
    winner   = context.get("winner", "Unknown")
    rnum     = context.get("round_number", "?")
    game     = context.get("game", "r6siege")
    game_name = {"r6siege": "Rainbow Six Siege", "valorant": "Valorant", "football": "Football"}.get(game, game)
    game_focus = _game_focus(game)

    prompt = f"""You are an expert {game_name} esports tactical coach analysing a competitive round clip.
Round {rnum}: {atk} are attacking, {defn} are defending. {winner} won.
Refer to players only as "{atk} attacker" or "{defn} defender" — no player names or operator names.

Watch the entire clip carefully.

{game_focus}

Return ONLY valid JSON — no other text:
{{
  "summary": "2-3 sentences describing exactly what happened and why the round ended this way",
  "loss_reason": "one sentence pinpointing the specific observable event that decided the round",
  "phase_breakdown": {{
    "setup": "what you observed in the opening phase",
    "mid_round": "the pivotal sequence of events — specific duels, utility, rotations",
    "endgame": "exactly how the round ended"
  }},
  "mistakes": [
    {{
      "team": "{atk} or {defn}",
      "category": "one of: positioning, utility, timing, decision-making, rotation, communication",
      "severity": "one of: critical, major, minor",
      "description": "Start with 'At [X]s, I can see...' then explain the mistake and consequence",
      "timestamp": <int seconds from clip start>,
      "confidence": <2 or 3 — 2=clearly visible, 3=unambiguous>,
      "better_alternative": "specific actionable alternative for this exact situation"
    }}
  ],
  "strengths": [
    "specific observable thing the winning team did well"
  ],
  "key_takeaway": "the single most important coaching point from this round"
}}

Only include mistakes you clearly saw. Fewer specific mistakes is better than more generic ones."""

    print("    [TL] Generating Pegasus tactical analysis...")
    gen_resp = requests.post(
        f"{BASE_URL}/generate",
        headers=headers,
        json={"video_id": video_id, "prompt": prompt, "temperature": 0.2}
    )
    gen_resp.raise_for_status()
    raw = gen_resp.json().get("data", "")
    print(f"    [TL] Pegasus raw ({len(raw)} chars): {raw[:120]}...")

    # Cleanup
    try:
        requests.delete(
            f"{BASE_URL}/indexes/{index_id}/videos/{video_id}",
            headers=headers
        )
        print(f"    [TL] Cleaned up video {video_id}")
    except Exception as e:
        print(f"    [TL] Cleanup warning: {e}")

    result = _extract_json(raw)
    if not result or "mistakes" not in result:
        print("    [TL] Could not parse Pegasus JSON response")
        return None

    # Filter low-confidence mistakes
    result["mistakes"] = [m for m in result["mistakes"] if m.get("confidence", 2) >= 2]
    return result
