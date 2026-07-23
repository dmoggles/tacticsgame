# Work Order — Attribute Variance & Ability Differentiation

## Status

Not a phase. This is a corrective work order sitting between Phase 2b
and any Phase 3, in the same spirit as the post–Phase 1 "AI, Balance &
Ability-Data Refactor" chunk.

It exists because telemetry from five played sessions (20 heroes)
showed that a hero's Tier 2 class track is currently a **deterministic
function of their attribute spread**: across all 18 heroes who used a
ranged ability, the track was Caster if Focus > Agility and Marksman if
Agility > Focus, with no exceptions. The two exact ties both resolved
to Marksman via first-match tie-breaking.

---

## Goal

Make a hero's specialisation a **lean rather than a destiny**.

The design intent — per the vision doc's discovery pillar, and per the
framing that Tier 1 is the admission ticket out of being classless
rather than the player's big choice — is that a hero's archetype
*should* be largely foreseeable from their nature. That's coherence,
not a bug. The problem is that it is currently **entirely** foreseeable,
which means Track 2 carries no information Track 1 doesn't already
contain, and the manual allocation point built in Phase 2b cannot
influence anything.

Target: specialisation predictable from the attribute spread roughly
two-thirds to three-quarters of the time, with the remainder driven by
how the hero was actually played. **Do not tune toward zero
predictability** — overcorrecting into randomness breaks the discovery
pillar in the other direction.

Two independent causes need addressing, and fixing only one will not
work:

- **Ability choice is a pure function of attributes.** Damage scales
  off exactly one attribute, the strongest ability is whichever
  attribute is highest, and class XP follows ability identity. Nothing
  about the board state enters the calculation.
- **Attribute spreads are landslides, not leans.** Focus 12 / Agility 2
  is a verdict. Even if situational factors could flip a choice, they
  cannot overcome gaps of 8–11 points.

---

## In Scope

### 1. Telemetry additions — do these first

The whole work order is measured against a metric, so the metric must
be capturable before anything changes.

Add to `engine/telemetry.py::write_session_report`, per hero:

- **Per-ability use counts** — how many times each of the four basics
  was actually used. Class XP is only a proxy for this; usage is the
  thing being influenced.
- **Manual allocation choices** — which attribute the player picked at
  each level-up, or that they declined. This is the steering *input*
  and it is currently unrecorded, which makes "tried to steer and
  failed" indistinguishable from "never tried."

Both are dev-side artifacts. The no-history rule from Phase 2b governs
the **UI**, not the telemetry dump — nothing here becomes reachable
from a player-facing path.

Capture a fresh baseline with these fields before making any of the
changes below.

### 2. Synthesis variance (addresses cause 2)

- The Dirichlet concentration parameter is currently an implicit
  `1.0` in `generate_hidden_affinity`. **Lift it to a named config
  constant** (`AFFINITY_CONCENTRATION` or similar) — per the
  architecture doc's no-magic-numbers rule, this is exactly the kind of
  value that will be retuned repeatedly.
- Raise it from 1.0 to a starting value of **2.0–3.0**. Dirichlet(1,…)
  is uniform over the simplex, so extreme vectors are as likely as
  balanced ones; a higher concentration keeps a discernible lean while
  bringing the second-best attribute close enough to matter.
- Second payoff, and part of the point: the Phase 2b manual allocation
  point goes from irrelevant against an 11-point gap to meaningful
  against a 3-point one. The steering mechanism the between-battle
  screen was built around only begins to function after this change.

### 3. Ability differentiation (addresses cause 1)

The substantive item. Each of the four basics must be distinguishable
by something **other than which attribute it scales**, so that a hero's
*position* constrains what they can use and class XP becomes a function
of attributes **and** how the hero was played.

The pattern already exists in the codebase — Shot has a minimum range,
Mend has a 3-turn cooldown. Extend it so every ability has a
situational identity. Starting suggestion, to be tuned rather than
taken as final:

| Ability | Range | Distinguishing property |
|---|---|---|
| Basic Strike | 1 | Highest damage, melee only |
| Basic Bolt | 1–3 | No minimum range; more damage than Shot |
| Basic Shot | 2–5 | Longest reach; cannot fire point-blank |
| Basic Mend | as now | 3-turn cooldown (unchanged) |

