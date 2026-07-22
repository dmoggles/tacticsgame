from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.hero import Hero


# TODO(phase2): agility-based initiative. For now, player heroes act in
# slot order, then enemy heroes act in slot order, repeat each round.
# Dead heroes are skipped at consumption time by the battle loop, not
# filtered out here, so mid-round deaths don't reshuffle turn indices.
def build_turn_order(player_squad: list[Hero], enemy_squad: list[Hero]) -> list[Hero]:
    return [*player_squad, *enemy_squad]
