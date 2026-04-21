"""
Turn-by-turn Gen 3 battle simulator — Nuzlocke-safe mode.

Lead and switch selection prioritises survival (fewest faints) over raw damage.
Scoring: projected HP remaining after KO-ing opponent, penalised heavily if
worst-case damage would KO the player first.  Only fall back to raw damage as
a tiebreaker.

Proactive switching: after every individual turn, if player HP drops below
HP_SWITCH_THRESHOLD *and* a safer teammate would take less cumulative damage
finishing this opponent, we switch immediately.
"""

import copy
import math
from dataclasses import dataclass
from src.tools.damage_calc import calc_damage, best_move_against, speed_order

# Fraction of max HP below which we evaluate a proactive switch
HP_SWITCH_THRESHOLD = 0.35

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

    goes_first: str

    player_action: str
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
    is_risky: bool


# ── Move helpers ───────────────────────────────────────────────────────────

def _make_generic_move(opponent: dict) -> dict:
    type1 = opponent.get("type1", "Normal")
    name, power = _TYPE_MOVE.get(type1, ("Tackle", 40))
    return {"id": 0, "name": name, "type": type1, "power": power,
            "accuracy": 90, "damage_class": "physical", "pp": 30}


def _opponent_move(opponent: dict, player: dict) -> dict:
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


# ── Survival scoring ───────────────────────────────────────────────────────

def _turns_to_finish(attacker_avg: float, target_hp: int) -> int:
    if attacker_avg <= 0:
        return 999
    return math.ceil(target_hp / attacker_avg)


def _survival_score(player: dict, opponent: dict) -> tuple[float, float]:
    """
    Nuzlocke survival score for player vs opponent.

    Returns (projected_hp_ratio_after_ko, avg_damage_output).
    - Positive ratio  → player survives the matchup with that fraction of max HP left.
    - Negative ratio  → player would faint in worst case before finishing the opponent.
    Higher is always better; tiebreak by damage output.
    """
    scored = best_move_against(player, opponent)
    p_avg = scored[0]["avg"] if scored else 0

    o_move = _opponent_move(opponent, player)
    o_max  = o_move["max"]

    opp_hp = opponent.get("current_hp", opponent.get("max_hp", 100))
    p_hp   = player["current_hp"]
    p_max  = player["max_hp"]

    turns = _turns_to_finish(p_avg, opp_hp)
    hp_after = p_hp - turns * o_max      # worst-case
    return (hp_after / p_max, p_avg)


# ── Lead / switch selection ────────────────────────────────────────────────

def _pick_lead(player_party: list[dict], first_opponent: dict) -> dict:
    alive = [p for p in player_party if not p.get("is_fainted") and p["current_hp"] > 0]
    if not alive:
        return player_party[0]
    return max(alive, key=lambda p: _survival_score(p, first_opponent))


def _best_survivor(
    player_party: list[dict],
    exclude_species: str,
    opponent: dict,
) -> dict | None:
    """Return the alive Pokémon (excluding current) with the highest survival score."""
    candidates = [
        p for p in player_party
        if p["species_name"] != exclude_species
        and not p.get("is_fainted")
        and p["current_hp"] > 0
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: _survival_score(p, opponent))


def _should_switch(current: dict, candidate: dict, opponent: dict, emergency: bool = False) -> bool:
    """
    True if switching to candidate is the safer Nuzlocke play.

    emergency=False (pre-battle): only switch if meaningfully better (> 10 % HP margin).
    emergency=True  (HP critical): switch to the least-bad option — any improvement counts,
                                   because burning a low-HP Pokémon further is always worse.
    """
    cur_ratio,  _ = _survival_score(current,   opponent)
    best_ratio, _ = _survival_score(candidate, opponent)
    # Always switch if candidate survives cleanly and current would not
    if cur_ratio < 0 and best_ratio >= 0:
        return True
    if emergency:
        return best_ratio > cur_ratio          # any improvement
    return best_ratio > cur_ratio + 0.10       # pre-battle: require clear margin


