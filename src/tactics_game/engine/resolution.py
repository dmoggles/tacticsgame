from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import config
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


@dataclass(frozen=True)
class ContestResult:
    """The fully observable outcome of one attacker-versus-defender roll."""

    attack_score: float
    defence_score: float
    attacker_noise: int
    defender_noise: int
    attacker_roll: float
    defender_roll: float
    margin: float

    @property
    def succeeded(self) -> bool:
        """A tie is a failed contest; a landed action must win outright."""
        return self.margin > 0


def weighted_attribute_score(hero: Hero, scaling: list[ScalingTerm]) -> float:
    """Return one component's attribute-weighted score for ``hero``."""
    return sum(getattr(hero.attributes, term.attribute) * term.multiplier for term in scaling)


def primary_attack_attribute(scaling: list[ScalingTerm]) -> str:
    """The unique highest-weighted attribute of an offensive component.

    Step 4's YAML validation will enforce this same invariant for data-loaded
    offensive components. Raising now avoids silently choosing an arbitrary
    defence relationship for malformed future data.
    """
    if not scaling:
        raise ValueError("a contested attack requires at least one scaling term")
    highest_multiplier = max(term.multiplier for term in scaling)
    primary_terms = [term for term in scaling if term.multiplier == highest_multiplier]
    if len(primary_terms) != 1:
        raise ValueError("a contested attack requires one unique primary attribute")
    return primary_terms[0].attribute


def defence_score(defender: Hero, primary_attribute: str) -> float:
    """Resolve plus the incoming attack's primary attribute, both tuneable."""
    return (
        defender.attributes.resolve * config.DEFENCE_RESOLVE_WEIGHT
        + getattr(defender.attributes, primary_attribute) * config.DEFENCE_PRIMARY_ATTRIBUTE_WEIGHT
    )


def roll_contest_noise(rng: random.Random) -> int:
    """One centered bell-shaped noise roll configured as a sum of equal dice."""
    dice_total = sum(
        rng.randint(1, config.CONTEST_DIE_FACES) for _ in range(config.CONTEST_DICE_COUNT)
    )
    center = config.CONTEST_DICE_COUNT * (config.CONTEST_DIE_FACES + 1) // 2
    return dice_total - center


def resolve_contest(
    attacker: Hero, defender: Hero, scaling: list[ScalingTerm], rng: random.Random
) -> ContestResult:
    """Resolve one pure contested roll for an offensive effect component."""
    attack_score = weighted_attribute_score(attacker, scaling)
    primary_attribute = primary_attack_attribute(scaling)
    defender_score = defence_score(defender, primary_attribute)
    attacker_noise = roll_contest_noise(rng)
    defender_noise = roll_contest_noise(rng)
    attacker_roll = attack_score + attacker_noise
    defender_roll = defender_score + defender_noise
    margin = round(attacker_roll - defender_roll, config.CONTEST_MARGIN_DECIMAL_PLACES)
    return ContestResult(
        attack_score=attack_score,
        defence_score=defender_score,
        attacker_noise=attacker_noise,
        defender_noise=defender_noise,
        attacker_roll=attacker_roll,
        defender_roll=defender_roll,
        margin=margin,
    )


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
            scaling_value = weighted_attribute_score(caster, component.scaling)
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
