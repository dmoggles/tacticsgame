from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .. import config
from ..models.ability import AbilityEffect, ResolutionResult

if TYPE_CHECKING:
    from ..models.hero import Hero

# Effects are built from declarative EffectComponents rather than one
# hand-written function per ability. Contested versus automatic resolution,
# the magnitude profile, and automatic variance all come from ability data.


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
    base: float
    scaling: list[ScalingTerm]
    verb: str
    applies_to: str = "target"  # "target" | "caster"
    contested: bool = True
    profile: DamageProfile | None = None
    automatic_variance_width: float = 0.0


@dataclass(frozen=True)
class ContestResult:
    """The fully observable outcome of one attacker-versus-defender roll."""

    attack_score: float
    advantaged_attack_score: float
    defence_score: float
    attacker_roll: float
    defender_roll: float
    margin: float

    @property
    def succeeded(self) -> bool:
        """A tie is a failed contest; a landed action must win outright."""
        return self.margin > 0


@dataclass(frozen=True)
class DamageProfile:
    """Margin-to-magnitude curve, loaded from named ability-data profiles."""

    base_flat: float
    base_per_attack: float
    baseline_quality: float
    margin_sensitivity: float
    quality_floor: float
    quality_cap: float


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


def roll_contest_score(score: float, rng: random.Random) -> float:
    """A continuous, bell-shaped roll whose width scales with ``score``."""
    return sum(
        rng.random() * score / config.CONTEST_ROLL_SAMPLE_COUNT
        for _ in range(config.CONTEST_ROLL_SAMPLE_COUNT)
    )


def resolve_contest(
    attacker: Hero, defender: Hero, scaling: list[ScalingTerm], rng: random.Random
) -> ContestResult:
    """Resolve one pure contested roll for an offensive effect component."""
    attack_score = weighted_attribute_score(attacker, scaling)
    advantaged_attack_score = attack_score * config.ATTACKER_ADVANTAGE
    primary_attribute = primary_attack_attribute(scaling)
    defender_score = defence_score(defender, primary_attribute)
    attacker_roll = roll_contest_score(advantaged_attack_score, rng)
    defender_roll = roll_contest_score(defender_score, rng)
    margin = attacker_roll - defender_roll
    return ContestResult(
        attack_score=attack_score,
        advantaged_attack_score=advantaged_attack_score,
        defence_score=defender_score,
        attacker_roll=attacker_roll,
        defender_roll=defender_roll,
        margin=margin,
    )


def normalised_margin(contest: ContestResult) -> float:
    """Dimensionless contest quality; raw margin never reaches damage math."""
    denominator = contest.advantaged_attack_score + contest.defence_score
    return 2 * contest.margin / denominator if denominator else 0.0


def damage_from_contest(contest: ContestResult, profile: DamageProfile) -> int:
    """Calculate a floored, capped magnitude from a successful contest."""
    if not contest.succeeded:
        return 0
    base = profile.base_flat + profile.base_per_attack * contest.attack_score
    quality = profile.baseline_quality + profile.margin_sensitivity * normalised_margin(contest)
    clamped_quality = min(profile.quality_cap, max(profile.quality_floor, quality))
    return max(1, round(base * clamped_quality))


def make_effect(components: list[EffectComponent]) -> AbilityEffect:
    """Build an (caster, target, rng) -> ResolutionResult effect from
    declarative components, matching the AbilityEffect contract exactly so
    the rest of the engine invokes it the same way regardless of how many
    components an ability has."""

    def effect(caster: Hero, target: Hero, rng: random.Random) -> ResolutionResult:
        total_damage = 0
        total_healing = 0
        clauses: list[str] = []
        for component in components:
            recipient = caster if component.applies_to == "caster" else target
            if component.profile is None:
                # Compatibility while Step 4 data migration is in progress.
                amount = round(component.base + weighted_attribute_score(caster, component.scaling))
            elif component.contested:
                contest = resolve_contest(caster, target, component.scaling, rng)
                amount = damage_from_contest(contest, component.profile)
            else:
                attack_score = weighted_attribute_score(caster, component.scaling)
                base = component.profile.base_flat + component.profile.base_per_attack * attack_score
                synthetic_margin = rng.uniform(
                    -component.automatic_variance_width, component.automatic_variance_width
                )
                quality = component.profile.baseline_quality + component.profile.margin_sensitivity * synthetic_margin
                amount = max(
                    1,
                    round(base * min(component.profile.quality_cap, max(component.profile.quality_floor, quality))),
                )
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
