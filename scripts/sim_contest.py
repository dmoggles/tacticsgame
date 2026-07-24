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
ATTACKER_ADVANTAGE_CANDIDATES = (1.20, 1.25, 1.30, 1.35, 1.40)
ATTACKER_ADVANTAGE = 1.30
CLASSLESS_HP_BASE = 12.0
CLASSLESS_HP_PER_RESOLVE = 0.6


@dataclass(frozen=True)
class DamageProfile:
    name: str
    baseline_quality: float
    margin_sensitivity: float
    quality_floor: float
    quality_cap: float


@dataclass(frozen=True)
class AbilityModel:
    name: str
    primary: AttributeName
    terms: tuple[tuple[AttributeName, float], ...]
    profile: DamageProfile
    base_flat: float
    base_per_attack: float
    automatic_variance_width: float | None = None


RELIABLE = DamageProfile("reliable", 0.75, 0.20, 0.60, 1.00)
# Revised from the doc/10 first guess of 0.40 after Sweep 5 showed it had a
# much lower mean than reliable. 0.65 keeps the intended high spread while
# aligning expected landed quality at parity.
SWINGY = DamageProfile("swingy", 0.65, 0.70, 0.20, 1.40)
STANDARD = DamageProfile("standard", 0.50, 0.50, 0.35, 1.20)

ABILITY_MODELS = (
    AbilityModel(
        "Strike", AttributeName.MIGHT,
        ((AttributeName.MIGHT, 0.8), (AttributeName.RESOLVE, 0.4)), STANDARD, 4.3, 0.24,
    ),
    AbilityModel("Bolt", AttributeName.FOCUS, ((AttributeName.FOCUS, 1.0),), SWINGY, 2.85, 0.18),
    AbilityModel("Shot", AttributeName.AGILITY, ((AttributeName.AGILITY, 1.0),), RELIABLE, 2.85, 0.12),
    AbilityModel(
        "Mend", AttributeName.RESOLVE, ((AttributeName.RESOLVE, 0.5),), RELIABLE, 2.0, 0.50,
        automatic_variance_width=0.25,
    ),
)


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


def sweep_advantaged_ratios(rng: random.Random, trials: int, samples: int) -> list[str]:
    rows = ["## Sweep 2b — advantaged fixed-ratio invariance", "", "| A/D | D | Success |", "| ---: | ---: | ---: |"]
    for ratio in RATIOS:
        for defence in MAGNITUDES:
            success, _, _ = _summary(
                scaled_ndx, ATTACKER_ADVANTAGE * ratio * defence, defence, rng, samples, trials
            )
            rows.append(f"| {ratio:g} | {defence:g} | {success:.2%} |")
    return rows


