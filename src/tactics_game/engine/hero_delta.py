from __future__ import annotations

from dataclasses import dataclass

from ..models.attributes import AttributeName, Attributes
from ..models.hero import ClassTrack, Hero

# The between-battle screen (docs/04_phase2b_definition.md section 6) must
# show "the delta from the previous battle" and nothing further back — no
# level-up history. A HeroSnapshot is the single, most-recent "before"
# state; nothing here accumulates a log of past snapshots, so the
# no-history requirement holds structurally, not just by UI convention.


@dataclass(frozen=True)
class HeroSnapshot:
    level: int
    attributes: Attributes
    class_xp: dict[ClassTrack, int]


@dataclass(frozen=True)
class HeroDelta:
    level_before: int
    level_after: int
    attribute_deltas: dict[AttributeName, int]
    class_xp_deltas: dict[ClassTrack, int]

    @property
    def leveled_up(self) -> bool:
        return self.level_after > self.level_before


def snapshot_hero(hero: Hero) -> HeroSnapshot:
    """Copies class_xp so a later mutation of `hero` can't retroactively
    change a snapshot already taken."""
    return HeroSnapshot(
        level=hero.level, attributes=hero.attributes, class_xp=dict(hero.class_xp)
    )


def compute_delta(before: HeroSnapshot, hero: Hero) -> HeroDelta:
    attribute_deltas = {
        AttributeName.MIGHT: hero.attributes.might - before.attributes.might,
        AttributeName.FOCUS: hero.attributes.focus - before.attributes.focus,
        AttributeName.RESOLVE: hero.attributes.resolve - before.attributes.resolve,
        AttributeName.AGILITY: hero.attributes.agility - before.attributes.agility,
    }
    class_xp_deltas = {
        track: hero.class_xp[track] - before.class_xp.get(track, 0) for track in ClassTrack
    }
    return HeroDelta(
        level_before=before.level,
        level_after=hero.level,
        attribute_deltas=attribute_deltas,
        class_xp_deltas=class_xp_deltas,
    )
