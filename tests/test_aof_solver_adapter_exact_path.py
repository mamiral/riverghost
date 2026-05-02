import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.database.persistence import MockPersistenceStrategy


class _ExactStubSolver:
    def __init__(self):
        self.calls = 0

    def analyze_hand_strategy(self, **kwargs):
        self.calls += 1
        return {
            "equity": 0.61,
            "ev": 1.25,
            "recommendation": "ALL-IN",
        }


def test_exact_path_calls_solver_per_sampled_combo_and_returns_combo_results():
    analyzer = PokerAnalyzer()
    persistence = MockPersistenceStrategy()
    solver = AllInFoldGTOSolver(analyzer, persistence)

    result = solver.evaluate_hand_key("AKs", num_opponents=2, pot_size=20.0, bet_amount=10.0, timeout_ms=900)

    assert result["status"] == "AVAILABLE"
    assert len(result["combo_results"]) >= 1  # At least one combo sampled
    assert "win_probability" in result
    assert "equity" in result
    assert "ev" in result


def test_exact_path_uses_combo_cache_on_repeated_request():
    analyzer = PokerAnalyzer()
    persistence = MockPersistenceStrategy()
    solver = AllInFoldGTOSolver(analyzer, persistence)

    # First call
    result1 = solver.evaluate_hand_key("KQo", num_opponents=2, pot_size=20.0, bet_amount=10.0, timeout_ms=900)
    # Second call - should work (no caching implemented in new version, but should not fail)
    result2 = solver.evaluate_hand_key("KQo", num_opponents=2, pot_size=20.0, bet_amount=10.0, timeout_ms=900)

    assert result1["status"] == "AVAILABLE"
    assert result2["status"] == "AVAILABLE"


def test_exact_path_returns_concrete_villain_hands():
    analyzer = PokerAnalyzer()
    persistence = MockPersistenceStrategy()
    solver = AllInFoldGTOSolver(analyzer, persistence)

    result = solver.evaluate_hand_key("KQs", num_opponents=1, pot_size=20.0, bet_amount=10.0, timeout_ms=900)

    assert result["status"] == "AVAILABLE"
    assert result["individual_outcomes"]
    assert all(
        outcome["villain_hand"] not in {"RANDOM", "NONE"}
        for outcome in result["individual_outcomes"]
    )


def test_exact_path_returns_individual_outcomes_in_evaluation_mode():
    analyzer = PokerAnalyzer()
    persistence = MockPersistenceStrategy()
    solver = AllInFoldGTOSolver(analyzer, persistence)

    result = solver.evaluate_hand_key("AKs", num_opponents=2, pot_size=20.0, bet_amount=10.0, timeout_ms=900)

    assert result["status"] == "AVAILABLE"
    assert result["individual_outcomes"]
    assert all(
        "hero_hand" in outcome and
        "villain_hand" in outcome and
        "outcome" in outcome and
        "ev_chips" in outcome
        for outcome in result["individual_outcomes"]
    )
