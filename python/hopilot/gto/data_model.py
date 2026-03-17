"""
Data model entities for the GTO browser.

Defines the conceptual entities used by the browser interface,
which are mapped to database queries by the repository layer.
"""

from dataclasses import dataclass
from typing import Literal, Optional
from datetime import datetime


@dataclass(frozen=True)
class PositionContext:
    """Represents a poker position context for GTO browsing."""
    id: Literal["UTG", "BTN", "SB", "BB"]
    label: str
    sort_order: int

    @classmethod
    def UTG(cls) -> 'PositionContext':
        return cls(id="UTG", label="Under the Gun", sort_order=1)

    @classmethod
    def BTN(cls) -> 'PositionContext':
        return cls(id="BTN", label="Button", sort_order=2)

    @classmethod
    def SB(cls) -> 'PositionContext':
        return cls(id="SB", label="Small Blind", sort_order=3)

    @classmethod
    def BB(cls) -> 'PositionContext':
        return cls(id="BB", label="Big Blind", sort_order=4)

    @classmethod
    def from_id(cls, position_id: str) -> 'PositionContext':
        """Create PositionContext from position ID string."""
        mapping = {
            "UTG": cls.UTG(),
            "BTN": cls.BTN(),
            "SB": cls.SB(),
            "BB": cls.BB()
        }
        if position_id not in mapping:
            raise ValueError(f"Unsupported position: {position_id}")
        return mapping[position_id]


@dataclass(frozen=True)
class ActionContext:
    """Represents an action context for GTO browsing."""
    id: Literal["FOLD", "ALL_IN"]
    label: str

    @classmethod
    def FOLD(cls) -> 'ActionContext':
        return cls(id="FOLD", label="Fold")

    @classmethod
    def ALL_IN(cls) -> 'ActionContext':
        return cls(id="ALL_IN", label="All-In")

    @classmethod
    def from_id(cls, action_id: str) -> 'ActionContext':
        """Create ActionContext from action ID string."""
        mapping = {
            "FOLD": cls.FOLD(),
            "ALL_IN": cls.ALL_IN()
        }
        if action_id not in mapping:
            raise ValueError(f"Unsupported action: {action_id}")
        return mapping[action_id]


@dataclass(frozen=True)
class MetricType:
    """Represents a metric type for GTO browsing."""
    id: Literal["WIN_LOSE_PROBABILITY", "EV", "EQUITY", "EQR"]
    label: str

    @classmethod
    def WIN_LOSE_PROBABILITY(cls) -> 'MetricType':
        return cls(id="WIN_LOSE_PROBABILITY", label="Win Probability")

    @classmethod
    def EV(cls) -> 'MetricType':
        return cls(id="EV", label="Expected Value")

    @classmethod
    def EQUITY(cls) -> 'MetricType':
        return cls(id="EQUITY", label="Equity")

    @classmethod
    def EQR(cls) -> 'MetricType':
        return cls(id="EQR", label="EV Ratio")

    @classmethod
    def from_id(cls, metric_id: str) -> 'MetricType':
        """Create MetricType from metric ID string."""
        mapping = {
            "WIN_LOSE_PROBABILITY": cls.WIN_LOSE_PROBABILITY(),
            "EV": cls.EV(),
            "EQUITY": cls.EQUITY(),
            "EQR": cls.EQR()
        }
        if metric_id not in mapping:
            raise ValueError(f"Unsupported metric: {metric_id}")
        return mapping[metric_id]


@dataclass(frozen=True)
class ConvergencePoint:
    """Represents a single point in convergence analysis."""
    num_simulations: int
    average_equity: float
    timestamp: Optional[datetime] = None

    @classmethod
    def from_simulations(cls, num_simulations: int, average_equity: float, timestamp: Optional[datetime] = None) -> 'ConvergencePoint':
        return cls(num_simulations=num_simulations, average_equity=average_equity, timestamp=timestamp)


@dataclass(frozen=True)
class JackpotStats:
    """Statistics for jackpot events in simulations."""
    jackpot_type: str
    frequency: int
    avg_payout: float
    total_payout: float
    hand_key: str | None = None  # Specific hand that triggered jackpots, if applicable


@dataclass(frozen=True)
class StrategyCellMetricValue:
    """Represents a single cell value in the GTO strategy matrix."""
    hand_key: str
    value: float | None
    status: Literal["AVAILABLE", "COMPUTING", "MISSING", "INVALID"]

    @classmethod
    def available(cls, hand_key: str, value: float) -> 'StrategyCellMetricValue':
        return cls(hand_key=hand_key, value=value, status="AVAILABLE")

    @classmethod
    def computing(cls, hand_key: str) -> 'StrategyCellMetricValue':
        return cls(hand_key=hand_key, value=None, status="COMPUTING")

    @classmethod
    def missing(cls, hand_key: str) -> 'StrategyCellMetricValue':
        return cls(hand_key=hand_key, value=None, status="MISSING")

    @classmethod
    def invalid(cls, hand_key: str) -> 'StrategyCellMetricValue':
        return cls(hand_key=hand_key, value=None, status="INVALID")