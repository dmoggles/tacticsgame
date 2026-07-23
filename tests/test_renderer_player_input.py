from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import random

import pygame

from tactics_game import config
from tactics_game.engine import progression
from tactics_game.engine.battle import Battle
from tactics_game.engine.session import Session
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Grid, Position
from tactics_game.models.hero import Hero
from tactics_game.visualizer import renderer

# Mirrors the Phase 1 SDL_VIDEODRIVER=dummy smoke-test precedent
# (docs/progress_update.md) — the one layer PlayerTurnController's unit
# tests can't cover, since it's the wiring between real pygame events and
# the controller/Battle calls, not the interaction logic itself.


def _tile_center(position: Position) -> tuple[int, int]:
    return (
        position.x * config.TILE_SIZE_PX + config.TILE_SIZE_PX // 2,
        position.y * config.TILE_SIZE_PX + config.TILE_SIZE_PX // 2,
    )


def _build_1v1_battle() -> tuple[Battle, Hero, Hero]:
    actor = Hero(
        name="Actor",
        attributes=Attributes(might=10, focus=1, resolve=1, agility=1),
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=30,
        current_hp=30,
        position=Position(0, 0),
        is_player_controlled=True,
    )
    enemy = Hero(
        name="Enemy",
        attributes=Attributes(might=1, focus=1, resolve=1, agility=1),
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=100,
        current_hp=100,
        position=Position(3, 0),
        is_player_controlled=False,
    )
    grid = Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)
    return Battle(grid=grid, player_squad=[actor], enemy_squad=[enemy]), actor, enemy


def test_a_full_player_turn_via_scripted_pygame_events() -> None:
    battle, actor, enemy = _build_1v1_battle()
    destination = Position(2, 0)
    strike_index = next(i for i, a in enumerate(actor.abilities) if a.name == "Basic Strike")

    pygame.init()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
    pygame.event.post(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=_tile_center(destination))
    )
    pygame.event.post(
        pygame.event.Event(pygame.KEYDOWN, key=renderer._ABILITY_SLOT_KEYS[strike_index])
    )
    pygame.event.post(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=_tile_center(enemy.position))
    )
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))

    renderer.run(battle, max_frames=3)

    assert actor.position == destination
    assert enemy.current_hp < 100
    assert battle.turn_index == 1
    assert battle.last_log is not None
    assert battle.last_log.actor_name == "Actor"


def test_cancel_and_reselect_does_not_commit_a_turn() -> None:
    battle, actor, enemy = _build_1v1_battle()

    pygame.init()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
    # Move, then cancel the whole turn back to idle (Esc from MOVING).
    pygame.event.post(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=_tile_center(Position(2, 0)))
    )
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))

    renderer.run(battle, max_frames=3)

    assert actor.position == Position(0, 0)
    assert enemy.current_hp == 100
    assert battle.turn_index == 0
    assert battle.last_log is None


def test_skip_move_and_skip_ability_ends_turn_as_a_pass() -> None:
    battle, actor, _enemy = _build_1v1_battle()

    pygame.init()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))  # skip move
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))  # skip ability
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))

    renderer.run(battle, max_frames=3)

    assert actor.position == Position(0, 0)
    assert battle.turn_index == 1
    assert battle.last_log is not None
    assert battle.last_log.description == "Actor passes"


def _make_player_hero(name: str, position: Position) -> Hero:
    return Hero(
        name=name,
        attributes=Attributes(might=1, focus=1, resolve=1, agility=1),
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=20,
        current_hp=20,
        position=position,
        is_player_controlled=True,
    )


def test_pressing_enter_after_a_won_battle_advances_the_session() -> None:
    player_squad = [
        _make_player_hero(f"Hero {i + 1}", Position(1, 2 + i * 3))
        for i in range(config.FIELDED_SQUAD_SIZE)
    ]
    session = Session(roster=player_squad, rng=random.Random(1), battles_total=2)
    session.begin_battle(player_squad)
    first_battle = session.current_battle
    assert first_battle is not None
    # Force the outcome directly rather than playing it out — this test is
    # about the render loop's session-advance wiring, not combat, which is
    # already covered elsewhere (tests/test_session.py, tests/test_battle.py).
    first_battle.winner = "player"
    first_battle.is_over = True

    pygame.init()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    renderer.run(first_battle, max_frames=2, session=session)

    assert session.battles_won == 1
    assert not session.is_over
    second_battle = session.current_battle
    assert second_battle is not None
    assert second_battle is not first_battle

    # The new battle should be immediately playable, same as any other.
    # run() calls pygame.quit() on exit, so re-init before posting more events.
    pygame.init()
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))  # skip move
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))  # skip ability
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    renderer.run(second_battle, max_frames=3, session=session)

    assert second_battle.turn_index == 1
    assert second_battle.last_log is not None
    assert second_battle.last_log.description.endswith("passes")


