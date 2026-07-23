# Phase 3 — Contested Resolution

## Goal

Replace deterministic combat resolution with **FT&G-style contested
rolls**: an action's success is the attacker's roll against the
defender's, and the margin of that contest scales its magnitude.

This is a foundational rework rather than a feature. It touches ability
resolution, the AI's scoring model, the UI's presentation of choices,
and every balance number in the project. It has almost nothing to do
with maps or terrain, which is why it is its own phase and why it comes
first — the AI's action scoring has to move from exact outcomes to
expected value, and doing that before the tactical work means it happens
once rather than twice.

**Context for why this is happening now:** deterministic resolution was
never a stated requirement. It entered the project as an opening
suggestion during ideation and was carried forward unexamined, while the
vision document simultaneously described Track 3 as contested checks
with rerolls on failure. Randomness was always in the design; it had
been quarantined into a deferred track and every phase doc was told to
keep `rng` unused. That plumbing (ADR 0001) now gets used for what it
was threaded through for.

---

## In Scope

### 1. The contested roll

- An action's resolution is **attacker roll vs. defender roll**.
- Both sides derive from **weighted combinations of attributes**,
  following the precedent already set by ability damage scaling: an
  ability declares attribute weights, and so does defence. Defence is
  **Resolve plus another attribute** at a ratio to be tuned — not a
  single stat.
  - This gives Resolve a genuine role for the first time. It has been a
    dead-end since the earliest telemetry, scaling only a conditional
    heal, which is why Resolve-heavy heroes kept taking their class
    identity from their second attribute.
  - The specific companion attribute and ratio are **tuning decisions**,
    not structural ones. What matters structurally is that defence is
    data-driven and multi-attribute, exactly like attack.
- **Distribution: bell-shaped, not uniform.** Sum-of-dice or an
  equivalent construction. The width relative to attribute magnitudes is
  the single most consequential number in this phase — it decides
  whether stats or dice dominate outcomes — and belongs in config, not
  in resolution code.
  - Rationale, worth preserving in an ADR: consequences in this design
    are hard (permanent wounds, retirement pressure, death if a downed
    hero is not reached). Fat tails plus hard consequences produces
    losing a long-serving veteran to a single fluke, which is both a
    savescum trigger and corrosive to the attachment the whole project
    is built around. A bell makes attribute advantages reliable and
    catastrophic outcomes require several bad rolls rather than one.

### 2. Margin-scaled magnitude

- Damage (and other magnitudes) scale with the **margin** of the
  contest. A narrow win grazes; a decisive win lands hard. One roll
  drives both whether an action works and how much it accomplishes.
- **Scaling must be sub-linear in the margin.** This is a design
  requirement, not a tuning preference. Linear scaling would let a high
  attribute pay twice — landing more often *and* hitting harder — which
  compounds in two directions the project has actively been fighting:
  it tightens the attribute-determinism that the variance and
  differentiation work loosened, and it widens the already-4:1 gap
  between developed and undeveloped heroes.
- **A damage floor is required.** A margin of 1 producing a negligible
  result makes marginal successes feel like failures. Any landed hit
  should accomplish something worth the action.

### 3. Per-ability resolution properties

Whether an ability is contested is decided **per ability, in data**.
Two independent properties:

- **Contested or automatic.** Basic Mend, for example, lands
  automatically — you do not roll to heal an ally.
- **Magnitude variance.** Independent of the above. An automatic
  ability can still vary in how much it accomplishes; Mend should.

Both go in `data/abilities.yaml` alongside the existing scaling terms.
Do not implement automatic-success as "a contested roll the attacker
always wins" — they are different mechanics and conflating them will
make the reroll ladder in Track 3 behave strangely later.

### 4. Tunable variance throughout

Every knob is data or config, none are constants inside resolution
logic:

- Distribution width (both sides)
- Margin-to-magnitude scaling curve and its floor
- Per-ability magnitude variance
- Per-ability contested/automatic flag
- Defence attribute weights and ratio

The project's working method is measure-then-tune, and that only
functions if the things being tuned are reachable without a code change.

### 5. AI rework: expected-value scoring

The AI's non-mutating action preview currently computes exact outcomes
and picks the best. It must move to expected value:

- Score candidate actions as **probability of success × expected
  magnitude**, not a single deterministic result.
- **Kill priority becomes probability of kill**, not a boolean. An
  action with a 60% chance to finish a target is a different proposition
  from one that certainly does, and the scoring should say so.
- Healing and other utility decisions need the same treatment.

This is the largest single piece of work in the phase and the one most
likely to introduce subtle regressions, since "the AI plays slightly
worse" does not fail a test. Treat the baseline fixture discipline as
mandatory here.

Note the preview is also a likely performance hotspot — it scratch-copies
heroes to evaluate candidates, and expected-value scoring may evaluate
more candidates. See item 7.

### 6. Showing the odds

