from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .hero import Hero


@dataclass(frozen=True)
class ResolutionResult:
    damage: int = 0
    healing: int = 0
    description: str = ""


# rng is unused by any effect this phase (resolution is fully
# deterministic) but is threaded through now so semi-random/contested
# resolution math (TODO(phaseN+)) can be added inside an effect function
# later without changing how abilities are invoked.
AbilityEffect = Callable[["Hero", "Hero", random.Random], ResolutionResult]


@dataclass(frozen=True)
class Ability:
    name: str
    range: int
    targets_ally: bool
    effect: AbilityEffect
    cost: int | None = None
    min_range: int = 0
    cooldown: int = 0  # turns (of the caster's own turns) before reuse; 0 = no cooldown
