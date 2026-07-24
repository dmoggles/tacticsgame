"""Parallel headless measurements for Phase 3 Step 7.

Runs paired, independent seeded sessions for progression/Track-2 metrics and
live-engine contest cells for hit and damage curves.  Results are emitted as
one Markdown report so balance changes can be compared against the same input
seeds rather than anecdotal battles.
"""

from __future__ import annotations

import argparse
import multiprocessing
import random
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from tactics_game import config
from tactics_game.engine import progression, resolution, roster
from tactics_game.engine.session import Session
from tactics_game.models.attributes import AffinityVector, AttributeName, Attributes
from tactics_game.models.grid import Position
from tactics_game.models.hero import ClassTrack, Hero

ATTR_TO_TRACK = {
    AttributeName.MIGHT: ClassTrack.FIGHTER,
    AttributeName.FOCUS: ClassTrack.CASTER,
    AttributeName.AGILITY: ClassTrack.MARKSMAN,
    AttributeName.RESOLVE: ClassTrack.HEALER,
}
TRACK_TO_ATTR = {track: attribute for attribute, track in ATTR_TO_TRACK.items()}
ABILITY_SCALING = {
    "Strike": [resolution.ScalingTerm("might", 0.8), resolution.ScalingTerm("resolve", 0.4)],
    "Bolt": [resolution.ScalingTerm("focus", 1.0)],
    "Shot": [resolution.ScalingTerm("agility", 1.0)],
}
PROFILES = {
    "Strike": resolution.DamageProfile(4.30, 0.24, 0.50, 0.50, 0.35, 1.20),
    "Bolt": resolution.DamageProfile(2.85, 0.18, 0.65, 0.70, 0.20, 1.40),
    "Shot": resolution.DamageProfile(2.85, 0.12, 0.75, 0.20, 0.60, 1.00),
}
ATTRIBUTE_LEVELS = (4, 8, 16, 32)
DEFENCE_MULTIPLIERS = (0.67, 1.0, 1.5, 2.0)


def _top_attribute(hero: Hero) -> AttributeName:
    return max(
        ((name, getattr(hero.attributes, name.value)) for name in AttributeName), key=lambda item: item[1]
    )[0]


def _top_track(hero: Hero) -> ClassTrack:
    return max(hero.class_xp.items(), key=lambda item: item[1])[0]


def _manual_attribute_for(hero: Hero) -> AttributeName:
    """Put the manual point into the attribute aligned with current Track 2.

    Before any ability use, all tracks tie; use the hero's current top
    attribute as the deterministic, identity-respecting tie-break instead of
    arbitrarily favouring the first enum member.
    """
    top_xp = max(hero.class_xp.values())
    leaders = [track for track, xp in hero.class_xp.items() if xp == top_xp]
    if len(leaders) != 1:
        return _top_attribute(hero)
    return TRACK_TO_ATTR[leaders[0]]


def _resolve_manual_points(heroes: list[Hero], rng: random.Random) -> None:
    for hero in heroes:
        while hero.pending_level_ups > 0:
            progression.resolve_manual_allocation(hero, _manual_attribute_for(hero), rng)


def _session_worker(seed: int) -> dict:
    rng = random.Random(seed)
    heroes = [
        progression.create_starting_hero(f"Hero {index + 1}", Position(1, 2 + index * 3), True, rng)
        for index in range(config.ROSTER_SIZE)
    ]
    starting_attributes = [
        {attribute.value: getattr(hero.attributes, attribute.value) for attribute in AttributeName}
        for hero in heroes
    ]
    session = Session(roster=heroes, rng=rng)
    timeline: list[dict] = []
    while not session.is_over:
        if session.current_battle is None:
            _resolve_manual_points(heroes, rng)
            session.begin_battle(roster.select_balanced_squad(heroes))
        assert session.current_battle is not None
        session.current_battle.run_to_completion()
        # Resolve fielded heroes' newly earned manual points before advance;
        # a final session advance may otherwise apply its decline fallback.
        _resolve_manual_points(heroes, rng)
        session.advance()
        timeline.append(
            {
                "battle": len(timeline) + 1,
                "mean_level": statistics.fmean(hero.level for hero in heroes),
                "mean_class_xp": statistics.fmean(sum(hero.class_xp.values()) for hero in heroes),
                "ability_uses": Counter(
                    {name: sum(hero.ability_uses.get(name, 0) for hero in heroes) for name in _ability_names()}
                ),
            }
        )
    hero_reports = [
        {
            "top_attribute": _top_attribute(hero).value,
            "top_track": _top_track(hero).value,
            "class_xp": {track.value: amount for track, amount in hero.class_xp.items()},
            "ability_uses": {name: hero.ability_uses.get(name, 0) for name in _ability_names()},
            "level": hero.level,
            "max_hp": hero.max_hp,
            "manual_allocations": list(hero.manual_allocations),
            "starting_attributes": starting,
            "final_attributes": {
                attribute.value: getattr(hero.attributes, attribute.value) for attribute in AttributeName
            },
        }
        for hero, starting in zip(heroes, starting_attributes, strict=True)
    ]
    return {"won": session.result == "won", "heroes": hero_reports, "timeline": timeline}


