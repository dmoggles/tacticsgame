# 0007. Manual attribute allocation defers only the deterministic point

## Status

Accepted

## Context

`docs/04_phase2b_definition.md` section 5 (build-order step 3) requires
that of a level-up's `POINTS_PER_LEVEL_UP` (3) attribute points, exactly
`MANUAL_ALLOCATION_POINTS_PER_LEVEL_UP` (1) is chosen deterministically by
the player, and the choice happens **on the between-battle screen, not
mid-battle** — no in-battle prompt is allowed.

This collides with how leveling already works. Since Phase 2a
(`docs/adr/0003-track1-per-battle-xp-and-downed-state.md`), `grant_xp`
completes a level-up fully and synchronously the moment enough XP is
granted — which happens inside `Battle._resolve_battle_end`, i.e. exactly
at the mid-battle/battle-end moment the doc forbids prompting at. A
player's choice genuinely cannot be known there. Something has to give:
either the *entire* level-up's point resolution is deferred until later
(when a choice can actually be collected), or only the specific point that
needs a choice is deferred, with the rest still resolving immediately as
before.

## Decision

Only the manual point is deferred — the automatic 2 points still resolve
immediately, exactly as `_level_up` already did before this phase:

- `Hero` gains `pending_level_ups: int = 0` — level-ups whose manual point
  hasn't been resolved yet. `hero.level` and `hero.xp` are unaffected by
  this and still update the instant a threshold is crossed, same as
  Phase 2a — only attribute/HP resolution for the manual point is queued.
- `progression._level_up(hero, rng)` now allocates only
  `POINTS_PER_LEVEL_UP - MANUAL_ALLOCATION_POINTS_PER_LEVEL_UP` (2) points
  via the existing affinity-weighted `allocate_points`, applies them
  (attributes + HP, factored into a new shared `_apply_attribute_points`
  helper), bumps `hero.level`, and increments `pending_level_ups` by 1.
  `grant_xp`'s multi-level-jump loop is otherwise unchanged — a big XP
  pool still queues one pending level-up per threshold crossed in the same
  call, exactly as `hero.level` already did.
- New `progression.resolve_manual_allocation(hero, attribute, rng)`
  resolves exactly one pending level-up's point: applies it to `attribute`
  if given, or — if `None` (the player declined/skipped) — draws it via one
  more affinity-weighted `allocate_points` call instead, so it's never
  forfeited. Raises `ValueError` if nothing is pending. A multi-level jump
  is resolved by calling this once per pending level-up.
- No `Session`/screen wiring — per the phase doc's own build order, step 3
  is "the choice and its application, independent of any screen." Nothing
  currently calls `resolve_manual_allocation`; that's step 4's job.

## Consequences

**Positive**

- `grant_xp`/`_level_up` keeps using `rng` for exactly the reason it
  already did — no parameter becomes dead, so nothing about
  `award_battle_xp`, `award_bench_bonus_xp`, `Battle._resolve_battle_end`,
  or `Session.advance()`'s signatures needed to change to support this
  step, keeping it scoped to `progression.py` and `models/hero.py` alone.
- Every existing XP/leveling test (multi-level jumps, the proportional-XP
  Session test from step 1) keeps working unchanged, since `hero.level`
  and `hero.xp` bookkeeping wasn't touched.
- `allocate_points`'s independent-draw-per-point behavior means splitting
  "2 now, 1 later" is statistically identical to drawing all 3 at once —
  no distribution change from doing it in two calls.

**Negative / trade-offs**

- A hero's attributes now update in two increments per level-up (2 points
  immediately, 1 point whenever `resolve_manual_allocation` is eventually
  called) rather than one atomic step. Between those two moments,
  `hero.attributes`/`hero.max_hp` reflect a partial level-up — acceptable
  since nothing reads hero state mid-resolution yet (no screen exists),
  but the eventual between-battle screen (step 4) needs to either resolve
  all pending level-ups before displaying "current attributes," or treat
  a mid-resolution state as legitimate to display.
- Nothing currently *forces* `pending_level_ups` to reach 0 — a session
  can keep running via `run_to_completion()` with heroes accumulating
  unresolved pending level-ups indefinitely, since no screen exists yet to
  resolve them. Deliberately deferred to step 4, where the between-battle
  screen becomes the thing that drives resolution before the next battle
  can start.

**Explicitly deferred (not built now)**

- Any `Session`-level enforcement that pending level-ups must be resolved
  before the next `begin_battle()` — a step 4 concern once a screen exists
  to resolve them through.
- The between-battle screen itself.

## Alternatives considered

- **Defer the entire level-up's point resolution** (all 3 points, not just
  the manual one) until `resolve_manual_allocation`-equivalent is called —
  rejected: `_level_up`'s `rng` parameter would become dead the moment
  attribute resolution moved out of it, and untangling `rng` from every
  downstream caller (`award_battle_xp`, `award_bench_bonus_xp`, `Battle`,
  `Session`) for no behavioral gain is unrelated scope creep for a step
  the phase doc scopes as "the choice and its application, independent of
  any screen" — not a rework of the whole XP-awarding pipeline.
- **Pass a decision-making callback into `grant_xp` itself**
  (`grant_xp(hero, amount, rng, choose_attribute=callback)`) so leveling
  stays a single synchronous call — rejected: this forces every caller,
  including `Battle`'s battle-end XP award and every existing headless
  test, to supply a decision function even though the doc explicitly
  forbids deciding synchronously at that moment. The deferred-`pending_
  level_ups` approach is what actually makes "not mid-battle" possible.
