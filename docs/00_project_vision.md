# Project Vision & Design Context

*Revision 2 — supersedes the original vision document.*

## Purpose of this document

This captures the full design intent behind the project — the "why" and
"eventually what" — separate from any single phase's build scope. Phase
documents and work orders define what is actually being built right now
and will often explicitly exclude things described here. **This document
is not a build spec.** Where it conflicts with a phase document on what
to build today, the phase document wins.

It exists so phase docs don't re-explain the whole system, and so anyone
picking the project up mid-stream has the full picture.

**What changed in revision 2.** The original document deferred the
question of run structure and leaned toward a roguelite reset. That
question is now resolved in the other direction: **the game is a
persistent career game, not a roguelite.** That single decision changes
what the tension is, what the goals are, and what the progression
systems are for, so most of this document is rewritten rather than
amended. The fiction is now a **mercenary company**, which in turn
reframes the tactical layer — an open elimination-based grid reads as an
arena and fights the fiction, so terrain, objectives and eventually fog
of war become direction rather than polish. Revision 2 also records
empirical findings from played and simulated sessions that now constrain
the design — see "What the data has told us."

---

## Elevator pitch

A turn-based, grid-based tactics game about running a **mercenary
company** over the long term. You recruit, develop, field, and
eventually lose a roster of heroes who grow in ways you only partly
control. The tactical layer is readable and positioning-driven; the
career layer is where the game actually lives.

The progression model is directly inspired by *Football, Tactics &
Glory* — hidden per-character affinity, weighted-random attribute
growth, usage-driven specialisation, and skills that improve by becoming
more *reliable* rather than merely stronger. That model was built for a
persistent career game, which is a large part of why this project is one
too.

---

## The fiction: a mercenary company

The mercenary company frame is not decoration. It supplies the four
things a persistent career structure needs, in the same way a football
pyramid does for FT&G:

- **An external ladder.** Reputation tiers gate access to better
  contracts. Ambition is legible without needing a story: work your way
  up to the contracts only the best companies get offered.
- **A repeating verdict.** A contract (or campaign season) ends, and it
  went well or it didn't. Clear, recurring, unambiguous.
- **Difficulty escalation from the fiction.** Harder opposition isn't a
  dialled-in curve; it's what a tier-four contract means.
- **A reason turnover exists.** Mercenaries age, get hurt, and quit.
  Without turnover, a career game is a ratchet where the best get better
  forever and no development decision has a downside.

---

## Core pillars

- **Attachment through earned, semi-unpredictable growth.** Heroes are
  neither blank slates the player sculpts nor fixed archetypes. Each has
  a hidden nature that growth leans toward, with limited player
  influence — so a build feels *discovered* through play as much as
  assigned.
- **Attachment requires loss.** A persistent roster only carries
  emotional weight if heroes can be taken away. Attrition is the
  emotional core, not a punishment layered on top.
- **Development time is the scarce resource.** Not survival. Every hero
  you improve is one you didn't. This replaces run-death as the source
  of tension and is what makes the progression tracks decisions rather
  than accumulation.
- **Classless start, emergent specialisation.** No hero begins locked
  into a role. What they become follows from how they get used.
- **Readable, deterministic combat within contact.** Positioning and
  decision-making over randomness, Into the Breach in spirit. Note that
  this is scoped to *contact*: uncertainty about what has not yet been
  found is a separate matter and is a deliberate part of the design —
  see "The tactical layer" for the reconciliation.
- **Abilities as evolving equipment, not fixed kit.** Abilities are data
  that scales, upgrades, and swaps — not hardcoded per-hero methods.

---

## The career loop

- A **contract** (currently implemented as a "session" — a sequence of
  battles) is the unit of play. It has a beginning, an end, and a
  verdict.
- Contracts are gated by **reputation** and pay out in **money**.
  Consequences persist: heroes carry level, attributes, class progress,
  wounds, and age forward indefinitely.
- Between contracts is where the career game happens: recruitment,
  facility investment, ability training, wound treatment, and deciding
  who develops and who sits.
- There is no reset. A hero's arc runs from raw recruit to veteran to
  whatever end they meet.

**Open: what a bad verdict costs.** Something must be at stake in a
contract beyond hero attrition — money, reputation, or access. This is
undecided and is a prerequisite for designing the contract layer.

---

## Attrition: the tension engine

