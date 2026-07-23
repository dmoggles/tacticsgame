from __future__ import annotations

import pytest

from tactics_game import config
from tactics_game.engine import progression, roster
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Position
from tactics_game.models.hero import Hero

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


def test_select_fielded_squad_returns_the_benched_remainder() -> None:
    roster_heroes = _make_roster(config.ROSTER_SIZE)
    fielded = roster_heroes[: config.FIELDED_SQUAD_SIZE]

    benched = roster.select_fielded_squad(roster_heroes, fielded)

    assert benched == roster_heroes[config.FIELDED_SQUAD_SIZE :]


def test_select_fielded_squad_allows_fielding_fewer_than_the_maximum() -> None:
    roster_heroes = _make_roster(config.ROSTER_SIZE)

    benched = roster.select_fielded_squad(roster_heroes, roster_heroes[:1])

    assert benched == roster_heroes[1:]


def test_select_fielded_squad_rejects_an_empty_selection() -> None:
    roster_heroes = _make_roster(config.ROSTER_SIZE)

    with pytest.raises(ValueError):
        roster.select_fielded_squad(roster_heroes, [])


def test_select_fielded_squad_rejects_more_than_the_fielded_maximum() -> None:
    roster_heroes = _make_roster(config.ROSTER_SIZE)

    with pytest.raises(ValueError):
        roster.select_fielded_squad(roster_heroes, roster_heroes[: config.FIELDED_SQUAD_SIZE + 1])


def test_select_fielded_squad_rejects_the_same_hero_fielded_twice() -> None:
    roster_heroes = _make_roster(config.ROSTER_SIZE)

    with pytest.raises(ValueError):
        roster.select_fielded_squad(roster_heroes, [roster_heroes[0], roster_heroes[0]])


def test_select_fielded_squad_rejects_a_hero_not_in_the_roster() -> None:
    roster_heroes = _make_roster(config.ROSTER_SIZE)
    outsider = _make_hero("Outsider")

    with pytest.raises(ValueError):
        roster.select_fielded_squad(roster_heroes, [outsider])


def test_select_fielded_squad_uses_identity_not_field_equality() -> None:
    # Two heroes can share every field value (name included) and still be
    # distinct roster slots — membership must be checked by identity.
    look_alike_a = _make_hero("Twin")
    look_alike_b = _make_hero("Twin")
    roster_heroes = [look_alike_a]

    with pytest.raises(ValueError):
        roster.select_fielded_squad(roster_heroes, [look_alike_b])
