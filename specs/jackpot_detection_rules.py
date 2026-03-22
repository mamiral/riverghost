"""
Jackpot Detection Rules Specification

This document defines the exact qualification rules for different jackpot types
in poker analysis systems. These rules determine when jackpot events are triggered
during hand evaluation and what payout multipliers apply.

PHASE 2: P1 - CRITICAL
- Defines exact qualification rules for jackpot detection
- Provides testable specifications for implementation
- Ensures consistency with target poker platform rules
"""

# ============================================================================
# JACKPOT QUALIFICATION RULES
# ============================================================================

JACKPOT_RULES = {
    # ============================================================================
    # ROYAL FLUSH (500x multiplier)
    # ============================================================================
    'royal_flush': {
        'description': 'Ace-high straight flush in the same suit',
        'qualifying_ranks': ['A', 'K', 'Q', 'J', 'T'],
        'suit_requirement': 'all_same',
        'card_count': 5,
        'board_requirement': 'flush_possible',
        'examples': [
            ['As', 'Ks', 'Qs', 'Js', 'Ts'],  # Royal flush spades
            ['Ah', 'Kh', 'Qh', 'Jh', 'Th'],  # Royal flush hearts
        ],
        'payout_multiplier': 500,
        'platform_notes': 'Highest value jackpot, requires all royal cards in same suit'
    },

    # ============================================================================
    # STRAIGHT FLUSH (100x multiplier)
    # ============================================================================
    'straight_flush': {
        'description': 'Five consecutive cards of the same suit (not royal)',
        'qualifying_ranks': 'consecutive',
        'suit_requirement': 'all_same',
        'card_count': 5,
        'board_requirement': 'flush_possible',
        'examples': [
            ['9s', '8s', '7s', '6s', '5s'],  # Steel wheel (wheel straight flush)
            ['Kd', 'Qd', 'Jd', 'Td', '9d'],  # Broadway straight flush
            ['7c', '6c', '5c', '4c', '3c'],  # Baby straight flush
        ],
        'invalid_examples': [
            ['As', 'Ks', 'Qs', 'Js', 'Ts'],  # Royal flush (higher priority)
            ['Ah', '2h', '3h', '4h', '5h'],  # Wheel with ace (counts as A-2-3-4-5)
        ],
        'payout_multiplier': 100,
        'platform_notes': 'Second highest jackpot, consecutive suited cards'
    },

    # ============================================================================
    # FOUR OF A KIND (50x multiplier)
    # ============================================================================
    'four_of_a_kind': {
        'description': 'Four cards of the same rank',
        'qualifying_ranks': 'quads',
        'suit_requirement': 'any',
        'card_count': 4,
        'board_requirement': 'quads_possible',
        'examples': [
            ['As', 'Ad', 'Ac', 'Ah'],  # Quad aces
            ['7s', '7d', '7c', '7h'],  # Quad sevens
            ['2s', '2d', '2c', '2h'],  # Quad deuces
        ],
        'payout_multiplier': 50,
        'platform_notes': 'Requires all four suits of same rank'
    },

    # ============================================================================
    # FULL HOUSE (10x multiplier)
    # ============================================================================
    'full_house': {
        'description': 'Three of a kind plus a pair',
        'qualifying_ranks': 'trips_plus_pair',
        'suit_requirement': 'any',
        'card_count': 5,
        'board_requirement': 'full_house_possible',
        'examples': [
            ['As', 'Ad', 'Ac', 'Kh', 'Kd'],  # Aces full of kings
            ['Qs', 'Qd', 'Qc', 'Jh', 'Jd'],  # Queens full of jacks
            ['7s', '7d', '7c', '2h', '2d'],  # Sevens full of deuces
        ],
        'payout_multiplier': 10,
        'platform_notes': 'Three cards same rank + two cards same rank'
    },

    # ============================================================================
    # FLUSH (5x multiplier)
    # ============================================================================
    'flush': {
        'description': 'Five cards of the same suit',
        'qualifying_ranks': 'any',
        'suit_requirement': 'all_same',
        'card_count': 5,
        'board_requirement': 'flush_possible',
        'examples': [
            ['As', 'Ks', 'Qs', 'Js', '9s'],  # Spade flush
            ['Ah', 'Qh', '8h', '7h', '3h'],  # Heart flush
            ['Kd', 'Jd', 'Td', '8d', '5d'],  # Diamond flush
        ],
        'payout_multiplier': 5,
        'platform_notes': 'All five cards same suit, any ranks'
    },

    # ============================================================================
    # STRAIGHT (4x multiplier)
    # ============================================================================
    'straight': {
        'description': 'Five consecutive cards of mixed suits',
        'qualifying_ranks': 'consecutive',
        'suit_requirement': 'mixed',
        'card_count': 5,
        'board_requirement': 'straight_possible',
        'examples': [
            ['As', 'Kh', 'Qd', 'Jc', 'Ts'],  # Broadway straight
            ['9s', '8h', '7d', '6c', '5s'],  # Regular straight
            ['5c', '4d', '3h', '2s', 'Ah'],  # Wheel (A-2-3-4-5)
        ],
        'invalid_examples': [
            ['As', 'Ks', 'Qs', 'Js', 'Ts'],  # Royal flush (higher priority)
            ['9s', '8s', '7s', '6s', '5s'],  # Straight flush (higher priority)
        ],
        'payout_multiplier': 4,
        'platform_notes': 'Consecutive ranks, mixed suits'
    },

    # ============================================================================
    # THREE OF A KIND (3x multiplier)
    # ============================================================================
    'three_of_a_kind': {
        'description': 'Three cards of the same rank',
        'qualifying_ranks': 'trips',
        'suit_requirement': 'any',
        'card_count': 3,
        'board_requirement': 'trips_possible',
        'examples': [
            ['As', 'Ad', 'Ac'],  # Three aces
            ['Ks', 'Kh', 'Kd'],  # Three kings
            ['2s', '2h', '2d'],  # Three deuces
        ],
        'payout_multiplier': 3,
        'platform_notes': 'Exactly three cards of same rank'
    },

    # ============================================================================
    # TWO PAIR (2x multiplier)
    # ============================================================================
    'two_pair': {
        'description': 'Two different pairs',
        'qualifying_ranks': 'two_pairs',
        'suit_requirement': 'any',
        'card_count': 4,
        'board_requirement': 'two_pair_possible',
        'examples': [
            ['As', 'Ad', 'Ks', 'Kh'],  # Aces and kings
            ['Qs', 'Qh', 'Js', 'Jd'],  # Queens and jacks
            ['7s', '7d', '2h', '2c'],  # Sevens and deuces
        ],
        'payout_multiplier': 2,
        'platform_notes': 'Two different ranks, each with exactly two cards'
    },

    # ============================================================================
    # ONE PAIR (1x multiplier)
    # ============================================================================
    'one_pair': {
        'description': 'Two cards of the same rank',
        'qualifying_ranks': 'pair',
        'suit_requirement': 'any',
        'card_count': 2,
        'board_requirement': 'pair_possible',
        'examples': [
            ['As', 'Ad'],  # Pair of aces
            ['Ks', 'Kh'],  # Pair of kings
            ['2s', '2h'],  # Pair of deuces
        ],
        'payout_multiplier': 1,
        'platform_notes': 'Exactly two cards of same rank'
    },

    # ============================================================================
    # HIGH CARD (0x multiplier - no jackpot)
    # ============================================================================
    'high_card': {
        'description': 'No qualifying hand - highest card wins',
        'qualifying_ranks': 'highest',
        'suit_requirement': 'any',
        'card_count': 1,
        'board_requirement': 'always',
        'examples': [
            ['As'],  # Ace high
            ['Ks'],  # King high
            ['Qs'],  # Queen high
        ],
        'payout_multiplier': 0,
        'platform_notes': 'No jackpot payout for high card hands'
    }
}

