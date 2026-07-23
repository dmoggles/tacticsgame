from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from .. import config
from ..models.grid import Grid, Position
from ..models.hero import Hero
from . import hero_delta, progression, roster
from .battle import Battle
from .hero_delta import HeroDelta, HeroSnapshot

# A session (working term — see docs/03_phase2a_definition.md section 6) is
# a sequence of battles fought by one persistent player roster. Enemy squads
# are regenerated per battle (progression.generate_enemy_squad); the roster's
# Hero objects are reused as-is across every Battle in the session, which is
# how attributes/level/xp/class_xp persist — no separate save/load mechanism
# exists or is needed (a session lives entirely in memory).
#
# Phase 2b (docs/04_phase2b_definition.md section 1-2) makes the roster
# larger than what's fielded per battle, and fielding a specific subset is a
# player choice made before every battle — so, unlike Phase 2a, Session can
# no longer auto-start the next battle on construction/advance(). See
# docs/adr/0006-roster-and-squad-selection.md, which supersedes ADR 0004's
# auto-start flow.


def _field_first_available(roster_: list[Hero]) -> list[Hero]:
    """Default squad-selection strategy for headless use (run_to_completion):
    field heroes prioritizing those with fewer fielded battles (roster.select_balanced_squad)
    so all roster heroes develop evenly during auto-play."""
    return roster.select_balanced_squad(roster_)
@dataclass
class Session:
    roster: list[Hero]
    rng: random.Random = field(default_factory=random.Random)
    battles_total: int = config.SESSION_BATTLE_COUNT
    battles_won: int = 0
    current_battle: Battle | None = field(default=None, init=False)
    fielded: list[Hero] = field(default_factory=list, init=False)
    benched: list[Hero] = field(default_factory=list, init=False)
    is_over: bool = field(default=False, init=False)
    result: str | None = field(default=None, init=False)  # "won" | "lost"
    _pre_battle_snapshots: list[HeroSnapshot] = field(default_factory=list, init=False)

    def begin_battle(self, fielded: list[Hero]) -> None:
        """Choose which roster heroes fight the next battle
        (docs/04_phase2b_definition.md section 2). Must be called before the
        first battle and again after every advance() that doesn't end the
        session — Session never fields anyone on its own.

        Snapshots the whole roster first, for deltas()'s to compare against
        once this battle resolves — see deltas()'s docstring on why this is
        the only "before" state Session ever keeps.
        """
        if self.is_over:
            raise ValueError("session is already over")
        if self.current_battle is not None and not self.current_battle.is_over:
            raise ValueError("current battle is still in progress")
        self.benched = roster.select_fielded_squad(self.roster, fielded)
        self.fielded = fielded
        self._pre_battle_snapshots = [hero_delta.snapshot_hero(hero) for hero in self.roster]
        for hero in self.fielded:
            hero.battles_fielded += 1
        for hero in self.benched:
            hero.battles_benched += 1
        self._prepare_battle()

    def deltas(self) -> list[HeroDelta]:
        """Per-roster-hero change (level/attributes/class XP) since the
        most recent begin_battle() call, in roster order.

        Only ever compares against the single most recent snapshot —
        docs/04_phase2b_definition.md section 6's hard requirement is "no
        level-up history," and begin_battle() overwrites the snapshot every
        time rather than appending to a log, so there is no history to
        expose even in principle. Empty before the first begin_battle().
        """
        if len(self._pre_battle_snapshots) != len(self.roster):
            return []
        return [
            hero_delta.compute_delta(snapshot, hero)
            for snapshot, hero in zip(self._pre_battle_snapshots, self.roster)
        ]

    def _resolve_all_pending_level_ups(self) -> None:
        """Resolve any pending manual attribute points remaining across the roster
        when a session ends, so points earned in the final battle are never silently lost."""
        for hero in self.roster:
            while hero.pending_level_ups > 0:
                progression.resolve_manual_allocation(hero, attribute=None, rng=self.rng)

    def advance(self) -> None:
        """Call once `self.current_battle.is_over`. Scores the finished
        battle (including bench-bonus XP, which only Session can award —
        see progression.award_bench_bonus_xp) and either ends the session or
        clears `current_battle`, awaiting the next begin_battle() call.

        A no-op once `is_over` — ending a session doesn't clear
        `current_battle` to something new to advance into, so a caller that
        doesn't stop calling this once the session is over would otherwise
        keep re-scoring the same finished battle forever (battles_won
        incrementing without bound).
        """
        if self.is_over:
            return
        battle = self.current_battle
        assert battle is not None and battle.is_over
        if battle.winner == "player" and self.benched:
            progression.award_bench_bonus_xp(self.benched, battle.enemy_squad, self.rng)
        if battle.winner == "enemy":
            self.is_over = True
            self.result = "lost"
            self.current_battle = None
            self._resolve_all_pending_level_ups()
            return
        self.battles_won += 1
        if self.battles_won >= self.battles_total:
            self.is_over = True
            self.result = "won"
            self.current_battle = None
            self._resolve_all_pending_level_ups()
            return
        self._apply_recovery()
        self.current_battle = None

    def run_to_completion(self, select_fielded: Callable[[list[Hero]], list[Hero]] | None = None) -> None:
        """Headless convenience, mirroring Battle.run_to_completion. Chooses
        a squad before every battle via `select_fielded` (roster -> fielded
        heroes), defaulting to `_field_first_available`."""
        select = select_fielded or _field_first_available
        while not self.is_over:
            if self.current_battle is None:
                self.begin_battle(select(self.roster))
            assert self.current_battle is not None
            self.current_battle.run_to_completion()
            self.advance()

    def _apply_recovery(self) -> None:
        """Gradual recovery (docs/04_phase2b_definition.md section 3): every
        roster hero heals a fraction of max_hp based on whether they were
        fielded or benched in the battle that just ended — benched heals
        substantially faster. Runs once per "between battles" gap, so it's
        called only when another battle is actually coming (not on the
        battle that ends the session — there's nothing to recover for)."""
        for hero in self.fielded:
            progression.recover_hp(hero, config.FIELDED_RECOVERY_FRACTION)
        for hero in self.benched:
            progression.recover_hp(hero, config.BENCHED_RECOVERY_FRACTION)

    def _prepare_battle(self) -> None:
        """Cooldowns and positions reset for whoever's fielded this battle.
        HP is untouched here — gradual recovery already ran in advance()
        before this was called; a fresh roster's heroes start at max_hp by
        construction (create_starting_hero). Benched heroes are untouched
        entirely — they never enter a Battle, so nothing about them needs
        resetting."""
        for index, hero in enumerate(self.fielded):
            hero.cooldowns = {}
            hero.position = Position(1, 2 + index * 3)
        grid = Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)
        enemy_squad = progression.generate_enemy_squad(self.rng, battle_index=self.battles_won)
        self.current_battle = Battle(
            grid=grid, player_squad=self.fielded, enemy_squad=enemy_squad, rng=self.rng
        )
