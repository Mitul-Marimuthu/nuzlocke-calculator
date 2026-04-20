"""Extracter agent — kept for completeness; binary parsing now done directly in api/main.py."""

import json
from src.agents._client import chat
from src.tools.sav_parser import parse_save, PokemonData


def _pokemon_to_dict(p: PokemonData) -> dict:
    return {
        "slot": p.slot, "nickname": p.nickname, "species_id": p.species_id,
        "species_name": p.species_name, "type1": p.type1, "type2": p.type2,
        "level": p.level, "current_hp": p.current_hp, "max_hp": p.max_hp,
        "atk": p.atk, "def": p.def_, "spa": p.spa, "spd": p.spd, "spe": p.spe,
        "moves": p.moves, "held_item_id": p.held_item_id, "experience": p.experience,
        "friendship": p.friendship, "ivs": p.ivs, "evs": p.evs, "is_fainted": p.is_fainted,
    }


def extract_party(sav_bytes: bytes) -> dict:
    try:
        save = parse_save(sav_bytes)
        data = {
            "trainer_name": save.trainer_name,
            "trainer_gender": save.trainer_gender,
            "trainer_id": save.trainer_id,
            "party": [_pokemon_to_dict(p) for p in save.party],
        }
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

    # Optional LLM summary
    response = chat(messages=[
        {"role": "system", "content": "Summarise this Pokémon party in 2-3 sentences for a Nuzlocke player."},
        {"role": "user",   "content": json.dumps(data)},
    ])
    return {"success": True, "data": data, "summary": response.choices[0].message.content}
