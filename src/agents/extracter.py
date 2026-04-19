"""
Extracter agent — parses a .sav file and returns the player's party as JSON.
"""

import json
import os
from google import genai
from google.genai import types
from src.tools.sav_parser import parse_save, PokemonData

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-2.0-flash"

TOOLS = [{
    "function_declarations": [{
        "name": "parse_sav_file",
        "description": (
            "Parse a Pokémon Emerald .sav file and return the player's party "
            "Pokémon with their levels, moves, types, and stats."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sav_hex": {
                    "type": "string",
                    "description": "Hex-encoded bytes of the .sav file",
                },
            },
            "required": ["sav_hex"],
        },
    }]
}]

SYSTEM_PROMPT = """You are the Extracter agent for a Pokémon Nuzlocke assistant.
Parse the player's save file using the parse_sav_file tool, then summarise each
Pokémon (name, level, types, moves, HP). Never fabricate party data — always call the tool."""


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


def _run_tool(name: str, args: dict) -> str:
    if name == "parse_sav_file":
        try:
            sav_bytes = bytes.fromhex(args["sav_hex"])
            save = parse_save(sav_bytes)
            return json.dumps({
                "success": True,
                "data": {
                    "trainer_name": save.trainer_name,
                    "trainer_gender": save.trainer_gender,
                    "trainer_id": save.trainer_id,
                    "party": [_pokemon_to_dict(p) for p in save.party],
                },
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    return json.dumps({"success": False, "error": f"Unknown tool: {name}"})


def extract_party(sav_bytes: bytes) -> dict:
    sav_hex = sav_bytes.hex()
    contents = [{
        "role": "user",
        "parts": [{"text": f"Parse this save file. Call parse_sav_file with sav_hex={sav_hex!r}"}],
    }]
    config = types.GenerateContentConfig(tools=TOOLS, system_instruction=SYSTEM_PROMPT)

    last_result: dict | None = None

    while True:
        response = client.models.generate_content(model=MODEL, contents=contents, config=config)
        candidate = response.candidates[0]

        # Collect model parts for history
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
            summary = " ".join(
                p["text"] for p in model_parts if "text" in p
            )
            return {
                "success": last_result is not None and last_result.get("success", False),
                "data": last_result["data"] if last_result else None,
                "summary": summary,
                "error": last_result.get("error") if last_result else "No tool result",
            }

        fn_results = []
        for part in fn_calls:
            name = part.function_call.name
            args = dict(part.function_call.args)
            result_str = _run_tool(name, args)
            parsed = json.loads(result_str)
            if parsed.get("success"):
                last_result = parsed
            fn_results.append({
                "function_response": {"name": name, "response": {"result": result_str}}
            })

        contents.append({"role": "user", "parts": fn_results})
