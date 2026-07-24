# Phase 3 Contest Foundation — Headless Simulation

**Date:** 2026-07-23  
**Model:** current Step 2 foundation — attacker score versus defence score,
then independent `3d3 - 6` noise on each side. Ties fail.

## Method

`scripts/simulate_contests.py` runs 50,000 seeded trials for every
combination of:

- Basic Strike (`Might × 0.8 + Resolve × 0.4`), Basic Bolt (`Focus × 1.0`),
  and Basic Shot (`Agility × 1.0`);
- attacker primary-attribute values 4, 8, and 12;
- defender Resolve values 4, 8, and 12; and
- defender matching-primary-attribute values 4, 8, and 12.

That is 81 scenarios and 4.05 million headless contests, using simulation
seed `20260723`. Reproduce the full table with:

```bash
uv run python scripts/simulate_contests.py
```

## Representative outcomes

Bolt and Shot use the same one-attribute profile and therefore produce the
same rates within sampling noise. These Bolt rows show the main score
relationship cleanly.

| Attacker Focus | Defender Resolve | Defender Focus | Attack score | Defence score | Success rate | Mean margin |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 4 | 4 | 8.0 | 4.0 | 96.2% | +3.99 |
| 8 | 4 | 8 | 8.0 | 5.2 | 89.2% | +2.80 |
| 8 | 8 | 4 | 8.0 | 6.8 | 76.8% | +1.20 |
| 8 | 8 | 8 | 8.0 | 8.0 | 40.5% | +0.00 |
| 8 | 8 | 12 | 8.0 | 9.2 | 23.1% | -1.20 |
| 8 | 12 | 8 | 8.0 | 10.8 | 10.6% | -2.82 |
| 8 | 12 | 12 | 8.0 | 12.0 | 1.0% | -3.99 |

Strike's secondary Resolve scaling gives it a distinct profile. With 4 Might
and 4 Resolve against a defender with 4 Resolve and 4 Might, Strike has a
4.8 attack score against 4.0 defence and lands 59.7% of the time. At 8 Might
and 4 Resolve against 8 Resolve and 8 Might, both scores are 8.0 and it lands
40.7% of the time.

## Findings

- **Resolve is load-bearing.** Raising defender Resolve from 4 to 12 changes
  defence by 5.6 points even when the matching attack stat does not change.
- **The current distribution is deliberately narrow.** A four-point score lead
  produces roughly 96% success; a four-point deficit produces roughly 1%.
  Stats dominate outcomes, and the dice mainly decide close contests.
- **Equal scores are not 50/50.** They land about 40% of the time because
  tied rolls fail. This is intentional in the current success rule, but should
  remain visible during post-integration tuning.
- **Integer dice create threshold plateaus around fractional weighted scores.**
  For example, Strike's 4.8 versus 4.0 score edge lands about 59.7%, because
  an otherwise tied noise result is enough to win; 4.8 versus 5.2 instead lands
  about 40.3%. The later balance pass should decide whether this sharpness is
  desirable or whether wider dice, different weights, or a different tie rule
  are warranted.

## Scope note

This measures only contest success and margin. Live damage is still
deterministic; Step 3 will make its magnitude depend on the margin and must
repeat the relevant sweeps once that mapping exists.
