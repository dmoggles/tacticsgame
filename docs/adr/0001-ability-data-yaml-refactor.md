# 0001. Move ability data to YAML, with classes owning abilities and a multi-component effect model

## Status

Accepted

## Context

The four basic-kit abilities (Basic Strike/Shot/Bolt/Mend) had their data
spread across two places: `config.py` held each ability's flat base
value, range, min-range, cooldown, and scaling multiplier as individual
named constants, and `resolution.py` had one hand-written Python function
per ability applying near-identical `base + attribute * multiplier` math.
`progression.create_basic_kit()` hardcoded four `Ability(...)` calls
wiring it together. Adding or tuning an ability meant touching three
files and writing a function that was ~90% boilerplate — directly against
`docs/01_architecture_setup.md`'s stated intent that "ability definitions
should be modeled as data, not hardcoded per-hero methods... abilities
are conceptually closer to equipment than to fixed class methods."

Three problems surfaced during design, before implementation:

1. **Abilities may need more than one effect.** E.g. an attack with a
   secondary self-heal/recoil component. A single `base`/`scaling_
   attribute`/`multiplier` triple per ability can't express that.
2. **Ownership direction was backwards.** `Ability` carried `class_track:
   ClassTrack` — the ability declaring which class it belongs to. Classes
   should own/reference abilities, not the reverse, especially once Tier
   1 archetypes eventually get their own kits (`docs/00_project_vision.md`).
3. **Where this is headed.** Abilities will eventually scale with
   multiple attributes, then with gear stats once equipment exists, and
   damage/to-hit will move from fixed to semi-random (possibly opposed)
   rolls. None of that is in scope now — equipment doesn't exist, and
   contested-roll math is explicitly out of scope per the architecture
   doc until a phase document calls for it — but the *shape* of the data
   and the effect-invocation contract needed to not require a second
   breaking rewrite when that work starts, the same way `Ability.cost:
   int | None = None` was added ahead of any resource system specifically
   so resolution logic wouldn't assume "free action" in a way that had to
   be unwound later.

## Decision

- Ability mechanics moved to `src/tactics_game/data/abilities.yaml`
  (`pyyaml` runtime dep, `types-PyYAML` dev dep), loaded and validated by
  `engine/ability_library.py` (fail-fast `ValueError`s naming the ability
  id and the bad/missing field; module-level cache; `Ability` instances
  are frozen/stateless and shared across every hero rather than rebuilt
  per hero).
- Class ownership of abilities moved to a **separate** file,
  `src/tactics_game/data/class_tracks.yaml`, loaded by
  `engine/class_track_library.py`. It lists ability ids per track (the
  inverse of the old per-ability `class_track` field) and cross-validates
  every id against `ability_library` at load time — every ability must
  appear in exactly one track, every referenced id must exist. `Ability`
  no longer has a `class_track` field. The `ClassTrack` enum relocated
  from `models/ability.py` to `models/hero.py`, its only remaining
  natural owner (`Hero.class_xp: dict[ClassTrack, int]`).
- An ability's `effect` in YAML is a **list of components** (a bare
  mapping normalizes to a one-item list), each with `kind` (`damage` |
  `heal`), `base`, a **list** of `scaling` terms (`{attribute,
  multiplier}` — not a single attribute/multiplier pair), a `verb` for
  the log description, and `applies_to` (`target` | `caster`, default
  `target`). `resolution.py` replaced four hand-written functions with
  `ScalingTerm` + `EffectComponent` dataclasses and one generic
  `make_effect(components) -> AbilityEffect` combinator that sums
  multiple components/terms into a single `ResolutionResult`.
- `AbilityEffect`'s signature gained an `rng: random.Random` parameter,
  unused by any effect this phase (resolution stays fully deterministic).
  `Battle` already owns `rng: random.Random`, so every real call site
  threads it through for free; `ai.py`'s non-mutating preview
  (`_preview_magnitude`) passes its own throwaway `random.Random()`.
- Fixed a bug this design surfaced: `_preview_magnitude` previously only
  scratch-copied `target`, assuming effects never mutate `caster` — false
  once a component can have `applies_to: caster`. It now copies both
  sides, so evaluating an option never actually applies it.

## Consequences

**Positive**

- Adding or tuning a basic-kit ability is now a data-file edit, not a
  code change across three files.
- `Ability` is pure mechanics; the class/progression system (which
  conceptually owns Track 2 categorization) owns the class-to-ability
  association, matching the direction the vision doc already implies for
  Tier 1 archetypes.
- The schema already supports multi-attribute scaling and multi-effect
  abilities (e.g. damage + self-heal) with zero further schema changes.
- `AbilityEffect`'s invocation contract (`(caster, target, rng) ->
  ResolutionResult`) shouldn't need to change again when semi-random or
  contested-roll resolution is implemented — `target` is already fully
  available for opposed-roll math, and `rng` is already threaded to every
  call site.

**Negative / trade-offs**

- New runtime dependency (`pyyaml`) and dev dependency (`types-PyYAML`).
- More indirection than the old one-function-per-ability code: effect
  closures are now built at load time from declarative components rather
  than being directly readable Python. Mitigated by keeping `resolution.
  make_effect` small and by `tests/test_resolution.py` exercising the
  combinator directly (single-term, multi-term, and multi-component
  cases).
- YAML has no compile-time type safety — malformed data only surfaces at
  load time. Mitigated by fail-fast validation with specific error
  messages (ability id + field name) and dedicated loader tests
  (`tests/test_ability_library.py`, `tests/test_class_track_library.py`)
  covering missing/invalid fields.

**Explicitly deferred (not built now)**

- No gear/equipment scaling — `ScalingTerm` has a `# TODO(phaseN+):` for
  a future `source` field rather than a new `gear` field added
  speculatively now.
- No actual random/contested rolls — `rng` is plumbed but unused; what
  "preview" should mean once real rolls exist (expected value vs. a
  sampled roll) is left as a `# TODO(phaseN+):` in `ai.py`.
- No multi-target/AoE support — multiple effect *components* still apply
  only to the ability's existing (caster, target) pair, not to several
  different enemies at once. That would need a different targeting model
  in `ai.py` and is out of scope here.

## Alternatives considered

- **Single `scaling_attribute` + `scaling_multiplier` fields per
  component**, instead of a `scaling: [...]` list — rejected, doesn't
  support the stated future need for abilities scaling off multiple
  attributes.
- **Keep `class_track` on `Ability`** — rejected as backwards ownership;
  see Context.
- **One combined `abilities.yaml`** with both ability mechanics and the
  class-track mapping — rejected in favor of two files, since they're
  different concerns (mechanics vs. progression bookkeeping) and the
  class file references the ability file's ids rather than the reverse.
- **`functools.partial` instead of closures** for building each
  `Ability.effect` from its component data — rejected; a nested function
  with the exact `AbilityEffect` signature is unambiguous for `ty`,
  whereas `partial`'s typing against a `Callable[...]` alias is less
  reliably inferred across type checkers.
