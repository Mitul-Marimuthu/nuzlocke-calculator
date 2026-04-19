"""
Calculator agent — given player party + trainer party JSON, calculates the optimal
no-item Nuzlocke battle strategy.
"""

import json
import os
from google import genai
from google.genai import types
from src.tools.damage_calc import best_move_against, estimate_turns_to_ko, speed_order, type_weaknesses

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash"

TOOLS = [{
    "function_declarations": [
        {
            "name": "calc_damage",
            "description": "Calculate min/max/avg damage for each of the attacker's moves against the defender.",
            "parameters": {
                "type": "object",
                "properties": {
                    "attacker": {"type": "object", "description": "Attacker dict: level, atk, spa, type1, type2, moves"},
                    "defender": {"type": "object", "description": "Defender dict: current_hp, def, spd, type1, type2"},
                },
                "required": ["attacker", "defender"],
            },
        },
        {
            "name": "calc_speed_order",
            "description": "Determine which Pokémon attacks first.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pokemon_a": {"type": "object", "description": "Pokémon A with spe stat"},
                    "pokemon_b": {"type": "object", "description": "Pokémon B with spe stat"},
                },
                "required": ["pokemon_a", "pokemon_b"],
            },
        },
        {
            "name": "calc_turns_to_ko",
            "description": "Estimate turns each side needs to KO the other.",
            "parameters": {
                "type": "object",
                "properties": {
                    "attacker": {"type": "object"},
                    "defender": {"type": "object"},
                },
                "required": ["attacker", "defender"],
            },
        },
        {
            "name": "get_type_weaknesses",
            "description": "Get all type effectiveness values for a Pokémon's type combo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type1": {"type": "string"},
                    "type2": {"type": "string"},
                },
                "required": ["type1"],
            },
        },
    ]
}]

SYSTEM_PROMPT = """You are the Calculator agent for a Pokémon Nuzlocke assistant.
Produce the optimal battle strategy to defeat the next trainer without losing any Pokémon.

Rules:
1. Never recommend items (Potions, X-items). Held items are fine.
2. Prioritise Pokémon survival above all else.
3. Use calc_speed_order to know who moves first.
4. Use worst-case damage (min player damage, max opponent damage).
5. Recommend switching if a matchup is dangerous.
6. Account for low-HP Pokémon.

Use the tools to run calculations, then output ONLY this JSON:
{
  "lead_recommendation": "<species_name>",
  "lead_reasoning": "<why>",
  "matchups": [
    {
      "player_pokemon": "<name>",
      "opponent_pokemon": "<name>",
      "recommended_move": "<move>",
      "risk_level": "safe|caution|dangerous",
      "notes": "<e.g. switch if below X HP>"
    }
  ],
  "overall_notes": "<general advice>",
  "danger_pokemon": ["<names of highest-risk opponent mons>"]
}"""


def _run_tool(name: str, args: dict) -> str:
    try:
        if name == "calc_damage":
            return json.dumps({"success": True, "data": best_move_against(args["attacker"], args["defender"])})
        if name == "calc_speed_order":
            return json.dumps({"success": True, "data": {"goes_first": speed_order(args["pokemon_a"], args["pokemon_b"])}})
        if name == "calc_turns_to_ko":
            return json.dumps({"success": True, "data": estimate_turns_to_ko(args["attacker"], args["defender"])})
        if name == "get_type_weaknesses":
            return json.dumps({"success": True, "data": type_weaknesses(args["type1"], args.get("type2"))})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})
    return json.dumps({"success": False, "error": f"Unknown tool: {name}"})


def calculate_strategy(player_party: list[dict], trainer_party: list[dict]) -> dict:
    context = json.dumps({"player_party": player_party, "opponent_party": trainer_party}, indent=2)

    contents = [{
        "role": "user",
        "parts": [{"text": f"Calculate the Nuzlocke strategy for this battle:\n\n{context}"}],
    }]
    config = types.GenerateContentConfig(tools=TOOLS, system_instruction=SYSTEM_PROMPT)

    while True:
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)
        candidate = response.candidates[0]

        model_parts = []
        fn_calls = []
        for part in candidate.content.parts:
            if hasattr(part, "function_call") and part.function_call:
                fn_calls.append(part)
                model_parts.append({
                    "function_call": {"name": part.function_call.name, "args": dict(part.function_call.args)}
                })
            elif hasattr(part, "text") and part.text:
                model_parts.append({"text": part.text})

        contents.append({"role": "model", "parts": model_parts})

        if not fn_calls:
            summary = " ".join(p["text"] for p in model_parts if "text" in p)
            strategy_data = None
            try:
                start = summary.find("{")
                end = summary.rfind("}") + 1
                if start >= 0 and end > start:
                    strategy_data = json.loads(summary[start:end])
            except Exception:
                pass
            return {"success": True, "data": strategy_data, "summary": summary}

        fn_results = []
        for part in fn_calls:
            name = part.function_call.name
            args = dict(part.function_call.args)
            fn_results.append({
                "function_response": {"name": name, "response": {"result": _run_tool(name, args)}}
            })

        contents.append({"role": "user", "parts": fn_results})
