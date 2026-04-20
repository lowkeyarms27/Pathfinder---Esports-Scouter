"""
Pathfinder game configuration.
Defines scouting-mode prompts: find exceptional plays, not mistakes.
"""

_R6_SCOUTING_CONTEXT = """
RAINBOW SIX SIEGE — SCOUTING FRAMEWORK

You are a talent scout, not a coach. Your goal is to identify EXCEPTIONAL plays that signal elite potential.

WHAT TO FLAG AS EXCEPTIONAL:
- Entry fragger: First duel wins on difficult angles, aggressive drone kills, explosive site takes
- Anchor: 1vX clutch plays, calm under pressure, information denial that saves rounds
- Roamer: Successful flank kills after extracting value, unpredictable rotations that catch attackers
- Support/IGL: Utility that directly enables a kill (smoke + push, flash + entry), clear callout→action sequences
- Hard breach: Wall opens that unlock critical angles at the right moment, adaptive breach timing

POSITIVE OUTLIER SIGNALS:
- Winning a duel against odds (low health, outnumbered, peeked from unexpected angle)
- Utility used proactively rather than reactively
- Calm positioning in 1v2+ situations
- Operator selection that exploits the specific map moment
- Communication that triggers coordinated team action

DO NOT flag routine plays. Only flag moments that would make a scout say "who is this player?"
"""

_R6_SCOUTING_KNOWLEDGE = """
OPERATOR ROLE SIGNATURES (for archetype identification):
- Hard Breach (Thermite/Hibana/Ace): Wall opens, breach timing, utility sequencing
- Entry Fragger (Ash/Sledge/Jager): Aggressive peeks, drone kills, first blood
- Anchor (Echo/Maestro/Mozzie): Site holds, gadget denial, clutch positioning
- Roamer (Jager/Bandit/Vigil): Spawn kills, information extraction, flank timing
- Support/IGL (Rook/Doc/Thermite): Armor drops, callouts, utility enabling teammates

CLUTCH INDICATORS (high weight for scouting):
- 1v2: Winning against 2 opponents
- 1v3+: Exceptional clutch, very high weight
- Plant under pressure: Successful defuser plant in 1v1+ situations
- Ace: Eliminating all 5 opponents in a single round
"""


GAME_CONFIGS = {
    "r6siege": {
        "name": "Rainbow Six Siege",
        "scouting_context": _R6_SCOUTING_CONTEXT,
        "role_knowledge": _R6_SCOUTING_KNOWLEDGE,
        "archetypes": ["Entry Fragger", "Anchor", "Roamer", "Support", "Hard Breach", "IGL"],
        "min_round_seconds": 60,
        "max_round_seconds": 240,
        "min_gap_between_rounds": 20,
    }
}


def get_config(game: str) -> dict:
    return GAME_CONFIGS.get(game, GAME_CONFIGS["r6siege"])