# ── Single-turn simulation ─────────────────────────────────────────────────

def _sim_one_turn(
    player: dict,
    opponent: dict,
    global_turn: int,
    matchup_label: str,
) -> tuple[SimTurn, int, int]:
    """
    Simulate exactly one turn.  Returns (SimTurn, player_hp_after, opp_hp_after).
    Caller is responsible for writing hp values back into their dicts.
    """
    p_move = _player_best_move(player, opponent)
    o_move = _opponent_move(opponent, player)

    if p_move is None:
        # No usable move — treat as struggle (tiny fixed damage)
        p_move = {"name": "Struggle", "type": "Normal", "power": 50,
                  "min": 5, "max": 10, "avg": 7, "effectiveness": 1.0,
                  "damage_class": "physical"}

    first = speed_order(player, opponent)
    goes_first = "player" if first == "a" else ("tie" if first == "tie" else "opponent")

    p_hp_before = player["current_hp"]
    o_hp_before = opponent["current_hp"]
    p_hp_after  = p_hp_before
    o_hp_after  = o_hp_before

    def apply_p():
        nonlocal o_hp_after
        o_hp_after = max(0, o_hp_after - p_move["avg"])

    def apply_o():
        nonlocal p_hp_after
        p_hp_after = max(0, p_hp_after - o_move["avg"])

    if goes_first in ("player", "tie"):
        apply_p()
        if o_hp_after > 0:
            apply_o()
    else:
        apply_o()
        if p_hp_after > 0:
            apply_p()

    is_risky = o_move["max"] >= player["max_hp"] * 0.4

    t = SimTurn(
        turn=global_turn,
        matchup=matchup_label,
        player_pokemon=player.get("nickname") or player["species_name"],
        player_pokemon_species=player["species_name"],
        player_hp_before=p_hp_before,
        player_hp_max=player["max_hp"],
        opponent_pokemon=opponent.get("nickname") or opponent["species_name"],
        opponent_hp_before=o_hp_before,
        opponent_hp_max=opponent["max_hp"],
        goes_first=goes_first,
        player_action=p_move["name"],
        player_action_type=p_move["type"],
        player_damage_min=p_move["min"],
        player_damage_max=p_move["max"],
        player_damage_avg=p_move["avg"],
        player_effectiveness=p_move["effectiveness"],
        opponent_action=o_move["name"],
        opponent_action_type=o_move["type"],
        opponent_damage_min=o_move["min"],
        opponent_damage_max=o_move["max"],
        opponent_damage_avg=o_move["avg"],
        opponent_effectiveness=o_move.get("effectiveness", 1.0),
        player_hp_after=p_hp_after,
        opponent_hp_after=o_hp_after,
        player_fainted=(p_hp_after == 0),
        opponent_fainted=(o_hp_after == 0),
        is_risky=is_risky,
    )
    return t, p_hp_after, o_hp_after


# ── Full battle ────────────────────────────────────────────────────────────

