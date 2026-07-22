# Project Architecture & Dev Environment Setup

## Overview

This is a turn-based hero-tactics game with squad management and a
three-track hero progression system (level/attributes, specialization,
ability training). This document defines the project's technical
foundation — package management, type checking, directory layout, and
core coding conventions — independent of any specific gameplay phase.

Read this document fully before writing any code. Gameplay scope for
the current phase lives in a separate phase-definition document.

---

## Tech Stack

- **Language:** Python (3.12+)
- **Package manager:** [`uv`](https://docs.astral.sh/uv/) — used for
  all dependency management, virtual env creation, and running scripts.
  Do not use pip/poetry/conda directly.
- **Type checker:** [`ty`](https://github.com/astral-sh/ty) — the
  project must pass `ty check` cleanly at all times. Treat type errors
  as build errors, not warnings.
- **Rendering (debug visualizer only):** `pygame` — used strictly as a
  passive state renderer during this phase (see below). Not a general
  UI framework at this stage.
- **Testing:** `pytest`

---

## Environment Setup

```bash
# Initialize the project (if not already done)
uv init tactics-game
cd tactics-game

# Add runtime dependencies
uv add pygame

# Add dev dependencies
uv add --dev ty pytest

# Run the project
uv run python -m tactics_game

# Run type checking
uv run ty check

# Run tests
uv run pytest
```

`uv.lock` should be committed. Do not hand-edit `pyproject.toml`
dependency sections outside of `uv add`/`uv remove`.

---

## Directory Structure

```
tactics-game/
├── pyproject.toml
├── uv.lock
├── src/
│   └── tactics_game/
│       ├── __init__.py
│       ├── __main__.py          # entry point
│       ├── models/              # pure data types, no logic
│       │   ├── __init__.py
│       │   ├── attributes.py
│       │   ├── hero.py
│       │   ├── ability.py
│       │   └── grid.py
│       ├── engine/               # game rules & state mutation, no rendering
│       │   ├── __init__.py
│       │   ├── battle.py
│       │   ├── turn_order.py
│       │   ├── ai.py
│       │   ├── progression.py    # XP, leveling, hidden affinity
│       │   └── resolution.py     # ability effect resolution
│       ├── visualizer/           # pygame rendering only, reads engine state
│       │   ├── __init__.py
│       │   └── renderer.py
│       └── config.py             # tunable constants, see below
└── tests/
    ├── test_progression.py
    ├── test_battle.py
    └── test_resolution.py
```

### Hard separation rule

**`models/` and `engine/` must never import `pygame` or anything from
`visualizer/`.** The game must be fully playable/testable headlessly
(via `pytest`, or a script that runs a battle and prints/returns
results) with zero rendering code involved. `visualizer/` is a
one-directional consumer of engine state — it reads, it never mutates.

This matters because gameplay logic will be iterated on far more
frequently and by more agent sessions than rendering will, and it must
be independently testable without a display/event loop involved.

---

## Coding Conventions

- **Use `dataclasses`** (or `attrs` if a clear need arises — default to
  stdlib `dataclasses`) for all model types. Prefer immutability
  (`frozen=True`) for value objects like `Attributes`, and mutability
  only where state genuinely changes turn-to-turn (e.g. `Hero.current_hp`,
  `Hero.position`).
- **Type-hint everything.** No untyped function signatures, no bare
  `dict`/`list` without generics. This project passing `ty check`
  cleanly is a hard requirement, not a nice-to-have.
- **No magic numbers in logic code.** Any tunable value (movement
  range, level-up point totals, XP thresholds, grid size, etc.) lives
  in `config.py` as a named constant, even if it's currently a
  placeholder. Future phases will tune these frequently — they should
  never be buried inline.
- **Design for future extensibility, but do not build unused
  scaffolding.** Concretely for this project:
  - Ability definitions should be modeled as **data**, not
    hardcoded per-hero methods — abilities are conceptually closer to
    equipment than to fixed class methods, since they are expected to
    evolve/scale/swap in future phases. A `Hero` holds a list of ability
    *instances* in 4 fixed slots; it does not define its own attack
    methods.
  - Ability cost should be an **optional** field on the ability data
    model (e.g. `cost: int | None = None`) even though no secondary
    resource (energy/mana) is implemented yet. This avoids assuming
    "free action" in the resolution logic in a way that would need to be
    unwound later.
  - Squad size should be a **config value**, not a hardcoded `2`,
    even though the current phase uses 2 heroes per side — the intended
    end state is 4 active + bench.
- **No premature systems.** Do not implement specialization tier
  unlocks, multiclassing, perk trees, equipment, or contested-roll
  math unless the current phase document explicitly calls for it. If
  something seems like it "should" be there for completeness, leave a
  `# TODO(phaseN):` comment instead of building it.

---

## What This Document Does NOT Cover

Gameplay scope, systems to build, and acceptance criteria for the
current milestone live in the phase definition document. This
document should remain stable across phases; phase documents will be
added incrementally as the project progresses.
