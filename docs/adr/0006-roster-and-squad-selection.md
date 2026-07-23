# 0006. Roster larger than the fielded squad; Session requires explicit squad selection

## Status

Accepted

## Context

`docs/04_phase2b_definition.md` sections 1-2 (build-order step 1) require a
player roster larger than what's fielded per battle, with fielding a
specific subset a real per-battle choice (including fielding fewer than the
maximum). Two prior decisions run into this directly:

- ADR 0004 gave `Session` an auto-advance flow: `__post_init__` and
  `advance()` always immediately prepare and start the next `Battle` from
  the whole squad, because in Phase 2a "whole squad" and "fielded squad"
  were the same list — there was no selection to make. That equivalence is
  gone once a roster exists: `Session` can no longer auto-start a battle
  without knowing which roster heroes were chosen, or "squad selection"
  would be meaningless — the player could never actually leave anyone
  benched. This doesn't invalidate ADR 0004's core decision (no
  serialization; object identity is the persistence mechanism, which is
  unchanged and still correct) — only its auto-start behavior needed
  revising, so ADR 0004 itself is not marked superseded.
- ADR 0003 gave `award_battle_xp` a `benched` parameter, hardcoded to `[]`
  at its one call site in `Battle._resolve_battle_end`, reasoning that
  `Session` "has no reason to know about it beyond reading `battle.winner`."
  That reasoning was correct in Phase 2a (no bench existed) but breaks now:
  `Battle` only ever sees the fielded squad, never the roster, so it
  structurally cannot know who's benched. Threading `benched` into `Battle`
  would give combat resolution a roster/bench concept it doesn't otherwise
  need, which cuts against the same engine-layer-minimalism reasoning ADR
  0003 used in the first place.

## Decision

- `config.py`: `SQUAD_SIZE` split into `ROSTER_SIZE = 4` (the player's full
  pool) and `FIELDED_SQUAD_SIZE = 2` (max per battle, and still the enemy
  squad's fixed size regardless of how many player heroes are fielded —
  fielding fewer is an intended "fight outnumbered" choice, not a reduction
  in enemy count).
- New `engine/roster.py::select_fielded_squad(roster, fielded) -> benched`:
  the only validation surface for a squad-selection choice — at least one
  hero, no more than `FIELDED_SQUAD_SIZE`, no repeats, every entry actually
  drawn from the roster. Membership/dedup checks are identity-based
  (`id()`), not `==`, since `Hero` uses the dataclass-generated field-value
  `__eq__` and two distinct heroes can otherwise share every field.
- `Session` gains `roster: list[Hero]` (replacing `player_squad`),
  `fielded: list[Hero]`, and `benched: list[Hero]` (both `init=False`,
  populated by `begin_battle`). `__post_init__` no longer prepares a battle.
- New `Session.begin_battle(fielded: list[Hero])`: validates via
  `roster.select_fielded_squad`, sets `fielded`/`benched`, and builds the
  `Battle` (what `_prepare_next_battle` used to do unconditionally).
  Raises `ValueError` if the session is already over or the current battle
  hasn't finished yet.
- `Session.advance()` no longer auto-prepares the next battle. It scores
  the finished battle (awarding bench-bonus XP itself — see below), and on
  a win that doesn't end the session, clears `current_battle` to `None`
  rather than starting the next one. The caller must call `begin_battle`
  again before the next battle can run.
- `Session.run_to_completion()` gained an optional `select_fielded:
  Callable[[list[Hero]], list[Hero]]` parameter (roster → chosen fielded
  heroes), defaulting to fielding the first `FIELDED_SQUAD_SIZE` roster
  members every battle — this exactly reproduces Phase 2a's behavior when
  roster size equals fielded size, so every existing full-auto headless
  test kept working unchanged.
- `progression.award_battle_xp` dropped its `benched` parameter — it's
  fielded-only now, matching the only thing `Battle` actually knows. A new
  `progression.award_bench_bonus_xp(benched, enemy_squad, rng,
  bench_multiplier=...)` is `Session`-called only, from `advance()`,
  immediately after a win (mirroring `Battle`'s own "XP only on victory"
  rule). `Battle._resolve_battle_end` is otherwise unchanged.
- `visualizer/renderer.py`: since the real between-battle squad-selection
  screen is step 4 (not built yet), the render loop now calls
  `session.begin_battle(session.roster[:FIELDED_SQUAD_SIZE])` itself
  immediately after a mid-session `advance()`, marked
  `# TODO(phase2b step4)`, so the existing "press Enter to continue"
  interactive flow keeps working (and the automated dummy-driver test
  covering it keeps passing) without a real screen existing yet. `
  __main__.py` builds a `ROSTER_SIZE` roster and calls `begin_battle` once
  before launching the renderer, for the same reason.

## Consequences

**Positive**

- Squad selection is now a real, load-bearing choice: nothing advances a
  session without it, so the between-battle screen (step 4) isn't
  decorative — it's the only path forward once the roster/fielded gap is
  real.
- `Battle` still never needs to know about a roster or a bench — the
  engine/rendering-style layering ADR 0003 established for XP resolution
  holds, just with the boundary drawn one layer further out (`Session`
  instead of `Battle`).
- `Session.run_to_completion`'s default selection strategy means every
  Phase 2a-era headless test needed a signature-level update (`roster=`
  instead of `player_squad=`, an explicit `begin_battle` call) but no
  behavioral rewrite — the underlying "field everyone" scenario still
  works unattended.

**Negative / trade-offs**

- `renderer.py`'s auto-select bridge is a real, if small, placeholder
  UI decision (always field the first `FIELDED_SQUAD_SIZE` roster members)
  baked into the render loop rather than left undecided — accepted because
  the alternative was a guaranteed crash (`assert next_battle is not None`
  failing) the moment a second battle in an interactive session began,
  which is worse than a clearly-marked placeholder due for replacement.
- `begin_battle` raising `ValueError` on misuse (session over, battle still
  in progress) rather than being unreachable-by-construction means callers
  (the future between-battle screen) must respect the state machine
  explicitly; no compile-time enforcement exists.

**Explicitly deferred (not built now)**

- The actual between-battle squad-selection screen — step 4. Today's
  renderer bridge is a placeholder, not that screen.
- Anything about *why* a player would bench someone (gradual recovery,
  manual allocation) — steps 2-3.

## Alternatives considered

- **Keep `Session` auto-starting with the first `FIELDED_SQUAD_SIZE`
  roster members by default, layering explicit selection on top as an
  override** — rejected: it would let every caller (including the eventual
  real screen) skip calling `begin_battle` entirely and nothing would ever
  force the choice to exist, undermining the entire point of section 2.
- **Thread `benched` through to `Battle`** (via `Session` passing it into
  the constructor or `_resolve_battle_end`) so `award_battle_xp`'s original
  single-call-site shape survives unchanged — rejected: gives `Battle` a
  roster/bench concept it structurally doesn't need, just to avoid adding
  one new function to `progression.py`.
- **Validate roster size against `config.ROSTER_SIZE` in `Session`** —
  rejected; the phase doc requires configurability, not a hard invariant,
  and nothing downstream currently depends on roster length being exactly
  `ROSTER_SIZE` (only `select_fielded_squad`'s `FIELDED_SQUAD_SIZE` cap is
  load-bearing).
