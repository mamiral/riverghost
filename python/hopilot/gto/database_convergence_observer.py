"""
Database convergence observer for storing convergence snapshots.

Implements the ConvergenceObserver protocol to store convergence tracking
data in the database during incremental aggregation.
"""

from hopilot.database import DatabaseConnection
from hopilot.gto.convergence_events import ConvergenceData, ConvergenceObserver
from hopilot.logging_config import get_logger
from hopilot.models.convergence_snapshot import ConvergenceSnapshot

logger = get_logger(__name__)


class DatabaseConvergenceObserver(ConvergenceObserver):
    """
    Observer that stores convergence snapshots in the database.

    Receives convergence update events and persists them as ConvergenceSnapshot
    records for later analysis and GUI plotting.
    """

    def __init__(self, db_connection: DatabaseConnection) -> None:
        """
        Initialize database convergence observer.

        Args:
            db_connection: Database connection for storing snapshots
        """
        self.db_connection = db_connection

    def on_convergence_update(self, data: ConvergenceData) -> None:
        """
        Handle convergence update by storing snapshot in database.

        Args:
            data: Convergence data to store
        """
        snapshot = ConvergenceSnapshot(
            cell_id=data.cell_id,
            simulation_id=data.simulation_id,
            sample_count=data.sample_count,
            equity=data.equity,
            win_probability=data.win_probability,
            ev=data.ev,
            timestamp=data.timestamp
        )

        with self.db_connection.session_scope() as session:
            session.add(snapshot)

        logger.debug(f"Stored convergence snapshot: cell {data.cell_id}, samples {data.sample_count}, equity {data.equity:.4f}")