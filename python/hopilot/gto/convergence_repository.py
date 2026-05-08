"""
Repository for convergence snapshot data access.

Provides CRUD operations for storing and retrieving convergence tracking data
during matrix cell aggregation.
"""

from datetime import datetime
from typing import Dict, List, Optional

from hopilot.database import DatabaseConnection
from hopilot.logging_config import get_logger
from hopilot.models.convergence_snapshot import ConvergenceSnapshot

logger = get_logger(__name__)


class ConvergenceRepository:
    """
    Repository for convergence snapshot data operations.

    Handles storage and retrieval of convergence tracking data,
    providing clean separation between business logic and data access.
    """

    def __init__(self, db_connection: DatabaseConnection) -> None:
        """
        Initialize repository with database connection.

        Args:
            db_connection: Database connection instance
        """
        self.db_connection = db_connection

    def store_snapshot(self, snapshot: ConvergenceSnapshot) -> None:
        """
        Store a convergence snapshot in the database.

        Args:
            snapshot: ConvergenceSnapshot instance to store
        """
        with self.db_connection.session_scope() as session:
            session.add(snapshot)
            logger.debug(f"Stored convergence snapshot for cell {snapshot.cell_id}, sample_count {snapshot.sample_count}")

    def get_convergence_history(self, cell_id: int, simulation_id: int) -> List[ConvergenceSnapshot]:
        """
        Get convergence history for a specific cell and simulation.

        Args:
            cell_id: Matrix cell ID
            simulation_id: Simulation ID

        Returns:
            List of convergence snapshots ordered by sample_count
        """
        with self.db_connection.session_scope() as session:
            snapshots = session.query(ConvergenceSnapshot)\
                .filter_by(cell_id=cell_id, simulation_id=simulation_id)\
                .order_by(ConvergenceSnapshot.sample_count)\
                .all()
            return snapshots

    def get_scenario_convergence(self, position: str, hand_key: str) -> List[ConvergenceSnapshot]:
        """
        Get aggregated convergence history for a canonical AoF scenario.
        
        Args:
            position: Hero position (UTG, BTN, SB, BB)
            hand_key: Hero hand (e.g. 'AA', 'AKo')
            
        Returns:
            List of convergence snapshots aggregated across all matching simulations
        """
        from sqlalchemy import func
        with self.db_connection.session_scope() as session:
            from hopilot.models import MatrixCell, Simulation
            
            # Find all simulation IDs for this canonical position
            # Use the simplified logic: position-actions are derived from position
            from hopilot.gto.aof_browser_state import preset_position_actions
            actions = preset_position_actions(position)
            
            active_players = [p for p, a in actions.items() if a == "ALL_IN"]
            
            # Find simulations matching this scenario
            # This is a bit complex due to parameters being JSON blobs in some cases
            all_sims = session.query(Simulation).all()
            matching_ids = []
            for sim in all_sims:
                params = sim.parameters
                if not isinstance(params, dict):
                    import json
                    try: params = json.loads(params)
                    except: continue
                
                if params.get("selected_position") == position:
                    matching_ids.append(sim.id)
            
            if not matching_ids:
                return []
                
            # Query all snapshots for these simulations and this hand
            snapshots = session.query(ConvergenceSnapshot)\
                .join(MatrixCell, ConvergenceSnapshot.cell_id == MatrixCell.id)\
                .filter(ConvergenceSnapshot.simulation_id.in_(matching_ids))\
                .filter(MatrixCell.hand_combination == hand_key)\
                .order_by(ConvergenceSnapshot.sample_count)\
                .all()
                
            return snapshots

    def get_latest_convergence(self, simulation_id: int) -> Dict[int, ConvergenceSnapshot]:
        """
        Get the latest convergence snapshot for each cell in a simulation.

        Args:
            simulation_id: Simulation ID

        Returns:
            Dictionary mapping cell_id to latest ConvergenceSnapshot
        """
        with self.db_connection.session_scope() as session:
            # Get the maximum sample_count for each cell
            from sqlalchemy import func
            subquery = session.query(
                ConvergenceSnapshot.cell_id,
                func.max(ConvergenceSnapshot.sample_count).label('max_sample_count')
            )\
            .filter_by(simulation_id=simulation_id)\
            .group_by(ConvergenceSnapshot.cell_id)\
            .subquery()

            # Join back to get the full snapshot records
            snapshots = session.query(ConvergenceSnapshot)\
                .join(subquery, (ConvergenceSnapshot.cell_id == subquery.c.cell_id) &
                      (ConvergenceSnapshot.sample_count == subquery.c.max_sample_count))\
                .all()

            return {snapshot.cell_id: snapshot for snapshot in snapshots}

    def prune_old_snapshots(self, simulation_id: int, keep_last_n: int) -> None:
        """
        Remove old convergence snapshots, keeping only the most recent N for each cell.

        Args:
            simulation_id: Simulation ID
            keep_last_n: Number of most recent snapshots to keep per cell
        """
        with self.db_connection.session_scope() as session:
            # For each cell, delete snapshots beyond the last N
            cells = session.query(ConvergenceSnapshot.cell_id)\
                .filter_by(simulation_id=simulation_id)\
                .distinct()\
                .all()

            for (cell_id,) in cells:
                # Get all snapshots for this cell, ordered by sample_count descending
                snapshots = session.query(ConvergenceSnapshot)\
                    .filter_by(cell_id=cell_id, simulation_id=simulation_id)\
                    .order_by(ConvergenceSnapshot.sample_count.desc())\
                    .all()

                # Delete all except the first keep_last_n
                if len(snapshots) > keep_last_n:
                    to_delete = snapshots[keep_last_n:]
                    for snapshot in to_delete:
                        session.delete(snapshot)

                    logger.debug(f"Pruned {len(to_delete)} old snapshots for cell {cell_id}")