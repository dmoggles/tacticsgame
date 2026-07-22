from __future__ import annotations

from dataclasses import dataclass, field

from .. import config
from .ability import Ability, ClassTrack
from .attributes import AffinityVector, Attributes
from .grid import Position


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
