"""Headless sweep of Phase 3's contested-roll foundation.

Run with ``uv run python scripts/simulate_contests.py``. The script reports
contest success rates only; live ability damage remains deterministic until
Phase 3 Step 3 connects margin to magnitude.
"""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass

from tactics_game.engine import progression, resolution
from tactics_game.models.attributes import AffinityVector, Attributes
from tactics_game.models.grid import Position
from tactics_game.models.hero import Hero

TRIALS_PER_SCENARIO = 50_000
SIMULATION_SEED = 20260723
ATTRIBUTE_BANDS = (4, 8, 12)
SUPPORT_ATTRIBUTE_VALUE = 4


@dataclass(frozen=True)
class AttackProfile:
    name: str
    scaling: list[resolution.ScalingTerm]


ATTACK_PROFILES = (
    AttackProfile(
        "Strike (Might 0.8 + Resolve 0.4)",
        [
            resolution.ScalingTerm(attribute="might", multiplier=0.8),
            resolution.ScalingTerm(attribute="resolve", multiplier=0.4),
        ],
    ),
    AttackProfile(
        "Bolt (Focus 1.0)",
        [resolution.ScalingTerm(attribute="focus", multiplier=1.0)],
    ),
    AttackProfile(
        "Shot (Agility 1.0)",
        [resolution.ScalingTerm(attribute="agility", multiplier=1.0)],
    ),
)


def _hero(name: str, attributes: Attributes) -> Hero:
    return Hero(
        name=name,
        attributes=attributes,
        hidden_affinity=AffinityVector(might=0.25, focus=0.25, resolve=0.25, agility=0.25),
        abilities=progression.create_basic_kit(),
        max_hp=20,
        current_hp=20,
        position=Position(0, 0),
        is_player_controlled=True,
    )


def _attributes(*, primary_attribute: str, primary_value: int, resolve: int) -> Attributes:
    values = {
        "might": SUPPORT_ATTRIBUTE_VALUE,
        "focus": SUPPORT_ATTRIBUTE_VALUE,
        "resolve": resolve,
        "agility": SUPPORT_ATTRIBUTE_VALUE,
    }
    values[primary_attribute] = primary_value
    return Attributes(**values)


def run_sweep(trials: int, seed: int) -> str:
    rows = [
        "| Attack | Attack primary | Defender Resolve | Defender matching stat | Attack score | Defence score | Success rate | Mean margin |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    scenario_index = 0
    for profile in ATTACK_PROFILES:
        primary_attribute = resolution.primary_attack_attribute(profile.scaling)
        for attacker_primary in ATTRIBUTE_BANDS:
            attacker = _hero(
                "Attacker",
                _attributes(
                    primary_attribute=primary_attribute,
                    primary_value=attacker_primary,
                    resolve=SUPPORT_ATTRIBUTE_VALUE,
                ),
            )
            for defender_resolve in ATTRIBUTE_BANDS:
                for defender_primary in ATTRIBUTE_BANDS:
                    defender = _hero(
                        "Defender",
                        _attributes(
                            primary_attribute=primary_attribute,
                            primary_value=defender_primary,
                            resolve=defender_resolve,
                        ),
                    )
                    rng = random.Random(seed + scenario_index)
                    results = [
                        resolution.resolve_contest(attacker, defender, profile.scaling, rng)
                        for _ in range(trials)
                    ]
                    success_rate = sum(result.succeeded for result in results) / trials
                    mean_margin = sum(result.margin for result in results) / trials
                    first = results[0]
                    rows.append(
                        "| "
                        f"{profile.name} | {attacker_primary} | {defender_resolve} | "
                        f"{defender_primary} | {first.attack_score:.1f} | "
                        f"{first.defence_score:.1f} | {success_rate:.1%} | {mean_margin:.2f} |"
                    )
                    scenario_index += 1
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=TRIALS_PER_SCENARIO)
    parser.add_argument("--seed", type=int, default=SIMULATION_SEED)
    args = parser.parse_args()
    print(run_sweep(args.trials, args.seed))


if __name__ == "__main__":
    main()
