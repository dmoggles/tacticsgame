from __future__ import annotations

import copy
import random
from collections import deque
from dataclasses import dataclass
from statistics import fmean
from typing import TYPE_CHECKING

from .. import config
from ..models.grid import Position

if TYPE_CHECKING:
    from ..models.ability import Ability, ResolutionResult
    from ..models.grid import Grid
    from ..models.hero import Hero

# Single source of truth for "what can this hero legally do right now" —
# see docs/03_phase2a_definition.md and docs/adr/0002-legal-action-query-api.md.
# Read-only: nothing here mutates battle state. `ai.decide_turn` consumes
# this module rather than computing legality itself, so the AI and any
# future UI can never disagree about what's legal.


@dataclass(frozen=True)
class AbilityOutcomePreview:
    """Sampled, non-mutating distribution for one candidate action.

    Expected damage is the probability-weighted action value (failed attacks
    contribute zero). ``expected_damage_on_success`` preserves the conditional
    quantity needed to explain the odds to a player later.
    """

    success_probability: float
    expected_damage: float
    expected_damage_on_success: float
    expected_healing: float
    kill_probability: float
    damage_samples: tuple[int, ...]
    magnitude_samples: tuple[int, ...]


def magnitude_range(preview: AbilityOutcomePreview) -> tuple[int, int]:
    """Return the literal sampled min–max range of landed magnitude.

    Failed attacks are excluded: success chance is already displayed
    separately, and including zeros would make a high-miss attack read as if
    it sometimes *lands* for zero damage. Automatic healing uses its sampled
    healing magnitudes through the same field.
    """
    samples = [sample for sample in preview.magnitude_samples if sample > 0]
    if not samples:
        return (0, 0)
    return (min(samples), max(samples))


def occupied_positions(actor: Hero, allies: list[Hero], enemies: list[Hero]) -> set[Position]:
    """Tiles no hero may move onto: every other living hero's position."""
    return {
        hero.position
        for hero in (*allies, *enemies)
        if hero is not actor and hero.is_alive
    }


def reachable_destinations(
    actor: Hero, allies: list[Hero], enemies: list[Hero], grid: Grid
) -> set[Position]:
    """All tiles `actor` could legally end its move on this turn.

    4-connected BFS flood-fill up to `config.MOVEMENT_RANGE` hops, pruned by
    grid bounds and occupancy. Always includes the actor's own tile (not
    moving is always legal).
    """
    occupied = occupied_positions(actor, allies, enemies)
    start = actor.position
    reachable = {start}
    frontier = deque([(start, 0)])
    while frontier:
        position, distance = frontier.popleft()
        if distance == config.MOVEMENT_RANGE:
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            candidate = Position(position.x + dx, position.y + dy)
            if candidate in reachable:
                continue
            if not grid.in_bounds(candidate) or candidate in occupied:
                continue
            reachable.add(candidate)
            frontier.append((candidate, distance + 1))
    return reachable


def usable_abilities(actor: Hero) -> list[Ability]:
    """Abilities not on cooldown.

    `Ability.cost` is deliberately not filtered on — no resource system
    exists yet (see docs/adr/0001-ability-data-yaml-refactor.md).
    """
    return [
        ability
        for ability in actor.abilities
        if actor.cooldowns.get(ability.name, 0) <= 0
    ]


def valid_targets(
    actor: Hero,
    ability: Ability,
    position: Position,
    allies: list[Hero],
    enemies: list[Hero],
) -> list[Hero]:
    """Legal targets for `ability` if cast from `position` (hypothetical —
    not necessarily `actor.position`, so move-then-act evaluation and a
    future move-preview UI can both reuse this).

    Returns every legal target regardless of whether it's a *good* choice
    (e.g. a full-HP ally is still a legal heal target) — legality and
    strategy stay separated; callers apply their own preference on top.
    """
    pool = allies if ability.targets_ally else enemies
    return [
        hero
        for hero in pool
        if hero.is_alive
        and ability.min_range <= position.distance_to(hero.position) <= ability.range
    ]


def preview_ability_outcome(caster: Hero, ability: Ability, target: Hero) -> AbilityOutcomePreview:
    """Return a deterministic sampled distribution for an ability action.

    Every sample runs the live effect against scratch copies, so expected
    magnitude integrates the real contest-margin curve rather than evaluating
    damage at a mean margin. The fixed preview RNG keeps AI choices and a
    future player display reproducible without consuming battle RNG.
    """
    rng = random.Random(0)
    results = []
    for _ in range(config.ABILITY_PREVIEW_SAMPLE_COUNT):
        scratch_caster = copy.copy(caster)
        scratch_target = copy.copy(target)
        results.append(ability.effect(scratch_caster, scratch_target, rng))

    damages = tuple(result.damage for result in results)
    healings = tuple(result.healing for result in results)
    successful_damage = tuple(damage for damage in damages if damage > 0)
    success_count = sum(
        damage > 0 or healing > 0 for damage, healing in zip(damages, healings, strict=True)
    )
    return AbilityOutcomePreview(
        success_probability=success_count / len(results),
        expected_damage=fmean(damages),
        expected_damage_on_success=fmean(successful_damage) if successful_damage else 0.0,
        expected_healing=fmean(healings),
        kill_probability=sum(damage >= target.current_hp for damage in damages) / len(results),
        damage_samples=damages,
        magnitude_samples=tuple(max(damage, healing) for damage, healing in zip(damages, healings, strict=True)),
    )
