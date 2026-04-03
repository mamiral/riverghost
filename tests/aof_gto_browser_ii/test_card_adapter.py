import time
import pytest
from aof_gto_browser_ii.shared.domain.card import Card, Rank, Suit
from aof_gto_browser_ii.shared.domain.hand import Hand
from aof_gto_browser_ii.shared.adapters.card_adapter import CardAdapter
from aof_gto_browser_ii.shared.exceptions.validation_errors import ValidationError


class TestCardAdapter:
    """Test suite for CardAdapter."""

    def test_to_pokerkit_individual_cards(self):
        """Test converting individual cards to PokerKit format."""
        # Test various cards
        assert CardAdapter.to_pokerkit(Card(Rank.ACE, Suit.SPADES)) == "As"
        assert CardAdapter.to_pokerkit(Card(Rank.KING, Suit.HEARTS)) == "Kh"
        assert CardAdapter.to_pokerkit(Card(Rank.QUEEN, Suit.DIAMONDS)) == "Qd"
        assert CardAdapter.to_pokerkit(Card(Rank.JACK, Suit.CLUBS)) == "Jc"
        assert CardAdapter.to_pokerkit(Card(Rank.TEN, Suit.SPADES)) == "Ts"
        assert CardAdapter.to_pokerkit(Card(Rank.TWO, Suit.HEARTS)) == "2h"

    def test_from_pokerkit_individual_cards(self):
        """Test converting PokerKit format to individual cards."""
        # Test parsing back
        card = CardAdapter.from_pokerkit("As")
        assert card == Card(Rank.ACE, Suit.SPADES)

        card = CardAdapter.from_pokerkit("kh")  # Case insensitive
        assert card == Card(Rank.KING, Suit.HEARTS)

        card = CardAdapter.from_pokerkit("2d")
        assert card == Card(Rank.TWO, Suit.DIAMONDS)

    def test_round_trip_individual_cards(self):
        """Test round-trip conversion for individual cards."""
        original_card = Card(Rank.ACE, Suit.SPADES)
        pokerkit_str = CardAdapter.to_pokerkit(original_card)
        converted_back = CardAdapter.from_pokerkit(pokerkit_str)
        assert converted_back == original_card

    def test_round_trip_all_52_cards(self):
        """Test round-trip conversion for all 52 cards."""
        for rank in Rank:
            for suit in Suit:
                original_card = Card(rank, suit)
                pokerkit_str = CardAdapter.to_pokerkit(original_card)
                converted_back = CardAdapter.from_pokerkit(pokerkit_str)
                assert converted_back == original_card, f"Failed for {original_card}"

    def test_to_pokerkit_hand(self):
        """Test converting hands to PokerKit format."""
        # Test suited hand
        hand = Hand.from_strings("As", "Ks")
        pokerkit_hand = CardAdapter.to_pokerkit_hand(hand)
        assert pokerkit_hand == ("As", "Ks")

        # Test offsuit hand
        hand = Hand.from_strings("Ah", "Kd")
        pokerkit_hand = CardAdapter.to_pokerkit_hand(hand)
        assert pokerkit_hand == ("Ah", "Kd")

        # Test pair
        hand = Hand.from_strings("2s", "2h")
        pokerkit_hand = CardAdapter.to_pokerkit_hand(hand)
        assert pokerkit_hand == ("2s", "2h")

    def test_from_pokerkit_hand(self):
        """Test converting PokerKit format to hands."""
        hand = CardAdapter.from_pokerkit_hand("As", "Ks")
        expected = Hand.from_strings("As", "Ks")
        assert hand == expected

        hand = CardAdapter.from_pokerkit_hand("ah", "kd")  # Case insensitive
        expected = Hand.from_strings("Ah", "Kd")
        assert hand == expected

    def test_round_trip_hands(self):
        """Test round-trip conversion for hands."""
        original_hand = Hand.from_strings("As", "Kh")
        pokerkit_tuple = CardAdapter.to_pokerkit_hand(original_hand)
        converted_back = CardAdapter.from_pokerkit_hand(*pokerkit_tuple)
        assert converted_back == original_hand

    def test_error_handling_invalid_card_strings(self):
        """Test error handling for invalid card strings."""
        with pytest.raises(ValueError):
            CardAdapter.from_pokerkit("Invalid")

        with pytest.raises(ValueError):
            CardAdapter.from_pokerkit("")

        with pytest.raises(ValueError):
            CardAdapter.from_pokerkit("A")  # Missing suit

        with pytest.raises(ValueError):
            CardAdapter.from_pokerkit("1s")  # Invalid rank

    def test_error_handling_duplicate_cards_in_hand(self):
        """Test error handling for duplicate cards in hand."""
        with pytest.raises(ValidationError):
            CardAdapter.from_pokerkit_hand("As", "As")

    def test_performance_single_conversion(self):
        """Test that single conversions are fast (< 1μs)."""
        card = Card(Rank.ACE, Suit.SPADES)

        # Measure conversion time
        start_time = time.perf_counter()
        for _ in range(1000):
            pokerkit_str = CardAdapter.to_pokerkit(card)
            converted_back = CardAdapter.from_pokerkit(pokerkit_str)
        end_time = time.perf_counter()

        total_time = end_time - start_time
        avg_time_per_conversion = total_time / 2000  # 1000 to_pokerkit + 1000 from_pokerkit

        # Should be reasonably fast (< 5μs)
        assert avg_time_per_conversion < 5e-6, f"Average conversion time: {avg_time_per_conversion:.2e}s"

    def test_case_insensitive_parsing(self):
        """Test that parsing is case insensitive."""
        # Test various cases
        assert CardAdapter.from_pokerkit("AS") == Card(Rank.ACE, Suit.SPADES)
        assert CardAdapter.from_pokerkit("as") == Card(Rank.ACE, Suit.SPADES)
        assert CardAdapter.from_pokerkit("As") == Card(Rank.ACE, Suit.SPADES)

        # Test hand parsing
        hand1 = CardAdapter.from_pokerkit_hand("AS", "KS")
        hand2 = Hand.from_strings("As", "Ks")
        assert hand1 == hand2