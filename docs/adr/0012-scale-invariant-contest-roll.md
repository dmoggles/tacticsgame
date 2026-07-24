# 0012. Scale-invariant continuous contest rolls replace fixed-width dice noise

## Status

Accepted; supersedes ADR 0011 in part (its noise model and rounding behaviour).

## Context

ADR 0011 used fixed-width centred `3d3 - 6` noise. In a persistent game, that
noise becomes negligible as attributes grow: equal-score odds silently move
towards certainty because the random range does not grow with the score. Its
discrete rolls also make ties a material rules artefact.

## Decision

- Each contest side rolls the mean of `N` independent continuous samples from
  `[0, score)`, with `N = 3`. The sample width therefore scales with its score
  while `N` controls the distribution's spread.
- The attacker score is multiplied by the global attacker-advantage constant
  before rolling. Resolve-plus-incoming-primary-attribute defence from ADR
  0011 remains unchanged.
- Ties require no special rounding rule: continuous samples make exact ties
  effectively absent, and a non-positive margin still fails.
- Damage uses the normalised margin `2 * margin / (advantaged attack score +
  defence score)`. This preserves the shape of a contest at every attribute
  scale, so no logarithmic or square-root compression is applied.

## Consequences

Equal score ratios have the same odds at low and high attributes, and seeded
battles remain reproducible. Three samples were chosen over a single uniform
sample because its central outcomes are less swingy; fixed additive noise was
rejected because it breaks scale invariance. Ability profiles now own their
damage-shaping knobs, while the roll count and defence weights remain global
configuration.
