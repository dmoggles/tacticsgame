from __future__ import annotations

import random

import pytest

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


def _make_squad(size: int, attributes: Attributes = _DEFAULT_ATTRIBUTES) -> list[Hero]:
    return [_make_hero(f"Hero {i + 1}", attributes=attributes) for i in range(size)]


def _force_win(session: Session) -> None:
    battle = session.current_battle
    assert battle is not None
    battle.winner = "player"
    battle.is_over = True


def test_session_has_no_battle_until_a_squad_is_fielded() -> None:
    roster = _make_squad(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(0))
    assert session.current_battle is None


def test_begin_battle_fields_a_chosen_subset_of_the_roster() -> None:
    roster = _make_squad(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(1))
    chosen = roster[: config.FIELDED_SQUAD_SIZE]

    session.begin_battle(chosen)

    assert session.fielded == chosen
    assert session.benched == roster[config.FIELDED_SQUAD_SIZE :]
    assert session.current_battle is not None
    assert session.current_battle.player_squad == chosen


@pytest.mark.parametrize(
    "build_fielded",
    [
        lambda roster: [],
        lambda roster: roster[: config.FIELDED_SQUAD_SIZE + 1],
        lambda roster: [roster[0], roster[0]],
        lambda roster: [_make_hero("Outsider")],
    ],
    ids=["empty", "over-max", "duplicate", "not-in-roster"],
)
def test_begin_battle_rejects_an_illegal_selection(build_fielded) -> None:
    roster = _make_squad(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(2))

    with pytest.raises(ValueError):
        session.begin_battle(build_fielded(roster))


def test_begin_battle_allows_fielding_fewer_than_the_maximum() -> None:
    roster = _make_squad(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(3))

    session.begin_battle(roster[:1])

    assert session.fielded == roster[:1]
    assert session.benched == roster[1:]
    assert session.current_battle is not None
    assert session.current_battle.player_squad == roster[:1]


def test_begin_battle_rejects_starting_a_new_battle_while_one_is_in_progress() -> None:
    roster = _make_squad(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(4))
    session.begin_battle(roster[: config.FIELDED_SQUAD_SIZE])

    with pytest.raises(ValueError):
        session.begin_battle(roster[config.FIELDED_SQUAD_SIZE :])


def test_roster_hero_identity_and_progression_persist_across_battles() -> None:
    roster = _make_squad(config.FIELDED_SQUAD_SIZE)
    original_heroes = list(roster)
    session = Session(roster=roster, rng=random.Random(5), battles_total=2)
    session.begin_battle(roster)

    first_battle = session.current_battle
    assert first_battle is not None
    first_battle.run_to_completion()
    session.advance()

    # Same Hero objects, not copies/rebuilds — this is the entire
    # persistence mechanism.
    assert session.roster == original_heroes
    for hero, original in zip(session.roster, original_heroes):
        assert hero is original

    if not session.is_over:
        assert session.current_battle is None
        session.begin_battle(session.roster)
        assert session.current_battle is not None
        assert session.current_battle.player_squad == original_heroes


def test_cooldowns_and_positions_reset_between_battles_for_fielded_heroes() -> None:
    roster = _make_squad(config.FIELDED_SQUAD_SIZE)
    roster[0].cooldowns["Basic Mend"] = 3
    roster[0].position = Position(6, 6)
    session = Session(roster=roster, rng=random.Random(6), battles_total=2)
    session.begin_battle(roster)
    _force_win(session)

    session.advance()
    session.begin_battle(session.roster)

    assert roster[0].cooldowns == {}
    assert roster[0].position == Position(1, 2)
    assert roster[1].position == Position(1, 5)


def test_hp_fully_heals_between_battles_for_fielded_heroes() -> None:
    roster = _make_squad(config.FIELDED_SQUAD_SIZE)
    roster[0].current_hp = 1
    session = Session(roster=roster, rng=random.Random(7), battles_total=2)
    session.begin_battle(roster)
    _force_win(session)

    session.advance()
    session.begin_battle(session.roster)

    assert roster[0].current_hp == roster[0].max_hp


def test_benched_heroes_are_untouched_by_battle_preparation() -> None:
    # Gradual recovery (Phase 2b step 2) hasn't landed yet — a benched
    # hero's position/cooldowns/HP must stay exactly as they were, not get
    # silently reset or healed by the fielded-only preparation step.
    roster = _make_squad(config.ROSTER_SIZE)
    benched_hero = roster[-1]
    benched_hero.current_hp = 1
    benched_hero.cooldowns["Basic Mend"] = 2
    benched_hero.position = Position(6, 6)

    session = Session(roster=roster, rng=random.Random(8), battles_total=1)
    session.begin_battle(roster[: config.FIELDED_SQUAD_SIZE])

    assert benched_hero in session.benched
    assert benched_hero.current_hp == 1
    assert benched_hero.cooldowns == {"Basic Mend": 2}
    assert benched_hero.position == Position(6, 6)