The property that matters is the **overlap structure**: at range 1 the
choice is Strike or Bolt; at 2–3 it's Bolt or Shot; at 4–5 only Shot
works. A Focus hero forced to long range must use Shot and accrues
Marksman XP; a Might hero pinned at range 3 must use Bolt and accrues
Caster XP. That mixing is the entire mechanism — preserve it through
whatever tuning follows.

Also: `Basic Shot` and `Basic Bolt` currently share an identical range
of 4, which is what produced the tie-breaking artifact flagged in Phase
1 and confirmed in play. Any tuning must keep them genuinely distinct.

### 4. Multi-attribute scaling (supporting, and the Resolve fix)

The ability data model already supports several scaling terms per
effect (ADR 0001), so this is a **YAML-only change with no code**.

- Give at least one attack ability a meaningful **Resolve** scaling
  term. Resolve is currently a dead-end: Might, Focus and Agility each
  scale an attack, while Resolve scales only a conditional heal. Both
  heavily Resolve-weighted heroes in the telemetry (affinity 0.75 and
  0.72) ended up in Marksman and Caster respectively, taking their
  ticket from their *second* attribute, because they had no offensive
  expression of their first. Folding a Resolve term into a melee or
  short-range attack is the cheapest fix and keeps the attribute set
  symmetric with the four class tracks.
- Beyond that, secondary scaling terms are worth adding for texture,
  but be clear-eyed about what they do: they make the deterministic
  function **harder to read**, not less deterministic. They support
  item 3; they do not substitute for it.

### 5. Session length, difficulty curve, and XP pacing

Every hero finished a five-battle session at level 1 or 2. One level-up
per session means the manual allocation choice — the player's only
steering lever — is exercised once or not at all. Rather than retuning
the XP threshold, address this structurally:

- **Extend the session from 5 battles to 10** (`config.SESSION_BATTLE_COUNT`).
- **Battles 6–10 field 3 enemies instead of 2.** This escalates
  difficulty and accelerates XP simultaneously — the pool already scales
  with enemy count, so no formula change is needed. Implement the count
  as a single clearly-marked curve function, consistent with the
  existing convention for the enemy generator.
- **Set `BENCH_XP_BONUS_MULTIPLIER` to 0.2** (from 0).

**On the bench multiplier — this reverses an earlier decision.** Phase
2b shipped it at 0 with the intent that meta-progression would unlock
it from nothing. It now starts at 0.2 and meta-progression raises it
from there. The reason is that a benched hero currently develops not at
all, so with roster 4 and fielded 2 a hero is standing still half the
time — which is the dominant reason heroes finish sessions at level 1–2,
more so than session length. The cost is that "the bench starts
earning" is no longer available as a meta-progression reveal.

**Watch the ratio, not the constant.** The multiplier applies to the
whole pool and is then split among the benched. At roster 4 / fielded 2
this happens to work out to each benched hero earning exactly 20% of a
fielded hero's share — but that equivalence is a coincidence of the
current squad sizes. At fielded 4 of a roster of 6 the same 0.2 constant
yields 40% of a fielded share. If squad sizes change, re-derive the
effective rate rather than assuming the constant still means what it
means today.

**Early-game difficulty is in scope after all.** Two of five sampled
sessions ended in a loss after two battles. If early difficulty is
already too steep, extending the session and escalating the back half
achieves nothing — sessions will keep ending before battle 6, and the
accelerated stretch never gets played. Pull early difficulty down until
sessions reliably reach the escalation, then judge the curve as a whole.

**Expect this to get most of the way, not all of it.** Doubling the
battle count roughly doubles level-ups, and the back-half enemy increase
adds perhaps another quarter — landing near 2.5–3 level-ups per fielded
hero rather than 3–4, before the bench multiplier's contribution. Keep
`config.XP_LEVEL_THRESHOLD` available as a trim, applied after
measurement rather than pre-emptively.

### 6. Bug fixes surfaced by telemetry

- **Dropped attribute point.** Level-1 heroes total exactly 19
  attribute points and level-2 heroes exactly 22 across 19 of 20
  sampled heroes; one level-2 hero totalled 21. Suspected cause: a
  pending manual-allocation point being dropped when a level-up lands
  in the session's final battle, with no between-battle screen
  following to resolve it. Confirm and fix; add a regression test that
  a pending allocation is never silently discarded at session end.
