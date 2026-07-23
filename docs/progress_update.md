# Progress Updates

## 2026-07-15 — Architecture Setup (`docs/01_architecture_setup.md`)

Scaffolded the project per the architecture doc. This doc has no formal
acceptance criteria list (it's the stable technical foundation, not a
gameplay phase), so "done" is measured against what it specifies:

- Initialized as a `uv`-managed project (`pyproject.toml`, `uv.lock`,
  `.python-version` pinned to 3.12) with a `src/tactics_game/` layout.
- Runtime dependency added: `pygame`. Dev dependencies added: `ty`, `pytest`.
- Directory layout created matching the doc exactly: `models/`, `engine/`,
  `visualizer/`, `config.py`, plus `tests/`. All files are currently empty
  stubs (no logic yet) — this milestone was structural only.
- Entry point wired as `src/tactics_game/__main__.py`, runnable via
  `uv run python -m tactics_game` (confirmed working, prints placeholder
  greeting). `pyproject.toml`'s `project.scripts` entry updated to match.
- Verified: `uv run ty check` passes cleanly; `uv run pytest` runs and
  correctly reports 0 tests collected (stub test files are empty).
- Committed as `7c18ed5`.

**Deviations from the doc:** none of substance. The doc's example commands
show `uv init tactics-game` creating a fresh subdirectory; since this repo
already existed with docs/CLAUDE.md in place, `uv init .` was used instead
to initialize in place, with `--package` added to get the `src/` layout
(plain `--app` alone produces a flat `main.py` layout, not `src/`).

**Deferred:** no actual game logic — models, engine, and visualizer are
empty files. That work starts with Phase 1 (`docs/02_phase1_definition.md`).

## 2026-07-15 — Phase 1: Core Loop & Track 1 Progression (`docs/02_phase1_definition.md`)

Implemented the full vertical slice: hero synthesis, the classless basic
kit, a headless battle loop, primitive enemy AI, and a passive pygame
debug visualizer.

**Acceptance criteria — all met:**

1. Hero synthesis (`engine/progression.py`) — `generate_hidden_affinity`
   builds a Dirichlet(1,1,1,1) sample from four `random.gammavariate`
   draws (no numpy dependency needed); `synthesize_starting_attributes`
   applies 5 simulated level-ups of 3 affinity-weighted points on top of
   base 1s. `test_progression.py::test_hidden_affinity_correlates_with_synthesized_attributes`
   synthesizes 500 heroes and asserts `statistics.correlation` between
   each attribute's affinity weight and its resulting value is > 0.5
   (observed ~0.8+) — hidden affinity never appears in any player-facing
   path, only in this dev-verification test.
2. `engine/battle.py`'s `Battle` runs a full 2v2, 8x12 headless battle
   to a win/loss via `run_to_completion()`; covered by
   `test_battle.py::test_battle_runs_headlessly_to_a_win_or_loss` across
   10 seeds with zero pygame involvement (`models/` and `engine/` were
   grepped to confirm no `pygame`/`visualizer` references).
3. `visualizer/renderer.py` reads `Battle` state directly every frame
   (no copy/serialization step), so visualized state matches the
   headless engine by construction. Verified with a scripted smoke test
   using `SDL_VIDEODRIVER=dummy` that steps a real `Battle` through 40
   frames of actual render calls with no exceptions, correct HP/position
   display, and a clean win resolution.
4. Track 1 XP accrues every turn an actor takes an action
   (`config.XP_PER_ACTION`); crossing `config.XP_LEVEL_THRESHOLD`
   triggers `_level_up`, looping to handle multi-level XP jumps in one
   call. Covered directly in `test_progression.py` (single level-up,
   multi-level jump, below-threshold no-op) and indirectly in
   `test_battle.py` (heroes reach level 2+ over a full battle).
5. Track 2 class XP counters (`Fighter`/`Marksman`/`Caster`/`Healer`)
   increment via `progression.grant_class_xp` on ability use and are
   visible in the visualizer sidebar; `test_resolution.py` confirms
   only the used ability's track increments, `test_battle.py` confirms
   nonzero accrual over a full battle. No thresholds/unlocks exist.
6. `uv run ty check` passes cleanly across the whole project.
   `uv run pytest` passes all 17 tests.

**Design notes / deviations:**

- Dirichlet sampling uses the standard Gamma-normalization construction
  via stdlib `random.gammavariate` rather than adding `numpy` as a
  dependency — not called out in the phase doc, but keeps the dependency
  footprint unchanged from the architecture doc.
