"""
Fetches Gen 3 species and move data from PokeAPI and caches them locally.
Run once before using the tool: python -m src.data.populate
"""

import json
import asyncio
import httpx
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "cache"
SPECIES_FILE = CACHE_DIR / "gen3_species.json"
MOVES_FILE = CACHE_DIR / "gen3_moves.json"

# Gen 3 national dex range
GEN3_SPECIES_IDS = range(1, 387)   # 1–386
GEN3_MOVE_IDS = range(1, 355)       # 1–354


async def fetch_species(client: httpx.AsyncClient, dex_id: int) -> dict | None:
    try:
        r = await client.get(f"https://pokeapi.co/api/v2/pokemon/{dex_id}")
        r.raise_for_status()
        data = r.json()

        types = [t["type"]["name"].capitalize() for t in data["types"]]
        stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}

        return {
            "id": dex_id,
            "name": data["name"].capitalize(),
            "type1": types[0],
            "type2": types[1] if len(types) > 1 else None,
            "hp": stats.get("hp", 0),
            "atk": stats.get("attack", 0),
            "def": stats.get("defense", 0),
            "spa": stats.get("special-attack", 0),
            "spd": stats.get("special-defense", 0),
            "spe": stats.get("speed", 0),
        }
    except Exception as e:
        print(f"  Failed species {dex_id}: {e}")
        return None


async def fetch_move(client: httpx.AsyncClient, move_id: int) -> dict | None:
    try:
        r = await client.get(f"https://pokeapi.co/api/v2/move/{move_id}")
        r.raise_for_status()
        data = r.json()

        return {
            "id": move_id,
            "name": data["name"].replace("-", " ").title(),
            "type": data["type"]["name"].capitalize(),
            "power": data["power"],
            "accuracy": data["accuracy"],
            "pp": data["pp"],
            "damage_class": data["damage_class"]["name"],  # physical / special / status
        }
    except Exception as e:
        print(f"  Failed move {move_id}: {e}")
        return None


async def populate():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Fetching species data (386 Pokémon)...")
        tasks = [fetch_species(client, i) for i in GEN3_SPECIES_IDS]
        results = await asyncio.gather(*tasks)
        species = {str(r["id"]): r for r in results if r}
        SPECIES_FILE.write_text(json.dumps(species, indent=2))
        print(f"  Saved {len(species)} species → {SPECIES_FILE}")

        print("Fetching move data (354 moves)...")
        tasks = [fetch_move(client, i) for i in GEN3_MOVE_IDS]
        results = await asyncio.gather(*tasks)
        moves = {str(r["id"]): r for r in results if r}
        MOVES_FILE.write_text(json.dumps(moves, indent=2))
        print(f"  Saved {len(moves)} moves → {MOVES_FILE}")

    print("Done. Run the API server now.")


if __name__ == "__main__":
    asyncio.run(populate())