**Legibility before commitment is what makes variance feel fair rather
than arbitrary, and it is the property that replaces determinism as the
readability pillar.** It is not optional polish.

- Before committing an action, the player sees its likelihood of success
  and its expected magnitude — something in the shape of "84% to land,
  4–9 damage."
- This is two numbers where there was previously one certainty, so it
  needs more display room than the current ability selection UI has.
- Enemy intent remains telegraphed: you know what they will attempt,
  not whether it lands.

The odds shown must be computed by the **engine's preview**, the same
one the AI scores against — not recomputed in the visualizer. If the
displayed odds and the actual resolution can ever disagree, players will
find it and lose trust in the entire system.

### 7. Measurement under variance

Every experimental result the project currently relies on was measured
under deterministic resolution. Variance widens every distribution.

- **Re-measure the standing design metric** — the fraction of heroes
  whose top class track is predicted by their top attribute — after the
  rework, and report it alongside the pre-change figure.
- **Sample sizes must grow.** Expect 50-session sweeps to become 200 or
  more before differences of a few points are resolvable.
- **Paired-seed comparison moves from good practice to mandatory.**
  Marginal percentages across unpaired runs will no longer resolve
  anything useful.
- Benchmark harness runtime before and after; parallelise across seeds
  (`multiprocessing`) if the larger sweeps become uncomfortable.
  Sessions are independent, so this needs no architectural change.

---

## Explicitly Out of Scope

- **Track 3 ability training.** This phase makes Track 3 *coherent* —
  reliability ladders need failures to improve on — but does not build
  it. No ability levels, no training queue, no rerolls.
- Terrain, cover, line of sight, pathfinding, map generation, fielded
  squad size, objectives — all Phase 4a.
- Rescue, wounds, death, mission types — Phase 4b.
- Distance-based damage dropoff. Leave room for it (range is already
  per-ability and margin already scales magnitude) but do not build it.
- The career layer entirely: age, retirement, recruitment, currencies,
  the contract ladder, save/load.
- Tier 1 unlocks, Tier 2 branches, multiclassing.
- Equipment, consumables, secondary resources.
- Engineered enemy types — enemies remain hero mirrors for now.

---

## Expected Consequences

**Every balance number in the project is invalidated.** Damage values,
enemy strength ramps, XP pool sizing, recovery rates, the level
threshold — all were tuned against certainty. Expect to retune from
scratch rather than adjust, and expect that retuning to take longer than
the mechanical work.

**The AI baseline fixture must be regenerated.** Battles are no longer
reproducible from the same seed under the old resolution, so the
existing fixture becomes meaningless rather than merely stale. Capture a
fresh baseline at the end of the phase and say so explicitly. Seeded
reproducibility itself must be preserved — the same seed must still
produce the same battle — or the entire experimental method breaks.

**ADRs are warranted** for the distribution choice and its width, the
margin-scaling curve, and the expected-value scoring model.

---

## Acceptance Criteria

1. Ability resolution is a contested roll between weighted attribute
   combinations on both sides, with defence data-driven and
   multi-attribute rather than a single hardcoded stat.
2. The roll distribution is bell-shaped, with its width a named config
   constant; a test asserts the empirical distribution matches the
   intended shape.
3. Magnitude scales sub-linearly with contest margin, with a floor
   ensuring any success accomplishes something meaningful. Tested at
   margin extremes.
4. Contested-vs-automatic and magnitude variance are independent
   per-ability data properties; Basic Mend lands automatically and
   varies in amount.
5. All variance knobs are reachable in data or config; no distribution
   parameters, scaling constants, or floors are embedded in resolution
   logic.
6. The AI scores actions by expected value, with kill priority expressed
   as probability of kill; regression-tested against a freshly captured
   seeded baseline.
7. The player sees success likelihood and expected magnitude before
   committing an action, computed by the engine preview rather than
   recalculated in the visualizer. A test asserts displayed odds and
   actual resolution agree over many trials.
8. Seeded battles remain exactly reproducible.
9. The standing predictability metric is re-measured under the new
   model with paired seeds and adequate sample size, and reported
   against the pre-change figure.
10. Harness runtime benchmarked before and after, with parallelisation
    applied if needed.
11. `uv run ty check` passes cleanly; `uv run pytest` passes.

---

## Suggested Build Order

1. **Capture a final deterministic baseline** and record the current
   predictability figure — after this phase the old fixture is
   meaningless, so anything worth comparing against must be captured
   now.
2. **The roll itself**: distribution, contested comparison, defence
   weighting. Pure functions, exhaustively testable in isolation.
3. **Margin-to-magnitude scaling** with its floor.
4. **Per-ability resolution properties** in YAML; migrate the four
   basics.
5. **AI expected-value scoring.**
6. **Odds display** in the visualizer.
7. **Re-measure, retune balance, capture the new baseline.**

Steps 2–4 are headless and should be nearly fully tested before step 5
begins. Step 7 is the long one.
