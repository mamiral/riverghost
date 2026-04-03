"""Tests for HandRange domain model."""

import pytest
from aof_gto_browser_ii.shared.domain.hand_range import HandRange
from aof_gto_browser_ii.shared.domain.hand import Hand
from aof_gto_browser_ii.shared.domain.card import Card, Rank, Suit
from aof_gto_browser_ii.shared.exceptions.validation_errors import RangeError


class TestHandRange:
    """Test HandRange dataclass functionality."""

    def test_handrange_construction(self):
        """Test basic HandRange construction."""
        hand1 = Hand.from_strings("As", "Ks")
        hand2 = Hand.from_strings("Ah", "Kd")  # Different suits to avoid duplicate shorthands
        hand_range = HandRange(hands=[hand1, hand2], notation="AKs")

        assert len(hand_range.hands) == 2
        assert hand_range.notation == "AKs"

    def test_handrange_duplicate_hand_validation(self):
        """Test that duplicate hands raise ValueError."""
        hand1 = Hand.from_strings("As", "Ks")
        hand2 = Hand.from_strings("As", "Ks")  # Same hand

        with pytest.raises(ValueError, match="duplicate"):
            HandRange(hands=[hand1, hand2], notation="AKs")

    def test_from_shorthand_empty(self):
        """Test that empty notation raises RangeError."""
        with pytest.raises(RangeError, match="Empty"):
            HandRange.from_shorthand("")

        with pytest.raises(RangeError, match="Empty"):
            HandRange.from_shorthand("   ")

    def test_from_shorthand_single_pair(self):
        """Test parsing single pair like 'AA'."""
        range_obj = HandRange.from_shorthand("AA")

        assert range_obj.size() == 1  # 1 hand type
        assert range_obj.num_combos() == 6  # 6 combinations for AA
        assert range_obj.notation == "AA"

        # Check that it contains AA hands
        aa_hand = Hand.from_strings("As", "Ah")  # One possible AA
        assert range_obj.contains(aa_hand)

    def test_from_shorthand_pair_plus(self):
        """Test parsing pair plus notation like '22+'."""
        range_obj = HandRange.from_shorthand("22+")

        # Should contain pairs from 22 to AA
        expected_pairs = ["22", "33", "44", "55", "66", "77", "88", "99", "TT", "JJ", "QQ", "KK", "AA"]
        assert range_obj.size() == len(expected_pairs)

        # Total combos: 13 pairs × 6 combos each = 78
        assert range_obj.num_combos() == 78

        # Check round-trip
        assert range_obj.to_shorthand() == "22+"

    def test_from_shorthand_single_suited(self):
        """Test parsing single suited hand like 'AKs'."""
        range_obj = HandRange.from_shorthand("AKs")

        assert range_obj.size() == 1  # 1 hand type
        assert range_obj.num_combos() == 4  # 4 suited combinations
        assert range_obj.notation == "AKs"

        # Check that it contains AKs hands
        aks_hand = Hand.from_strings("As", "Ks")
        assert range_obj.contains(aks_hand)

    def test_from_shorthand_single_offsuit(self):
        """Test parsing single offsuit hand like 'AKo'."""
        range_obj = HandRange.from_shorthand("AKo")

        assert range_obj.size() == 1  # 1 hand type
        assert range_obj.num_combos() == 12  # 12 offsuit combinations
        assert range_obj.notation == "AKo"

        # Check that it contains AKo hands
        ako_hand = Hand.from_strings("As", "Kh")  # One possible AKo
        assert range_obj.contains(ako_hand)

    def test_from_shorthand_suited_plus(self):
        """Test parsing suited plus notation like 'AKs+'."""
        range_obj = HandRange.from_shorthand("AKs+")

        # Should contain AKs, AQs, AJs, ATs, A9s, A8s, A7s, A6s, A5s, A4s, A3s, A2s
        assert range_obj.size() == 12

        # Total combos: 12 hands × 4 combos each = 48
        assert range_obj.num_combos() == 48

        # Check round-trip
        assert range_obj.to_shorthand() == "AKs+"

    def test_from_shorthand_pair_range(self):
        """Test parsing pair range like '22-99'."""
        range_obj = HandRange.from_shorthand("22-99")

        # Should contain pairs from 22 to 99 (8 pairs)
        expected_pairs = ["22", "33", "44", "55", "66", "77", "88", "99"]
        assert range_obj.size() == len(expected_pairs)

        # Total combos: 8 pairs × 6 combos each = 48
        assert range_obj.num_combos() == 48

        # Check round-trip
        assert range_obj.to_shorthand() == "22-99"

    def test_from_shorthand_suited_range(self):
        """Test parsing suited range like 'A5s-A2s'."""
        range_obj = HandRange.from_shorthand("A5s-A2s")

        # Should contain A5s, A4s, A3s, A2s (4 hands)
        assert range_obj.size() == 4

        # Total combos: 4 hands × 4 combos each = 16
        assert range_obj.num_combos() == 16

        # Check round-trip
        assert range_obj.to_shorthand() == "A5s-A2s"

    def test_from_shorthand_complex_notation(self):
        """Test parsing complex notation like 'AKs+,QQ+,A5s-A2s'."""
        range_obj = HandRange.from_shorthand("AKs+,QQ+,A5s-A2s")

        # AKs+ (12 hands) + QQ+ (3 pairs) + A5s-A2s (4 hands) = 19 total, but overlap of 4 hands = 15 unique
        expected_size = 15
        assert range_obj.size() == expected_size

        # Check round-trip
        assert range_obj.to_shorthand() == "AKs+,QQ+,A5s-A2s"

    def test_from_shorthand_semicolon_separation(self):
        """Test that semicolon and comma both work as separators."""
        range1 = HandRange.from_shorthand("AKs,QQ")
        range2 = HandRange.from_shorthand("AKs;QQ")

        assert range1.size() == range2.size() == 2

    def test_from_shorthand_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        range_obj = HandRange.from_shorthand(" AKs , QQ , 22+ ")

        assert range_obj.size() == 14  # AKs + QQ + 22+ (13 pairs)
        assert range_obj.to_shorthand() == " AKs , QQ , 22+ "

    def test_from_shorthand_invalid_formats(self):
        """Test that invalid formats raise RangeError."""
        invalid_notations = [
            "XX+",  # Invalid rank
            "AKx",  # Invalid suit indicator
            "A5s-A2h",  # Mixed suit indicators in range
            "ABC",  # Invalid format
            "A",  # Too short
            "AKs-",  # Incomplete range
            "-AKs",  # Incomplete range
        ]

        for invalid in invalid_notations:
            with pytest.raises(Exception):  # Can be RangeError, ValueError, etc.
                HandRange.from_shorthand(invalid)

    def test_to_strings(self):
        """Test to_strings() returns card pairs for DTO transport."""
        range_obj = HandRange.from_shorthand("AKs")
        strings = range_obj.to_strings()

        assert len(strings) == 1  # 1 hand type
        assert all(len(pair) == 2 for pair in strings)  # Each pair has 2 strings
        assert all(isinstance(card_str, str) for pair in strings for card_str in pair)

    def test_size_and_num_combos(self):
        """Test size() and num_combos() calculations."""
        # Single pair
        pair_range = HandRange.from_shorthand("AA")
        assert pair_range.size() == 1
        assert pair_range.num_combos() == 6

        # Single suited
        suited_range = HandRange.from_shorthand("AKs")
        assert suited_range.size() == 1
        assert suited_range.num_combos() == 4

        # Single offsuit
        offsuit_range = HandRange.from_shorthand("AKo")
        assert offsuit_range.size() == 1
        assert offsuit_range.num_combos() == 12

    def test_contains(self):
        """Test contains() method."""
        range_obj = HandRange.from_shorthand("AKs")

        aks_hand = Hand.from_strings("As", "Ks")
        ako_hand = Hand.from_strings("As", "Kh")
        qq_hand = Hand.from_strings("Qs", "Qh")

        assert range_obj.contains(aks_hand) == True
        assert range_obj.contains(ako_hand) == False
        assert range_obj.contains(qq_hand) == False

    def test_union(self):
        """Test union() static method."""
        range1 = HandRange.from_shorthand("AKs")
        range2 = HandRange.from_shorthand("QQ")

        union_range = HandRange.union(range1, range2)

        assert union_range.size() == 2  # AKs + QQ
        assert "AKs" in union_range.notation
        assert "QQ" in union_range.notation

        # Should contain hands from both ranges
        aks_hand = Hand.from_strings("As", "Ks")
        qq_hand = Hand.from_strings("Qs", "Qh")
        assert union_range.contains(aks_hand)
        assert union_range.contains(qq_hand)

    def test_intersection(self):
        """Test intersection() static method."""
        range1 = HandRange.from_shorthand("AKs,QQ")
        range2 = HandRange.from_shorthand("QQ,KK")

        intersection_range = HandRange.intersection(range1, range2)

        assert intersection_range.size() == 1  # Only QQ
        assert "QQ" in intersection_range.notation

        # Should contain only common hands
        qq_hand = Hand.from_strings("Qs", "Qh")
        aks_hand = Hand.from_strings("As", "Ks")
        kk_hand = Hand.from_strings("Ks", "Kh")

        assert intersection_range.contains(qq_hand)
        assert not intersection_range.contains(aks_hand)
        assert not intersection_range.contains(kk_hand)

    def test_handrange_immutability(self):
        """Test that HandRange is immutable (frozen dataclass)."""
        range_obj = HandRange.from_shorthand("AKs")

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            range_obj.hands = []

        with pytest.raises(AttributeError):
            range_obj.notation = "QQ"

    def test_handrange_hashability(self):
        """Test that HandRange is hashable."""
        range1 = HandRange.from_shorthand("AKs")
        range2 = HandRange.from_shorthand("AKs")
        range3 = HandRange.from_shorthand("QQ")

        # Can be used in sets
        range_set = {range1, range2, range3}
        assert len(range_set) == 2  # range1 and range2 are equal

        # Can be used as dict keys
        range_dict = {range1: "broadway", range3: "ladies"}
        assert range_dict[range2] == "broadway"

    def test_handrange_equality(self):
        """Test HandRange equality comparison."""
        range1 = HandRange.from_shorthand("AKs")
        range2 = HandRange.from_shorthand("AKs")  # Same content
        range3 = HandRange.from_shorthand("QQ")  # Different content

        assert range1 == range2
        assert range1 != range3

    def test_str_and_repr(self):
        """Test __str__() and __repr__() methods."""
        range_obj = HandRange.from_shorthand("AKs+,QQ+")

        assert str(range_obj) == "AKs+,QQ+"
        repr_str = repr(range_obj)
        assert "HandRange.from_shorthand" in repr_str
        assert "'AKs+,QQ+'" in repr_str

    def test_performance_parsing(self):
        """Test that complex range parsing completes within performance requirements (< 10ms)."""
        import time

        complex_notation = "AKs+,QQ+,A5s-A2s,KQs+,JTs+,T9s+,98s+,87s+,76s+,65s+,54s+,43s+,32s+"

        start_time = time.time()
        range_obj = HandRange.from_shorthand(complex_notation)
        end_time = time.time()

        parsing_time_ms = (end_time - start_time) * 1000

        # Should parse in less than 10ms
        assert parsing_time_ms < 10.0, f"Parsing took {parsing_time_ms}ms, expected < 10ms"

        # Should have created a valid range
        assert range_obj.size() > 0
        assert range_obj.num_combos() > 0

    def test_deduplication(self):
        """Test that duplicate hands are automatically removed."""
        # Create notation that would generate duplicates
        range_obj = HandRange.from_shorthand("AKs,AKs,QQ,QQ")

        # Should only have 2 unique hand types despite duplicate notation
        assert range_obj.size() == 2

        # Should contain both AKs and QQ
        aks_hand = Hand.from_strings("As", "Ks")
        qq_hand = Hand.from_strings("Qs", "Qh")
        assert range_obj.contains(aks_hand)
        assert range_obj.contains(qq_hand)

    def test_edge_cases(self):
        """Test edge cases in range parsing."""
        # Single card range (should work)
        single_range = HandRange.from_shorthand("AA")
        assert single_range.size() == 1

        # Range with same start/end
        same_range = HandRange.from_shorthand("AKs-AKs")
        assert same_range.size() == 1

        # Complex mixed notation
        mixed_range = HandRange.from_shorthand("AKs+,22+,A5s-A2s,TT,QQ+")
        assert mixed_range.size() > 5  # Should have multiple hand types