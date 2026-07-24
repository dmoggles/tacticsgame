"""Compare fixed-noise and scale-invariant contest models headlessly.

This is deliberately independent of ``engine.resolution`` while the Phase 3
patch is being evaluated. It keeps the legacy 3d3 model runnable alongside
the proposed scaled continuous model from docs/08_patch_scale_invariant_contest_roll.md.
"""

from __future__ import annotations

import argparse
import random
import statistics
from collections.abc import Callable
from dataclasses import dataclass

from tactics_game import config
from tactics_game.engine import progression
from tactics_game.models.attributes import AttributeName, Attributes

TRIALS_PER_CELL = 50_000
REALISTIC_PAIRS = 200
REALISTIC_TRIALS = 2_000
SIMULATION_SEED = 20260724
MAGNITUDES = (2.0, 4.0, 8.0, 16.0, 32.0, 64.0)
RATIOS = (1.5, 2.0, 3.0)
CAREER_LEVEL_UPS = (0, 5, 20, 50)
SENSITIVITY_SAMPLES = (1, 2, 3, 5, 10)


@dataclass(frozen=True)
class ContestSample:
    margin: float

    @property
    def succeeded(self) -> bool:
        return self.margin > 0


ContestRoll = Callable[[float, float, random.Random, int], ContestSample]


def legacy_3d3(attack: float, defence: float, rng: random.Random, _: int) -> ContestSample:
    """The pre-patch fixed-width additive model, retained for comparison."""
    attacker_noise = sum(rng.randint(1, 3) for _ in range(3)) - 6
    defender_noise = sum(rng.randint(1, 3) for _ in range(3)) - 6
    return ContestSample(attack + attacker_noise - defence - defender_noise)


def scaled_ndx(attack: float, defence: float, rng: random.Random, samples: int) -> ContestSample:
    """Continuous N-sample scaled Irwin-Hall rolls from the patch specification."""
    attacker_roll = sum(rng.random() * attack / samples for _ in range(samples))
    defender_roll = sum(rng.random() * defence / samples for _ in range(samples))
    return ContestSample(attacker_roll - defender_roll)


MODELS: tuple[tuple[str, ContestRoll], ...] = (
    ("legacy_3d3", legacy_3d3),
    ("scaled_ndx", scaled_ndx),
)


def _summary(roll: ContestRoll, attack: float, defence: float, rng: random.Random, samples: int, trials: int) -> tuple[float, float, float]:
    outcomes = [roll(attack, defence, rng, samples) for _ in range(trials)]
    success = sum(outcome.succeeded for outcome in outcomes) / trials
    margins = [outcome.margin for outcome in outcomes]
    tie_rate = sum(margin == 0 for margin in margins) / trials
    return success, statistics.stdev(margins), tie_rate


def sweep_parity(rng: random.Random, trials: int, samples: int) -> list[str]:
    rows = ["## Sweep 1 — parity across magnitude", "", "| Model | A = D | Success | Margin SD | Exact ties |", "| --- | ---: | ---: | ---: | ---: |"]
    for name, roll in MODELS:
        for magnitude in MAGNITUDES:
            success, margin_sd, ties = _summary(roll, magnitude, magnitude, rng, samples, trials)
            rows.append(f"| {name} | {magnitude:g} | {success:.2%} | {margin_sd:.3f} | {ties:.2%} |")
    return rows


def sweep_ratios(rng: random.Random, trials: int, samples: int) -> list[str]:
    rows = ["## Sweep 2 — fixed ratio across magnitude", "", "| Model | A/D | D | Success |", "| --- | ---: | ---: | ---: |"]
    for name, roll in MODELS:
        for ratio in RATIOS:
            for defence in MAGNITUDES:
                success, _, _ = _summary(roll, ratio * defence, defence, rng, samples, trials)
                rows.append(f"| {name} | {ratio:g} | {defence:g} | {success:.2%} |")
    return rows


