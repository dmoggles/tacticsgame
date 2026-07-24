# Phase 3 — Attacker Advantage & Damage Sweep Corrections

Supersedes the damage calibration in
`phase3_scale_invariant_comparison.md` §"Sweeps 4 and 5". The contest
roll itself is unchanged and remains validated — margin SD of 0.470802
at score 2 matches the theoretical `S/√18` = 0.4714, and sweep 5's
internals check out (`reliable` relative SD 3.6% against 3.5% predicted,
`swingy` 12.3% against 12.5%).

**Do these in the order given.** Item 1 changes the inputs to everything
below it, so re-deriving damage before it lands means doing the work
twice.

---

## 1. Attacker advantage — do this first

### The problem is structural, not a tuning miss

A ~50% success rate against an evenly matched opponent feels bad. For
comparison, a *poor* melee hit rate in BG3 is around 70%; 50% reads as
long-odds territory, not as the normal case.

**Symmetry forces the current result.** When both sides draw from
identically shaped distributions, neither can be favoured — parity is
50% by identity. No choice of `N`, distribution shape, or defence
weighting can move it. Other games avoid this because their "even"
opponent is not parity in roll terms: D&D and BG3 tune attack bonus
deliberately to beat level-appropriate AC, so a fair fight already has
the attacker ahead.

### The change

Introduce a single named config constant — an **attacker advantage** —
applied as a multiplier above 1 on the attack score, or equivalently
below 1 on defence. The two are interchangeable; pick one and document
which.

- **Calibrate it to give ~70% success at attribute parity.** From the
  existing sweep data (parity 50%, ratio 1.5 → 79.6%) the effective
  ratio needed is near **1.3**, but **measure it rather than adopting
  that figure** — sweep 2's harness answers this directly.
- **Apply it globally, to enemies as well as heroes.** A hidden
  hero-only bonus is the wrong mechanism. BG3's felt asymmetry comes
  from PCs being better optimised than their opposition, not from a
  concealed modifier. The player's edge should come from enemy design,
  which is coming anyway once enemies stop being hero mirrors.

### Resulting curve, for sanity-checking

Parity ~70%, a genuine 1.5× advantage ~90%, being outmatched 1.5× still
~40%. Competence as the default, failure as the exception, bad matchups
unfavourable rather than hopeless.

### One decision this forces — flag it, don't assume

Because the advantage shifts the contest, it raises **both** success
rate and normalised margin — and therefore damage quality as well as hit
frequency. At attribute parity with a 1.3 multiplier, mean normalised
margin becomes about `(k−1)/(k+1)` ≈ 0.13 rather than 0.

- **Recommended: let it affect both.** One code path, and "an easier
  contest is also won more decisively" is coherent. But it means the TTK
  impact is **larger than the hit-rate change alone implies** — do not
  assume a clean 1.4× and scale the damage constants by it. Re-derive
  from measurement.
- **Alternative, if damage should be untouched:** subtract the advantage
  from the margin before normalising, making it an accuracy bonus only.
  Cleaner separation of knobs, one extra concept. Raise this rather than
  choosing silently.

### Verify invariance survives

A constant multiplier preserves ratios, so scale invariance should be
unaffected. **Re-run sweep 2 and confirm it is still flat** across the
32× score range. If it isn't, the multiplier has been applied somewhere
it shouldn't be.

---

## 2. Verify the TTK units before re-deriving anything

The reported sweep 4 figures appear to be **per hit, not per action**.

Working K=0 by hand: a best-ability attack score near 6.9 gives
`base = 1.9 + 0.12 × 6.9 ≈ 2.73`. At parity, normalised margin
conditional on success has a mean around 0.19, so `standard` quality is
≈ 0.59 — floor and cap never bind. That is ≈ 1.62 damage per landed hit
against HP ≈ 14.5: about **8.9 hits**, or **17.9 actions** at ~50%
success. The report gives 8.32.

At K=50 the same arithmetic gives ≈ 6.0 hits or ≈ 12 actions; the report
gives 5.78. Both land within ~10% of the hit count and are off by a
stable factor near 2.1 from the action count. **That the factor is
stable across a 50-level span is the signal** — attribute-estimate error
would push the two ends in different directions.

**Check whether `P(success)` appears in the damage-per-action
computation** — either dividing damage-per-hit or multiplying expected
damage before it is divided into HP. If it does not, the figures are
per-hit and true TTK is roughly double what was reported.

