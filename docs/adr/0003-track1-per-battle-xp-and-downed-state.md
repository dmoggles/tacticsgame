# 0003. Track 1 XP as a per-battle pool; downed heroes revive at battle end

## Status

Accepted

## Context

`docs/03_phase2a_definition.md` sections 4–5 require two changes, bundled
here because both land in the same battle-end resolution hook and step 3
(session chaining) depends on both:

1. Track 1 XP moves from per-action accrual (`config.XP_PER_ACTION`,
   granted every turn in `Battle._take_turn`) to a per-battle pool
   awarded once, on victory. The doc's rationale (not re-litigated here):
   per-action accrual fed both Track 1 ("just showing up") and Track 2
   ("what you did") off the same signal, collapsing a distinction the
   design wants kept. The doc explicitly requires the old path be
   **removed**, not left alongside.
2. 0 HP means downed, not dead: a hero sits out the rest of the current
   battle (already true — `Hero.is_alive` already gated turn order, AI
   targeting, and tile occupancy) and revives at a minimal HP at battle
   end, rather than staying at 0 HP indefinitely. A battle is lost only
   when the whole fielded squad is downed (already true in
   `Battle._check_win_condition`).

## Decision

- `config.py`: removed `XP_PER_ACTION`. Added `XP_POOL_PER_STRENGTH_POINT
  = 25`, `BENCH_XP_BONUS_MULTIPLIER = 0.0`, `DOWNED_REVIVE_HP = 1`.
- `engine/progression.py`, three new functions:
  - `compute_enemy_strength(enemy_squad) -> int`: sum of enemy levels.
    Isolated in its own function since the doc explicitly names this as
    "exactly the number that will be revised repeatedly" — sum-of-levels
    was chosen over sum-of-attributes (the doc's other named option)
    purely for simplicity; nothing about the surrounding code depends on
    which was picked.
  - `compute_battle_xp_pool(enemy_squad) -> int`:
    `XP_POOL_PER_STRENGTH_POINT * compute_enemy_strength(enemy_squad)`.
  - `award_battle_xp(fielded, benched, enemy_squad, rng, bench_multiplier=config.BENCH_XP_BONUS_MULTIPLIER)`:
    splits the pool evenly (integer floor division) across `fielded` via
    the existing `grant_xp` (its multi-level-jump loop needed no
    changes). Downed heroes need no special-casing — they're never
    removed from their squad list, so they're already in `fielded` and
    get a full share automatically, matching the doc's "downed heroes
    count as fielded" requirement for free. `benched` gets a separate
    bonus pool (`bench_multiplier * pool`, split evenly), guarded against
    division by zero when empty. Phase 2a never calls this with a
    non-empty `benched` — no bench exists yet (Phase 2b) — but the
    parameter and the guard exist now per the doc's explicit instruction,
    so 2b's bench doesn't require touching this function's signature
    again.
  - `revive_downed_hero(hero)`: sets `current_hp = DOWNED_REVIVE_HP` if
    `not hero.is_alive`.
- `engine/battle.py`: `_take_turn` no longer calls `grant_xp` at all.
  `_check_win_condition`, on determining a winner, now calls
  `_resolve_battle_end()` once (naturally exactly-once, since `step()`
  already short-circuits once `is_over` is set):
  - XP is awarded only when `winner == "player"` (doc: "on battle
    victory") — enemy squads get no Track 1 XP at all now, matching that
    they're ephemeral/regenerated per battle (step 3) rather than a
    persistent roster.
  - Revival runs over `player_squad` regardless of win or loss — a
    downed hero shouldn't stay stuck at 0 HP as a matter of engine-state
    hygiene, independent of what session chaining (step 3) later does
    with a loss (per the doc, a lost battle ends the session anyway, so
    revival mostly matters for the win case where the session
    continues — but the rule itself isn't conditioned on outcome).
  - `benched=[]` is hardcoded at this one call site, since `Battle` has
    no bench concept in Phase 2a.

## Consequences

**Positive**

- Track 1 and Track 2 are now genuinely independent signals: Track 1
  only ever changes at battle end from a pool tied to what was fought,
  Track 2 still accrues per ability use during battle, unchanged.
- Downed heroes are a real, tested state distinct from permanent removal
  — nothing in the engine can currently ever remove a hero from a squad
  list, so "downed, not dead" was already almost true by construction;
  this closes the one actual gap (revival).

**Negative / trade-offs**

- `tests/fixtures/ai_vs_ai_baseline.json` needed regenerating (see
  below) — an unavoidable, expected consequence of the rework, not a
  bug, but worth naming as a cost: the fixture no longer proves "AI
  behavior is unchanged across all of Phase 2a," only "AI behavior is
  unchanged since this commit."
- `award_battle_xp`'s even split uses integer floor division; a pool that
  doesn't divide evenly quietly loses the remainder rather than
  distributing it. Acceptable for placeholder numbers; revisit only if
  it becomes visible at real balance values.

**Explicitly deferred (not built now)**

- Actually exercising the `benched` parameter — Phase 2b's bench.
- Gradual HP recovery for downed heroes between battles — Phase 2b;
  Phase 2a's between-battle placeholder (full heal, step 3) covers the
  gap, per the phase doc's own note that this makes a separate injury
  system unnecessary.
- Tuning `XP_POOL_PER_STRENGTH_POINT`/enemy-strength formula — explicitly
  a placeholder per the doc, expected to change with playtesting data
  once step 4 (real player input) exists.

## AI-vs-AI baseline fixture: documented deviation

Regenerated `tests/fixtures/ai_vs_ai_baseline.json` after this change.
Diffed old vs. new output field-by-field across all 10 committed seeds
before regenerating, to confirm every difference was attributable to
this rework rather than an unrelated bug:

- Every enemy hero's `xp` now ends at 0 (enemies never receive Track 1 XP
  under the new model, at all — expected, see Decision above).
- Two seeds (1 and 3) show a previously-permanently-downed hero now
  `is_alive: true` with `current_hp` at `DOWNED_REVIVE_HP` — the new
  revival mechanic firing, exactly as designed.
- Seed 3 alone shows a changed round/step count (7→6 rounds, 20→18
  steps) and a hero ending at a different level — the one case where
  removing mid-battle leveling actually altered a fight's trajectory (an
  enemy that used to reach level 2 mid-battle, changing its damage
  output, now stays level 1 for the whole fight).
- **`winner` is identical across all 10 seeds, with no exceptions** —
  strong evidence this is a scoped, understood change rather than a
  regression.

## Alternatives considered

- **Awarding XP to the enemy squad too, on a loss** — rejected; enemy
  squads are ephemeral (regenerated per battle, step 3), so persistent
  Track 1 growth for them has no meaning in this design.
- **Reviving downed heroes only on victory**, skipping it on a loss since
  the session ends anyway (step 3) — rejected in favor of the simpler,
  outcome-independent rule; conditioning revival on `winner` would be an
  extra branch to save nothing, since a lost battle's engine state is
  discarded by session chaining regardless.
- **Sum of enemy attributes for "strength"** instead of sum of levels —
  both explicitly sanctioned by the phase doc; levels chosen only for
  simplicity, not for any stated correctness reason. Revisit freely.
