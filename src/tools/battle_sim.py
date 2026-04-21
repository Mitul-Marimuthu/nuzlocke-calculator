"""
Turn-by-turn Gen 3 battle simulator.
Simulates each turn deterministically using damage calc, then returns a full
turn log that the calculator agent annotates.
"""

import copy
import math
from dataclasses import dataclass
from src.tools.damage_calc import calc_damage, best_move_against, speed_order
from src.data.type_chart import get_effectiveness

# Generic move power when a trainer Pokémon has no recorded moveset
_TYPE_MOVE: dict[str, tuple[str, int]] = {
    "Normal":   ("Tackle",           40),
    "Fire":     ("Ember",            40),
    "Water":    ("Water Gun",        40),
    "Electric": ("Thunder Shock",    40),
    "Grass":    ("Vine Whip",        35),
    "Ice":      ("Powder Snow",      40),
    "Fighting": ("Low Kick",         50),
    "Poison":   ("Poison Sting",     15),
    "Ground":   ("Mud Slap",         20),
    "Flying":   ("Gust",             40),
    "Psychic":  ("Confusion",        50),
    "Bug":      ("Leech Life",       20),
    "Rock":     ("Rock Throw",       50),
    "Ghost":    ("Shadow Ball",      80),
    "Dragon":   ("Dragon Rage",      40),
    "Dark":     ("Bite",             60),
    "Steel":    ("Metal Claw",       50),
}
_MAX_TURNS_PER_MATCHUP = 20


@dataclass
class SimTurn:
    turn: int
    matchup: str

    player_pokemon: str
    player_pokemon_species: str
    player_hp_before: int
    player_hp_max: int

    opponent_pokemon: str
    opponent_hp_before: int
    opponent_hp_max: int

    goes_first: str          # "player" | "opponent" | "tie"

    player_action: str       # move name
    player_action_type: str
    player_damage_min: int
    player_damage_max: int
    player_damage_avg: int
    player_effectiveness: float

    opponent_action: str
    opponent_action_type: str
    opponent_damage_min: int
    opponent_damage_max: int
    opponent_damage_avg: int
    opponent_effectiveness: float

    player_hp_after: int
    opponent_hp_after: int

    player_fainted: bool
    opponent_fainted: bool
    is_risky: bool           # opponent worst-case damage > 50 % of player max HP


def _make_generic_move(opponent: dict) -> dict:
    type1 = opponent.get("type1", "Normal")
    name, power = _TYPE_MOVE.get(type1, ("Tackle", 40))
    return {"id": 0, "name": name, "type": type1, "power": power,
            "accuracy": 90, "damage_class": "physical", "pp": 30}


def _opponent_move(opponent: dict, player: dict) -> dict:
    """Return the opponent's best recorded move, or a synthesised generic one."""
    moves = [m for m in opponent.get("moves", []) if m.get("power")]
    if moves:
        scored = best_move_against(opponent, player)
        if scored:
            return scored[0]
    move = _make_generic_move(opponent)
    dmg = calc_damage(
        attacker_level=opponent.get("level", 10),
        attacker_atk=opponent.get("atk", 30),
        attacker_spa=opponent.get("spa", 30),
        move_power=move["power"],
        move_type=move["type"],
        attacker_type1=opponent.get("type1", "Normal"),
        attacker_type2=opponent.get("type2"),
        defender_def=player.get("def", 30),
        defender_spd=player.get("spd", 30),
        defender_type1=player.get("type1", "Normal"),
        defender_type2=player.get("type2"),
    )
    return {**move, **dmg}


def _player_best_move(player: dict, opponent: dict) -> dict | None:
    scored = best_move_against(player, opponent)
    return scored[0] if scored else None


