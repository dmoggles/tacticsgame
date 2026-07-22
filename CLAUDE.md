# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Phase 1 (`docs/02_phase1_definition.md`) is implemented and scaffolded per `docs/01_architecture_setup.md` — `pyproject.toml`, `src/tactics_game/`, and `tests/` all exist and are the current source of truth, not just a target layout. See `docs/progress_update.md` for what's shipped against each phase's acceptance criteria, and `docs/adr/` for why specific designs were chosen (see "Architecture Decision Records" below) — both are more reliable than re-deriving intent from scratch.

Read all three project docs before making design decisions — they are the actual spec, not background reading:

- `docs/00_project_vision.md` — full design intent ("why" and "eventually what"). Describes many systems that are **not** in scope yet (multiclassing, tier unlocks, perk trees, equipment, ability training). Useful for understanding the direction of a decision, but never a build spec for the current phase.
- `docs/01_architecture_setup.md` — tech stack, directory layout, and hard coding conventions. Stable across phases.
- `docs/02_phase1_definition.md` — what is actually in scope to build *right now*, plus an explicit out-of-scope list and acceptance criteria.

When a phase document and the vision doc conflict on what to build today, **the phase document wins**. Future phase docs will be added as `03_...`, `04_...`, etc.; check for the highest-numbered phase doc to find current scope.

## Agent instructions

At the conclusion of every phase (i.e. when a phase document's acceptance criteria are met), document exactly what was accomplished in `docs/progress_update.md` at the repo root — which acceptance criteria were met, any deviations from the phase doc, and what was deliberately deferred. Append a new dated section per phase rather than overwriting prior entries.

### Architecture Decision Records

Whenever you make (or are asked to make) a **non-trivial architectural or design decision** — a refactor that changes how a subsystem is structured, a reversal or bend of an existing convention documented here or in `docs/`, introducing a new dependency, or resolving a real design fork with named alternatives — write an ADR to `docs/adr/NNNN-short-title.md` (four-digit sequential number, lowercase-kebab title). This is separate from `docs/progress_update.md`: progress updates log *what shipped against a phase's acceptance criteria*; ADRs record *why a specific design was chosen over its alternatives*, for whoever (human or agent) next needs to understand or revisit the decision.

- Use the standard sections: **Status** (Accepted, unless told otherwise), **Context** (the problem/tension that forced a decision), **Decision** (what was actually built, concretely — file/module names, not vague prose), **Consequences** (positive, negative/trade-offs, and anything explicitly deferred), **Alternatives considered** (named, with a one-line reason each was rejected).
- ADRs are **persistent and append-only**: never edit or delete a prior ADR to reflect a later change. If a later decision supersedes one, add a new ADR and edit the old one's Status line to `Superseded by ADR-000X` — the historical reasoning stays intact.
- Not every change needs one — a bug fix, a config tweak, or a straightforward feature addition that doesn't involve a real design fork doesn't warrant an ADR. When in doubt, ask: "if someone reads only this file six months from now, will they be confused about why this is shaped the way it is?" If yes, write the ADR.

## Commands

Once the project is scaffolded per `docs/01_architecture_setup.md`, this project uses `uv` exclusively (not pip/poetry/conda) and `ty` for type checking (not mypy):

```bash
uv add <package>              # add a runtime dependency
uv add --dev <package>        # add a dev dependency
uv run python -m tactics_game # run the game
uv run ty check               # type check — must pass cleanly, treat as a build error
uv run pytest                 # run tests
uv run pytest tests/test_progression.py::test_name  # run a single test
```

`uv.lock` is committed. Never hand-edit dependency sections of `pyproject.toml` — use `uv add`/`uv remove`.

## Architecture

This is a turn-based, grid-based hero-tactics game (Into the Breach-style positioning) with a three-track hero progression system inspired by *Football, Tactics & Glory*: Track 1 (level & attributes, weighted-random growth via hidden per-hero affinity), Track 2 (usage-based specialization), Track 3 (deliberate ability training, future). Phase 1 only implements Track 1 fully, with Track 2 accruing silently.

### Hard separation: engine vs. rendering

The single most important structural rule in this codebase:

**`models/` and `engine/` must never import `pygame` or anything from `visualizer/`.** The game must be fully playable and testable headlessly (via `pytest`, or a script that runs a battle and returns results) with zero rendering involved. `visualizer/` is a one-directional, read-only consumer of engine state — it reads engine state, it never mutates it. If the visualizer needs data the engine doesn't expose, add a read method to the engine rather than reaching into internals.

This matters because gameplay logic will be iterated on far more frequently than rendering.

### Directory layout (per architecture doc)

```
src/tactics_game/
├── models/     # pure data types, no logic (Attributes, Hero, Ability, Grid)
├── engine/     # game rules & state mutation, no rendering
│   ├── battle.py
│   ├── turn_order.py
│   ├── ai.py                    # swappable enemy decision strategy
│   ├── progression.py           # XP, leveling, hidden affinity, class-XP
│   ├── resolution.py            # generic ability effect math
│   ├── ability_library.py       # loads/validates data/abilities.yaml
│   └── class_track_library.py   # loads/validates data/class_tracks.yaml
├── data/       # ability & class-track data (YAML) — see docs/adr/0001-...
├── visualizer/ # pygame rendering only, reads engine state
└── config.py   # all tunable constants (ability-specific data now lives
                 # in data/ instead — see docs/adr/0001-...)
```

### Coding conventions

- `dataclasses` for all model types; `frozen=True` for value objects (e.g. `Attributes`), mutable only where state genuinely changes turn-to-turn (e.g. `Hero.current_hp`, `Hero.position`).
- Type-hint everything; the project must pass `ty check` cleanly at all times.
- **No magic numbers in logic code.** Any tunable value (movement range, XP thresholds, grid size, level-up point totals, etc.) lives in `config.py` as a named constant, even as a placeholder.
- Abilities are **data, not hardcoded per-hero methods** — a `Hero` holds ability *instances* in 4 fixed slots; it does not define its own attack methods. Ability mechanics live in `data/abilities.yaml` (loaded via `engine/ability_library.py`), not as one Python function per ability — see `docs/adr/0001-ability-data-yaml-refactor.md`. Each ability's effect is a function/strategy `(caster: Hero, target: Hero, rng: random.Random) -> ResolutionResult` (`rng` is currently unused — plumbed ahead of semi-random/contested resolution) so the resolution math inside can change without restructuring how abilities are invoked.
- Ability `cost` is an optional field (`int | None = None`) even with no resource system implemented yet — don't let resolution logic assume "free action" in a way that has to be unwound later.
- Squad size is a config value, not hardcoded — engine layer must not assume exactly 2 heroes per side even though Phase 1 uses 2 (target end state is 4 active + bench).
- Hidden affinity vectors (Dirichlet-distributed weights over the four attributes) must never appear in player-facing output — dev/test logging of them for verification is fine and expected, but keep it clearly separated from anything player-facing.
- Don't build systems ahead of the current phase (specialization tier unlocks, multiclassing, perk trees, equipment, contested-roll math, etc.). If something seems like it should exist for completeness, leave a `# TODO(phaseN): ...` comment instead of implementing it.
