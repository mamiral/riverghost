"""Tests for Card domain model."""

import pytest
from aof_gto_browser_ii.shared.domain.card import Card, Rank, Suit


class TestRank:
    """Test Rank enum functionality."""

    def test_rank_values(self):
        """Test that Rank enum has correct integer values."""
        assert Rank.TWO == 2
        assert Rank.THREE == 3
        assert Rank.TEN == 10
        assert Rank.JACK == 11
        assert Rank.QUEEN == 12
        assert Rank.KING == 13
        assert Rank.ACE == 14

    def test_rank_char_property(self):
        """Test that rank.char returns correct single-character representation."""
        assert Rank.TWO.char == "2"
        assert Rank.THREE.char == "3"
        assert Rank.TEN.char == "T"
        assert Rank.JACK.char == "J"
        assert Rank.QUEEN.char == "Q"
        assert Rank.KING.char == "K"
        assert Rank.ACE.char == "A"


class TestSuit:
    """Test Suit enum functionality."""

    def test_suit_values(self):
        """Test that Suit enum has correct string values."""
        assert Suit.SPADES == "s"
        assert Suit.HEARTS == "h"
        assert Suit.DIAMONDS == "d"
        assert Suit.CLUBS == "c"

    def test_suit_full_name_property(self):
        """Test that suit.full_name returns correct full names."""
        assert Suit.SPADES.full_name == "Spades"
        assert Suit.HEARTS.full_name == "Hearts"
        assert Suit.DIAMONDS.full_name == "Diamonds"
        assert Suit.CLUBS.full_name == "Clubs"


