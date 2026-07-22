from __future__ import annotations

import random

from tactics_game import config
from tactics_game.engine import progression
from tactics_game.engine.battle import Battle
from tactics_game.engine.progression import create_starting_hero
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Grid, Position
from tactics_game.models.hero import Hero


def _build_battle(seed: int) -> Battle:
    rng = random.Random(seed)
    grid = Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)
    player_squad = [
        create_starting_hero(f"Hero {i + 1}", Position(1, 2 + i * 3), True, rng)
        for i in range(config.SQUAD_SIZE)
    ]
    enemy_squad = [
        create_starting_hero(
            f"Enemy {i + 1}", Position(config.GRID_WIDTH - 2, 2 + i * 3), False, rng
        )
        for i in range(config.SQUAD_SIZE)
    ]
    return Battle(grid=grid, player_squad=player_squad, enemy_squad=enemy_squad, rng=rng)


def test_battle_runs_headlessly_to_a_win_or_loss() -> None:
    for seed in range(10):
        battle = _build_battle(seed)
        battle.run_to_completion()
        assert battle.is_over
        assert battle.winner in ("player", "enemy")


def test_step_processes_exactly_one_turn() -> None:
    battle = _build_battle(seed=3)
    assert battle.turn_index == 0
    assert battle.last_log is None
    battle.step()
    assert battle.last_log is not None
    assert battle.turn_index == 1


def test_heroes_gain_track1_xp_and_can_level_up_during_battle() -> None:
    # AI decision-making affects how quickly a given seed's battle resolves,
    # so pin the property (level-ups happen via the battle loop) across a
    # spread of seeds rather than one exact seed's outcome.
    leveled_up = False
    for seed in range(10):
        battle = _build_battle(seed=seed)
        battle.run_to_completion()
        for hero in battle.all_heroes:
            assert hero.xp >= 0
            assert hero.level >= 1
        leveled_up = leveled_up or any(hero.level > 1 for hero in battle.all_heroes)
    assert leveled_up


def test_ability_usage_accrues_track2_class_xp() -> None:
    battle = _build_battle(seed=7)
    battle.run_to_completion()
    total_class_xp = sum(xp for hero in battle.all_heroes for xp in hero.class_xp.values())
    assert total_class_xp > 0


def test_heroes_never_leave_the_grid() -> None:
    battle = _build_battle(seed=99)
    grid = battle.grid
    while not battle.is_over:
        battle.step()
        for hero in battle.all_heroes:
            assert grid.in_bounds(hero.position)


def test_basic_mend_goes_on_cooldown_after_use_and_cycles_back() -> None:
    # A lone, badly-hurt healer with a distant, weak enemy: self-heal is
    # always in range regardless of movement, so this isolates the cooldown
    # tick/gate cycle from AI targeting/positioning concerns.
    healer = Hero(
        name="Healer",
        attributes=Attributes(might=1, focus=1, resolve=1, agility=1),
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=100,
        current_hp=10,
        position=Position(0, 0),
        is_player_controlled=True,
    )
    dummy = Hero(
        name="Dummy",
        attributes=Attributes(might=1, focus=1, resolve=1, agility=1),
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=1000,
        current_hp=1000,
        position=Position(config.GRID_WIDTH - 1, config.GRID_HEIGHT - 1),
        is_player_controlled=False,
    )
    grid = Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)
    battle = Battle(grid=grid, player_squad=[healer], enemy_squad=[dummy])

    cooldowns_after_healer_turns = []
    mend_used = []
    for _ in range(4):
        battle.step()  # Healer's turn
        cooldowns_after_healer_turns.append(healer.cooldowns.get("Basic Mend", 0))
        mend_used.append(
            battle.last_log is not None and "mends" in battle.last_log.description
        )
        if not battle.is_over:
            battle.step()  # Dummy's turn

    assert healer.is_alive
    assert mend_used == [True, False, False, True]
    assert cooldowns_after_healer_turns == [
        config.BASIC_MEND_COOLDOWN,
        config.BASIC_MEND_COOLDOWN - 1,
        config.BASIC_MEND_COOLDOWN - 2,
        config.BASIC_MEND_COOLDOWN,
    ]