def test_session_progress_does_not_run_away_after_the_session_ends() -> None:
    # Regression: after the session-ending battle finishes, many frames
    # can elapse before the player presses anything (there's nothing left
    # to advance to). battles_won must not keep climbing past
    # battles_total on every one of those frames.
    player_squad = [
        _make_player_hero(f"Hero {i + 1}", Position(1, 2 + i * 3))
        for i in range(config.FIELDED_SQUAD_SIZE)
    ]
    session = Session(roster=player_squad, rng=random.Random(2), battles_total=1)
    session.begin_battle(player_squad)
    battle = session.current_battle
    assert battle is not None
    battle.winner = "player"
    battle.is_over = True

    pygame.init()
    # No events posted at all — just many frames of the session already over.
    renderer.run(battle, max_frames=30, session=session)

    assert session.is_over
    assert session.result == "won"
    assert session.battles_won == session.battles_total == 1


def test_between_battle_screen_click_and_enter_choose_the_next_squad() -> None:
    # A roster bigger than the fielded squad, so there's an actual choice
    # to click through rather than the screen defaulting straight to READY.
    roster = [
        _make_player_hero(f"Hero {i + 1}", Position(1, 2 + i * 3)) for i in range(3)
    ]
    session = Session(roster=roster, rng=random.Random(30), battles_total=2)
    session.begin_battle(roster[: config.FIELDED_SQUAD_SIZE])  # Hero 1, Hero 2
    battle = session.current_battle
    assert battle is not None
    battle.winner = "player"
    battle.is_over = True

    pygame.init()
    # Deselect Hero 1 (row 0), select Hero 3 (row 2), then confirm — all
    # queued before run() starts, so they drain in the same frame the
    # between-battle screen is created (mirrors how the existing turn
    # tests queue several events ahead of a single run() call).
    row0_center = (100, config.BETWEEN_BATTLE_TOP_PX + 30)
    row2_center = (100, config.BETWEEN_BATTLE_TOP_PX + 2 * config.BETWEEN_BATTLE_ROW_HEIGHT_PX + 30)
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=row0_center, button=1))
    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=row2_center, button=1))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))

    renderer.run(battle, max_frames=2, session=session)

    assert session.current_battle is not None
    assert session.current_battle is not battle
    assert session.fielded == [roster[1], roster[2]]
    assert session.benched == [roster[0]]


def test_between_battle_screen_waits_for_confirmation_before_starting_a_battle() -> None:
    roster = [_make_player_hero(f"Hero {i + 1}", Position(1, 2 + i * 3)) for i in range(3)]
    session = Session(roster=roster, rng=random.Random(31), battles_total=2)
    session.begin_battle(roster[: config.FIELDED_SQUAD_SIZE])
    battle = session.current_battle
    assert battle is not None
    battle.winner = "player"
    battle.is_over = True

    pygame.init()
    # No events posted — nothing should advance past the screen on its own.
    renderer.run(battle, max_frames=5, session=session)

    assert session.current_battle is None
    assert not session.is_over
    assert session.battles_won == 1


def test_between_battle_screen_key_1_resolves_a_pending_manual_allocation() -> None:
    roster = [_make_player_hero(f"Hero {i + 1}", Position(1, 2 + i * 3)) for i in range(2)]
    session = Session(roster=roster, rng=random.Random(32), battles_total=2)
    session.begin_battle(roster)
    battle = session.current_battle
    assert battle is not None
    battle.winner = "player"
    battle.is_over = True
    # Simulate a level-up's manual point still awaiting a choice, same as
    # progression.resolve_manual_allocation's own tests do directly.
    roster[0].pending_level_ups = 1
    might_before = roster[0].attributes.might

    pygame.init()
    # 1 = Might. Roster size equals FIELDED_SQUAD_SIZE here, so the screen
    # defaults straight to READY once allocation clears — the queued ENTER
    # confirms in the same frame, covering both the allocation prompt and
    # the hand-off back to a playable battle in one pass.
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))

    renderer.run(battle, max_frames=2, session=session)

    assert roster[0].pending_level_ups == 0
    assert roster[0].attributes.might == might_before + config.MANUAL_ALLOCATION_POINTS_PER_LEVEL_UP
    assert session.current_battle is not None
    assert session.current_battle is not battle