Note the absolute numbers above are inferred from synthesis parameters
rather than read from the code, so treat the *ratio* as the finding, not
the estimates.

Definitions, for the avoidance of doubt:

- **Action** — one use of an offensive ability on a turn, whether or not
  it lands.
- **Hit** — an action that won the contest.
- `TTK_actions = TTK_hits / P(success)`.

Actions is the currency the TTK target is expressed in, because it is
what determines battle length. After item 1 the conversion factor
becomes ≈ 1.43 rather than ≈ 2.

---

## 3. Restore the wielder-matters axis

Collapsing Strike, Bolt and Shot to a common `d₀ = 1.9, d₁ = 0.12`
removed the dimension these knobs exist for. `d₀` versus `d₁` controls
**how much the wielder's attribute changes what an ability delivers** —
the difference between a weapon anyone can use to similar effect and one
that rewards a specialist. With a shared shape, the only remaining
differentiation is quality profile, which is texture rather than
scaling.

The TTK problem that motivated the change was real. **The fix is to
lower the level while keeping the spread**, not to flatten it —
something in the shape of Strike 0.16, Bolt 0.12, Shot 0.08 preserves
the same mean with the axis intact. Exact values follow from item 2's
re-derivation.

If the intent is instead that the *classless* kit should be deliberately
undifferentiated on this axis, with variety arriving at Tier 1 — that is
defensible, but state it as a design decision rather than reaching it
through tuning.

---

## 4. Restore Strike as the highest-damage attack

Strike currently has the same base as Bolt and Shot plus the weakest
quality profile (`standard`, `g₀` 0.50 against `reliable`'s 0.75 and the
revised `swingy`'s 0.65), giving it the **lowest** mean landed damage of
the three.

This inverts ADR 0010, which made Strike range-1 with the highest damage
precisely because melee is the most positionally expensive option. An
attack that is both the hardest to deliver and the weakest is a strictly
dominated choice, and the AI will correctly stop using it.

Strike must come out ahead on damage once base and profile are combined.
Either raise its `d₁` (consistent with item 3) or move it to a stronger
profile — but the combined result, not one term, is what matters.

---

## 5. Re-run sweep 5 across ratios, not only at parity

Sweep 5 appears to have run at parity, where normalised margin
conditional on success has an SD of only about 0.14. Quality therefore
occupies a narrow band and **the floor and cap essentially never bind**
— so the sweep is measuring the profiles at their least differentiated
point.

Re-run at A/D of **1.5 and 2.0** as well. Those are the matchups where
`m` approaches and exceeds 1, where caps bind, and where `swingy`'s
upside actually appears. That is what the profiles do across the range
players will encounter.

The parity-only result showing `reliable` and `swingy` as distinguishable
is real but is the weakest case; the lopsided cases should separate them
considerably further.

---

## Acceptance Criteria

1. Attacker advantage exists as a named config constant, calibrated by
   measurement to ~70% success at attribute parity, applied globally to
   heroes and enemies alike.
2. Whether the advantage affects damage quality as well as hit rate is
   explicitly decided and recorded, not left implicit.
3. Sweep 2 re-run and still flat across the 32× score range.
4. The actions-versus-hits question in item 2 is resolved in code, with
   the finding stated plainly — including if the original figures were
   correct after all.
5. `d₀`/`d₁` re-derived after item 1, with the per-ability spread on
   `d₁` restored rather than collapsed.
6. Strike has the highest mean landed damage of the three attacks, with
   base and profile considered together.
7. Sweep 5 re-run at parity, 1.5 and 2.0, with mean, SD and
   10th/50th/90th percentiles reported at each.
8. Placeholder values replaced by measured ones, with both recorded so
   the change is auditable.
9. `uv run ty check` passes cleanly; `uv run pytest` passes.

---

## Carried forward — unchanged, not in scope here

- Tier 1 kit replacement removing the classless Strike crutch without
  conditional ability data.
- The additive class-primary HP term; classless HP stays
  `h₀ + r·Resolve`.
- Telemetry on whether matching-primary defence reads as good texture or
  punishing specialisation.
- Initiative, deferred to the tactical phase.
- `N = 3` remains provisional pending enemy scaling.

**One knock-on worth noting for later:** with the attacker favoured by
default, cover becomes the mechanism that claws the advantage back. It
has more work to do than when the baseline was already a coin flip,
which strengthens the case for two meaningful tiers when terrain arrives.
