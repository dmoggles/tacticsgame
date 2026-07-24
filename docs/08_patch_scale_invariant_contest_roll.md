# Patch — Scale-Invariant Contest Roll & Margin-Derived Damage

**Amends:** `docs/06_phase3_resolution_definition.md` (Phase 3, steps 2–3)
**Supersedes:** ADR 0011's noise model and rounding behaviour. The rest
of ADR 0011 — the contest primitives, dynamic Resolve-plus-matching
defence, seeded RNG threading, headless testability — stands.

**Do not start this patch by rewriting code.** Step 1 is a simulation
comparing the current model against the proposed one. The purpose of
this patch is as much to *verify* the change as to make it.

---

## Why this changes

The `3d3 - 6` noise added to each side has **fixed width regardless of
attribute magnitude**. Total margin swing is bounded at ±6, so once the
gap between attack and defence scores exceeds 6 the contest is
deterministic.

That is survivable today, because attributes run 1–15 and gaps run 2–4.
It is not survivable in a persistent career game, which is what this
project now is. At attributes of 40 versus 30, ±6 is noise around a
foregone conclusion. The system would deliver **maximum randomness where
heroes are least established, and minimum randomness where the stakes
are highest** — the exact inverse of what the design wants.

The simulation also exposed a second issue: at equal weighted scores the
attacker wins only ~40% of contests, because `3d3` vs `3d3` ties ~19.3%
of the time and every tie resolves as failure. Nothing chose that
number. The decimal rounding introduced to prevent float artefacts makes
it slightly worse by converting near-ties into exact ties.

Both problems have the same root: the randomness is a **fixed additive
term** rather than a property of the contest.

---

## 1. The roll

Replace additive fixed-width noise with **dice sized by the contested
score itself** — the FT&G model (`1dX` where X is the attribute),
generalised to `N` dice to recover a bell shape.

For a side with contested score `S`:

```
roll = Σ (i = 1..N) Uniform(0, S/N)
```

- Mean `S/2`, standard deviation `S / (√12 · √N)`.
- Both mean *and* spread scale with `S`, so a contest stays a contest at
  any magnitude.
- `N` is a named config constant and is now **the** knob for "how random
  is combat," entirely independent of attribute magnitude. `N = 3` is a
  reasonable starting point; `N = 1` reproduces FT&G exactly.

`A` = attacker's weighted attribute score (existing
`weighted_attribute_score`, still excluding flat base magnitude).
`D` = defender's score from the existing `defence_score`.

```
margin  = roll(A) − roll(D)
success = margin > 0
```

### 1a. Sample continuously, not with integer dice

Attribute scores are floats — a weighted sum like `Might·0.8 +
Resolve·0.4` gives 4.8, and `4.8 / 3` is not a die size. **Use `N`
continuous uniform samples** (a scaled Irwin–Hall distribution), not
integer dice with rounded faces. Rounding face sizes at low attribute
values distorts the distribution badly and reintroduces exactly the
granularity problems this patch removes.

### 1b. Tie handling disappears

With continuous sampling, exact ties have probability zero, so the 40%
parity artefact resolves itself and `success = margin > 0` needs no
special case.

**Remove the decimal-rounding step from `resolve_contest`.** It was
introduced to stop float representation producing accidental wins; under
continuous sampling it can only manufacture the ties it was meant to
prevent. Keep the *seeded* determinism requirement — same seed, same
result — which is unaffected.

---

## 2. Normalised margin

Raw margin scales linearly with attribute magnitude: the same 3:1
tactical advantage produces a margin near 2 early in a career and near
20 late in one. **Never feed raw margin into a damage function** — the
scale explosion is why logarithmic damage looked necessary, and it is an
artefact of units rather than a real design requirement.

Normalise first:

```
m = 2 · margin / (A + D)
```

- Dimensionless quality-of-success. At parity `m ∈ [−1, +1]`; its mean
  is `(A − D) / (A + D)`, a clean normalised advantage measure.
