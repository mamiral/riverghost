"""
Phase 4: Minimal database-only browser data provider.

Replacement for AoFBrowserDataProvider after cache infrastructure removed.
Provides matrix data access via SQLAlchemy ORM (database only).
No cache, no aggregation, no solver modes.

CREATED IN: Phase 4 cleanup (replaces deleted AoFBrowserDataProvider)
"""

import asyncio
from typing import Any, Dict, List, Optional
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.data_model import PositionContext, ActionContext, MetricType
from hopilot.gto.aof_browser_state import POSITIONS, normalize_position_actions, METRICS, build_browser_context
from hopilot.gto.aof_hand_matrix import build_matrix_keys, format_metric_value
from hopilot.logging_config import get_logger

STATUS_AVAILABLE = "AVAILABLE"
STATUS_MISSING = "MISSING"
STATUS_NO_CONTEST = "NO_CONTEST"


class BrowserDatabaseProvider:
    """
    Minimal provider for GUI matrix queries against database.
    
    Provides context building and database queries only.
    All cache infrastructure removed in Phase 4.
    """

    def __init__(self, database_url: str):
        """Initialize with database connection only."""
        self.logger = get_logger(__name__)
        self.database_url = database_url
        self.database_repository = DatabaseRepository(database_url=database_url)
        self._matrix_keys = build_matrix_keys()
        
        self.logger.info(f"BrowserDatabaseProvider initialized with database: {database_url}")

    def _resolve_num_opponents(self, action: str, position_actions: Dict[str, str]) -> int:
        """Resolve the number of opponents based on action and position actions."""
        # Count active positions (not folded)
        active_positions = [pos for pos, act in position_actions.items() if act != "FOLD"]
        # Subtract 1 for hero
        return max(0, len(active_positions) - 1)

    def _baseline_equity(self, hand_key: str) -> float:
        """Get baseline equity for a hand key (simplified)."""
        # This is a simplified baseline - in a real implementation this would be more sophisticated
        return 0.5

    def _is_no_contest_scenario(self, position: str, position_actions: Dict[str, str], strict_current_action: bool) -> bool:
        """
        Check if this is a no-contest scenario where the player automatically wins or loses.
        
        NO_CONTEST occurs when:
        1. All other players fold (uncontested pot)
        2. Current player folds but others are all-in (also uncontested for that player)
        """
        normalized_actions = normalize_position_actions(position_actions)
        current_action = normalized_actions.get(position, "FOLD")
        
        # Count active players (those who haven't folded)
        active_positions = [pos for pos, action in normalized_actions.items() if action != "FOLD"]
        
        if strict_current_action:
            # In strict mode, only consider the current player's action
            return len(active_positions) <= 1  # Only current player is active, or no one is active
        
        # All other players folded
        other_active = [pos for pos in active_positions if pos != position]
        return len(other_active) == 0

    def get_matrix_sweep_run_summary(self, scenario_contract: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return one run-scoped matrix sweep summary for a persisted scenario contract."""
        simulation = self.database_repository.find_matrix_sweep_run_by_contract(scenario_contract)
        if simulation is None:
            return None
        return self.database_repository.get_matrix_sweep_summary(simulation.id)

    def get_matrix_payload(
        self,
        position: str,
        metric: str,
        position_actions: Dict[str, str] | None = None,
        pot_size: float = 20.0,
        bet_amount: float = 10.0,
        strict_current_action: bool = False,
        allow_compute: bool = True,
        on_cell_complete: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Get matrix payload from database.

        Phase 4: Read-only database access for GUI.
        """
        try:
            context = self._build_context(
                position=position,
                metric=metric,
                position_actions=position_actions,
                pot_size=pot_size,
                bet_amount=bet_amount,
                strict_current_action=strict_current_action,
            )
        except ValueError as e:
            self.logger.warning(f"Invalid context: {e}")
            return {
                "context": {
                    "position": position,
                    "action": normalize_position_actions(position_actions or {}).get(position, "UNKNOWN"),
                    "metric": metric,
                    "position_actions": normalize_position_actions(position_actions or {}),
                    "active_players": sum(1 for action in normalize_position_actions(position_actions or {}).values() if action != "FOLD"),
                    "pot_size": float(pot_size),
                    "bet_amount": float(bet_amount),
                },
                "cells": [],
                "status": STATUS_MISSING,
                "status_message": f"Invalid context: {e}",
            }

        if self._is_no_contest_scenario(position, position_actions or {}, strict_current_action):
            self.logger.debug(f"NO_CONTEST scenario detected for position {position}")
            cells = []
            for row in range(13):
                for col in range(13):
                    hand_key = self._matrix_keys[row][col]
                    if metric == "WIN_LOSE_PROBABILITY":
                        value = 1.0
                    elif metric == "EV":
                        value = pot_size
                    else:
                        value = 1.0
                    cells.append({
                        "row": row,
                        "col": col,
                        "hand_key": hand_key,
                        "value": value,
                        "status": STATUS_NO_CONTEST,
                        "display": format_metric_value(metric, value),
                    })
            return {
                "context": context,
                "cells": cells,
                "status": STATUS_AVAILABLE,
                "status_message": "No contest - all other players folded",
            }

        try:
            scenario_contract = self._build_scenario_contract(context)
            simulation = self.database_repository.find_matrix_sweep_run_by_contract(scenario_contract)
            if simulation is None:
                return self._build_missing_payload(context)

            summary = self.database_repository.get_matrix_sweep_summary(simulation.id)
            if summary is None or summary["hand_matrix"] is None or not summary["matrix_cells"] or len(summary["matrix_cells"]) != 169:
                return self._build_missing_payload(context)

            cells = self._build_cells_from_summary(summary["matrix_cells"], metric, on_cell_complete)
            return {
                "context": context,
                "cells": cells,
                "status": STATUS_AVAILABLE,
                "status_message": "Matrix loaded from database",
            }
        except Exception as e:
            self.logger.error(f"Database query failed: {e}", exc_info=True)
            payload = self._build_missing_payload(context)
            payload["status_message"] = f"Database error: {e}"
            return payload

    def _build_scenario_contract(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build the persisted matrix-sweep scenario contract from browser context."""
        return {
            "selected_position": context["position"],
            "hero_action": context["action"],
            "position_actions": context["position_actions"],
            "active_players": sum(1 for action in context["position_actions"].values() if action != "FOLD"),
            "num_opponents": max(0, sum(1 for pos, action in context["position_actions"].items() if action != "FOLD" and pos != context["position"])),
            "pot_size": float(context["pot_size"]),
            "bet_amount": float(context["bet_amount"]),
            "sims_per_combo": 120,
            "num_simulations": 120,
            "matrix_size": "13x13",
            "game_type": "cash",
            "run_kind": "matrix_sweep",
        }

    def _build_missing_payload(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Return the explicit missing scenario payload according to the spec."""
        cells = []
        for row in range(13):
            for col in range(13):
                hand_key = self._matrix_keys[row][col]
                cells.append({
                    "row": row,
                    "col": col,
                    "hand_key": hand_key,
                    "value": None,
                    "status": STATUS_MISSING,
                    "display": format_metric_value(context["metric"], None),
                })
        return {
            "context": context,
            "cells": cells,
            "status": STATUS_MISSING,
            "status_message": "No aggregated run available for the requested scenario",
        }

    def _build_cells_from_summary(
        self,
        matrix_cells: list,
        metric: str,
        on_cell_complete: Optional[Any],
    ) -> list[Dict[str, Any]]:
        """Build a 169-cell payload from matrix summary rows."""
        cells = []
        for cell in matrix_cells:
            metric_value = 0.0
            status = STATUS_AVAILABLE
            if cell.aggregated_metric is not None:
                metric_value = self._extract_metric_value(cell.aggregated_metric, metric)
            else:
                metric_value = 0.0

            hand_key = cell.hand_combination
            if hasattr(cell, "hero_hand") and " vs " in hand_key:
                hand_key = cell.hero_hand

            display = format_metric_value(metric, metric_value)
            cells.append({
                "row": cell.row_index,
                "col": cell.col_index,
                "hand_key": hand_key,
                "value": metric_value,
                "status": status,
                "display": display,
            })

            if on_cell_complete and callable(on_cell_complete):
                try:
                    on_cell_complete(cell.row_index, cell.col_index, metric_value, status)
                except Exception as callback_error:
                    self.logger.warning(f"Cell completion callback failed: {callback_error}")

        # Ensure the payload is ordered by row and col
        return sorted(cells, key=lambda c: (c["row"], c["col"]))

    def _extract_metric_value(self, aggregated_metric, metric: str) -> float:
        """Extract the requested metric value from an AggregatedMetric row."""
        if metric == "WIN_LOSE_PROBABILITY":
            return float(aggregated_metric.win_probability if aggregated_metric.win_probability is not None else aggregated_metric.equity or 0.0)
        if metric == "EQUITY":
            return float(aggregated_metric.equity if aggregated_metric.equity is not None else 0.0)
        if metric == "EV":
            return float(aggregated_metric.ev if aggregated_metric.ev is not None else aggregated_metric.jackpot_adjusted_ev or 0.0)
        if metric == "EQR":
            return float(aggregated_metric.jackpot_adjusted_ev if aggregated_metric.jackpot_adjusted_ev is not None else aggregated_metric.ev or 0.0)
        return 0.0

    def get_matrix_from_database(
        self,
        position: str,
        metric: str,
        position_actions: Dict[str, str] | None = None,
        pot_size: float = 20.0,
        bet_amount: float = 10.0,
        strict_current_action: bool = False,
        allow_compute: bool = True,
        on_cell_complete: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Alias for get_matrix_payload() for compatibility with GUI components."""
        return self.get_matrix_payload(
            position=position,
            metric=metric,
            position_actions=position_actions,
            pot_size=pot_size,
            bet_amount=bet_amount,
            strict_current_action=strict_current_action,
            allow_compute=allow_compute,
            on_cell_complete=on_cell_complete,
        )

    def _build_context(
        self,
        position: str,
        metric: str,
        position_actions: Dict[str, str] | None = None,
        pot_size: float = 20.0,
        bet_amount: float = 10.0,
        strict_current_action: bool = False,
    ) -> Dict[str, Any]:
        """Build browser context from parameters."""
        if position not in POSITIONS:
            raise ValueError(f"Invalid position: {position}")
        if metric not in METRICS:
            raise ValueError(f"Invalid metric: {metric}")

        actions = normalize_position_actions(position_actions or {})
        active_players = sum(1 for action in actions.values() if action != "FOLD")

        return {
            "position": position,
            "action": actions.get(position, "UNKNOWN"),
            "metric": metric,
            "position_actions": actions,
            "active_players": active_players,
            "pot_size": float(pot_size),
            "bet_amount": float(bet_amount),
            "effective_mode": "strict-current-action" if strict_current_action else "analysis",
            "timeout_ms": 30000,  # Phase 4: Default timeout for solver
        }



    def _run_async_query(self, context: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """
        Execute database query synchronously.
        """
        # Create proper context objects from dict
        try:
            position_ctx = PositionContext.from_id(context.get("position", "UTG"))
            action_ctx = ActionContext.from_id(context.get("action", "ALL_IN"))
            metric_ctx = MetricType.from_id(context.get("metric", "EQUITY"))
        except (ValueError, KeyError) as e:
            self.logger.error(f"Invalid context parameters: {e}")
            return {}
        
        # Query synchronously - let exceptions bubble up
        return self.database_repository.get_strategy_matrix_sync(
            position=position_ctx,
            action=action_ctx,
            metric=metric_ctx
        )

    async def get_convergence_data(self, position: str, position_actions: Dict[str, str] | None = None):
        """
        Get convergence data for a specific position and action context.
        
        Delegates to the database repository for convergence analysis.
        """
        try:
            # Convert position and actions to context objects
            position_ctx = PositionContext.from_id(position)
            actions = normalize_position_actions(position_actions or {})
            action_ctx = ActionContext.from_id(actions.get(position, "ALL_IN"))
            
            # Get convergence data from repository
            return await self.database_repository.get_convergence_data(position_ctx, action_ctx)
        except Exception as e:
            self.logger.error(f"Failed to get convergence data: {e}")
            return []