def _hero_attributes(rng: random.Random, career_level_ups: int) -> Attributes:
    affinity = progression.generate_hidden_affinity(rng)
    attributes = progression.synthesize_starting_attributes(affinity, rng)
    totals = {name: getattr(attributes, name.value) for name in AttributeName}
    for _ in range(career_level_ups):
        for name, count in progression.allocate_points(affinity, config.POINTS_PER_LEVEL_UP, rng).items():
            totals[name] += count
    return Attributes(
        might=totals[AttributeName.MIGHT],
        focus=totals[AttributeName.FOCUS],
        resolve=totals[AttributeName.RESOLVE],
        agility=totals[AttributeName.AGILITY],
    )


def _score(attributes: Attributes, terms: tuple[tuple[AttributeName, float], ...]) -> float:
    return sum(getattr(attributes, attribute.value) * multiplier for attribute, multiplier in terms)


def _defence(attributes: Attributes, primary: AttributeName) -> float:
    return (
        attributes.resolve * config.DEFENCE_RESOLVE_WEIGHT
        + getattr(attributes, primary.value) * config.DEFENCE_PRIMARY_ATTRIBUTE_WEIGHT
    )


def sweep_realistic(rng: random.Random, samples: int) -> list[str]:
    rows = ["## Sweep 3 — realistic hero distributions", "", "| Model | Career level-ups | Ability | Mean success | Success SD | Mean normalised margin |", "| --- | ---: | --- | ---: | ---: | ---: |"]
    abilities = (
        ("Strike", AttributeName.MIGHT, ((AttributeName.MIGHT, 0.8), (AttributeName.RESOLVE, 0.4))),
        ("Bolt", AttributeName.FOCUS, ((AttributeName.FOCUS, 1.0),)),
        ("Shot", AttributeName.AGILITY, ((AttributeName.AGILITY, 1.0),)),
    )
    for name, roll in MODELS:
        for career_level_ups in CAREER_LEVEL_UPS:
            for ability, primary, terms in abilities:
                rates: list[float] = []
                normalized_margins: list[float] = []
                for _ in range(REALISTIC_PAIRS):
                    attacker = _hero_attributes(rng, career_level_ups)
                    defender = _hero_attributes(rng, career_level_ups)
                    attack = _score(attacker, terms)
                    defence = _defence(defender, primary)
                    outcomes = [roll(attack, defence, rng, samples) for _ in range(REALISTIC_TRIALS)]
                    rates.append(sum(outcome.succeeded for outcome in outcomes) / REALISTIC_TRIALS)
                    normalized_margins.extend(2 * outcome.margin / (attack + defence) for outcome in outcomes)
                rows.append(
                    f"| {name} | {career_level_ups} | {ability} | {statistics.mean(rates):.2%} | "
                    f"{statistics.stdev(rates):.2%} | {statistics.mean(normalized_margins):+.3f} |"
                )
    return rows


def sweep_sensitivity(rng: random.Random, trials: int) -> list[str]:
    rows = ["## Sweep 6 — N sensitivity", "", "| N | A/D | D | Success |", "| ---: | ---: | ---: | ---: |"]
    for samples in SENSITIVITY_SAMPLES:
        for ratio in RATIOS:
            for defence in MAGNITUDES:
                success, _, _ = _summary(scaled_ndx, ratio * defence, defence, rng, samples, trials)
                rows.append(f"| {samples} | {ratio:g} | {defence:g} | {success:.2%} |")
    return rows


def run(trials: int, seed: int, samples: int) -> str:
    rng = random.Random(seed)
    lines = [
        "# Contest-model comparison (simulation-only)",
        "",
        f"Seed `{seed}`; {trials:,} trials per numeric cell; scaled model N = {samples}.",
        "Legacy uses additive `3d3 - 6`; scaled uses continuous score-sized samples.",
        "",
        *sweep_parity(rng, trials, samples), "", *sweep_ratios(rng, trials, samples), "",
        *sweep_realistic(rng, samples), "", *sweep_sensitivity(rng, trials),
        "",
        "Sweeps 4–5 require the per-ability damage profiles and HP decision explicitly deferred by the patch.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=TRIALS_PER_CELL)
    parser.add_argument("--seed", type=int, default=SIMULATION_SEED)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = run(args.trials, args.seed, args.samples)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as file:
            file.write(report)
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
