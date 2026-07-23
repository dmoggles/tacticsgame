from __future__ import annotations

import random

from .. import config
from ..models.ability import Ability
from ..models.attributes import AffinityVector, AttributeName, Attributes
from ..models.grid import Position
from ..models.hero import ClassTrack, Hero
from . import ability_library, class_track_library


def generate_hidden_affinity(rng: random.Random) -> AffinityVector:
    """Symmetric-Dirichlet-distributed weights over the four attributes.

    Built from independent Gamma(alpha, 1) draws normalized to sum to 1,
    the standard construction for a Dirichlet sample without requiring a
    numpy dependency.
    """
    samples = [rng.gammavariate(config.DIRICHLET_ALPHA, 1.0) for _ in AttributeName]
    total = sum(samples)
    weights = [sample / total for sample in samples]
    return AffinityVector(
        might=weights[0], focus=weights[1], resolve=weights[2], agility=weights[3]
    )


def allocate_points(
    affinity: AffinityVector, num_points: int, rng: random.Random
) -> dict[AttributeName, int]:
    """Distribute `num_points` across attributes via weighted-random draws.

    Each point is an independent weighted sample against the hero's hidden
    affinity, not a proportional split — this preserves run-to-run variance
    between heroes with similar affinity vectors.
    """
    names_and_weights = affinity.as_weights()
    names = [name for name, _ in names_and_weights]
    weights = [weight for _, weight in names_and_weights]
    counts: dict[AttributeName, int] = {name: 0 for name in names}
    for name in rng.choices(names, weights=weights, k=num_points):
        counts[name] += 1
    return counts


def synthesize_starting_attributes(
    affinity: AffinityVector, rng: random.Random
) -> Attributes:
    """5 simulated level-ups of 3 affinity-weighted points, atop base values."""
    totals: dict[AttributeName, int] = {
        name: config.BASE_ATTRIBUTE_VALUE for name in AttributeName
    }
    for _ in range(config.SYNTHESIS_LEVEL_UPS):
        allocation = allocate_points(affinity, config.POINTS_PER_LEVEL_UP, rng)
        for name, count in allocation.items():
            totals[name] += count
    return Attributes(
        might=totals[AttributeName.MIGHT],
        focus=totals[AttributeName.FOCUS],
        resolve=totals[AttributeName.RESOLVE],
        agility=totals[AttributeName.AGILITY],
    )


def compute_max_hp(attributes: Attributes) -> int:
    """Derived HP, isolated here so the formula is trivial to revise later."""
    return config.BASE_HP + (attributes.might + attributes.resolve) * config.HP_ATTRIBUTE_MULTIPLIER


def create_basic_kit() -> list[Ability]:
    """The classless Tier 0 kit every hero starts with, filling all 4 slots.

    Ability data lives in data/abilities.yaml — see engine/ability_library.py.
    """
    return ability_library.load_abilities()


def create_starting_hero(
    name: str, position: Position, is_player_controlled: bool, rng: random.Random
) -> Hero:
    """Level-0 hero synthesis: hidden affinity + 5 simulated level-ups.

    No player influence — pure roster generation.
    """
    affinity = generate_hidden_affinity(rng)
    attributes = synthesize_starting_attributes(affinity, rng)
    max_hp = compute_max_hp(attributes)
    return Hero(
        name=name,
        attributes=attributes,
        hidden_affinity=affinity,
        abilities=create_basic_kit(),
        max_hp=max_hp,
        current_hp=max_hp,
        position=position,
        is_player_controlled=is_player_controlled,
    )


def generate_enemy_squad(rng: random.Random) -> list[Hero]:
    """A fresh enemy squad for one battle in a session.

    Flat/unscaled this phase — no difficulty curve yet (see
    docs/03_phase2a_definition.md section 6) — isolated in its own
    function since a difficulty curve is the thing most likely to change
    this later.
    """
    return [
        create_starting_hero(
            name=f"Enemy {i + 1}",
            position=Position(config.GRID_WIDTH - 2, 2 + i * 3),
            is_player_controlled=False,
            rng=rng,
        )
        for i in range(config.SQUAD_SIZE)
    ]


