from __future__ import annotations

import random
from dataclasses import dataclass, field

from .. import config
from ..models.grid import Grid, Position
from ..models.hero import Hero
from . import progression
from .battle import Battle

# A session (working term — see docs/03_phase2a_definition.md section 6) is
# a sequence of battles fought by one persistent player squad. Enemy squads
# are regenerated per battle (progression.generate_enemy_squad); the player
# squad's Hero objects are reused as-is across every Battle in the session,
# which is how attributes/level/xp/class_xp persist — no separate save/load
# mechanism exists or is needed (a session lives entirely in memory).


@dataclass
class Session:
    player_squad: list[Hero]
    rng: random.Random = field(default_factory=random.Random)
    battles_total: int = config.SESSION_BATTLE_COUNT
    battles_won: int = 0
    current_battle: Battle | None = field(default=None, init=False)
    is_over: bool = field(default=False, init=False)
    result: str | None = field(default=None, init=False)  # "won" | "lost"

    def __post_init__(self) -> None:
        self._prepare_next_battle()

    def advance(self) -> None:
        """Call once `self.current_battle.is_over`. Scores the finished
        battle and either starts the next one or ends the session."""
        battle = self.current_battle
        assert battle is not None and battle.is_over
        if battle.winner == "enemy":
            self.is_over = True
            self.result = "lost"
            return
        self.battles_won += 1
        if self.battles_won >= self.battles_total:
            self.is_over = True
            self.result = "won"
            return
        self._prepare_next_battle()

    def run_to_completion(self) -> None:
        """Headless convenience, mirroring Battle.run_to_completion."""
        while not self.is_over:
            assert self.current_battle is not None
            self.current_battle.run_to_completion()
            self.advance()

    def _prepare_next_battle(self) -> None:
        """Cooldowns and positions reset per battle; HP restoration is
        gated behind config.FULL_HEAL_BETWEEN_BATTLES (see its docstring —
        a Phase 2a placeholder for Phase 2b's gradual recovery)."""
        for index, hero in enumerate(self.player_squad):
            hero.cooldowns = {}
            hero.position = Position(1, 2 + index * 3)
            if config.FULL_HEAL_BETWEEN_BATTLES:
                hero.current_hp = hero.max_hp
        grid = Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)
        enemy_squad = progression.generate_enemy_squad(self.rng)
        self.current_battle = Battle(
            grid=grid, player_squad=self.player_squad, enemy_squad=enemy_squad, rng=self.rng
        )
