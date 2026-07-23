from __future__ import annotations

import copy
import random
from collections import deque
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


def preview_ability_outcome(caster: Hero, ability: Ability, target: Hero) -> ResolutionResult:
    """Non-mutating preview of an ability's effect, reusing the real
    resolution math.

    Runs the effect against scratch copies of both caster and target — not
    just target — since an effect component can apply to the caster (e.g. a
    self-heal), and previewing an option must never actually apply it.
    """
    scratch_caster = copy.copy(caster)
    scratch_target = copy.copy(target)
    return ability.effect(scratch_caster, scratch_target, random.Random())
