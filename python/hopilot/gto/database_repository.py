"""Retained for backward-compatibility error class re-exports only.

All proxy methods have been removed. New code must import domain repositories directly:
  - GameStateRepository, SimulationRepository, PrecomputeJobRepository, AnalyticsRepository
"""

from hopilot.gto.repository_errors import DatabaseConnectionError, InvalidContextError

__all__ = ["DatabaseConnectionError", "InvalidContextError"]

