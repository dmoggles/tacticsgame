# Progress Updates

## 2026-07-15 — Architecture Setup (`docs/01_architecture_setup.md`)

Scaffolded the project per the architecture doc. This doc has no formal
acceptance criteria list (it's the stable technical foundation, not a
gameplay phase), so "done" is measured against what it specifies:

- Initialized as a `uv`-managed project (`pyproject.toml`, `uv.lock`,
  `.python-version` pinned to 3.12) with a `src/tactics_game/` layout.
- Runtime dependency added: `pygame`. Dev dependencies added: `ty`, `pytest`.
- Directory layout created matching the doc exactly: `models/`, `engine/`,
  `visualizer/`, `config.py`, plus `tests/`. All files are currently empty
  stubs (no logic yet) — this milestone was structural only.
- Entry point wired as `src/tactics_game/__main__.py`, runnable via
  `uv run python -m tactics_game` (confirmed working, prints placeholder
  greeting). `pyproject.toml`'s `project.scripts` entry updated to match.
- Verified: `uv run ty check` passes cleanly; `uv run pytest` runs and
  correctly reports 0 tests collected (stub test files are empty).
- Committed as `7c18ed5`.

**Deviations from the doc:** none of substance. The doc's example commands
show `uv init tactics-game` creating a fresh subdirectory; since this repo
already existed with docs/CLAUDE.md in place, `uv init .` was used instead
to initialize in place, with `--package` added to get the `src/` layout
(plain `--app` alone produces a flat `main.py` layout, not `src/`).

**Deferred:** no actual game logic — models, engine, and visualizer are
empty files. That work starts with Phase 1 (`docs/02_phase1_definition.md`).
