from __future__ import annotations

import random

from .. import config
from ..models.ability import Ability
from ..models.attributes import AffinityVector, AttributeName, Attributes
from ..models.grid import Position
from ..models.hero import ClassTrack, Hero
from . import ability_library, class_track_library


def generate_hidden_affinity(rng: random.Random) -> AffinityVector:
    """Symmetric-Dirichlet-distributed weights over the four attributes.

    Built from independent Gamma(alpha, 1) draws normalized to sum to 1,
    the standard construction for a Dirichlet sample without requiring a
    numpy dependency. Concentration parameter set by config.AFFINITY_CONCENTRATION.
    """
    samples = [rng.gammavariate(config.AFFINITY_CONCENTRATION, 1.0) for _ in AttributeName]
    total = sum(samples)
    weights = [sample / total for sample in samples]
    return AffinityVector(
        might=weights[0], focus=weights[1], resolve=weights[2], agility=weights[3]
    )


def allocate_points(
    affinity: AffinityVector, num_points: int, rng: random.Random
) -> dict[AttributeName, int]:
    """Distribute `num_points` across attributes via weighted-random draws.

    Each point is an independent weighted sample against the hero's hidden
    affinity, not a proportional split — this preserves run-to-run variance
    between heroes with similar affinity vectors.
    """
    names_and_weights = affinity.as_weights()
    names = [name for name, _ in names_and_weights]
    weights = [weight for _, weight in names_and_weights]
    counts: dict[AttributeName, int] = {name: 0 for name in names}
    for name in rng.choices(names, weights=weights, k=num_points):
        counts[name] += 1
    return counts


def synthesize_starting_attributes(
    affinity: AffinityVector, rng: random.Random
) -> Attributes:
    """5 simulated level-ups of 3 affinity-weighted points, atop base values."""
    totals: dict[AttributeName, int] = {
        name: config.BASE_ATTRIBUTE_VALUE for name in AttributeName
    }
    for _ in range(config.SYNTHESIS_LEVEL_UPS):
        allocation = allocate_points(affinity, config.POINTS_PER_LEVEL_UP, rng)
        for name, count in allocation.items():
            totals[name] += count
    return Attributes(
        might=totals[AttributeName.MIGHT],
        focus=totals[AttributeName.FOCUS],
        resolve=totals[AttributeName.RESOLVE],
        agility=totals[AttributeName.AGILITY],
    )


def compute_max_hp(attributes: Attributes) -> int:
    """Derived HP, isolated here so the formula is trivial to revise later."""
    return config.BASE_HP + (attributes.might + attributes.resolve) * config.HP_ATTRIBUTE_MULTIPLIER


def create_basic_kit() -> list[Ability]:
    """The classless Tier 0 kit every hero starts with, filling all 4 slots.

    Ability data lives in data/abilities.yaml — see engine/ability_library.py.
    """
    return ability_library.load_abilities()


def create_starting_hero(
    name: str, position: Position, is_player_controlled: bool, rng: random.Random
) -> Hero:
    """Level-0 hero synthesis: hidden affinity + 5 simulated level-ups.

    No player influence — pure roster generation.
    """
    affinity = generate_hidden_affinity(rng)
    attributes = synthesize_starting_attributes(affinity, rng)
    max_hp = compute_max_hp(attributes)
    return Hero(
        name=name,
        attributes=attributes,
        hidden_affinity=affinity,
        abilities=create_basic_kit(),
        max_hp=max_hp,
        current_hp=max_hp,
        position=position,
        is_player_controlled=is_player_controlled,
    )


def compute_enemy_squad_size(battle_index: int) -> int:
    """Enemy count curve: flat at config.FIELDED_SQUAD_SIZE (2 enemies) across all battles.
    3-vs-2 mode disabled per user directive.
    """
    return config.FIELDED_SQUAD_SIZE


