"""
Test suite for Jackpot Detection Rules (JACKPOT-001).

Validates that jackpot qualification rules are properly defined and testable.

PHASE 2: P1 - CRITICAL
- Validates jackpot rule definitions
- Tests rule consistency and completeness
- Ensures platform compatibility
"""

import pytest
from specs.jackpot_detection_rules import (
    JACKPOT_RULES,
    JACKPOT_PRIORITY_ORDER,
    PLATFORM_RULES
)


class TestJackpotRules:
    """Test suite for jackpot detection rule definitions."""

    def test_all_jackpot_types_defined(self):
        """Test that all expected jackpot types are defined."""
        expected_types = [
            'royal_flush', 'straight_flush', 'four_of_a_kind',
            'full_house', 'flush', 'straight', 'three_of_a_kind',
            'two_pair', 'one_pair', 'high_card'
        ]

        for jackpot_type in expected_types:
            assert jackpot_type in JACKPOT_RULES, f"Missing jackpot type: {jackpot_type}"

    def test_jackpot_rules_structure(self):
        """Test that all jackpot rules have required fields."""
        required_fields = [
            'description', 'qualifying_ranks', 'suit_requirement',
            'card_count', 'board_requirement', 'examples', 'payout_multiplier'
        ]

        for jackpot_type, rules in JACKPOT_RULES.items():
            for field in required_fields:
                assert field in rules, f"Jackpot {jackpot_type} missing field: {field}"

    def test_jackpot_priority_order(self):
        """Test that priority order contains all jackpot types."""
        assert len(JACKPOT_PRIORITY_ORDER) == len(JACKPOT_RULES)

        for jackpot_type in JACKPOT_RULES.keys():
            assert jackpot_type in JACKPOT_PRIORITY_ORDER, f"Priority order missing: {jackpot_type}"

    def test_royal_flush_rules(self):
        """Test royal flush specific rules."""
        rules = JACKPOT_RULES['royal_flush']

        assert rules['payout_multiplier'] == 500
        assert rules['card_count'] == 5
        assert rules['suit_requirement'] == 'all_same'
        assert len(rules['qualifying_ranks']) == 5
        assert 'A' in rules['qualifying_ranks']
        assert 'T' in rules['qualifying_ranks']

        # Test examples
        assert len(rules['examples']) >= 2
        for example in rules['examples']:
            assert len(example) == 5
            # Check all same suit
            suit = example[0][1]
            assert all(card[1] == suit for card in example)

    def test_straight_flush_rules(self):
        """Test straight flush specific rules."""
        rules = JACKPOT_RULES['straight_flush']

        assert rules['payout_multiplier'] == 100
        assert rules['card_count'] == 5
        assert rules['suit_requirement'] == 'all_same'
        assert rules['qualifying_ranks'] == 'consecutive'

        # Test examples
        assert len(rules['examples']) >= 3
        for example in rules['examples']:
            assert len(example) == 5
            # Check all same suit
            suit = example[0][1]
            assert all(card[1] == suit for card in example)

    def test_four_of_a_kind_rules(self):
        """Test four of a kind specific rules."""
        rules = JACKPOT_RULES['four_of_a_kind']

        assert rules['payout_multiplier'] == 50
        assert rules['card_count'] == 4
        assert rules['suit_requirement'] == 'any'
        assert rules['qualifying_ranks'] == 'quads'

        # Test examples
        for example in rules['examples']:
            assert len(example) == 4
            # Check all same rank
            rank = example[0][0]
            assert all(card[0] == rank for card in example)
            # Check all different suits
            suits = [card[1] for card in example]
            assert len(set(suits)) == 4

    def test_full_house_rules(self):
        """Test full house specific rules."""
        rules = JACKPOT_RULES['full_house']

        assert rules['payout_multiplier'] == 10
        assert rules['card_count'] == 5
        assert rules['suit_requirement'] == 'any'
        assert rules['qualifying_ranks'] == 'trips_plus_pair'

        # Test examples
        for example in rules['examples']:
            assert len(example) == 5
            ranks = [card[0] for card in example]
            rank_counts = {}
            for rank in ranks:
                rank_counts[rank] = rank_counts.get(rank, 0) + 1

            # Should have one rank with 3 cards, one with 2 cards
            assert 3 in rank_counts.values()
            assert 2 in rank_counts.values()

    def test_flush_rules(self):
        """Test flush specific rules."""
        rules = JACKPOT_RULES['flush']

        assert rules['payout_multiplier'] == 5
        assert rules['card_count'] == 5
        assert rules['suit_requirement'] == 'all_same'

        # Test examples
        for example in rules['examples']:
            assert len(example) == 5
            # Check all same suit
            suit = example[0][1]
            assert all(card[1] == suit for card in example)

    def test_straight_rules(self):
        """Test straight specific rules."""
        rules = JACKPOT_RULES['straight']

        assert rules['payout_multiplier'] == 4
        assert rules['card_count'] == 5
        assert rules['suit_requirement'] == 'mixed'
        assert rules['qualifying_ranks'] == 'consecutive'

    def test_payout_multipliers_unique(self):
        """Test that payout multipliers are unique and decrease properly."""
        multipliers = {}
        for jackpot_type, rules in JACKPOT_RULES.items():
            multiplier = rules['payout_multiplier']
            assert multiplier not in multipliers, f"Duplicate multiplier {multiplier}"
            multipliers[jackpot_type] = multiplier

        # Check that multipliers decrease in priority order
        for i in range(len(JACKPOT_PRIORITY_ORDER) - 1):
            current_type = JACKPOT_PRIORITY_ORDER[i]
            next_type = JACKPOT_PRIORITY_ORDER[i + 1]
            current_mult = multipliers[current_type]
            next_mult = multipliers[next_type]
            assert current_mult >= next_mult, f"Priority order wrong: {current_type}({current_mult}) < {next_type}({next_mult})"

    def test_platform_rules_defined(self):
        """Test that platform-specific rules are defined."""
        expected_platforms = ['ggpoker', 'pokerstars']

        for platform in expected_platforms:
            assert platform in PLATFORM_RULES, f"Missing platform: {platform}"

        for platform, rules in PLATFORM_RULES.items():
            required_fields = ['name', 'jackpot_enabled', 'special_rules']
            for field in required_fields:
                assert field in rules, f"Platform {platform} missing field: {field}"

    def test_card_format_validation(self):
        """Test that all card examples follow proper format."""
        def is_valid_card(card):
            if len(card) != 2:
                return False
            rank, suit = card[0], card[1]
            valid_ranks = 'A23456789TJQK'
            valid_suits = 'shcd'  # spades, hearts, clubs, diamonds
            return rank in valid_ranks and suit in valid_suits

        for jackpot_type, rules in JACKPOT_RULES.items():
            if 'examples' in rules:
                for example in rules['examples']:
                    for card in example:
                        assert is_valid_card(card), f"Invalid card format in {jackpot_type}: {card}"

    def test_no_duplicate_examples(self):
        """Test that examples are not duplicated across jackpot types."""
        all_examples = set()

        for jackpot_type, rules in JACKPOT_RULES.items():
            if 'examples' in rules:
                for example in rules['examples']:
                    # Convert to tuple for hashing
                    example_tuple = tuple(sorted(example))
                    assert example_tuple not in all_examples, f"Duplicate example in {jackpot_type}: {example}"
                    all_examples.add(example_tuple)

    def test_rule_completeness(self):
        """Test that all rules have sufficient detail for implementation."""
        for jackpot_type, rules in JACKPOT_RULES.items():
            # Every rule should have a clear description
            assert len(rules['description']) > 10, f"Description too short for {jackpot_type}"

            # Every rule should have examples
            assert len(rules['examples']) > 0, f"No examples for {jackpot_type}"

            # Payout multiplier should be reasonable
            assert rules['payout_multiplier'] >= 0, f"Invalid multiplier for {jackpot_type}"
            assert rules['payout_multiplier'] <= 500, f"Multiplier too high for {jackpot_type}"