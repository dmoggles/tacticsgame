from __future__ import annotations

import random

from . import config
from .engine.battle import Battle
from .engine.progression import create_starting_hero
from .models.grid import Grid, Position
from .visualizer import renderer


def build_demo_battle(seed: int | None = None) -> Battle:
    """A squad-size-agnostic 2v2 (per config.SQUAD_SIZE) demo battle."""
    rng = random.Random(seed)
    grid = Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)

    player_squad = [
        create_starting_hero(
            name=f"Hero {i + 1}",
            position=Position(x=1, y=2 + i * 3),
            is_player_controlled=True,
            rng=rng,
        )
        for i in range(config.SQUAD_SIZE)
    ]
    enemy_squad = [
        create_starting_hero(
            name=f"Enemy {i + 1}",
            position=Position(x=config.GRID_WIDTH - 2, y=2 + i * 3),
            is_player_controlled=False,
            rng=rng,
        )
        for i in range(config.SQUAD_SIZE)
    ]
    return Battle(grid=grid, player_squad=player_squad, enemy_squad=enemy_squad, rng=rng)


def main() -> None:
    battle = build_demo_battle()
    renderer.run(battle)


if __name__ == "__main__":
    main()