# ============================================================================
# DETECTION PRIORITY ORDER
# ============================================================================

"""
Jackpot detection priority (highest to lowest):

1. royal_flush (500x) - Most valuable
2. straight_flush (100x) - Second most valuable
3. four_of_a_kind (50x) - Quads
4. full_house (10x) - Boat
5. flush (5x) - Suit match
6. straight (4x) - Rank sequence
7. three_of_a_kind (3x) - Trips
8. two_pair (2x) - Two pairs
9. one_pair (1x) - Single pair
10. high_card (0x) - No jackpot

Only the highest qualifying jackpot is awarded per hand.
Multiple jackpots cannot be awarded for the same card combination.
"""

JACKPOT_PRIORITY_ORDER = [
    'royal_flush',
    'straight_flush',
    'four_of_a_kind',
    'full_house',
    'flush',
    'straight',
    'three_of_a_kind',
    'two_pair',
    'one_pair',
    'high_card'
]

# ============================================================================
# PLATFORM SPECIFIC RULES
# ============================================================================

PLATFORM_RULES = {
    'ggpoker': {
        'name': 'GGPoker',
        'jackpot_enabled': True,
        'board_cards_required': True,
        'hole_cards_required': True,
        'evaluation_timing': 'after_river',
        'payout_calculation': 'multiplier_times_pot',
        'max_jackpot_per_hand': 1,
        'special_rules': [
            'Royal flush requires all 5 cards (no 4-card royals)',
            'Straight flush beats regular straight',
            'Flush beats straight of same ranks',
            'Wheel (A-2-3-4-5) counts as straight',
            'Suit breaking only matters for flushes'
        ]
    },

    'pokerstars': {
        'name': 'PokerStars',
        'jackpot_enabled': True,
        'board_cards_required': True,
        'hole_cards_required': True,
        'evaluation_timing': 'after_river',
        'payout_calculation': 'multiplier_times_pot',
        'max_jackpot_per_hand': 1,
        'special_rules': [
            'Similar to GGPoker rules',
            'May have different multiplier values',
            'Platform-specific jackpot promotions possible'
        ]
    }
}

# ============================================================================
# DETECTION ALGORITHM REQUIREMENTS
# ============================================================================

"""
For implementation, the jackpot detection algorithm must:

1. Evaluate hands only after all board cards are dealt (river)
2. Check for jackpots in priority order (highest first)
3. Stop at first qualifying jackpot found
4. Record qualifying cards that formed the jackpot
5. Calculate payout as: pot_size * multiplier
6. Handle platform-specific rules and multipliers
7. Support custom jackpot types for future features

Input: Player hole cards + board cards (7 total)
Output: Jackpot type, qualifying cards, payout amount
"""

# ============================================================================
# TESTING REQUIREMENTS
# ============================================================================

"""
Each jackpot type must have comprehensive test cases covering:

1. Valid qualifying combinations
2. Invalid combinations (edge cases)
3. Priority ordering (higher jackpots take precedence)
4. Platform-specific rule variations
5. Payout calculation accuracy
6. Qualifying card identification
7. Boundary conditions (min/max cards, etc.)

Test coverage target: >95% of jackpot detection logic
"""