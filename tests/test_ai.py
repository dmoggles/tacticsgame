from __future__ import annotations

from tactics_game import config
from tactics_game.engine import ai, progression
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Grid, Position
from tactics_game.models.hero import Hero

_DEFAULT_ATTRIBUTES = Attributes(might=1, focus=1, resolve=1, agility=1)


def _make_hero(
    name: str,
    position: Position,
    current_hp: int = 20,
    max_hp: int = 20,
    attributes: Attributes = _DEFAULT_ATTRIBUTES,
    is_player_controlled: bool = True,
) -> Hero:
    return Hero(
        name=name,
        attributes=attributes,
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=max_hp,
        current_hp=current_hp,
        position=position,
        is_player_controlled=is_player_controlled,
    )


def _grid() -> Grid:
    return Grid(width=config.GRID_WIDTH, height=config.GRID_HEIGHT)


def test_decide_turn_heals_a_critically_injured_ally_in_range() -> None:
    healer = _make_hero("Healer", Position(0, 0))
    injured_ally = _make_hero("Ally", Position(0, 2), current_hp=2, max_hp=20)

    decision = ai.decide_turn(healer, [healer, injured_ally], [], _grid())

    assert decision.destination is None
    assert decision.ability_decision is not None
    assert decision.ability_decision.ability.name == "Basic Mend"
    assert decision.ability_decision.target is injured_ally


def test_decide_turn_skips_healing_while_on_cooldown() -> None:
    healer = _make_hero("Healer", Position(0, 0))
    healer.cooldowns["Basic Mend"] = 2
    injured_ally = _make_hero("Ally", Position(0, 2), current_hp=2, max_hp=20)

    decision = ai.decide_turn(healer, [healer, injured_ally], [], _grid())

    # Nothing else to do: no enemies, and the only heal ability is locked.
    assert decision.ability_decision is None


def test_decide_turn_prefers_the_higher_damage_reachable_attack() -> None:
    strong_might = Attributes(might=20, focus=1, resolve=1, agility=1)
    actor = _make_hero("Actor", Position(0, 0), attributes=strong_might)
    enemy = _make_hero(
        "Enemy", Position(1, 0), current_hp=100, max_hp=100, is_player_controlled=False
    )

    decision = ai.decide_turn(actor, [actor], [enemy], _grid())

    # Adjacent: Strike (Might-scaled, huge here) and Bolt are both reachable,
    # Shot isn't (below its min range) — the far stronger Strike should win,
    # and since the actor is already in range there's no need to move.
    assert decision.destination is None
    assert decision.ability_decision is not None
    assert decision.ability_decision.ability.name == "Basic Strike"
    assert decision.ability_decision.target is enemy


def test_decide_turn_falls_back_to_ranged_when_melee_is_unreachable_this_turn() -> None:
    strong_might = Attributes(might=20, focus=1, resolve=1, agility=1)
    actor = _make_hero("Actor", Position(0, 0), attributes=strong_might)
    enemy = _make_hero(
        "Enemy", Position(5, 0), current_hp=100, max_hp=100, is_player_controlled=False
    )

    decision = ai.decide_turn(actor, [actor], [enemy], _grid())

    # Moving the full MOVEMENT_RANGE only closes the gap to distance 2 —
    # melee (range 1) is still unreachable, but Basic Shot (min 2, max 4) is,
    # so the actor should move in and shoot rather than whiff toward melee.
    assert decision.destination == Position(config.MOVEMENT_RANGE, 0)
    assert decision.ability_decision is not None
    assert decision.ability_decision.ability.name == "Basic Shot"
    assert decision.ability_decision.target is enemy


def test_decide_turn_just_moves_when_nothing_is_reachable_yet() -> None:
    actor = _make_hero("Actor", Position(0, 0))
    enemy = _make_hero(
        "Enemy", Position(0, 11), current_hp=100, max_hp=100, is_player_controlled=False
    )

    decision = ai.decide_turn(actor, [actor], [enemy], _grid())

    assert decision.destination == Position(0, config.MOVEMENT_RANGE)
    assert decision.ability_decision is None


def test_decide_turn_passes_when_nothing_to_do() -> None:
    actor = _make_hero("Actor", Position(0, 0))

    decision = ai.decide_turn(actor, [actor], [], _grid())

    assert decision.destination is None
    assert decision.ability_decision is None
