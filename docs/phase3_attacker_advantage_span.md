# Phase 3 — Attacker-advantage span

Simulation of the proposed global `1.30` attacker-score multiplier. Each row
uses 100,000 seeded scaled-N=3 contests, a defender score of 8, and the
current simulation-only classless damage bases. `Both` lets the multiplier
affect normalized-margin quality; `accuracy-only` removes its mean shift from
the quality margin while retaining its hit-rate effect.

| Raw A/D | Hit rate | Ability | Both action damage | Accuracy-only action damage |
| ---: | ---: | --- | ---: | ---: |
| 0.75 | 47.84% | Strike | 0.742 | 0.677 |
| 0.75 | 47.84% | Bolt | 0.976 | 0.884 |
| 0.75 | 47.84% | Shot | 0.986 | 0.960 |
| 1.00 | 70.43% | Strike | 1.256 | 1.143 |
| 1.00 | 70.43% | Bolt | 1.658 | 1.499 |
| 1.00 | 70.43% | Shot | 1.610 | 1.565 |
| 1.25 | 83.22% | Strike | 1.693 | 1.545 |
| 1.25 | 83.22% | Bolt | 2.241 | 2.034 |
| 1.25 | 83.22% | Shot | 2.096 | 2.037 |
| 1.50 | 89.86% | Strike | 2.055 | 1.884 |
| 1.50 | 89.86% | Bolt | 2.726 | 2.488 |
| 1.50 | 89.86% | Shot | 2.472 | 2.404 |
| 2.00 | 95.88% | Strike | 2.687 | 2.492 |
| 2.00 | 95.88% | Bolt | 3.578 | 3.305 |
| 2.00 | 95.88% | Shot | 3.089 | 3.011 |

The quality-inclusive path increases action damage by roughly 3–11% over
accuracy-only, with the largest difference on the swingy Bolt profile. It
preserves a single coherent contest path: easier attacks both land more often
and land more decisively.
