from __future__ import annotations

import json

from tactics_game.dev_tools import FIXTURE_PATH, capture_baseline


def test_ai_vs_ai_behaviour_matches_committed_baseline_fixture() -> None:
    """Guards the committed Phase 3 expected-value AI baseline.

    A failure here means AI-vs-AI behaviour changed —
    either fix an unintended regression, or regenerate the fixture via
    `uv run python -m tactics_game.dev_tools` and document the intentional
    deviation in the progress update, per the phase doc.
    """
    committed = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert capture_baseline() == committed
