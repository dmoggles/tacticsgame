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
