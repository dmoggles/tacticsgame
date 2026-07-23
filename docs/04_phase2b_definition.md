# Phase 2b — Roster, Recovery & Directed Growth

## Goal

Phase 2a made the game playable across a sequence of battles. Phase 2b
builds the **non-combat half of the game**: the between-battle screen
where the player manages a roster, recovers injured heroes, and — for
the first time — deliberately steers a hero's growth.

Three systems land here, and they are deliberately coupled:

1. **Roster larger than the fielded squad**, with squad selection
   before each battle.
2. **Gradual recovery** — benched heroes heal faster than fielded ones,
   replacing 2a's placeholder full heal.
3. **Manual attribute allocation** — one player-chosen point per
   level-up, the mechanism by which a player steers a hero against
   their hidden affinity.

**Why these belong together:** gradual healing is a bench mechanic — a
damaged hero sitting out is only a decision if there's someone to swap
in, otherwise it's a death spiral. Conversely a bench is pointless
without carried damage, since you'd always field your best. And manual
allocation needs a screen to live on, which is the same screen roster
management needs. Splitting these further would ship three half-systems
that each need the other two to be testable.

This phase also delivers the **telemetry** that Phase 3 needs to set
Tier 1 unlock thresholds against real player behaviour.

---

## In Scope

### 1. Roster larger than the fielded squad

- The player has a **roster** (config constant, suggest 4) from which a
  **fielded squad** (config constant, currently 2) is selected per
  battle.
- Battle size stays 2v2 — no combat, AI, or balance work is disturbed
  by this phase. This is the cheapest possible expression of the
  mechanic.
- Roster and fielded-squad sizes must both be config-driven. The
  intended end state is 4 fielded plus a bench; nothing in the engine
  may assume the current values.
- Note: with a roster of 4 and up to 2 fielded, the "field fewer" choice
  is thin (2 or 1). That's expected — the decision space widens when
  fielded squad size grows in a later phase.

### 2. Squad selection before each battle

- Before each battle in a session, the player chooses which roster
  heroes to field, up to the fielded-squad maximum.
- The player may **field fewer than the maximum.** Per the Phase 2a XP
  model, the battle XP pool splits evenly among fielded heroes, so
  running short-handed concentrates growth into fewer heroes at the
  cost of fighting outnumbered. This is an intended decision point, not
  an exploit.
- Minimum of one fielded hero.
- Downed heroes (at minimal HP) may still be fielded — the player is
  free to make that mistake.

### 3. Gradual recovery

Replaces the `# TODO(phase2b)` full-heal placeholder from Phase 2a.

- Between battles, every hero recovers HP at a rate determined by
  whether they were **fielded** or **benched** in the battle just
  fought.
- Benched heroes recover substantially more (both rates are config
  constants). Exact values are placeholders — the point is that sitting
  out is the mechanism by which a hero returns to full strength.
- Recovery is expressed as a **config'd rate**, not baked into a heal
  function, so that consumables (instant recovery, out of scope — see
  below) can be added later without restructuring this.
- No separate injury system. A hero downed in battle revives at minimal
  HP (Phase 2a) and climbs back via the same recovery rate as any other
  damage. "She's been on the bench three fights and I want her back" is
  the intended feeling and it falls out of HP alone.

### 4. Bench bonus XP — turning on the plumbing

Phase 2a implemented `BENCH_XP_BONUS_MULTIPLIER * pool`, split among
benched heroes, defaulting to 0. Phase 2b is where that path is
actually exercised, since a bench now exists.

- The multiplier **stays at 0 by default.** It is intended to become
  upgradeable through meta-progression investment in a much later
  phase; that upgrade path is not built here.
- Consequence worth stating plainly: at multiplier 0, benching a hero
  to heal costs them all XP from that battle. This is intended tension
  — recovery competes with development — but it is the **first number
  to revisit** if playtesting makes rotation feel purely punishing.
  Keep it trivially tunable.
- Tests should cover the non-zero case even though the shipped default
  is zero.

### 5. Manual attribute allocation

The first implementation of player-directed growth, and the mechanism
by which a player steers a hero against their hidden affinity.

**Mechanics:**

- A level-up grants 3 attribute points, as now. Of those, **1 is
  chosen deterministically by the player** and the remaining 2 are
  distributed by affinity-weighted random draw, as currently
  implemented.
- The number of manually-allocated points is a **config constant,
  fixed at 1** for this phase. Training facilities, which raise it
  through investment, are out of scope. The design invariant is that
  this number can never reach the full per-level total — some portion
  of growth always remains affinity-driven.
- The choice is made on the **between-battle screen**, not mid-battle.
  Since Phase 2a moved levelling to battle end, this falls out
  naturally — no in-battle prompt is needed.
- Multi-level jumps present multiple allocation choices in sequence.
- If the player declines or skips, allocate the point by affinity like
  the others rather than forfeiting it.

**Why this matters (context for anyone tuning it later):** ability
damage scales off the attribute matching its archetype, and attributes
grow toward hidden affinity — so without this mechanic there's a
feedback loop where a hero's affinity determines which ability is best,
which determines what the player uses, which determines their
specialization. Affinity would quietly decide everything and player
agency over Track 2 would be largely cosmetic. The deterministic point
is what makes steering possible: it's a guaranteed +1 per level against
a random draw, so consistently investing in an off-affinity attribute
does eventually pay off — at the cost of several levels spent using an
ability the hero is currently bad at. That cost is the design; the
point is that the choice exists at all.

