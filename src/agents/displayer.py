"""
Displayer agent — formats player party, trainer party, and strategy into
a clean JSON structure for the frontend.
"""

import json
from src.agents._client import chat

SYSTEM_PROMPT = """You are the Displayer agent for a Pokémon Nuzlocke assistant.
Format the input data into this exact JSON structure. Output ONLY the JSON — no markdown, no extra text.

{
  "player": {
    "trainer_name": "...",
    "party": [
      {
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
  },
  "strategy": {
    "lead_recommendation": "...",
    "lead_reasoning": "...",
    "matchups": [...],
    "overall_notes": "...",
    "danger_pokemon": [...]
  }
}

Rules:
- Build sprite_url from species_id.
- Set danger_level using the strategy danger_pokemon list and matchup risk_levels.
- Set strategy_role: lead = recommended lead, bench = fainted or not needed, closer = saved for last, support = utility."""


def format_for_display(player_data: dict, trainer_data: dict, strategy_data: dict) -> dict:
    context = json.dumps({
        "player_data": player_data,
        "trainer_data": trainer_data,
        "strategy_data": strategy_data,
    }, indent=2)

    response = chat(messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": context},
    ])

    raw = response.choices[0].message.content or ""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        display_data = json.loads(raw[start:end])
        return {"success": True, "data": display_data}
    except Exception as e:
        return {"success": False, "data": None, "error": f"JSON parse error: {e}", "raw": raw}