- `m` may exceed 1 when `A ≫ D` (approaching 2 as `D → 0`), so the
  damage function must clamp.

---

## 3. Damage

```
damage = base(A) × quality(m)

base(A)    = d₀ + d₁ · A
quality(m) = clamp(g₀ + g₁ · m, quality_floor, quality_cap)
```

**All six knobs are per-ability data, not global constants.** They live
in `data/abilities.yaml` alongside the existing scaling terms. Set
globally they would give every attack the same feel; set per ability
they give each attack its own damage profile, which is a substantial
amount of design expression for six numbers.

### What each knob expresses

- **`d₀` vs `d₁` — how much the wielder matters.** This is the knob that
  does the most work. High `d₀` with low `d₁` is a weapon anyone can use
  to similar effect: excellent for a raw recruit, nearly worthless in a
  veteran's hands. Low `d₀` with high `d₁` is the reverse — clumsy when
  weak, devastating when strong. This is a recruitment and equipment
  axis as much as a combat one.
- **`g₁` — margin sensitivity.** Low `g₁` means damage barely varies
  with how well the contest was won: precise, mechanical, reliable. High
  `g₁` means glancing blows do little and decisive ones devastate. Two
  abilities with identical expected damage feel completely different
  across these settings.
- **`g₀` — baseline quality**, where a marginal success lands.
- **`quality_floor` / `quality_cap` — the tails.** A high floor means
  even a graze hurts; a low cap means no blowouts against weak
  defenders. `quality_floor` remains the **damage floor** required by
  the phase doc: a landed hit must accomplish something worth the
  action.

### Named profiles, to contain the tuning surface

Six knobs across four abilities is manageable; across thirty it is not,
especially since they interact non-obviously.

Define a small set of **named profiles** in data — starting suggestions
`reliable` (high `g₀`, low `g₁`, high floor), `swingy` (low `g₀`, high
`g₁`, low floor, high cap), and `scaling` (low `d₀`, high `d₁`) — which
abilities reference by name, with per-knob overrides where an ability
genuinely needs to be its own thing. Most abilities should name a
profile and stop there.

### Forward compatibility

Two later systems land on these knobs rather than needing parallel
machinery, and the data model should not make that awkward:

- **Track 3 ability training** gets a ladder that isn't only "add a
  reroll" — raising `g₀` or lifting `quality_floor` reads precisely as
  *trained skill produces consistency*, which fits the
  reliability-over-power philosophy better than rerolls alone.
- **Equipment**, when it arrives, becomes modifiers on these knobs
  rather than a second damage system.

### Two consequences

- **Sub-linearity is satisfied structurally** and needs no logarithm.
  Normalisation bounds `m`, so the earlier concern about a high
  attribute paying twice is contained: against a *fixed* opponent a
  stronger attacker gains on both axes, but against a scaled opponent
  only `base(A)` grows. Compounding is bounded by the enemy scaling
  curve, which is where it should live.
- **Per-ability profiles raise the stakes on the odds display.** If
  every ability has its own damage curve, the player cannot intuit it
  from familiarity. Showing likelihood and expected magnitude before
  commitment stops being a nicety and becomes the only channel through
  which profiles are legible at all.

---

## 4. Time-to-kill target

**Design target: flat to mildly shrinking over a career.**

With `HP = h₀ + h₁ · (Might + Resolve)` and `base(A) = d₀ + d₁ · A`,
time-to-kill starts at `h₀/d₀` and asymptotes to `h₁/d₁`. Setting

```
h₀/d₀  >  h₁/d₁
```

produces a monotonic, self-limiting shrink. No exponents required. The
constants set early-career TTK; the coefficients set where it settles.
Suggested starting target: **~4 hits early, converging to ~3**.

**Reckon TTK in actions, not hits.** Success at parity is ~50%, so a
three-hit kill is a six-action kill in an even matchup. Tuning against
hits will make battles roughly twice as long as intended.

### The target applies to a hero's best available ability, not to every ability

