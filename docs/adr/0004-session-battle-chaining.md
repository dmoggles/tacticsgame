# 0004. Session as a thin driver over reused Hero objects, not a persistence layer

## Status

Accepted

## Context

`docs/03_phase2a_definition.md` section 6 asks for a **session**: a
sequence of N battles fought by one persistent player squad, with enemy
squads regenerated fresh each battle (no difficulty curve yet), cooldowns
and positions reset per battle, HP fully healed between battles as an
explicit placeholder, and the session ending on either winning all N
battles or losing one. Step 2 (ADR 0003) already made `Battle` own its
own end-of-battle resolution (XP award, downed-hero revival) — this step
only needed to drive a *sequence* of `Battle` instances sharing state.

The open design question was how "persistence" should actually work:
serialize/restore hero state between battles, or something simpler.

## Decision

- New `engine/session.py`, `Session` dataclass: `player_squad: list[Hero]`,
  a shared `rng`, `battles_total` (default `config.SESSION_BATTLE_COUNT
  = 5`), `battles_won`, and derived `current_battle`/`is_over`/`result`
  fields (`init=False`, set by `__post_init__`/`advance()` — same pattern
  `Battle` already uses for `current_order`).
- **No serialization.** `Session` holds the *same* `Hero` objects for its
  entire lifetime and passes that exact list into every `Battle` it
  constructs. `attributes`/`level`/`xp`/`class_xp` persist purely because
  they're fields on objects that are never copied or rebuilt — object
  identity *is* the persistence mechanism. This directly matches the
  doc's own explicit non-goal ("save/load persistence across process
  restarts — a session lives in memory"): there was never a reason to
  build a snapshot/restore layer for state that only needs to survive
  within one running process.
- `Session` only resets what the doc says *doesn't* carry over:
  `_prepare_next_battle()` clears `hero.cooldowns`, resets `hero.position`
  to the fixed per-index starting tile (matching the position convention
  already used by `__main__.build_demo_battle`/`dev_tools.build_seeded_battle`/
  `test_battle._build_battle`), and — gated behind new
  `config.FULL_HEAL_BETWEEN_BATTLES` (`True`, `# TODO(phase2b)`) — sets
  `current_hp = max_hp`.
- New `progression.generate_enemy_squad(rng) -> list[Hero]`: the doc's
  required "single clearly-marked generator function," flat/unscaled this
  phase, reusing `create_starting_hero` exactly as the three existing
  squad-builder call sites already do for their enemy half.
- `Session` exposes both `advance()` (call once the current battle is
  over; scores it and either starts the next battle or ends the session)
  and `run_to_completion()` (loops `advance()`/`Battle.run_to_completion()`
  until `is_over`) — deliberately mirroring `Battle`'s own `step()` /
  `run_to_completion()` split, since a future player-driven visualizer
  (step 4) will need the fine-grained `advance()` hook the same way it'll
  need `Battle.step()`.
- Grid dimensions are not parameterized on `Session` — nothing else in
  the codebase parameterizes them either; every call site just reads
  `config.GRID_WIDTH`/`GRID_HEIGHT` directly.

## Consequences

**Positive**

- Zero new persistence code, and therefore nothing to keep in sync if
  `Hero` grows new fields later — anything added to `Hero` persists
  across battles for free, with no `Session`-side serialization logic to
  update.
- `Session`'s API shape (`advance()`/`run_to_completion()`) sets up step
  4's player-input work without guessing at what it'll need: the
  visualizer will drive `Battle.step()` from player clicks and call
  `Session.advance()` exactly when `Battle.is_over` flips, which is
  already the natural seam.

**Negative / trade-offs**

- Because `Hero` objects are mutated in place and shared by reference,
  any code that holds an older reference to a squad list (rather than
  going through `Session.player_squad`/`Session.current_battle.player_squad`)
  sees live mutations, not a stable snapshot. Not an issue for anything
  built so far, but worth naming for whoever wires in a UI that might
  want to display "last battle's" state after `advance()` has already
  moved on.
- `FULL_HEAL_BETWEEN_BATTLES` is a boolean gate rather than a numeric
  heal-fraction constant — chosen because Phase 2a only ever needs "on,"
  and a fractional constant with only one real value in use would be
  unexercised flexibility. Phase 2b's gradual recovery is expected to
  replace the gated block entirely, not tune a fraction within it.

**Explicitly deferred (not built now)**

- Wiring `Session` into `__main__.py`/the visualizer — step 4.
- Any difficulty curve in `generate_enemy_squad` — flat/unscaled per the
  doc; the function is isolated specifically so this is a contained
  future change.
- Roster/bench, gradual recovery, squad selection, manual attribute
  allocation, the between-battle screen, telemetry — Phase 2b per the
  phase doc's own out-of-scope list.

## Alternatives considered

- **Snapshot Hero state into a lightweight persistence record between
  battles** (e.g. a `HeroSaveState` dataclass copied in and out of each
  `Battle`) — rejected: it's strictly more code for the same outcome
  given everything currently lives in one process for one session, and
  it would need to be kept in sync with `Hero`'s fields by hand. Revisit
  only if/when actual cross-process save/load is ever in scope, which is
  explicitly not a Phase 2 concern.
- **`Session` owning battle-end resolution itself** (XP award, downed
  revival) instead of delegating to `Battle._resolve_battle_end` — 
  rejected; that logic already lives correctly in `Battle` as of step 2
  (ADR 0003), scoped to a single battle, and `Session` has no reason to
  know about it beyond reading `battle.winner`.
- **A numeric `BETWEEN_BATTLE_HEAL_FRACTION` constant** instead of a
  boolean gate — considered, rejected for now since Phase 2a has no use
  for any value other than "fully on"; see Consequences.
