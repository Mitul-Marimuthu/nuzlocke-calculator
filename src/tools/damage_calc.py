"""
Gen 3 damage formula and battle analysis utilities.
Physical/Special split is type-based in Gen 3 (not per-move like Gen 4+).
"""

import math
from src.data.type_chart import get_effectiveness, TYPES

# Types that are Physical in Gen 3
PHYSICAL_TYPES = {"Normal", "Fighting", "Poison", "Ground", "Flying", "Bug", "Rock", "Ghost", "Steel"}
SPECIAL_TYPES = {"Fire", "Water", "Grass", "Electric", "Ice", "Psychic", "Dragon", "Dark"}


def is_physical(move_type: str) -> bool:
    return move_type in PHYSICAL_TYPES


def calc_damage(
    attacker_level: int,
    attacker_atk: int,
    attacker_spa: int,
    move_power: int,
    move_type: str,
    attacker_type1: str,
    attacker_type2: str | None,
    defender_def: int,
    defender_spd: int,
    defender_type1: str,
    defender_type2: str | None = None,
    critical: bool = False,
) -> dict:
    """
    Returns a dict with min/max/average damage, and type effectiveness multiplier.
    Uses the standard Gen 3 damage formula with ±15% random range.
    """
    if move_power is None or move_power == 0:
        return {"min": 0, "max": 0, "avg": 0, "effectiveness": 1.0, "is_ohko": False}

    physical = is_physical(move_type)
    a_stat = attacker_atk if physical else attacker_spa
    d_stat = defender_def if physical else defender_spd

    if critical:
        crit_multiplier = 2
    else:
        crit_multiplier = 1

    # STAB bonus
    stab = 1.5 if (move_type == attacker_type1 or move_type == attacker_type2) else 1.0

    # Type effectiveness
    effectiveness = get_effectiveness(move_type, defender_type1, defender_type2)

    # Base damage (before random roll)
    base = math.floor(
        math.floor(
            math.floor(2 * attacker_level / 5 + 2) * move_power * a_stat / d_stat
        ) / 50
    ) + 2

    base = math.floor(base * crit_multiplier * stab * effectiveness)

    # Gen 3 random range: 85/100 to 100/100 (integer rolls 217–255 / 255)
    min_dmg = math.floor(base * 85 / 100)
    max_dmg = base  # roll of 255/255 = ×1.0

    return {
        "min": min_dmg,
        "max": max_dmg,
        "avg": round((min_dmg + max_dmg) / 2),
        "effectiveness": effectiveness,
        "stab": stab > 1.0,
        "physical": physical,
        "is_ohko": False,  # flagged by caller based on target HP
    }


def best_move_against(
    attacker: dict,
    defender: dict,
) -> list[dict]:
    """
    Score each of the attacker's moves against the defender.
    Returns moves sorted by average expected damage, descending.
    """
    scored = []
    for move in attacker.get("moves", []):
        if not move.get("power"):
            continue

        result = calc_damage(
            attacker_level=attacker["level"],
            attacker_atk=attacker["atk"],
            attacker_spa=attacker["spa"],
            move_power=move["power"],
            move_type=move["type"],
            attacker_type1=attacker["type1"],
            attacker_type2=attacker.get("type2"),
            defender_def=defender["def"],
            defender_spd=defender["spd"],
            defender_type1=defender["type1"],
            defender_type2=defender.get("type2"),
        )
        scored.append({**move, **result})

    scored.sort(key=lambda m: m["avg"], reverse=True)
    return scored


def speed_order(pokemon_a: dict, pokemon_b: dict) -> str:
    """Returns 'a', 'b', or 'tie' indicating who moves first."""
    sa, sb = pokemon_a["spe"], pokemon_b["spe"]
    if sa > sb:
        return "a"
    if sb > sa:
        return "b"
    return "tie"


def estimate_turns_to_ko(attacker: dict, defender: dict) -> dict:
    """
    Estimate how many turns it takes each side to KO the other,
    using the best available damaging move.
    """
    def turns(atk: dict, dfn: dict) -> float | None:
        moves = best_move_against(atk, dfn)
        if not moves:
            return None
        best_avg = moves[0]["avg"]
        if best_avg <= 0:
            return None
        return math.ceil(dfn["current_hp"] / best_avg)

    return {
        "attacker_turns": turns(attacker, defender),
        "defender_turns": turns(defender, attacker),
    }


def type_weaknesses(type1: str, type2: str | None = None) -> dict:
    """Return all attacking types and their effectiveness against a given type combo."""
    result = {}
    for t in TYPES:
        eff = get_effectiveness(t, type1, type2)
        if eff != 1.0:
            result[t] = eff
    return result