def test_enemy_squad_is_regenerated_each_battle() -> None:
    roster = _make_squad(config.FIELDED_SQUAD_SIZE)
    session = Session(roster=roster, rng=random.Random(9), battles_total=2)
    session.begin_battle(roster)
    first_battle = session.current_battle
    assert first_battle is not None
    first_enemy_squad = first_battle.enemy_squad
    _force_win(session)

    session.advance()
    session.begin_battle(session.roster)

    second_battle = session.current_battle
    assert second_battle is not None
    second_enemy_squad = second_battle.enemy_squad
    assert len(first_enemy_squad) == len(second_enemy_squad)
    for old, new in zip(first_enemy_squad, second_enemy_squad):
        assert old is not new


def _total_progress(hero: Hero) -> int:
    """XP gained, expressed independent of level-up wraparound (grant_xp
    zeroes .xp exactly when a gain lands on a level threshold), so a
    before/after comparison can't be fooled by a lucky/unlucky boundary."""
    return (hero.level - 1) * config.XP_LEVEL_THRESHOLD + hero.xp


def test_fielding_fewer_heroes_gives_each_a_proportionally_larger_xp_share() -> None:
    # Same seed in both sessions and enemy generation not depending on how
    # many player heroes are fielded means the XP pool is identical across
    # both runs — the only variable is fielded-squad size. Overwhelming
    # attributes guarantee a real win (via actual combat, not a hand-set
    # flag) even when outnumbered, so award_battle_xp's real call path
    # through Battle._resolve_battle_end actually fires.
    overwhelming = Attributes(might=100, focus=100, resolve=100, agility=100)

    full_roster = _make_squad(2, attributes=overwhelming)
    full_session = Session(roster=full_roster, rng=random.Random(42), battles_total=1)
    full_session.begin_battle(full_roster)
    full_battle = full_session.current_battle
    assert full_battle is not None
    full_battle.run_to_completion()
    full_session.advance()

    short_roster = _make_squad(2, attributes=overwhelming)
    short_session = Session(roster=short_roster, rng=random.Random(42), battles_total=1)
    short_session.begin_battle(short_roster[:1])
    short_battle = short_session.current_battle
    assert short_battle is not None
    short_battle.run_to_completion()
    short_session.advance()

    assert full_session.result == "won"
    assert short_session.result == "won"
    assert _total_progress(short_roster[0]) >= 2 * _total_progress(full_roster[0])
    assert _total_progress(short_roster[0]) > 0


def test_bench_bonus_xp_is_zero_at_default_multiplier() -> None:
    roster = _make_squad(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(10), battles_total=1)
    session.begin_battle(roster[: config.FIELDED_SQUAD_SIZE])
    _force_win(session)

    session.advance()

    assert session.benched
    for hero in session.benched:
        assert hero.xp == 0


def test_session_ends_in_win_once_all_battles_are_won() -> None:
    overwhelming = Attributes(might=100, focus=100, resolve=100, agility=100)
    roster = _make_squad(config.FIELDED_SQUAD_SIZE, attributes=overwhelming)
    session = Session(roster=roster, rng=random.Random(11), battles_total=3)

    session.run_to_completion()

    assert session.is_over
    assert session.result == "won"
    assert session.battles_won == session.battles_total


def test_advance_is_a_noop_once_the_session_is_over() -> None:
    # Regression: a caller that keeps calling advance() every frame after
    # the session already ended (e.g. a UI loop that doesn't stop) must
    # not keep re-scoring the same finished battle — battles_won should
    # never move past battles_total, no matter how many extra calls.
    overwhelming = Attributes(might=100, focus=100, resolve=100, agility=100)
    roster = _make_squad(config.FIELDED_SQUAD_SIZE, attributes=overwhelming)
    session = Session(roster=roster, rng=random.Random(12), battles_total=2)
    session.run_to_completion()
    assert session.is_over
    assert session.result == "won"
    assert session.battles_won == session.battles_total

    for _ in range(10):
        session.advance()

    assert session.battles_won == session.battles_total
    assert session.result == "won"


def test_session_ends_in_loss_when_a_battle_is_lost() -> None:
    for seed in range(3):
        fragile = Attributes(might=1, focus=1, resolve=1, agility=1)
        roster = _make_squad(config.FIELDED_SQUAD_SIZE, attributes=fragile)
        for hero in roster:
            hero.current_hp = 1
        session = Session(roster=roster, rng=random.Random(seed), battles_total=5)

        session.run_to_completion()

        assert session.is_over
        assert session.result == "lost"
        assert session.battles_won < session.battles_total


def test_run_to_completion_accepts_a_custom_selection_strategy() -> None:
    roster = _make_squad(config.ROSTER_SIZE)
    session = Session(roster=roster, rng=random.Random(13), battles_total=2)

    session.run_to_completion(select_fielded=lambda r: r[:1])

    assert session.is_over
    assert session.result in ("won", "lost")


def test_session_runs_end_to_end_to_a_win_or_loss() -> None:
    for seed in range(10):
        rng = random.Random(seed)
        roster = [
            progression.create_starting_hero(
                name=f"Hero {i + 1}",
                position=Position(1, 2 + i * 3),
                is_player_controlled=True,
                rng=rng,
            )
            for i in range(config.FIELDED_SQUAD_SIZE)
        ]
        session = Session(roster=roster, rng=rng, battles_total=config.SESSION_BATTLE_COUNT)

        session.run_to_completion()

        assert session.is_over
        assert session.result in ("won", "lost")
