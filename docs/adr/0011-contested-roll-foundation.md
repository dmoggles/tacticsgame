# 0011. Contested-roll foundation uses dynamic Resolve defence and centered 3d3 noise

## Status

Superseded in part by ADR 0012 (noise model and rounding behaviour); defence
model and contest primitives remain accepted.

## Context

Phase 3 replaces deterministic combat with opposed attacker-versus-defender
rolls. The roll needs to make attribute advantages dependable without making a
single unlucky outcome capable of deciding a future high-stakes battle. It also
needs to give Resolve a universal defensive role without reducing every attack
to the same static defence matchup.

## Decision

- `engine/resolution.py` now provides pure contest primitives:
  `weighted_attribute_score`, `primary_attack_attribute`, `defence_score`,
  `roll_contest_noise`, and `resolve_contest`. `ContestResult` records both
  scores, noise rolls, final rolls, signed margin, and success.
- Attack score is the effect component's existing weighted attribute scaling,
  without its flat base magnitude. Defence is `Resolve * 0.7` plus the
  defender's value in the incoming component's primary attack attribute
  (`* 0.3`). The primary attribute is the one unique scaling term with the
  highest multiplier; missing or tied primary terms raise `ValueError`.
- Each side adds independent centered `3d3 - 6` noise. Dice count, faces, and
  both defence weights are named values in `config.py`.
- Contest margins are rounded to named decimal precision before success is
  determined, so mathematically equal weighted scores cannot become accidental
  wins through binary floating-point representation.
- These functions consume the supplied seeded RNG. Existing ability effects do
  not yet call them: Step 3 will connect contest margin to magnitude.

## Consequences

**Positive**

- The distribution is bell-shaped and bounded (`-3` through `+3` per side), so
  central outcomes are common and extreme rolls are rare.
- Defence reacts to the kind of attack being received: a hero's Might helps
  against a Might-led strike, Focus against a Focus-led bolt, and so on, while
  Resolve always contributes.
- The entire roll is headless, deterministic under a seed, and directly
  testable before live combat behavior changes.

**Negative / trade-offs**

- The initial `3d3 - 6` width and `0.7/0.3` defence ratio are balance
  placeholders that require Phase 3 measurement and retuning.
- Tied primary attack scaling is invalid rather than resolved by an arbitrary
  tie-break; Step 4 must validate this in ability data.

**Explicitly deferred**

- Margin-to-magnitude scaling and the damage floor (Phase 3, Step 3).
- Per-ability contested/automatic and magnitude-variance data (Step 4).
- Expected-value previews, AI scoring, and player odds display.

## Alternatives considered

- **Static Resolve plus one fixed secondary attribute** — rejected: it makes
  all incoming attacks share one defensive relationship instead of reflecting
  their distinct attribute profiles.
- **Uniform random noise** — rejected: its flat probability makes extreme
  outcomes too common for the project’s intended hard consequences.
- **Wider 3d6 noise** — rejected initially: it would make variance dominate the
  current low attribute magnitudes before post-rework balance data exists.
