"""
Calculator agent — given player party + trainer party JSON, calculates the optimal
no-item Nuzlocke battle strategy.
"""

import json
from src.agents._client import chat
from src.tools.damage_calc import best_move_against, estimate_turns_to_ko, speed_order, type_weaknesses

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calc_damage",
            "description": "Calculate min/max/avg damage for each of the attacker's moves against the defender. Returns moves sorted by average damage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "attacker": {"type": "object", "description": "Attacker dict with level, atk, spa, type1, type2, moves"},
                    "defender": {"type": "object", "description": "Defender dict with current_hp, def, spd, type1, type2"},
                },
                "required": ["attacker", "defender"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calc_speed_order",
            "description": "Determine which Pokémon attacks first based on Speed stat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pokemon_a": {"type": "object", "description": "Pokémon A with spe stat"},
                    "pokemon_b": {"type": "object", "description": "Pokémon B with spe stat"},
                },
                "required": ["pokemon_a", "pokemon_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calc_turns_to_ko",
            "description": "Estimate turns each side needs to KO the other using their best move.",
            "parameters": {
                "type": "object",
                "properties": {
                    "attacker": {"type": "object"},
                    "defender": {"type": "object"},
                },
                "required": ["attacker", "defender"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_type_weaknesses",
            "description": "Get all non-neutral type effectiveness values against a Pokémon's type combo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "type1": {"type": "string"},
                    "type2": {"type": "string"},
                },
                "required": ["type1"],
            },
        },
    },
]

SYSTEM_PROMPT = """You are the Calculator agent for a Pokémon Nuzlocke assistant.
Produce the optimal battle strategy to defeat the next trainer without losing any Pokémon.

Rules:
1. Never recommend items (Potions, X-items). Held items are fine.
2. Prioritise Pokémon survival above all else.
3. Use calc_speed_order to know who moves first.
4. Plan around worst-case damage (min player damage, max opponent damage).
5. Recommend switching if a matchup is dangerous.
6. Account for Pokémon already at low HP.

Use the tools to run calculations, then output ONLY this JSON (no other text):
{
  "lead_recommendation": "<species or nickname>",
  "lead_reasoning": "<why>",
  "matchups": [
    {
      "player_pokemon": "<name>",
      "opponent_pokemon": "<name>",
      "recommended_move": "<move name>",
      "risk_level": "safe|caution|dangerous",
      "notes": "<e.g. switch out if below X HP>"
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

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"Calculate the Nuzlocke strategy:\n\n{context}"},
    ]

    while True:
        response = chat(messages, tools=TOOLS)
        msg = response.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                result = _run_tool(tc.function.name, args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        else:
            summary = msg.content or ""
            strategy_data = None
            try:
                start = summary.find("{")
                end = summary.rfind("}") + 1
                if start >= 0 and end > start:
                    strategy_data = json.loads(summary[start:end])
            except Exception:
                pass
            return {"success": True, "data": strategy_data, "summary": summary}
