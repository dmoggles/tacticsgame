from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ..models.hero import ClassTrack
from . import ability_library

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "class_tracks.yaml"

_cache: dict[str, ClassTrack] | None = None  # ability name -> track


def load_class_tracks() -> dict[str, ClassTrack]:
    """Ability name -> the ClassTrack whose Track 2 counter it feeds.

    Classes own abilities, not the reverse: this reads data/class_tracks.yaml,
    which lists ability ids per track, and cross-validates every id against
    data/abilities.yaml.
    """
    global _cache
    if _cache is None:
        _cache = _load()
    return dict(_cache)


def _load() -> dict[str, ClassTrack]:
    with _DATA_PATH.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    raw_tracks = data.get("class_tracks") if isinstance(data, dict) else None
    if not isinstance(raw_tracks, dict) or not raw_tracks:
        raise ValueError(f"{_DATA_PATH}: expected a non-empty top-level 'class_tracks' mapping")

    ability_names_by_id = ability_library.load_ability_ids()
    valid_track_values = {track.value for track in ClassTrack}

    result: dict[str, ClassTrack] = {}
    for track_value, ability_ids in raw_tracks.items():
        if track_value not in valid_track_values:
            raise ValueError(
                f"{_DATA_PATH}: unknown class track '{track_value}' "
                f"(expected one of {sorted(valid_track_values)})"
            )
        if not isinstance(ability_ids, list) or not ability_ids:
            raise ValueError(
                f"{_DATA_PATH}: track '{track_value}' must list at least one ability id"
            )
        track = ClassTrack(track_value)
        for ability_id in ability_ids:
            _assign(result, ability_names_by_id, track_value, track, ability_id)

    missing = set(ability_names_by_id.values()) - set(result.keys())
    if missing:
        raise ValueError(f"{_DATA_PATH}: abilities missing a class track: {sorted(missing)}")
    return result


def _assign(
    result: dict[str, ClassTrack],
    ability_names_by_id: dict[str, str],
    track_value: Any,
    track: ClassTrack,
    ability_id: Any,
) -> None:
    if ability_id not in ability_names_by_id:
        raise ValueError(
            f"{_DATA_PATH}: track '{track_value}' references unknown ability id '{ability_id}'"
        )
    name = ability_names_by_id[ability_id]
    if name in result:
        raise ValueError(f"{_DATA_PATH}: ability '{ability_id}' appears in more than one track")
    result[name] = track
