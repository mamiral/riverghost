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
from hopilot.gto.aof_solver_adapter import AoFSolverAdapter
from hopilot.gto.data_model import PositionContext, ActionContext, MetricType
from hopilot.gto.aof_browser_state import POSITIONS, normalize_position_actions, METRICS, build_browser_context
from hopilot.gto.aof_hand_matrix import build_matrix_keys, format_metric_value
from hopilot.logging_config import get_logger

logger = get_logger(__name__)

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
        """Initialize with database connection and solver for fallback computation."""
        self.logger = get_logger(__name__)
        self.database_repository = DatabaseRepository(database_url=database_url)
        self._matrix_keys = build_matrix_keys()
        # Initialize solver adapter for fallback computation when database is empty
        self._solver = AoFSolverAdapter()
        self.logger.info(f"BrowserDatabaseProvider initialized with database: {database_url} and AoFSolverAdapter")

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
            # Return empty cells list for invalid context
            return {
                "context": {
                    "position": position,
                    "action": normalize_position_actions(position_actions or {}).get(position, "UNKNOWN"),
                    "metric": metric,
                    "position_actions": normalize_position_actions(position_actions or {}),
                    "active_players": sum(1 for action in normalize_position_actions(position_actions or {}).values() if action == "ALL_IN"),
                    "pot_size": float(pot_size),
                    "bet_amount": float(bet_amount),
                },
                "cells": [],
                "status": STATUS_MISSING,
                "status_message": f"Invalid context: {e}",
            }

        # Check for NO_CONTEST scenarios first
        if self._is_no_contest_scenario(position, position_actions or {}, strict_current_action):
            self.logger.debug(f"NO_CONTEST scenario detected for position {position}")
            cells = []
            for row in range(13):
                for col in range(13):
                    hand_key = self._matrix_keys[row][col]
                    # For NO_CONTEST, the value depends on the metric
                    if metric == "WIN_LOSE_PROBABILITY":
                        value = 1.0  # Player wins uncontested
                    elif metric == "EV":
                        value = pot_size  # Player wins the pot
                    else:
                        value = 1.0  # Default to 1.0 for other metrics
                    
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

        # Query database for matrix data
        try:
            matrix_data = self._run_async_query(context)
            
            if not matrix_data:
                self.logger.debug(f"No matrix data found for context: {context}")
                
                # Try solver fallback if allowed
                if allow_compute:
                    self.logger.debug("Attempting solver fallback for missing data")
                    cells = self._compute_matrix_with_solver(context)
                    if cells:
                        return {
                            "context": context,
                            "cells": cells,
                            "status": STATUS_AVAILABLE,
                            "status_message": "Matrix computed with solver",
                        }
                
                # Return empty cells list if no data and no solver fallback
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
                    "status_message": "No database in this context",
                }
            
            # Format the matrix for GUI display
            formatted_matrix = {}
            metric_id = context["metric"]
            for hand_key, metric_dict in matrix_data.items():
                if isinstance(metric_dict, dict) and metric_id in metric_dict:
                    value = metric_dict[metric_id]
                    formatted_matrix[hand_key] = format_metric_value(context["metric"], value)
                elif not isinstance(metric_dict, dict):
                    formatted_matrix[hand_key] = format_metric_value(context["metric"], metric_dict)
            
            # Build cells list in the same format as precompute
            cells = []
            for row in range(13):
                for col in range(13):
                    hand_key = self._matrix_keys[row][col]
                    raw_value = None
                    display = "-"
                    status = STATUS_MISSING
                    if hand_key in matrix_data:
                        metric_dict = matrix_data[hand_key]
                        if isinstance(metric_dict, dict) and metric_id in metric_dict:
                            raw_value = metric_dict[metric_id]
                            # Ensure raw_value is numeric
                            if isinstance(raw_value, str):
                                try:
                                    raw_value = float(raw_value)
                                except ValueError:
                                    raw_value = 0.5  # default value
                            display = format_metric_value(context["metric"], raw_value)
                            status = STATUS_AVAILABLE
                        elif not isinstance(metric_dict, dict):
                            raw_value = metric_dict
                            # Ensure raw_value is numeric
                            if isinstance(raw_value, str):
                                try:
                                    raw_value = float(raw_value)
                                except ValueError:
                                    raw_value = 0.5  # default value
                            display = format_metric_value(context["metric"], raw_value)
                            status = STATUS_AVAILABLE
                    
                    cells.append({
                        "row": row,
                        "col": col,
                        "hand_key": hand_key,
                        "value": raw_value,
                        "status": status,
                        "display": display,
                    })
            
            return {
                "context": context,
                "cells": cells,
                "status": STATUS_AVAILABLE,
                "status_message": "Matrix loaded from database",
            }
        except Exception as e:
            self.logger.error(f"Database query failed: {e}", exc_info=True)
            # Return full matrix of MISSING cells on database error (no solver fallback)
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
                "status_message": f"Database error: {e}",
            }

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

    def _compute_matrix_with_solver(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Compute matrix data using the AoF solver as fallback.
        """
        cells = []
        position = context["position"]
        metric = context["metric"]
        position_actions = context["position_actions"]
        pot_size = context["pot_size"]
        bet_amount = context["bet_amount"]
        
        # Get number of opponents
        num_opponents = self._solver.resolve_num_opponents(
            context["action"], 
            position_actions
        )
        
        for row in range(13):
            for col in range(13):
                hand_key = self._matrix_keys[row][col]
                
                try:
                    # Use solver to compute value
                    result = self._solver.evaluate_hand_key(
                        hand_key=hand_key,
                        num_opponents=num_opponents,
                        pot_size=pot_size,
                        bet_amount=bet_amount,
                    )
                    
                    if result["status"] == "AVAILABLE" and result.get("win_probability") is not None:
                        # Extract the appropriate value based on metric
                        if metric == "WIN_LOSE_PROBABILITY":
                            value = result.get("win_probability", 0.5)
                        elif metric == "EV":
                            value = result.get("ev", 0.0)
                        elif metric == "EQUITY":
                            value = result.get("equity", 0.5)
                        elif metric == "EQR":
                            # EQR (EV Ratio) - for now use equity as fallback since mock doesn't provide it
                            value = result.get("equity", 0.5)
                        else:
                            value = result.get("win_probability", 0.5)  # Default fallback
                        
                        status = STATUS_AVAILABLE
                        display = format_metric_value(metric, value)
                    elif result["status"] == "TIMEOUT":
                        value = None
                        status = "TIMEOUT"
                        display = "TIMEOUT"
                    elif result["status"] == "ERROR":
                        value = None
                        status = "ERROR"
                        display = "ERROR"
                    else:
                        value = None
                        status = STATUS_MISSING
                        display = format_metric_value(metric, value)
                        
                except Exception as e:
                    self.logger.warning(f"Solver failed for hand {hand_key}: {e}")
                    value = None
                    status = STATUS_MISSING
                    display = format_metric_value(metric, value)
                
                cells.append({
                    "row": row,
                    "col": col,
                    "hand_key": hand_key,
                    "value": value,
                    "status": status,
                    "display": display,
                })
        
        return cells

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
        active_players = sum(1 for action in actions.values() if action == "ALL_IN")

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

    def _baseline_equity(self, hand_key: str) -> float:
        """Return baseline equity for a hand against a random hand.
        
        Phase 4: Simplified to return 0.5 (50%) for all hands.
        In real usage, this would compute actual equity from database or solver.
        """
        return 0.5

    def _resolve_num_opponents(self, action: str, position_actions: Dict[str, str]) -> int:
        """Resolve number of opponents based on position actions.
        
        Phase 4: Count ALL_IN actions from opponents.
        """
        if action == "FOLD":
            return 0
        # Count all opponents with ALL_IN action
        opponents = sum(1 for pos, act in position_actions.items() if pos != "UTG" and act == "ALL_IN")
        return max(1, opponents)  # At least 1 opponent
