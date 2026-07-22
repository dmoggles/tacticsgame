# Phase 1 — Core Loop & Track 1 Progression

## Goal

Build the smallest possible vertical slice that proves out the core
battle loop and the first progression track (level/attributes), with
Track 2 (specialization) XP accumulating silently in the background
for future use. No classes, no ability unlocks, no tier system, no
equipment, no resources, no player input beyond stepping through a
debug visualizer.

This phase is about validating the *shape* of the simulation, not
tuning it. Numbers should be reasonable placeholders, not final
balance.

---

## In Scope

### 1. Attributes

Four attributes, per prior design discussion:

- **Might**
- **Focus**
- **Resolve**
- **Agility**

No derived stats beyond these for now except HP (see Hero Synthesis
below) — no secondary resources (energy/mana), no dodge/crit formulas
yet.

### 2. Hidden Affinity & Hero Synthesis

Each hero has a hidden, never-displayed affinity vector across the
four attributes, generated via a **Dirichlet distribution** (so the
four weights are positive and sum to 1). This vector is stored on the
hero but must never be surfaced in any log, UI, or debug output aimed
at the player — it's fine (and expected) to log it during dev/testing
for verification purposes, but keep that clearly separated from
player-facing output.

**Starting hero synthesis (level-0 generation):**

- All four attributes start at a base value (config constant,
  suggest `1` as placeholder — call it `BASE_ATTRIBUTE_VALUE`).
- Apply **5 simulated level-ups**, each granting **3 points**,
  distributed across the four attributes weighted by the hero's hidden
  affinity vector (i.e. each point-allocation draws proportionally to
  the affinity weights — sampling with those weights, not just
  multiplying and rounding, so there's genuine variance run to run).
  This nets 15 total allocated points on top of the base values.
- This process has **no player influence** — it's pure synthesis at
  hero creation time, used to produce the starting roster.
- Result: each starting hero has a full `Attributes` object with some
  natural lean toward their hidden affinity, but with enough
  randomness in the per-point rolls that two heroes with similar
  affinity vectors won't be identical.

**Derived HP:** define HP as a simple function of Might + Resolve for
now (e.g. `HP = base_hp + (might + resolve) * multiplier`, both
config constants). This can and will change — keep it isolated in one
function so it's trivial to revise.

### 3. Basic Abilities (Track 0 — classless kit)

Every hero starts with exactly these four abilities, filling all 4
ability slots:

1. **Basic Strike** — melee physical attack
2. **Basic Shot** — ranged physical attack
3. **Basic Bolt** — ranged spell attack
4. **Basic Mend** — heal

**Resolution for Phase 1: fully deterministic, flat values.** No
contested rolls, no attribute-vs-attribute checks yet — e.g. Basic
Strike deals a flat damage amount (config constant), Basic Mend
restores a flat HP amount. This is intentionally a placeholder;
**do not build the resolution system in a way that assumes flat/free
values are permanent.** Concretely:

- Model each ability's effect as a function/strategy that takes
  `(caster: Hero, target: Hero) -> ResolutionResult`
  rather than inlining a damage number directly into battle logic.
  Swapping in attribute-scaled or contested-roll math later should
  mean changing the inside of that function, not restructuring how
  abilities are invoked.
- Ability `cost` field exists on the data model per the architecture
  doc but is unused/`None` this phase — no energy system yet.
- 4 ability slots is a fixed invariant of `Hero` regardless of what
  fills them, now or in future phases.

Using an ability accrues XP toward its corresponding **Track 2 class
XP counter** (see below) — this is the only thing Track 2 does this
phase.

### 4. Track 1 Progression (Level & Attributes) — active this phase

- Heroes accumulate **XP** from battle participation (define
  "participation" simply for now — e.g. flat XP per turn the hero
  takes an action; refine later).
- On crossing an XP threshold (config constant — a flat threshold per
  level is fine for Phase 1, no need for a scaling curve yet), the
  hero **levels up**:
  - Gains 3 attribute points, distributed via the same
    weighted-by-hidden-affinity process used in initial synthesis.
  - No manual/deterministic point allocation yet — that mechanic
    (training-facility-gated manual point control) is explicitly
    **out of scope** this phase. All level-up points are
    affinity-weighted-random for now, in-battle or otherwise.

### 5. Track 2 Progression (Class XP) — accumulate only, no payoff

- Four counters per hero: **Fighter, Marksman, Caster, Healer**.
- Using the corresponding basic ability increments that counter by
  some config amount.
- **No thresholds fire, no unlocks happen, no tier-1 archetypes are
  granted this phase.** These counters exist purely so the accrual
  logic and data model are in place; they should be visible in the
  debug visualizer/logs for verification but have zero gameplay
  effect yet.

### 6. Battle Grid

- **8 columns × 12 rows.**
- Simple tile-based positions (integer x/y), no terrain/elevation/
  obstacles yet.
- **Movement range per turn: flat constant, identical for all heroes.**
  Not attribute-scaled yet (Agility does not affect movement this
  phase — it's tracked on the hero but has no gameplay effect yet,
  which is fine and expected).

### 7. Squad Setup

- **2 heroes per side** for this phase (player squad vs. enemy squad).
- Config-driven squad size, not hardcoded — see architecture doc.
  Future phases will move to 4 active + bench; the data model should
  not assume exactly 2 anywhere in the engine layer.

### 8. Turn Order

- Simple, fixed placeholder scheme is acceptable — e.g. player heroes
  act in slot order, then enemy heroes act in slot order, repeat.
  Explicitly **not** initiative/Agility-based yet. Flag this clearly
  as a placeholder (`# TODO(phase2): agility-based initiative`) so
  it's not mistaken for a final decision.

### 9. Enemy AI

Primitive rule-based decision-making, e.g. a simple priority list
evaluated each enemy turn:

1. If a hero is within ability range, use an ability against the
   nearest/lowest-HP valid target (pick one simple rule, doesn't need
   to be smart).
2. Otherwise, move toward the nearest hero (within movement range).

This should live in `engine/ai.py` as a swappable strategy — future
phases will likely want smarter or per-enemy-type AI, so keep the
decision function isolated rather than inlined into the battle loop.

### 10. Win/Loss Condition

- Battle ends when one side's heroes are all reduced to 0 HP.
- No draws, no turn limits, no objective tiles yet.

### 11. Debug Visualizer (Pygame)

- Passive renderer only — draws the 8x12 grid, hero positions
  (simple shapes/labels are fine, no sprites/art needed), current HP
  per hero, and whatever's useful for verifying state (e.g. current
  turn indicator, last action taken).
