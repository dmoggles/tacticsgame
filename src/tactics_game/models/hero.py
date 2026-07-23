from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .. import config
from .ability import Ability
from .attributes import AffinityVector, Attributes
from .grid import Position


class ClassTrack(str, Enum):
    """Track 2 usage-based specialization counters (accrual only in Phase 1).

    Classes own abilities, not the reverse — see engine/class_track_library.py
    for which abilities feed each track.
    """

    FIGHTER = "fighter"
    MARKSMAN = "marksman"
    CASTER = "caster"
    HEALER = "healer"


@dataclass
class Hero:
    name: str
    attributes: Attributes
    hidden_affinity: AffinityVector
    abilities: list[Ability]
    max_hp: int
    current_hp: int
    position: Position
    is_player_controlled: bool
    level: int = 1
    xp: int = 0
    class_xp: dict[ClassTrack, int] = field(
        default_factory=lambda: {track: 0 for track in ClassTrack}
    )
    cooldowns: dict[str, int] = field(default_factory=dict)  # ability name -> turns remaining

    def __post_init__(self) -> None:
        if len(self.abilities) != config.ABILITY_SLOT_COUNT:
            raise ValueError(
                f"Hero must have exactly {config.ABILITY_SLOT_COUNT} abilities, "
                f"got {len(self.abilities)}"
            )

    @property
    def is_alive(self) -> bool:
        return self.current_hp > 0
