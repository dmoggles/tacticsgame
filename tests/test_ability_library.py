from __future__ import annotations

import pytest

from tactics_game.engine import ability_library


def test_load_abilities_returns_the_four_basic_kit_abilities() -> None:
    abilities = ability_library.load_abilities()
    by_name = {ability.name: ability for ability in abilities}

    assert set(by_name) == {"Basic Strike", "Basic Shot", "Basic Bolt", "Basic Mend"}

    strike = by_name["Basic Strike"]
    assert strike.range == 1
    assert strike.min_range == 0
    assert strike.cooldown == 0
    assert strike.targets_ally is False

    shot = by_name["Basic Shot"]
    assert shot.range == 4
    assert shot.min_range == 2

    mend = by_name["Basic Mend"]
    assert mend.targets_ally is True
    assert mend.cooldown == 3


def test_load_abilities_returns_shared_instances_across_calls() -> None:
    # Ability is frozen/stateless — safe (and intended) to share rather than
    # rebuild per hero.
    first = {a.name: a for a in ability_library.load_abilities()}
    second = {a.name: a for a in ability_library.load_abilities()}
    assert first["Basic Strike"] is second["Basic Strike"]


def test_load_ability_ids_maps_ids_to_display_names() -> None:
    ids = ability_library.load_ability_ids()
    assert ids["basic_strike"] == "Basic Strike"
    assert ids["basic_mend"] == "Basic Mend"


def _valid_ability_entry() -> dict:
    return {
        "id": "test_ability",
        "name": "Test Ability",
        "targets_ally": False,
        "range": 1,
        "effect": {
            "kind": "damage",
            "base": 1,
            "scaling": [{"attribute": "might", "multiplier": 1}],
            "verb": "pokes",
        },
    }


def test_build_ability_raises_on_missing_required_field() -> None:
    entry = _valid_ability_entry()
    del entry["range"]
    with pytest.raises(ValueError, match="range"):
        ability_library._build_ability("test_ability", entry)


def test_build_ability_raises_on_missing_effect() -> None:
    entry = _valid_ability_entry()
    del entry["effect"]
    with pytest.raises(ValueError, match="effect"):
        ability_library._build_ability("test_ability", entry)


def test_build_ability_normalizes_a_bare_effect_mapping_to_one_component() -> None:
    ability = ability_library._build_ability("test_ability", _valid_ability_entry())
    assert ability.name == "Test Ability"


def test_build_component_raises_on_unknown_kind() -> None:
    with pytest.raises(ValueError, match="kind"):
        ability_library._build_component(
            "test_ability", {"kind": "bogus", "base": 1, "verb": "pokes"}
        )


def test_build_component_raises_on_unknown_applies_to() -> None:
    with pytest.raises(ValueError, match="applies_to"):
        ability_library._build_component(
            "test_ability",
            {"kind": "damage", "base": 1, "verb": "pokes", "applies_to": "everyone"},
        )


def test_build_scaling_term_raises_on_unknown_attribute() -> None:
    with pytest.raises(ValueError, match="attribute"):
        ability_library._build_scaling_term("test_ability", {"attribute": "luck", "multiplier": 1})