Four graded mechanisms remove heroes from the roster, from soft to hard:

- **Age and retirement.** Every hero has an age. The probability they
  hang up their boots rises as they get older. Retirement should be
  **telegraphed** rather than rolled silently — a hero signalling
  they're considering it gives the player a final campaign with them and
  a real decision, where a hero simply not appearing next contract is
  just a lost dice roll.
- **Wounds.** Being downed in battle inflicts a permanent malus. Wounds
  also raise retirement probability, so damage accumulates across a
  career in two directions at once. Wounds should be legible and
  characterful (a named injury with a specific effect) rather than an
  abstract stat decrement — that's what makes them a story instead of a
  number.
- **Death.** A downed hero dies if not **rescued** in time.
- **Departure by economics** (possible, undesigned): heroes you can't
  afford to keep.

**The rescue mechanic is the design's best structural idea and should be
protected.** A hero going down converts the battle into a rescue
objective mid-fight, so permadeath becomes something the player *plays
against* rather than something delivered by a roll after the fact. It is
also the fairest possible permadeath — you lost them because you
couldn't get there in time, and you knew that while it was happening. As
a side effect it retrofits genuine tactical tension into battles that
currently have none.

**Rescue requires a fielded squad of at least 4.** At two heroes, one
going down leaves a single hero who usually cannot cross the map, and
trying is a spiral rather than a decision. This makes the fielded-squad
increase a prerequisite for the attrition design, not a nice-to-have.

**The central risk of this whole system is rate.** The heroes fielded
most are the ones wounded most, which points attrition directly at the
heroes the player is most attached to. That is either the emotional core
working as designed or the thing that breaks it, depending entirely on
frequency and severity. The known failure mode in comparable games is
players defending themselves by refusing to get attached — treating the
roster as consumable, which is the exact inverse of this project's first
pillar. Wound frequency and malus severity must be independently
tunable, not controlled by a single knob.

---

## Two currencies

- **Money buys things:** recruitment, facilities, equipment, wound
  treatment. Paying to reduce a specific hero's wound is a particularly
  good sink, because it is a budget decision made about someone the
  player cares about.
- **Reputation buys access:** contract tiers, quality of the recruit
  pool, possibly unique heroes.

Keeping them distinct in kind — resource versus gate — stops the career
layer collapsing into one linear ratchet.

---

## Recruitment

If heroes leave, they must be replaced, and recruitment is where money,
reputation, and age intersect.

- **Age is the natural recruitment axis:** the cheap veteran who is
  strong now but retires soon versus the expensive prospect who isn't
  yet anything. This is FT&G's transfer market almost exactly.
- **The classless Tier 0 hero is already the youth intake.** A raw
  recruit arriving with four basic abilities and no specialisation is a
  system that already exists.
- Open: whether recruits arrive raw, experienced, or both, and whether
  the recruit pool's quality is reputation-gated.

---

## The three progression tracks

Each is fed by a different kind of play.

### Track 1 — Level & Attributes ("just showing up")

- Four attributes: **Might, Focus, Resolve, Agility.**
- Each hero has a **hidden affinity vector** across them, generated via
  a Dirichlet distribution and never revealed. It can be intuited from
  how a hero develops, but never shown.
- XP is awarded as a **per-battle pool** derived from enemy count and
  strength, split evenly among fielded heroes; benched heroes receive a
  separate bonus computed from a multiplier on the pool. Fielding fewer
  heroes concentrates growth — a deliberate risk/reward decision.
- On level-up a hero gains points distributed by affinity-weighted
  random draw, **except** for a small number the player allocates
  deterministically. That count is intended to rise with investment in
  training facilities, and can never reach the full per-level total —
  some growth always remains affinity-driven.

### Track 2 — Specialisation (usage-based identity)

- **Tier 0:** every hero starts classless with four basic abilities —
  melee strike, ranged physical shot, ranged spell bolt, heal — whose
  use accrues XP toward Fighter, Marksman, Caster and Healer
  respectively.
- **Tier 1:** crossing a threshold unlocks that archetype's perk tree, a
  growth lean, and typically an upgraded action.

  **Tier 1 is the admission ticket out of being classless, not the
  player's big choice.** A hero specialising broadly in line with their
  nature is the design working, not failing — it is the discovery pillar
  paying out. Design effort should not be spent trying to make Tier 1
  player-steerable.
