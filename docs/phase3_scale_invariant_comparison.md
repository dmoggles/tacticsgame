# Phase 3 — Scale-invariant contest comparison

This is the simulation-first checkpoint required by
[`08_patch_scale_invariant_contest_roll.md`](08_patch_scale_invariant_contest_roll.md).
It does not change `engine/resolution.py`.

## Method

[`scripts/sim_contest.py`](../scripts/sim_contest.py) runs the old additive
`3d3 - 6` model and the proposed continuous score-scaled `N`-sample model
side-by-side from the same seed. The recorded run used seed `20260724`,
5,000 trials per numeric cell, `N = 3`, 200 synthesized hero pairs for each
realistic case, and 2,000 trials per pair.

The full report is reproducible with:

```bash
uv run python scripts/sim_contest.py
```

## Results

### Parity

| Model | Score | Success | Margin SD | Exact-tie rate |
| --- | ---: | ---: | ---: | ---: |
| Legacy | 2 | 41.06% | 2.000 | 19.66% |
| Legacy | 64 | 40.24% | 2.017 | 19.58% |
| Scaled, N=3 | 2 | 48.58% | 0.481 | 0.00% |
| Scaled, N=3 | 64 | 49.90% | 14.989 | 0.00% |

The legacy model confirms the 40%-at-parity tie artefact and fixed margin
spread. The scaled model is approximately 50% at parity, has no sampled exact
ties, and its margin spread grows in proportion to score.

The supplemental 100,000-trial verification at parity score 2 measured
**49.966%** success, margin SD **0.470802**, and **0.0000%** exact ties. The
scaled harness does not round margins before either measuring ties or deciding
success; the earlier 48.58% result was ordinary sampling variation, not
residual discretisation.

### Fixed attack/defence ratio across a 32× score range

| A/D | Legacy success at D=2 → D=64 | Scaled N=3 success at D=2 → D=64 |
| ---: | ---: | ---: |
| 1.5 | 59.76% → 100.00% | 79.62% → 79.26% |
| 2.0 | 76.46% → 100.00% | 90.62% → 89.80% |
| 3.0 | 96.32% → 100.00% | 97.24% → 97.10% |

This passes the patch's headline invariant: for the scaled model, success is
constant within Monte Carlo variation for a fixed ratio, regardless of
absolute score. The legacy model becomes deterministic as scores rise.

### Realistic synthesized heroes

The sweep now includes same-stage (`K` versus `K`) and lagged enemy cases
(`K` versus `K−5` and `K−10`, clamped at zero). Same-stage comparisons confirm
that the distribution remains near parity as both sides grow; lagged cases
show the expected increased success rate and make the deferred enemy-scaling
question measurable rather than hidden by same-stage pairing. Strike's higher
mean is **intended behaviour**: its classless Resolve term remains as an
offensive crutch for Resolve-heavy heroes and must not be removed by a balance
pass. It is deferred to Tier 1 kit replacement.

### N sensitivity

`N` changes how much a given ratio decides the contest while retaining scale
invariance. At A/D=1.5, success is roughly 67% at N=1, 79% at N=3, 85% at
N=5, and 93% at N=10. `N=3` is therefore a reasonable conservative initial
setting: it avoids the uniform swinginess of N=1 without making a 1.5× edge
near-certain.

## Sweeps 4 and 5 — damage calibration

The supplied initial damage terms (`d0` 1.5–2.0; `d1` 0.45–0.60) made the
best ability fall from roughly five actions at K=0 to fewer than two at K=50.
They were therefore replaced in the simulation with a common classless base
shape of **`d0 = 1.9`, `d1 = 0.12`** for Strike, Bolt, and Shot. With classless
HP `12 + 0.6 * Resolve`, the scaled N=3 sweep reports best-ability TTK of:

| Career K | Best-ability TTK (actions) |
| ---: | ---: |
| 0 | 8.32 |
| 5 | 7.21 |
| 20 | 7.15 |
| 50 | 5.78 |

This is the intended flat-to-mildly-shrinking classless curve. The values are
still simulation-only until the per-ability YAML migration.

Sweep 5 also showed that the supplied `swingy` baseline quality of 0.40 was
not comparable to `reliable` (mean landed damage 5.32 versus 7.88). Raising
`swingy.g0` to **0.65** aligns its mean while retaining its larger spread:

| Profile | Mean landed damage | SD | P10 / P50 / P90 |
| --- | ---: | ---: | --- |
| reliable | 7.88 | 0.28 | 7.56 / 7.82 / 8.29 |
| swingy | 7.83 | 0.96 | 6.72 / 7.65 / 9.18 |
| standard | 5.96 | 0.71 | 5.15 / 5.81 / 6.97 |

`reliable` and `swingy` are therefore visibly distinct as required.

## Conclusion and carried-forward work

The simulation supports replacing fixed-width additive noise with the scaled
continuous model. The following items are carried forward, not blockers:

1. The future Tier 1 kit-replacement design that removes the classless Strike
   crutch without conditional ability data.
2. Tier 1's additive class-primary HP term; classless HP is now resolved as
   `12 + 0.6 * Resolve`.
3. Telemetry on whether matching-primary defence reads as good texture or
   punishing specialisation. Initiative remains deferred to tactical work.

The comparison harness retains the legacy path for subsequent validation.