This matters now that `d₀` and `d₁` are per-ability. An ability with
high `d₀` and low `d₁` will show **rising** TTK across a career — its
damage stays roughly flat while HP climbs. That is not a tuning failure;
it is obsolescence, and it is the intended behaviour of a weapon that
does not care who is holding it.

So the criterion is: for a hero at any career stage, the **best ability
available to them** against a same-stage defender should yield flat to
mildly shrinking TTK. Individual abilities may and should diverge from
that curve in both directions. A sim that holds every ability to the
global target will flag correct behaviour as a failure.

---

## 5. Flagged for decision — do not resolve unilaterally

These are surfaced by the change but are not part of it. Raise them;
don't silently pick.

- **Resolve is now defensively dominant.** A point of Resolve gives
  `+0.7` defence against *everything*; a point in any other attribute
  gives `+0.3` but only against attacks led by that attribute — expected
  value roughly `0.1`. That is ~7× the universal value of any
  alternative. On top of it, Basic Strike still carries the `Resolve
  0.4` attack term added by the earlier work order, which existed
  specifically because Resolve had no offensive expression. Contested
  defence solves that problem on its own, so that term is arguably now
  redundant. **Recommendation: remove `resolve: 0.4` from Basic Strike
  rather than tune the 0.7 down.** Needs sign-off.
- **HP and damage key off different attribute sets.** HP scales with
  Might + Resolve; damage scales with the attacker's primary attribute.
  A Focus-heavy hero therefore gains damage as fast as anyone but almost
  no HP, becoming progressively glassier over a career. That may be
  desirable build identity or an accident of a Phase 1 formula written
  when nothing scaled. Needs a decision before TTK tuning means much.
- **First-strike advantage grows as TTK shrinks**, and turn order is
  still the Phase 1 placeholder (player slot order, then enemy slot
  order). Agility remains unused with initiative pencilled in as its
  eventual job. Flag whether initiative should be pulled forward.
- **"Like resists like."** Because defence includes the incoming
  attack's primary attribute, a high-Focus hero resists Bolts. This may
  read as good rock-paper-scissors texture or as punishing
  specialisation. Only telemetry will tell; note it as a watch item.

---

## 6. Simulation comparison — do this first

Extend the harness that produced `combat_sim.md` into a **model-parameterised**
script (suggest `scripts/sim_contest.py`) that can run either
`legacy_3d3` or `scaled_ndx` and emit a comparison table. Both models
must be runnable side by side from the same seed set for the whole life
of this patch — do not delete the legacy path until the comparison is
signed off.

Report every sweep for **both models**.

### Sweep 1 — Parity across magnitude

`A = D ∈ {2, 4, 8, 16, 32, 64}`. Report success rate, margin standard
deviation, and exact-tie rate.

Expected: legacy holds ~40% success with constant margin SD and ~19%
ties; scaled holds ~50% success with margin SD proportional to `A` and
~0% ties. **This sweep is what demonstrates the tie artefact is gone.**

### Sweep 2 — Fixed ratio across magnitude (the headline test)

`A/D ∈ {1.5, 2, 3}` at `D ∈ {2, 4, 8, 16, 32, 64}`. Report success rate.

Expected: scaled gives a **constant** success rate per ratio regardless
of magnitude — this is the entire point of the change. Legacy degenerates
toward 100% as magnitude rises, which is the failure being fixed.

If the scaled model's success rate is not flat across magnitude for a
fixed ratio, the implementation is wrong. Treat this as the patch's
primary correctness test, not merely a report.

### Sweep 3 — Realistic hero distributions

Generate real heroes via `synthesize_starting_attributes` plus `K`
applied level-ups for `K ∈ {0, 5, 20, 50}`, and run contests between
same-`K` pairs using the actual four basic abilities. Report the
distribution of success rates and of normalised margin.

`K = 0` is roughly today's game; `K = 50` is a career veteran. The
previous sim used a 4/8/12 grid, which is far coarser than heroes
actually are — post-work-order attribute gaps run 2–4 points, so live
contests cluster near parity where dice dominate. This sweep is what
shows whether `N` feels right at the magnitudes that actually occur.

