# 0008. Between-battle screen: single-snapshot deltas, allocate-then-select flow

## Status

Accepted

## Context

`docs/04_phase2b_definition.md` section 6 (build-order step 4) is the
payoff screen tying together roster/squad selection (section 2, ADR 0006)
and manual attribute allocation (section 5, ADR 0007): per roster hero, show
level (and whether it changed), attributes with the delta from the previous
battle, class XP with delta, and HP/recovery status — with a **hard
requirement that no level-up history is ever exposed**, current delta only.

Two things needed a real design beyond "wire the existing pieces into a
screen":

1. Nothing in the engine tracked "what changed since last time" at all —
   `Hero` only ever holds current state. Something has to compute a delta,
   and the no-history requirement means whatever holds the "before" state
   must be structurally incapable of accumulating a log, not just
   conventionally discouraged from displaying one.
2. A single between-battle visit has to resolve two different kinds of
   player interaction in sequence — manual allocation choices (0 or more,
   per ADR 0007's `pending_level_ups`) and squad selection (ADR 0006's
   `begin_battle`) — and the doc's own multi-level-jump requirement ("present
   multiple allocation choices in sequence") means these can't just be two
   independent, order-agnostic controls.

## Decision

**Snapshot/delta mechanism** — new `engine/hero_delta.py`:

- `HeroSnapshot` (level, attributes, a *copied* class_xp dict) and
  `HeroDelta` (level before/after, per-attribute deltas, per-class-track
  deltas, `leveled_up` property) are both plain frozen dataclasses.
- `Session` gains one field, `_pre_battle_snapshots: list[HeroSnapshot]`,
  populated in `begin_battle()` — a snapshot of the *entire* roster, taken
  immediately before that battle starts. It is **overwritten**, not
  appended to, on every `begin_battle()` call.
- `Session.deltas() -> list[HeroDelta]` compares the current roster against
  that one stored snapshot, in roster order. Before the first
  `begin_battle()`, it returns `[]`.
- This makes "no history" a structural property, not a UI-layer promise:
  there is only ever one snapshot in memory, and it's gone the moment the
  next battle begins. A screen (or a bug) cannot expose a second-to-last
  delta because the data to compute one no longer exists.
- Storage is a **list parallel to `Session.roster`**, not a
  `dict[Hero, HeroSnapshot]` — `Hero` is an unhashable dataclass (mutable,
  default `eq=True` sets `__hash__ = None`), the same reason
  `engine/roster.py` (ADR 0006) already uses identity-based list
  operations instead of dict/set membership for heroes.

**Screen flow** — new `visualizer/between_battle_screen.py::BetweenBattleController`,
a pygame-free state machine mirroring `PlayerTurnController`'s shape
(ADR 0005): `ALLOCATING -> SELECTING -> READY`.

- `ALLOCATING` comes first, unconditionally, whenever any roster hero has
  `pending_level_ups > 0`. `pending_hero` always resolves to the first such
  hero in roster order; `choose_manual_attribute(attribute_or_None)` calls
  `progression.resolve_manual_allocation` and stays on the same hero across
  a multi-level jump until its count reaches 0, matching the doc's
  "sequential choices" requirement directly off the data model built in
  ADR 0007 — no separate queue/ordering logic needed here beyond "ask
  `pending_hero` again."
- Once nothing is pending, the controller is in `SELECTING`/`READY`
  (`READY` once `selected` is non-empty) and `toggle_fielded`/`confirm`
  drive `Session.begin_battle` exactly as ADR 0006 already defined it.
- `selected` is pre-filled with `session.fielded` (who fought last battle)
  in `__post_init__`, not left empty — a one-click-confirm default for the
  common "field the same squad again" case, freely overridable by clicking
  before confirming. This is also why the pre-existing session-chaining
  renderer test (`test_pressing_enter_after_a_won_battle_advances_the_session`,
  ADR 0005) kept passing unmodified: with roster size equal to fielded size
  it has nothing to pick, so the screen is `READY` immediately and one
  Enter press confirms it, same as before this screen existed.

