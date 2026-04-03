import math
import pytest
from aof_gto_browser_ii.shared.domain.bet import Bet


class TestBet:
    """Test suite for Bet domain model."""

    def test_construction_valid_amount(self):
        """Test creating Bet with valid amount."""
        bet = Bet(2.5)
        assert bet.amount_bb == 2.5

    def test_validation_positive_amount(self):
        """Test that bet amount must be > 0."""
        with pytest.raises(ValueError, match="Bet amount must be > 0"):
            Bet(0.0)

        with pytest.raises(ValueError, match="Bet amount must be > 0"):
            Bet(-1.0)

    def test_validation_finite_amount(self):
        """Test that bet amount must be finite."""
        with pytest.raises(ValueError, match="Bet amount must be finite"):
            Bet(float('nan'))

        with pytest.raises(ValueError, match="Bet amount must be finite"):
            Bet(float('inf'))

        with pytest.raises(ValueError, match="Bet amount must be finite"):
            Bet(float('-inf'))

    def test_floating_point_rounding(self):
        """Test that amounts are rounded to 2 decimal places."""
        # Test rounding up
        bet = Bet(2.99999999)
        assert bet.amount_bb == 3.00

        # Test rounding down
        bet = Bet(2.99499999)
        assert bet.amount_bb == 2.99

        # Test exact values preserved
        bet = Bet(2.50)
        assert bet.amount_bb == 2.50

    def test_is_zero_always_false(self):
        """Test that is_zero() always returns False."""
        bet = Bet(0.01)
        assert not bet.is_zero()

        bet = Bet(1000.0)
        assert not bet.is_zero()

    def test_is_all_in(self):
        """Test all-in detection."""
        bet = Bet(10.0)

        # Not all-in with larger stack
        assert not bet.is_all_in(15.0)

        # Exactly all-in
        assert bet.is_all_in(10.0)

        # All-in with smaller stack
        assert bet.is_all_in(5.0)

    def test_display_value(self):
        """Test formatted display value."""
        bet = Bet(2.5)
        assert bet.display_value() == "2.50 BB"

        bet = Bet(10.0)
        assert bet.display_value() == "10.00 BB"

        bet = Bet(0.25)
        assert bet.display_value() == "0.25 BB"

    def test_immutability(self):
        """Test that Bet is immutable."""
        bet = Bet(5.0)
        with pytest.raises(AttributeError):
            bet.amount_bb = 10.0  # Should fail

    def test_hashability(self):
        """Test that Bet instances are hashable."""
        bet1 = Bet(5.0)
        bet2 = Bet(5.0)
        bet3 = Bet(10.0)

        # Same amounts should have same hash
        assert hash(bet1) == hash(bet2)
        # Different amounts should have different hashes
        assert hash(bet1) != hash(bet3)

        # Should work in sets
        bet_set = {bet1, bet2, bet3}
        assert len(bet_set) == 2  # bet1 and bet2 are equal

    def test_string_representations(self):
        """Test string representations."""
        bet = Bet(2.5)
        assert str(bet) == "2.50 BB"
        assert repr(bet) == "Bet(amount_bb=2.5)"

    def test_edge_cases(self):
        """Test edge cases."""
        # Very small amount
        bet = Bet(0.01)
        assert bet.amount_bb == 0.01

        # Very large amount
        bet = Bet(999999.99)
        assert bet.amount_bb == 999999.99

        # Rounding edge cases
        bet = Bet(1.005)
        assert bet.amount_bb == 1.01  # Rounds up

        bet = Bet(1.004)
        assert bet.amount_bb == 1.00  # Rounds down

    def test_rounding_preserves_validation(self):
        """Test that rounding doesn't create invalid values."""
        # This would be 0.00 after rounding, should be invalid
        with pytest.raises(ValueError, match="Bet amount must be > 0"):
            Bet(0.004)  # Rounds to 0.00

        # This should be valid
        bet = Bet(0.005)  # Rounds to 0.01
        assert bet.amount_bb == 0.01