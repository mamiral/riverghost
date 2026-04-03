import pytest
from aof_gto_browser_ii.shared.domain.equity_result import EquityResult
from aof_gto_browser_ii.shared.domain.hand import Hand
from aof_gto_browser_ii.shared.domain.card import Card, Rank, Suit


class TestEquityResult:
    """Test suite for EquityResult domain model."""

    @pytest.fixture
    def sample_hand(self) -> Hand:
        """Sample hand for testing."""
        return Hand.from_strings("As", "Kh")

    def test_construction_valid_probabilities(self, sample_hand):
        """Test creating EquityResult with valid probabilities."""
        result = EquityResult(
            hand=sample_hand,
            equity=0.6,
            win_prob=0.5,
            draw_prob=0.2,
            loss_prob=0.3,
            num_simulations=10000
        )
        assert result.hand == sample_hand
        assert result.equity == 0.6
        assert result.win_prob == 0.5
        assert result.draw_prob == 0.2
        assert result.loss_prob == 0.3
        assert result.num_simulations == 10000

    def test_validation_probability_ranges(self, sample_hand):
        """Test that probabilities must be between 0.0 and 1.0."""
        # Test win_prob too high
        with pytest.raises(ValueError, match="win_prob must be between 0.0 and 1.0"):
            EquityResult(
                hand=sample_hand,
                equity=0.6,
                win_prob=1.5,
                draw_prob=0.2,
                loss_prob=0.3,
                num_simulations=10000
            )

        # Test negative probability
        with pytest.raises(ValueError, match="loss_prob must be between 0.0 and 1.0"):
            EquityResult(
                hand=sample_hand,
                equity=0.6,
                win_prob=0.5,
                draw_prob=0.2,
                loss_prob=-0.1,
                num_simulations=10000
            )

    def test_validation_probability_sum(self, sample_hand):
        """Test that probabilities must sum to 1.0 ± 0.01."""
        # Sum too high
        with pytest.raises(ValueError, match="Probabilities must sum to 1.0 ± 0.01"):
            EquityResult(
                hand=sample_hand,
                equity=0.6,
                win_prob=0.5,
                draw_prob=0.3,
                loss_prob=0.3,
                num_simulations=10000
            )

        # Sum too low
        with pytest.raises(ValueError, match="Probabilities must sum to 1.0 ± 0.01"):
            EquityResult(
                hand=sample_hand,
                equity=0.6,
                win_prob=0.4,
                draw_prob=0.2,
                loss_prob=0.3,
                num_simulations=10000
            )

    def test_validation_equity_calculation(self, sample_hand):
        """Test that equity must equal win_prob + 0.5 * draw_prob."""
        # Incorrect equity
        with pytest.raises(ValueError, match="Equity must equal win_prob \\+ 0.5 \\* draw_prob"):
            EquityResult(
                hand=sample_hand,
                equity=0.7,  # Should be 0.5 + 0.5*0.2 = 0.6
                win_prob=0.5,
                draw_prob=0.2,
                loss_prob=0.3,
                num_simulations=10000
            )

    def test_validation_simulations_minimum(self, sample_hand):
        """Test that num_simulations must be >= 1000."""
        with pytest.raises(ValueError, match="num_simulations must be >= 1000"):
            EquityResult(
                hand=sample_hand,
                equity=0.6,
                win_prob=0.5,
                draw_prob=0.2,
                loss_prob=0.3,
                num_simulations=500
            )

    def test_display_properties(self, sample_hand):
        """Test formatted percentage properties."""
        result = EquityResult(
            hand=sample_hand,
            equity=0.6,
            win_prob=0.5,
            draw_prob=0.2,
            loss_prob=0.3,
            num_simulations=10000
        )

        assert result.win_percent == "50.00%"
        assert result.draw_percent == "20.00%"
        assert result.loss_percent == "30.00%"
        assert result.equity_percent == "60.00%"

    def test_from_monte_carlo(self, sample_hand):
        """Test creating EquityResult from Monte Carlo counts."""
        result = EquityResult.from_monte_carlo(
            hand=sample_hand,
            wins=5000,
            draws=2000,
            losses=3000,
            total_simulations=10000
        )

        assert result.hand == sample_hand
        assert result.win_prob == 0.5
        assert result.draw_prob == 0.2
        assert result.loss_prob == 0.3
        assert result.equity == 0.6  # 0.5 + 0.5*0.2
        assert result.num_simulations == 10000

    def test_from_monte_carlo_invalid_counts(self, sample_hand):
        """Test that Monte Carlo counts must sum to total_simulations."""
        with pytest.raises(ValueError, match="Win/draw/loss counts .* must sum to total_simulations"):
            EquityResult.from_monte_carlo(
                hand=sample_hand,
                wins=5000,
                draws=2000,
                losses=3000,
                total_simulations=9000  # Doesn't match sum
            )

    def test_immutability(self, sample_hand):
        """Test that EquityResult is immutable."""
        result = EquityResult(
            hand=sample_hand,
            equity=0.6,
            win_prob=0.5,
            draw_prob=0.2,
            loss_prob=0.3,
            num_simulations=10000
        )

        with pytest.raises(AttributeError):
            result.equity = 0.7  # Should fail

    def test_hashability(self, sample_hand):
        """Test that EquityResult instances are hashable."""
        result1 = EquityResult(
            hand=sample_hand,
            equity=0.6,
            win_prob=0.5,
            draw_prob=0.2,
            loss_prob=0.3,
            num_simulations=10000
        )
        result2 = EquityResult(
            hand=sample_hand,
            equity=0.6,
            win_prob=0.5,
            draw_prob=0.2,
            loss_prob=0.3,
            num_simulations=10000
        )
        result3 = EquityResult(
            hand=Hand.from_strings("Qs", "Jh"),  # Different hand
            equity=0.6,
            win_prob=0.5,
            draw_prob=0.2,
            loss_prob=0.3,
            num_simulations=10000
        )

        # Same results should have same hash
        assert hash(result1) == hash(result2)
        # Different results should have different hashes
        assert hash(result1) != hash(result3)

        # Should work in sets
        result_set = {result1, result2, result3}
        assert len(result_set) == 2  # result1 and result2 are equal

    def test_string_representations(self, sample_hand):
        """Test string representations."""
        result = EquityResult(
            hand=sample_hand,
            equity=0.5234,
            win_prob=0.5,
            draw_prob=0.0468,
            loss_prob=0.4532,
            num_simulations=10000
        )

        assert str(result) == "AKo (52.34%)"
        assert "EquityResult" in repr(result)
        assert "hand=AKo" in repr(result)
        assert "equity=0.5234" in repr(result)

    def test_edge_cases(self, sample_hand):
        """Test edge cases."""
        # Exactly 1000 simulations
        result = EquityResult(
            hand=sample_hand,
            equity=1.0,
            win_prob=1.0,
            draw_prob=0.0,
            loss_prob=0.0,
            num_simulations=1000
        )
        assert result.num_simulations == 1000

        # All wins
        result = EquityResult(
            hand=sample_hand,
            equity=1.0,
            win_prob=1.0,
            draw_prob=0.0,
            loss_prob=0.0,
            num_simulations=10000
        )
        assert result.equity == 1.0

        # All losses
        result = EquityResult(
            hand=sample_hand,
            equity=0.0,
            win_prob=0.0,
            draw_prob=0.0,
            loss_prob=1.0,
            num_simulations=10000
        )
        assert result.equity == 0.0

        # All draws (should give 0.5 equity)
        result = EquityResult(
            hand=sample_hand,
            equity=0.5,
            win_prob=0.0,
            draw_prob=1.0,
            loss_prob=0.0,
            num_simulations=10000
        )
        assert result.equity == 0.5

    def test_probability_precision_tolerance(self, sample_hand):
        """Test that small floating-point precision errors are tolerated."""
        # Probabilities sum to 1.0001 (within tolerance)
        result = EquityResult(
            hand=sample_hand,
            equity=0.6,
            win_prob=0.5,
            draw_prob=0.2,
            loss_prob=0.3001,  # Sum = 1.0001
            num_simulations=10000
        )
        assert result.loss_prob == 0.3001

        # Probabilities sum to 0.9999 (within tolerance)
        result = EquityResult(
            hand=sample_hand,
            equity=0.6,
            win_prob=0.5,
            draw_prob=0.2,
            loss_prob=0.2999,  # Sum = 0.9999
            num_simulations=10000
        )
        assert result.loss_prob == 0.2999