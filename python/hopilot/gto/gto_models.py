"""
GTO Models for All-In-or-Fold Poker Analysis

This module defines Pydantic models for GTO analysis parameters and results.
"""

from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from hopilot.logging_config import get_logger

logger = get_logger(__name__)


class BonusPayouts(BaseModel):
    """Configuration for bonus payouts on special hands."""
    royal_flush: float = 500.0
    straight_flush: float = 100.0
    four_of_a_kind: float = 50.0
    full_house: float = 10.0
    flush: float = 5.0
    straight: float = 4.0
    three_of_a_kind: float = 3.0
    two_pair: float = 2.0
    one_pair: float = 1.0

    def get_multiplier(self, hand_category: str) -> float:
        """Get bonus multiplier for a hand category."""
        return getattr(self, hand_category, 0.0)


class GTOParameters(BaseModel):
    """Parameters for GTO analysis calculations."""
    num_opponents: int = Field(ge=1, le=9)  # 1-9 opponents
    pot_size: float = Field(gt=0)  # Current pot size
    bet_amount: float = Field(gt=0)  # All-in bet amount
    num_simulations: int = Field(ge=100, le=10000)  # Monte Carlo samples
    bonus_payouts: BonusPayouts = Field(default_factory=BonusPayouts)
    random_seed: Optional[int] = None  # For reproducible results


class GTOHandResult(BaseModel):
    """Result for a single hand in GTO analysis."""
    hand: List[str]  # The hole cards
    shorthand: str   # Shorthand notation
    equity: float    # Win probability vs random
    ev: float        # Expected value including bonuses
    hand_category: str  # Best hand category achieved
    bonus_multiplier: float  # Applied bonus multiplier


class GTOResult(BaseModel):
    """Complete GTO analysis result."""
    parameters: GTOParameters
    threshold_equity: float  # Minimum equity for profitable all-in
    optimal_hands: int       # Number of hands that should be played
    total_hands: int         # Total hands analyzed
    optimal_range: List[str] # List of optimal hand shorthands
    hand_results: List[GTOHandResult]
    calculation_time: float  # Time taken in seconds
    valid_simulations: int   # Total simulations run


class NashEquilibriumResult(BaseModel):
    """Result of push-fold Nash equilibrium calculation for range vs range optimization."""
    hero_range_name: str      # Name of hero range
    villain_range_name: str   # Name of villain range
    hero_shove_frequencies: Dict[str, float]    # Hand -> shove frequency (0.0-1.0)
    villain_call_frequencies: Dict[str, float]  # Hand -> call frequency (0.0-1.0)
    hero_ev: float             # Expected value for hero in equilibrium
    villain_ev: float          # Expected value for villain in equilibrium (should be 0)
    exploitability: float      # How far from true Nash (0 = perfect Nash)
    convergence_iterations: int # Iterations needed for convergence
    calculation_time: float    # Time taken in seconds