from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

from .. import config
from ..engine import progression, roster

if TYPE_CHECKING:
    from ..engine.session import Session
    from ..models.attributes import AttributeName
    from ..models.hero import Hero

# Drives the between-battle screen's interaction (docs/04_phase2b_definition.md
# section 6): resolve any pending manual attribute allocations (section 5),
# then choose the next battle's fielded squad (section 2). No pygame import —
# mirrors visualizer/player_input.py's split between pure interaction logic
# (here, fully unit-testable headlessly) and event-loop plumbing (renderer.py).
#
# Nothing here mutates Session/Hero state except through
# progression.resolve_manual_allocation() and, on confirm(),
# Session.begin_battle() — the same "nothing applies until the deliberate
# final step" shape PlayerTurnController uses for a battle turn.


class BetweenBattlePhase(Enum):
    ALLOCATING = auto()  # resolving a pending manual level-up point
    SELECTING = auto()  # choosing the fielded squad
    READY = auto()  # a legal squad is selected; confirm() will start the battle


@dataclass
class BetweenBattleController:
    session: Session
    phase: BetweenBattlePhase = field(init=False)
    selected: list[Hero] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        # Defaults to re-fielding whoever fought last battle — a one-click
        # confirm for the common case, still freely overridable via
        # toggle_fielded() before confirming.
        self.selected = list(self.session.fielded)
        self.phase = (
            BetweenBattlePhase.ALLOCATING
            if self.pending_hero is not None
            else self._phase_after_selection_change()
        )

    @property
    def pending_hero(self) -> Hero | None:
        """The roster hero (in roster order) currently awaiting a manual
        allocation choice, or None once every pending level-up is resolved."""
        return next((hero for hero in self.session.roster if hero.pending_level_ups > 0), None)

    def choose_manual_attribute(self, attribute: AttributeName | None) -> bool:
        """`attribute=None` means the player declined/skipped — the point
        still gets allocated by affinity, never forfeited (see
        progression.resolve_manual_allocation). A multi-level jump keeps
        `pending_hero` on the same hero until every one of their pending
        level-ups is resolved, one call per level-up."""
        if self.phase != BetweenBattlePhase.ALLOCATING:
            return False
        hero = self.pending_hero
        if hero is None:
            return False
        progression.resolve_manual_allocation(hero, attribute, self.session.rng)
        if self.pending_hero is None:
            self.phase = self._phase_after_selection_change()
        return True

    def toggle_fielded(self, hero: Hero) -> bool:
        if self.phase not in (BetweenBattlePhase.SELECTING, BetweenBattlePhase.READY):
            return False
        if any(candidate is hero for candidate in self.selected):
            self.selected = [candidate for candidate in self.selected if candidate is not hero]
        elif len(self.selected) < config.FIELDED_SQUAD_SIZE:
            self.selected.append(hero)
        else:
            return False
        self.phase = self._phase_after_selection_change()
        return True

    @property
    def is_ready(self) -> bool:
        return self.phase == BetweenBattlePhase.READY

    def confirm(self) -> None:
        assert self.is_ready, "confirm() called before a legal squad was selected"
        self.session.begin_battle(self.selected)

    def _phase_after_selection_change(self) -> BetweenBattlePhase:
        return BetweenBattlePhase.READY if self.selected else BetweenBattlePhase.SELECTING
