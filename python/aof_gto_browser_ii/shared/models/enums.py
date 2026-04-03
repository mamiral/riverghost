# AOF GTO Browser II - Shared Model Enumerations
#
# Type-safe enumerations for poker analysis. All enums inherit from str
# for direct JSON serialization and display formatting.
#
# FR-001: Position enum with 4 members (UTG, BTN, SB, BB)
# FR-002: Action enum with 2 members (FOLD, ALL_IN)
# FR-003: MetricType enum with 4 members (EQUITY, EV, EQR, WIN_LOSE_PROBABILITY)
# FR-004: Support creation by name, value, and attribute
# FR-005: String inheritance for serialization

from enum import Enum


class Position(str, Enum):
    """Poker table position (4-max all-in/fold game).

    Positions are ordered from earliest to latest action:
    - UTG: Under the gun (first to act pre-flop)
    - BTN: Button (best position post-flop)
    - SB: Small blind
    - BB: Big blind
    """
    UTG = "utg"
    BTN = "btn"
    SB = "sb"
    BB = "bb"


class Action(str, Enum):
    """All-in/fold action (binary decision).

    Only two actions are supported in the MVP:
    - FOLD: Don't play the hand
    - ALL_IN: Commit all remaining chips
    """
    FOLD = "fold"
    ALL_IN = "all_in"


class MetricType(str, Enum):
    """Analysis metric for display and computation.

    Metrics align with Phase 1.1 EquityResult fields:
    - EQUITY: Pot equity percentage (0.0-1.0)
    - EV: Expected value in dollars (can be negative)
    - EQR: Equity to risk ratio (0.0 to ∞)
    - WIN_LOSE_PROBABILITY: Win vs lose probability (-1.0 to 1.0)
    """
    EQUITY = "equity"
    EV = "ev"
    EQR = "eqr"
    WIN_LOSE_PROBABILITY = "win_lose_probability"