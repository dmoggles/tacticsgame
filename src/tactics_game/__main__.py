from __future__ import annotations

import random

from . import config
from .engine.progression import create_starting_hero
from .engine.session import Session
from .models.grid import Position
from .models.hero import Hero
from .visualizer import renderer


def build_player_squad(rng: random.Random) -> list[Hero]:
    """A squad-size-agnostic (per config.SQUAD_SIZE) fresh player squad."""
    return [
        create_starting_hero(
            name=f"Hero {i + 1}",
            position=Position(x=1, y=2 + i * 3),
            is_player_controlled=True,
            rng=rng,
        )
        for i in range(config.SQUAD_SIZE)
    ]


def main() -> None:
    rng = random.Random()
    session = Session(player_squad=build_player_squad(rng), rng=rng)
    battle = session.current_battle
    assert battle is not None
    renderer.run(battle, session=session)


if __name__ == "__main__":
    main()
