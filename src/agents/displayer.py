"""
Displayer agent — takes the player party, trainer party, and strategy JSON
and formats it into a rich display structure for the frontend.
"""

import json
import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are the Displayer agent for a Pokémon Nuzlocke assistant.
Your job is to format battle analysis data into a clean, structured JSON that the frontend
can render directly.

Given player party data, trainer party data, and a strategy, output this exact JSON structure:

{
  "player": {
    "trainer_name": "...",
    "party": [
      {
        "nickname": "...",
        "species_name": "...",
        "level": 0,
        "type1": "...",
        "type2": "...",
        "hp_current": 0,
        "hp_max": 0,
        "hp_percent": 0.0,
        "is_fainted": false,
        "moves": [{"name": "...", "type": "...", "power": 0}],
        "sprite_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/<dex_id>.png",
        "strategy_role": "lead | support | closer | bench",
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
        "level": 0,
        "type1": "...",
        "type2": "...",
        "moves": [],
        "sprite_url": "...",
        "danger_level": "low | medium | high"
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

Use the species_id to build the sprite URL. Always include all fields.
Set danger_level based on the strategy's danger_pokemon list and matchup risk levels."""


def format_for_display(
    player_data: dict,
    trainer_data: dict,
    strategy_data: dict,
) -> dict:
    """
    Returns: { success, data: display dict, error }
    """
    context = json.dumps({
        "player_data": player_data,
        "trainer_data": trainer_data,
        "strategy_data": strategy_data,
    }, indent=2)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": (
                    "Format this data for frontend display. Output only the JSON object, "
                    "no other text.\n\n" + context
                ),
            }
        ],
    )

    raw = "".join(block.text for block in response.content if hasattr(block, "text"))

    try:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        display_data = json.loads(raw[start:end])
        return {"success": True, "data": display_data}
    except Exception as e:
        return {"success": False, "data": None, "error": f"JSON parse error: {e}", "raw": raw}
