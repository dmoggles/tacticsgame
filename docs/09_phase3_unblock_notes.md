# Phase 3 — Decisions to Unblock the Sim Sweeps

Answers the three blocking items in
`phase3_scale_invariant_comparison.md`, plus corrections arising from
review of that report. Read alongside
`08_patch_scale_invariant_contest_roll.md`.

---

## The three blocking items — resolved

**1. Basic Strike's secondary Resolve scaling — KEEP IT. No data change.**

- It stays while a hero is classless, as a deliberate crutch: a
  high-Resolve hero otherwise has contest defence and healing but no
  offensive expression, and no interesting abilities yet.
- It is removed at **Tier 1 specialisation**, not now.
- **The report's observation that Strike's mean success is elevated is
  therefore intended behaviour, not an artefact.** Amend that note in
  the report so a later pass does not "correct" it.
- Prefer implementing the eventual removal as **kit replacement at Tier
  1** (the classless and specialised kits are different abilities)
  rather than resolution reading hero state to decide which scaling
  terms apply. Conditional ability data couples abilities to hero state
  and that coupling will spread.

**2. HP formula — resolved. Additive, in two parts.**

```
HP = h₀ + r · Resolve + c_class · A_primary
```

- `r < 1`. **The Resolve term always applies and is never replaced.**
- `c_class` is zero while classless, and a class-dependent multiplier
  once specialised — higher for tank-type classes.
- **Might is dropped from HP.** Fighters get it back through
  `c_class · A_primary`, since Fighter's primary is Might.
- The class term is **additive**, so HP can only step up at
  specialisation. There is no discontinuity to guard against.
- Consequence worth knowing: TTK converges to
  `(r·(R/A) + c_class) / d₁`. The class multiplier sets a durability
  floor; a hero's own Resolve lean stacks on top, so two heroes of the
  same class differ in toughness by affinity. That is intended texture.

**3. Initiative — NOT blocking. Proceed without it.**

- Sweeps 4 and 5 compute TTK per action and damage distributions. Turn
  order does not enter that arithmetic. It affects battle outcomes, not
  these sweeps.
- The TTK shrink is mild, so schedule initiative into the tactical
  phase rather than holding damage tuning for it.
- **"Like resists like" is likewise a telemetry watch item, not a
  blocker.** Whether matching-primary defence reads as good
  rock-paper-scissors texture or as punishing specialisation can only be
  answered from play data.

---

## One verification before proceeding

- **Parity at score 2 came in at 48.58%**, roughly 2σ below the 50% that
  symmetry requires, while score 64 sat at 49.90%. The pattern — a
  deficit at small scores, none at large — is what residual
  discretisation looks like, since rounding produces proportionally more
  ties when margin spread is small.
- Rerun parity at score 2 with ~100k trials. If it stays near 48.6%, it
  is systematic and something is still rounding.
- Confirm the reported 0.00% tie rate is measured **after** any rounding
  step, not before. A pre-rounding measurement would not show the
  problem.

---

## One methodological fix

- **Sweep 3 as run cannot answer what it appears to answer.** Pairing
  same-K heroes against same-K heroes is *guaranteed* to sit near 50%
  under a scale-invariant roll — both sides grew equally, so the ratio
  never moves. It validates that invariance survives realistic attribute
  distributions, which is worth having, but it says nothing about
  whether career progression feels meaningful.
- Add lagged cases: heroes at `K` against enemies at `K−5` and `K−10`.
- Note this is the deferred enemy-scaling question resurfacing as a
  measurement problem. It does not need solving now, but the sweep
  should stop implying it has been.

---

## Scope note on sweep 4

- **Tune the classless regime only.** `h₀`, `r`, `d₀`, `d₁` are
  tunable now.
- `c_class` cannot be tuned until Tier 1 exists. Treat class multipliers
  as symbolic; validate the *shape* of the class formula, not its
  numbers.
- **Per-class TTK becomes a Tier 1 acceptance criterion**, not a Phase 3
  one.
- Recall that the TTK target applies to a hero's **best available
  ability**, not to every ability — rising TTK on a low-`d₁` ability is
  correct obsolescence.

---

## Measurement cautions

- **Strike now serves two of four attributes** (Might and Resolve), so
  the Fighter track should attract disproportionate traffic across the
  whole roster. This will move the standing predictability metric on its
  own, independently of the roll change. **Separate the two effects when
  the post-patch measurement comes back**, or one will be misattributed
  to the other.
- Watch specifically for **Resolve-affinity heroes routing into
  Fighter**. Strike feeds Fighter XP, but Resolve is Healer's attribute
  — so the crutch may point exactly the heroes it exists for at the
  wrong Tier 1 class. If this shows up, the likely fix is making Mend
  compete better in the classless phase, not removing the crutch.
- **Resolve now buys both contest defence and HP.** That is acceptable
  because the class term guarantees a durability baseline regardless, so
  it is an incentive rather than a dependency. If telemetry shows
  Resolve becoming the stat every build wants, **trim `r` first**, not
  the 0.7 defence weight.

---

## Still owed from the patch, before Phase 3 step 5

- **Automatic-ability magnitude variance.** Basic Mend auto-lands and so
  has no margin; `quality(m)` is undefined for it. Draw a synthetic
  quality from a zero-centred distribution of per-ability width and feed
  the same damage pipeline and the same knobs. Width zero is valid and
  means deterministic magnitude.
- **Per-ability contested/automatic flag** in ability data.
- **Data validation at ability-library load** rejecting tied or missing
  primary attack scaling terms. ADR 0011 currently raises `ValueError`
  during resolution, which is a crash mid-battle; that raise should
  become an assertion about something already guaranteed at load.
- Confirm the **deterministic baseline** from Phase 3 step 1 was
  captured. Per ADR 0011 the primitives exist but effects do not call
  them, so live combat is still deterministic and it remains capturable
  — but only until margin is wired to magnitude.

---

## Carried forward — not blocking, do not resolve unilaterally

- **Does Tier 1 replace all four basics, or only the archetype-matching
  one?** The 4-slot invariant forces the question: every class ability
  displaces something. A hero with one class ability and three generic
  ones may or may not feel like they have become something. This is a
  Tier 1 design question.
- **Class should name its HP attribute** (Fighter→Might,
  Marksman→Agility, Caster→Focus, Healer→Resolve) rather than the
  formula computing "highest," so a hero's HP basis cannot drift
  mid-career.
- **Step or ramp?** Whether `c_class` arrives all at once at Tier 1 or
  phases in with specialisation level.
- **Multiclass HP rule** — likely the lower of the two class
  multipliers, consistent with multiclassing's existing cost structure.
- **`N = 3` is provisional.** A 1.5× edge winning ~80% is a real
  decisiveness choice, and the right value depends on what ratios
  actually occur in play — which depends on enemy scaling, still
  undecided. Re-run the `N` sweep once enemies stop being hero mirrors.
