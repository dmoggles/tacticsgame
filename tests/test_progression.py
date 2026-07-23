from __future__ import annotations

import random
import statistics

import pytest

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


def test_level_up_applies_automatic_points_immediately_and_queues_the_manual_one() -> None:
    hero = _make_hero_with_affinity(AffinityVector(might=1.0, focus=0.0, resolve=0.0, agility=0.0))
    rng = random.Random(0)
    auto_points = config.POINTS_PER_LEVEL_UP - config.MANUAL_ALLOCATION_POINTS_PER_LEVEL_UP

    old_max_hp = hero.max_hp
    progression.grant_xp(hero, config.XP_LEVEL_THRESHOLD, rng)

    assert hero.level == 2
    assert hero.xp == 0
    assert hero.pending_level_ups == 1
    # Only the automatic points are applied yet — the manual one is still
    # pending, not forfeited.
    assert hero.attributes.might == 1 + auto_points
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
    assert hero.pending_level_ups == 2


def test_resolve_manual_allocation_applies_the_chosen_attribute() -> None:
    # Affinity weighted fully toward focus, so the automatic points went
    # there — the manual choice picks a different attribute regardless.
    hero = _make_hero_with_affinity(AffinityVector(might=0.0, focus=1.0, resolve=0.0, agility=0.0))
    rng = random.Random(2)
    progression.grant_xp(hero, config.XP_LEVEL_THRESHOLD, rng)
    might_before_manual = hero.attributes.might
    max_hp_before_manual = hero.max_hp

    progression.resolve_manual_allocation(hero, AttributeName.MIGHT, rng)

    assert hero.pending_level_ups == 0
    assert hero.attributes.might == might_before_manual + config.MANUAL_ALLOCATION_POINTS_PER_LEVEL_UP
    assert hero.max_hp == max_hp_before_manual + 2 * config.MANUAL_ALLOCATION_POINTS_PER_LEVEL_UP
    assert hero.current_hp == hero.max_hp


def test_resolve_manual_allocation_falls_back_to_affinity_when_skipped() -> None:
    hero = _make_hero_with_affinity(AffinityVector(might=1.0, focus=0.0, resolve=0.0, agility=0.0))
    rng = random.Random(3)
    progression.grant_xp(hero, config.XP_LEVEL_THRESHOLD, rng)

    progression.resolve_manual_allocation(hero, None, rng)

    # Declining doesn't forfeit the point — with affinity fully weighted to
    # might, both the automatic and the skipped-manual point land there,
    # totalling the full per-level-up amount.
    assert hero.pending_level_ups == 0
    assert hero.attributes.might == 1 + config.POINTS_PER_LEVEL_UP


def test_resolve_manual_allocation_raises_with_nothing_pending() -> None:
    hero = _make_hero_with_affinity(AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25))
    rng = random.Random(4)

    with pytest.raises(ValueError):
        progression.resolve_manual_allocation(hero, AttributeName.MIGHT, rng)


def test_multi_level_jump_resolves_one_pending_level_up_at_a_time() -> None:
    hero = _make_hero_with_affinity(AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25))
    rng = random.Random(5)
    progression.grant_xp(hero, config.XP_LEVEL_THRESHOLD * 2, rng)
    assert hero.pending_level_ups == 2

    progression.resolve_manual_allocation(hero, AttributeName.MIGHT, rng)
    assert hero.pending_level_ups == 1

    progression.resolve_manual_allocation(hero, AttributeName.MIGHT, rng)
    assert hero.pending_level_ups == 0


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


def test_award_bench_bonus_xp_is_zero_at_explicit_zero_multiplier() -> None:
    benched = [_make_leveled_hero("Bench", 1)]
    enemy_squad = [_make_leveled_hero("Enemy", 2)]
    rng = random.Random(5)

    progression.award_bench_bonus_xp(benched, enemy_squad, rng, bench_multiplier=0.0)

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


def test_recover_hp_heals_a_fraction_of_max_hp() -> None:
    hero = _make_leveled_hero("Recovering", 1)
    hero.current_hp = 1

    progression.recover_hp(hero, 0.5)

    assert hero.current_hp == 1 + round(0.5 * hero.max_hp)


def test_recover_hp_never_exceeds_max_hp() -> None:
    hero = _make_leveled_hero("AlmostFull", 1)
    hero.current_hp = hero.max_hp - 1

    progression.recover_hp(hero, 1.0)

    assert hero.current_hp == hero.max_hp


def test_recover_hp_heals_a_hero_from_the_downed_revive_floor() -> None:
    # No separate injury system: a hero just revived at DOWNED_REVIVE_HP
    # climbs back via the exact same function as any other damage.
    hero = _make_leveled_hero("Downed", 1)
    hero.current_hp = 0

    progression.revive_downed_hero(hero)
    assert hero.current_hp == config.DOWNED_REVIVE_HP

    progression.recover_hp(hero, config.BENCHED_RECOVERY_FRACTION)

    assert hero.current_hp > config.DOWNED_REVIVE_HP
