"""Tests for the Gen 3 damage calculator."""

import pytest
from src.tools.damage_calc import calc_damage, is_physical, speed_order, type_weaknesses
from src.data.type_chart import get_effectiveness


def test_is_physical():
    assert is_physical("Normal") is True
    assert is_physical("Fire") is False
    assert is_physical("Fighting") is True
    assert is_physical("Psychic") is False
    assert is_physical("Steel") is True


def test_type_effectiveness_supereffective():
    # Water vs Fire = ×2
    assert get_effectiveness("Water", "Fire") == 2.0


def test_type_effectiveness_immune():
    # Normal vs Ghost = immune
    assert get_effectiveness("Normal", "Ghost") == 0.0
    # Ground vs Flying = immune
    assert get_effectiveness("Ground", "Flying") == 0.0
    # Psychic vs Dark = immune
    assert get_effectiveness("Psychic", "Dark") == 0.0


def test_type_effectiveness_double():
    # Electric vs Water/Flying = ×4
    assert get_effectiveness("Electric", "Water", "Flying") == 4.0


def test_type_effectiveness_neutral():
    assert get_effectiveness("Normal", "Normal") == 1.0


def test_calc_damage_returns_range():
    result = calc_damage(
        attacker_level=50,
        attacker_atk=80,
        attacker_spa=60,
        move_power=90,
        move_type="Water",
        attacker_type1="Water",
        attacker_type2=None,
        defender_def=70,
        defender_spd=65,
        defender_type1="Fire",
        defender_type2=None,
    )
    assert result["min"] > 0
    assert result["max"] >= result["min"]
    assert result["avg"] == round((result["min"] + result["max"]) / 2)
    assert result["effectiveness"] == 2.0
    assert result["stab"] is True


def test_calc_damage_zero_power():
    result = calc_damage(
        attacker_level=50, attacker_atk=80, attacker_spa=60,
        move_power=0, move_type="Water",
        attacker_type1="Water", attacker_type2=None,
        defender_def=70, defender_spd=65,
        defender_type1="Fire",
    )
    assert result["min"] == 0
    assert result["max"] == 0


def test_speed_order():
    fast = {"spe": 100}
    slow = {"spe": 60}
    assert speed_order(fast, slow) == "a"
    assert speed_order(slow, fast) == "b"
    assert speed_order(fast, fast) == "tie"


def test_type_weaknesses_contains_known():
    weaknesses = type_weaknesses("Fire", None)
    assert weaknesses["Water"] == 2.0
    assert weaknesses["Ground"] == 2.0
    assert weaknesses["Rock"] == 2.0
