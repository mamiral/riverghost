"""
Phase 4: Minimal database-only browser data provider.

Replacement for AoFBrowserDataProvider after cache infrastructure removed.
Provides matrix data access via SQLAlchemy ORM (database only).
No cache, no aggregation, no solver modes.

CREATED IN: Phase 4 cleanup (replaces deleted AoFBrowserDataProvider)
"""

from typing import Any, Dict, Optional
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.gto.aof_browser_state import POSITIONS, normalize_position_actions, METRICS, build_browser_context
from hopilot.gto.aof_hand_matrix import build_matrix_keys, format_metric_value
from hopilot.logging_config import get_logger

logger = get_logger(__name__)

STATUS_AVAILABLE = "AVAILABLE"
STATUS_MISSING = "MISSING"


class BrowserDatabaseProvider:
    """
    Minimal provider for GUI matrix queries against database.
    
    Provides context building and database queries only.
    All cache infrastructure removed in Phase 4.
    """

    def __init__(self, database_url: str):
        """Initialize with database connection."""
        self.logger = get_logger(__name__)
        self.database_repository = DatabaseRepository(database_url=database_url)
        self._matrix_keys = build_matrix_keys()
        self._solver = None  # Phase 4: Optional solver for testing/mocking
        self.logger.info(f"BrowserDatabaseProvider initialized with database: {database_url}")

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
        
        Phase 4: Database-only implementation. No cache, no solver fallback.
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
            return self._build_status_payload(
                {
                    "position": position,
                    "action": normalize_position_actions(position_actions or {}).get(position, "UNKNOWN"),
                    "metric": metric,
                    "position_actions": normalize_position_actions(position_actions or {}),
                    "active_players": sum(1 for action in normalize_position_actions(position_actions or {}).values() if action == "ALL_IN"),
                    "pot_size": float(pot_size),
                    "bet_amount": float(bet_amount),
                },
                STATUS_MISSING,
                f"Invalid context: {e}",
            )

        # Query database for matrix data
        try:
            payload = self.database_repository.get_matrix_payload(
                position=position,
                metric=metric,
                position_actions=position_actions,
                pot_size=pot_size,
                bet_amount=bet_amount,
                strict_current_action=strict_current_action,
                allow_compute=allow_compute,
                on_cell_complete=on_cell_complete,
            )
            return payload
        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            return self._build_status_payload(
                context,
                STATUS_MISSING,
                f"Database error: {e}",
            )

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

    def _build_status_payload(
        self, context: Dict[str, Any], status: str, message: str
    ) -> Dict[str, Any]:
        """Build a status-only payload (no data)."""
        return {
            "context": context,
            "cells": [],
            "status_message": message,
        }

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
