from __future__ import annotations

import pytest

from tactics_game import config
from tactics_game.engine import progression
from tactics_game.engine.turn import TurnDecision
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Grid, Position
from tactics_game.models.hero import Hero
from tactics_game.visualizer.player_input import InputPhase, PlayerTurnController

_DEFAULT_ATTRIBUTES = Attributes(might=1, focus=1, resolve=1, agility=1)


def _make_hero(
    name: str,
    position: Position,
    is_player_controlled: bool = True,
    current_hp: int = 20,
    max_hp: int = 20,
) -> Hero:
    return Hero(
        name=name,
        attributes=_DEFAULT_ATTRIBUTES,
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=max_hp,
        current_hp=current_hp,
        position=position,
        is_player_controlled=is_player_controlled,
    )


def _grid() -> Grid:
    return Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)


def _ability(name: str, hero: Hero):
    return next(a for a in hero.abilities if a.name == name)


def _controller(actor: Hero, allies: list[Hero], enemies: list[Hero]) -> PlayerTurnController:
    return PlayerTurnController(actor=actor, allies=allies, enemies=enemies, grid=_grid())


def test_starts_idle() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])
    assert controller.phase == InputPhase.IDLE


def test_select_active_hero_moves_to_moving() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])

    assert controller.select_active_hero() is True
    assert controller.phase == InputPhase.MOVING


def test_select_active_hero_is_noop_outside_idle() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])
    controller.select_active_hero()

    assert controller.select_active_hero() is False
    assert controller.phase == InputPhase.MOVING


def test_choose_destination_rejects_unreachable_tile() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])
    controller.select_active_hero()
    far_away = Position(config.GRID_WIDTH - 1, config.GRID_HEIGHT - 1)

    assert far_away not in controller.reachable_tiles
    assert controller.choose_destination(far_away) is False
    assert controller.phase == InputPhase.MOVING
    assert controller.pending_destination is None


def test_choose_destination_accepts_reachable_tile() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])
    controller.select_active_hero()
    destination = Position(1, 0)
    assert destination in controller.reachable_tiles

    assert controller.choose_destination(destination) is True
    assert controller.pending_destination == destination
    assert controller.phase == InputPhase.ACTING


def test_skip_move_advances_without_a_destination() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])
    controller.select_active_hero()

    assert controller.skip_move() is True
    assert controller.pending_destination is None
    assert controller.phase == InputPhase.ACTING


def test_choose_ability_rejects_ability_on_cooldown() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    actor.cooldowns["Basic Mend"] = 2
    mend = _ability("Basic Mend", actor)
    controller = _controller(actor, [actor], [])
    controller.select_active_hero()
    controller.skip_move()

    assert mend not in controller.usable_abilities
    assert controller.choose_ability(mend) is False
    assert controller.phase == InputPhase.ACTING


def test_choose_ability_accepts_usable_ability() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    strike = _ability("Basic Strike", actor)
    controller = _controller(actor, [actor], [])
    controller.select_active_hero()
    controller.skip_move()

    assert controller.choose_ability(strike) is True
    assert controller.pending_ability is strike


def test_target_preview_is_cached_and_only_available_while_targeting() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    enemy = _make_hero("Enemy", Position(1, 0), is_player_controlled=False)
    controller = _controller(actor, [actor], [enemy])
    strike = _ability("Basic Strike", actor)

    assert controller.outcome_preview_for(enemy) is None
    controller.select_active_hero()
    controller.skip_move()
    controller.choose_ability(strike)

    first = controller.outcome_preview_for(enemy)
    second = controller.outcome_preview_for(enemy)
    assert first is not None
    assert second is first
    assert 0 < first.success_probability <= 1
    assert controller.phase == InputPhase.TARGETING


def test_skip_ability_advances_to_ready_with_no_ability_decision() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])
    controller.select_active_hero()
    controller.skip_move()

    assert controller.skip_ability() is True
    assert controller.pending_ability_decision is None
    assert controller.phase == InputPhase.READY


