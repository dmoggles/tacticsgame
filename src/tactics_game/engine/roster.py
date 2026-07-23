from __future__ import annotations

from .. import config
from ..models.hero import Hero

# A roster (docs/04_phase2b_definition.md section 1) is the player's full
# pool of heroes; a fielded squad is the subset chosen to fight one battle.
# This module only validates that choice and derives the benched remainder —
# it holds no state of its own (Session owns the actual roster/fielded/
# benched lists).


def select_fielded_squad(roster: list[Hero], fielded: list[Hero]) -> list[Hero]:
    """Validate `fielded` as a legal choice from `roster` and return the
    benched remainder (roster minus fielded).

    Legal means: at least one hero, no more than config.FIELDED_SQUAD_SIZE,
    no repeats, and every entry actually drawn from `roster`. Membership is
    checked by identity (`id()`), not equality — Hero uses the dataclass-
    generated `__eq__`, which compares field values, so two distinct heroes
    with identical stats would otherwise be indistinguishable here.
    """
    if not fielded:
        raise ValueError("must field at least one hero")
    if len(fielded) > config.FIELDED_SQUAD_SIZE:
        raise ValueError(
            f"cannot field more than {config.FIELDED_SQUAD_SIZE} heroes, got {len(fielded)}"
        )
    fielded_ids = [id(hero) for hero in fielded]
    if len(set(fielded_ids)) != len(fielded_ids):
        raise ValueError("fielded squad contains the same hero more than once")
    roster_ids = {id(hero) for hero in roster}
    for hero in fielded:
        if id(hero) not in roster_ids:
            raise ValueError(f"{hero.name} is not in the roster")
    fielded_id_set = set(fielded_ids)
    return [hero for hero in roster if id(hero) not in fielded_id_set]


def select_balanced_squad(roster: list[Hero]) -> list[Hero]:
    """Select a fielded squad prioritizing heroes with fewer fielded battles.
    Used for balanced squad rotation (e.g. headless auto-play / telemetry)."""
    sorted_roster = sorted(roster, key=lambda h: (h.battles_fielded, roster.index(h)))
    return sorted_roster[: config.FIELDED_SQUAD_SIZE]
