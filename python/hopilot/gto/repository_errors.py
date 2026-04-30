"""Common repository exceptions for GTO persistence/query boundaries."""


class RepositoryError(Exception):
    """Base exception for repository boundary failures."""


class GameStateRepositoryError(RepositoryError):
    """Raised when raw game-state persistence fails."""


class SimulationRepositoryError(RepositoryError):
    """Raised when simulation or matrix persistence fails."""


class PrecomputeJobRepositoryError(RepositoryError):
    """Raised when precompute job tracking persistence fails."""


class AnalyticsRepositoryError(RepositoryError):
    """Raised when analytics/query projection retrieval fails."""


class DatabaseConnectionError(RepositoryError):
    """Raised when the backing database is unavailable."""


class InvalidContextError(RepositoryError):
    """Raised when a query context is invalid for the requested operation."""