def _simulate_matchup(
    player: dict,
    opponent: dict,
    turn_offset: int,
) -> tuple[list[SimTurn], dict, dict]:
    """
    Simulate one player Pokémon vs one opponent Pokémon.
    Returns (turns, player_state_after, opponent_state_after).
    Both dicts are mutated copies with updated current_hp.
    """
    p = copy.deepcopy(player)
    o = copy.deepcopy(opponent)
    turns: list[SimTurn] = []
    matchup_label = f"{p.get('nickname') or p['species_name']} vs {o['species_name']}"

    for t in range(1, _MAX_TURNS_PER_MATCHUP + 1):
        p_hp_before = p["current_hp"]
        o_hp_before = o["current_hp"]

        # Determine actions
        p_move_data = _player_best_move(p, o)
        o_move_data = _opponent_move(o, p)

        if p_move_data is None:
            break

        # Speed order
        first = speed_order(p, o)   # "a" = player, "b" = opponent, "tie"
        goes_first = "player" if first == "a" else ("tie" if first == "tie" else "opponent")

        # Apply damage in speed order
        p_hp_after = p_hp_before
        o_hp_after = o_hp_before

        def apply_p_move():
            nonlocal o_hp_after
            o_hp_after = max(0, o_hp_after - p_move_data["avg"])

        def apply_o_move():
            nonlocal p_hp_after
            p_hp_after = max(0, p_hp_after - o_move_data["avg"])

        if goes_first in ("player", "tie"):
            apply_p_move()
            if o_hp_after > 0:
                apply_o_move()
        else:
            apply_o_move()
            if p_hp_after > 0:
                apply_p_move()

        p["current_hp"] = p_hp_after
        o["current_hp"] = o_hp_after

        is_risky = o_move_data["max"] >= (p["max_hp"] * 0.5)

        turns.append(SimTurn(
            turn=turn_offset + t,
            matchup=matchup_label,
            player_pokemon=p.get("nickname") or p["species_name"],
            player_pokemon_species=p["species_name"],
            player_hp_before=p_hp_before,
            player_hp_max=p["max_hp"],
            opponent_pokemon=o["species_name"],
            opponent_hp_before=o_hp_before,
            opponent_hp_max=o["max_hp"],
            goes_first=goes_first,
            player_action=p_move_data["name"],
            player_action_type=p_move_data["type"],
            player_damage_min=p_move_data["min"],
            player_damage_max=p_move_data["max"],
            player_damage_avg=p_move_data["avg"],
            player_effectiveness=p_move_data["effectiveness"],
            opponent_action=o_move_data["name"],
            opponent_action_type=o_move_data["type"],
            opponent_damage_min=o_move_data["min"],
            opponent_damage_max=o_move_data["max"],
            opponent_damage_avg=o_move_data["avg"],
            opponent_effectiveness=o_move_data.get("effectiveness", 1.0),
            player_hp_after=p_hp_after,
            opponent_hp_after=o_hp_after,
            player_fainted=(p_hp_after == 0),
            opponent_fainted=(o_hp_after == 0),
            is_risky=is_risky,
        ))

        if p_hp_after == 0 or o_hp_after == 0:
            break

    return turns, p, o


def _pick_lead(player_party: list[dict], first_opponent: dict) -> dict:
    """Pick the player Pokémon with the best average damage against the first opponent."""
    best = None
    best_score = -1
    for p in player_party:
        if p.get("is_fainted") or p["current_hp"] <= 0:
            continue
        scored = best_move_against(p, first_opponent)
        score = scored[0]["avg"] if scored else 0
        if score > best_score:
            best_score = score
            best = p
    return best or player_party[0]


def _pick_best_switch(
    player_party: list[dict],
    current_player: dict,
    opponent: dict,
) -> dict | None:
    """Find the best available player Pokémon (not fainted, not current) for this opponent."""
    best = None
    best_score = -1
    for p in player_party:
        if p["species_name"] == current_player["species_name"]:
            continue
        if p.get("is_fainted") or p["current_hp"] <= 0:
            continue
        scored = best_move_against(p, opponent)
        score = scored[0]["avg"] if scored else 0
        if score > best_score:
            best_score = score
            best = p
    return best


