# Project Vision & Design Context

## Purpose of this document

This captures the full design intent behind the project — the "why"
and "eventually what" — separate from any single phase's build scope.
Phase documents (e.g. `02_phase1_definition.md`) define what's
actually being built *right now* and will often explicitly exclude
things described here. **This document is not a build spec.** When
something here conflicts with a phase document on what to build
today, the phase document wins. This exists so future phase docs
don't need to re-explain the whole system from scratch, and so
anyone (human or agent) picking up the project mid-stream has the
full picture of where it's headed.

---

## Elevator pitch

A turn-based, grid-based hero-tactics game (Into the Breach-style
positioning and readability) built around a small, persistent squad
of heroes who develop real attachment over the course of a run — not
through a large disposable roster, but through visible, earned,
partially-unpredictable growth of a handful of characters you keep
choosing to field.

The progression system is directly inspired by *Football, Tactics &
Glory*'s player development model — specifically its combination of
hidden per-character affinity, weighted-random attribute growth, a
separate usage-based specialization system, and skills that improve
by changing *how reliably* they work rather than just scaling numbers.

---

## Core pillars

- **Attachment through earned, semi-unpredictable growth.** Heroes
  aren't blank slates the player fully sculpts, nor are they fixed
  archetypes. They have a hidden "nature" (affinity) that growth
  leans toward, with limited player influence — so a hero's build
  feels *discovered* through play, not just assigned.
- **Classless start, emergent specialization.** No hero begins locked
  into a role. What a hero becomes is driven by how the player
  actually uses them in battle.
- **Deterministic, readable tactical combat.** Positioning and
  decision-making matter more than randomness at the moment-to-moment
  battle level (ITB-style telegraphing is the aspirational feel,
  though early phases start fully deterministic and simple).
- **Abilities as evolving equipment, not fixed kit.** An ability tied
  to a hero today should be swappable/upgradable/replaceable in the
  future — abilities are data that scales and changes, not hardcoded
  per-hero methods.

---

## The Three Progression Tracks

The hero development system has three genuinely independent tracks,
each fed by a different kind of play:

### Track 1 — Level & Attributes ("just showing up")

- Four attributes: **Might, Focus, Resolve, Agility.**
- Each hero has a **hidden affinity vector** across these four
  attributes (generated via a Dirichlet distribution — positive
  weights summing to 1), never revealed to the player directly. It
  can be *intuited* from how a hero's stats develop over time, but
  never shown as a number.
- Heroes gain XP from battle participation. On leveling up, they gain
  a fixed number of attribute points, distributed via a weighted
  random draw against their hidden affinity — growth naturally trends
  toward what a hero is "meant" to be, without being deterministic or
  fully visible.
- **Future feature (not yet implemented):** limited **manual
  allocation** — the player can lock a small number of points per
  level-up to a stat of their choosing, deterministically overriding
  the random weighting. The number of points that can be manually
  allocated is gated by investment in a training-facility meta-system
  (starts at a small number, e.g. 1, and increases with investment).
  A hero can never reach *full* manual allocation, no matter how
  invested the facilities are — some portion of growth always remains
  affinity-driven.

### Track 2 — Specialization (usage-based role identity)

Two tiers, both earned by *what the hero actually does in battle*,
not by an upfront class choice:

- **Tier 0 — classless universal kit.** Every hero starts with the
  same four basic abilities: melee strike, ranged physical shot,
  ranged spell bolt, and a heal. Using each accrues XP toward a
  corresponding broad archetype track:
  - Basic Strike → **Fighter**
  - Basic Shot → **Marksman**
  - Basic Bolt → **Caster**
  - Basic Mend → **Healer**
- **Tier 1 — broad archetype (future).** Crossing an XP threshold in
  one of the four tracks unlocks that archetype's perk tree, a stat
  growth lean, and typically an upgraded action. Unlocking one
  doesn't lock out the others — a hero can walk into multiple Tier 1
  archetypes over time (see Multiclassing below).