- Ability effect functions (`engine/resolution.py`) both mutate `target`
  and return a `ResolutionResult`, matching the phase doc's
  `(caster, target) -> ResolutionResult` signature literally, so
  swapping in contested-roll math later changes only function bodies.
- Movement and ability range both use Manhattan distance on the 8x12
  grid; movement is a straight-line greedy step toward the target
  (no obstacles/terrain exist yet, so this is equivalent to any other
  shortest path).
- Enemy AI (`engine/ai.py`) only ever selects non-heal abilities as
  attacks — `Basic Mend`'s effect and Track 2 Healer accrual are
  exercised directly in `test_resolution.py` rather than via AI, since
  the phase doc's priority list doesn't specify heal-target selection
  logic and inventing one felt like scope creep beyond "doesn't need to
  be smart."
- `Basic Shot` and `Basic Bolt` share the same placeholder range
  (`config.BASIC_SHOT_RANGE == BASIC_BOLT_RANGE == 4`), so in practice
  the AI's first-match tie-breaking means Bolt is rarely chosen over
  Shot in a real battle. Both are still fully implemented and unit
  tested independently; this is a placeholder-number artifact, not a
  bug, and can be tuned later without touching any structure.
- `__main__.py` now builds a demo 2v2 battle (`build_demo_battle`,
  squad-size-agnostic via `config.SQUAD_SIZE`) and launches the
  visualizer — `uv run python -m tactics_game` is the way to watch a
  battle interactively (space to step, `A` to auto-play, Esc to quit).