def simulate_battle(player_party: list[dict], trainer_party: list[dict]) -> dict:
    """
    Full battle simulation.
    Returns a dict with:
      lead_recommendation, all_turns (list of SimTurn dicts),
      matchup_summary (per opponent Pokémon), surviving_party
    """
    players = copy.deepcopy(player_party)
    opponents = copy.deepcopy(trainer_party)

    # Ensure all have current_hp
    for p in players:
        if "current_hp" not in p:
            p["current_hp"] = p.get("max_hp", p["level"] * 2 + 20)
        if "max_hp" not in p:
            p["max_hp"] = p["current_hp"]
    for o in opponents:
        if "current_hp" not in o:
            o["current_hp"] = o.get("max_hp", o["level"] * 2 + 20)
        if "max_hp" not in o:
            o["max_hp"] = o["current_hp"]

    lead = _pick_lead(players, opponents[0])
    # Sync lead back into players list
    for i, p in enumerate(players):
        if p["species_name"] == lead["species_name"]:
            players[i] = lead
            break

    all_turns: list[dict] = []
    matchup_summaries: list[dict] = []
    current_player = lead
    turn_counter = 0

    for opp in opponents:
        opp_turns: list[SimTurn] = []

        # Check if we need a better matchup switch before starting
        switch_target = _pick_best_switch(players, current_player, opp)
        if switch_target:
            # Compare: would switching give significantly better damage?
            cur_scored = best_move_against(current_player, opp)
            sw_scored  = best_move_against(switch_target, opp)
            cur_avg = cur_scored[0]["avg"] if cur_scored else 0
            sw_avg  = sw_scored[0]["avg"]  if sw_scored  else 0
            if sw_avg > cur_avg * 1.5:
                current_player = switch_target

        while opp["current_hp"] > 0:
            # If current player fainted, find next available
            if current_player["current_hp"] <= 0:
                nxt = _pick_best_switch(players, current_player, opp)
                if nxt is None:
                    break
                current_player = nxt

            turns, p_after, o_after = _simulate_matchup(
                current_player, opp, turn_counter
            )
            opp_turns.extend(turns)
            turn_counter += len(turns)

            # Update states
            for i, p in enumerate(players):
                if p["species_name"] == p_after["species_name"]:
                    players[i] = p_after
                    current_player = p_after
                    break
            opp["current_hp"] = o_after["current_hp"]

            # Safety: if player fainted during this matchup and opp still alive, switch
            if p_after["current_hp"] <= 0 and opp["current_hp"] > 0:
                nxt = _pick_best_switch(players, p_after, opp)
                if nxt is None:
                    break
                current_player = nxt

        risky_turns = sum(1 for t in opp_turns if t.is_risky)
        risk_level = "dangerous" if risky_turns >= 2 else ("caution" if risky_turns == 1 else "safe")

        matchup_summaries.append({
            "opponent_pokemon": opp["species_name"],
            "player_pokemon_used": (opp_turns[0].player_pokemon if opp_turns else current_player.get("nickname") or current_player["species_name"]),
            "turns_to_ko": len(opp_turns),
            "risk_level": risk_level,
        })

        all_turns.extend([{
            "turn": t.turn,
            "matchup": t.matchup,
            "player_pokemon": t.player_pokemon,
            "player_pokemon_species": t.player_pokemon_species,
            "player_hp_before": t.player_hp_before,
            "player_hp_max": t.player_hp_max,
            "opponent_pokemon": t.opponent_pokemon,
            "opponent_hp_before": t.opponent_hp_before,
            "opponent_hp_max": t.opponent_hp_max,
            "goes_first": t.goes_first,
            "player_action": t.player_action,
            "player_action_type": t.player_action_type,
            "player_damage_min": t.player_damage_min,
            "player_damage_max": t.player_damage_max,
            "player_damage_avg": t.player_damage_avg,
            "player_effectiveness": t.player_effectiveness,
            "opponent_action": t.opponent_action,
            "opponent_action_type": t.opponent_action_type,
            "opponent_damage_min": t.opponent_damage_min,
            "opponent_damage_max": t.opponent_damage_max,
            "opponent_damage_avg": t.opponent_damage_avg,
            "opponent_effectiveness": t.opponent_effectiveness,
            "player_hp_after": t.player_hp_after,
            "opponent_hp_after": t.opponent_hp_after,
            "player_fainted": t.player_fainted,
            "opponent_fainted": t.opponent_fainted,
            "is_risky": t.is_risky,
        } for t in opp_turns])

    lead_name = lead.get("nickname") or lead["species_name"]
    surviving = [p for p in players if p["current_hp"] > 0]

    return {
        "lead_recommendation": lead_name,
        "turns": all_turns,
        "matchup_summary": matchup_summaries,
        "surviving_party": [p["species_name"] for p in surviving],
        "total_turns": turn_counter,
    }
