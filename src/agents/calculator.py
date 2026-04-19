"""
Calculator agent — given player party + trainer party JSON, calculates the optimal
no-item battle strategy for a Nuzlocke run.
"""

import json
import os
import anthropic
from src.tools.damage_calc import best_move_against, estimate_turns_to_ko, speed_order, type_weaknesses

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"

# ── Tool definitions ───────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "calc_damage",
        "description": (
            "Calculate min/max/average damage for each of the attacker's moves "
            "against the defender. Returns moves sorted by average damage."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "attacker": {
                    "type": "object",
                    "description": "Attacker Pokémon dict with level, atk, spa, type1, type2, moves",
                },
                "defender": {
                    "type": "object",
                    "description": "Defender Pokémon dict with current_hp, def, spd, type1, type2",
                },
            },
            "required": ["attacker", "defender"],
        },
    },
    {
        "name": "calc_speed_order",
        "description": "Determine which Pokémon attacks first based on Speed stat.",
        "input_schema": {
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
        "description": "Estimate how many turns each side needs to KO the other.",
        "input_schema": {
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
        "description": "Get all type effectiveness values for a Pokémon's type combination.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type1": {"type": "string"},
                "type2": {"type": "string", "description": "Optional second type"},
            },
            "required": ["type1"],
        },
    },
]


def _run_tool(tool_name: str, tool_input: dict) -> str:
    try:
        if tool_name == "calc_damage":
            result = best_move_against(tool_input["attacker"], tool_input["defender"])
            return json.dumps({"success": True, "data": result})

        elif tool_name == "calc_speed_order":
            result = speed_order(tool_input["pokemon_a"], tool_input["pokemon_b"])
            return json.dumps({"success": True, "data": {"goes_first": result}})

        elif tool_name == "calc_turns_to_ko":
            result = estimate_turns_to_ko(tool_input["attacker"], tool_input["defender"])
            return json.dumps({"success": True, "data": result})

        elif tool_name == "get_type_weaknesses":
            result = type_weaknesses(tool_input["type1"], tool_input.get("type2"))
            return json.dumps({"success": True, "data": result})

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

    return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})


# ── Agent loop ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Calculator agent for a Pokémon Nuzlocke assistant.
Your job is to produce the optimal battle strategy for the player to defeat the next trainer
without losing any Pokémon (a Nuzlocke death is permanent).

Rules you MUST follow:
1. Never recommend using items (Potions, X-items, etc.) — held items are fine.
2. Prioritize Pokémon survival above all else, even if it makes the battle slower.
3. Consider speed to know if the player moves first or gets hit first.
4. Consider worst-case damage (minimum damage from player, maximum damage from opponent).
5. Recommend switching out if a matchup is dangerous, even if it costs a turn.
6. Account for fainting: if a Pokémon is already at low HP, factor that in.

Use the calc_damage, calc_speed_order, calc_turns_to_ko, and get_type_weaknesses tools
to do the math before making any recommendation.

Output a JSON strategy with this structure:
{
  "lead_recommendation": "<species_name>",
  "lead_reasoning": "<why this lead>",
  "matchups": [
    {
      "player_pokemon": "<name>",
      "opponent_pokemon": "<name>",
      "recommended_move": "<move>",
      "risk_level": "safe|caution|dangerous",
      "notes": "<e.g. switch out if below X HP>"
    }
  ],
  "overall_notes": "<general advice>",
  "danger_pokemon": ["<names of opponent mons that pose highest risk>"]
}"""


def calculate_strategy(player_party: list[dict], trainer_party: list[dict]) -> dict:
    """
    Returns: { success, data: strategy dict, summary: str }
    """
    context = json.dumps({
        "player_party": player_party,
        "opponent_party": trainer_party,
    }, indent=2)

    messages = [
        {
            "role": "user",
            "content": (
                "Calculate the optimal Nuzlocke strategy for this battle.\n\n"
                f"Battle data:\n{context}\n\n"
                "Use the tools to run damage calculations, check speed order, and assess "
                "type matchups before finalizing the strategy. Output the final strategy as JSON."
            ),
        }
    ]

    strategy_data = None

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_str = _run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            summary = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            # Try to extract the JSON strategy from the summary
            try:
                start = summary.find("{")
                end = summary.rfind("}") + 1
                if start >= 0 and end > start:
                    strategy_data = json.loads(summary[start:end])
            except Exception:
                strategy_data = None

            return {
                "success": True,
                "data": strategy_data,
                "summary": summary,
            }
        else:
            return {"success": False, "error": f"Unexpected stop_reason: {response.stop_reason}"}
