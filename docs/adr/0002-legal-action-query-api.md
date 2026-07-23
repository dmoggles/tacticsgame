# 0002. Legal-action query API as a shared engine module

## Status

Accepted

## Context

`docs/03_phase2a_definition.md` requires a read-only "what can this hero
legally do right now" API in `engine/`, built before any player-input UI
work, with `ai.decide_turn` refactored to consume it rather than computing
legality itself. Before this, `engine/ai.py` computed every piece of
legality inline and privately: `_occupied_positions` (bounds/occupancy),
`_step_toward` (a single greedy path, not general reachability),
`_on_cooldown` and inline range checks (ability/target legality), and
`_preview_magnitude` (non-mutating outcome preview).

The phase doc names the risk directly: once player input exists, the
visualizer will need to answer these same questions (which tiles can I
highlight as reachable, which targets are valid for this ability) to
drive clicks. If the UI reimplements that logic independently, "legal
per the AI" and "legal per the UI" can silently drift apart — a bug class
that presents as a confusing UI issue (a tile highlights as reachable but
the move is rejected, or vice versa) rather than an obvious logic bug.
The only way to prevent that is one shared implementation, not two that
happen to agree today.

A secondary problem: `_step_toward`'s movement legality was really "is
this specific next tile in a straight-line walk in bounds and
unoccupied," not "what tiles can this hero reach this turn" — the latter
is what a UI needs to highlight, and needs to correctly handle a hero
directly blocking the straight-line path to a farther tile that's still
reachable by going around.

## Decision

- New module `engine/queries.py` (free functions, matching the existing
  style of `progression.py`/`resolution.py`/`turn_order.py` — no query
  object/class introduced, since none of the phase's read patterns
  benefit from stateful grouping). No `models/`/`engine/` imports
  pygame/visualizer; queries.py is no exception.
- `occupied_positions(actor, allies, enemies) -> set[Position]` — moved
  verbatim from `ai._occupied_positions`.
- `reachable_destinations(actor, allies, enemies, grid) -> set[Position]`
  — **new**, not a lift. A proper 4-connected BFS flood-fill from the
  actor's position, up to `config.MOVEMENT_RANGE` hops, pruned by
  `grid.in_bounds` and `occupied_positions`, always including the actor's
  own tile. This is the general "what could a UI highlight" answer;
  `ai.py`'s own `_step_toward` — a greedy single-path walk toward one
  specific target tile — is a movement *strategy*, not a legality
  computation, and is deliberately left in `ai.py` unchanged except for
  sourcing its occupancy set from `queries.occupied_positions`. Every
  tile the greedy walk can ever produce is provably a member of the BFS
  set (each of its steps is independently bounds/occupancy-legal), so the
  two can never disagree — the greedy walk just doesn't attempt to
  enumerate every legal tile, only to pick one.
- `usable_abilities(actor) -> list[Ability]` — abilities not on cooldown.
  `Ability.cost` (see ADR 0001) is deliberately not filtered on; no
  resource system exists yet.
- `valid_targets(actor, ability, position, allies, enemies) -> list[Hero]`
  — legal targets for `ability` cast from a **hypothetical** `position`
  (not necessarily `actor.position`), so both AI's move-then-act
  evaluation and a future move-preview UI reuse the same function. Pool
  is `allies` or `enemies` per `ability.targets_ally`; filtered to
  `is_alive` and `min_range <= distance <= range`. Returns every legal
  target regardless of whether it's a *good* choice (e.g. a full-HP ally
  is still a legal heal target) — legality and strategy stay separated;
  `ai.py` applies its own HP-threshold preference on top, same as before.
- `preview_ability_outcome(caster, ability, target) -> ResolutionResult`
  — moved from `ai._preview_magnitude`, same scratch-copy-both-sides
  technique (already correct per ADR 0001's caster-copy fix), but returns
  the full `ResolutionResult` instead of a collapsed `int` magnitude, so
  a future UI can show real preview text/numbers. `ai.py`'s scoring
  becomes `result.damage + result.healing` at the call site — arithmetically
  identical to what `_preview_magnitude` returned directly.
- `ai.py`'s `_best_heal_decision` and `_best_offensive_decision` now
  source usability/targeting/preview from `queries.*` instead of private
  duplicates; `decide_turn`, `_decide_heal`, `_decide_attack`,
  `_most_injured_ally`, and `_step_toward`'s pathing algorithm are
  unchanged — they're strategy, not legality.
- Correctness verified two ways: the pre-existing AI-vs-AI baseline
  fixture (`tests/fixtures/ai_vs_ai_baseline.json`, captured on `main`
  before this refactor) still matches exactly, proving the move is
  structural; and a new `tests/test_queries.py` asserts, across several
  constructed board states, that every field of `ai.decide_turn`'s output
  is contained in what the query layer reports as legal.

## Consequences

**Positive**

- One implementation of "what's legal" that both the AI and, starting
  with build-order step 4, the player-facing UI will consume — the UI
  can never compute its own legality now that `queries.py` exists as the
  obvious place to add anything it needs.
- `reachable_destinations` is genuinely more correct than the old
  AI-only movement check for the general question (finds detours around
  a single blocking hero); `valid_targets`/`preview_ability_outcome`
  returning full objects instead of a bare bool/int gives a future UI
  richer information (which targets are legal, what a hit would actually
  do) for free.
- AI-vs-AI behavior is unchanged and verified against the pre-refactor
  baseline fixture, not just "looks the same by eye."

**Negative / trade-offs**

- `reachable_destinations` is now the *complete* legal set, computed via
  flood-fill; the AI's own `_step_toward` still only produces one path.
  A future UI that highlights `reachable_destinations` will show more
  options than any single AI move ever uses — intended (that's the point
  of exposing full legality to the UI), but worth naming so it doesn't
  read as an inconsistency later.
- `valid_targets` takes 5 positional-ish parameters (actor, ability,
  position, allies, enemies); acceptable for Phase 2a's scope, revisit if
  it grows further once the UI is calling it directly.

**Explicitly deferred (not built now)**

- No caching/memoization of `reachable_destinations` — flood-fill over an
  8x12 grid is cheap; revisit only if profiling says otherwise.
- No `Ability.cost` filtering in `usable_abilities` — no resource system
  exists yet (ADR 0001).
- Player-input wiring that actually calls this API from the visualizer —
  that's build-order step 4, not this step.

## Alternatives considered

- **A stateful `BattleQueries`/`LegalActions` object** wrapping
  `(battle, actor)` — rejected for now; every function here is a pure
  computation over explicit arguments, matching the free-function style
  already used throughout `engine/`, and there's no shared setup cost
  that would justify an object.
- **Making `ai.py`'s `_step_toward` itself BFS-optimal** (shortest path
  around obstacles) instead of leaving its greedy single-path heuristic
  as-is — rejected for this step: it would be a genuine AI behavior
  change, which the phase doc explicitly wants deferred/justified
  separately rather than smuggled into a "just a refactor" step, and it
  isn't needed for `reachable_destinations` (the UI-facing legality
  question) to be correct.
- **Filtering `valid_targets` to only "worthwhile" targets** (e.g.
  excluding full-HP allies from heal targets) — rejected; that's a
  strategy preference, not a legality fact, and belongs in `ai.py`'s own
  heuristics (and eventually player judgment), not in the shared legality
  layer.
