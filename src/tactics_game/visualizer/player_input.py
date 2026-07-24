from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from ..engine import queries
from ..engine.turn import AbilityDecision, TurnDecision

if TYPE_CHECKING:
    from ..engine.queries import AbilityOutcomePreview
    from ..models.ability import Ability
    from ..models.grid import Grid, Position
    from ..models.hero import Hero

# Accumulates one player-controlled hero's turn from clicks/keys into a
# TurnDecision, using engine/queries.py as the single source of legal
# actions at every stage — this module never computes reachability, range,
# or cooldown legality itself. No pygame import: this is pure interaction
# *logic*, kept separate from the event-loop plumbing in renderer.py, and
# fully unit-testable headlessly as a result.
#
# Nothing here mutates Battle/Hero state. The caller takes the finished
# TurnDecision (via build_decision(), once is_ready) and applies it through
# Battle.take_turn() — the one and only engine mutation in the whole flow.


class InputPhase(Enum):
    IDLE = auto()  # waiting for the player to select the active hero
    MOVING = auto()  # choosing a destination, or declining
    ACTING = auto()  # choosing an ability, or declining
    TARGETING = auto()  # choosing a target for the chosen ability
    READY = auto()  # move/act decided; waiting for an explicit end-turn


@dataclass
class PlayerTurnController:
    actor: Hero
    allies: list[Hero]
    enemies: list[Hero]
    grid: Grid
    phase: InputPhase = InputPhase.IDLE
    pending_destination: Position | None = field(default=None, init=False)
    pending_ability: Ability | None = field(default=None, init=False)
    pending_ability_decision: AbilityDecision | None = field(default=None, init=False)
    _preview_cache: dict[int, AbilityOutcomePreview] = field(default_factory=dict, init=False)

    def select_active_hero(self) -> bool:
        if self.phase != InputPhase.IDLE:
            return False
        self.phase = InputPhase.MOVING
        return True

    @property
    def effective_position(self) -> Position:
        return self.pending_destination or self.actor.position

    @property
    def reachable_tiles(self) -> set[Position]:
        return queries.reachable_destinations(self.actor, self.allies, self.enemies, self.grid)

    @property
    def usable_abilities(self) -> list[Ability]:
        return queries.usable_abilities(self.actor)

    @property
    def valid_targets(self) -> list[Hero]:
        if self.pending_ability is None:
            return []
        return queries.valid_targets(
            self.actor, self.pending_ability, self.effective_position, self.allies, self.enemies
        )

    def outcome_preview_for(self, target: Hero) -> AbilityOutcomePreview | None:
        """The engine-owned odds for a currently selectable target.

        A player turn cannot mutate battle state before Enter commits it, so a
        small cache avoids re-sampling the same distribution every render
        frame while keeping the shown preview tied to the exact action.
        """
        if self.phase != InputPhase.TARGETING or self.pending_ability is None:
            return None
        if target not in self.valid_targets:
            return None
        key = id(target)
        if key not in self._preview_cache:
            self._preview_cache[key] = queries.preview_ability_outcome(
                self.actor, self.pending_ability, target
            )
        return self._preview_cache[key]

    def choose_destination(self, position: Position) -> bool:
        if self.phase != InputPhase.MOVING or position not in self.reachable_tiles:
            return False
        self.pending_destination = position
        self.phase = InputPhase.ACTING
        return True

    def skip_move(self) -> bool:
        if self.phase != InputPhase.MOVING:
            return False
        self.pending_destination = None
        self.phase = InputPhase.ACTING
        return True

    def choose_ability(self, ability: Ability) -> bool:
        if self.phase != InputPhase.ACTING or ability not in self.usable_abilities:
            return False
        self.pending_ability = ability
        self._preview_cache.clear()
        self.phase = InputPhase.TARGETING
        return True

    def skip_ability(self) -> bool:
        if self.phase != InputPhase.ACTING:
            return False
        self.pending_ability = None
        self.pending_ability_decision = None
        self._preview_cache.clear()
        self.phase = InputPhase.READY
        return True

    def choose_target(self, position: Position) -> bool:
        if self.phase != InputPhase.TARGETING or self.pending_ability is None:
            return False
        target = next((hero for hero in self.valid_targets if hero.position == position), None)
        if target is None:
            return False
        self.pending_ability_decision = AbilityDecision(ability=self.pending_ability, target=target)
        self.phase = InputPhase.READY
        return True

    def cancel(self) -> bool:
        """Step back exactly one stage. Nothing has been applied to
        Battle at any stage before commit, so every cancel is free.

        TARGETING -> ACTING (re-pick or skip the ability)
        ACTING or READY -> MOVING (reconsider the move too)
        MOVING -> IDLE (deselect the hero entirely)
        IDLE -> no-op
        """
        if self.phase == InputPhase.TARGETING:
            self.pending_ability = None
            self._preview_cache.clear()
            self.phase = InputPhase.ACTING
        elif self.phase in (InputPhase.ACTING, InputPhase.READY):
            self.pending_destination = None
            self.pending_ability = None
            self.pending_ability_decision = None
            self._preview_cache.clear()
            self.phase = InputPhase.MOVING
        elif self.phase == InputPhase.MOVING:
            self.phase = InputPhase.IDLE
        else:
            return False
        return True

    @property
    def is_ready(self) -> bool:
        return self.phase == InputPhase.READY

    def build_decision(self) -> TurnDecision:
        assert self.is_ready, "build_decision() called before move/act were both decided"
        return TurnDecision(
            destination=self.pending_destination,
            ability_decision=self.pending_ability_decision,
        )
