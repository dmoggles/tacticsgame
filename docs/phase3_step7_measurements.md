# Phase 3 Step 7 measurements

200 paired seeded sessions; 20,000 trials per live-engine curve cell; 4 workers.
Wall-clock collection time: 91.7s.

**Methodology.** Each session receives a distinct deterministic seed and runs independently through the live session, battle, AI, and contested-resolution paths; worker processes collect those paired seed results in parallel, so aggregation changes runtime rather than outcomes. Before every battle, the headless policy fields the two roster heroes with the fewest prior fielded battles, breaking ties by roster order; this deliberately measures balanced rotation rather than a strongest-team policy. Starting attributes are synthesized from each hero's hidden affinity. Each pending free level-up point is assigned to the attribute aligned with that hero's current leading specialization track (Fighter→Might, Caster→Focus, Marksman→Agility, Healer→Resolve); ties before specialization use the current top attribute. Progression and specialization metrics are roster-level observations after every completed battle and at session end. Each curve cell repeatedly invokes the live contest and normalised-margin damage helpers against synthetic attribute/defence pairings; to-hit is successful actions divided by trials, damage/action includes misses, and landed damage is conditional on success.

## Session and specialization outcomes

- Full-session win rate: 22.5%
- Top-attribute → top-track predictability: 65.9% (527/800); pre-Phase-3 comparison: 57.25%.
- Fighter top-track share: 49.8%; this is reported separately because Strike's Might+Resolve scaling is a known confound.

| Track | XP collected | Heroes ending top-track |
| --- | ---: | ---: |
| fighter | 40475 | 398 |
| marksman | 16440 | 129 |
| caster | 27990 | 273 |
| healer | 14300 | 0 |

| Ability | Uses |
| --- | ---: |
| Basic Strike | 8095 |
| Basic Bolt | 5598 |
| Basic Shot | 3288 |
| Basic Mend | 2860 |

## Level-up attribute allocation

Automatic points are the final attribute gain minus recorded user-directed points; starting synthesis is excluded.

| Attribute | Affinity-driven automatic | User-chosen specialization | Total level-up gain |
| --- | ---: | ---: | ---: |
| might | 460 | 502 | 962 |
| focus | 403 | 243 | 646 |
| resolve | 465 | 1 | 466 |
| agility | 432 | 134 | 566 |

## Final max-HP distribution

| Level | Heroes | Min HP | Mean HP | Max HP |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 324 | 14 | 26.97 | 42 |
| 2 | 256 | 16 | 32.74 | 48 |
| 3 | 36 | 20 | 33.61 | 48 |
| 4 | 184 | 24 | 41.53 | 58 |

| Preferred track | Heroes | Min HP | Mean HP | Max HP |
| --- | ---: | ---: | ---: | ---: |
| caster | 273 | 14 | 26.23 | 46 |
| fighter | 398 | 22 | 38.05 | 58 |
| marksman | 129 | 16 | 28.43 | 54 |

## Level and class-XP trend by completed battle

| Battle | Mean level | Mean class XP |
| ---: | ---: | ---: |
| 1 | 1.00 | 15.9 |
| 2 | 1.00 | 38.0 |
| 3 | 1.42 | 64.0 |
| 4 | 1.74 | 89.5 |
| 5 | 2.38 | 116.7 |
| 6 | 2.93 | 143.0 |
| 7 | 3.00 | 167.7 |
| 8 | 3.96 | 193.5 |
| 9 | 4.00 | 214.5 |
| 10 | 4.00 | 236.5 |

## Live to-hit and damage curves

Damage is mean damage per action; landed damage is conditional on a hit. Actual score ratio is shown because Resolve contributes to defence.

