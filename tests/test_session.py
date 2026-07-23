from __future__ import annotations

import random

from tactics_game import config
from tactics_game.engine import progression
from tactics_game.engine.session import Session
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Position
from tactics_game.models.hero import Hero

_DEFAULT_ATTRIBUTES = Attributes(might=1, focus=1, resolve=1, agility=1)


def _make_hero(
    name: str,
    attributes: Attributes = _DEFAULT_ATTRIBUTES,
    current_hp: int | None = None,
) -> Hero:
    max_hp = progression.compute_max_hp(attributes)
    return Hero(
        name=name,
        attributes=attributes,
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=max_hp,
        current_hp=max_hp if current_hp is None else current_hp,
        position=Position(0, 0),
        is_player_controlled=True,
    )


def _default_squad() -> list[Hero]:
    return [_make_hero(f"Hero {i + 1}") for i in range(config.SQUAD_SIZE)]


def test_player_squad_hero_identity_and_progression_persist_across_battles() -> None:
    squad = _default_squad()
    original_heroes = list(squad)
    session = Session(player_squad=squad, rng=random.Random(1), battles_total=2)

    first_battle = session.current_battle
    assert first_battle is not None
    first_battle.run_to_completion()
    session.advance()

    # Same Hero objects, not copies/rebuilds — this is the entire
    # persistence mechanism.
    assert session.player_squad == original_heroes
    for hero, original in zip(session.player_squad, original_heroes):
        assert hero is original

    if not session.is_over:
        # Whatever the first battle awarded is still on the hero going
        # into the second battle's squad.
        assert session.current_battle is not None
        assert session.current_battle.player_squad == original_heroes


def test_cooldowns_and_positions_reset_between_battles() -> None:
    squad = _default_squad()
    squad[0].cooldowns["Basic Mend"] = 3
    squad[0].position = Position(6, 6)
    session = Session(player_squad=squad, rng=random.Random(2), battles_total=2)
    battle = session.current_battle
    assert battle is not None
    battle.winner = "player"
    battle.is_over = True

    session.advance()

    assert squad[0].cooldowns == {}
    assert squad[0].position == Position(1, 2)
    assert squad[1].position == Position(1, 5)


def test_hp_fully_heals_between_battles() -> None:
    squad = _default_squad()
    squad[0].current_hp = 1
    session = Session(player_squad=squad, rng=random.Random(3), battles_total=2)
    battle = session.current_battle
    assert battle is not None
    battle.winner = "player"
    battle.is_over = True

    session.advance()

    assert squad[0].current_hp == squad[0].max_hp


def test_enemy_squad_is_regenerated_each_battle() -> None:
    squad = _default_squad()
    session = Session(player_squad=squad, rng=random.Random(4), battles_total=2)
    first_battle = session.current_battle
    assert first_battle is not None
    first_enemy_squad = first_battle.enemy_squad
    first_battle.winner = "player"
    first_battle.is_over = True

    session.advance()

    second_battle = session.current_battle
    assert second_battle is not None
    second_enemy_squad = second_battle.enemy_squad
    assert len(first_enemy_squad) == len(second_enemy_squad)
    for old, new in zip(first_enemy_squad, second_enemy_squad):
        assert old is not new


def test_session_ends_in_win_once_all_battles_are_won() -> None:
    overwhelming = Attributes(might=100, focus=100, resolve=100, agility=100)
    squad = [_make_hero(f"Hero {i + 1}", attributes=overwhelming) for i in range(config.SQUAD_SIZE)]
    session = Session(player_squad=squad, rng=random.Random(5), battles_total=3)

    session.run_to_completion()

    assert session.is_over
    assert session.result == "won"
    assert session.battles_won == session.battles_total


def test_session_ends_in_loss_when_a_battle_is_lost() -> None:
    for seed in range(3):
        fragile = Attributes(might=1, focus=1, resolve=1, agility=1)
        squad = [
            _make_hero(f"Hero {i + 1}", attributes=fragile, current_hp=1)
            for i in range(config.SQUAD_SIZE)
        ]
        session = Session(player_squad=squad, rng=random.Random(seed), battles_total=5)

        session.run_to_completion()

        assert session.is_over
        assert session.result == "lost"
        assert session.battles_won < session.battles_total


def test_session_runs_end_to_end_to_a_win_or_loss() -> None:
    for seed in range(10):
        rng = random.Random(seed)
        squad = [
            progression.create_starting_hero(
                name=f"Hero {i + 1}", position=Position(1, 2 + i * 3), is_player_controlled=True, rng=rng
            )
            for i in range(config.SQUAD_SIZE)
        ]
        session = Session(player_squad=squad, rng=rng, battles_total=config.SESSION_BATTLE_COUNT)

        session.run_to_completion()

        assert session.is_over
        assert session.result in ("won", "lost")