### 6. Between-battle screen

The payoff surface of this phase. It hosts squad selection (section 2)
and attribute allocation (section 5), and displays per hero:

- Level, and whether they levelled since the last battle.
- Current attributes, **with the delta from the previous battle
  highlighted** (e.g. "Might 7 → 9").
- Class XP per track (Fighter/Marksman/Caster/Healer), with delta.
- Current/max HP, and whether they are recovering.

**Hard requirement — no level-up history.** Show the current delta
only. A scrollable history of every past level-up's deltas would let a
player reconstruct the hidden affinity vector precisely with a
spreadsheet, which defeats an explicit design goal. The current delta
alone conveys "she keeps growing into Agility" without handing over the
numbers.

This is helped by the allocation mechanic: since the displayed delta
mixes the player's chosen point with two random ones, a single delta is
genuinely ambiguous about how much was affinity. Combined with no
history, reconstruction stays properly out of reach.

Still debug-grade UI — no art, no animation, no polish. Functional
layout is sufficient.

### 7. Telemetry for Phase 3

A concrete deliverable, not an afterthought. At session end, dump
per-hero progression data behind a flag (JSON or CSV; no analysis
tooling needed):

- Total class XP per track, level reached, final attribute spread,
  battles fielded vs. benched.
- **Class XP concentration** — how concentrated a hero's class XP ended
  up (any reasonable measure: share held by the top track, or a
  normalized entropy).
- **The hero's hidden affinity vector**, so concentration can be
  correlated against it offline.

**Why the affinity correlation specifically:** it tests whether player
agency over specialization is real or cosmetic. If class XP
concentration correlates strongly with affinity across played sessions,
it means heroes are becoming what they were born as regardless of
player intent — and the response would be to give off-affinity
abilities non-damage value, or to feed spec XP from role behaviour
rather than raw ability use. If the correlation is weak, steering is
working. This is the single most valuable thing a played session can
tell us, and it costs almost nothing to capture.

Affinity may appear in this dump because it is a **dev artifact, not a
player-facing path**. Keep it clearly separated from anything the UI
can reach.

---

## Explicitly Out of Scope

- **Consumables** (instant-heal items). These are the "pay to skip the
  wait" counterpart to gradual recovery, and imply a currency and
  reward economy downstream of run structure. Deferring them costs
  nothing so long as recovery is a config'd rate rather than baked in.
- Training facilities / any variation in the number of manually
  allocatable points. The count is fixed at 1 here.
- Tier 1 archetype unlocks, perk trees, Tier 2 branches, multiclassing
- Track 3 ability training
- Contested-roll resolution — `rng` stays plumbed and unused
- Secondary resources, equipment/gear, AoE abilities, new abilities
- Meta-progression, rewards, currency, run structure
- Save/load across process restarts
- Permanent hero loss — downed-not-dead remains the model
- Difficulty scaling curves for generated enemy squads
- Agility-driven initiative, terrain, telegraphed enemy intent

---

## A note on the roguelite question

Still does not need answering, and should not be answered
speculatively in code. Build the session as a self-contained sequence
with no reset semantics either way.

Phase 2b is the thing most likely to answer it: after several battles
of rotating a roster and watching heroes recover, it will be much
clearer whether losing them at session end reads as painful-in-a-good-
way or merely annoying.

---

## Acceptance Criteria

Phase 2b is done when:

1. A roster larger than the fielded squad exists, both sizes
   config-driven, with no engine code assuming the current values.
2. The player selects a fielded squad before each battle, may field
   fewer than the maximum, and the Phase 2a XP pool splits evenly
   across however many were fielded — verified by a test asserting a
   short-handed squad receives proportionally more XP each.
3. Gradual recovery replaces the full-heal placeholder; benched heroes
   recover faster than fielded ones, both rates config'd, verified
   across a multi-battle session test.
4. Bench bonus XP is awarded correctly to benched heroes, tested at
   both the default 0 multiplier and a non-zero value.
5. A hero downed in battle revives at minimal HP and recovers over
   subsequent battles via the standard recovery rate.
6. On level-up, the player allocates 1 point deterministically and 2
   are affinity-weighted; skipping allocates by affinity rather than
   forfeiting; multi-level jumps present sequential choices. Covered by
   headless tests against the allocation data model.
7. The between-battle screen displays level, attributes with deltas,
   class XP with deltas, and HP/recovery status — verified manually and
   by a headless test asserting correct deltas across a two-battle
   session.
8. **No level-up history is exposed anywhere in the UI.**
9. Session-end telemetry dumps per-hero class XP, concentration,
   affinity vector, level, attributes, and fielded/benched counts
   behind a flag.
10. `uv run ty check` passes cleanly; `uv run pytest` passes.

---

## Suggested build order

1. Roster + fielded-squad data model and squad selection (headless,
   testable without UI).
2. Recovery rates replacing the full-heal placeholder; bench bonus XP
   path exercised.
3. Manual allocation data model — the choice and its application,
   independent of any screen.
4. Between-battle screen wiring all three together.
5. Telemetry dump.

As with 2a, the headless data-model work should land and be tested
before any of it is wired to a screen.
