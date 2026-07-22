from __future__ import annotations

import random

from tactics_game import config
from tactics_game.engine import progression, resolution
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Position
from tactics_game.models.hero import ClassTrack, Hero


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


def _rng() -> random.Random:
    return random.Random(0)


def test_damage_effect_scales_with_a_single_attribute() -> None:
    component = resolution.EffectComponent(
        kind="damage",
        base=5,
        scaling=[resolution.ScalingTerm(attribute="might", multiplier=1)],
        verb="strikes",
    )
    effect = resolution.make_effect([component])

    caster = _make_hero("Caster", 20, 20, Attributes(might=1, focus=1, resolve=1, agility=1))
    target = _make_hero("Target", 20, 20)
    result = effect(caster, target, _rng())
    assert result.damage == 6
    assert target.current_hp == 14
    assert result.description == "Caster strikes Target for 6"

    stronger_caster = _make_hero(
        "Stronger", 20, 20, Attributes(might=10, focus=1, resolve=1, agility=1)
    )
    fresh_target = _make_hero("Target2", 20, 20)
    stronger_result = effect(stronger_caster, fresh_target, _rng())
    assert stronger_result.damage > result.damage


def test_damage_effect_scales_with_multiple_attributes() -> None:
    component = resolution.EffectComponent(
        kind="damage",
        base=2,
        scaling=[
            resolution.ScalingTerm(attribute="might", multiplier=1),
            resolution.ScalingTerm(attribute="agility", multiplier=0.5),
        ],
        verb="recklessly strikes",
    )
    effect = resolution.make_effect([component])

    caster = _make_hero("Caster", 20, 20, Attributes(might=4, focus=1, resolve=1, agility=6))
    target = _make_hero("Target", 20, 20)
    result = effect(caster, target, _rng())
    # 2 + 4*1 + 6*0.5 = 9
    assert result.damage == 9
    assert target.current_hp == 11


def test_heal_effect_scales_with_an_attribute_and_does_not_overheal() -> None:
    component = resolution.EffectComponent(
        kind="heal",
        base=6,
        scaling=[resolution.ScalingTerm(attribute="resolve", multiplier=0.5)],
        verb="mends",
    )
    effect = resolution.make_effect([component])

    caster = _make_hero("Healer", 20, 20, Attributes(might=1, focus=1, resolve=1, agility=1))
    target = _make_hero("Target", 5, 20)
    result = effect(caster, target, _rng())
    # round(6 + 1*0.5) == 6 (banker's rounding: round(6.5) -> 6)
    assert result.healing == 6
    assert target.current_hp == 11

    near_full_target = _make_hero("Target2", 19, 20)
    effect(caster, near_full_target, _rng())
    assert near_full_target.current_hp == 20  # capped at max_hp, no overheal

    wiser_caster = _make_hero(
        "Wiser", 20, 20, Attributes(might=1, focus=1, resolve=10, agility=1)
    )
    fresh_target = _make_hero("Target3", 5, 20)
    wiser_result = effect(wiser_caster, fresh_target, _rng())
    assert wiser_result.healing > result.healing


def test_damage_does_not_reduce_hp_below_zero() -> None:
    component = resolution.EffectComponent(
        kind="damage",
        base=5,
        scaling=[resolution.ScalingTerm(attribute="might", multiplier=1)],
        verb="strikes",
    )
    effect = resolution.make_effect([component])
    caster = _make_hero("Caster", 20, 20)
    target = _make_hero("Target", 1, 20)
    effect(caster, target, _rng())
    assert target.current_hp == 0


def test_multi_component_effect_can_apply_to_both_caster_and_target() -> None:
    components = [
        resolution.EffectComponent(
            kind="damage",
            base=8,
            scaling=[resolution.ScalingTerm(attribute="might", multiplier=1)],
            verb="recklessly strikes",
        ),
        resolution.EffectComponent(
            kind="heal",
            base=2,
            scaling=[resolution.ScalingTerm(attribute="might", multiplier=0.25)],
            verb="is invigorated by the blow, healing",
            applies_to="caster",
        ),
    ]
    effect = resolution.make_effect(components)

    caster = _make_hero("Caster", 10, 20, Attributes(might=4, focus=1, resolve=1, agility=1))
    target = _make_hero("Target", 20, 20)
    result = effect(caster, target, _rng())

    assert target.current_hp == 20 - (8 + 4)  # damage component
    assert caster.current_hp == 10 + (2 + 1)  # heal component, applied to caster
    assert result.damage == 12
    assert result.healing == 3
    assert "recklessly strikes" in result.description
    assert "invigorated" in result.description


def test_grant_class_xp_increments_only_the_target_track() -> None:
    hero = _make_hero("Hero", 20, 20)
    progression.grant_class_xp(hero, ClassTrack.FIGHTER)
    assert hero.class_xp[ClassTrack.FIGHTER] == config.CLASS_XP_PER_ABILITY_USE
    for track in ClassTrack:
        if track != ClassTrack.FIGHTER:
            assert hero.class_xp[track] == 0


def test_grant_class_xp_for_ability_resolves_the_correct_track() -> None:
    hero = _make_hero("Hero", 20, 20)
    basic_shot = next(a for a in hero.abilities if a.name == "Basic Shot")
    progression.grant_class_xp_for_ability(hero, basic_shot)
    assert hero.class_xp[ClassTrack.MARKSMAN] == config.CLASS_XP_PER_ABILITY_USE
    for track in ClassTrack:
        if track != ClassTrack.MARKSMAN:
            assert hero.class_xp[track] == 0
