"""Developer tooling: AI-vs-AI behavioural baseline capture.

Not part of the game itself and not imported by models/engine/visualizer.
Kept inside the installed package purely so the capture logic and its
regression test (tests/test_ai_vs_ai_baseline.py) share one import path and
one definition of "build a seeded battle" instead of drifting apart.

See docs/03_phase2a_definition.md, build-order step 0: this fixture must be
captured on `main` before the legal-action query API refactor lands, so the
refactor can be checked against pre-refactor AI behaviour rather than a
tautological post-refactor snapshot.

Deliberately headless: builds battles straight from engine/models, with no
import of `__main__` or `visualizer` (which would pull in pygame).
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from . import config
from .engine.battle import Battle
from .engine.progression import create_starting_hero
from .models.grid import Grid, Position
from .models.hero import Hero

SEEDS: range = range(config.AI_BASELINE_SEED_COUNT)

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "ai_vs_ai_baseline.json"
)


def build_seeded_battle(seed: int) -> Battle:
    """Deterministic 2v2 (per config.FIELDED_SQUAD_SIZE) battle, given a seed."""
    rng = random.Random(seed)
    grid = Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)
    player_squad = [
        create_starting_hero(f"Hero {i + 1}", Position(1, 2 + i * 3), True, rng)
        for i in range(config.FIELDED_SQUAD_SIZE)
    ]
    enemy_squad = [
        create_starting_hero(
            f"Enemy {i + 1}", Position(config.GRID_WIDTH - 2, 2 + i * 3), False, rng
        )
        for i in range(config.FIELDED_SQUAD_SIZE)
    ]
    return Battle(grid=grid, player_squad=player_squad, enemy_squad=enemy_squad, rng=rng)


def run_seeded_battle(seed: int) -> tuple[Battle, int]:
    """Run a seeded battle to completion, also returning the step count."""
    battle = build_seeded_battle(seed)
    steps_taken = 0
    while not battle.is_over and steps_taken < config.MAX_BATTLE_STEPS:
        battle.step()
        steps_taken += 1
    return battle, steps_taken


def _serialize_hero(hero: Hero) -> dict[str, Any]:
    return {
        "name": hero.name,
        "is_player_controlled": hero.is_player_controlled,
        "is_alive": hero.is_alive,
        "level": hero.level,
        "xp": hero.xp,
        "current_hp": hero.current_hp,
        "max_hp": hero.max_hp,
        "position": {"x": hero.position.x, "y": hero.position.y},
        "class_xp": {track.value: amount for track, amount in hero.class_xp.items()},
    }


def _serialize_battle(seed: int, battle: Battle, steps_taken: int) -> dict[str, Any]:
    return {
        "seed": seed,
        "winner": battle.winner,
        "rounds": battle.round_number,
        "steps": steps_taken,
        "heroes": [_serialize_hero(hero) for hero in battle.all_heroes],
    }


def capture_baseline() -> list[dict[str, Any]]:
    return [_serialize_battle(seed, *run_seeded_battle(seed)) for seed in SEEDS]


def write_baseline_fixture() -> None:
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(capture_baseline(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_baseline_fixture()
    print(f"Wrote AI-vs-AI baseline fixture: {FIXTURE_PATH}")
