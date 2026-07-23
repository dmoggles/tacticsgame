from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..models.hero import ClassTrack, Hero
from .session import Session

# Session-end telemetry (docs/04_phase2b_definition.md section 7): whether
# player agency over Track 2 specialization is real or cosmetic hinges on
# correlating class-XP concentration against each hero's hidden affinity
# offline. The affinity vector appears in this dump *because* it's a dev
# artifact, not a player-facing path — nothing in visualizer/ ever reads a
# telemetry report back for on-screen display (see docs/adr/0008-
# between-battle-screen.md's snapshot/delta mechanism for the player-facing
# equivalent, which never touches affinity at all).

DEFAULT_OUTPUT_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "telemetry" / "session_report.json"
)


def compute_class_xp_concentration(class_xp: dict[ClassTrack, int]) -> float:
    """Share of total class XP held by the single highest track — 1.0 is
    fully specialized, 0.25 is perfectly even across all four tracks.
    0.0 for a hero with no class XP at all (nothing to be concentrated).

    Chosen over a normalized-entropy measure (the phase doc's other named
    option) purely for simplicity, same spirit as
    progression.compute_enemy_strength's sum-of-levels choice.
    """
    total = sum(class_xp.values())
    return max(class_xp.values()) / total if total > 0 else 0.0


def build_hero_report(hero: Hero) -> dict[str, Any]:
    return {
        "name": hero.name,
        "level": hero.level,
        "attributes": {
            "might": hero.attributes.might,
            "focus": hero.attributes.focus,
            "resolve": hero.attributes.resolve,
            "agility": hero.attributes.agility,
        },
        "class_xp": {track.value: amount for track, amount in hero.class_xp.items()},
        "class_xp_concentration": compute_class_xp_concentration(hero.class_xp),
        "hidden_affinity": {name.value: weight for name, weight in hero.hidden_affinity.as_weights()},
        "battles_fielded": hero.battles_fielded,
        "battles_benched": hero.battles_benched,
    }


def build_session_report(session: Session) -> list[dict[str, Any]]:
    return [build_hero_report(hero) for hero in session.roster]


def write_session_report(session: Session, path: Path | None = None) -> Path:
    """Writes build_session_report(session) as indented JSON, creating the
    parent directory if needed (mirrors dev_tools.write_baseline_fixture).
    Returns the path actually written to, for callers that want to log it."""
    output_path = path if path is not None else DEFAULT_OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_session_report(session), indent=2) + "\n", encoding="utf-8")
    return output_path