def simulate_battle(player_party: list[dict], trainer_party: list[dict]) -> dict:
    """
    Full Nuzlocke-safe battle simulation.

    Runs one turn at a time so proactive switching can fire after every turn.
    Lead and switch decisions minimise faints rather than maximise damage.
    """
    players   = copy.deepcopy(player_party)
    opponents = copy.deepcopy(trainer_party)

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
    for i, p in enumerate(players):
        if p["species_name"] == lead["species_name"]:
            players[i] = lead
            break

    all_turns:         list[dict] = []
    matchup_summaries: list[dict] = []
    current_player = lead
    global_turn    = 0

    for opp in opponents:
        opp_turn_count = 0
        opp_risky      = 0

        # Pre-battle: switch to a safer lead if one exists
        candidate = _best_survivor(players, current_player["species_name"], opp)
        if candidate and _should_switch(current_player, candidate, opp):
            current_player = candidate

        matchup_label = f"{current_player.get('nickname') or current_player['species_name']} vs {opp['species_name']}"

        for _ in range(_MAX_TURNS_PER_MATCHUP * len(players)):
            # Force-switch if fainted
            if current_player["current_hp"] <= 0:
                nxt = _best_survivor(players, current_player["species_name"], opp)
                if nxt is None:
                    break
                current_player = nxt
                matchup_label = f"{current_player.get('nickname') or current_player['species_name']} vs {opp['species_name']}"

            if opp["current_hp"] <= 0:
                break

            # Proactive switch: HP critically low — use least-bad available option
            hp_ratio = current_player["current_hp"] / current_player["max_hp"]
            if hp_ratio < HP_SWITCH_THRESHOLD:
                candidate = _best_survivor(players, current_player["species_name"], opp)
                if candidate and _should_switch(current_player, candidate, opp, emergency=True):
                    current_player = candidate
                    matchup_label = f"{current_player.get('nickname') or current_player['species_name']} vs {opp['species_name']}"

            global_turn += 1
            opp_turn_count += 1

            turn, p_hp, o_hp = _sim_one_turn(
                current_player, opp, global_turn, matchup_label
            )

            # Write HP back
            current_player["current_hp"] = p_hp
            opp["current_hp"] = o_hp
            for i, p in enumerate(players):
                if p["species_name"] == current_player["species_name"]:
                    players[i] = current_player
                    break

            if turn.is_risky:
                opp_risky += 1

            all_turns.append({
                "turn": turn.turn,
                "matchup": turn.matchup,
                "player_pokemon": turn.player_pokemon,
                "player_pokemon_species": turn.player_pokemon_species,
                "player_hp_before": turn.player_hp_before,
                "player_hp_max": turn.player_hp_max,
                "opponent_pokemon": turn.opponent_pokemon,
                "opponent_hp_before": turn.opponent_hp_before,
                "opponent_hp_max": turn.opponent_hp_max,
                "goes_first": turn.goes_first,
                "player_action": turn.player_action,
                "player_action_type": turn.player_action_type,
                "player_damage_min": turn.player_damage_min,
                "player_damage_max": turn.player_damage_max,
                "player_damage_avg": turn.player_damage_avg,
                "player_effectiveness": turn.player_effectiveness,
                "opponent_action": turn.opponent_action,
                "opponent_action_type": turn.opponent_action_type,
                "opponent_damage_min": turn.opponent_damage_min,
                "opponent_damage_max": turn.opponent_damage_max,
                "opponent_damage_avg": turn.opponent_damage_avg,
                "opponent_effectiveness": turn.opponent_effectiveness,
                "player_hp_after": turn.player_hp_after,
                "opponent_hp_after": turn.opponent_hp_after,
                "player_fainted": turn.player_fainted,
                "opponent_fainted": turn.opponent_fainted,
                "is_risky": turn.is_risky,
            })

            if o_hp <= 0:
                break

        risk_level = "dangerous" if opp_risky >= 2 else ("caution" if opp_risky == 1 else "safe")
        matchup_summaries.append({
            "opponent_pokemon": opp["species_name"],
            "player_pokemon_used": (
                all_turns[-opp_turn_count]["player_pokemon"]
                if opp_turn_count > 0 and opp_turn_count <= len(all_turns)
                else current_player.get("nickname") or current_player["species_name"]
            ),
            "turns_to_ko": opp_turn_count,
            "risk_level": risk_level,
        })

    lead_name = lead.get("nickname") or lead["species_name"]
    surviving = [p for p in players if p["current_hp"] > 0]

    return {
        "lead_recommendation": lead_name,
        "turns": all_turns,
        "matchup_summary": matchup_summaries,
        "surviving_party": [p.get("nickname") or p["species_name"] for p in surviving],
        "total_turns": global_turn,
    }
