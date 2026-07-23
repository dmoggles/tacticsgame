# Phase 2a — Player Agency & Battle Continuity

## Goal

Turn the Phase 1 simulation into something a human plays, across a
sequence of battles rather than a single demo.

Two things land here:

1. **Player control** of the fielded squad — real selection, movement,
   and targeting input, replacing AI decisions on the player's side.
2. **Battle continuity** — a chain of battles fought by a persistent
   squad, with hero state carrying across.

Alongside these, one **corrective rework**: Track 1 XP moves from
per-action accrual to a per-battle pool (see section 5). This is a
design-fidelity fix, not tuning — see the rationale in that section.

Phase 2a deliberately adds **no new progression systems.** Manual
attribute allocation, roster/bench, and the between-battle screen are
all Phase 2b. Tier 1 archetype unlocks remain out of scope entirely —
see "Why Tier 1 is deferred".

---

## In Scope

### 1. Legal-action query API (`engine/`)

The architectural core of this phase. Build it first, before any input
handling.

The engine must expose read-only queries answering "what can this hero
legally do right now":

- Reachable destinations for a given hero this turn (move points, grid
  bounds, occupancy).
- Usable abilities for a given hero (cooldowns, and the ability `cost`
  field if/when a resource system exists).
- Valid targets for a given hero + ability + hypothetical position
  (min/max range via `Position.distance_to`, ally vs. enemy targeting).
- A **non-mutating preview** of an ability's outcome against a target,
  reusing the real resolution math. `ai.py` already does this
  internally, including the caster-scratch-copy fix from ADR 0001 —
  that logic should be **lifted out of `ai.py` into the shared query
  layer**, not duplicated.

Requirements:

- `ai.decide_turn` must be **refactored to consume this API** rather
  than computing legality itself. One source of truth for "what's
  legal" is the entire point: if the UI and the AI can disagree about
  reachability or valid targets, that is a bug class that will present
  as a UI bug and waste a lot of time.
- The API lives in `engine/` and imports nothing from `visualizer/`.
  The architecture doc's hard separation rule gets its first real test
  here: **the UI must never compute legality itself, and never reach
  into engine internals to do so.** If the UI needs something, add a
  query method.
- All queries are pure and read-only. Nothing in this layer mutates
  battle state.

### 2. Player turn control

The player controls the fielded squad; the AI continues to control the
enemy side.

Interaction model — keep it crude, this is still debug-grade UI:

- Select an active hero (click, or cycle with a key).
- See reachable tiles highlighted; click one to move, or decline.
- Select one of the hero's 4 abilities; see valid targets highlighted;
  click one to resolve.
- Move and action remain **independent within a turn** (per the
  post-Phase-1 change) — a hero may do either, both, or neither. If
  supporting arbitrary ordering is awkward, move-then-act is
  acceptable; mark it `# TODO` as a placeholder rather than a decision.
- End turn explicitly.
- **Cancel before commit:** movement and ability selections are
  cancellable up until they resolve. Undo of a *resolved* action is out
  of scope — this is "I clicked the wrong hero" protection only.

The visualizer is promoted from passive renderer to interactive UI, but
its remit stays narrow: highlight state, take clicks/keys, call into
the engine. No animation, no art, no menus.

**Keep AI-vs-AI auto-play working** alongside player control. It
remains the fastest way to smoke-test the engine and losing it would be
a real regression in iteration speed. A key toggle or CLI flag to run a
battle fully AI-driven is a deliverable, not a nice-to-have.

### 3. Class XP visibility at the point of decision

Track 2 accrual must be visible **while the player is choosing**, not
only in a post-hoc counter. When choosing between Basic Strike and
Basic Bolt, the player should see which class track each choice feeds.

This matters more than it sounds. The design intent is that
specialization is *steered*, not stumbled into. If the player can't see
the action→track connection while choosing, Track 2 degrades into an
invisible side-effect. A small label on the ability (e.g. "→ Caster")
plus the existing running counters is sufficient.

### 4. Downed, not dead

Reaching 0 HP means a hero is **downed**, not removed from the roster:

