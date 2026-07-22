from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    x: int
    y: int

    def distance_to(self, other: Position) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)


@dataclass(frozen=True)
class Grid:
    width: int
    height: int

    def in_bounds(self, position: Position) -> bool:
        return 0 <= position.x < self.width and 0 <= position.y < self.height
