# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**No code exists yet.** This repository currently contains only design/planning docs under `docs/`. There is no `pyproject.toml`, no `src/`, no tests. The first implementation work should follow the environment setup and directory layout in `docs/01_architecture_setup.md` exactly rather than improvising a structure.

Read all three docs before writing code — they are the actual spec, not background reading:

- `docs/00_project_vision.md` — full design intent ("why" and "eventually what"). Describes many systems that are **not** in scope yet (multiclassing, tier unlocks, perk trees, equipment, ability training). Useful for understanding the direction of a decision, but never a build spec for the current phase.
- `docs/01_architecture_setup.md` — tech stack, directory layout, and hard coding conventions. Stable across phases.
- `docs/02_phase1_definition.md` — what is actually in scope to build *right now*, plus an explicit out-of-scope list and acceptance criteria.

When a phase document and the vision doc conflict on what to build today, **the phase document wins**. Future phase docs will be added as `03_...`, `04_...`, etc.; check for the highest-numbered phase doc to find current scope.

## Agent instructions

At the conclusion of every phase (i.e. when a phase document's acceptance criteria are met), document exactly what was accomplished in `docs/progress_update.md` at the repo root — which acceptance criteria were met, any deviations from the phase doc, and what was deliberately deferred. Append a new dated section per phase rather than overwriting prior entries.

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
│   ├── ai.py            # swappable enemy decision strategy
│   ├── progression.py   # XP, leveling, hidden affinity
│   └── resolution.py    # ability effect resolution
├── visualizer/ # pygame rendering only, reads engine state
└── config.py   # all tunable constants
```

### Coding conventions

- `dataclasses` for all model types; `frozen=True` for value objects (e.g. `Attributes`), mutable only where state genuinely changes turn-to-turn (e.g. `Hero.current_hp`, `Hero.position`).
- Type-hint everything; the project must pass `ty check` cleanly at all times.
- **No magic numbers in logic code.** Any tunable value (movement range, XP thresholds, grid size, level-up point totals, etc.) lives in `config.py` as a named constant, even as a placeholder.
- Abilities are **data, not hardcoded per-hero methods** — a `Hero` holds ability *instances* in 4 fixed slots; it does not define its own attack methods. Model each ability's effect as a function/strategy `(caster: Hero, target: Hero) -> ResolutionResult` so flat placeholder math can later be swapped for attribute-scaled or contested-roll math without restructuring how abilities are invoked.
- Ability `cost` is an optional field (`int | None = None`) even with no resource system implemented yet — don't let resolution logic assume "free action" in a way that has to be unwound later.
- Squad size is a config value, not hardcoded — engine layer must not assume exactly 2 heroes per side even though Phase 1 uses 2 (target end state is 4 active + bench).
- Hidden affinity vectors (Dirichlet-distributed weights over the four attributes) must never appear in player-facing output — dev/test logging of them for verification is fine and expected, but keep it clearly separated from anything player-facing.
- Don't build systems ahead of the current phase (specialization tier unlocks, multiclassing, perk trees, equipment, contested-roll math, etc.). If something seems like it should exist for completeness, leave a `# TODO(phaseN): ...` comment instead of implementing it.