class TestCard:
    """Test Card dataclass functionality."""

    def test_card_construction(self):
        """Test basic Card construction."""
        card = Card(Rank.ACE, Suit.SPADES)
        assert card.rank == Rank.ACE
        assert card.suit == Suit.SPADES

    def test_card_immutability(self):
        """Test that Card is immutable (frozen dataclass)."""
        card = Card(Rank.ACE, Suit.SPADES)

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            card.rank = Rank.KING

        with pytest.raises(AttributeError):
            card.suit = Suit.HEARTS

    def test_card_hashability(self):
        """Test that Card is hashable (can be used in sets and dicts)."""
        card1 = Card(Rank.ACE, Suit.SPADES)
        card2 = Card(Rank.ACE, Suit.SPADES)
        card3 = Card(Rank.KING, Suit.HEARTS)

        # Can be used in sets
        card_set = {card1, card2, card3}
        assert len(card_set) == 2  # card1 and card2 are equal

        # Can be used as dict keys
        card_dict = {card1: "ace spades", card3: "king hearts"}
        assert card_dict[card2] == "ace spades"  # card2 == card1

    def test_card_equality(self):
        """Test Card equality comparison."""
        card1 = Card(Rank.ACE, Suit.SPADES)
        card2 = Card(Rank.ACE, Suit.SPADES)
        card3 = Card(Rank.KING, Suit.SPADES)
        card4 = Card(Rank.ACE, Suit.HEARTS)

        assert card1 == card2
        assert card1 != card3
        assert card1 != card4
        assert card3 != card4

    def test_from_string_shorthand(self):
        """Test parsing shorthand card strings."""
        test_cases = [
            ("As", Rank.ACE, Suit.SPADES),
            ("Kh", Rank.KING, Suit.HEARTS),
            ("Qd", Rank.QUEEN, Suit.DIAMONDS),
            ("Jc", Rank.JACK, Suit.CLUBS),
            ("2s", Rank.TWO, Suit.SPADES),
            ("3h", Rank.THREE, Suit.HEARTS),
            ("4d", Rank.FOUR, Suit.DIAMONDS),
            ("5c", Rank.FIVE, Suit.CLUBS),
            ("6s", Rank.SIX, Suit.SPADES),
            ("7h", Rank.SEVEN, Suit.HEARTS),
            ("8d", Rank.EIGHT, Suit.DIAMONDS),
            ("9c", Rank.NINE, Suit.CLUBS),
            ("Ts", Rank.TEN, Suit.SPADES),
        ]

        for string_input, expected_rank, expected_suit in test_cases:
            card = Card.from_string(string_input)
            assert card.rank == expected_rank
            assert card.suit == expected_suit

    def test_from_string_long_form(self):
        """Test parsing long form card strings."""
        test_cases = [
            ("ACE OF SPADES", Rank.ACE, Suit.SPADES),
            ("KING OF HEARTS", Rank.KING, Suit.HEARTS),
            ("QUEEN OF DIAMONDS", Rank.QUEEN, Suit.DIAMONDS),
            ("JACK OF CLUBS", Rank.JACK, Suit.CLUBS),
            ("TEN OF SPADES", Rank.TEN, Suit.SPADES),
            ("TWO OF HEARTS", Rank.TWO, Suit.HEARTS),
        ]

        for string_input, expected_rank, expected_suit in test_cases:
            card = Card.from_string(string_input)
            assert card.rank == expected_rank
            assert card.suit == expected_suit

    def test_from_string_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        test_cases = [
            ("as", "As"),
            ("AS", "As"),
            ("As", "As"),
            ("aS", "As"),
            ("ace of spades", "As"),
            ("Ace Of Spades", "As"),
            ("ACE of SPADES", "As"),
        ]

        for input_str, expected_output in test_cases:
            card = Card.from_string(input_str)
            assert card.to_string() == expected_output

    def test_from_string_whitespace_handling(self):
        """Test that whitespace is properly trimmed."""
        test_cases = [
            (" As ", "As"),
            ("  Kh  ", "Kh"),
            (" Qd\t", "Qd"),
            ("\nJc ", "Jc"),
        ]

        for input_str, expected_output in test_cases:
            card = Card.from_string(input_str)
            assert card.to_string() == expected_output

    def test_from_string_invalid_formats(self):
        """Test that invalid card strings raise ValueError."""
        invalid_inputs = [
            "",  # Empty string
            "A",  # Missing suit
            "1s",  # Invalid rank
            "AX",  # Invalid suit
            "AS EXTRA",  # Extra content
            "INVALID",  # No "of"
            "ACE SPADES",  # Missing "of"
            "KING OF",  # Missing suit
            "QUEEN OF INVALID",  # Invalid suit
        ]

        for invalid_input in invalid_inputs:
            with pytest.raises(ValueError):
                Card.from_string(invalid_input)

    def test_to_string(self):
        """Test to_string() returns normalized shorthand."""
        test_cases = [
            (Card(Rank.ACE, Suit.SPADES), "As"),
            (Card(Rank.KING, Suit.HEARTS), "Kh"),
            (Card(Rank.QUEEN, Suit.DIAMONDS), "Qd"),
            (Card(Rank.JACK, Suit.CLUBS), "Jc"),
            (Card(Rank.TEN, Suit.SPADES), "Ts"),
            (Card(Rank.TWO, Suit.HEARTS), "2h"),
        ]

        for card, expected_string in test_cases:
            assert card.to_string() == expected_string

    def test_str_method(self):
        """Test __str__() uses shorthand format."""
        card = Card(Rank.ACE, Suit.SPADES)
        assert str(card) == "As"
        assert str(card) == card.to_string()

    def test_repr_method(self):
        """Test __repr__() provides detailed representation."""
        card = Card(Rank.ACE, Suit.SPADES)
        repr_str = repr(card)
        assert "Card" in repr_str
        assert "ACE" in repr_str
        assert "SPADES" in repr_str

    def test_is_ace(self):
        """Test is_ace() method."""
        ace_spades = Card(Rank.ACE, Suit.SPADES)
        king_hearts = Card(Rank.KING, Suit.HEARTS)

        assert ace_spades.is_ace() == True
        assert king_hearts.is_ace() == False

    def test_round_trip_conversion(self):
        """Test that all 52 cards can round-trip through string conversion."""
        all_ranks = list(Rank)
        all_suits = list(Suit)

        for rank in all_ranks:
            for suit in all_suits:
                original_card = Card(rank, suit)

                # Convert to string and back
                string_form = original_card.to_string()
                reconstructed_card = Card.from_string(string_form)

                # Should be identical
                assert original_card == reconstructed_card
                assert original_card.rank == reconstructed_card.rank
                assert original_card.suit == reconstructed_card.suit