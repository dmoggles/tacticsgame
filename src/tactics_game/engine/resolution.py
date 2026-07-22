from __future__ import annotations

from typing import TYPE_CHECKING

from .. import config
from ..models.ability import ResolutionResult

if TYPE_CHECKING:
    from ..models.hero import Hero

# Phase 1 resolution is deterministic — no contested rolls yet — but each
# basic ability's magnitude scales with the attribute matching its
# archetype (Fighter/Might, Marksman/Agility, Caster/Focus, Healer/Resolve),
# so a hero's synthesized attributes make them meaningfully better at the
# ability that matches their hidden affinity lean. Each function mutates
# `target` and returns a ResolutionResult describing what happened, matching
# the (caster, target) -> ResolutionResult ability effect signature so this
# math can be swapped out later without touching how abilities are invoked.
# TODO(phase2+): contested-roll resolution math.


def resolve_basic_strike(caster: Hero, target: Hero) -> ResolutionResult:
    damage = config.BASIC_STRIKE_DAMAGE + caster.attributes.might * config.BASIC_STRIKE_MIGHT_SCALING
    target.current_hp = max(0, target.current_hp - damage)
    return ResolutionResult(
        damage=damage,
        description=f"{caster.name} strikes {target.name} for {damage}",
    )


def resolve_basic_shot(caster: Hero, target: Hero) -> ResolutionResult:
    damage = config.BASIC_SHOT_DAMAGE + caster.attributes.agility * config.BASIC_SHOT_AGILITY_SCALING
    target.current_hp = max(0, target.current_hp - damage)
    return ResolutionResult(
        damage=damage,
        description=f"{caster.name} shoots {target.name} for {damage}",
    )


def resolve_basic_bolt(caster: Hero, target: Hero) -> ResolutionResult:
    damage = config.BASIC_BOLT_DAMAGE + caster.attributes.focus * config.BASIC_BOLT_FOCUS_SCALING
    target.current_hp = max(0, target.current_hp - damage)
    return ResolutionResult(
        damage=damage,
        description=f"{caster.name} bolts {target.name} for {damage}",
    )


def resolve_basic_mend(caster: Hero, target: Hero) -> ResolutionResult:
    healing = round(
        config.BASIC_MEND_HEAL + caster.attributes.resolve * config.BASIC_MEND_RESOLVE_SCALING
    )
    target.current_hp = min(target.max_hp, target.current_hp + healing)
    return ResolutionResult(
        healing=healing,
        description=f"{caster.name} mends {target.name} for {healing}",
    )