- **Tier 2:** finer branches within an archetype, driven by specific
  in-battle behaviour rather than ability identity — Fighter splits to
  Vanguard (holding position, absorbing hits) or Duelist (killing blows,
  chains); Caster to Controller (landing CC) or Blaster (AoE/burst);
  similar splits for Marksman and Healer. **This is where genuine player
  agency over identity is intended to live.**

### Track 3 — Ability Training (deliberate investment)

- Abilities are trained over time — queued, completing after some number
  of battles, rushable with currency.
- Ability **levels change reliability, not just power**: level 1 is a
  single contested check, level 2 grants a second check on failure,
  level 3 improves further. Levelling an ability should make it feel
  *trustworthy* rather than merely bigger. This is the mechanic borrowed
  most directly from FT&G and is considered core identity.

**Track 3 has been deferred through every phase so far, and that should
change.** Under a persistent structure it is the mechanism that makes
development time genuinely scarce — you cannot train everything at once
— which is the tension replacing run-death. It is the choice engine, not
a flavour system.

---

## Multiclassing

Crossing into a second Tier 1 archetype is a deliberate, costed
decision. Reaching the threshold offers a choice; declining banks or
wastes the off-track XP with no penalty. Committing applies a menu of
tradeoffs, intended to be partly player-selected so multiclassing reads
as build flavour rather than a flat tax:

- Diluted or shared perk pool across both archetypes
- Slower ability training (fewer training slots)
- **Reduced manual attribute allocation** — one fewer manually
  allocatable point per level-up than the facility tier grants, so a
  multiclassed hero can never reach full manual allocation even at
  maximum investment

Diverging *within* one Tier 1 archetype is intended to be a softer,
automatic dilution rather than a commit-and-pay decision.

---

## Squad & roster

- **Target: 4 fielded heroes plus a bench**, drawn from a larger roster.
  Currently 2 fielded of a roster of 4.
- Fielded squad size 4 is a prerequisite for the rescue mechanic (see
  Attrition) and widens the "field fewer for concentrated XP" decision,
  which is currently thin.
- Bench time is how heroes recover from damage; recovery is gradual, and
  eventually instant via consumables.

---

## The tactical layer

### The problem

The battle layer currently presents an **arena**, and the mercenary
fiction wants something closer to XCOM or Battle Brothers. Two things
encode the arena, and the second matters more than it looks:

- **An open, symmetric 8x12 grid with no terrain.** This is a pitch —
  well suited to an athletic contest or a gladiator bout between two
  sides who agreed to meet here under known conditions.
- **A win condition of "reduce the enemy to zero HP."** This is the
  bigger offender. Mercenary work is escort, retrieval, holding a
  position until extraction, raiding and withdrawing. Fog of war laid
  over an elimination map is still an arena, only darker.

The tactical layer has not meaningfully deepened since Phase 1 while
three progression systems were built on top of it. That is a standing
risk in its own right — progression cannot rescue combat nobody wants to
replay — and the fiction shift makes it acute.

### Direction, in dependency order

**1. Objectives beyond elimination.** Does the most fiction work for the
least cost, and it defines what maps need to contain. Asymmetric setups,
entry and extraction points, reasons to leave a map rather than clear
it. Contract *types* in the career layer are defined by what battles can
express, so this comes first.

**2. Terrain and cover.** The prerequisite for everything below — fog on
an empty grid is just a radius circle. Terrain also does independent
work: it makes positioning matter, creates chokepoints, and is what
makes rescue a real question (can you reach them, or is there a wall in
the way?).

**3. Line of sight, then fog of war.** Approach tension, discovery, and
a genuine unknown. Also gives **Agility** a job — it has been tracked
since Phase 1 and still does nothing; vision range is the natural fit.

**4. Stealth — deferred, and the most expensive of the four.** Requires
detection states, alertness modelling, asymmetric line of sight, and
substantial AI rework; it also tends to want detection rolls, which
fights the deterministic resolution the project has kept clean. It is
the least necessary for the fiction — Battle Brothers has essentially
none and reads as mercenary work fine. Revisit only after fog is
working.

### Reconciling fog of war with the readability pillar

These two goals are in genuine conflict and the tension should be
resolved deliberately rather than discovered later. Into the Breach
readability means telegraphed intent and no hidden information; fog of
war is hidden information by definition.