def _ability_names() -> tuple[str, ...]:
    return ("Basic Strike", "Basic Bolt", "Basic Shot", "Basic Mend")


def _hero(level: int, primary: str) -> Hero:
    values = {name.value: level for name in AttributeName}
    values[primary] = level
    return Hero(
        name="measurement", attributes=Attributes(**values),
        hidden_affinity=AffinityVector(0.25, 0.25, 0.25, 0.25),
        abilities=progression.create_basic_kit(), max_hp=1000, current_hp=1000,
        position=Position(0, 0), is_player_controlled=True,
    )


def _curve_worker(cell: tuple[str, int, float, int, int]) -> dict:
    ability, level, defence_multiplier, trials, seed = cell
    scaling = ABILITY_SCALING[ability]
    primary = resolution.primary_attack_attribute(scaling)
    attacker = _hero(level, primary)
    defender = _hero(max(1, round(level * defence_multiplier)), primary)
    rng = random.Random(seed)
    damages = []
    successes = 0
    first = None
    for _ in range(trials):
        contest = resolution.resolve_contest(attacker, defender, scaling, rng)
        first = contest
        damage = resolution.damage_from_contest(contest, PROFILES[ability])
        successes += damage > 0
        damages.append(damage)
    assert first is not None
    landed = [damage for damage in damages if damage > 0]
    return {
        "ability": ability, "level": level, "defence_multiplier": defence_multiplier,
        "attack": first.attack_score, "defence": first.defence_score,
        "hit": successes / trials, "damage": statistics.fmean(damages),
        "landed_damage": statistics.fmean(landed) if landed else 0.0,
    }


def _healing_worker(cell: tuple[int, int, int]) -> dict:
    level, trials, seed = cell
    caster = _hero(level, "resolve")
    mend = next(ability for ability in caster.abilities if ability.name == "Basic Mend")
    rng = random.Random(seed)
    amounts = []
    for _ in range(trials):
        target = _hero(level, "resolve")
        target.current_hp = 1
        amounts.append(mend.effect(caster, target, rng).healing)
    return {
        "level": level,
        "mean": statistics.fmean(amounts),
        "minimum": min(amounts),
        "maximum": max(amounts),
    }


def _parallel(function, jobs: list, workers: int) -> list:
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(function, job) for job in jobs]
        results = []
        for completed, future in enumerate(as_completed(futures), start=1):
            results.append(future.result())
            if completed % 10 == 0 or completed == len(futures):
                print(f"  collected {completed}/{len(futures)} jobs", flush=True)
        return results


