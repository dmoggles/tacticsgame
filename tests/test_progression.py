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


def _make_leveled_hero(name: str, level: int) -> Hero:
    hero = _make_hero_with_affinity(AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25))
    hero.name = name
    hero.level = level
    return hero


def test_compute_enemy_strength_sums_enemy_levels() -> None:
    enemies = [_make_leveled_hero("A", 1), _make_leveled_hero("B", 3)]
    assert progression.compute_enemy_strength(enemies) == 4


def test_compute_battle_xp_pool_scales_with_enemy_strength() -> None:
    weak_squad = [_make_leveled_hero("A", 1)]
    strong_squad = [_make_leveled_hero("A", 1), _make_leveled_hero("B", 4)]

    assert progression.compute_battle_xp_pool(strong_squad) > progression.compute_battle_xp_pool(
        weak_squad
    )
    assert progression.compute_battle_xp_pool(weak_squad) == (
        config.XP_POOL_PER_STRENGTH_POINT * progression.compute_enemy_strength(weak_squad)
    )


def test_award_battle_xp_splits_pool_evenly_across_fielded_heroes() -> None:
    fielded = [_make_leveled_hero("A", 1), _make_leveled_hero("B", 1)]
    enemy_squad = [_make_leveled_hero("Enemy", 1)]
    rng = random.Random(3)

    progression.award_battle_xp(fielded, enemy_squad, rng)

    expected_pool = progression.compute_battle_xp_pool(enemy_squad)
    assert fielded[0].xp == fielded[1].xp == expected_pool // len(fielded)


def test_award_battle_xp_gives_downed_heroes_a_full_share() -> None:
    downed = _make_leveled_hero("Downed", 1)
    downed.current_hp = 0
    healthy = _make_leveled_hero("Healthy", 1)
    enemy_squad = [_make_leveled_hero("Enemy", 1)]
    rng = random.Random(4)

    progression.award_battle_xp([downed, healthy], enemy_squad, rng)

    # Presence, not survival, earns the share — a downed hero was still
    # fielded, so it gets exactly what a standing ally gets.
    assert downed.xp == healthy.xp
    assert downed.xp > 0


def test_award_battle_xp_triggers_multi_level_jumps_from_a_large_pool() -> None:
    hero = _make_leveled_hero("Grower", 1)
    # A squad of high-level enemies drives compute_battle_xp_pool well past
    # several level thresholds in one call, exercising grant_xp's existing
    # multi-level-jump loop (see test_grant_xp_applies_every_level_crossed_in_one_call).
    enemy_squad = [_make_leveled_hero(f"Enemy {i}", 10) for i in range(4)]
    rng = random.Random(7)

    progression.award_battle_xp([hero], enemy_squad, rng)

    assert hero.level > 3


def test_award_bench_bonus_xp_is_zero_at_default_multiplier() -> None:
    benched = [_make_leveled_hero("Bench", 1)]
    enemy_squad = [_make_leveled_hero("Enemy", 2)]
    rng = random.Random(5)

    progression.award_bench_bonus_xp(benched, enemy_squad, rng)

    assert benched[0].xp == 0


def test_award_bench_bonus_xp_scales_with_explicit_multiplier() -> None:
    benched = [_make_leveled_hero("Bench1", 1), _make_leveled_hero("Bench2", 1)]
    enemy_squad = [_make_leveled_hero("Enemy", 2)]
    rng = random.Random(6)

    progression.award_bench_bonus_xp(benched, enemy_squad, rng, bench_multiplier=0.5)

    pool = progression.compute_battle_xp_pool(enemy_squad)
    expected_bench_share = round(0.5 * pool) // len(benched)
    assert benched[0].xp == benched[1].xp == expected_bench_share
    assert expected_bench_share > 0


def test_award_bench_bonus_xp_is_a_noop_with_no_benched_heroes() -> None:
    enemy_squad = [_make_leveled_hero("Enemy", 2)]
    rng = random.Random(8)

    # Must not raise (e.g. a division by zero on an empty benched list).
    progression.award_bench_bonus_xp([], enemy_squad, rng, bench_multiplier=0.5)
