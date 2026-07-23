from __future__ import annotations

import json
import random

from tactics_game import config
from tactics_game.engine import progression, telemetry
from tactics_game.engine.session import Session
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Position
from tactics_game.models.hero import ClassTrack, Hero

_ATTRIBUTES = Attributes(might=5, focus=4, resolve=6, agility=3)
_AFFINITY = AffinityVector(might=0.4, focus=0.1, resolve=0.4, agility=0.1)


def _make_hero(name: str) -> Hero:
    max_hp = progression.compute_max_hp(_ATTRIBUTES)
    return Hero(
        name=name,
        attributes=_ATTRIBUTES,
        hidden_affinity=_AFFINITY,
        abilities=progression.create_basic_kit(),
        max_hp=max_hp,
        current_hp=max_hp,
        position=Position(0, 0),
        is_player_controlled=True,
        level=3,
    )


def test_concentration_is_zero_with_no_class_xp() -> None:
    class_xp = {track: 0 for track in ClassTrack}
    assert telemetry.compute_class_xp_concentration(class_xp) == 0.0


def test_concentration_is_one_when_fully_specialized() -> None:
    class_xp = {track: 0 for track in ClassTrack}
    class_xp[ClassTrack.FIGHTER] = 40
    assert telemetry.compute_class_xp_concentration(class_xp) == 1.0


def test_concentration_is_a_quarter_when_perfectly_even() -> None:
    class_xp = {track: 10 for track in ClassTrack}
    assert telemetry.compute_class_xp_concentration(class_xp) == 0.25


def test_concentration_reflects_the_top_tracks_share() -> None:
    class_xp = {ClassTrack.FIGHTER: 30, ClassTrack.MARKSMAN: 10, ClassTrack.CASTER: 0, ClassTrack.HEALER: 0}
    assert telemetry.compute_class_xp_concentration(class_xp) == 30 / 40


def test_build_hero_report_includes_all_required_fields() -> None:
    hero = _make_hero("Sample")
    hero.class_xp[ClassTrack.FIGHTER] = 20
    hero.class_xp[ClassTrack.CASTER] = 5
    hero.battles_fielded = 4
    hero.battles_benched = 1

    report = telemetry.build_hero_report(hero)

    assert report["name"] == "Sample"
    assert report["level"] == 3
    assert report["attributes"] == {"might": 5, "focus": 4, "resolve": 6, "agility": 3}
    assert report["class_xp"] == {"fighter": 20, "marksman": 0, "caster": 5, "healer": 0}
    assert report["class_xp_concentration"] == 20 / 25
    assert report["hidden_affinity"] == {"might": 0.4, "focus": 0.1, "resolve": 0.4, "agility": 0.1}
    assert report["battles_fielded"] == 4
    assert report["battles_benched"] == 1


def test_build_session_report_covers_the_whole_roster_not_just_fielded() -> None:
    roster = [_make_hero(f"Hero {i + 1}") for i in range(config.ROSTER_SIZE)]
    session = Session(roster=roster, rng=random.Random(0))
    session.begin_battle(roster[: config.FIELDED_SQUAD_SIZE])

    report = telemetry.build_session_report(session)

    assert len(report) == config.ROSTER_SIZE
    assert {entry["name"] for entry in report} == {hero.name for hero in roster}


def test_write_session_report_writes_valid_json_matching_the_report(tmp_path) -> None:
    roster = [_make_hero(f"Hero {i + 1}") for i in range(config.FIELDED_SQUAD_SIZE)]
    session = Session(roster=roster, rng=random.Random(1))
    session.begin_battle(roster)
    output_path = tmp_path / "nested" / "session_report.json"

    written_path = telemetry.write_session_report(session, output_path)

    assert written_path == output_path
    assert output_path.exists()
    on_disk = json.loads(output_path.read_text(encoding="utf-8"))
    assert on_disk == telemetry.build_session_report(session)


def test_write_session_report_defaults_to_the_module_output_path(tmp_path, monkeypatch) -> None:
    default_path = tmp_path / "telemetry" / "session_report.json"
    monkeypatch.setattr(telemetry, "DEFAULT_OUTPUT_PATH", default_path)
    roster = [_make_hero(f"Hero {i + 1}") for i in range(config.FIELDED_SQUAD_SIZE)]
    session = Session(roster=roster, rng=random.Random(2))
    session.begin_battle(roster)

    written_path = telemetry.write_session_report(session)

    assert written_path == default_path
    assert default_path.exists()
