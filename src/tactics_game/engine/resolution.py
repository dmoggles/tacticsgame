from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..models.ability import AbilityEffect, ResolutionResult

if TYPE_CHECKING:
    from ..models.hero import Hero

# Phase 1 resolution is deterministic — no contested rolls yet — but each
# ability's magnitude scales with whichever attribute(s) its data says it
# should (see data/abilities.yaml). Effects are built from declarative
# EffectComponents rather than one hand-written function per ability, so
# adding/tuning an ability is a data change, not a code change.
# TODO(phaseN+): contested-roll resolution math (rng is already threaded
# through AbilityEffect for this, but unused so far).


@dataclass(frozen=True)
class ScalingTerm:
    """One attribute's contribution to an effect component's magnitude."""

    attribute: str  # might | focus | resolve | agility (caster.attributes)
    multiplier: float
    # TODO(phaseN+): gear-sourced terms once equipment exists as a concept
    # — extend this with a `source` field rather than restructuring
    # EffectComponent.


@dataclass(frozen=True)
class EffectComponent:
    """One damage/heal application within an ability's effect.

    An ability's effect is a list of these — most abilities need exactly
    one, but this supports e.g. an attack with a secondary self-heal
    without changing how abilities are invoked.
    """

    kind: str  # "damage" | "heal"
    # TODO(phaseN+): a "roll" kind (and/or a `contested: bool` flag) once
    # semi-random / opposed resolution is implemented.
    base: float
    scaling: list[ScalingTerm]
    verb: str
    applies_to: str = "target"  # "target" | "caster"


def make_effect(components: list[EffectComponent]) -> AbilityEffect:
    """Build an (caster, target, rng) -> ResolutionResult effect from
    declarative components, matching the AbilityEffect contract exactly so
    the rest of the engine invokes it the same way regardless of how many
    components an ability has."""

    def effect(caster: Hero, target: Hero, rng: random.Random) -> ResolutionResult:
        # rng is unused this phase — resolution is still fully
        # deterministic. TODO(phaseN+): semi-random modified rolls,
        # possibly contested against target's own roll (target is already
        # fully available above for that).
        total_damage = 0
        total_healing = 0
        clauses: list[str] = []
        for component in components:
            recipient = caster if component.applies_to == "caster" else target
            scaling_value = sum(
                getattr(caster.attributes, term.attribute) * term.multiplier
                for term in component.scaling
            )
            amount = round(component.base + scaling_value)
            if component.kind == "damage":
                recipient.current_hp = max(0, recipient.current_hp - amount)
                total_damage += amount
            else:
                recipient.current_hp = min(recipient.max_hp, recipient.current_hp + amount)
                total_healing += amount
            clauses.append(f"{caster.name} {component.verb} {recipient.name} for {amount}")
        return ResolutionResult(
            damage=total_damage, healing=total_healing, description="; ".join(clauses)
        )

    return effect
