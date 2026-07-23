# Phase 4a — Maps, Terrain & Squad Expansion

## Goal

Replace the open, featureless arena with real maps, and grow the fielded
squad to the design's target size.

This is the tactical infrastructure phase. It deliberately delivers less
*fiction* than Phase 4b will — the mission types and the rescue mechanic
that make a battle read as mercenary work are deferred — but it builds
the layer all of that sits on. Terrain, pathfinding and line of sight
are prerequisites for objectives, for rescue, and eventually for fog of
war; building them first means the AI is reworked once instead of twice.

One objective type (**extraction**) is included, not because the mission
design needs it yet, but to prove the shape of the objective system
against a real map before Phase 4b builds four more on top of it.

---

## Why this before the career layer

Per the vision doc: contract types in the career layer are defined by
what battles can express. Designing contracts against elimination-only
arena battles would either constrain them or force a redesign once maps
gain objectives — and building the career layer on top of arena combat
would cement exactly the fiction the project is moving away from.

---

## In Scope

### 1. Map model and terrain

A map becomes a first-class data structure rather than a bare width and
height.

Keep the terrain vocabulary deliberately small for this phase. Three
properties per tile, orthogonal to each other:

- **Passable / impassable** — can a unit enter this tile.
- **Blocks line of sight / doesn't** — independent of passability, so
  you get low walls (passable? no; sight-blocking? no) and thickets
  (passable? yes; sight-blocking? yes) without inventing a type
  taxonomy.
- **Cover** — **two tiers**. Cover modifies the defender's side of the
  contested roll introduced in Phase 3. The precise semantics of each
  tier are deliberately left to tuning; what this phase owes is that the
  data model carries two levels and that the resolution path reads them.

  Note that much of what "full cover" means in other games is already
  handled by sight-blocking — a target you cannot see is not harder to
  hit, it is untargetable. What cover expresses is the partial case:
  exposed, but harder to hurt.

Resist building a rich terrain type enum. Named types (wall, rubble,
water, forest) are presentation over these properties and can be added
later without touching engine logic.

**Grid dimensions become map properties, not global constants.** 8x12
was chosen for an open arena with two heroes a side; with four heroes
and terrain it is cramped. **Start at 16x16**, but treat that as a dial
rather than a decision — maps carry their own dimensions, and no engine
code may assume a fixed size. Expect to change it once terrain density
and objective placement are real.

### 2. Pathfinding

Movement is currently a greedy straight-line step toward a target, which
was correct when no obstacles existed. It is now wrong.

- Implement A* (or Dijkstra for the reachability set — computing all
  reachable tiles within move points in one pass is usually cheaper than
  repeated A*).
- The **reachable-destinations query** from Phase 2a's legal-action API
  is where this lands. Its signature should not need to change; only its
  implementation. If it does need to change, that is a signal the API
  boundary was drawn in the wrong place and is worth an ADR.
- `ai.decide_turn` consumes the query layer already, so the AI should
  inherit pathfinding without direct modification. Verify this rather
  than assuming it.

### 3. Line of sight

- Implement LOS between tiles (Bresenham or a symmetric variant —
  symmetry matters more than precision; an asymmetric LOS where A sees B
  but B does not see A produces confusing tactical situations).
- **Ranged abilities require LOS to their target.** This is what makes
  terrain matter rather than merely exist: cover creates safe
  approaches, chokepoints, and firing lanes.
- The **valid-targets query** enforces LOS. As with pathfinding, the AI
  should inherit this through the query layer.
- **This is not fog of war.** Unit visibility and hidden information are
  Phase 4c or later. LOS here governs what can be *shot*, not what can
  be *seen*. Keeping these separate matters: LOS is a targeting rule and
  is compatible with full information; fog is hidden information and
  needs the reconciliation described in the vision doc.

### 4. Map generation

- Maps are generated per battle, not hand-placed one at a time.
- **Pick whatever is simplest to build.** This subsystem is isolated
  behind map generation — nothing else in the engine cares how a map
  came to exist, only what it contains — so it can be replaced later
  without disturbing anything. Do not spend design effort here.
  Randomised obstacle scatter with fixed deployment zones is entirely
  acceptable for this phase; templated layouts are a reasonable
  alternative if they turn out to be no harder.