def grant_xp(hero: Hero, amount: int, rng: random.Random) -> None:
    """Grant Track 1 XP, applying every level-up crossed (loop for big jumps)."""
    hero.xp += amount
    while hero.xp >= config.XP_LEVEL_THRESHOLD:
        hero.xp -= config.XP_LEVEL_THRESHOLD
        _level_up(hero, rng)


def _level_up(hero: Hero, rng: random.Random) -> None:
    allocation = allocate_points(hero.hidden_affinity, config.POINTS_PER_LEVEL_UP, rng)
    old_max_hp = hero.max_hp
    hero.attributes = hero.attributes.with_bonus(
        might=allocation[AttributeName.MIGHT],
        focus=allocation[AttributeName.FOCUS],
        resolve=allocation[AttributeName.RESOLVE],
        agility=allocation[AttributeName.AGILITY],
    )
    hero.level += 1
    hero.max_hp = compute_max_hp(hero.attributes)
    hero.current_hp += hero.max_hp - old_max_hp


def compute_enemy_strength(enemy_squad: list[Hero]) -> int:
    """Sum of enemy levels — the per-battle XP pool's basis.

    Isolated in its own function since this is exactly the number most
    likely to be revised as balance work continues (see
    docs/03_phase2a_definition.md section 5); sum-of-attributes is an
    equally valid alternative the doc calls out, just not the one chosen
    here.
    """
    return sum(enemy.level for enemy in enemy_squad)


def compute_battle_xp_pool(enemy_squad: list[Hero]) -> int:
    """Total Track 1 XP pool awarded on battle victory."""
    return config.XP_POOL_PER_STRENGTH_POINT * compute_enemy_strength(enemy_squad)


def award_battle_xp(
    fielded: list[Hero],
    benched: list[Hero],
    enemy_squad: list[Hero],
    rng: random.Random,
    bench_multiplier: float = config.BENCH_XP_BONUS_MULTIPLIER,
) -> None:
    """Track 1 XP as a per-battle pool, split evenly across `fielded`.

    Downed heroes need no special-casing: they're never removed from
    their squad list, so they're still in `fielded` and receive a full
    share like anyone else — they were present. `benched` heroes receive
    a separate bonus pool on top (not carved out of the fielded pool),
    scaled by `bench_multiplier`; Phase 2a has no bench, so `benched` is
    always empty in practice, but the plumbing exists now so Phase 2b's
    bench doesn't require touching this function again.
    """
    pool = compute_battle_xp_pool(enemy_squad)
    if fielded:
        share = pool // len(fielded)
        for hero in fielded:
            grant_xp(hero, share, rng)
    if benched:
        bench_pool = round(bench_multiplier * pool)
        bench_share = bench_pool // len(benched)
        for hero in benched:
            grant_xp(hero, bench_share, rng)


def revive_downed_hero(hero: Hero) -> None:
    """Downed, not dead: a hero at 0 HP comes back at a minimal HP value
    at battle end, rather than staying permanently removed."""
    if not hero.is_alive:
        hero.current_hp = config.DOWNED_REVIVE_HP


def grant_class_xp(
    hero: Hero, track: ClassTrack, amount: int = config.CLASS_XP_PER_ABILITY_USE
) -> None:
    """Track 2 accrual only this phase — no thresholds fire, no unlocks."""
    hero.class_xp[track] += amount


def grant_class_xp_for_ability(
    hero: Hero, ability: Ability, amount: int = config.CLASS_XP_PER_ABILITY_USE
) -> None:
    """Credit whichever track owns `ability`, per data/class_tracks.yaml."""
    track = class_track_library.load_class_tracks()[ability.name]
    grant_class_xp(hero, track, amount)