def sweep_attacker_advantage(rng: random.Random, trials: int, samples: int) -> list[str]:
    rows = [
        "## Attacker-advantage calibration",
        "",
        "| Attack multiplier | Parity success | 1.5× success | 1.5× disadvantage success |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for multiplier in ATTACKER_ADVANTAGE_CANDIDATES:
        parity, _, _ = _summary(scaled_ndx, multiplier, 1.0, rng, samples, trials)
        advantage, _, _ = _summary(scaled_ndx, multiplier * 1.5, 1.0, rng, samples, trials)
        disadvantage, _, _ = _summary(scaled_ndx, multiplier, 1.5, rng, samples, trials)
        rows.append(
            f"| {multiplier:.2f} | {parity:.2%} | {advantage:.2%} | {disadvantage:.2%} |"
        )
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


def _classless_hp(attributes: Attributes) -> float:
    return CLASSLESS_HP_BASE + CLASSLESS_HP_PER_RESOLVE * attributes.resolve


def _damage(
    attack: float,
    defence: float,
    margin: float,
    profile: DamageProfile,
    base_flat: float,
    base_per_attack: float,
) -> float:
    normalized_margin = 2 * margin / (attack + defence) if attack + defence > 0 else 0.0
    quality = profile.baseline_quality + profile.margin_sensitivity * normalized_margin
    clamped_quality = min(profile.quality_cap, max(profile.quality_floor, quality))
    return (base_flat + base_per_attack * attack) * clamped_quality


def _automatic_damage(attack: float, model: AbilityModel, rng: random.Random) -> float:
    assert model.automatic_variance_width is not None
    synthetic_margin = rng.uniform(-model.automatic_variance_width, model.automatic_variance_width)
    quality = model.profile.baseline_quality + model.profile.margin_sensitivity * synthetic_margin
    clamped_quality = min(model.profile.quality_cap, max(model.profile.quality_floor, quality))
    return (model.base_flat + model.base_per_attack * attack) * clamped_quality


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


def sweep_realistic(
    rng: random.Random, samples: int, pairs: int, trials: int
) -> list[str]:
    rows = [
        "## Sweep 3 — realistic hero distributions",
        "",
        "| Model | Player K | Enemy K | Ability | Mean success | Success SD | Mean normalised margin |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    abilities = (
        ("Strike", AttributeName.MIGHT, ((AttributeName.MIGHT, 0.8), (AttributeName.RESOLVE, 0.4))),
        ("Bolt", AttributeName.FOCUS, ((AttributeName.FOCUS, 1.0),)),
        ("Shot", AttributeName.AGILITY, ((AttributeName.AGILITY, 1.0),)),
    )
    for name, roll in MODELS:
        for player_level_ups in CAREER_LEVEL_UPS:
            enemy_level_ups_values = sorted(
                {max(0, player_level_ups - lag) for lag in (0, 5, 10)}, reverse=True
            )
            for enemy_level_ups in enemy_level_ups_values:
                for ability, primary, terms in abilities:
                    rates: list[float] = []
                    normalized_margins: list[float] = []
                    for _ in range(pairs):
                        attacker = _hero_attributes(rng, player_level_ups)
                        defender = _hero_attributes(rng, enemy_level_ups)
                        attack = _score(attacker, terms)
                        defence = _defence(defender, primary)
                        outcomes = [roll(attack, defence, rng, samples) for _ in range(trials)]
                        rates.append(sum(outcome.succeeded for outcome in outcomes) / trials)
                        normalized_margins.extend(
                            2 * outcome.margin / (attack + defence) for outcome in outcomes
                        )
                    rows.append(
                        f"| {name} | {player_level_ups} | {enemy_level_ups} | {ability} | "
                        f"{statistics.mean(rates):.2%} | {statistics.stdev(rates):.2%} | "
                        f"{statistics.mean(normalized_margins):+.3f} |"
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


def sweep_ttk(rng: random.Random, samples: int, pairs: int, trials: int) -> list[str]:
    rows = [
        "## Sweep 4 — classless time to kill",
        "",
        "| Model | K | Ability | Mean TTK actions | Best-ability TTK actions |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    offensive_abilities = tuple(model for model in ABILITY_MODELS if model.automatic_variance_width is None)
    for model_name, roll in MODELS:
        for career_level_ups in CAREER_LEVEL_UPS:
            total_hp = 0.0
            total_damage: dict[str, float] = {model.name: 0.0 for model in offensive_abilities}
            total_best_damage = 0.0
            for _ in range(pairs):
                attacker = _hero_attributes(rng, career_level_ups)
                defender = _hero_attributes(rng, career_level_ups)
                defender_hp = _classless_hp(defender)
                total_hp += defender_hp
                expected_damages: dict[str, float] = {}
                for ability in offensive_abilities:
                    attack = _score(attacker, ability.terms)
                    defence = _defence(defender, ability.primary)
                    damages = []
                    for _ in range(trials):
                        contest = roll(attack, defence, rng, samples)
                        damages.append(
                            _damage(
                                attack, defence, contest.margin, ability.profile,
                                ability.base_flat, ability.base_per_attack,
                            ) if contest.succeeded else 0.0
                        )
                    expected_damage = statistics.mean(damages)
                    expected_damages[ability.name] = expected_damage
                    total_damage[ability.name] += expected_damage
                total_best_damage += max(expected_damages.values())
            for ability in offensive_abilities:
                mean_hp = total_hp / pairs
                mean_damage = total_damage[ability.name] / pairs
                mean_best_damage = total_best_damage / pairs
                rows.append(
                    f"| {model_name} | {career_level_ups} | {ability.name} | "
                    f"{mean_hp / mean_damage:.2f} | {mean_hp / mean_best_damage:.2f} |"
                )
    return rows


def sweep_damage_profiles(rng: random.Random, samples: int, trials: int) -> list[str]:
    rows = [
        "## Sweep 5 — landed-damage profile distributions",
        "",
        "| Profile | Career proxy | Mean | SD | P10 | P50 | P90 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for career_proxy, score in (("K=0", 8.0), ("K=20", 28.0)):
        for profile in (RELIABLE, SWINGY, STANDARD):
            landed: list[float] = []
            while len(landed) < trials:
                contest = scaled_ndx(score, score, rng, samples)
                if contest.succeeded:
                    landed.append(_damage(score, score, contest.margin, profile, 10.0, 0.0))
            rows.append(
                f"| {profile.name} | {career_proxy} | {statistics.mean(landed):.2f} | "
                f"{statistics.stdev(landed):.2f} | {_percentile(landed, 0.1):.2f} | "
                f"{_percentile(landed, 0.5):.2f} | {_percentile(landed, 0.9):.2f} |"
            )
    return rows


def run(
    trials: int, seed: int, samples: int, realistic_pairs: int, realistic_trials: int
) -> str:
    rng = random.Random(seed)
    lines = [
        "# Contest-model comparison (simulation-only)",
        "",
        f"Seed `{seed}`; {trials:,} trials per numeric cell; scaled model N = {samples}.",
        "Legacy uses additive `3d3 - 6`; scaled uses continuous score-sized samples.",
        "",
        *sweep_parity(rng, trials, samples), "", *sweep_ratios(rng, trials, samples), "",
        *sweep_attacker_advantage(rng, trials, samples), "",
        *sweep_realistic(rng, samples, realistic_pairs, realistic_trials), "",
        *sweep_ttk(rng, samples, realistic_pairs, realistic_trials), "",
        *sweep_damage_profiles(rng, samples, trials), "",
        *sweep_sensitivity(rng, trials),
        "",
        "Sweeps 4–5 use the first-pass placeholder profiles and classless HP formula from docs/10.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=TRIALS_PER_CELL)
    parser.add_argument("--seed", type=int, default=SIMULATION_SEED)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--realistic-pairs", type=int, default=REALISTIC_PAIRS)
    parser.add_argument("--realistic-trials", type=int, default=REALISTIC_TRIALS)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = run(
        args.trials, args.seed, args.samples, args.realistic_pairs, args.realistic_trials
    )
    if args.output:
        with open(args.output, "w", encoding="utf-8") as file:
            file.write(report)
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
