# 0009. Synthesis variance via named AFFINITY_CONCENTRATION parameter

## Status

Accepted

## Context

Telemetry from initial play sessions showed that hero specialisation tracks were deterministic functions of attribute spreads: across all heroes using ranged abilities, Focus > Agility reliably produced Caster and Agility > Focus produced Marksman, with no exceptions.

Initial hero generation used an implicit Dirichlet concentration parameter of `1.0` (`DIRICHLET_ALPHA`), representing a uniform distribution over the 4-simplex. This frequently generated extreme attribute leanings (gaps of 8–11 points), rendering subsequent manual attribute allocations and situational board play completely unable to steer a hero's specialization path.

To make specialization a lean rather than a fixed destiny (targeting predictability around 66%–75%), hero attribute spreads needed to be brought closer together without eliminating character archetype identity.

## Decision

- Lift the implicit `1.0` Dirichlet parameter to a named, explicit configuration constant: `AFFINITY_CONCENTRATION` in `src/tactics_game/config.py`, with an initial value of `2.5`.
- Maintain `DIRICHLET_ALPHA = AFFINITY_CONCENTRATION` for backwards compatibility in existing tests.
- Update `progression.generate_hidden_affinity` to draw Gamma samples using `config.AFFINITY_CONCENTRATION`.

## Consequences

**Positive**

- Narrowed attribute point spreads (e.g., gaps of 2–4 points instead of 8–11 points), enabling manual allocation points and situational in-battle decision making to meaningfully steer class progression.
- Empirical telemetry re-measurement confirmed a predictability rate of ~65% (matching the 66%-75% target window).
- Replaces magic numbers with a named tuning constant in accordance with architecture guidelines.

**Negative / trade-offs**

- Synthesized hero attribute profiles are less extreme, requiring AI baseline fixtures to be regenerated and documented.

## Alternatives considered

- **Keep concentration at 1.0 and rely solely on ability range overlaps** — rejected: large attribute gaps (8–11 points) consistently overwhelmed situational XP gains regardless of board positioning.
- **Set concentration > 5.0 (near uniform attributes)** — rejected: overcorrected into randomness, destroying hero identity and violating the discovery pillar.
