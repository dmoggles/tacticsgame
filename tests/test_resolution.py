from __future__ import annotations

from tactics_game import config
from tactics_game.engine import progression, resolution
from tactics_game.models.ability import ClassTrack
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Position
from tactics_game.models.hero import Hero


def _make_hero(
    name: str,
    current_hp: int,
    max_hp: int,
    attributes: Attributes = Attributes(might=1, focus=1, resolve=1, agility=1),
) -> Hero:
    return Hero(
        name=name,
        attributes=attributes,
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=max_hp,
        current_hp=current_hp,
        position=Position(0, 0),
        is_player_controlled=True,
    )


def test_basic_strike_scales_with_might() -> None:
    caster = _make_hero("Caster", 20, 20, Attributes(might=1, focus=1, resolve=1, agility=1))
    target = _make_hero("Target", 20, 20)
    result = resolution.resolve_basic_strike(caster, target)
    expected = config.BASIC_STRIKE_DAMAGE + 1 * config.BASIC_STRIKE_MIGHT_SCALING
    assert result.damage == expected
    assert target.current_hp == 20 - expected

    stronger_caster = _make_hero(
        "Stronger", 20, 20, Attributes(might=10, focus=1, resolve=1, agility=1)
    )
    stronger_result = resolution.resolve_basic_strike(stronger_caster, target)
    assert stronger_result.damage > result.damage


def test_basic_shot_scales_with_agility() -> None:
    caster = _make_hero("Caster", 20, 20, Attributes(might=1, focus=1, resolve=1, agility=1))
    target = _make_hero("Target", 20, 20)
    result = resolution.resolve_basic_shot(caster, target)
    expected = config.BASIC_SHOT_DAMAGE + 1 * config.BASIC_SHOT_AGILITY_SCALING
    assert result.damage == expected
    assert target.current_hp == 20 - expected

    faster_caster = _make_hero(
        "Faster", 20, 20, Attributes(might=1, focus=1, resolve=1, agility=10)
    )
    faster_result = resolution.resolve_basic_shot(faster_caster, target)
    assert faster_result.damage > result.damage


def test_basic_bolt_scales_with_focus() -> None:
    caster = _make_hero("Caster", 20, 20, Attributes(might=1, focus=1, resolve=1, agility=1))
    target = _make_hero("Target", 20, 20)
    result = resolution.resolve_basic_bolt(caster, target)
    expected = config.BASIC_BOLT_DAMAGE + 1 * config.BASIC_BOLT_FOCUS_SCALING
    assert result.damage == expected
    assert target.current_hp == 20 - expected

    sharper_caster = _make_hero(
        "Sharper", 20, 20, Attributes(might=1, focus=10, resolve=1, agility=1)
    )
    sharper_result = resolution.resolve_basic_bolt(sharper_caster, target)
    assert sharper_result.damage > result.damage


def test_damage_does_not_reduce_hp_below_zero() -> None:
    caster = _make_hero("Caster", 20, 20)
    target = _make_hero("Target", 1, 20)
    resolution.resolve_basic_strike(caster, target)
    assert target.current_hp == 0


def test_basic_mend_scales_with_resolve() -> None:
    caster = _make_hero("Healer", 20, 20, Attributes(might=1, focus=1, resolve=1, agility=1))
    target = _make_hero("Target", 5, 20)
    result = resolution.resolve_basic_mend(caster, target)
    expected = round(config.BASIC_MEND_HEAL + 1 * config.BASIC_MEND_RESOLVE_SCALING)
    assert result.healing == expected
    assert target.current_hp == 5 + expected

    wiser_caster = _make_hero(
        "Wiser", 20, 20, Attributes(might=1, focus=1, resolve=10, agility=1)
    )
    fresh_target = _make_hero("Target2", 5, 20)
    wiser_result = resolution.resolve_basic_mend(wiser_caster, fresh_target)
    assert wiser_result.healing > result.healing


def test_basic_mend_does_not_overheal_past_max_hp() -> None:
    caster = _make_hero("Healer", 20, 20)
    target = _make_hero("Target", 19, 20)
    resolution.resolve_basic_mend(caster, target)
    assert target.current_hp == 20


def test_grant_class_xp_increments_only_the_target_track() -> None:
    hero = _make_hero("Hero", 20, 20)
    progression.grant_class_xp(hero, ClassTrack.FIGHTER)
    assert hero.class_xp[ClassTrack.FIGHTER] == config.CLASS_XP_PER_ABILITY_USE
    for track in ClassTrack:
        if track != ClassTrack.FIGHTER:
            assert hero.class_xp[track] == 0
