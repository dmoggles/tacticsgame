from __future__ import annotations

import random

from tactics_game import config
from tactics_game.engine import progression
from tactics_game.engine.session import Session
from tactics_game.models.attributes import AffinityVector, AttributeName, Attributes
from tactics_game.models.grid import Position
from tactics_game.models.hero import Hero
from tactics_game.visualizer.between_battle_screen import BetweenBattleController, BetweenBattlePhase

_ATTRIBUTES = Attributes(might=1, focus=1, resolve=1, agility=1)


def _make_hero(name: str) -> Hero:
    max_hp = progression.compute_max_hp(_ATTRIBUTES)
    return Hero(
        name=name,
        attributes=_ATTRIBUTES,
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=max_hp,
        current_hp=max_hp,
        position=Position(0, 0),
        is_player_controlled=True,
    )


def _make_roster(size: int) -> list[Hero]:
    return [_make_hero(f"Hero {i + 1}") for i in range(size)]


def test_starts_in_selecting_when_nobody_has_a_pending_level_up() -> None:
    session = Session(roster=_make_roster(config.ROSTER_SIZE), rng=random.Random(0))

    controller = BetweenBattleController(session=session)

    assert controller.phase == BetweenBattlePhase.SELECTING
    assert controller.selected == []


def test_starts_in_allocating_when_a_hero_has_a_pending_level_up() -> None:
    roster = _make_roster(config.ROSTER_SIZE)
    roster[0].pending_level_ups = 1
    session = Session(roster=roster, rng=random.Random(1))

    controller = BetweenBattleController(session=session)

    assert controller.phase == BetweenBattlePhase.ALLOCATING
    assert controller.pending_hero is roster[0]


def test_choose_manual_attribute_applies_the_point_and_advances_to_selecting() -> None:
    roster = _make_roster(config.ROSTER_SIZE)
    roster[0].pending_level_ups = 1
    session = Session(roster=roster, rng=random.Random(2))
    controller = BetweenBattleController(session=session)

    assert controller.choose_manual_attribute(AttributeName.MIGHT) is True

    assert roster[0].pending_level_ups == 0
    assert roster[0].attributes.might == 2
    assert controller.phase == BetweenBattlePhase.SELECTING


def test_choose_manual_attribute_stays_on_the_same_hero_for_a_multi_level_jump() -> None:
    roster = _make_roster(config.ROSTER_SIZE)
    roster[0].pending_level_ups = 2
    session = Session(roster=roster, rng=random.Random(3))
    controller = BetweenBattleController(session=session)

    controller.choose_manual_attribute(AttributeName.MIGHT)
    assert controller.phase == BetweenBattlePhase.ALLOCATING
    assert controller.pending_hero is roster[0]
    assert roster[0].pending_level_ups == 1

    controller.choose_manual_attribute(AttributeName.MIGHT)
    assert roster[0].pending_level_ups == 0
    assert controller.phase == BetweenBattlePhase.SELECTING


def test_choose_manual_attribute_none_falls_back_to_affinity_instead_of_forfeiting() -> None:
    roster = _make_roster(config.ROSTER_SIZE)
    roster[0].pending_level_ups = 1
    total_before = (
        roster[0].attributes.might
        + roster[0].attributes.focus
        + roster[0].attributes.resolve
        + roster[0].attributes.agility
    )
    session = Session(roster=roster, rng=random.Random(4))
    controller = BetweenBattleController(session=session)

    assert controller.choose_manual_attribute(None) is True

    total_after = (
        roster[0].attributes.might
        + roster[0].attributes.focus
        + roster[0].attributes.resolve
        + roster[0].attributes.agility
    )
    assert total_after == total_before + config.MANUAL_ALLOCATION_POINTS_PER_LEVEL_UP
    assert roster[0].pending_level_ups == 0


def test_choose_manual_attribute_is_a_noop_outside_allocating_phase() -> None:
    session = Session(roster=_make_roster(config.ROSTER_SIZE), rng=random.Random(5))
    controller = BetweenBattleController(session=session)
    assert controller.phase == BetweenBattlePhase.SELECTING

    assert controller.choose_manual_attribute(AttributeName.MIGHT) is False


def test_toggle_fielded_selects_and_deselects() -> None:
    roster = _make_roster(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(6))
    controller = BetweenBattleController(session=session)

    assert controller.toggle_fielded(roster[0]) is True
    assert controller.selected == [roster[0]]
    assert controller.phase == BetweenBattlePhase.READY

    assert controller.toggle_fielded(roster[0]) is True
    assert controller.selected == []
    assert controller.phase == BetweenBattlePhase.SELECTING


def test_toggle_fielded_caps_at_the_fielded_squad_size() -> None:
    roster = _make_roster(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(7))
    controller = BetweenBattleController(session=session)

    for hero in roster[: config.FIELDED_SQUAD_SIZE]:
        assert controller.toggle_fielded(hero) is True

    overflow = roster[config.FIELDED_SQUAD_SIZE]
    assert controller.toggle_fielded(overflow) is False
    assert overflow not in controller.selected
    assert len(controller.selected) == config.FIELDED_SQUAD_SIZE


def test_toggle_fielded_is_a_noop_during_allocating() -> None:
    roster = _make_roster(config.ROSTER_SIZE)
    roster[0].pending_level_ups = 1
    session = Session(roster=roster, rng=random.Random(8))
    controller = BetweenBattleController(session=session)

    assert controller.toggle_fielded(roster[1]) is False
    assert controller.selected == []


def test_confirm_starts_the_next_battle_with_the_selected_squad() -> None:
    roster = _make_roster(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(9))
    controller = BetweenBattleController(session=session)
    controller.toggle_fielded(roster[0])

    assert controller.is_ready
    controller.confirm()

    assert session.current_battle is not None
    assert session.fielded == [roster[0]]


def test_default_selection_prefills_with_the_previously_fielded_squad() -> None:
    roster = _make_roster(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(10), battles_total=2)
    session.begin_battle(roster[: config.FIELDED_SQUAD_SIZE])
    battle = session.current_battle
    assert battle is not None
    battle.winner = "player"
    battle.is_over = True
    session.advance()

    controller = BetweenBattleController(session=session)

    assert controller.selected == roster[: config.FIELDED_SQUAD_SIZE]
    assert controller.phase == BetweenBattlePhase.READY
