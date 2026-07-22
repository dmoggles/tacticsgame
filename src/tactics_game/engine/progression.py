from __future__ import annotations

import random

from .. import config
from ..models.ability import Ability, ClassTrack
from ..models.attributes import AffinityVector, AttributeName, Attributes
from ..models.grid import Position
from ..models.hero import Hero
from . import resolution


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
    """The classless Tier 0 kit every hero starts with, filling all 4 slots."""
    return [
        Ability(
            name="Basic Strike",
            class_track=ClassTrack.FIGHTER,
            range=config.BASIC_STRIKE_RANGE,
            targets_ally=False,
            effect=resolution.resolve_basic_strike,
        ),
        Ability(
            name="Basic Shot",
            class_track=ClassTrack.MARKSMAN,
            range=config.BASIC_SHOT_RANGE,
            min_range=config.BASIC_SHOT_MIN_RANGE,
            targets_ally=False,
            effect=resolution.resolve_basic_shot,
        ),
        Ability(
            name="Basic Bolt",
            class_track=ClassTrack.CASTER,
            range=config.BASIC_BOLT_RANGE,
            targets_ally=False,
            effect=resolution.resolve_basic_bolt,
        ),
        Ability(
            name="Basic Mend",
            class_track=ClassTrack.HEALER,
            range=config.BASIC_MEND_RANGE,
            cooldown=config.BASIC_MEND_COOLDOWN,
            targets_ally=True,
            effect=resolution.resolve_basic_mend,
        ),
    ]


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


def grant_class_xp(
    hero: Hero, track: ClassTrack, amount: int = config.CLASS_XP_PER_ABILITY_USE
) -> None:
    """Track 2 accrual only this phase — no thresholds fire, no unlocks."""
    hero.class_xp[track] += amount
