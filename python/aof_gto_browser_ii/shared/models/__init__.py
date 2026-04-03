# AOF GTO Browser II - Shared Models
#
# This module defines the complete frontend-backend contract for Phase 1.2.
# All classes are immutable (frozen=True) and thread-safe.
#
# ARCHITECTURE:
# - Strict layering: Only stdlib + Phase 1.1 domain models (no GUI/DB/service imports)
# - Type safety: Comprehensive validation in __post_init__() methods
# - Serialization: All DTOs JSON-serializable (enums as strings)
# - Immutability: All dataclasses frozen for thread-safety
#
# CONTRACT COMPLIANCE:
# - FR-013: All DTOs use frozen=True dataclass decorator
# - FR-014: All DTOs implement __post_init__() validation
# - FR-015: Descriptive ValueError messages with actual vs expected values
# - FR-016: Error messages include context for debugging
# - FR-017: Zero external dependencies (stdlib only)
# - FR-018: Only Phase 1.1 domain models imported
# - FR-019: No GUI/database/service layer imports
# - FR-020: JSON-serializable for API contracts
#
# Exports:
#   - Enumerations: Position, Action, MetricType (string-inheriting)
#   - Input DTOs: PositionContext, ActionContext, AnalysisRequest
#   - Output DTOs: HandEvaluation, MatrixPayload, CellDisplay, PrecomputeProgress

from .enums import Position, Action, MetricType
from .input_context import PositionContext, ActionContext, AnalysisRequest
from .output_payload import HandEvaluation, MatrixPayload, CellDisplay, PrecomputeProgress

__all__ = [
    # Enumerations
    "Position",
    "Action",
    "MetricType",
    # Input DTOs
    "PositionContext",
    "ActionContext",
    "AnalysisRequest",
    # Output DTOs
    "HandEvaluation",
    "MatrixPayload",
    "CellDisplay",
    "PrecomputeProgress",
]