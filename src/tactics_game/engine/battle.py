from __future__ import annotations

import random
from dataclasses import dataclass, field

from .. import config
from ..models.grid import Grid
from ..models.hero import Hero
from . import ai, progression, turn_order
from .turn import TurnDecision


@dataclass(frozen=True)
class TurnLog:
    actor_name: str
    description: str


@dataclass
class Battle:
    grid: Grid
    player_squad: list[Hero]
    enemy_squad: list[Hero]
    rng: random.Random = field(default_factory=random.Random)
    round_number: int = 0
    turn_index: int = 0
    current_order: list[Hero] = field(default_factory=list)
    is_over: bool = False
    winner: str | None = None
    last_log: TurnLog | None = None

    def __post_init__(self) -> None:
        self._start_new_round()
        self._tick_current_actor_cooldowns()

    @property
    def all_heroes(self) -> list[Hero]:
        return [*self.player_squad, *self.enemy_squad]

    @property
    def current_actor(self) -> Hero | None:
        """Read-only: who is up next, without consuming their turn. `None`
        once the battle is over.

        For a UI to check before deciding whether to call `step()` (AI)
        or build a `take_turn()` decision (player) — actually consuming a
        turn always goes through `_next_actor()`, which this mirrors
        without mutating state, so it's advisory only.
        """
        if self.is_over:
            return None
        for hero in self.current_order[self.turn_index :]:
            if hero.is_alive:
                return hero
        return next(
            (
                hero
                for hero in turn_order.build_turn_order(self.player_squad, self.enemy_squad)
                if hero.is_alive
            ),
            None,
        )

    def step(self) -> None:
        """Advance the simulation by exactly one hero's turn, AI-driven
        for whichever side is up."""
        if self.is_over:
            return
        actor = self._next_actor()
        if actor is None:
            return
        allies = self.player_squad if actor.is_player_controlled else self.enemy_squad
        enemies = self.enemy_squad if actor.is_player_controlled else self.player_squad
        decision = ai.decide_turn(actor, allies, enemies, self.grid)
        self._resolve_turn(actor, decision)

    def take_turn(self, actor: Hero, decision: TurnDecision) -> None:
        """Apply a specific decision for `actor` — the manual-input
        counterpart to `step()`'s AI-driven path, for player-controlled
        heroes when the visualizer supplies the decision instead of
        `ai.decide_turn`. The caller is responsible for choosing a legal
        decision (see `engine/queries.py`); like `step()`, this doesn't
        re-validate legality, only that it's actually `actor`'s turn.
        """
        if self.is_over:
            return
        next_up = self._next_actor()
        if next_up is not actor:
            raise ValueError(f"It is not {actor.name}'s turn")
        self._resolve_turn(actor, decision)

    def run_to_completion(self, max_steps: int = config.MAX_BATTLE_STEPS) -> None:
        steps_taken = 0
        while not self.is_over and steps_taken < max_steps:
            self.step()
            steps_taken += 1

    def _next_actor(self) -> Hero | None:
        while True:
            while self.turn_index < len(self.current_order):
                candidate = self.current_order[self.turn_index]
                if candidate.is_alive:
                    return candidate
                self.turn_index += 1
            self._start_new_round()

    def _start_new_round(self) -> None:
        self.round_number += 1
        self.turn_index = 0
        self.current_order = turn_order.build_turn_order(self.player_squad, self.enemy_squad)

    def _resolve_turn(self, actor: Hero, decision: TurnDecision) -> None:
        # `actor`'s cooldowns were already ticked when they became current
        # (see _tick_current_actor_cooldowns) — before this turn's decision
        # (AI or, across many UI frames, a human) was made, not after.

        # An entity may move up to its move points AND take an action on
        # the same turn — these are independent, not mutually exclusive.
        segments: list[str] = []
        if decision.destination is not None:
            actor.position = decision.destination
            segments.append(
                f"{actor.name} moves to ({decision.destination.x}, {decision.destination.y})"
            )
        if decision.ability_decision is not None:
            ability = decision.ability_decision.ability
            result = ability.effect(actor, decision.ability_decision.target, self.rng)
            progression.grant_class_xp_for_ability(actor, ability)
            if ability.cooldown > 0:
                actor.cooldowns[ability.name] = ability.cooldown
            segments.append(result.description)

        description = "; ".join(segments) if segments else f"{actor.name} passes"

        self.last_log = TurnLog(actor_name=actor.name, description=description)
        self.turn_index += 1
        self._check_win_condition()
        if not self.is_over:
            self._tick_current_actor_cooldowns()

    def _tick_current_actor_cooldowns(self) -> None:
        """Tick the next actor's cooldowns exactly once, right as they
        become current — not at resolution time. Cooldowns must already
        reflect this turn before any decision is made from them: the AI
        decides in one shot, but a human decides across many UI frames
        via `current_actor`/`engine/queries.py`, all of which must see
        this turn's already-ticked state, not last turn's."""
        actor = self.current_actor
        if actor is not None:
            for name, remaining in list(actor.cooldowns.items()):
                if remaining > 0:
                    actor.cooldowns[name] = remaining - 1

    def _check_win_condition(self) -> None:
        if all(not hero.is_alive for hero in self.player_squad):
            self.is_over = True
            self.winner = "enemy"
        elif all(not hero.is_alive for hero in self.enemy_squad):
            self.is_over = True
            self.winner = "player"
        else:
            return
        self._resolve_battle_end()

    def _resolve_battle_end(self) -> None:
        """Track 1 XP (victory only) and downed-hero revival (regardless
        of outcome — a downed hero shouldn't stay stuck at 0 HP as an
        engine-state matter). Phase 2a has no bench, so `benched` is
        always empty here."""
        if self.winner == "player":
            progression.award_battle_xp(self.player_squad, [], self.enemy_squad, self.rng)
        for hero in self.player_squad:
            progression.revive_downed_hero(hero)