- A downed hero is out for the remainder of the current battle.
- At battle end, a downed hero revives at a minimal HP value (config
  constant).
- Recovery from that low HP is a Phase 2b concern (bench regen). For
  Phase 2a, the placeholder heal rule in section 6 covers it.
- A battle is lost when **all fielded heroes are downed**. Individual
  heroes are never permanently lost in this phase.

This supersedes Phase 1's terminal-at-0-HP model and aligns with the
vision doc's soft-permadeath intent. It also means recovery-over-time
in 2b needs no separate injury system — it's just HP.

### 5. Track 1 XP rework: per-battle pool

**This supersedes `config.XP_PER_ACTION` and the per-turn accrual path
in `battle.py`. The old path must be removed, not left alongside.** It
will break the Phase 1 test asserting heroes reach level 2+ over a
single battle; that test should be rewritten against the new model.

**Rationale (do not "simplify" this back):** the design separates Track
1 as the "just showing up" track from Track 2 as the "what you actually
did" track. Per-action accrual collapsed that distinction — both tracks
were fed by the same signal, one merely filtered by ability type. A
per-battle pool restores the separation: Track 1 measures presence,
Track 2 measures usage.

**Mechanics:**

- On battle victory, compute a **total XP pool** derived from the enemy
  squad's count and strength.
- "Strength" needs a definition that doesn't exist yet. Sum of enemy
  levels is the cheap version; sum of enemy attributes reflects the
  actual spread. Either is fine — but isolate it in **one clearly
  marked function**, since it's exactly the number that will be revised
  repeatedly.
- The pool is **split evenly among the fielded heroes.** This is
  deliberate: fielding fewer heroes concentrates XP into each, creating
  a real risk/reward decision (grow faster, fight short-handed). It is
  not a bug to be balanced away.
- Downed heroes count as fielded and receive a full share. They were
  present; the downed state and its recovery time are already the
  penalty.
- **Bench bonus XP:** benched heroes receive
  `BENCH_XP_BONUS_MULTIPLIER * pool`, split evenly among them. This is
  a *bonus* computed on top of the pool, not a slice taken out of it —
  fielded heroes' shares are unaffected. **The multiplier defaults to
  0**; it becomes upgradeable through meta-progression investment in a
  much later phase. Implement the plumbing and the config constant now
  even though it evaluates to zero.
  - (In Phase 2a there is no bench, so this path is unexercised. Build
    it anyway — 2b turns it on, and retrofitting it into the award
    function later means touching this logic twice.)
- Levelling therefore happens at **battle end**, not mid-battle. The
  existing multi-level-jump loop in `_level_up` should be retained.
- Track 2 class XP accrual is **unchanged** — still per ability use,
  during battle.

### 6. Session chaining

- A **session** (working term — deliberately not "run", since run
  structure is undesigned) is a sequence of N battles, N from config.
  Suggest 5 as a starting value.
- The player's squad **persists across battles**: attributes, level,
  XP, class XP. Cooldowns and positions reset per battle.
- Enemy squads are regenerated per battle. No difficulty curve this
  phase — flat or trivially-scaled is fine, in a single clearly-marked
  generator function.
- Session ends when all battles are won, or when a battle is lost (all
  fielded heroes downed).
- **HP between battles: full heal, as an explicit placeholder.** Put it
  behind a config constant and mark it `# TODO(phase2b)`. Gradual
  recovery replaces this in 2b; full heal exists here only so that 2a
  doesn't produce a death spiral in the absence of a bench.

---

## Why Tier 1 is deferred

Tier 1 archetype unlocks are the natural next feature and are
explicitly not in Phase 2 at all. The dependency runs the wrong way:
unlock thresholds are a balance decision, and thresholds tuned against
AI-driven usage won't survive contact with a human who has favourite
abilities. Phase 2 produces the data that makes those thresholds real
rather than guessed.

---

## Explicitly Out of Scope

Deferred to **Phase 2b**: roster/bench, gradual recovery, squad
selection, manual attribute allocation, the between-battle screen,
telemetry.

Deferred beyond Phase 2 entirely:

