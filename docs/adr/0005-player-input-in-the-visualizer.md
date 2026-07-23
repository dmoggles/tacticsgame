# 0005. Player input as a pygame-free controller consumed by a thin renderer loop

## Status

Accepted

## Context

`docs/03_phase2a_definition.md` sections 2–3 (acceptance criterion 2):
the player controls the fielded squad's turns through the visualizer —
select a hero, move, choose an ability, choose a target, cancel before
committing, end turn explicitly — while the AI keeps controlling the
enemy side and stays available as a full auto-play mode. Before this,
`renderer.run(battle)` was purely passive: SPACE always called
`battle.step()`, which *always* resolved the current actor's turn via
`ai.decide_turn`, for either side. There was no way to inject a
human-supplied turn, and no non-mutating way to ask "whose turn is it"
without consuming it.

## Decision

**Engine seam.** `Battle` gained:
- `current_actor` (read-only `@property`): peeks who's up next without
  mutating `turn_index`/rounds. Purely advisory — a UI needs to check
  this every rendered frame while a human is still deciding, without
  committing to anything.
- `take_turn(actor, decision)`: the manual-input counterpart to `step()`.
  Internally calls the same battle-tested `_next_actor()` `step()` uses
  (not the peek) before resolving, so all the real round-rollover/
  dead-skipping bookkeeping stays in the one place that already gets it
  right; raises `ValueError` if `actor` isn't actually next up.
- `_take_turn` split into `step()` (AI decides, then applies) and a
  shared `_resolve_turn(actor, decision)` both paths funnel through.

**`TurnDecision`/`AbilityDecision` moved to new `engine/turn.py`.** They
represent *a turn*, not *an AI's turn* — a human-driven turn via the
visualizer produces the identical shape. Once the visualizer needs to
construct these to call `Battle.take_turn`, importing them from `ai.py`
would be exactly the kind of "UI reaching into unrelated internals" step
1 was built to prevent. `ai.py` now imports them from `.turn`.

