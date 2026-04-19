import json
from pathlib import Path
from functools import lru_cache

_CACHE = Path(__file__).parent / "cache"


@lru_cache(maxsize=1)
def load_species() -> dict:
    p = _CACHE / "gen3_species.json"
    if not p.exists():
        raise FileNotFoundError("Species cache missing. Run: python -m src.data.populate")
    return json.loads(p.read_text())


@lru_cache(maxsize=1)
def load_moves() -> dict:
    p = _CACHE / "gen3_moves.json"
    if not p.exists():
        raise FileNotFoundError("Moves cache missing. Run: python -m src.data.populate")
    return json.loads(p.read_text())


def get_species(dex_id: int) -> dict | None:
    return load_species().get(str(dex_id))


def get_move(move_id: int) -> dict | None:
    return load_moves().get(str(move_id))
