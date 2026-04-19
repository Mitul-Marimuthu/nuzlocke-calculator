"""
Researcher agent — given a .gba ROM (and optional trainer index hint),
returns the next trainer the player will face as JSON.
"""

import json
import os
import anthropic
from src.tools.gba_parser import (
    get_all_trainers, get_trainer_by_index, search_trainers,
    TrainerData, TrainerPokemon,
)

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"

# ── Tool definitions ───────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "get_trainer_by_index",
        "description": "Look up a specific trainer by their index in the trainer table.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rom_hex": {"type": "string", "description": "Hex-encoded .gba ROM bytes"},
                "trainer_index": {"type": "integer", "description": "Trainer table index (0-854)"},
            },
            "required": ["rom_hex", "trainer_index"],
        },
    },
    {
        "name": "search_trainers_by_name",
        "description": "Search for trainers whose name contains the given string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rom_hex": {"type": "string", "description": "Hex-encoded .gba ROM bytes"},
                "name": {"type": "string", "description": "Trainer name to search for"},
            },
            "required": ["rom_hex", "name"],
        },
    },
    {
        "name": "list_trainers_summary",
        "description": "Get a summary list of all trainers (index, name, class, party count). Use to browse before picking the next one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rom_hex": {"type": "string", "description": "Hex-encoded .gba ROM bytes"},
                "offset": {"type": "integer", "description": "Start listing from this index", "default": 0},
                "limit": {"type": "integer", "description": "Max trainers to return", "default": 50},
            },
            "required": ["rom_hex"],
        },
    },
]


def _trainer_to_dict(t: TrainerData) -> dict:
    return {
        "trainer_index": t.trainer_index,
        "name": t.name,
        "trainer_class": t.trainer_class,
        "is_double": t.is_double,
        "party": [
            {
                "species_id": p.species_id,
                "species_name": p.species_name,
                "type1": p.type1,
                "type2": p.type2,
                "level": p.level,
                "iv_value": p.iv_value,
                "held_item_id": p.held_item_id,
                "moves": p.moves,
            }
            for p in t.party
        ],
    }


def _run_tool(tool_name: str, tool_input: dict, rom_bytes: bytes) -> str:
    try:
        if tool_name == "get_trainer_by_index":
            t = get_trainer_by_index(rom_bytes, tool_input["trainer_index"])
            if not t:
                return json.dumps({"success": False, "error": "Trainer not found"})
            return json.dumps({"success": True, "data": _trainer_to_dict(t)})

        elif tool_name == "search_trainers_by_name":
            results = search_trainers(rom_bytes, tool_input["name"])
            return json.dumps({
                "success": True,
                "data": [_trainer_to_dict(t) for t in results[:10]],
            })

        elif tool_name == "list_trainers_summary":
            all_t = get_all_trainers(rom_bytes)
            offset = tool_input.get("offset", 0)
            limit = tool_input.get("limit", 50)
            summary = [
                {"index": t.trainer_index, "name": t.name, "class": t.trainer_class, "party_count": len(t.party)}
                for t in all_t[offset: offset + limit]
            ]
            return json.dumps({"success": True, "data": summary, "total": len(all_t)})

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

    return json.dumps({"success": False, "error": f"Unknown tool: {tool_name}"})


# ── Agent loop ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Researcher agent for a Pokémon Nuzlocke assistant.
Your job is to identify the next trainer the player will face and return their full party data.

You have tools to search and browse trainers from the ROM. When the user gives you a trainer
name or index, look them up directly. If uncertain, list trainers near the player's progression
to find the correct one.

Return the trainer's name, class, whether it's a double battle, and full party details
(species, level, types, moves if available). Never fabricate trainer data — always use tools."""


def research_next_trainer(rom_bytes: bytes, trainer_hint: str | int | None = None) -> dict:
    """
    Returns: { success, data: TrainerData dict, summary: str }
    trainer_hint: name string or int index, or None to let the agent decide.
    """
    if isinstance(trainer_hint, int):
        hint_text = f"The next trainer has index {trainer_hint} in the trainer table."
    elif isinstance(trainer_hint, str):
        hint_text = f"The next trainer's name is '{trainer_hint}'."
    else:
        hint_text = "I don't know the exact next trainer. Please list trainers to help identify who comes next."

    # We pass rom_hex out-of-band so the LLM doesn't need to read it as text
    rom_hex = rom_bytes.hex()

    messages = [
        {
            "role": "user",
            "content": (
                f"{hint_text}\n\n"
                f"Use the tools to look up the trainer. Pass rom_hex={rom_hex!r} to any tool."
            ),
        }
    ]

    last_trainer_result = None

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
                    result_str = _run_tool(block.name, block.input, rom_bytes)
                    parsed = json.loads(result_str)
                    if parsed.get("success") and "data" in parsed:
                        if isinstance(parsed["data"], dict) and "trainer_index" in parsed["data"]:
                            last_trainer_result = parsed
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
            return {
                "success": last_trainer_result is not None,
                "data": last_trainer_result["data"] if last_trainer_result else None,
                "summary": summary,
                "error": None if last_trainer_result else "Could not identify trainer",
            }
        else:
            return {"success": False, "error": f"Unexpected stop_reason: {response.stop_reason}"}