- Tier 1 archetype unlocks, perk trees, upgraded actions
- Tier 2 specialization branches
- Multiclassing and its tradeoffs
- Training facilities / variable manual-allocation counts
- Track 3 ability training
- **Contested-roll resolution.** `rng` stays plumbed and unused. The
  temptation is real now that the parameter exists everywhere, but
  ability *levels* changing resolution reliability is a Track 3
  mechanic and Track 3 does not exist. Resolution stays deterministic.
- Consumables (instant-heal items) — these imply a currency and reward
  economy downstream of run structure
- Secondary resources (energy/mana) — `cost` remains optional/unused
- Equipment/gear
- AoE / multi-target abilities
- New abilities beyond the four basics
- Meta-progression, rewards, currency
- The roguelite-vs-persistent run structure decision
- Save/load persistence across process restarts — a session lives in
  memory
- Agility-driven initiative — turn order stays the Phase 1 placeholder
- Terrain, obstacles, elevation, telegraphed enemy intent

---

## Acceptance Criteria

Phase 2a is done when:

1. `engine/` exposes a legal-action query API covering reachable tiles,
   usable abilities, valid targets, and non-mutating outcome preview;
   `ai.decide_turn` consumes it rather than computing legality itself,
   with tests asserting the AI and the query layer agree on legality
   across a set of constructed board states.
2. A human can play a full battle to a win or loss through the
   visualizer: selecting heroes, moving, choosing abilities and
   targets, cancelling selections, ending turns.
3. AI-vs-AI auto-play still runs to completion, behaviourally unchanged
   from before the refactor — verified against the seeded baseline
   fixture captured in build-order step 0, which must predate the
   refactor. Any intentional deviation is documented rather than
   absorbed by regenerating the fixture.
4. `models/` and `engine/` still contain zero `pygame`/`visualizer`
   imports (re-grepped), and the UI computes no legality of its own.
5. Track 1 XP is awarded as a per-battle pool split evenly among
   fielded heroes; `XP_PER_ACTION` and the per-turn accrual path are
   gone. Tests cover: pool scales with enemy count/strength, even split
   across fielded heroes, downed heroes receive a full share, bench
   bonus evaluates to zero at the default multiplier and to the
   expected value when the multiplier is non-zero.
6. Levelling occurs at battle end, including correct multi-level jumps
   from a single large pool.
7. Heroes reaching 0 HP are downed rather than removed, revive at
   minimal HP at battle end, and a battle is lost only when all fielded
   heroes are downed.
8. A session of N battles runs end to end with a persistent squad,
   resolving to session-win or battle-loss.
9. `uv run ty check` passes cleanly; `uv run pytest` passes.

---

## Suggested build order

0. **Capture an AI-vs-AI behavioural baseline before touching anything.**
   On current `main`, run a fixed set of seeded AI-vs-AI battles (ten is
   plenty) and record their outcomes — final HP, positions, turn count,
   winner, and per-hero class XP totals. Commit this as a regression
   fixture.

   This must happen **first**, before the refactor in step 1. Acceptance
   criterion 3 asks for the AI to be behaviourally unchanged after the
   refactor, and that is unverifiable if the baseline is captured
   afterwards — at that point it records post-refactor behaviour and the
   check becomes tautological. The failure mode being guarded against is
   an AI that still passes every functional test but makes slightly worse
   decisions, which is easy to introduce while moving heuristic logic
   between modules and very hard to notice by eye.

   If a deliberate behavioural change to the AI turns out to be necessary
   during step 1, that's fine — update the fixture, and say so explicitly
   in the progress update and the accompanying ADR. What must not happen
   is the fixture being regenerated silently to make a failing comparison
   pass.

1. Legal-action query API + AI refactor onto it — pure engine work,
   fully testable headlessly, no UI involved.
2. Track 1 XP rework + downed state — also headless, also fully
   testable, and it touches battle resolution which step 3 depends on.
3. Session/battle-chaining data model and squad-state persistence.
4. Player input in the visualizer, built on a query layer that is by
   then already proven.

Steps 1 and 2 are the ones worth being careful about; 3 and 4 are
comparatively mechanical once those are right.
