from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .hero import Hero


class ClassTrack(str, Enum):
    """Track 2 usage-based specialization counters (accrual only in Phase 1)."""

    FIGHTER = "fighter"
    MARKSMAN = "marksman"
    CASTER = "caster"
    HEALER = "healer"


@dataclass(frozen=True)
class ResolutionResult:
    damage: int = 0
    healing: int = 0
    description: str = ""


# TODO(phase2+): swap flat/free-action resolution for attribute-scaled or
# contested-roll math without changing this call signature.
AbilityEffect = Callable[["Hero", "Hero"], ResolutionResult]


@dataclass(frozen=True)
class Ability:
    name: str
    class_track: ClassTrack
    range: int
    targets_ally: bool
    effect: AbilityEffect
    cost: int | None = None
    min_range: int = 0
    cooldown: int = 0  # turns (of the caster's own turns) before reuse; 0 = no cooldown