| Ability | Attribute level | Defence multiplier | Attack | Defence | To-hit | Damage/action | Landed damage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Strike | 4 | 2.00 | 4.8 | 8.0 | 30.1% | 0.95 | 3.15 |
| Strike | 4 | 1.50 | 4.8 | 6.0 | 53.9% | 1.75 | 3.26 |
| Strike | 4 | 0.67 | 4.8 | 3.0 | 91.9% | 3.48 | 3.79 |
| Strike | 4 | 1.00 | 4.8 | 4.0 | 81.5% | 2.88 | 3.53 |
| Strike | 8 | 1.00 | 9.6 | 8.0 | 81.0% | 3.48 | 4.29 |
| Strike | 8 | 2.00 | 9.6 | 16.0 | 30.6% | 1.17 | 3.81 |
| Strike | 8 | 1.50 | 9.6 | 12.0 | 53.6% | 2.12 | 3.95 |
| Strike | 8 | 0.67 | 9.6 | 5.0 | 95.3% | 4.59 | 4.82 |
| Strike | 16 | 1.50 | 19.2 | 24.0 | 53.2% | 2.86 | 5.38 |
| Strike | 16 | 1.00 | 19.2 | 16.0 | 81.2% | 4.72 | 5.81 |
| Strike | 16 | 0.67 | 19.2 | 11.0 | 93.3% | 5.91 | 6.34 |
| Strike | 16 | 2.00 | 19.2 | 32.0 | 30.9% | 1.60 | 5.18 |
| Strike | 32 | 1.50 | 38.4 | 48.0 | 53.2% | 4.30 | 8.08 |
| Strike | 32 | 0.67 | 38.4 | 21.0 | 94.5% | 9.17 | 9.71 |
| Strike | 32 | 2.00 | 38.4 | 64.0 | 30.3% | 2.35 | 7.75 |
| Strike | 32 | 1.00 | 38.4 | 32.0 | 81.0% | 7.10 | 8.77 |
| Bolt | 4 | 2.00 | 4.0 | 8.0 | 19.8% | 0.52 | 2.65 |
| Bolt | 4 | 1.50 | 4.0 | 6.0 | 38.2% | 1.05 | 2.74 |
| Bolt | 4 | 0.67 | 4.0 | 3.0 | 85.8% | 2.71 | 3.15 |
| Bolt | 4 | 1.00 | 4.0 | 4.0 | 70.6% | 2.09 | 2.96 |
| Bolt | 8 | 2.00 | 8.0 | 16.0 | 19.4% | 0.61 | 3.17 |
| Bolt | 8 | 1.50 | 8.0 | 12.0 | 38.8% | 1.26 | 3.26 |
| Bolt | 8 | 0.67 | 8.0 | 5.0 | 91.5% | 3.62 | 3.96 |
| Bolt | 8 | 1.00 | 8.0 | 8.0 | 70.1% | 2.46 | 3.51 |
| Bolt | 16 | 1.00 | 16.0 | 16.0 | 69.9% | 3.29 | 4.71 |
| Bolt | 16 | 2.00 | 16.0 | 32.0 | 19.3% | 0.82 | 4.25 |
| Bolt | 16 | 1.50 | 16.0 | 24.0 | 38.1% | 1.67 | 4.38 |
| Bolt | 16 | 0.67 | 16.0 | 11.0 | 89.1% | 4.60 | 5.17 |
| Bolt | 32 | 2.00 | 32.0 | 64.0 | 19.2% | 1.24 | 6.43 |
| Bolt | 32 | 1.50 | 32.0 | 48.0 | 38.3% | 2.54 | 6.64 |
| Bolt | 32 | 0.67 | 32.0 | 21.0 | 90.8% | 7.14 | 7.86 |
| Bolt | 32 | 1.00 | 32.0 | 32.0 | 70.8% | 5.03 | 7.11 |
| Shot | 4 | 2.00 | 4.0 | 8.0 | 19.7% | 0.59 | 2.98 |
| Shot | 4 | 1.50 | 4.0 | 6.0 | 38.3% | 1.14 | 2.98 |
| Shot | 4 | 1.00 | 4.0 | 4.0 | 70.2% | 2.10 | 2.99 |
| Shot | 4 | 0.67 | 4.0 | 3.0 | 85.8% | 2.57 | 3.00 |
| Shot | 8 | 1.50 | 8.0 | 12.0 | 38.3% | 1.15 | 3.00 |
| Shot | 8 | 1.00 | 8.0 | 8.0 | 70.8% | 2.13 | 3.00 |
| Shot | 8 | 2.00 | 8.0 | 16.0 | 19.6% | 0.59 | 3.00 |
| Shot | 8 | 0.67 | 8.0 | 5.0 | 91.7% | 2.77 | 3.02 |
| Shot | 16 | 2.00 | 16.0 | 32.0 | 19.7% | 0.79 | 4.00 |
| Shot | 16 | 1.00 | 16.0 | 16.0 | 70.4% | 2.82 | 4.00 |
| Shot | 16 | 0.67 | 16.0 | 11.0 | 89.2% | 3.57 | 4.00 |
| Shot | 16 | 1.50 | 16.0 | 24.0 | 38.1% | 1.52 | 4.00 |
| Shot | 32 | 2.00 | 32.0 | 64.0 | 19.4% | 0.98 | 5.04 |
| Shot | 32 | 1.50 | 32.0 | 48.0 | 38.9% | 1.98 | 5.09 |
| Shot | 32 | 1.00 | 32.0 | 32.0 | 71.1% | 3.73 | 5.25 |
| Shot | 32 | 0.67 | 32.0 | 21.0 | 90.3% | 4.96 | 5.50 |

## Automatic healing summary

Basic Mend has no to-hit roll; values below are its live synthetic-quality outcome distribution against an uncapped injured ally.

| Resolve level | Mean healing | Min | Max |
| ---: | ---: | ---: | ---: |
| 16 | 3.00 | 3 | 3 |
| 4 | 2.00 | 2 | 2 |
| 8 | 2.49 | 2 | 3 |
| 32 | 3.66 | 3 | 4 |