- **No menus, no animation, no player input for choosing
  actions/targets.** The only interactivity needed is stepping through
  the simulation — e.g. spacebar to advance one turn, or an
  auto-play mode that steps on a timer. This is a tool for watching
  the engine's own decisions play out, not a game UI.
- Must read from engine state only — see the hard separation rule in
  the architecture doc. If the visualizer needs something the engine
  doesn't expose, add a read method to the engine, don't reach into
  internals.

---

## Explicitly Out of Scope for Phase 1

To avoid scope creep, the following are **not** part of this phase
even though they've been discussed in design conversations:

- Tier 1 archetype unlocks (Fighter/Marksman/Caster/Healer becoming
  "real" — perk trees, upgraded actions, stat leans)
- Tier 2 specialization branches (Vanguard/Duelist/Controller/etc.)
- Multiclassing and its tradeoff penalties
- Manual attribute point allocation / training facilities
- Ability training/leveling (Track 3) — abilities are static this
  phase, no leveling of ability power
- Contested-roll resolution math (attribute vs. attribute checks)
- Any secondary resource (energy, mana, stamina cost enforcement)
- Equipment/items
- Real player input for actions/targeting — battles this phase can be
  fully AI-vs-AI (both sides), or player-squad-vs-AI-squad with
  player actions scripted/randomized rather than truly interactive —
  whichever is simpler to stand up first. Genuine player control is a
  later phase.
- Meta-progression, run structure, currency, between-battle screens

---

## Acceptance Criteria

Phase 1 is done when:

1. A script/test can synthesize a roster of level-0 heroes with hidden
   affinity vectors and verify the 15-point distribution lands
   correctly (statistically, across many synthesized heroes — hidden
   affinity should visibly correlate with resulting attribute leans
   over a large sample).
2. A full battle (2v2, 8x12 grid) can run start-to-finish headlessly
   (no pygame) via a test, resolving to a win/loss based on HP.
3. The same battle can be watched via the Pygame debug visualizer,
   stepping turn-by-turn, and the visualized state matches what the
   headless engine reports.
4. Heroes gain Track 1 XP through battle participation and level up
   correctly (weighted-random 3-point allocation) mid-battle or
   between battles (whichever is simpler to test first).
5. Track 2 class XP counters increment correctly based on ability
   usage and are inspectable (log or visualizer overlay), with no
   downstream effects yet.
6. `ty check` passes cleanly across the whole project.
