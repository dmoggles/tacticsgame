from __future__ import annotations

import random

from . import config
from .engine.progression import create_starting_hero
from .engine.session import Session
from .models.grid import Position
from .models.hero import Hero
from .visualizer import renderer


def build_player_roster(rng: random.Random) -> list[Hero]:
    """A roster-size-agnostic (per config.ROSTER_SIZE) fresh player roster."""
    return [
        create_starting_hero(
            name=f"Hero {i + 1}",
            position=Position(x=1, y=2 + i * 3),
            is_player_controlled=True,
            rng=rng,
        )
        for i in range(config.ROSTER_SIZE)
    ]


def main() -> None:
    rng = random.Random()
    session = Session(roster=build_player_roster(rng), rng=rng)
    # TODO(phase2b step4): field via the between-battle squad-selection
    # screen instead of always fielding the first FIELDED_SQUAD_SIZE roster
    # members — that screen doesn't exist yet.
    session.begin_battle(session.roster[: config.FIELDED_SQUAD_SIZE])
    battle = session.current_battle
    assert battle is not None
    renderer.run(battle, session=session)


if __name__ == "__main__":
    main()