### Sweep 4 — Time-to-kill curve

For the same `K` values, compute expected damage per action
(`P(success) × E[damage | success]`) against a same-`K` defender, and
divide into that defender's HP. Report **TTK in actions**, broken out
**per ability** and for the hero's **best available ability**.

Expected: the best-ability curve is flat to mildly shrinking as `K`
rises. Individual abilities may diverge — a high-`d₀`/low-`d₁` ability
showing rising TTK is correct obsolescence, not a failure. Only the
best-ability curve is held to the target. A rising best-ability curve
means `base(A)` is not keeping pace with HP and the constants need
re-deriving.

### Sweep 5 — Damage profile comparison

At fixed attributes (`K = 0` and `K = 20`), run each named profile
against the same defender and report the **full damage distribution**,
not just the mean: mean, standard deviation, and the 10th/50th/90th
percentiles of damage per landed hit.

The point is to confirm the profiles are actually distinguishable.
`reliable` and `swingy` tuned to the same expected damage should show
clearly different spreads; if they don't, `g₁` is doing less work than
intended and wants widening before anything is balanced around it.

### Sweep 6 — `N` sensitivity

Repeat sweep 2 for `N ∈ {1, 2, 3, 5, 10}`. `N = 1` is FT&G exactly.
This is what makes the randomness knob legible before it is tuned
blind.

---

## 7. Reconciliation with Phase 3, and where to resume

