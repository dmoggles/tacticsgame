from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AttributeName(str, Enum):
    MIGHT = "might"
    FOCUS = "focus"
    RESOLVE = "resolve"
    AGILITY = "agility"


@dataclass(frozen=True)
class Attributes:
    might: int
    focus: int
    resolve: int
    agility: int

    def with_bonus(
        self,
        *,
        might: int = 0,
        focus: int = 0,
        resolve: int = 0,
        agility: int = 0,
    ) -> Attributes:
        return Attributes(
            might=self.might + might,
            focus=self.focus + focus,
            resolve=self.resolve + resolve,
            agility=self.agility + agility,
        )


@dataclass(frozen=True)
class AffinityVector:
    """Hidden per-hero weights over the four attributes, summing to 1.

    Never surfaced in player-facing output; dev/test logging only.
    """

    might: float
    focus: float
    resolve: float
    agility: float

    def as_weights(self) -> list[tuple[AttributeName, float]]:
        return [
            (AttributeName.MIGHT, self.might),
            (AttributeName.FOCUS, self.focus),
            (AttributeName.RESOLVE, self.resolve),
            (AttributeName.AGILITY, self.agility),
        ]
