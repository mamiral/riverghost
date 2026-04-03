"""Custom exception types for domain model validation."""


class ValidationError(Exception):
    """Base exception for domain model validation failures."""
    pass


class RangeError(ValidationError):
    """Exception raised for invalid HandRange notation or operations."""
    pass


class PositionError(ValidationError):
    """Exception raised for invalid position values."""
    pass