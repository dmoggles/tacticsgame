from __future__ import annotations

import pytest

from tactics_game.engine import class_track_library
from tactics_game.models.hero import ClassTrack


def test_load_class_tracks_resolves_the_four_basic_abilities() -> None:
    tracks = class_track_library.load_class_tracks()
    assert tracks["Basic Strike"] == ClassTrack.FIGHTER
    assert tracks["Basic Shot"] == ClassTrack.MARKSMAN
    assert tracks["Basic Bolt"] == ClassTrack.CASTER
    assert tracks["Basic Mend"] == ClassTrack.HEALER


def test_assign_raises_on_unknown_ability_id() -> None:
    with pytest.raises(ValueError, match="unknown ability id"):
        class_track_library._assign(
            {}, {"basic_strike": "Basic Strike"}, "fighter", ClassTrack.FIGHTER, "not_real"
        )


def test_assign_raises_when_an_ability_is_assigned_to_two_tracks() -> None:
    ability_names_by_id = {"basic_strike": "Basic Strike"}
    result: dict[str, ClassTrack] = {}
    class_track_library._assign(
        result, ability_names_by_id, "fighter", ClassTrack.FIGHTER, "basic_strike"
    )
    with pytest.raises(ValueError, match="more than one track"):
        class_track_library._assign(
            result, ability_names_by_id, "marksman", ClassTrack.MARKSMAN, "basic_strike"
        )
