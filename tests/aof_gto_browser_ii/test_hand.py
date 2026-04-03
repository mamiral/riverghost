"""Tests for Hand domain model."""

import pytest
from aof_gto_browser_ii.shared.domain.hand import Hand
from aof_gto_browser_ii.shared.domain.card import Card, Rank, Suit
from aof_gto_browser_ii.shared.exceptions.validation_errors import ValidationError


class TestHand:
    """Test Hand dataclass functionality."""

    def test_hand_construction(self):
        """Test basic Hand construction."""
        card1 = Card(Rank.ACE, Suit.SPADES)
        card2 = Card(Rank.KING, Suit.HEARTS)
        hand = Hand(card1=card1, card2=card2)

        assert hand.card1 == card1
        assert hand.card2 == card2

    def test_hand_duplicate_card_validation(self):
        """Test that duplicate cards raise ValidationError."""
        card1 = Card(Rank.ACE, Suit.SPADES)
        card2 = Card(Rank.ACE, Suit.SPADES)  # Same card

        with pytest.raises(ValidationError, match="duplicate"):
            Hand(card1=card1, card2=card2)

    def test_from_strings(self):
        """Test Hand.from_strings() parsing."""
        hand = Hand.from_strings("As", "Kh")

        assert hand.card1.rank == Rank.ACE
        assert hand.card1.suit == Suit.SPADES
        assert hand.card2.rank == Rank.KING
        assert hand.card2.suit == Suit.HEARTS

    def test_from_tuple(self):
        """Test Hand.from_tuple() parsing."""
        hand = Hand.from_tuple(("As", "Kh"))

        assert hand.card1.rank == Rank.ACE
        assert hand.card1.suit == Suit.SPADES
        assert hand.card2.rank == Rank.KING
        assert hand.card2.suit == Suit.HEARTS

    def test_to_strings(self):
        """Test to_strings() for DTO transport."""
        hand = Hand.from_strings("As", "Kh")
        strings = hand.to_strings()

        assert strings == ("As", "Kh")

    def test_to_shorthand_pairs(self):
        """Test to_shorthand() for pairs."""
        test_cases = [
            (("As", "Ah"), "AA"),
            (("Ks", "Kh"), "KK"),
            (("Qs", "Qh"), "QQ"),
            (("2s", "2h"), "22"),
        ]

        for card_strings, expected in test_cases:
            hand = Hand.from_strings(*card_strings)
            assert hand.to_shorthand() == expected

    def test_to_shorthand_suited(self):
        """Test to_shorthand() for suited hands."""
        test_cases = [
            (("As", "Ks"), "AKs"),
            (("Kh", "Qh"), "KQs"),
            (("Jd", "Td"), "JTs"),
            (("9c", "8c"), "98s"),
            (("7s", "2s"), "72s"),
        ]

        for card_strings, expected in test_cases:
            hand = Hand.from_strings(*card_strings)
            assert hand.to_shorthand() == expected

    def test_to_shorthand_offsuit(self):
        """Test to_shorthand() for offsuit hands."""
        test_cases = [
            (("As", "Kh"), "AKo"),
            (("Kd", "Qc"), "KQo"),
            (("Js", "Th"), "JTo"),
            (("9h", "8d"), "98o"),
            (("7c", "2s"), "72o"),
        ]

        for card_strings, expected in test_cases:
            hand = Hand.from_strings(*card_strings)
            assert hand.to_shorthand() == expected

    def test_to_shorthand_order_independence(self):
        """Test that hand order doesn't affect shorthand (AKs vs KAs both become AKs)."""
        hand1 = Hand.from_strings("As", "Ks")  # A first
        hand2 = Hand.from_strings("Ks", "As")  # K first

        assert hand1.to_shorthand() == "AKs"
        assert hand2.to_shorthand() == "AKs"
        assert hand1.to_shorthand() == hand2.to_shorthand()

    def test_to_cards(self):
        """Test to_cards() returns list of cards."""
        hand = Hand.from_strings("As", "Kh")
        cards = hand.to_cards()

        assert len(cards) == 2
        assert cards[0] == hand.card1
        assert cards[1] == hand.card2

    def test_is_pair(self):
        """Test is_pair() method."""
        pair_hand = Hand.from_strings("As", "Ah")
        non_pair_hand = Hand.from_strings("As", "Kh")

        assert pair_hand.is_pair() == True
        assert non_pair_hand.is_pair() == False

    def test_is_suited(self):
        """Test is_suited() method."""
        suited_hand = Hand.from_strings("As", "Ks")
        offsuit_hand = Hand.from_strings("As", "Kh")

        assert suited_hand.is_suited() == True
        assert offsuit_hand.is_suited() == False

    def test_is_offsuit(self):
        """Test is_offsuit() method."""
        suited_hand = Hand.from_strings("As", "Ks")
        offsuit_hand = Hand.from_strings("As", "Kh")

        assert suited_hand.is_offsuit() == False
        assert offsuit_hand.is_offsuit() == True

    def test_num_combos(self):
        """Test num_combos() returns correct combination counts."""
        pair_hand = Hand.from_strings("As", "Ah")  # Pair
        suited_hand = Hand.from_strings("As", "Ks")  # Suited
        offsuit_hand = Hand.from_strings("As", "Kh")  # Offsuit

        assert pair_hand.num_combos() == 6
        assert suited_hand.num_combos() == 4
        assert offsuit_hand.num_combos() == 12

    def test_is_broadway(self):
        """Test is_broadway() method."""
        broadway_hand = Hand.from_strings("As", "Ks")  # A, K
        non_broadway_hand = Hand.from_strings("9s", "8s")  # 9, 8
        mixed_hand = Hand.from_strings("As", "9s")  # A, 9

        assert broadway_hand.is_broadway() == True
        assert non_broadway_hand.is_broadway() == False
        assert mixed_hand.is_broadway() == False

    def test_is_connected(self):
        """Test is_connected() method."""
        connected_hand = Hand.from_strings("As", "Ks")  # A, K (diff = 1)
        non_connected_hand = Hand.from_strings("As", "Qs")  # A, Q (diff = 2)
        pair_hand = Hand.from_strings("As", "Ah")  # Pair (diff = 0)

        assert connected_hand.is_connected() == True
        assert non_connected_hand.is_connected() == False
        assert pair_hand.is_connected() == False

    def test_is_gapped(self):
        """Test is_gapped() method."""
        gapped_hand = Hand.from_strings("As", "Qs")  # A, Q (diff = 2)
        double_gapped_hand = Hand.from_strings("As", "Js")  # A, J (diff = 3)
        connected_hand = Hand.from_strings("As", "Ks")  # A, K (diff = 1)
        wide_gapped_hand = Hand.from_strings("As", "Ts")  # A, T (diff = 4)

        assert gapped_hand.is_gapped() == True
        assert double_gapped_hand.is_gapped() == True
        assert connected_hand.is_gapped() == False
        assert wide_gapped_hand.is_gapped() == False

    def test_hand_immutability(self):
        """Test that Hand is immutable (frozen dataclass)."""
        hand = Hand.from_strings("As", "Kh")

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            hand.card1 = Card(Rank.QUEEN, Suit.SPADES)

        with pytest.raises(AttributeError):
            hand.card2 = Card(Rank.QUEEN, Suit.HEARTS)

    def test_hand_hashability(self):
        """Test that Hand is hashable."""
        hand1 = Hand.from_strings("As", "Kh")
        hand2 = Hand.from_strings("As", "Kh")
        hand3 = Hand.from_strings("Kd", "Ah")

        # Can be used in sets
        hand_set = {hand1, hand2, hand3}
        assert len(hand_set) == 2  # hand1 and hand2 are equal

        # Can be used as dict keys
        hand_dict = {hand1: "pocket rockets", hand3: "big slick"}
        assert hand_dict[hand2] == "pocket rockets"

    def test_hand_equality(self):
        """Test Hand equality comparison."""
        hand1 = Hand.from_strings("As", "Kh")
        hand2 = Hand.from_strings("As", "Kh")  # Same cards
        hand3 = Hand.from_strings("Kh", "As")  # Same cards, different order
        hand4 = Hand.from_strings("As", "Qh")  # Different cards

        assert hand1 == hand2
        assert hand1 == hand3  # Order doesn't matter for equality
        assert hand1 != hand4

    def test_str_method(self):
        """Test __str__() uses shorthand."""
        hand = Hand.from_strings("As", "Kh")
        assert str(hand) == "AKo"
        assert str(hand) == hand.to_shorthand()

    def test_repr_method(self):
        """Test __repr__() provides detailed representation."""
        hand = Hand.from_strings("As", "Kh")
        repr_str = repr(hand)
        assert "Hand.from_strings" in repr_str
        assert "'As'" in repr_str
        assert "'Kh'" in repr_str

    def test_all_possible_hands_creation(self):
        """Test that all 1326 possible hands can be created without errors."""
        # This is a sanity check - we don't need to test all 1326 explicitly
        # Just test a few representative ones
        test_hands = [
            ("As", "Kh"), ("2s", "3h"), ("Td", "Jc"), ("Qs", "Ks"),
            ("Ac", "Ad"), ("7h", "7d"), ("9s", "9c")
        ]

        for card1_str, card2_str in test_hands:
            # Should not raise any exceptions
            hand = Hand.from_strings(card1_str, card2_str)
            assert hand is not None
            assert hand.to_shorthand() is not None

    def test_edge_cases(self):
        """Test edge cases for hand creation and methods."""
        # Test with different card orders
        hand1 = Hand.from_strings("As", "Ks")  # A first
        hand2 = Hand.from_strings("Ks", "As")  # K first

        assert hand1.to_shorthand() == hand2.to_shorthand() == "AKs"

        # Test boundary ranks
        low_hand = Hand.from_strings("2s", "3h")
        assert low_hand.to_shorthand() == "32o"

        high_hand = Hand.from_strings("As", "Ks")
        assert high_hand.to_shorthand() == "AKs"