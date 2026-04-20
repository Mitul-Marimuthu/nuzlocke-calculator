"""Researcher agent — kept for completeness; binary parsing now done directly in api/main.py."""

import json
from src.agents._client import chat
from src.tools.gba_parser import get_trainer_by_index, search_trainers, get_all_trainers, TrainerData


def _trainer_to_dict(t: TrainerData) -> dict:
    return {
        "trainer_index": t.trainer_index, "name": t.name,
        "trainer_class": t.trainer_class, "is_double": t.is_double,
        "party": [
            {"species_id": p.species_id, "species_name": p.species_name,
             "type1": p.type1, "type2": p.type2, "level": p.level,
             "iv_value": p.iv_value, "held_item_id": p.held_item_id, "moves": p.moves}
            for p in t.party
        ],
    }


def research_next_trainer(rom_bytes: bytes, trainer_hint: str | int | None = None) -> dict:
    try:
        trainer: TrainerData | None = None
        if isinstance(trainer_hint, int):
            trainer = get_trainer_by_index(rom_bytes, trainer_hint)
        elif isinstance(trainer_hint, str):
            results = search_trainers(rom_bytes, trainer_hint)
            trainer = results[0] if results else None
        if trainer is None:
            all_t = get_all_trainers(rom_bytes)
            trainer = all_t[0] if all_t else None
        if trainer is None:
            return {"success": False, "data": None, "error": "No trainer found"}
        data = _trainer_to_dict(trainer)
    except Exception as e:
        return {"success": False, "data": None, "error": str(e)}

    response = chat(messages=[
        {"role": "system", "content": "Summarise this trainer's team threat level in 2-3 sentences for a Nuzlocke player."},
        {"role": "user",   "content": json.dumps(data)},
    ])
    return {"success": True, "data": data, "summary": response.choices[0].message.content}
