from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.ability import Ability
    from ..models.grid import Position
    from ..models.hero import Hero

# A turn's shape, independent of who decided it — ai.decide_turn produces
# one, and so does a human via visualizer/player_input.py::PlayerTurnController.


@dataclass(frozen=True)
class AbilityDecision:
    ability: Ability
    target: Hero


@dataclass(frozen=True)
class TurnDecision:
    """A full turn: an entity may move up to its move points AND act.

    `destination` is None if the actor doesn't move; `ability_decision` is
    None if it doesn't act. Both may be set on the same turn.
    """

    destination: Position | None
    ability_decision: AbilityDecision | None