def generate_enemy_squad(rng: random.Random, battle_index: int = 0) -> list[Hero]:
    """A fresh enemy squad for one battle in a session.

    Enemy count escalates from 2 to 3 at battle 6 (battle_index 5) via
    compute_enemy_squad_size. Early battles (0..1) synthesize with slightly fewer
    level-ups (3-4 vs 5) to soften early difficulty so sessions reach the back half.
    """
    enemy_count = compute_enemy_squad_size(battle_index)
    level_ups = 2 if battle_index == 0 else (3 if battle_index == 1 else config.SYNTHESIS_LEVEL_UPS)
    row_step = max(2, config.GRID_HEIGHT // (enemy_count + 1))
    squad: list[Hero] = []
    for i in range(enemy_count):
        affinity = generate_hidden_affinity(rng)
        totals: dict[AttributeName, int] = {name: config.BASE_ATTRIBUTE_VALUE for name in AttributeName}
        for _ in range(level_ups):
            allocation = allocate_points(affinity, config.POINTS_PER_LEVEL_UP, rng)
            for name, count in allocation.items():
                totals[name] += count
        attributes = Attributes(
            might=totals[AttributeName.MIGHT],
            focus=totals[AttributeName.FOCUS],
            resolve=totals[AttributeName.RESOLVE],
            agility=totals[AttributeName.AGILITY],
        )
        max_hp = compute_max_hp(attributes)
        hero = Hero(
            name=f"Enemy {i + 1}",
            attributes=attributes,
            hidden_affinity=affinity,
            abilities=create_basic_kit(),
            max_hp=max_hp,
            current_hp=max_hp,
            position=Position(config.GRID_WIDTH - 2, 2 + i * row_step),
            is_player_controlled=False,
        )
        squad.append(hero)
    return squad


def grant_xp(hero: Hero, amount: int, rng: random.Random) -> None:
    """Grant Track 1 XP, applying every level-up crossed (loop for big jumps)."""
    hero.xp += amount
    while hero.xp >= config.XP_LEVEL_THRESHOLD:
        hero.xp -= config.XP_LEVEL_THRESHOLD
        _level_up(hero, rng)


def _apply_attribute_points(hero: Hero, allocation: dict[AttributeName, int]) -> None:
    old_max_hp = hero.max_hp
    hero.attributes = hero.attributes.with_bonus(
        might=allocation[AttributeName.MIGHT],
        focus=allocation[AttributeName.FOCUS],
        resolve=allocation[AttributeName.RESOLVE],
        agility=allocation[AttributeName.AGILITY],
    )
    hero.max_hp = compute_max_hp(hero.attributes)
    hero.current_hp += hero.max_hp - old_max_hp


def _level_up(hero: Hero, rng: random.Random) -> None:
    """Applies a level-up's automatic, affinity-weighted points immediately
    (docs/04_phase2b_definition.md section 5: "the remaining 2 ... as
    currently implemented"). The manual point is deliberately deferred —
    queued via `pending_level_ups` and resolved later by
    `resolve_manual_allocation`, typically on the between-battle screen,
    never mid-battle."""
    auto_points = config.POINTS_PER_LEVEL_UP - config.MANUAL_ALLOCATION_POINTS_PER_LEVEL_UP
    allocation = allocate_points(hero.hidden_affinity, auto_points, rng)
    _apply_attribute_points(hero, allocation)
    hero.level += 1
    hero.pending_level_ups += 1


def resolve_manual_allocation(
    hero: Hero, attribute: AttributeName | None, rng: random.Random
) -> None:
    """Resolve one pending level-up's manual point (docs/04_phase2b_definition.md
    section 5). `attribute=None` means the player declined/skipped — the
    point is allocated by affinity like the others rather than forfeited.
    A multi-level jump queues several pending level-ups at once; call this
    once per pending level-up, in sequence.
    """
    if hero.pending_level_ups <= 0:
        raise ValueError(f"{hero.name} has no pending level-up to resolve")
    manual_points = config.MANUAL_ALLOCATION_POINTS_PER_LEVEL_UP
    if attribute is None:
        allocation = allocate_points(hero.hidden_affinity, manual_points, rng)
        hero.manual_allocations.append(None)
    else:
        allocation = {name: 0 for name in AttributeName}
        allocation[attribute] = manual_points
        hero.manual_allocations.append(attribute.value)
    _apply_attribute_points(hero, allocation)
    hero.pending_level_ups -= 1


def compute_enemy_strength(enemy_squad: list[Hero]) -> int:
    """Sum of enemy levels — the per-battle XP pool's basis.

    Isolated in its own function since this is exactly the number most
    likely to be revised as balance work continues (see
    docs/03_phase2a_definition.md section 5); sum-of-attributes is an
    equally valid alternative the doc calls out, just not the one chosen
    here.
    """
    return sum(enemy.level for enemy in enemy_squad)


def compute_battle_xp_pool(enemy_squad: list[Hero]) -> int:
    """Total Track 1 XP pool awarded on battle victory."""
    return config.XP_POOL_PER_STRENGTH_POINT * compute_enemy_strength(enemy_squad)


def award_battle_xp(
    fielded: list[Hero],
    enemy_squad: list[Hero],
    rng: random.Random,
) -> None:
    """Track 1 XP as a per-battle pool, split evenly across `fielded`.

    Downed heroes need no special-casing: they're never removed from
    their squad list, so they're still in `fielded` and receive a full
    share like anyone else — they were present. `Battle` (the only caller)
    only ever knows about the fielded squad, not a roster — bench-bonus XP
    is a separate concern only `Session` has the information to award; see
    `award_bench_bonus_xp` and docs/adr/0006-roster-and-squad-selection.md.
    """
    pool = compute_battle_xp_pool(enemy_squad)
    if fielded:
        share = pool // len(fielded)
        for hero in fielded:
            grant_xp(hero, share, rng)


def award_bench_bonus_xp(
    benched: list[Hero],
    enemy_squad: list[Hero],
    rng: random.Random,
    bench_multiplier: float = config.BENCH_XP_BONUS_MULTIPLIER,
) -> None:
    """Bonus Track 1 XP for benched heroes, on top of (not carved out of)
    the fielded pool computed from the same battle's enemy squad.

    Called by `Session` after a battle resolves, not by `Battle` itself —
    only `Session` knows who was benched. `bench_multiplier` stays at 0 by
    default (docs/04_phase2b_definition.md section 4); non-zero is exercised
    directly in tests even though it's not the shipped default.
    """
    if not benched:
        return
    pool = compute_battle_xp_pool(enemy_squad)
    bench_pool = round(bench_multiplier * pool)
    bench_share = bench_pool // len(benched)
    for hero in benched:
        grant_xp(hero, bench_share, rng)


def revive_downed_hero(hero: Hero) -> None:
    """Downed, not dead: a hero at 0 HP comes back at a minimal HP value
    at battle end, rather than staying permanently removed."""
    if not hero.is_alive:
        hero.current_hp = config.DOWNED_REVIVE_HP


def recover_hp(hero: Hero, fraction: float) -> None:
    """Between-battle HP recovery: heal `fraction` of max_hp, capped at
    max_hp. The same function whether `hero` was merely bruised or just
    revived at config.DOWNED_REVIVE_HP — no separate injury system, "she's
    been on the bench three fights" falls out of HP alone
    (docs/04_phase2b_definition.md section 3)."""
    healed = round(fraction * hero.max_hp)
    hero.current_hp = min(hero.max_hp, hero.current_hp + healed)


def grant_class_xp(
    hero: Hero, track: ClassTrack, amount: int = config.CLASS_XP_PER_ABILITY_USE
) -> None:
    """Track 2 accrual only this phase — no thresholds fire, no unlocks."""
    hero.class_xp[track] += amount


def grant_class_xp_for_ability(
    hero: Hero, ability: Ability, amount: int = config.CLASS_XP_PER_ABILITY_USE
) -> None:
    """Credit whichever track owns `ability`, per data/class_tracks.yaml."""
    track = class_track_library.load_class_tracks()[ability.name]
    grant_class_xp(hero, track, amount)