- Whatever is chosen, generation must guarantee **connectivity** —
  every deployment tile can reach every objective tile. A map that
  cannot be completed is a hard bug, and this needs a test that
  generates many maps and verifies reachability.

### 5. Fielded squad of four

- `FIELDED_SQUAD_SIZE` goes from 2 to 4; roster grows correspondingly.
  **Roster size was not decided — use 8 as a placeholder** and flag it
  in config as an open tuning question, since it directly controls how
  much bench rotation and recovery pressure exist.
- Enemy squad sizing scales accordingly, but **do not invest effort
  here**. Enemies are currently mirror images of heroes and are intended
  to become specifically engineered enemy types in a later phase, at
  which point squad size and composition become design decisions rather
  than symmetry. Match the fielded squad and move on.
- Note that 4v4 with terrain is a substantially different tactical
  problem from 2v2 in the open — expect existing difficulty tuning to be
  invalidated wholesale rather than merely shifted.

**Bench XP multiplier stays at 0.2.** It is worth knowing that this no
longer means what it meant: at roster 4 / fielded 2 it happened to yield
each benched hero exactly 20% of a fielded share, and at fielded 4 of a
roster of 6 the same constant yields roughly 40%. That drift is
accepted for now — a tuning pass on progression rates is deferred rather
than folded into this phase. Record the actual effective fraction in the
progress update so the later pass starts from a known number.

### 6. Extraction objective

One objective type only, as a proving ground for the system's shape:

- The map has one or more **extraction tiles**. A battle is won when all
  surviving fielded heroes have reached one, or by elimination as
  before — whichever the mission specifies.
- **The objective must be a data-driven mission parameter**, not a
  hardcoded battle mode. Phase 4b adds several more (hold a position,
  retrieve, escort, raid-and-withdraw), and they should slot into the
  same structure rather than each needing new branching in the battle
  loop.
- The AI needs minimal awareness — enough that enemies do not ignore a
  hero walking calmly to the exit. Simple is fine; sophistication is 4b.

This is the smallest objective that forces the battle loop to stop
assuming elimination, which is the point.

### 7. AI rework

The AI inherits pathfinding and LOS through the query layer, but needs
direct work for:

- **Cover awareness** — preferring positions with cover, or at least not
  actively stepping out of it.
- **Terrain-aware approach** — the greedy "move toward nearest enemy"
  fallback will walk into walls or take absurd routes without a
  path-aware version.
- **Minimal objective awareness** per item 6.

Keep the priority-list structure. This does not need to become a good
AI; it needs to stop being an obviously broken one on maps with walls.

### 8. Visualizer

- Render terrain (passability, sight-blocking, cover) legibly. Debug
  grade — coloured tiles with a legend is sufficient; no art.
- Handle four heroes a side without the sidebar overflowing, and handle
  maps larger than 8x12 (scroll, scale, or size the window to the map).
- Show LOS/reachability highlighting that accounts for terrain, so a
  human can see why a tile is unreachable or a target invalid.

### 9. Harness performance guardrail

The simulation harness has become central to how this project is
designed, and this phase makes each battle substantially more expensive
— more units, larger maps, pathfinding, LOS checks.

- **Benchmark the harness before and after**, and record both figures in
  the progress update.
- **Parallelise across seeds** (`multiprocessing`) if the post-change
  figure makes a 50-session sweep uncomfortable. Sessions are
  independent, so this is close to free and needs no architectural
  change.
- If a specific kernel dominates after parallelisation, profile before
  optimising. Pathfinding and the AI's non-mutating action preview
  (which scratch-copies heroes) are the two likely candidates.

A balance sweep that cannot be run overnight is a balance sweep that
stops being run.

---

## Explicitly Out of Scope

Deferred to **Phase 4b**: mission types beyond extraction, the rescue
mechanic, death, wounds, AI objective sophistication.

Deferred to **Phase 4c or later**: fog of war and unit visibility;
stealth, detection, and alertness.

Deferred to the **career layer (Phase 5+)**: age, retirement,
recruitment, money and reputation, the contract ladder, save/load
persistence.

Deferred indefinitely / unchanged:

