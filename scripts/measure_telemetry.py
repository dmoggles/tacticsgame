from __future__ import annotations

import random
from collections import Counter
from typing import Any

from tactics_game import config
from tactics_game.engine import progression
from tactics_game.engine.session import Session
from tactics_game.models.attributes import AttributeName
from tactics_game.models.hero import ClassTrack, Hero

# Map top attribute to corresponding class track
ATTR_TO_TRACK = {
    AttributeName.MIGHT: ClassTrack.FIGHTER,
    AttributeName.FOCUS: ClassTrack.CASTER,
    AttributeName.AGILITY: ClassTrack.MARKSMAN,
    AttributeName.RESOLVE: ClassTrack.HEALER,
}


def get_top_attribute(hero: Hero) -> AttributeName:
    attrs = [
        (AttributeName.MIGHT, hero.attributes.might),
        (AttributeName.FOCUS, hero.attributes.focus),
        (AttributeName.RESOLVE, hero.attributes.resolve),
        (AttributeName.AGILITY, hero.attributes.agility),
    ]
    return max(attrs, key=lambda pair: pair[1])[0]


def get_top_class_track(hero: Hero) -> ClassTrack:
    tracks = list(hero.class_xp.items())
    return max(tracks, key=lambda pair: pair[1])[0]


def run_measurement(num_sessions: int = 50, seed: int = 42) -> dict[str, Any]:
    rng = random.Random(seed)

    total_heroes = 0
    predicted_heroes = 0
    ability_totals: dict[str, int] = {
        "Basic Strike": 0,
        "Basic Bolt": 0,
        "Basic Shot": 0,
        "Basic Mend": 0,
    }
    level_totals: list[int] = []
    session_logs: list[dict[str, Any]] = []
    wave_ended_counter: Counter[int] = Counter()
    full_wins = 0

    for s_idx in range(1, num_sessions + 1):
        roster = [
            progression.create_starting_hero(
                f"Hero {i + 1}",
                position=progression.Position(1, 2 + i * 3),
                is_player_controlled=True,
                rng=rng,
            )
            for i in range(config.ROSTER_SIZE)
        ]
        session = Session(roster=roster, rng=rng)
        session.run_to_completion()

        # Calculate wave ended on:
        # If won full session, ended after wave config.SESSION_BATTLE_COUNT (10)
        # If lost, ended on wave (session.battles_won + 1)
        if session.result == "won":
            ended_on_wave = config.SESSION_BATTLE_COUNT
            full_wins += 1
        else:
            ended_on_wave = session.battles_won + 1

        wave_ended_counter[ended_on_wave] += 1

        session_logs.append(
            {
                "session": s_idx,
                "result": session.result,
                "battles_won": session.battles_won,
                "ended_on_wave": ended_on_wave,
            }
        )

        for hero in roster:
            total_heroes += 1
            top_attr = get_top_attribute(hero)
            top_track = get_top_class_track(hero)
            expected_track = ATTR_TO_TRACK[top_attr]

            if top_track == expected_track:
                predicted_heroes += 1

            for name, count in hero.ability_uses.items():
                ability_totals[name] = ability_totals.get(name, 0) + count

            level_totals.append(hero.level)

    predictability_rate = (predicted_heroes / total_heroes) if total_heroes > 0 else 0.0
    avg_level = sum(level_totals) / len(level_totals) if level_totals else 0.0
    avg_level_ups = avg_level - 1.0

    return {
        "num_sessions": num_sessions,
        "total_heroes": total_heroes,
        "predicted_heroes": predicted_heroes,
        "predictability_rate": predictability_rate,
        "ability_totals": ability_totals,
        "avg_level_ups_per_hero": avg_level_ups,
        "full_wins": full_wins,
        "full_win_rate": full_wins / num_sessions,
        "wave_ended_counter": wave_ended_counter,
        "session_logs": session_logs,
    }


def print_post_run_report(results: dict[str, Any]) -> None:
    num_sessions = results["num_sessions"]
    print("=" * 65)
    print(f"       POST-RUN REPORT: {num_sessions} AUTO-RUN SESSIONS")
    print("=" * 65)

    print("\n--- OVERALL SUMMARY ---")
    print(f"Total Sessions Run:          {num_sessions}")
    print(f"Full Session Victories:      {results['full_wins']} ({results['full_win_rate'] * 100:.1f}%)")
    print(f"Total Heroes Analyzed:       {results['total_heroes']}")
    print(
        f"Predictability Rate:         {results['predictability_rate'] * 100:.1f}% "
        f"({results['predicted_heroes']}/{results['total_heroes']} heroes matched top stat to top class)"
    )
    print(f"Average Level-Ups per Hero:  {results['avg_level_ups_per_hero']:.2f}")

    print("\n--- WAVE ENDED BREAKDOWN ---")
    print(f"{'Wave / Battle':<15} | {'Sessions Ended Here':<22} | {'Percentage':<10}")
    print("-" * 55)
    for wave in range(1, config.SESSION_BATTLE_COUNT + 1):
        count = results["wave_ended_counter"].get(wave, 0)
        pct = (count / num_sessions) * 100
        label = f"Wave {wave} (Won All)" if wave == config.SESSION_BATTLE_COUNT and count == results["full_wins"] else f"Wave {wave}"
        print(f"{label:<15} | {count:<22} | {pct:>8.1f}%")

    print("\n--- PER-ABILITY USAGE COUNTS ---")
    for name, count in results["ability_totals"].items():
        print(f"  {name:<15}: {count:>5} uses")

    print("\n--- INDIVIDUAL SESSION OUTCOMES ---")
    print(f"{'Session #':<10} | {'Outcome':<10} | {'Battles Won':<12} | {'Ended On Wave':<15}")
    print("-" * 55)
    for log in results["session_logs"]:
        outcome_str = log["result"].upper()
        print(
            f"Session {log['session']:<2} | {outcome_str:<10} | "
            f"{log['battles_won']:<12} | Wave {log['ended_on_wave']:<10}"
        )
    print("=" * 65)


if __name__ == "__main__":
    results = run_measurement(50)
    print_post_run_report(results)