**Deferred (per phase doc's explicit out-of-scope list):** Tier 1/2
archetype unlocks, multiclassing, manual attribute allocation, Track 3
ability training, contested-roll resolution, secondary resources,
equipment, real player input, meta-progression/run structure — none of
these were touched.

## 2026-07-23 — AI, Balance & Ability-Data Refactor (post–Phase 1)

Not tied to a new phase document — this is incremental refinement and an
architectural refactor built on top of the completed Phase 1 vertical
slice, driven by playtesting and forward-looking design needs flagged
during the work itself. Two chunks of work landed since the last update:

**Combat & AI refinements** (commit `c8457e8`, merged to `main` via PR
#1):

- Basic Shot gained a minimum range (can't fire point-blank); range
  checks switched from Manhattan to proper Euclidean distance
  (`Position.distance_to`) — supersedes the Phase 1 note above that
  movement/range used Manhattan distance.
- A turn can now move up to move points **and** take an action in the
  same turn (previously mutually exclusive) — `ai.decide_turn` returns a
  `TurnDecision` with independent `destination`/`ability_decision`.
- Ability damage/healing scales with the attribute matching its
  archetype (Might→Fighter, Agility→Marksman, Focus→Caster, Resolve→
  Healer), so hero builds now meaningfully differentiate which ability
  they're best at (numbers lived in `config.py` at this point; moved to
  YAML in the second chunk below).
- AI reworked to prefer the strongest reachable attack (scored via a
  non-mutating preview of the real resolution math, with a kill-priority
  bonus), fall back to a ranged attack when melee is unreachable that
  turn, and heal a critically injured ally or self before attacking —
  supersedes the Phase 1 note above that AI never selected heal
  abilities.
- Basic Mend given a 3-turn cooldown, tracked per-hero (`Hero.
  cooldowns`) and enforced in AI targeting.
- Debug visualizer gained a toggleable hero-card view (`C` key), sized
  to its own content, and a full-width message bar below the grid so
  combined move+ability event text no longer overruns the sidebar.

**Ability data moved to YAML** (commit `cf37c96`, branch `feature/
ability-data-yaml-refactor`, not yet merged): replaced per-ability
`config.py` constants and four hand-written resolution functions with
`data/abilities.yaml` + `data/class_tracks.yaml`, loaded and validated by
new `engine/ability_library.py` / `engine/class_track_library.py`
modules. Full rationale, alternatives considered, and consequences are
recorded in `docs/adr/0001-ability-data-yaml-refactor.md` — summary:

- `Ability.class_track` removed entirely; classes now own/reference
  abilities via a separate data file, not the reverse.
- An ability's effect is a list of components (so one ability can have
  multiple effects, e.g. damage + self-heal), each with a list of
  attribute-scaling terms (so one effect can scale off multiple
  attributes) — both were previously single values.
- `AbilityEffect` gained an unused `rng: random.Random` parameter,
  threaded through every call site now so future semi-random/contested
  resolution won't need a second breaking signature change.
- Fixed a latent AI bug this design surfaced: the non-mutating attack
  preview in `ai.py` only scratch-copied the target, not the caster —
  safe today, but would have let a future caster-directed effect (e.g.
  self-heal) apply for real during evaluation.

Also added a persistent instruction in `CLAUDE.md` to write an ADR for
future non-trivial design decisions, and corrected two things `CLAUDE.md`
had gone stale on: the "no code exists yet" project-status blurb, and an
outdated ability-effect signature reference.

**Verification:** `uv run pytest` — 37 tests pass (up from 17 at Phase 1
completion: 14 new/rewritten across `test_resolution.py`,
`test_ability_library.py`, `test_class_track_library.py`, `test_ai.py`,
`test_battle.py`). `uv run ty check` passes cleanly, including the new
`pyyaml`/`types-PyYAML` dependencies. Both chunks were also verified by
running full demo battles headlessly and by rendering the visualizer
(`SDL_VIDEODRIVER=dummy`) to confirm no regressions in damage numbers,
class-XP routing, cooldowns, or on-screen labels.

**Deferred:** everything from the original Phase 1 deferred list above
still applies. Additionally, and explicitly called out in ADR 0001: no
gear/equipment scaling, no actual random/contested rolls (`rng` is
plumbed but unused), and no multi-target/AoE ability support.

## 2026-07-23 — Phase 2a: Player Agency & Battle Continuity (`docs/03_phase2a_definition.md`)

Implemented in the phase doc's suggested build order (steps 0–4), each
landing as its own commit with its own ADR where a real design decision
was involved.

**Acceptance criteria — all met:**

1. `engine/queries.py` is the legal-action query API: `reachable_destinations`
   (a real 4-connected BFS flood-fill — strictly more correct than the
   AI's own single-path greedy walk for the general "what's reachable"
   question), `usable_abilities`, `valid_targets` (against a hypothetical
   position, so move-then-act evaluation and a move-preview UI can share
   it), and `preview_ability_outcome` (a non-mutating scratch-copy
   preview, lifted from `ai.py`). `ai.decide_turn` was refactored onto
   this API rather than computing legality itself.
   `tests/test_queries.py` includes a dedicated check that `ai.decide_turn`'s
   output is always contained in what the query layer reports as legal,
   across several constructed board states. See ADR 0002.
2. A human can play a full battle to a win or loss through the visualizer:
   select the active hero (click or Tab), move (click a highlighted
   reachable tile or skip), choose an ability (1–4, cooldown-gated ones
   marked and rejected) or skip, choose a target (click a highlighted
   valid target), cancel any in-progress choice a stage at a time (Esc),
   and end the turn explicitly (Enter). AI-vs-AI full auto-play (`A`)
   still works unchanged. See ADR 0005.
3. AI-vs-AI auto-play still runs to completion, verified against the
   seeded baseline fixture (`tests/fixtures/ai_vs_ai_baseline.json`)
   captured on `main` before any refactoring (build-order step 0). It
   stayed bit-identical through the query-API refactor (step 1) and the
   player-input work (step 4). It needed one deliberate, documented
   regeneration after the Track 1 XP rework (step 2), since heroes no
   longer leveling up mid-battle genuinely changes combat trajectories in
   a small number of seeds — diffed field-by-field before regenerating to
   confirm every delta was attributable to that mechanism and not a bug;
   `winner` was identical across all 10 seeds throughout. See ADR 0003.
4. `models/` and `engine/` still contain zero `pygame`/`visualizer`
   imports — re-grepped after every step, including step 4 which only
   ever adds to `visualizer/`.
5. Track 1 XP is a per-battle pool (`progression.award_battle_xp`),
   awarded once on victory and split evenly across the fielded squad;
   `config.XP_PER_ACTION` and the per-turn accrual path in `battle.py`
   are gone. Downed heroes get a full share (they're never removed from
   `fielded`, so this needed no special-casing). Bench bonus XP is
   plumbed and tested at both the default zero multiplier and an
   explicit non-zero one, even though Phase 2a never has a non-empty
   bench. See ADR 0003.
6. Levelling happens at battle end; `grant_xp`'s existing multi-level-jump
   loop handles a single large pool crossing several thresholds at once,
   covered directly in `tests/test_progression.py`.
7. Heroes at 0 HP are downed, not removed — `Hero.is_alive` already gated
   turn order/targeting/occupancy correctly; the new behavior is
   `progression.revive_downed_hero` reviving them to
   `config.DOWNED_REVIVE_HP` at battle end (win or lose). A battle ends
   only when a whole fielded squad is downed, tested directly.
8. `engine/session.py::Session` runs N battles
   (`config.SESSION_BATTLE_COUNT`) with a persistent squad to
   session-win or battle-loss, headlessly (`tests/test_session.py`) and
   now through the visualizer too (`__main__.py` launches a `Session`;
   `renderer.run()` takes an optional `session` and advances to the next
   battle on an explicit Enter press once one ends). Persistence needed
   no serialization — the same `Hero` objects flow through every `Battle`
   in the session, so attributes/level/xp/class_xp carry forward by
   identity; `Session` only resets what shouldn't persist (cooldowns,
   positions, and — behind `config.FULL_HEAL_BETWEEN_BATTLES`, an
   explicit `# TODO(phase2b)` placeholder — HP). See ADR 0004 and ADR 0005.
