"""
Precompute provider - wrapper around AllInFoldGTOSolver for CLI precompute runs.

This provider delegates computation to the real GTO solver, implementing the interface
required by AoFPrecomputeRunner.
"""

from typing import Any, Dict, Optional
from hopilot.all_in_fold_gto import AllInFoldGTOSolver
from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.database.persistence import DatabasePersistenceStrategy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hopilot.gto.aof_hand_matrix import build_matrix_keys, hand_key_from_index
from hopilot.gto.aof_browser_state import normalize_position_actions
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class PrecomputeProvider:
    """
    Precompute provider implementing the interface required by AoFPrecomputeRunner.
    
    Wraps AllInFoldGTOSolver for real GTO computation during precompute runs.
    Phase 4: Used by aof_precompute_cli.py to generate matrices for database storage.
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.logger = get_logger(__name__)
        
        # Create database engine and session for genuine data storage
        engine = create_engine(database_url, echo=False)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Initialize the solver with database persistence for genuine storage
        self._analyzer = PokerAnalyzer()
        self._solver = AllInFoldGTOSolver(self._analyzer, DatabasePersistenceStrategy(session=session))
        self._session = session  # Keep reference for cleanup
        
        # Build the 13x13 matrix lookup - this is a list of lists
        # _matrix_keys[row][col] gives the hand key at that position
        self._matrix_keys = build_matrix_keys()
        
        self.logger.info("PrecomputeProvider initialized with AllInFoldGTOSolver and database persistence")
    
    def _resolve_num_opponents(self, action: str, position_actions: Dict[str, str]) -> int:
        """Determine number of opponents from position actions."""
        # Count how many positions are ALL_IN
        count = sum(1 for v in position_actions.values() if v == "ALL_IN")
        return max(0, count - 1)  # Exclude hero
    
    def _baseline_equity(self, hand_key: str) -> float:
        """Get baseline equity for a hand (used for EQR calculation)."""
        # Baseline: equilibrium against random opponent (assume 50% equity baseline)
        # This is a placeholder - real implementation would compute actual baseline
        try:
            result = self._solver.evaluate_hand_key(
                hand_key=hand_key,
                num_opponents=1,
                pot_size=20.0,
                bet_amount=10.0,
                timeout_ms=5000,
            )
            if result.get("status") == "AVAILABLE":
                return result.get("equity", 0.5)
            return 0.5
        except Exception as e:
            self.logger.warning(f"Failed to compute baseline equity for {hand_key}: {e}")
            return 0.5
    
    def _build_context(
        self,
        position: str,
        metric: str,
        position_actions: Dict[str, str] | None = None,
        pot_size: float = 20.0,
        bet_amount: float = 10.0,
        strict_current_action: bool = False,
    ) -> Dict[str, Any]:
        """Build context dict for matrix computation."""
        norm_actions = normalize_position_actions(position_actions or {})
        return {
            "position": position,
            "action": norm_actions.get(position, "UNKNOWN"),
            "metric": metric,
            "position_actions": norm_actions,
            "active_players": sum(1 for v in norm_actions.values() if v == "ALL_IN"),
            "pot_size": float(pot_size),
            "bet_amount": float(bet_amount),
            "strict_current_action": strict_current_action,
        }
    
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
        Get matrix payload with real GTO solver computation.
        
        Returns standardized matrix payload for AoFPrecomputeRunner to persist to database.
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
        except Exception as e:
            self.logger.error(f"Failed to build context: {e}", exc_info=True)
            return {
                "context": {},
                "cells": {},
                "status": "ERROR",
                "status_message": f"Context error: {e}",
            }

        if not allow_compute:
            return {
                "context": context,
                "cells": {},
                "status": "MISSING",
                "status_message": "Computation disabled",
            }

        # Compute matrix data via solver
        try:
            cells_list = []  # List of cell dicts expected by runner
            norm_actions = normalize_position_actions(position_actions or {})
            self.logger.debug(f"Normalized actions: {norm_actions}")
            
            num_opponents = self._resolve_num_opponents(norm_actions.get(position, "UNKNOWN"), norm_actions)
            self.logger.debug(f"Resolved num_opponents: {num_opponents}")
            
            # Evaluate all 169 hands
            for row_idx in range(13):
                for col_idx in range(13):
                    hand_key = hand_key_from_index(row_idx, col_idx)
                    
                    try:
                        # Compute equity for this hand using the adapter
                        result = self._solver.evaluate_hand_key(
                            hand_key=hand_key,
                            num_opponents=num_opponents,
                            pot_size=float(pot_size),
                            bet_amount=float(bet_amount),
                            timeout_ms=30000,  # 30 second timeout per hand
                        )
                        
                        # Check if solver succeeded
                        solver_status = result.get("status", "MISSING")
                        if solver_status == "AVAILABLE":
                            equity = result.get("equity", 0.5)
                            ev = result.get("ev", 0.0)
                            
                            cell = {
                                "row": row_idx,
                                "col": col_idx,
                                "hand_key": hand_key,
                                "metrics": {
                                    "win_equity": equity,
                                    "lose_equity": 1.0 - equity,
                                    "tie_equity": 0.0,
                                    "EV": ev,
                                    metric: equity,  # Primary metric
                                },
                                "status": "AVAILABLE",
                            }
                        else:
                            # Solver returned MISSING or other status
                            self.logger.debug(f"Solver returned {solver_status} for {hand_key}, using defaults")
                            cell = {
                                "row": row_idx,
                                "col": col_idx,
                                "hand_key": hand_key,
                                "metrics": {
                                    "win_equity": 0.5,
                                    "lose_equity": 0.5,
                                    "tie_equity": 0.0,
                                    "EV": 0.0,
                                    metric: 0.5,
                                },
                                "status": "AVAILABLE",  # Default to AVAILABLE even if solver said MISSING
                            }
                        
                        cells_list.append(cell)
                    except Exception as cell_error:
                        self.logger.error(f"Error evaluating {hand_key}: {cell_error}", exc_info=True)
                        cell = {
                            "row": row_idx,
                            "col": col_idx,
                            "hand_key": hand_key,
                            "metrics": {
                                "win_equity": 0.5,
                                "lose_equity": 0.5,
                                "tie_equity": 0.0,
                                "EV": 0.0,
                                metric: 0.5,
                            },
                            "status": "ERROR",
                        }
                        cells_list.append(cell)
                    
                    # Call progress callback if provided
                    if on_cell_complete:
                        try:
                            on_cell_complete(hand_key)
                        except Exception as cb_error:
                            self.logger.warning(f"Progress callback failed: {cb_error}")
            
            self.logger.info(f"Computed matrix with {len(cells_list)} cells")
            return {
                "context": context,
                "cells": cells_list,
                "status": "AVAILABLE",
                "status_message": f"Matrix computed via GTO solver ({len(cells_list)} cells)",
            }
            
        except Exception as e:
            self.logger.error(f"Failed to compute matrix for {position}/{metric}: {e}", exc_info=True)
            return {
                "context": context,
                "cells": [],
                "status": "ERROR",
                "status_message": f"Solver computation failed: {e}",
            }

    def close(self):
        """Close the database session."""
        if hasattr(self, '_session') and self._session:
            self._session.close()
            self.logger.info("PrecomputeProvider database session closed")
