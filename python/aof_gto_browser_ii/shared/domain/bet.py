import math
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


@dataclass(frozen=True)
class Bet:
    """Immutable bet representation with amount in big blinds.

    Represents a poker bet amount with validation for positive finite values.
    Amounts are rounded to 2 decimal places to handle floating-point precision.
    """

    amount_bb: float

    def __post_init__(self) -> None:
        """Validate bet constraints after initialization."""
        # Validate finite values first
        if not math.isfinite(self.amount_bb):
            raise ValueError(f"Bet amount must be finite, got {self.amount_bb}")

        # Round to handle floating-point precision issues using proper financial rounding
        rounded_amount = float(Decimal(str(self.amount_bb)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        # Validate positive amount
        if rounded_amount <= 0:
            raise ValueError(f"Bet amount must be > 0, got {rounded_amount} BB (original: {self.amount_bb})")

        # Update the field with rounded value
        object.__setattr__(self, 'amount_bb', rounded_amount)

    def is_zero(self) -> bool:
        """Check if bet is zero (always False since amount > 0)."""
        return False

    def is_all_in(self, stack_bb: float) -> bool:
        """Check if this bet represents an all-in bet.

        Args:
            stack_bb: Player's remaining stack in big blinds

        Returns:
            True if bet amount >= stack size
        """
        return self.amount_bb >= stack_bb

    def display_value(self) -> str:
        """Format bet amount for UI display.

        Returns:
            Formatted string like "2.5 BB" or "0.50 BB"
        """
        return f"{self.amount_bb:.2f} BB"

    def __str__(self) -> str:
        """String representation showing bet amount."""
        return self.display_value()

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"Bet(amount_bb={self.amount_bb})"