9. `uv run ty check` passes cleanly; `uv run pytest` passes all 102 tests
   (up from 61 at the end of step 2).

**Bug found via manual testing, fixed same day:** `Session.advance()`
didn't change `current_battle` when it ended the session (there's no
next battle to prepare on a win or loss), so a UI loop that keeps calling
it every frame after the session is already over kept re-scoring the
same finished battle forever — observed in practice as the sidebar's win
counter racing far past `battles_total`. Fixed by making `advance()` a
no-op once `is_over`, regardless of caller behavior, plus tightening the
renderer's own guard to not rely on that alone. Regression-tested both at
the engine level (`test_advance_is_a_noop_once_the_session_is_over`) and
by reproducing the exact symptom through the render loop
(`test_session_progress_does_not_run_away_after_the_session_ends`). Noted
in ADR 0005 rather than a new ADR, since it's a correctness fix to a
decision recorded there, not a new one.

**Design notes / deviations:**

- Cooldown ticking moved from "start of turn resolution" to "the instant
  an actor becomes current" (`Battle._tick_current_actor_cooldowns`,
  primed in `__post_init__` and at the end of `_resolve_turn`). Not
  planned upfront — surfaced because a human can spend many UI frames
  deciding a turn, during which `queries.usable_abilities` must already
  reflect this turn's ticked cooldowns, not last turn's. Verified
  behaviorally identical for the AI path (same values, just computed
  earlier), so the baseline fixture needed no change for this. See ADR 0005.
- `TurnDecision`/`AbilityDecision` moved from `engine/ai.py` to a new
  `engine/turn.py` — they represent a turn's shape regardless of who
  decided it (AI or a human via `visualizer/player_input.py`), and
  leaving them in `ai.py` would have made the visualizer reach into
  AI-specific internals to build one.
- `visualizer/player_input.py::PlayerTurnController` has no `pygame`
  import at all, despite living in `visualizer/` — it's pure interaction
  logic (a state machine over `engine/queries.py` calls), kept separate
  from `renderer.py`'s event-loop plumbing specifically so it's
  unit-testable headlessly. Nearly all of the actual turn-building logic
  lives here, not in `renderer.py`.
- Testing a pygame UI without a way to drive a real window: three layers
  — headless `PlayerTurnController` unit tests, pure pixel/key-mapping
  helper tests, and one `SDL_VIDEODRIVER=dummy` integration test posting
  scripted real `pygame` events through `renderer.run()`'s actual event
  loop (`renderer.run()` gained an optional `max_frames` to bound it).
  Mirrors the Phase 1 dummy-driver smoke test, but as committed automated
  tests rather than a one-off manual script.

**Deferred (per phase doc's explicit out-of-scope list, all Phase 2b):**
roster/bench, gradual recovery, squad selection, manual attribute
allocation, the between-battle screen, telemetry. Also still deferred,
per the doc's beyond-Phase-2 list: Tier 1/2 archetype unlocks,
multiclassing, Track 3 ability training, contested-roll resolution,
consumables, secondary resources, equipment, AoE abilities, new
abilities, meta-progression, save/load across process restarts,
agility-driven initiative, terrain/obstacles. Within Phase 2a's own
scope: arbitrary move/act ordering beyond move-then-act is left as a
`# TODO` in `ai.py` (the doc explicitly allows this as a placeholder,
not a decision), and undo of a *resolved* action was never in scope
("cancel before commit" only).