This patch replaces work already done (ADR 0011's noise model) and
partially pre-empts work not yet started. This section exists so the
agent can pick Phase 3 back up cleanly rather than guessing what is
still owed.

### Phase 3 text this patch overrides

The Phase 3 document has been amended in place to match, but for the
avoidance of doubt:

- **§1, distribution width.** Phase 3 originally described roll width as
  a free config constant and "the single most consequential number in
  this phase." Under this patch, width is *derived* from the contested
  score and is no longer independently tunable. `N` replaces it as the
  knob.
- **§2, sub-linearity.** Phase 3 originally required magnitude to scale
  sub-linearly **in the margin**. That wording is superseded: the
  requirement is sub-linearity in the attacker's *attribute*, and
  normalising the margin satisfies it. A quality function that is
  linear in *normalised* margin is correct. **Do not additionally apply
  a logarithm or square root** in pursuit of the original wording — that
  would compress a symptom that normalisation has already removed, and
  would push time-to-kill in the wrong direction over a career.
- **§4, the tunable-knob list.** Superseded by the per-ability knobs and
  named profiles in section 3 above.
- **Acceptance criteria 2 and 3** are reworded accordingly.

### The gap this patch does not close

**Automatic abilities have no contest and therefore no margin**, so
`quality(m)` is undefined for them. Basic Mend is the live case: it
lands automatically but must still vary in magnitude.

Resolution: an automatic ability draws a synthetic quality from a
**zero-centred distribution of per-ability width** and feeds it through
the same damage pipeline and the same six knobs. One magnitude path, not
two, and an automatic ability can carry a damage profile exactly as a
contested one does. Width zero is a valid configuration meaning fully
deterministic magnitude.

This belongs to Phase 3 step 4, not to this patch — but it must not be
forgotten, because the patch's damage pipeline is what step 4 will be
wiring into.

### Before starting: confirm the deterministic baseline exists

Phase 3 build order step 1 required capturing a final baseline under
deterministic resolution. Per ADR 0011, the contest primitives exist but
**ability effects do not yet call them**, so live combat is still
deterministic and that baseline is still capturable.

**Verify it was captured. If it was not, capture it before touching
anything else.** After step 3 wires margin to magnitude it is gone
permanently, and with it any ability to attribute a behavioural change
to the resolution rework rather than to a bug.

### Phase 3 state after this patch

| Phase 3 step | Status after this patch |
|---|---|
| 1 — deterministic baseline | Verify; capture if missing |
| 2 — the roll | **Complete** (redone by this patch) |
| 3 — margin-to-magnitude, floor | **Complete** (this patch) |
| 4 — per-ability resolution properties | **Partial.** Damage knobs and profiles done. Still owed: contested/automatic flag, automatic-ability magnitude variance, and data validation rejecting tied or missing primary scaling terms at ability-library load rather than at resolution time |
| 5 — AI expected-value scoring | Not started |
| 6 — odds display | Not started |
| 7 — re-measure, retune, new baseline | Not started |

**Resume at step 4**, completing the items listed above, then proceed
through 5–7 as written.

### Two things steps 5 and 6 inherit from this patch

Neither is a conflict, but both are more work than the Phase 3 text
implies and should be planned for rather than discovered:

- **Expected magnitude is an integral, not a lookup.** `E[damage |
  success]` must be taken over the margin distribution conditional on
  success — not evaluated at the mean margin. Per-ability profiles make
  this sharper: two abilities with equal expected damage and different
  spreads are not interchangeable, and a scorer that ignores spread will
  rate them as if they were.
- **The odds preview must produce a damage *distribution*, not a
  bound.** "84% to land, 4–9 damage" now depends on both contested
  scores and the ability's profile. The same preview serves the AI and
  the display, so it must be computed once in the engine — if displayed
  odds and actual resolution can ever disagree, players will find it.

---



1. Contest rolls are `N` continuous uniform samples scaled by each
   side's contested score; `N` and the distribution parameters are named
   config constants.
2. No integer dice, no rounded face sizes, no decimal rounding of
   margins.
3. Exact-tie rate is ~0 in the scaled model, measured and reported.
4. **Success rate for a fixed attack/defence ratio is constant across
   attribute magnitude**, verified by sweep 2 across at least a 32×
   magnitude range.
5. Damage uses normalised margin, with clamp and floor; raw margin
   never reaches a damage function, and no logarithm or square root is
   applied on top of normalisation.
6. TTK in actions for a hero's **best available ability** is flat to
   mildly shrinking across `K ∈ {0, 5, 20, 50}`, verified by sweep 4.
   Individual abilities are not held to this target — divergence,
   including rising TTK for low-`d₁` abilities, is expected and correct.
7. The six damage knobs are per-ability data referencing named profiles,
   with per-knob override available; no damage-shaping constant is
   global. Sweep 5 shows the profiles produce visibly different damage
   distributions at equal expected damage.
8. `combat_sim.md` is regenerated for both models with all six sweeps,
   and the legacy path remains runnable until sign-off.
9. Seeded battles remain exactly reproducible.
10. Flagged items in section 5 are raised in the progress update with a
    recommendation, not silently resolved.
11. The Phase 3 deterministic baseline is confirmed captured (section 7)
    before any resolution code changes.
12. `uv run ty check` passes cleanly; `uv run pytest` passes.

---

## ADR

Write a new ADR superseding ADR 0011's noise decision. It should record:
the scale-invariance failure of fixed-width noise in a persistent career
game; the tie artefact and how continuous sampling removes it; the
choice of `N` continuous samples over both `1dX` (uniform, too swingy
for hard consequences) and fixed additive noise; and margin
normalisation as the reason logarithmic damage is unnecessary.

Mark ADR 0011 as superseded in part rather than rewriting it — the
defence model and primitives it established are unchanged.

---

## Build Order

1. **Simulation first.** Parameterise the harness, implement the scaled
   model inside it only, run all six sweeps. Do not touch
   `engine/resolution.py` yet.
2. Review the sweeps. If sweep 2 is not flat, stop and fix before
   proceeding.
3. Port the scaled roll into `engine/resolution.py`; remove additive
   noise and margin rounding.
4. Normalised margin and the damage function with clamp and floor;
   per-ability knobs and named profiles in `data/abilities.yaml`.
5. Re-derive HP and damage constants against the sweep-4 TTK target,
   holding only the best-available-ability curve to it.
6. Regenerate the baseline fixture; document the diff.

Steps 1–2 are the point of this patch. Everything after is mechanical
once the sweeps agree.