def run(sessions: int, trials: int, seed: int, workers: int) -> str:
    started = perf_counter()
    session_results = _parallel(_session_worker, [seed + index for index in range(sessions)], workers)
    curve_jobs = [
        (ability, level, multiplier, trials, seed + 100_000 + index)
        for index, (ability, level, multiplier) in enumerate(
            (item for item in ((ability, level, multiplier) for ability in ABILITY_SCALING for level in ATTRIBUTE_LEVELS for multiplier in DEFENCE_MULTIPLIERS))
        )
    ]
    curves = _parallel(_curve_worker, curve_jobs, workers)
    healing = _parallel(
        _healing_worker,
        [(level, trials, seed + 200_000 + index) for index, level in enumerate(ATTRIBUTE_LEVELS)],
        workers,
    )
    elapsed = perf_counter() - started
    heroes = [hero for result in session_results for hero in result["heroes"]]
    predicted = sum(
        ATTR_TO_TRACK[AttributeName(hero["top_attribute"])].value == hero["top_track"]
        for hero in heroes
    )
    tracks = Counter(hero["top_track"] for hero in heroes)
    ability_uses = Counter({name: sum(hero["ability_uses"][name] for hero in heroes) for name in _ability_names()})
    class_xp = Counter({track.value: sum(hero["class_xp"][track.value] for hero in heroes) for track in ClassTrack})
    manual_points = Counter(
        allocation for hero in heroes for allocation in hero["manual_allocations"] if allocation is not None
    )
    total_level_up_points = Counter(
        {
            attribute.value: sum(
                hero["final_attributes"][attribute.value] - hero["starting_attributes"][attribute.value]
                for hero in heroes
            )
            for attribute in AttributeName
        }
    )
    hp_by_level: defaultdict[int, list[int]] = defaultdict(list)
    hp_by_track: defaultdict[str, list[int]] = defaultdict(list)
    for hero in heroes:
        hp_by_level[hero["level"]].append(hero["max_hp"])
        hp_by_track[hero["top_track"]].append(hero["max_hp"])
    trends: defaultdict[int, list[dict]] = defaultdict(list)
    for result in session_results:
        for point in result["timeline"]:
            trends[point["battle"]].append(point)
    lines = [
        "# Phase 3 Step 7 measurements", "",
        f"{sessions} paired seeded sessions; {trials:,} trials per live-engine curve cell; {workers} workers.",
        f"Wall-clock collection time: {elapsed:.1f}s.", "",
        "**Methodology.** Each session receives a distinct deterministic seed and runs independently through the live session, battle, AI, and contested-resolution paths; worker processes collect those paired seed results in parallel, so aggregation changes runtime rather than outcomes. Before every battle, the headless policy fields the two roster heroes with the fewest prior fielded battles, breaking ties by roster order; this deliberately measures balanced rotation rather than a strongest-team policy. Starting attributes are synthesized from each hero's hidden affinity. Each pending free level-up point is assigned to the attribute aligned with that hero's current leading specialization track (Fighter→Might, Caster→Focus, Marksman→Agility, Healer→Resolve); ties before specialization use the current top attribute. Progression and specialization metrics are roster-level observations after every completed battle and at session end. Each curve cell repeatedly invokes the live contest and normalised-margin damage helpers against synthetic attribute/defence pairings; to-hit is successful actions divided by trials, damage/action includes misses, and landed damage is conditional on success.", "",
        "## Session and specialization outcomes", "",
        f"- Full-session win rate: {sum(result['won'] for result in session_results) / sessions:.1%}",
        f"- Top-attribute → top-track predictability: {predicted / len(heroes):.1%} ({predicted}/{len(heroes)}); pre-Phase-3 comparison: 57.25%.",
        f"- Fighter top-track share: {tracks['fighter'] / len(heroes):.1%}; this is reported separately because Strike's Might+Resolve scaling is a known confound.", "",
        "| Track | XP collected | Heroes ending top-track |", "| --- | ---: | ---: |",
        *[f"| {track.value} | {class_xp[track.value]} | {tracks[track.value]} |" for track in ClassTrack], "",
        "| Ability | Uses |", "| --- | ---: |", *[f"| {name} | {ability_uses[name]} |" for name in _ability_names()], "",
        "## Level-up attribute allocation", "",
        "Automatic points are the final attribute gain minus recorded user-directed points; starting synthesis is excluded.", "",
        "| Attribute | Affinity-driven automatic | User-chosen specialization | Total level-up gain |", "| --- | ---: | ---: | ---: |",
        *[
            f"| {attribute.value} | {total_level_up_points[attribute.value] - manual_points[attribute.value]} | "
            f"{manual_points[attribute.value]} | {total_level_up_points[attribute.value]} |"
            for attribute in AttributeName
        ], "",
        "## Final max-HP distribution", "",
        "| Level | Heroes | Min HP | Mean HP | Max HP |", "| ---: | ---: | ---: | ---: | ---: |",
        *[
            f"| {level} | {len(values)} | {min(values)} | {statistics.fmean(values):.2f} | {max(values)} |"
            for level, values in sorted(hp_by_level.items())
        ], "",
        "| Preferred track | Heroes | Min HP | Mean HP | Max HP |", "| --- | ---: | ---: | ---: | ---: |",
        *[
            f"| {track} | {len(values)} | {min(values)} | {statistics.fmean(values):.2f} | {max(values)} |"
            for track, values in sorted(hp_by_track.items())
        ], "",
        "## Level and class-XP trend by completed battle", "",
        "| Battle | Mean level | Mean class XP |", "| ---: | ---: | ---: |",
        *[f"| {battle} | {statistics.fmean(point['mean_level'] for point in points):.2f} | {statistics.fmean(point['mean_class_xp'] for point in points):.1f} |" for battle, points in sorted(trends.items())], "",
        "## Live to-hit and damage curves", "",
        "Damage is mean damage per action; landed damage is conditional on a hit. Actual score ratio is shown because Resolve contributes to defence.", "",
        "| Ability | Attribute level | Defence multiplier | Attack | Defence | To-hit | Damage/action | Landed damage |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        *[f"| {row['ability']} | {row['level']} | {row['defence_multiplier']:.2f} | {row['attack']:.1f} | {row['defence']:.1f} | {row['hit']:.1%} | {row['damage']:.2f} | {row['landed_damage']:.2f} |" for row in curves],
        "",
        "## Automatic healing summary", "",
        "Basic Mend has no to-hit roll; values below are its live synthetic-quality outcome distribution against an uncapped injured ally.", "",
        "| Resolve level | Mean healing | Min | Max |", "| ---: | ---: | ---: | ---: |",
        *[f"| {row['level']} | {row['mean']:.2f} | {row['minimum']} | {row['maximum']} |" for row in healing],
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=200)
    parser.add_argument("--trials", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=20260724)
    parser.add_argument("--workers", type=int, default=min(8, multiprocessing.cpu_count()))
    parser.add_argument("--output", type=Path, default=Path("docs/phase3_step7_measurements.md"))
    args = parser.parse_args()
    args.output.write_text(run(args.sessions, args.trials, args.seed, args.workers), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
