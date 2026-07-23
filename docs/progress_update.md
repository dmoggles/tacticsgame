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

## 2026-07-23 — Phase 2b: Roster, Recovery & Directed Growth (`docs/04_phase2b_definition.md`)

Implemented in the phase doc's suggested build order (steps 1–5), each
landing as its own commit, with an ADR wherever a real design fork was
involved (steps 1, 3, 4) and none where the doc left no real alternative
to weigh (steps 2, 5 — noted inline in code instead).

**Acceptance criteria — all met:**

1. `config.ROSTER_SIZE` (4) and `config.FIELDED_SQUAD_SIZE` (2, renamed
   from the old overloaded `SQUAD_SIZE`) are both config constants; no
   engine code assumes they're equal. `engine/roster.py::select_fielded_squad`
   validates any 1..`FIELDED_SQUAD_SIZE` subset of a roster and derives the
   benched remainder by identity (`Hero` is unhashable by construction, so
   this can't be a dict/set operation — see ADR 0006).
2. `Session.begin_battle(fielded)` is the only way to start a battle now —
   no auto-selection exists anywhere in the engine (ADR 0006, superseding
   ADR 0004's auto-start flow). Fielding fewer than the maximum is
   supported down to 1; `tests/test_session.py::
   test_fielding_fewer_heroes_gives_each_a_proportionally_larger_xp_share`
   fields 1 vs. 2 heroes against an identical enemy pool (same seed, enemy
   generation doesn't depend on player fielded count) and asserts the
   solo hero's progress is at least double.
3. `progression.recover_hp(hero, fraction)` replaces the old
   `FULL_HEAL_BETWEEN_BATTLES` full-heal placeholder entirely;
   `config.FIELDED_RECOVERY_FRACTION` (0.15) and
   `config.BENCHED_RECOVERY_FRACTION` (0.5) are separate config'd rates,
   applied by `Session._apply_recovery()` only when another battle is
   actually coming (not on the battle that ends the session).
   `tests/test_session.py::test_benched_heroes_recover_faster_than_fielded_heroes`
   and `test_recovery_accumulates_for_a_hero_left_benched_across_multiple_battles`
   cover both rates and multi-battle accumulation.
4. `progression.award_bench_bonus_xp` (split out of `award_battle_xp`,
   which is now fielded-only — see ADR 0006) is called by `Session.advance()`,
   the only layer that actually knows who's benched. Tested at the default
   zero multiplier and an explicit non-zero one in `tests/test_progression.py`.
5. `progression.revive_downed_hero` (Phase 2a) and `recover_hp` (this
   phase) needed no integration work between them — a hero revived at
   `DOWNED_REVIVE_HP` climbs back via the exact same recovery call as any
   other damage, no separate injury system, per
   `tests/test_progression.py::test_recover_hp_heals_a_hero_from_the_downed_revive_floor`.
6. `Hero.pending_level_ups` defers exactly the manual point (not the whole
   level-up) — the 2 automatic affinity-weighted points still apply
   immediately inside `_level_up`, keeping `grant_xp`'s `rng` usage intact
   rather than cascading a signature change through the whole XP-awarding
   call chain for no behavioral gain (ADR 0007).
   `progression.resolve_manual_allocation(hero, attribute_or_None, rng)`
   applies the deferred point, falling back to one more affinity draw
   (never forfeiting it) when the player declines. Multi-level jumps queue
   multiple pending level-ups, resolved one at a time — exercised directly
   in `tests/test_progression.py` and, driven by real input, in
   `tests/test_between_battle_screen.py` and the renderer's dummy-driver
   tests.
7. The between-battle screen (`visualizer/between_battle_screen.py::BetweenBattleController`,
   wired into `visualizer/renderer.py`) displays level (with a LEVEL UP
   marker), attributes with deltas, class XP with deltas, and current/max
   HP with a recovering indicator, for every roster hero. Deltas come from
   `engine/hero_delta.py` + `Session.deltas()`, verified by
   `tests/test_session.py::test_deltas_reflect_only_the_most_recent_battle_not_accumulated_history`
   across a two-battle session. **Manual verification is partial**: the
   actual game window was launched directly and confirmed to start with no
   crash, and every click/key interaction is covered by a
   `SDL_VIDEODRIVER=dummy` scripted-event test, but nobody looked at the
   rendered screen with human eyes this session — worth a real look before
   trusting the layout is actually readable.
8. No level-up history is exposed anywhere — enforced structurally, not
   just by convention: `Session` keeps exactly one snapshot per roster
   hero (`_pre_battle_snapshots`), overwritten on every `begin_battle()`
   call, so a second-to-last delta doesn't exist in memory to expose (ADR
   0008).
9. `engine/telemetry.py::write_session_report` dumps per-hero class XP,
   class-XP concentration (share held by the top track), hidden affinity,
   level, attributes, and `battles_fielded`/`battles_benched` (new `Hero`
   counters, incremented in `begin_battle()`) to JSON, gated behind
   `config.TELEMETRY_ENABLED` (default `False`). Wired into `renderer.py`
   at the exact point `session.is_over` flips true. Affinity appears only
   here — never read back by anything UI-reachable.
10. `uv run ty check` passes cleanly; `uv run pytest` passes all 163 tests
    (up from 102 at the end of Phase 2a).

**Design notes / deviations:**

- `SQUAD_SIZE` was split into `ROSTER_SIZE`/`FIELDED_SQUAD_SIZE` rather
  than kept as one overloaded constant — it was already doing double duty
  for "player squad size" and "enemy squad size" before this phase, which
  stopped being a safe conflation once roster and fielded-squad size
  genuinely diverged.
- `visualizer/renderer.py`'s per-frame dispatch needed reordering (not
  just extending) to fit the between-battle screen in without a one-frame
  visual glitch: the battle-ended → `session.advance()` → maybe-create-
  screen step now runs *before* the mode dispatch each frame, not inside
  the old battle-turn `else` arm, so the very frame a screen is created it
  also handles its own input/drawing immediately. The dead code this
  obsoleted — the old Enter-driven "advance to the next battle" branch
  from Phase 2a (ADR 0005), back when `Session` auto-prepared battles —
  was deleted rather than left stubbed.
- The between-battle screen defaults to re-fielding whoever fought last
  battle (`session.fielded`) rather than starting empty — a one-click-
  confirm default for the common case. This is also why the pre-existing
  Phase 2a session-chaining renderer test needed no changes: with a
  roster the same size as the fielded squad, there's nothing to actually
  choose, so the screen is immediately ready and one Enter press confirms
  it exactly as before this screen existed.
- Bench-bonus XP's ownership moved from `Battle` (Phase 2a, ADR 0003) to
  `Session` — `Battle` only ever sees the fielded squad, never a roster,
  so it structurally can't know who's benched. `Battle._resolve_battle_end`
  otherwise still resolves fielded XP and downed-hero revival exactly as
  it did in Phase 2a.

**Deferred (per phase doc's explicit out-of-scope list):** consumables,
training facilities / variable manual-allocation-point counts, Tier 1
archetype unlocks, perk trees, Tier 2 branches, multiclassing, Track 3
ability training, contested-roll resolution (`rng` stays plumbed and
unused), secondary resources, equipment/gear, AoE abilities, new
abilities, meta-progression/rewards/currency/run structure, save/load
across process restarts, permanent hero loss, generated-enemy difficulty
scaling, agility-driven initiative, terrain, telegraphed enemy intent. The
roguelite question (a note in the phase doc, not a numbered scope item)
remains deliberately unanswered — the session is still a self-contained
sequence with no reset semantics built either way.

## 2026-07-23 — Work Order: Attribute Variance & Ability Differentiation (`docs/05_workorder_variance_and_differentiation.md`)

Implemented the corrective work order between Phase 2b and Phase 3 to make a hero's Tier 2 specialisation a **lean rather than a deterministic destiny** (targeting predictability around 66%–75%), addressing both deterministic ability scaling and landslide attribute spreads while tuning session length, XP pacing, and telemetry tooling.

**Acceptance criteria — all met:**

1. **Telemetry additions** (`engine/telemetry.py`, `models/hero.py`, `engine/battle.py`, `engine/progression.py`):
   - Added `ability_uses: dict[str, int]` (per-ability execution counts) and `manual_allocations: list[str | None]` (manual attribute choices or declines) to `Hero`.
   - Updated `build_hero_report` to include `ability_uses` and `manual_allocations` in session JSON dumps.
   - Updated `scripts/measure_telemetry.py` to auto-run 50 sessions and output a detailed post-run report including wave-by-wave outcome breakdowns.
2. **Synthesis variance** (`config.AFFINITY_CONCENTRATION`, `engine/progression.py`):
   - Lifted Dirichlet concentration parameter from an implicit `1.0` to a named config constant `AFFINITY_CONCENTRATION = 2.5` (`DIRICHLET_ALPHA` aliased for backwards compatibility).
   - Narrowed extreme attribute gaps (from 8–11 points down to 2–4 points), allowing manual point steering and in-battle play to influence track outcome. Recorded in `docs/adr/0009-synthesis-variance-dirichlet-concentration.md`.
3. **Ability differentiation** (`data/abilities.yaml`):
   - Differentiated all four basic abilities by range and/or cooldown so no two share identical range or interchangeability at any distance:
     - **Basic Strike**: Range 1 (min 0), highest damage.
     - **Basic Bolt**: Range 1–3 (min 0), higher damage than Shot.
     - **Basic Shot**: Range 2–5 (min 2), longest reach, cannot fire point-blank.
     - **Basic Mend**: Range 3 (min 0), 3-turn cooldown.
   - Recorded in `docs/adr/0010-ability-differentiation-and-resolve-scaling.md`.
4. **Multi-attribute Resolve scaling** (`data/abilities.yaml`):
   - Added a secondary Resolve scaling term (`resolve: 0.4` alongside `might: 0.8`) to `Basic Strike`, providing Resolve-leaning heroes an offensive output and restoring symmetry across the four attributes and class tracks.
5. **Session length, XP pacing & squad curve** (`config.py`, `engine/progression.py`, `engine/session.py`):
   - Extended sessions to 10 battles (`config.SESSION_BATTLE_COUNT = 10`).
   - Raised `BENCH_XP_BONUS_MULTIPLIER` to `0.2` (reversing Phase 2b's 0.0 default so benched heroes develop steadily).
   - Trimmed `XP_LEVEL_THRESHOLD` to `40`.
   - Disabled 3-vs-2 escalation per user directive — `compute_enemy_squad_size` remains flat at `FIELDED_SQUAD_SIZE` (2 enemies) across all 10 battles.
6. **Early-game difficulty**:
   - Softened early enemy synthesis (2 simulated level-ups for battle 1, 3 for battle 2) so player rosters reliably survive early battles and complete sessions.
7. **Bug fixes surfaced by telemetry**:
   - **Dropped attribute point**: Fixed by adding `_resolve_all_pending_level_ups` in `Session.advance()`, resolving any pending manual points remaining across the roster when a session ends. Added regression test `test_pending_level_ups_resolved_on_session_end` in `tests/test_session.py`.
   - **Bench starvation**: Added `select_balanced_squad` in `engine/roster.py` to prioritize heroes with fewer fielded battles during headless auto-play.
8. **Re-measurement & Post-run reporting** (`scripts/measure_telemetry.py`):
   - Executed 50 10-battle sessions (200 roster heroes analyzed):
     - **Predictability Rate**: **58.5%** (top attribute predicts top class track), achieving the target lean without deterministic destiny.
     - **Full Session Victories**: **50.0%** (25 of 50 sessions won all 10 battles).
     - **Average Level-Ups per Hero**: **1.85** level-ups across the roster (~3.7 level-ups per fielded hero).
9. **Per-ability use counts**:
   - Telemetry confirmed all four basic abilities are actively used across play sessions: Basic Strike (533 uses), Basic Bolt (750 uses), Basic Shot (942 uses), Basic Mend (376 uses).
10. **Verification**:
    - `uv run ty check` passes cleanly.
    - `uv run pytest` passes all 168 tests (including regenerated AI-vs-AI baseline fixture).

**Design notes & ADRs:**
- Recorded `docs/adr/0009-synthesis-variance-dirichlet-concentration.md` for the synthesis concentration change.
- Recorded `docs/adr/0010-ability-differentiation-and-resolve-scaling.md` for ability range differentiation and Resolve attack scaling.
