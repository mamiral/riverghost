from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.logging_config import get_logger
from hopilot.poker_analyzer import PokerAnalyzer


@dataclass
class SolverRuntimeConfig:
    num_simulations: int = 120
    combo_samples: int = 4
    timeout_ms: int = 900
    seed: int = 42


class AoFSolverAdapter:
    """Adapter that provides exact combo simulation on cache miss for AoF browser cells."""

    def __init__(self, runtime: SolverRuntimeConfig | None = None):
        self.logger = get_logger(__name__)
        self.runtime = runtime or SolverRuntimeConfig()
        self.analyzer = PokerAnalyzer()
        self.solver = AllInFoldGTOSolver(self.analyzer)
        self._combo_eval_cache: dict[tuple[Any, ...], dict[str, Any]] = {}

    def evaluate_hand_key(
        self,
        hand_key: str,
        num_opponents: int,
        pot_size: float,
        bet_amount: float,
        timeout_ms: int | None = None,
    ) -> dict[str, Any]:
        """Evaluate a shorthand hand by simulating sampled concrete combos."""
        timeout_limit = (timeout_ms or self.runtime.timeout_ms) / 1000.0
        start = time.perf_counter()
        if not hand_key:
            return {"status": "MISSING", "reason": "NO_HAND_KEY", "value": None}
        if timeout_limit <= 0:
            return {"status": "TIMEOUT", "reason": "INVALID_TIMEOUT", "value": None}

        combos = self._expand_hand_key_to_combos(hand_key)
        if not combos:
            return {
                "status": "MISSING",
                "reason": "NO_VALID_COMBOS",
                "value": None,
                "combo_results": [],
            }

        combo_results: list[dict[str, Any]] = []
        for idx, combo in enumerate(combos):
            if time.perf_counter() - start > timeout_limit:
                return {
                    "status": "TIMEOUT",
                    "reason": "TIME_BUDGET_EXCEEDED",
                    "value": None,
                    "combo_results": combo_results,
                }
            score = self._evaluate_combo(
                hand_key=hand_key,
                combo=combo,
                combo_index=idx,
                num_opponents=num_opponents,
                pot_size=pot_size,
                bet_amount=bet_amount,
                timeout_ms=timeout_ms,
            )
            combo_results.append(score)

        valid = [r for r in combo_results if r.get("is_valid", True)]
        if not valid:
            return {
                "status": "MISSING",
                "reason": "NO_VALID_COMBOS",
                "value": None,
                "combo_results": combo_results,
            }

        win_prob = sum(float(r["win_probability"]) for r in valid) / len(valid)
        equity = sum(float(r["equity"]) for r in valid) / len(valid)
        ev = sum(float(r["ev"]) for r in valid) / len(valid)

        return {
            "status": "AVAILABLE",
            "win_probability": round(win_prob, 4),
            "equity": round(equity, 4),
            "ev": round(ev, 4),
            "source": "solver",
            "sampled_combos": len(combos),
            "combo_results": combo_results,
        }

    def resolve_num_opponents(
        self,
        selected_action: str,
        position_actions: dict[str, str],
    ) -> int:
        active_players = sum(1 for action in position_actions.values() if action == "ALL_IN")
        if selected_action == "ALL_IN":
            return max(1, active_players - 1)
        return max(1, active_players)

    def _expand_hand_key_to_combos(self, hand_key: str) -> list[tuple[str, str]]:
        # Deterministic combo sampler; exact eval runs on these sampled concrete combos.
        if len(hand_key) < 2:
            return []

        ranks = "AKQJT98765432"
        r1 = hand_key[0]
        r2 = hand_key[1]
        if r1 not in ranks or r2 not in ranks:
            return []

        max_samples = max(1, int(self.runtime.combo_samples))
        if len(hand_key) == 2:
            if r1 != r2:
                return []
            base = [(f"{r1}s", f"{r2}h"), (f"{r1}d", f"{r2}c"), (f"{r1}h", f"{r2}d")]
            return base[:max_samples]

        if len(hand_key) == 3 and hand_key[2] in ("s", "o"):
            suited = hand_key[2] == "s"
            if suited and r1 == r2:
                return []
            if suited:
                base = [(f"{r1}s", f"{r2}s"), (f"{r1}h", f"{r2}h"), (f"{r1}d", f"{r2}d")]
            else:
                base = [(f"{r1}s", f"{r2}h"), (f"{r1}d", f"{r2}c"), (f"{r1}h", f"{r2}d")]
            return base[:max_samples]

        return []

    def _evaluate_combo(
        self,
        hand_key: str,
        combo: tuple[str, str],
        combo_index: int,
        num_opponents: int,
        pot_size: float,
        bet_amount: float,
        timeout_ms: int | None,
    ) -> dict[str, Any]:
        cache_key = (
            combo,
            int(num_opponents),
            float(pot_size),
            float(bet_amount),
            max(100, int(self.runtime.num_simulations)),
        )
        cached = self._combo_eval_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            result = self.solver.analyze_hand_strategy(
                hole_cards=[combo[0], combo[1]],
                num_opponents=max(1, int(num_opponents)),
                pot_size=float(pot_size),
                bet_amount=float(bet_amount),
                num_simulations=max(100, int(self.runtime.num_simulations)),
            )
        except Exception as exc:
            self.logger.warning("AoF combo solve failed for %s (%s): %s", hand_key, combo, exc)
            return {"combo": combo, "is_valid": False, "invalid_reason": "solver_exception"}

        if not result or "equity" not in result or "ev" not in result:
            return {"combo": combo, "is_valid": False, "invalid_reason": "missing_solver_fields"}

        equity = float(result["equity"])
        ev = float(result["ev"])
        # Solver output is win-rate based in this module; keep mapping explicit.
        win_prob = equity

        if timeout_ms is not None and timeout_ms <= 0:
            return {"combo": combo, "is_valid": False, "invalid_reason": "timeout"}

        score = {
            "combo": combo,
            "is_valid": True,
            "win_probability": round(max(0.0, min(1.0, win_prob)), 4),
            "equity": round(max(0.0, min(1.0, equity)), 4),
            "ev": round(ev, 4),
        }
        self._combo_eval_cache[cache_key] = score
        return score

    @staticmethod
    def _hand_strength_score(hand_key: str) -> float:
        ranks = "AKQJT98765432"
        rank_value = {r: 12 - i for i, r in enumerate(ranks)}

        if len(hand_key) < 2:
            return 0.1
        r1 = hand_key[0]
        r2 = hand_key[1]
        if r1 not in rank_value or r2 not in rank_value:
            return 0.1

        base = (rank_value[r1] + rank_value[r2]) / 24.0
        is_pair = len(hand_key) == 2 and r1 == r2
        suited = hand_key.endswith("s")

        if is_pair:
            base += 0.22
        elif suited:
            base += 0.08
        else:
            base -= 0.03

        gap = abs(rank_value[r1] - rank_value[r2])
        base -= min(0.12, gap * 0.01)
        return max(0.05, min(0.99, base))
