from __future__ import annotations

import random

import pytest

from tactics_game import config
from tactics_game.engine import ability_library, ai, progression
from tactics_game.engine.battle import Battle
from tactics_game.engine.progression import create_starting_hero
from tactics_game.engine.turn import TurnDecision
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


def test_track1_xp_does_not_accrue_mid_battle() -> None:
    # Supersedes the old per-action accrual model (docs/03_phase2a_definition.md
    # section 5): XP is now a per-battle pool awarded only at battle end, so
    # no hero's xp/level should move at all while the battle is in progress.
    battle = _build_battle(seed=5)
    for _ in range(6):
        if battle.is_over:
            break
        battle.step()
        for hero in battle.all_heroes:
            assert hero.xp == 0
            assert hero.level == 1


def test_track1_xp_is_awarded_to_the_player_squad_on_victory() -> None:
    # AI decision-making affects how quickly/whether a given seed's battle
    # resolves in the player's favor, so check the property across a spread
    # of seeds rather than pinning to one seed's exact outcome.
    any_player_victory = False
    for seed in range(10):
        battle = _build_battle(seed=seed)
        battle.run_to_completion()
        if battle.winner == "player":
            any_player_victory = True
            assert all(hero.xp > 0 for hero in battle.player_squad)
        else:
            # No reward for losing: player squad gets no XP pool on defeat.
            assert all(hero.xp == 0 for hero in battle.player_squad)
    assert any_player_victory


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

    mend_cooldown = next(
        a for a in ability_library.load_abilities() if a.name == "Basic Mend"
    ).cooldown

    assert healer.is_alive
    assert mend_used == [True, False, False, True]
    assert cooldowns_after_healer_turns == [
        mend_cooldown,
        mend_cooldown - 1,
        mend_cooldown - 2,
        mend_cooldown,
    ]


def test_downed_hero_is_not_removed_and_revives_at_battle_end() -> None:
    # A hero already at 0 HP shouldn't end the battle by itself (only "all
    # fielded heroes downed" does), shouldn't be removed from the squad, and
    # should come back at DOWNED_REVIVE_HP once the battle concludes.
    downed_hero = Hero(
        name="Downed",
        attributes=Attributes(might=1, focus=1, resolve=1, agility=1),
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=20,
        current_hp=0,
        position=Position(0, 0),
        is_player_controlled=True,
    )
    striker = Hero(
        name="Striker",
        attributes=Attributes(might=20, focus=1, resolve=1, agility=1),
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=40,
        current_hp=40,
        position=Position(1, 0),
        is_player_controlled=True,
    )
    enemy = Hero(
        name="Enemy",
        attributes=Attributes(might=1, focus=1, resolve=1, agility=1),
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=5,
        current_hp=5,
        position=Position(2, 0),
        is_player_controlled=False,
    )
    grid = Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)
    battle = Battle(grid=grid, player_squad=[downed_hero, striker], enemy_squad=[enemy])

    # Downed alone doesn't end the battle: the striker is still standing.
    assert not battle.is_over

    battle.run_to_completion()

    assert battle.winner == "player"
    assert downed_hero in battle.player_squad
    assert downed_hero.is_alive
    assert downed_hero.current_hp == config.DOWNED_REVIVE_HP
    # Downed heroes still count as fielded and get a full XP share.
    assert downed_hero.xp == striker.xp
    assert downed_hero.xp > 0


def test_current_actor_matches_what_step_would_consume_next() -> None:
    battle = _build_battle(seed=11)
    for _ in range(10):
        if battle.is_over:
            break
        expected_actor = battle.current_actor
        assert expected_actor is not None
        battle.step()
        assert battle.last_log is not None
        assert battle.last_log.actor_name == expected_actor.name


def test_take_turn_applies_the_same_effects_step_would() -> None:
    battle = _build_battle(seed=12)
    actor = battle.current_actor
    assert actor is not None
    allies = battle.player_squad if actor.is_player_controlled else battle.enemy_squad
    enemies = battle.enemy_squad if actor.is_player_controlled else battle.player_squad
    decision = ai.decide_turn(actor, allies, enemies, battle.grid)

    battle.take_turn(actor, decision)

    assert battle.last_log is not None
    assert battle.last_log.actor_name == actor.name
    assert battle.turn_index == 1


def test_take_turn_raises_if_it_is_not_the_given_actors_turn() -> None:
    battle = _build_battle(seed=13)
    actor = battle.current_actor
    assert actor is not None
    not_yet_up = next(hero for hero in battle.all_heroes if hero is not actor)

    with pytest.raises(ValueError):
        battle.take_turn(not_yet_up, TurnDecision(destination=None, ability_decision=None))


def test_cooldowns_are_ticked_before_the_actors_next_turn_becomes_current() -> None:
    # Mirrors test_basic_mend_goes_on_cooldown_after_use_and_cycles_back's
    # setup, but checks the state *before* the healer's second turn is
    # taken — cooldowns must already be ticked by the time an actor
    # becomes current, since a human (via the UI) decides across many
    # frames using that state, not in one atomic step like the AI does.
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

    battle.step()  # Healer casts Basic Mend, goes on cooldown
    mend_cooldown = next(
        a for a in ability_library.load_abilities() if a.name == "Basic Mend"
    ).cooldown
    battle.step()  # Dummy's turn — primes Healer's cooldowns for next turn

    assert battle.current_actor is healer
    assert healer.cooldowns["Basic Mend"] == mend_cooldown - 1
