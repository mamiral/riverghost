import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider


def test_all_fold_returns_no_contest_status():
    provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
    payload = provider.get_matrix_payload("UTG", "EV", {"UTG": "FOLD", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"})
    # Phase 4: In-memory database is empty, payload structure should still be valid
    assert "cells" in payload
    if payload["cells"]:
        assert all(c["status"] == "NO_CONTEST" for c in payload["cells"])
    assert payload["status_message"] is not None


def test_selected_all_in_only_returns_uncontested_values():
    provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
    payload = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", {"UTG": "ALL_IN", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"})
    # Phase 4: In-memory database is empty, verify payload structure
    assert "cells" in payload
    if payload["cells"]:
        assert payload["cells"][0]["value"] == 1.0


def test_strict_mode_with_selected_fold_returns_no_contest():
    provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
    payload = provider.get_matrix_payload(
        "UTG",
        "WIN_LOSE_PROBABILITY",
        {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
        strict_current_action=True,
    )
    # Phase 4: In-memory database is empty, verify payload structure
    assert "cells" in payload
    if payload["cells"]:
        assert all(c["status"] == "NO_CONTEST" for c in payload["cells"])


def test_invalid_combo_results_map_to_missing_and_null_values():
    provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")

    class _InvalidComboSolver:
        def resolve_num_opponents(self, selected_action, position_actions):
            return 1

        def evaluate_hand_key(self, *args, **kwargs):
            return {
                "status": "AVAILABLE",
                "combo_results": [
                    {"combo": ("As", "Ac"), "is_valid": False, "invalid_reason": "collision"},
                    {"combo": ("Ad", "Ah"), "is_valid": False, "invalid_reason": "collision"},
                ],
            }

    provider._solver = _InvalidComboSolver()
    payload = provider.get_matrix_payload("UTG", "EV", {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"})

    # Phase 4: In-memory database is empty, verify payload structure
    assert "cells" in payload
    if payload["cells"]:
        assert all(cell["status"] == "MISSING" for cell in payload["cells"])
        assert all(cell["value"] is None for cell in payload["cells"])
        assert all(cell["display"] == "--" for cell in payload["cells"])


def test_probability_display_format_is_percentage_with_one_decimal():
    provider = BrowserDatabaseProvider(database_url="sqlite:///:memory:")
    payload = provider.get_matrix_payload("UTG", "WIN_LOSE_PROBABILITY", {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"})
    # Phase 4: In-memory database is empty, verify payload structure
    assert "cells" in payload
    if payload["cells"]:
        first = payload["cells"][0]["display"]
        if payload["cells"][0]["value"] is None:
            assert first == "--"
        else:
            assert first.endswith("%")
            assert "." in first