- **Bench starvation.** The between-battle screen defaults to
  re-fielding last battle's squad (a deliberate Phase 2b convenience),
  but in practice one hero was benched for an entire session twice in
  five, and 4-of-5 battles in another. The bench XP change in item 5
  softens the consequence — a benched hero now develops slowly rather
  than not at all — but doesn't address the default that caused it, and
  a hero who never plays still contributes no telemetry. Consider
  surfacing battles-benched more prominently on the screen, or
  defaulting toward heroes who have sat out. Do not remove the player's
  ability to bench someone indefinitely — this is a nudge, not a
  constraint.

---

## Explicitly Out of Scope

- Tier 1 archetype unlocks — this work order prepares the signal they
  will be built on; it does not build them
- Tier 2 branches, multiclassing, Track 3 ability training
- Contested-roll resolution — `rng` stays plumbed and unused
- New abilities beyond the four basics
- Increasing fielded squad size beyond 2. Worth noting this is now the
  most likely next candidate: at 3 enemies in the back half, "field
  fewer heroes for a larger XP share" stops being a live option, so the
  tension deliberately built in Phase 2b exists only in battles 1–5
  until the fielded squad grows.
- Enemy *quality* scaling — enemies remain generated at flat strength;
  only their count changes. Hero levels therefore outpace enemy
  strength across a session by design.
- Equipment, consumables, secondary resources, meta-progression, run
  structure, save/load

---

## Expected Consequences

**The AI baseline fixture will need regenerating.** Items 2, 3 and 5
all change combat trajectories legitimately. Apply the same discipline
as Phase 2a step 2: diff the fixture field-by-field before regenerating,
confirm every delta is attributable to an intended change rather than a
bug, and document it. Do not regenerate silently to make a comparison
pass.

**ADRs are warranted** for items 2 and 3 — the synthesis variance
change and the ability differentiation scheme are both real design
forks with alternatives worth recording.

---

## Acceptance Criteria

1. Telemetry captures per-ability use counts and per-level-up manual
   allocation choices; a pre-change baseline has been captured using
   the extended schema.
2. The Dirichlet concentration parameter is a named config constant and
   no longer an implicit 1.0.
3. All four basic abilities are differentiated on range and/or cooldown
   such that no two are interchangeable at any board position; Shot and
   Bolt in particular no longer share an identical range.
4. At least one attack ability scales meaningfully off Resolve.
5. Sessions run 10 battles, with battles 6–10 fielding 3 enemies via a
   single clearly-marked curve function; `BENCH_XP_BONUS_MULTIPLIER` is
   0.2. A full session produces at least 3 level-ups per consistently
   fielded hero — apply the `XP_LEVEL_THRESHOLD` trim only if
   measurement shows it falls short.
6. Sessions reliably reach the escalated back half. If a meaningful
   fraction still end before battle 6, early difficulty needs pulling
   down further before the curve can be judged.
7. The dropped-attribute-point bug is reproduced, fixed, and covered by
   a regression test.
8. **Re-measurement:** after the changes, run a set of sessions
   (AI auto-play is acceptable and preferred for volume — at least 20
   sessions) and report what fraction of heroes' top class track is
   predicted by their top matching attribute. Report the figure; do not
   tune blindly toward the two-thirds-to-three-quarters target, since
   the right value is ultimately a judgement call the played feel
   should inform.
9. Per-ability use counts show all four basics being used across the
   sample, with none effectively dead.
10. `uv run ty check` passes cleanly; `uv run pytest` passes.

---

## Suggested Build Order

1. Telemetry additions; capture extended baseline.
2. Synthesis variance (config constant + raised concentration).
3. Ability differentiation in YAML; retune.
4. Resolve scaling term.
5. Session length, enemy curve, bench multiplier, early-game difficulty.
6. Bug fixes.
7. Re-measure and report; regenerate the AI fixture with a documented
   diff.

Steps 2, 3 and 5 all move combat balance, so expect the fixture diff at
step 7 to be substantial. That is fine — what matters is that every
delta is explainable.

Note that step 5 is the one most likely to need iterating on: the
difficulty curve and the level-up count are judged against played
sessions, not derived, so expect to run the measurement, adjust, and
run it again rather than landing it in one pass.
