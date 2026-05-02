import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_solver_adapter import AoFSolverAdapter


def test_resolve_num_opponents_all_in_hero_only():
    adapter = AoFSolverAdapter()

    num_opp = adapter.resolve_num_opponents("ALL_IN", {"BTN": "ALL_IN"})
    assert num_opp == 0


def test_resolve_num_opponents_fold_context():
    adapter = AoFSolverAdapter()

    num_opp = adapter.resolve_num_opponents("FOLD", {"BTN": "ALL_IN", "BB": "ALL_IN"})
    assert num_opp == 2
