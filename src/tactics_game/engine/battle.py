from __future__ import annotations

import random
from dataclasses import dataclass, field

from .. import config
from ..models.grid import Grid
from ..models.hero import Hero
from . import ai, progression, turn_order


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

    @property
    def all_heroes(self) -> list[Hero]:
        return [*self.player_squad, *self.enemy_squad]

    def step(self) -> None:
        """Advance the simulation by exactly one hero's turn."""
        if self.is_over:
            return
        actor = self._next_actor()
        if actor is None:
            return
        self._take_turn(actor)
        self._check_win_condition()

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

    def _take_turn(self, actor: Hero) -> None:
        self._tick_cooldowns(actor)

        allies = self.player_squad if actor.is_player_controlled else self.enemy_squad
        enemies = self.enemy_squad if actor.is_player_controlled else self.player_squad
        decision = ai.decide_turn(actor, allies, enemies, self.grid)

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

    def _tick_cooldowns(self, actor: Hero) -> None:
        """Cooldowns count down once per the actor's own turn."""
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