**Why allocate-then-select and not the reverse or interleaved:** attribute
deltas need to reflect the *final* post-allocation state to be meaningful
("Might 7 → 9" should include the manual point, not just the automatic
two) — see ADR 0007's Consequences, which already flagged this ordering
requirement as the trade-off of deferring only the manual point.
Squad selection has no such dependency on allocation being resolved first,
but gating it behind `ALLOCATING` is simpler than allowing both
simultaneously and gives every level-up prompt a guaranteed, uninterrupted
moment of attention — consistent with the phase doc's "still debug-grade
UI... functional layout is sufficient," not a polish choice.

**Renderer wiring** (`visualizer/renderer.py`): the existing per-frame
dispatch (`if battle.is_over: ... else: ...`) gained a between-battle branch
placed *before* the old battle-turn-input branch, checked first each frame,
with its own event handling/drawing and a `continue`. The battle-ended →
`session.advance()` → maybe-create-`BetweenBattleController` step was moved
to run **before** that dispatch (not inside the old `else` arm), so the very
frame a battle ends and the screen is created, that screen's own event
handling runs immediately rather than one stale frame of the just-finished
battle's UI rendering first. The now-dead old branch that advanced `battle`
to `session.current_battle` on Enter (from ADR 0005, back when `Session`
auto-prepared the next battle) was deleted — `BetweenBattleController.confirm()`
is the only path to a new battle now.

## Consequences

**Positive**

- The no-history requirement is enforced by data lifetime, not by an
  agreement to not build a history UI — a future contributor adding a
  "show more" button would find there's nothing to show more of, not a
  temptation to add a log.
- `resolve_manual_allocation`'s existing multi-level-jump behavior (ADR
  0007) needed zero changes to support "present choices in sequence" — the
  controller just asks `pending_hero` again after each resolution.
- Reusing `session.fielded` as the pre-fill default meant zero existing
  tests needed updating for the new screen to exist; the one case with
  nothing to choose (roster size == fielded size) degenerates to the old
  one-Enter-press behavior automatically.

**Negative / trade-offs**

- `Session.deltas()`'s list is positional (parallel to `Session.roster`),
  so any future code that reorders or filters `roster` without keeping
  `_pre_battle_snapshots` in lockstep would silently misattribute deltas to
  the wrong hero. Acceptable now since nothing in Phase 2b ever reorders or
  mutates roster membership — flagged here for whoever adds that later.
- The between-battle screen is deliberately minimal: a fixed-height row per
  roster hero, keyboard slots 1-4 for attribute choice, click-to-toggle for
  squad selection. No scrolling, no confirmation dialog on an empty/illegal
  selection beyond simply not becoming `READY`. Matches the phase doc's
  explicit "no art, no animation, no polish" scope, not an oversight.

**Explicitly deferred (not built now)**

- Telemetry (step 5) — `Session.deltas()`/`HeroSnapshot` are not reused for
  it; the telemetry dump reads final state directly, per the phase doc's
  section 7 list, not deltas.

## Alternatives considered

- **Keep a snapshot per hero on `Hero` itself** (e.g.
  `Hero.previous_snapshot`) instead of on `Session` — rejected: this is
  session-scoped bookkeeping ("since the last begin_battle"), not a
  property of a hero on its own, and would leak a UI-adjacent concern into
  the core model that `models/hero.py` otherwise has no reason to know
  about.
- **`dict[Hero, HeroSnapshot]` keyed by hero** instead of a roster-parallel
  list — rejected outright: `Hero` is unhashable by construction (see
  Decision above), so this would not even run.
- **Let squad selection happen before/alongside allocation** — rejected;
  see the "why allocate-then-select" reasoning above. Interleaving would
  also complicate `is_ready` into needing to track two independent
  completion conditions instead of one linear phase progression.
- **Auto-resolve declined/skipped allocations at screen-exit instead of
  requiring an explicit SPACE press per pending hero** — rejected: the doc
  requires the choice (including explicitly declining) to be presented,
  not silently defaulted; a player who never sees the prompt hasn't
  "declined" anything.
