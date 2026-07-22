from __future__ import annotations

import random
import statistics

from tactics_game import config
from tactics_game.engine import progression
from tactics_game.models.attributes import AffinityVector, AttributeName, Attributes
from tactics_game.models.grid import Position
from tactics_game.models.hero import Hero


def test_hidden_affinity_correlates_with_synthesized_attributes() -> None:
    rng = random.Random(1234)
    sample_size = 500
    affinity_weights: dict[AttributeName, list[float]] = {name: [] for name in AttributeName}
    attribute_values: dict[AttributeName, list[int]] = {name: [] for name in AttributeName}

    for i in range(sample_size):
        hero = progression.create_starting_hero(
            name=f"Sample {i}",
            position=Position(0, 0),
            is_player_controlled=True,
            rng=rng,
        )
        for name, weight in hero.hidden_affinity.as_weights():
            affinity_weights[name].append(weight)
        attribute_values[AttributeName.MIGHT].append(hero.attributes.might)
        attribute_values[AttributeName.FOCUS].append(hero.attributes.focus)
        attribute_values[AttributeName.RESOLVE].append(hero.attributes.resolve)
        attribute_values[AttributeName.AGILITY].append(hero.attributes.agility)

    for name in AttributeName:
        correlation = statistics.correlation(affinity_weights[name], attribute_values[name])
        assert correlation > 0.5, f"{name} affinity->attribute correlation too weak: {correlation}"


def test_starting_attributes_include_base_plus_fifteen_allocated_points() -> None:
    rng = random.Random(99)
    hero = progression.create_starting_hero(
        name="Sample", position=Position(0, 0), is_player_controlled=True, rng=rng
    )
    total = hero.attributes.might + hero.attributes.focus + hero.attributes.resolve + hero.attributes.agility
    expected = 4 * config.BASE_ATTRIBUTE_VALUE + config.SYNTHESIS_LEVEL_UPS * config.POINTS_PER_LEVEL_UP
    assert total == expected


def _make_hero_with_affinity(affinity: AffinityVector) -> Hero:
    attributes = Attributes(might=1, focus=1, resolve=1, agility=1)
    return Hero(
        name="Leveler",
        attributes=attributes,
        hidden_affinity=affinity,
        abilities=progression.create_basic_kit(),
        max_hp=progression.compute_max_hp(attributes),
        current_hp=progression.compute_max_hp(attributes),
        position=Position(0, 0),
        is_player_controlled=True,
    )


def test_level_up_grants_points_weighted_fully_toward_a_single_attribute() -> None:
    hero = _make_hero_with_affinity(AffinityVector(might=1.0, focus=0.0, resolve=0.0, agility=0.0))
    rng = random.Random(0)

    old_max_hp = hero.max_hp
    progression.grant_xp(hero, config.XP_LEVEL_THRESHOLD, rng)

    assert hero.level == 2
    assert hero.xp == 0
    assert hero.attributes.might == 1 + config.POINTS_PER_LEVEL_UP
    assert hero.attributes.focus == 1
    assert hero.attributes.resolve == 1
    assert hero.attributes.agility == 1
    assert hero.max_hp == progression.compute_max_hp(hero.attributes)
    assert hero.current_hp - old_max_hp == hero.max_hp - old_max_hp


def test_grant_xp_applies_every_level_crossed_in_one_call() -> None:
    hero = _make_hero_with_affinity(AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25))
    rng = random.Random(1)

    progression.grant_xp(hero, config.XP_LEVEL_THRESHOLD * 2 + 5, rng)

    assert hero.level == 3
    assert hero.xp == 5


def test_xp_below_threshold_does_not_level_up() -> None:
    hero = _make_hero_with_affinity(AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25))
    rng = random.Random(2)

    progression.grant_xp(hero, config.XP_LEVEL_THRESHOLD - 1, rng)

    assert hero.level == 1
    assert hero.xp == config.XP_LEVEL_THRESHOLD - 1
