# 0010. Basic ability differentiation and Resolve attack scaling

## Status

Accepted

## Context

In initial phases, basic abilities had overlapping or identical ranges (e.g. Basic Bolt and Basic Shot both shared range 4), and damage scaled strictly off single attributes (Might -> Strike, Focus -> Bolt, Agility -> Shot). Additionally, Resolve lacked any offensive expression, scaling only a conditional heal (Basic Mend), leaving Resolve-leaning heroes with no offensive way to leverage their primary stat.

Because abilities were interchangeable at several board distances and damage was purely a function of stats, combat positioning did not constrain ability choice. heroes always picked whichever ability matched their highest stat.

## Decision

- Differentiate all four basic abilities on range, minimum range, and cooldown in `data/abilities.yaml`:
  - **Basic Strike**: Melee range 1 (min 0), highest damage (base 5, Might 0.8 + Resolve 0.4 scaling).
  - **Basic Bolt**: Medium range 1–3 (min 0), higher damage than Shot (base 5, Focus 1.0 scaling).
  - **Basic Shot**: Long reach range 2–5 (min 2), cannot be fired point-blank (base 4, Agility 1.0 scaling).
  - **Basic Mend**: Range 3 (min 0), 3-turn cooldown, heal base 6 (Resolve 0.5 scaling).
- Add a Resolve scaling term (`resolve: 0.4`) to **Basic Strike** alongside `might: 0.8`. This gives Resolve an offensive expression, keeping attribute growth symmetric with the four class tracks.

## Consequences

**Positive**

- Establishes clear range overlap structure:
  - Range 1: Strike or Bolt
  - Range 2–3: Bolt or Shot
  - Range 4–5: Only Shot
- Positioning forces heroes to make situational ability choices (e.g., a Focus hero at range 5 must use Shot and accrue Marksman XP; a Might hero at range 3 must use Bolt and accrue Caster XP).
- Telemetry confirms all four basic abilities are used regularly in play.
- Resolves the Resolve dead-end problem by allowing Resolve-leaning heroes an offensive output.

**Negative / trade-offs**

- AI battle trajectories and target selections changed, requiring baseline fixture regeneration.

## Alternatives considered

- **Make Basic Bolt melee-only** — rejected: deprives casters of medium reach and collapses Caster identity into Fighter.
- **Add a new fifth ability for Resolve** — rejected: out of scope for Tier 0 classless kit invariant (which specifies exactly 4 starting abilities).
