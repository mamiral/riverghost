import pytest
import os
import sys

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from hopilot.hand_range import HandRange, expand_range_to_hands, validate_range_syntax


class TestHandRange:
    """Test the HandRange class functionality."""

    def test_parse_aks(self):
        """Test parsing AKs."""
        result = HandRange.parse_shorthand("AKs")
        assert len(result) == 4  # 4 suit combinations
        expected = [('As', 'Ks'), ('Ah', 'Kh'), ('Ad', 'Kd'), ('Ac', 'Kc')]
        assert set(result) == set(expected)

    def test_parse_ako(self):
        """Test parsing AKo."""
        result = HandRange.parse_shorthand("AKo")
        assert len(result) == 12  # 4*3 = 12 offsuit combinations
        # Check that no suited combinations are included
        for card1, card2 in result:
            assert card1[1] != card2[1]  # Different suits

    def test_parse_pair(self):
        """Test parsing pocket pair."""
        result = HandRange.parse_shorthand("22")
        assert len(result) == 12  # 6 unique pairs * 2 orderings
        # All should be 2's with different suits
        for card1, card2 in result:
            assert card1[0] == '2' and card2[0] == '2'
            assert card1[1] != card2[1]

    def test_parse_range_dash(self):
        """Test parsing A5s-A2s."""
        result = HandRange.parse_shorthand("A5s-A2s")
        assert len(result) == 16  # 4 hands * 4 combinations each
        ranks = set()
        for card1, card2 in result:
            assert card1[0] == 'A'
            assert card1[1] == card2[1]  # Suited
            ranks.add(card2[0])
        assert ranks == {'2', '3', '4', '5'}

    def test_shorthand_from_cards(self):
        """Test converting cards back to shorthand."""
        assert HandRange.shorthand_from_cards(['As', 'Ks']) == 'AKs'
        assert HandRange.shorthand_from_cards(['As', 'Kh']) == 'AKo'
        assert HandRange.shorthand_from_cards(['2s', '2h']) == '22'

    def test_expand_range_to_hands(self):
        """Test the main expansion function."""
        hands = expand_range_to_hands("AKs")
        assert len(hands) == 4
        assert all(len(hand) == 2 for hand in hands)

    def test_validate_range_syntax(self):
        """Test range syntax validation."""
        assert validate_range_syntax("AKs") == True
        assert validate_range_syntax("invalid") == False
        assert validate_range_syntax("A5s-A2s") == True


if __name__ == "__main__":
    pytest.main([__file__])