- Tier 1 archetype unlocks, Tier 2 branches, multiclassing
- Track 3 ability training
- Contested-roll resolution — `rng` stays plumbed and unused
- Equipment, consumables, secondary resources
- Agility-driven initiative — turn order remains the Phase 1 placeholder
  (note: Agility gains a real job when fog arrives, via vision range;
  not this phase)
- New abilities beyond the four basics
- Elevation and multi-level maps

---

## Expected Consequences

**The AI baseline fixture will need regenerating, comprehensively.**
Terrain, pathfinding, LOS and squad size all change battle trajectories
by design. Apply the established discipline: diff before regenerating,
confirm every delta is attributable to an intended change, document it.
Given the scale of change here, consider whether the existing fixture is
still meaningful or whether a fresh baseline captured at the end of this
phase is more honest — and say which was chosen and why.

**All existing balance tuning is invalidated.** Enemy strength ramps,
XP pool sizing, recovery rates and the level threshold were tuned for
2v2 in the open. Expect to retune rather than adjust.

**ADRs are warranted** for the terrain property model and the LOS
algorithm choice if it is non-obvious. Map generation does not need one
unless the simple approach proves inadequate and something more
elaborate replaces it.

---

## Acceptance Criteria

1. Maps are first-class objects carrying their own dimensions and
   per-tile passability, sight-blocking and cover; no engine code
   assumes a fixed grid size.
2. Movement uses real pathfinding; the reachable-destinations query
   returns only genuinely reachable tiles, verified against constructed
   maps with walls, dead ends, and enclosed areas.
3. Ranged abilities require line of sight; the valid-targets query
   enforces it; LOS is symmetric, with a test asserting symmetry across
   randomly generated maps.
4. Maps are generated per battle, with a test that generates many maps
   and verifies every deployment tile can reach every objective tile.
5. Battles run 4v4 with a roster larger than the fielded squad; the
   effective benched-to-fielded XP fraction under the new squad ratio is
   measured and recorded, with the 0.2 constant left unchanged.
6. The extraction objective works as a data-driven mission parameter,
   and the battle loop no longer assumes elimination is the only win
   condition.
7. The AI plays competently enough on walled maps not to path into
   obstacles or ignore an extracting enemy; regression-tested across
   seeded battles on generated maps.
8. `models/` and `engine/` still contain zero `pygame`/`visualizer`
   imports; the visualizer computes no legality of its own.
9. The visualizer renders terrain, four heroes a side, and larger maps
   legibly, with terrain-aware reachability and target highlighting.
10. Harness runtime benchmarked before and after, with figures recorded;
    parallelisation applied if needed to keep a 50-session sweep
    practical.
11. `uv run ty check` passes cleanly; `uv run pytest` passes.

---

## Suggested Build Order

1. **Map model and terrain data structures.** Pure data, no behaviour.
   Includes map-carried dimensions.
2. **Pathfinding**, behind the existing reachable-destinations query.
   Headless, heavily testable against constructed maps.
3. **Line of sight**, behind the existing valid-targets query. Same.
4. **Map generation**, whatever is simplest, with the connectivity test.
5. **Squad size to four**, plus bench multiplier re-derivation and enemy
   sizing.
6. **Extraction objective** and the mission-parameter structure.
7. **AI rework** for cover, terrain-aware approach, and objectives.
8. **Visualizer** updates.
9. **Benchmark, parallelise if needed, retune balance, regenerate the
   fixture.**

Steps 1–4 are the load-bearing ones and are all headless and testable
without any UI. Step 9 will take longer than it looks — this phase
invalidates every balance number in `config.py`.

---

## What Phase 4b will cover

Recorded here so the seam is visible and 4a is not tempted to drift into
it:

- Mission types beyond extraction: hold a position, retrieve, escort,
  raid-and-withdraw
- The **rescue mechanic** — a downed hero becomes a rescue objective
  mid-battle, and dies if not reached in time
- **Wounds** — permanent, legible maluses inflicted by being downed
- AI sophisticated enough to play objectives rather than merely
  acknowledge them

4b is where a battle starts reading as mercenary work rather than a
fight on nicer terrain. It depends on essentially everything in 4a,
which is why the split falls here.
