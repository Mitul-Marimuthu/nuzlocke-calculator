"""
Displayer agent — formats player party and opponent into display-ready JSON,
then merges with the pre-computed strategy data (no LLM reformatting of turns).
"""

import json
from src.agents._client import chat

SYSTEM_PROMPT = """You are the Displayer agent for a Pokémon Nuzlocke assistant.
Format the input data into this exact JSON structure. Output ONLY valid JSON — no markdown fences, no extra text.

{
  "player": {
    "trainer_name": "...",
    "party": [
      {
        "slot": 0,
        "nickname": "...",
        "species_name": "...",
        "species_id": 0,
        "type1": "...",
        "type2": null,
        "level": 0,
        "hp_current": 0,
        "hp_max": 0,
        "hp_percent": 0.0,
        "is_fainted": false,
        "moves": [{"id": 0, "name": "...", "type": "...", "power": null, "pp": 0}],
        "sprite_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/<species_id>.png",
        "strategy_role": "lead|support|closer|bench",
        "risk_note": "..."
      }
    ]
  },
  "opponent": {
    "name": "...",
    "trainer_class": "...",
    "is_double": false,
    "party": [
      {
        "species_name": "...",
        "species_id": 0,
        "type1": "...",
        "type2": null,
        "level": 0,
        "moves": [],
        "sprite_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/<species_id>.png",
        "danger_level": "low|medium|high"
      }
    ]
  }
}

Rules:
- sprite_url: use species_id (e.g. Geodude=74 → .../74.png)
- danger_level: high if in danger_pokemon list, medium if matchup_summary risk=caution, else low
- strategy_role: lead = lead_recommendation match, bench = fainted/unused, closer = saved for last dangerous mon, support = utility
- hp_percent: hp_current / hp_max * 100 rounded to 1 decimal
- Output ONLY the player+opponent JSON above — do NOT include strategy/turns"""


def format_for_display(player_data: dict, trainer_data: dict, strategy_data: dict) -> dict:
    context = json.dumps({
        "player_data": player_data,
        "trainer_data": trainer_data,
        # Give LLM just enough strategy context to assign roles/danger levels
        "strategy_context": {
            "lead_recommendation": strategy_data.get("lead_recommendation"),
            "danger_pokemon": strategy_data.get("danger_pokemon", []),
            "matchup_summary": strategy_data.get("matchup_summary", []),
            "surviving_party": strategy_data.get("surviving_party", []),
        },
    }, indent=2)

    response = chat(messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": context},
    ])

    raw = response.choices[0].message.content or ""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        display_parts = json.loads(raw[start:end])
    except Exception as e:
        return {"success": False, "data": None, "error": f"JSON parse error: {e}", "raw": raw}

    # Merge: LLM formats player+opponent display, strategy passes through as-is
    display_data = {
        "player": display_parts.get("player", {"trainer_name": player_data.get("trainer_name", ""), "party": []}),
        "opponent": display_parts.get("opponent", {"name": trainer_data.get("name", ""), "trainer_class": "", "is_double": False, "party": []}),
        "strategy": strategy_data,
    }
    return {"success": True, "data": display_data}