- **Tier 2 — fine specialization (future).** Within an unlocked Tier
  1 archetype, more specific in-battle behavior drives finer branches
  — e.g. within Fighter: tanking hits/holding position → **Vanguard**,
  landing killing blows/chaining attacks → **Duelist**. Within Caster:
  landing CC effects → **Controller**, AoE/burst damage → **Blaster**.
  Similar splits exist for Marksman (Sharpshooter/Skirmisher) and
  Healer (Mender/Warder).

### Track 3 — Ability Training (deliberate investment, future)

- Abilities are trained over time (queued, completes after N battles,
  rushable with a run currency), not instantly unlocked.
- Ability **levels change how reliably they work, not just their
  power** — this is the mechanic borrowed most directly from FT&G and
  considered a core part of the game's identity. A level 1 ability is
  a single contested check (attacker attribute vs. defender
  attribute); level 2 grants a second check if the first fails; level
  3 further improves (guaranteed effect, or an added bonus). Leveling
  an ability should feel like it becomes *trustworthy*, not just
  bigger numbers.
- Ties into the "abilities as equipment" pillar — an ability's data
  representation should support this kind of scaling/evolution from
  early on, even in phases where the actual math is flat/placeholder.

---

## Multiclassing (future)

Crossing into a second Tier 1 archetype is a **deliberate, costed
decision**, not automatic — reaching the XP threshold in a second
track offers the player a choice to commit or decline. Declining
simply wastes/banks the off-track XP with no penalty; the hero stays
a clean specialist.

Committing applies a **menu of possible tradeoffs** (design intends
to let the player pick which cost(s) apply, giving multiclassing a
build-flavor feel rather than a flat tax):

- Diluted/shared perk tree pool across both archetypes
- Slower ability training (fewer training "slots")
- **Reduced manual attribute allocation** (Track 1) — specifically,
  multiclassing reduces the number of manually-allocatable points per
  level-up by 1, relative to whatever the training facility tier
  currently grants. This means a multiclassed hero can never reach
  full manual allocation even at max facility investment — a durable,
  legible cost that doesn't require its own separate mechanic.

Diverging *within* a single Tier 1 archetype (e.g. a Fighter earning
both Vanguard and Duelist behavior) is intended to be a **softer,
automatic dilution** rather than requiring the same explicit
commit-and-pay decision — refinement within an archetype, not a split
of core identity.

---

## Squad & Run Structure (future, loosely defined)

- Persistent hero roster within a run (not disposable units) — target
  is **4 active heroes + a bench**, developed further as design
  continues.
- No permadeath by default, or a soft version (downed, not dead) —
  permanent loss should be rare and meaningful, not a routine outcome.
- Run structure: sequence of battles across escalating "islands,"
  reward choices between battles, meta-currency and meta-unlocks
  across runs (roguelite reset favored over fully persistent
  cross-run heroes, for balance/scope reasons).

---

## Battle Loop (future, loosely defined)

- Grid-based (8x12 confirmed as the working size), deterministic
  positioning-first combat in the spirit of Into the Breach —
  telegraphed enemy intent, no hidden information about what's about
  to happen, puzzle-like decision-making.
- Early phases intentionally simplify this significantly (flat
  movement, no telegraphing, primitive AI, deterministic ability
  resolution) to validate the core loop and progression tracks before
  adding tactical depth.

---

## Explicit non-goals / deferred decisions

These have been discussed but intentionally left unresolved pending
further design work — not forgotten, just not yet decided:

- Exact XP thresholds, point totals, and other balance numbers
  (treated as tunable, not yet meaningful)
- Full enemy AI sophistication / telegraphing system
- Equipment/item systems
- Whether hidden affinity is ever indirectly reconstructable via a
  stats-history screen, or stays fully opaque forever
- Whether a 5th Tier 1 archetype or Tier 2 branch (e.g. Skirmisher) is
  warranted once four feels tested
- Multiplayer/shared state — current design assumes single-player

---

## Relationship to phase documents

Each phase document should:

- Reference this document for *why*, not restate it
- Explicitly list what subset of this vision is in scope
- Explicitly list relevant deferred systems as **out of scope**, so
  scope creep doesn't happen by accident
- Feel free to make placeholder decisions (flat numbers, simplified
  mechanics) where this document describes a future, richer version —
  placeholders should be flagged in code as such (see architecture
  doc's conventions on config constants and TODO comments)
