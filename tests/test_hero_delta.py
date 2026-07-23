from __future__ import annotations

from tactics_game.engine import hero_delta, progression
from tactics_game.models.attributes import AffinityVector, AttributeName, Attributes
from tactics_game.models.grid import Position
from tactics_game.models.hero import ClassTrack, Hero

_ATTRIBUTES = Attributes(might=1, focus=2, resolve=3, agility=4)


def _make_hero() -> Hero:
    return Hero(
        name="Sample",
        attributes=_ATTRIBUTES,
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=progression.compute_max_hp(_ATTRIBUTES),
        current_hp=progression.compute_max_hp(_ATTRIBUTES),
        position=Position(0, 0),
        is_player_controlled=True,
    )


def test_compute_delta_is_all_zero_for_an_unchanged_hero() -> None:
    hero = _make_hero()
    before = hero_delta.snapshot_hero(hero)

    delta = hero_delta.compute_delta(before, hero)

    assert not delta.leveled_up
    assert all(change == 0 for change in delta.attribute_deltas.values())
    assert all(change == 0 for change in delta.class_xp_deltas.values())


def test_compute_delta_reflects_attribute_and_level_changes() -> None:
    hero = _make_hero()
    before = hero_delta.snapshot_hero(hero)

    hero.attributes = hero.attributes.with_bonus(might=2, agility=1)
    hero.level = 2

    delta = hero_delta.compute_delta(before, hero)

    assert delta.leveled_up
    assert delta.level_before == 1
    assert delta.level_after == 2
    assert delta.attribute_deltas[AttributeName.MIGHT] == 2
    assert delta.attribute_deltas[AttributeName.AGILITY] == 1
    assert delta.attribute_deltas[AttributeName.FOCUS] == 0
    assert delta.attribute_deltas[AttributeName.RESOLVE] == 0


def test_compute_delta_reflects_class_xp_changes() -> None:
    hero = _make_hero()
    before = hero_delta.snapshot_hero(hero)

    hero.class_xp[ClassTrack.FIGHTER] += 5

    delta = hero_delta.compute_delta(before, hero)

    assert delta.class_xp_deltas[ClassTrack.FIGHTER] == 5
    assert delta.class_xp_deltas[ClassTrack.MARKSMAN] == 0


def test_snapshot_is_unaffected_by_later_mutation() -> None:
    # The whole point of a snapshot: it must not silently track the live
    # hero, or "delta since the snapshot" would always read as zero.
    hero = _make_hero()
    before = hero_delta.snapshot_hero(hero)

    hero.class_xp[ClassTrack.HEALER] += 10
    hero.attributes = hero.attributes.with_bonus(resolve=3)

    assert before.class_xp[ClassTrack.HEALER] == 0
    assert before.attributes.resolve == 3
