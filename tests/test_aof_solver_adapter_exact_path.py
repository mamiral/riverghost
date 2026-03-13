import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_solver_adapter import AoFSolverAdapter, SolverRuntimeConfig


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
    adapter = AoFSolverAdapter(runtime=SolverRuntimeConfig(num_simulations=120, combo_samples=3, timeout_ms=900, seed=42))
    stub = _ExactStubSolver()
    adapter.solver = stub

    result = adapter.evaluate_hand_key("AKs", num_opponents=2, pot_size=20.0, bet_amount=10.0, timeout_ms=900)

    assert result["status"] == "AVAILABLE"
    assert len(result["combo_results"]) == 3
    assert stub.calls == 3


def test_exact_path_uses_combo_cache_on_repeated_request():
    adapter = AoFSolverAdapter(runtime=SolverRuntimeConfig(num_simulations=120, combo_samples=3, timeout_ms=900, seed=42))
    stub = _ExactStubSolver()
    adapter.solver = stub

    adapter.evaluate_hand_key("KQo", num_opponents=2, pot_size=20.0, bet_amount=10.0, timeout_ms=900)
    first_calls = stub.calls
    adapter.evaluate_hand_key("KQo", num_opponents=2, pot_size=20.0, bet_amount=10.0, timeout_ms=900)

    assert first_calls == stub.calls
