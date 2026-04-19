"""
Extracter agent — parses a .sav file and returns the player's party as JSON.
Wraps sav_parser as a Claude tool so the LLM can call it.
"""

import json
import os
import anthropic
from src.tools.sav_parser import parse_save, PokemonData, SaveData

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"

# ── Tool definition ────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "parse_sav_file",
        "description": (
            "Parse a Pokémon Emerald .sav file and return the player's party "
            "Pokémon with their levels, moves, types, and stats."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sav_hex": {
                    "type": "string",
                    "description": "Hex-encoded bytes of the .sav file",
                },
            },
            "required": ["sav_hex"],
        },
    }
]


def _pokemon_to_dict(p: PokemonData) -> dict:
    return {
        "slot": p.slot,
        "nickname": p.nickname,
        "species_id": p.species_id,
        "species_name": p.species_name,
        "type1": p.type1,
        "type2": p.type2,
        "level": p.level,
        "current_hp": p.current_hp,
        "max_hp": p.max_hp,
        "atk": p.atk,
        "def": p.def_,
        "spa": p.spa,
        "spd": p.spd,
        "spe": p.spe,
        "moves": p.moves,
        "held_item_id": p.held_item_id,
        "experience": p.experience,
        "friendship": p.friendship,
        "ivs": p.ivs,
        "evs": p.evs,
        "is_fainted": p.is_fainted,
    }


def _run_tool(tool_name: str, tool_input: dict) -> str:
    if tool_name == "parse_sav_file":
        try:
            sav_bytes = bytes.fromhex(tool_input["sav_hex"])
            save = parse_save(sav_bytes)
            result = {
                "success": True,
                "data": {
                    "trainer_name": save.trainer_name,
                    "trainer_gender": save.trainer_gender,
                    "trainer_id": save.trainer_id,
                    "party": [_pokemon_to_dict(p) for p in save.party],
                },
            }
        except Exception as e:
            result = {"success": False, "error": str(e)}
        return json.dumps(result)
    return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})


# ── Agent loop ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Extracter agent for a Pokémon Nuzlocke assistant.
Your job is to parse the player's save file and return a clean JSON summary of their party.
Use the parse_sav_file tool. After parsing, return a brief summary of each Pokémon
(name, level, types, moves, HP) in plain language so the user can verify correctness.
Always call the tool — never guess or fabricate party data."""


def extract_party(sav_bytes: bytes) -> dict:
    """
    Given raw .sav file bytes, returns:
    { success, data: { trainer_name, trainer_gender, trainer_id, party: [...] }, summary: str }
    """
    sav_hex = sav_bytes.hex()
    messages = [
        {
            "role": "user",
            "content": f"Parse this save file and return the player's party. sav_hex length: {len(sav_hex)} chars.",
        }
    ]

    # Inject hex as a tool input context to avoid passing it through the LLM text
    messages[0]["content"] += (
        f"\n\nPlease call parse_sav_file with sav_hex={sav_hex!r}"
    )

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
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
            # Retrieve the parsed data from the last tool result
            last_result = None
            for msg in reversed(messages):
                if isinstance(msg["content"], list):
                    for item in msg["content"]:
                        if isinstance(item, dict) and item.get("type") == "tool_result":
                            last_result = json.loads(item["content"])
                            break
                if last_result:
                    break

            return {
                "success": last_result.get("success", False) if last_result else False,
                "data": last_result.get("data") if last_result else None,
                "summary": summary,
                "error": last_result.get("error") if last_result else "No tool result found",
            }
        else:
            return {"success": False, "error": f"Unexpected stop_reason: {response.stop_reason}"}
