from __future__ import annotations

from typing import TYPE_CHECKING

from .. import config
from ..models.grid import Position
from . import queries
from .turn import AbilityDecision, TurnDecision

if TYPE_CHECKING:
    from ..models.grid import Grid
    from ..models.hero import Hero

__all__ = ["AbilityDecision", "TurnDecision", "decide_turn"]


def decide_turn(
    actor: Hero, allies: list[Hero], enemies: list[Hero], grid: Grid
) -> TurnDecision:
    """Primitive priority-list decision strategy, swappable per architecture doc.

    1. If a living ally is hurt below `config.HEAL_TRIGGER_HP_FRACTION` and a
       heal ability can reach them (moving toward them first if needed),
       heal — life preservation outranks attacking.
    2. Otherwise, attack: compare the strongest reachable attack from the
       actor's current position against the strongest reachable attack after
       moving toward the nearest enemy, and take whichever is better. This
       naturally prefers a hard-hitting melee strike when reachable, but
       falls back to whatever ranged attack it *can* reach if not — it never
       moves somewhere strictly worse just to attack.
    3. If no attack is reachable even after moving, just move toward the
       nearest enemy. If there are no living enemies, pass.
    """
    living_allies = [ally for ally in allies if ally.is_alive]
    living_enemies = [enemy for enemy in enemies if enemy.is_alive]

    heal_decision = _decide_heal(actor, allies, enemies, living_allies, grid)
    if heal_decision is not None:
        return heal_decision

    if not living_enemies:
        return TurnDecision(destination=None, ability_decision=None)

    return _decide_attack(actor, allies, enemies, living_enemies, grid)


def _decide_heal(
    actor: Hero,
    allies: list[Hero],
    enemies: list[Hero],
    living_allies: list[Hero],
    grid: Grid,
) -> TurnDecision | None:
    most_injured = _most_injured_ally(living_allies)
    if most_injured is None:
        return None

    heal_decision = _best_heal_decision(actor, actor.position, living_allies)
    if heal_decision is not None:
        return TurnDecision(destination=None, ability_decision=heal_decision)

    occupied = queries.occupied_positions(actor, allies, enemies)
    destination = _step_toward(actor.position, most_injured.position, grid, occupied)
    heal_decision = _best_heal_decision(actor, destination, living_allies)
    if heal_decision is not None:
        return TurnDecision(destination=destination, ability_decision=heal_decision)

    return None


def _decide_attack(
    actor: Hero,
    allies: list[Hero],
    enemies: list[Hero],
    living_enemies: list[Hero],
    grid: Grid,
) -> TurnDecision:
    current_best = _best_offensive_decision(actor, actor.position, living_enemies)

    nearest = min(
        living_enemies, key=lambda enemy: actor.position.distance_to(enemy.position)
    )
    occupied = queries.occupied_positions(actor, allies, enemies)
    destination = _step_toward(actor.position, nearest.position, grid, occupied)
    moved_best = _best_offensive_decision(actor, destination, living_enemies)

    if moved_best is not None and (current_best is None or moved_best[1] > current_best[1]):
        return TurnDecision(destination=destination, ability_decision=moved_best[0])
    if current_best is not None:
        return TurnDecision(destination=None, ability_decision=current_best[0])
    return TurnDecision(destination=destination, ability_decision=None)


def _most_injured_ally(living_allies: list[Hero]) -> Hero | None:
    injured = [
        ally
        for ally in living_allies
        if ally.current_hp / ally.max_hp < config.HEAL_TRIGGER_HP_FRACTION
    ]
    if not injured:
        return None
    return min(injured, key=lambda ally: ally.current_hp / ally.max_hp)


def _best_heal_decision(
    caster: Hero, position: Position, living_allies: list[Hero]
) -> AbilityDecision | None:
    best: tuple[AbilityDecision, float] | None = None
    for ability in queries.usable_abilities(caster):
        if not ability.targets_ally:
            continue
        for ally in queries.valid_targets(caster, ability, position, living_allies, []):
            if ally.current_hp / ally.max_hp >= config.HEAL_TRIGGER_HP_FRACTION:
                continue
            preview = queries.preview_ability_outcome(caster, ability, ally)
            score = preview.expected_healing
            if best is None or score > best[1]:
                best = (AbilityDecision(ability=ability, target=ally), score)
    return best[0] if best is not None else None


def _best_offensive_decision(
    caster: Hero, position: Position, living_enemies: list[Hero]
) -> tuple[AbilityDecision, float] | None:
    """The strongest reachable attack from `position`, scored by expected
    damage (a killing blow always outranks raw damage maximization)."""
    best: tuple[AbilityDecision, float] | None = None
    for ability in queries.usable_abilities(caster):
        if ability.targets_ally:
            continue
        for enemy in queries.valid_targets(caster, ability, position, [], living_enemies):
            preview = queries.preview_ability_outcome(caster, ability, enemy)
            score = (
                preview.expected_damage
                + config.AI_KILL_SCORE_BONUS * preview.kill_probability
            )
            if best is None or score > best[1]:
                best = (AbilityDecision(ability=ability, target=enemy), score)
    return best


def _step_toward(
    start: Position, target: Position, grid: Grid, occupied: set[Position]
) -> Position:
    current = start
    for _ in range(config.MOVEMENT_RANGE):
        dx = target.x - current.x
        dy = target.y - current.y
        if dx == 0 and dy == 0:
            break
        if abs(dx) >= abs(dy) and dx != 0:
            candidate = Position(current.x + (1 if dx > 0 else -1), current.y)
        elif dy != 0:
            candidate = Position(current.x, current.y + (1 if dy > 0 else -1))
        else:
            break
        if not grid.in_bounds(candidate) or candidate in occupied or candidate == target:
            break
        current = candidate
    return current