def test_choose_target_rejects_position_not_a_valid_target() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    enemy = _make_hero("Enemy", Position(5, 5), is_player_controlled=False)
    strike = _ability("Basic Strike", actor)  # range 1
    controller = _controller(actor, [actor], [enemy])
    controller.select_active_hero()
    controller.skip_move()
    controller.choose_ability(strike)

    assert controller.choose_target(enemy.position) is False
    assert controller.phase == InputPhase.TARGETING
    assert controller.pending_ability_decision is None


def test_choose_target_accepts_valid_target() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    enemy = _make_hero("Enemy", Position(1, 0), is_player_controlled=False)
    strike = _ability("Basic Strike", actor)  # range 1
    controller = _controller(actor, [actor], [enemy])
    controller.select_active_hero()
    controller.skip_move()
    controller.choose_ability(strike)

    assert controller.choose_target(enemy.position) is True
    assert controller.pending_ability_decision is not None
    assert controller.pending_ability_decision.ability is strike
    assert controller.pending_ability_decision.target is enemy
    assert controller.phase == InputPhase.READY


def test_valid_targets_use_the_pending_destination_not_actual_position() -> None:
    # Basic Strike has range 1 — out of range from (0,0) (distance 4), in
    # range from a hypothetical post-move position of (3,0) (distance 1),
    # and (3,0) is itself within MOVEMENT_RANGE=3 of the actor's start.
    actor = _make_hero("Actor", Position(0, 0))
    enemy = _make_hero("Enemy", Position(4, 0), is_player_controlled=False)
    strike = _ability("Basic Strike", actor)
    controller = _controller(actor, [actor], [enemy])
    controller.select_active_hero()
    destination = Position(config.MOVEMENT_RANGE, 0)
    assert destination in controller.reachable_tiles
    controller.choose_destination(destination)
    controller.choose_ability(strike)

    assert enemy in controller.valid_targets


def test_cancel_from_targeting_returns_to_acting() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    enemy = _make_hero("Enemy", Position(1, 0), is_player_controlled=False)
    strike = _ability("Basic Strike", actor)
    controller = _controller(actor, [actor], [enemy])
    controller.select_active_hero()
    controller.skip_move()
    controller.choose_ability(strike)

    assert controller.cancel() is True
    assert controller.phase == InputPhase.ACTING
    assert controller.pending_ability is None


def test_cancel_from_acting_or_ready_returns_to_moving_and_clears_everything() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])
    controller.select_active_hero()
    controller.choose_destination(Position(1, 0))

    assert controller.cancel() is True
    assert controller.phase == InputPhase.MOVING
    assert controller.pending_destination is None
    assert controller.pending_ability is None


def test_cancel_from_moving_returns_to_idle() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])
    controller.select_active_hero()

    assert controller.cancel() is True
    assert controller.phase == InputPhase.IDLE


def test_cancel_from_idle_is_noop() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])

    assert controller.cancel() is False
    assert controller.phase == InputPhase.IDLE


def test_build_decision_before_ready_raises() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])

    with pytest.raises(AssertionError):
        controller.build_decision()


def test_build_decision_full_pass() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    controller = _controller(actor, [actor], [])
    controller.select_active_hero()
    controller.skip_move()
    controller.skip_ability()

    assert controller.is_ready
    assert controller.build_decision() == TurnDecision(destination=None, ability_decision=None)


def test_build_decision_with_move_and_ability() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    enemy = _make_hero("Enemy", Position(1, 0), is_player_controlled=False)
    strike = _ability("Basic Strike", actor)
    controller = _controller(actor, [actor], [enemy])
    controller.select_active_hero()
    controller.skip_move()
    controller.choose_ability(strike)
    controller.choose_target(enemy.position)

    decision = controller.build_decision()
    assert decision.destination is None
    assert decision.ability_decision is not None
    assert decision.ability_decision.ability is strike
    assert decision.ability_decision.target is enemy
