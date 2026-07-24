# Phase 3 — Blocking List Closed; Proceed to Sweeps 4 and 5

Supplements `09_phase3_unblock_notes.md`. Read after
`phase3_scale_invariant_comparison.md`.

**The parity verification is accepted.** Margin SD of 0.470802 at score
2 matches the theoretical `S/√18` = 0.4714 to four significant figures,
and the 100k-trial success rate of 49.966% confirms the earlier 48.58%
was sampling variation. The scaled model is correct, not merely
plausible.

---

## Nothing on the current blocking list is a blocker

The conclusion section of the comparison report lists three items as
blocking sweeps 4 and 5. None of them are, and the list also contradicts
itself.

- **Item 2 is already resolved by its own text.** It states classless HP
  is `h₀ + r·Resolve` with the class multiplier symbolic — that *is* the
  decision. The closing paragraph then withholds the sweeps pending "the
  unresolved HP decision." Both cannot be true. Delete the closing
  claim.
- **Item 1 — Tier 1 kit replacement — is a Tier 1 design question.** It
  has no bearing on time-to-kill or damage-distribution arithmetic.
  Carry it forward; it blocks nothing here.
- **Item 3 — telemetry on matching-primary defence — cannot be resolved
  before the sweeps**, because it needs play data. Listing it as a
  prerequisite makes it a permanent blocker by construction. It is a
  watch item, as is initiative.

**Proceed to sweeps 4 and 5.**

---

## The chicken-and-egg to avoid

The report withholds the sweeps pending "numerical per-ability damage
profiles." **Sweeps 4 and 5 are the instrument for deriving those
numbers.** Sweep 4 tunes `h₀`, `r`, `d₀`, `d₁` against the TTK target;
sweep 5 checks whether the profiles are distinguishable at all.

They need plausible *starting values*, not settled ones. Treating tuned
values as a precondition inverts the simulate-first method the patch is
built on: pick placeholders, run, read, adjust, re-run.

---

## Starting values — placeholders, expected to move

All figures below are **first guesses chosen to be roughly in range, not
balance proposals.** Their only job is to let the sweeps run and produce
a gradient to tune along. Do not defend them; replace them with what
sweep 4 indicates.

### Damage profiles

Define three named profiles in ability data. `g₀` is baseline quality at
zero normalised margin, `g₁` margin sensitivity, then floor and cap:

| Profile | `g₀` | `g₁` | floor | cap |
| --- | ---: | ---: | ---: | ---: |
| `reliable` | 0.75 | 0.20 | 0.60 | 1.00 |
| `swingy` | 0.40 | 0.70 | 0.20 | 1.40 |
| `standard` | 0.50 | 0.50 | 0.35 | 1.20 |

`reliable` and `swingy` are deliberately set to similar expected quality
with very different spread — that similarity is what sweep 5 tests. If
their damage distributions come out looking alike, `g₁` is doing less
work than intended and wants widening before anything is balanced around
it.

### Base terms and initial assignment

`base(A) = d₀ + d₁·A`, per ability:

| Ability | Profile | `d₀` | `d₁` |
| --- | --- | ---: | ---: |
| Basic Strike | `standard` | 2.0 | 0.60 |
| Basic Bolt | `swingy` | 1.5 | 0.55 |
| Basic Shot | `reliable` | 1.5 | 0.45 |
| Basic Mend | `reliable` | 2.0 | 0.50 |

Rationale for the shape, not the numbers: Strike is highest-damage and
melee-only; Shot has the longest reach and the lowest scaling; Bolt sits
between and carries the variance. Mend is automatic (see below).

### HP and the TTK target

```
HP = h₀ + r · Resolve        (classless; class term symbolic)
```

Starting values `h₀ = 12`, `r = 0.6`.

Target: **~4 hits early converging to ~3**, which requires `h₀/d₀ >
h₁/d₁` — with `h₁` here being `r`. Reckon TTK in **actions**, not hits:
at ~50% success near parity, a three-hit kill is a six-action kill.

Only the **best available ability** is held to the target. Rising TTK on
a low-`d₁` ability is correct obsolescence.

### Automatic abilities

Basic Mend has no contest and therefore no margin. Draw a synthetic
normalised quality from a zero-centred distribution and feed the same
pipeline and the same knobs. Starting width: **0.25**. Width zero is
valid and means deterministic magnitude.

---

## Also fix in the report

**The lagged cases have no numbers.** The report says they "show the
expected increased success rate," which is a claim, not a measurement.
Adding `K` vs `K−5` and `K−10` was specifically to make the enemy-scaling
question measurable; without figures it remains hidden, just differently.

Publish a table of success rates at each lag across career stages. That
is the data that will eventually indicate what enemy scaling curve makes
progression feel like progression, and it is worth having on record
before the question is taken up properly.

---

## Acceptance for this step

1. The comparison report's blocking list is replaced with a
   carried-forward list; the self-contradicting closing claim is removed.
2. Lagged-enemy success rates are tabulated with actual figures.
3. Sweep 4 runs and reports per-ability and best-available-ability TTK
   in actions across `K ∈ {0, 5, 20, 50}`.
4. Sweep 5 runs and reports mean, standard deviation, and 10th/50th/90th
   percentile damage per landed hit for each profile.
5. `h₀`, `r`, `d₀`, `d₁` are re-derived from sweep 4 against the TTK
   target, and the revised values recorded alongside the placeholders
   they replaced.
6. If `reliable` and `swingy` are not visibly distinguishable in sweep
   5, say so explicitly and propose widened `g₁` rather than proceeding.
