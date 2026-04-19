"""
Researcher agent — given a .gba ROM (and optional trainer hint),
returns the next trainer the player will face as JSON.
"""

import json
import os
from google import genai
from google.genai import types
from src.tools.gba_parser import (
    get_all_trainers, get_trainer_by_index, search_trainers, TrainerData,
)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash"

TOOLS = [{
    "function_declarations": [
        {
            "name": "get_trainer_by_index",
            "description": "Look up a specific trainer by their index in the trainer table.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rom_hex": {"type": "string", "description": "Hex-encoded .gba ROM bytes"},
                    "trainer_index": {"type": "integer", "description": "Trainer table index (0–854)"},
                },
                "required": ["rom_hex", "trainer_index"],
            },
        },
        {
            "name": "search_trainers_by_name",
            "description": "Search for trainers whose name contains the given string.",
            "parameters": {
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
            "description": "Get a summary list of trainers (index, name, class, party count).",
            "parameters": {
                "type": "object",
                "properties": {
                    "rom_hex": {"type": "string", "description": "Hex-encoded .gba ROM bytes"},
                    "offset": {"type": "integer", "description": "Start index"},
                    "limit":  {"type": "integer", "description": "Max results"},
                },
                "required": ["rom_hex"],
            },
        },
    ]
}]

SYSTEM_PROMPT = """You are the Researcher agent for a Pokémon Nuzlocke assistant.
Identify the next trainer the player will face using the provided tools.
Return the trainer's name, class, double-battle flag, and full party details.
Never fabricate trainer data — always use the tools."""


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


def _run_tool(name: str, args: dict, rom_bytes: bytes) -> str:
    try:
        if name == "get_trainer_by_index":
            t = get_trainer_by_index(rom_bytes, args["trainer_index"])
            if not t:
                return json.dumps({"success": False, "error": "Trainer not found"})
            return json.dumps({"success": True, "data": _trainer_to_dict(t)})

        if name == "search_trainers_by_name":
            results = search_trainers(rom_bytes, args["name"])
            return json.dumps({"success": True, "data": [_trainer_to_dict(t) for t in results[:10]]})

        if name == "list_trainers_summary":
            all_t = get_all_trainers(rom_bytes)
            offset = args.get("offset", 0)
            limit = args.get("limit", 50)
            summary = [
                {"index": t.trainer_index, "name": t.name, "class": t.trainer_class, "party_count": len(t.party)}
                for t in all_t[offset: offset + limit]
            ]
            return json.dumps({"success": True, "data": summary, "total": len(all_t)})

    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

    return json.dumps({"success": False, "error": f"Unknown tool: {name}"})


def research_next_trainer(rom_bytes: bytes, trainer_hint: str | int | None = None) -> dict:
    rom_hex = rom_bytes.hex()

    if isinstance(trainer_hint, int):
        hint_text = f"The next trainer has index {trainer_hint}."
    elif isinstance(trainer_hint, str):
        hint_text = f"The next trainer's name is '{trainer_hint}'."
    else:
        hint_text = "Unknown next trainer — list trainers to identify who comes next."

    contents = [{
        "role": "user",
        "parts": [{"text": f"{hint_text}\nUse the tools. Pass rom_hex={rom_hex!r} to any tool."}],
    }]
    config = types.GenerateContentConfig(tools=TOOLS, system_instruction=SYSTEM_PROMPT)

    last_trainer: dict | None = None

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
            return {
                "success": last_trainer is not None,
                "data": last_trainer,
                "summary": summary,
                "error": None if last_trainer else "Could not identify trainer",
            }

        fn_results = []
        for part in fn_calls:
            name = part.function_call.name
            args = dict(part.function_call.args)
            result_str = _run_tool(name, args, rom_bytes)
            parsed = json.loads(result_str)
            if parsed.get("success") and isinstance(parsed.get("data"), dict) and "trainer_index" in parsed["data"]:
                last_trainer = parsed["data"]
            fn_results.append({
                "function_response": {"name": name, "response": {"result": result_str}}
            })

        contents.append({"role": "user", "parts": fn_results})
