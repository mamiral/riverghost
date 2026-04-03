# AOF GTO Browser II - Input Context DTOs
#
# Data Transfer Objects for frontend → backend communication.
# These define the contract for analysis requests.
#
# FR-006: PositionContext - describes poker position and context
# FR-007: ActionContext - specifies action in position context
# FR-008: AnalysisRequest - complete analysis request (CRITICAL)

from dataclasses import dataclass
from typing import Optional
from .enums import Position, Action, MetricType
from aof_gto_browser_ii.shared.domain.hand import Hand  # Phase 1.1 domain model
from aof_gto_browser_ii.shared.domain.hand_range import HandRange  # Phase 1.1 domain model


@dataclass(frozen=True)
class PositionContext:
    """Complete description of a poker position for analysis.

    Defines the position, opponent count, and optional hero hand for analysis.
    Used as the foundation for all analysis requests.

    FR-006: PositionContext with position, num_opponents, heroes_hole_cards, pot_size_bb
    """

    position: Position
    num_opponents: int
    heroes_hole_cards: Optional[Hand] = None
    pot_size_bb: float = 1.0

    def __post_init__(self):
        """Validate PositionContext fields."""
        # FR-015: Raise ValueError with descriptive messages
        if not isinstance(self.position, Position):
            raise ValueError(f"position must be Position enum, got {type(self.position)}")

        if self.num_opponents < 1 or self.num_opponents > 3:
            raise ValueError(f"num_opponents must be 1-3 (4 max players), got {self.num_opponents}")

        if self.pot_size_bb <= 0:
            raise ValueError(f"pot_size_bb must be positive, got {self.pot_size_bb}")

        if self.heroes_hole_cards and not isinstance(self.heroes_hole_cards, Hand):
            raise ValueError(f"heroes_hole_cards must be Hand domain model, got {type(self.heroes_hole_cards)}")


@dataclass(frozen=True)
class ActionContext:
    """Specifies an action taken in a position context.

    Combines a position context with a specific action (fold or all-in).
    Used for analyzing specific decision points.

    FR-007: ActionContext with position_context and action
    """

    position_context: PositionContext
    action: Action

    def __post_init__(self):
        """Validate ActionContext fields."""
        if not isinstance(self.position_context, PositionContext):
            raise ValueError("position_context must be PositionContext")

        if not isinstance(self.action, Action):
            raise ValueError("action must be Action enum")

        # FR-007: action must be valid for all-in/fold context
        if self.action not in (Action.FOLD, Action.ALL_IN):
            raise ValueError(f"All-in/fold allows only FOLD or ALL_IN, got {self.action}")

    @property
    def is_aggressive(self) -> bool:
        """Returns True if action is ALL_IN, False if FOLD."""
        return self.action == Action.ALL_IN


@dataclass(frozen=True)
class AnalysisRequest:
    """Complete analysis request: combines position context with analysis parameters.

    This is the PRIMARY REQUEST CONTRACT between frontend and backend.
    It encapsulates everything needed for backend to execute analysis.

    FR-008 (CRITICAL): AnalysisRequest with position_context, opponent_range, metric_type, precompute, session_id
    FR-021: session_id for request correlation and session management

    Examples:
        # Basic equity analysis
        request = AnalysisRequest(
            position_context=PositionContext(position=Position.BTN, num_opponents=1)
        )

        # Advanced analysis with custom range
        request = AnalysisRequest(
            position_context=PositionContext(
                position=Position.UTG,
                num_opponents=2,
                pot_size_bb=15.0
            ),
            opponent_range=HandRange.from_shorthand("22+,AKs,AQo"),
            metric_type=MetricType.EV,
            precompute=True,
            session_id="session_001"
        )
    """

    position_context: PositionContext
    opponent_range: Optional[HandRange] = None
    metric_type: MetricType = MetricType.EQUITY
    precompute: bool = False
    session_id: Optional[str] = None

    def __post_init__(self):
        """Validate AnalysisRequest fields."""
        # FR-016: Include actual vs expected values in error messages
        if not isinstance(self.position_context, PositionContext):
            raise ValueError(f"position_context must be PositionContext, got {type(self.position_context)}")

        if self.opponent_range and not isinstance(self.opponent_range, HandRange):
            raise ValueError(f"opponent_range must be HandRange domain model, got {type(self.opponent_range)}")

        if not isinstance(self.metric_type, MetricType):
            raise ValueError(f"metric_type must be MetricType enum, got {type(self.metric_type)}")

        if not isinstance(self.precompute, bool):
            raise ValueError(f"precompute must be bool, got {type(self.precompute)}")

        if self.session_id is not None:
            if not isinstance(self.session_id, str):
                raise ValueError(f"session_id must be string, got {type(self.session_id)}")
            if len(self.session_id) == 0:
                raise ValueError("session_id must be non-empty string if provided")

    @property
    def is_heads_up(self) -> bool:
        """Returns True if heads-up (1 opponent)."""
        return self.position_context.num_opponents == 1

    @property
    def is_partial_request(self) -> bool:
        """Returns True if only computing for hero's specific hand (not full matrix)."""
        return self.position_context.heroes_hole_cards is not None

    @property
    def is_precompute_requested(self) -> bool:
        """Returns True if full matrix precomputation requested."""
        return self.precompute

    @property
    def effective_opponent_range(self) -> HandRange:
        """Returns opponent range, defaulting to all hands if not specified."""
        return self.opponent_range if self.opponent_range else HandRange.from_shorthand("*")

    def with_opponent_range(self, range_shorthand: str) -> 'AnalysisRequest':
        """Create a new request with specified opponent range (functional style)."""
        new_range = HandRange.from_shorthand(range_shorthand)
        return AnalysisRequest(
            position_context=self.position_context,
            opponent_range=new_range,
            metric_type=self.metric_type,
            precompute=self.precompute,
            session_id=self.session_id
        )

    def with_metric_type(self, metric: MetricType) -> 'AnalysisRequest':
        """Create a new request with different metric type."""
        return AnalysisRequest(
            position_context=self.position_context,
            opponent_range=self.opponent_range,
            metric_type=metric,
            precompute=self.precompute,
            session_id=self.session_id
        )