**Cooldown-tick timing had to move.** This was the one real bug the
refactor surfaced, not something planned upfront: cooldowns used to tick
at the *start* of turn resolution, computed and applied in the same
synchronous call as the AI's decision. That's wrong once decisions can
take many UI frames — `queries.usable_abilities` (which the UI polls
repeatedly while a human is choosing) must already reflect this turn's
ticked cooldowns, not last turn's, or a human would see an ability marked
unavailable when it should already be off cooldown by their turn (an
actual bug, not a display lag — confirmed by
`test_basic_mend_goes_on_cooldown_after_use_and_cycles_back` failing when
this was first tried). Fixed by ticking the *next* actor's cooldowns
exactly once, immediately when they become current — at the end of
`_resolve_turn` (priming whoever's next) and once in `__post_init__`
(priming the very first actor) — rather than at the start of resolving
their own turn. Verified behaviorally identical for the AI path (same
values, same relative ordering to that actor's own decision, just
computed slightly earlier in wall-clock terms) — the AI-vs-AI baseline
fixture needed no regeneration.

**New `visualizer/player_input.py::PlayerTurnController`.** A plain
dataclass state machine — deliberately no `pygame` import — walking
`IDLE → MOVING → ACTING → TARGETING → READY` via `select_active_hero()` /
`choose_destination()` / `skip_move()` / `choose_ability()` /
`skip_ability()` / `choose_target()` / `cancel()` / `build_decision()`.
Every legality check (`reachable_tiles`, `usable_abilities`,
`valid_targets`) delegates straight to `engine/queries.py` — this module
computes none of it itself. `cancel()` steps back exactly one stage
(TARGETING→ACTING, ACTING/READY→MOVING, MOVING→IDLE), matching the doc's
"cancel before commit": nothing is applied to `Battle` until
`build_decision()`'s result is handed to `take_turn()`, so every
intermediate choice is a free no-op to undo. Being pygame-free makes it
fully unit-testable headlessly (`tests/test_player_input.py`), which is
where essentially all of the actual interaction *logic* lives.

**Interaction model, mapped to concrete controls:**
- Select: click the current-turn hero's tile, or Tab. Only the actual
  current actor is ever selectable — Phase 2a's turn order is fixed slot
  order (no simultaneous multi-hero choice), so this still satisfies the
  doc's literal "select... click, or cycle with a key" without inventing
  freedom the engine doesn't have.
- Move: click a highlighted reachable tile, SPACE to skip, clicking the
  hero's own tile also counts as skip (rather than a same-tile "move").
- Act: 1–4 for ability slots (cooldown-gated ones are visibly marked and
  rejected), SPACE to skip.
- Target: click a highlighted valid-target tile.
- Cancel: Esc, one stage at a time; Esc with nothing to cancel quits.
- End turn: Enter, once move and act are both decided (either may be a
  skip).
- Enemy turns and full auto-play (`A`, unchanged) still resolve via
  `battle.step()` exactly as before.

**Class XP visibility (section 3).** The ability list shown during
`ACTING` gets a `→ <track>` suffix, sourced from the already-existing
`class_track_library.load_class_tracks()` (already used in
`_draw_hero_card`) — no new data path needed.

**Testing strategy — three layers, since a pygame window can't be driven
through a browser tool:**
1. `tests/test_player_input.py`: full headless coverage of
   `PlayerTurnController`'s state machine — this is where correctness
   actually lives, and it needs no display at all.
2. `tests/test_renderer_helpers.py`: the small pure functions
   (`_pixel_to_tile`, `_ability_slot_key_index`) extracted specifically so
   they're testable without a display.
3. `tests/test_renderer_player_input.py`, `SDL_VIDEODRIVER=dummy`: posts
   scripted sequences of real `pygame` events through `renderer.run()`
   (given a new `max_frames` parameter to bound the loop) and asserts on
   resulting `Battle` state — covers the actual wiring between pygame
   events and the controller/engine calls, the one layer the other two
   can't reach. Mirrors the Phase 1 dummy-driver smoke-test precedent
   (`docs/progress_update.md`), but as a committed, automated test rather
   than a one-off manual script.

**Session continuation.** Once step 3's `Session` and this step's playable
`Battle` both existed, `__main__.py` still only ever launched one
standalone `Battle` — after it ended there was no way to reach the next
one. Wired `Session` into `renderer.run()` via a new optional `session`
parameter (omit it to play one standalone battle, unchanged): the moment
`battle.is_over`, the finished battle is scored into the session
immediately (`session.advance()`, guarded by `not session.is_over and
session.current_battle is battle`) so `battles_won`/`is_over`/`result`
are accurate right away, but the *displayed* `battle` only swaps to
`session.current_battle` when the player presses **Enter** — chosen over
auto-continuing after a pause so the player gets a deliberate moment to
see the result, matching the existing explicit-end-turn feel rather than
introducing a second, timer-driven pacing model alongside it (auto-play's
`AUTO_PLAY_INTERVAL_MS` pacing already exists for a different purpose —
watching AI-vs-AI, not reviewing a result). `__main__.py`'s `main()` now
builds a `Session` (via a renamed `build_player_squad`, replacing the old
single-battle `build_demo_battle`) instead of one `Battle`.

**Bug found and fixed during manual testing:** `Session.advance()` didn't
change `current_battle` when it ended the session (win or loss) — there's
no next battle to prepare. That meant the renderer's `current_battle is
battle` guard, which relies on `advance()`'s side effect of producing a
*new* battle object to detect "already scored," stayed permanently true
once the session was over, so `advance()` fired again on every remaining
frame — silently re-incrementing `battles_won` without bound forever
(observed in practice as the win counter racing far past
`battles_total`). Fixed at the source: `Session.advance()` is now a
no-op once `self.is_over`, regardless of caller behavior — a real
engine-level correctness property (`tests/test_session.py::
test_advance_is_a_noop_once_the_session_is_over`), not just a
renderer-side patch — and the renderer's own guard was tightened to
`not session.is_over and session.current_battle is battle` so it doesn't
rely on the engine-side fix alone.

## Consequences

**Positive**

- The UI computes zero legality itself, closing the loop step 1 opened:
  every highlighted tile, every enabled ability, every valid target comes
  from `engine/queries.py`.
- `PlayerTurnController` is reusable by any future front end (a real GUI
  toolkit, a web client) since it has no rendering dependency at all —
  it only needs the current `Battle`'s `current_actor`/squads/grid.
- The cooldown-timing fix makes the engine strictly more correct for
  *any* multi-frame decision process, not just this specific UI.

**Negative / trade-offs**

- `Battle.current_actor` and the real consuming path (`_next_actor()` via
  `step()`/`take_turn()`) are two separate code paths that must agree by
  construction rather than by sharing one implementation — accepted
  because unifying them would require either mutating on every peek
  (wrong) or a more invasive caching scheme; `current_actor`'s fallback
  branch re-derives the same ordering `_next_actor()` uses
  (`turn_order.build_turn_order`), so they can't silently drift apart
  from unrelated edits to just one of them.
- No animation/art, per the doc's own explicit scope — highlights are
  flat translucent tile overlays, ability choice is number keys with text
  labels, not clickable buttons.

**Explicitly deferred (not built now)**

- Arbitrary move/act ordering beyond move-then-act — left as a `# TODO`
  per the doc's explicit allowance, not a decision.
- Undo of a *resolved* action, roster/bench, squad selection, the
  between-battle screen, animation — Phase 2b or explicitly out of scope
  per the phase doc.

## Alternatives considered

- **Free hero selection among the whole squad**, letting the player pick
  which of their heroes acts next — rejected; the engine's turn order is
  fixed slot order this phase (`engine/turn_order.py`'s own `# TODO`), so
  this would require an unrelated turn-order redesign well outside this
  step's scope.
- **Ticking cooldowns lazily inside `queries.usable_abilities`** instead
  of an explicit priming step on `Battle` — rejected: `queries` functions
  are meant to be pure/read-only per their own module contract (step 1);
  mutating hero state as a side effect of a query would violate that far
  more than the chosen fix does.
- **A menu/button-based ability picker** instead of number-key hotkeys —
  rejected per the phase doc's explicit "no menus" instruction for this
  debug-grade UI.
- **Auto-continuing to the next battle after a short pause** (reusing
  `AUTO_PLAY_INTERVAL_MS`-style pacing) instead of an explicit Enter
  press — user's explicit preference; also keeps one consistent mental
  model (every battle-ending or turn-ending moment is player-acknowledged)
  rather than mixing timer-driven and input-driven pacing in the same UI.
