"""
Gemini video analysis using the google-genai SDK.
Uploads clips to Gemini Files API for deep tactical coaching analysis.
"""
import os
import json
import re
import time
from google import genai
from backend.agents.game_config import get_config

MODEL = "gemini-2.5-flash"


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    return genai.Client(api_key=api_key)


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


def _format_examples(examples: list) -> str:
    if not examples:
        return ""
    lines = ["The following are high-quality analyses from past rounds. Match this level of detail and specificity:\n"]
    for i, ex in enumerate(examples, 1):
        atk = ex.get("attacking_team", "Attackers")
        defn = ex.get("defending_team", "Defenders")
        winner = ex.get("winner", "?")
        rnum = ex.get("round_number", "?")
        result_json = ex.get("full_result", "{}")
        lines.append(f"--- Example {i}: Round {rnum}, {atk} vs {defn}, {winner} won ---")
        lines.append(result_json)
        lines.append("--- End example ---\n")
    return "\n".join(lines)


def analyze_clip(clip_path: str, context: dict, examples: list = None) -> dict | None:
    """
    Upload clip to Gemini Files API and run deep tactical analysis.
    Returns: summary, loss_reason, phase_breakdown, mistakes (severity + category),
             strengths, key_takeaway.
    """
    client = _get_client()
    cfg = get_config(context.get("game", "r6siege"))

    atk = context.get("attacking_team", "Attackers")
    defn = context.get("defending_team", "Defenders")
    winner = context.get("winner", "Unknown")
    round_num = context.get("round_number", "?")
    notes = context.get("notes", "")

    print(f"    Uploading {os.path.basename(clip_path)} to Gemini Files API...")
    uploaded = client.files.upload(file=clip_path, config={"mime_type": "video/mp4"})

    for _ in range(30):
        f = client.files.get(name=uploaded.name)
        if f.state.name == "ACTIVE":
            break
        if f.state.name == "FAILED":
            raise RuntimeError("Gemini file processing failed")
        time.sleep(3)
    else:
        raise RuntimeError("Gemini file processing timed out")

    few_shot = _format_examples(examples or [])

    prompt = f"""{cfg['coaching_prompt']}

{few_shot}
Round {round_num}: {atk} attacking, {defn} defending. {winner} won.
Refer to players only as "{atk} attacker" or "{defn} defender" — no player names or operator names.
{f"Additional context: {notes}" if notes else ""}

━━━ STEP 1 — WATCH FIRST ━━━
Before writing anything, watch the entire clip. Mentally note:
- Every elimination: who died, at what second, from where
- Every piece of utility used and what it hit or missed
- Player positions and when they moved
- The exact sequence of events that decided the round

━━━ STEP 2 — GROUNDING RULES ━━━
Your analysis must follow these exactly:
1. Every mistake must be something you LITERALLY SAW happen in this clip
2. Every timestamp must match a real visible moment — if you are not sure of the exact second, give your best estimate but lower the confidence
3. Start each mistake description with what you observe: "At Xs, [attacker/defender] [specific visible action]..." then explain why it was wrong
4. Do NOT write generic coaching points that could apply to any round — only what happened HERE
5. FEWER specific grounded mistakes is better than MORE generic ones
6. If you cannot clearly see a mistake, do NOT include it

━━━ STEP 3 — OUTPUT ━━━
Return ONLY valid JSON — no other text:
{{
  "summary": "2-3 sentences describing exactly what happened in this clip and why it ended the way it did",
  "loss_reason": "one sentence grounded in a specific observable event that decided the round",
  "phase_breakdown": {{
    "setup": "what you observed in the opening phase — drone play, positioning, setup choices",
    "mid_round": "the pivotal sequence of events you saw — specific duels, utility, rotations",
    "endgame": "exactly how the round ended — final duel, plant/defuse, numbers situation"
  }},
  "mistakes": [
    {{
      "team": "{atk} or {defn}",
      "category": "one of: positioning, utility, timing, decision-making, rotation, communication",
      "severity": "one of: critical, major, minor",
      "description": "Start with 'At [X]s, I can see...' then explain the mistake and its consequence",
      "clip_timestamp_s": <int seconds from clip start — the frame where mistake is most visible>,
      "confidence": <1, 2, or 3 — 1=uncertain/partially visible, 2=clear, 3=unambiguous>,
      "better_alternative": "specific actionable alternative grounded in what the situation called for"
    }}
  ],
  "strengths": [
    "specific observable thing the winning team did well — reference what you saw"
  ],
  "key_takeaway": "the single most important coaching point from THIS round specifically"
}}"""

    models_to_try = [MODEL, "gemini-2.5-flash", "gemini-flash-latest"]
    raw = None
    for model in models_to_try:
        for attempt in range(4):
            try:
                # Thinking mode: Gemini 2.5 Flash reasons internally before responding
                # dramatically improves grounding and reduces hallucination
                if model == MODEL:
                    from google.genai import types
                    response = client.models.generate_content(
                        model=model,
                        contents=[uploaded, prompt],
                        config=types.GenerateContentConfig(
                            thinking_config=types.ThinkingConfig(thinking_budget=8000)
                        )
                    )
                else:
                    response = client.models.generate_content(
                        model=model, contents=[uploaded, prompt]
                    )
                raw = response.text
                break
            except Exception as e:
                msg = str(e).lower()
                if "503" in msg or "unavailable" in msg or "429" in msg or "quota" in msg:
                    wait_time = (2 ** attempt) * 5
                    print(f"    {model} rate limited or unavailable, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise
        if raw:
            break

    try:
        client.files.delete(name=uploaded.name)
    except Exception:
        pass

    if not raw:
        return None

    print(f"    Gemini raw: {raw[:200]}")
    result = _extract_json(raw)
    if not result or "mistakes" not in result:
        return None

    # Convert timestamps and drop low-confidence mistakes (confidence=1)
    kept, dropped = [], 0
    for m in result["mistakes"]:
        m["timestamp"] = int(m.pop("clip_timestamp_s", 0))
        confidence = m.pop("confidence", 2)
        if confidence >= 2:
            kept.append(m)
        else:
            dropped += 1
    if dropped:
        print(f"    Filtered {dropped} low-confidence mistake(s)")
    result["mistakes"] = kept

    return result


def synthesize_analyses(gemini_result: dict, pegasus_result: dict, context: dict) -> dict:
    """
    Merge Gemini and Pegasus analyses into a single unified result.

    Mistakes: merged in Python using timestamp + category agreement.
      - Both agents flagged it (within 8s, same category) → confidence 3 (high)
      - Only one agent flagged it → confidence 2 (medium)

    Narrative fields: synthesized via a fast text-only Gemini call.
    """
    if not pegasus_result:
        return gemini_result

    # ── Merge mistakes ──────────────────────────────────────────────
    g_mistakes = gemini_result.get("mistakes", [])
    p_mistakes = pegasus_result.get("mistakes", [])

    merged = []
    p_matched = set()

    for gm in g_mistakes:
        g_ts  = gm.get("timestamp", 0)
        g_cat = gm.get("category", "")
        agreed = False
        for i, pm in enumerate(p_mistakes):
            if i in p_matched:
                continue
            p_ts  = pm.get("timestamp", 0)
            p_cat = pm.get("category", "")
            if abs(g_ts - p_ts) <= 8 and g_cat == p_cat:
                agreed = True
                p_matched.add(i)
                break
        gm["confidence"] = 3 if agreed else 2
        merged.append(gm)

    # Add Pegasus-only mistakes not matched to any Gemini mistake
    for i, pm in enumerate(p_mistakes):
        if i not in p_matched:
            merged.append({
                "team":             pm.get("team", ""),
                "category":         pm.get("category", ""),
                "severity":         pm.get("severity", "major"),
                "description":      pm.get("description", ""),
                "timestamp":        int(pm.get("timestamp", 0)),
                "better_alternative": pm.get("better_alternative", ""),
                "confidence":       2,
            })

    # Sort by timestamp
    merged.sort(key=lambda m: m.get("timestamp", 0))

    agreed_count = sum(1 for m in merged if m.get("confidence") == 3)
    print(f"    [Synthesis] {len(merged)} mistakes total — {agreed_count} agreed by both agents")

    # ── Synthesize narrative fields via text-only Gemini call ────────
    print("    [Synthesis] Synthesizing narrative fields...")
    client = _get_client()

    atk    = context.get("attacking_team", "Attackers")
    defn   = context.get("defending_team", "Defenders")
    winner = context.get("winner", "Unknown")

    synthesis_prompt = f"""Two independent AI coaches have analysed the same {context.get('game','esports')} clip.
Round: {atk} attacking, {defn} defending. {winner} won.

GEMINI ANALYSIS:
Summary: {gemini_result.get('summary', '')}
Loss reason: {gemini_result.get('loss_reason', '')}
Phase breakdown: {json.dumps(gemini_result.get('phase_breakdown', {}))}
Strengths: {json.dumps(gemini_result.get('strengths', []))}
Key takeaway: {gemini_result.get('key_takeaway', '')}

PEGASUS ANALYSIS:
Summary: {pegasus_result.get('summary', '')}
Loss reason: {pegasus_result.get('loss_reason', '')}
Phase breakdown: {json.dumps(pegasus_result.get('phase_breakdown', {}))}
Strengths: {json.dumps(pegasus_result.get('strengths', []))}
Key takeaway: {pegasus_result.get('key_takeaway', '')}

Synthesize both into a single unified coaching analysis. Where they agree, that is ground truth.
Where they differ, pick the more specific and grounded version.
Return ONLY valid JSON — no other text:
{{
  "summary": "...",
  "loss_reason": "...",
  "phase_breakdown": {{"setup": "...", "mid_round": "...", "endgame": "..."}},
  "strengths": ["..."],
  "key_takeaway": "..."
}}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[synthesis_prompt]
        )
        narrative = _extract_json(response.text)
    except Exception as e:
        print(f"    [Synthesis] Narrative synthesis failed ({e}), using Gemini narrative")
        narrative = None

    if not narrative:
        narrative = {
            "summary":        gemini_result.get("summary", ""),
            "loss_reason":    gemini_result.get("loss_reason", ""),
            "phase_breakdown": gemini_result.get("phase_breakdown", {}),
            "strengths":      gemini_result.get("strengths", []),
            "key_takeaway":   gemini_result.get("key_takeaway", ""),
        }

    return {**narrative, "mistakes": merged}