**The resolution is a split by phase of engagement: uncertainty about
what has not been found, determinism once it has.** You do not know what
is behind the ridge. The moment an enemy is in view, its intent is fully
telegraphed and the fight is a solvable puzzle. This is roughly how
Battle Brothers reads in practice, it preserves the pillar where it
matters, and it buys approach tension without costing tactical
legibility.

### Costs to go in with eyes open

- **Pathfinding.** Terrain kills the greedy straight-line movement the
  AI currently uses, and the engine's reachability queries stop being
  trivial.
- **Map generation becomes a system**, not a constant — varied shapes,
  entry points, and objective placement. This is a larger lift than
  terrain itself.
- **AI rework** follows from both, plus objectives it must understand.

### Sequencing consequence

**The tactical rework should precede the career layer.** Contract types
depend on what battles can express, so designing contracts against arena
battles would either constrain them or force a redesign once maps gain
objectives. Building the career layer on top of arena combat would also
cement precisely the fiction the project is moving away from.

The natural shape of the next tactical phase is **terrain and cover,
objectives beyond elimination, a fielded squad of four, and the rescue
mechanic** — coherent as a unit because rescue depends on all three of
the others. Fog follows once line of sight exists.

---

## What the data has told us

Findings from played and simulated sessions that now constrain design
decisions. These are empirical, not speculative.

- **Class track was initially a pure function of attributes.** Across 18
  heroes who used a ranged ability, the track was Caster if Focus >
  Agility and Marksman otherwise, without exception. Track 2 carried no
  information Track 1 didn't already contain. Ability differentiation by
  range band, plus reduced attribute variance, brought predictability
  down to roughly 47–51%.
- **The single manual attribute point is not an identity lever.** In a
  paired-seed experiment, steering *against* nature produced
  predictability and track-flip rates identical to no steering at all.
  Steering *with* nature raised predictability modestly. Whether it acts
  as a power or versatility lever is unestablished — differences in win
  rate sat within noise once seeds were paired.
- **Why: the lever is dwarfed, not weak.** Over ten battles a hero ends
  with roughly 25 attribute points, of which about 2 are manual — the
  player controls around 8% of the final vector. Under a *persistent*
  structure this reinterprets favourably: a career supplies the runway a
  ten-battle session does not, and the mechanic should be re-measured
  over career-length timescales before being judged.
- **Realistic squad selection produces a 4:1 progression divide.**
  Fielding the strongest pair repeatedly yields roughly 3.4 level-ups
  for core heroes against 0.8 for relief. Under persistence this
  compounds rather than resetting, and needs a deliberate answer — it is
  either the roster-management pressure the design wants or a death
  spiral for anyone outside the starting two.
- **Heroes are legible too early.** Fifteen of a hero's nineteen
  starting attribute points come from synthesis, so a player can read
  their nature off the roster screen before they've fought once.
  Reducing the synthesis base would make nature emerge through play and
  simultaneously raise the relative weight of everything the player does
  afterward.

---

## Open questions

Discussed but deliberately unresolved:

- What a bad contract verdict actually costs
- Wound malus design — what kind of effect, and how severe
- Attrition rate tuning, the central risk of the whole design
- Whether recruits arrive raw, experienced, or both
- How opposition scales across a career now that flat difficulty is no
  longer defensible
- Grid size and shape once terrain and objectives exist — 8x12 was
  chosen for an open arena and should not be assumed to survive
- How maps are generated: hand-authored, procedural, or templated
- Whether stealth is ever worth its cost
- Whether hidden affinity stays permanently opaque or becomes indirectly
  reconstructable
- Balance numbers generally — treated as tunable, not yet meaningful

## Non-goals

- Multiplayer or shared state — single-player throughout
- Real-time or physics-driven combat

---

## Consequences for infrastructure

Two things previously deferred as "not needed yet" become mandatory
under a persistent structure, and phase docs should stop deferring them:

- **Save/load.** A career that evaporates on process exit is not a
  career.
- **Opposition scaling.** Flat enemy strength was defensible for a
  five-battle session; against heroes with dozens of level-ups it makes
  the back half of a career trivial.

---

## Relationship to phase documents

Each phase document should reference this document for *why* rather than
restating it, explicitly list what subset is in scope, explicitly list
deferred systems as out of scope so scope creep doesn't happen by
accident, and flag placeholder decisions in code as placeholders.
