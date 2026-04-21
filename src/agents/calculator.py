"""
Calculator agent — runs a deterministic turn-by-turn battle simulation,
then asks the LLM to annotate each turn with Nuzlocke-specific strategic notes.
"""

import json
from src.agents._client import chat
from src.tools.battle_sim import simulate_battle

SYSTEM_PROMPT = """You are a Pokémon Nuzlocke expert analyst.
You will be given a pre-computed turn-by-turn battle simulation.
Your job is to annotate each turn with a concise strategic note (1-2 sentences max).

For each turn focus on:
- Whether the player should deviate from the simulated move (e.g. use a status move instead)
- Whether to switch out based on HP remaining
- Any OHKO or crit risks the player should know about
- Specific Nuzlocke danger (e.g. "this turn could end the run if you get unlucky")

Also provide:
- lead_reasoning: why this lead was chosen
- overall_notes: 2-3 sentences of overarching Nuzlocke advice for this fight
- danger_pokemon: list of opponent Pokémon that pose the highest risk

Respond ONLY with this JSON (no markdown, no extra text):
{
  "lead_reasoning": "...",
  "overall_notes": "...",
  "danger_pokemon": ["..."],
  "turn_notes": {
    "1": "Turn 1 note...",
    "2": "Turn 2 note...",
    ...
  }
}"""


def calculate_strategy(player_party: list[dict], trainer_party: list[dict]) -> dict:
    # Step 1: deterministic simulation (no LLM)
    sim = simulate_battle(player_party, trainer_party)

    # Step 2: LLM annotates the turns
    context = json.dumps({
        "player_party": player_party,
        "opponent_party": trainer_party,
        "simulation": sim,
    }, indent=2)

    response = chat(messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": context},
    ])

    raw = response.choices[0].message.content or ""
    annotations: dict = {}
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            annotations = json.loads(raw[start:end])
    except Exception:
        annotations = {"lead_reasoning": "", "overall_notes": raw, "danger_pokemon": [], "turn_notes": {}}

    # Step 3: merge annotations into turns
    turn_notes = annotations.get("turn_notes", {})
    for turn in sim["turns"]:
        key = str(turn["turn"])
        turn["note"] = turn_notes.get(key, "")

    return {
        "success": True,
        "data": {
            "lead_recommendation": sim["lead_recommendation"],
            "lead_reasoning": annotations.get("lead_reasoning", ""),
            "overall_notes": annotations.get("overall_notes", ""),
            "danger_pokemon": annotations.get("danger_pokemon", []),
            "matchup_summary": sim["matchup_summary"],
            "turns": sim["turns"],
            "total_turns": sim["total_turns"],
            "surviving_party": sim["surviving_party"],
        },
    }
