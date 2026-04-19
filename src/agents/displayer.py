"""
Displayer agent — formats player party, trainer party, and strategy into
a clean JSON structure for the frontend.
"""

import json
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash"

SYSTEM_PROMPT = """You are the Displayer agent for a Pokémon Nuzlocke assistant.
Format the input data into this exact JSON structure for the frontend. Output ONLY the JSON.

{
  "player": {
    "trainer_name": "...",
    "party": [
      {
        "nickname": "...",
        "species_name": "...",
        "species_id": 0,
        "type1": "...",
        "type2": "...",
        "level": 0,
        "hp_current": 0,
        "hp_max": 0,
        "hp_percent": 0.0,
        "is_fainted": false,
        "moves": [{"id": 0, "name": "...", "type": "...", "power": 0, "pp": 0}],
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
        "type2": "...",
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

Build sprite_url using species_id. Set danger_level from the strategy's danger_pokemon list."""


def format_for_display(player_data: dict, trainer_data: dict, strategy_data: dict) -> dict:
    context = json.dumps({
        "player_data": player_data,
        "trainer_data": trainer_data,
        "strategy_data": strategy_data,
    }, indent=2)

    response = client.models.generate_content(
        model=MODEL,
        contents=[{"role": "user", "parts": [{"text": context}]}],
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )

    raw = response.text or ""
    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        display_data = json.loads(raw[start:end])
        return {"success": True, "data": display_data}
    except Exception as e:
        return {"success": False, "data": None, "error": f"JSON parse error: {e}", "raw": raw}
