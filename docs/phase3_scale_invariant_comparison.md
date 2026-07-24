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

The scaled model stays materially stable from a new recruit (`K=0`) through
50 extra affinity-driven level-ups. Across Strike/Bolt/Shot, the sampled mean
success rates remain broadly around 45–62%; the legacy model instead widens
the between-pair success-rate spread as careers progress. Strike's higher mean
is expected under the *current* kit because it still has Resolve attack
scaling, which is one of the patch's flagged decisions rather than a result
to balance around yet.

### N sensitivity

`N` changes how much a given ratio decides the contest while retaining scale
invariance. At A/D=1.5, success is roughly 67% at N=1, 79% at N=3, 85% at
N=5, and 93% at N=10. `N=3` is therefore a reasonable conservative initial
setting: it avoids the uniform swinginess of N=1 without making a 1.5× edge
near-certain.

## Conclusion and remaining work

The simulation supports replacing fixed-width additive noise with the scaled
continuous model. It also makes the following patch-mandated decisions
blocking before damage/TTK sweeps can be honestly tuned:

1. Whether to remove Basic Strike's secondary Resolve scaling now that Resolve
   is universally defensive (the patch recommends removal).
2. Whether the existing HP formula—Might plus Resolve only—is intended to
   leave Focus- and Agility-led heroes progressively glassier.
3. Whether initiative must be advanced before TTK is reduced, and whether
   matching-primary defence reads as desirable specialisation texture.

Sweeps 4 and 5 are deliberately not reported yet: they require the unresolved
HP decision and numerical per-ability damage profiles. The comparison harness
is retained so those sweeps can be added without deleting the legacy path.
