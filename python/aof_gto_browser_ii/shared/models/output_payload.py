# AOF GTO Browser II - Output Payload DTOs
#
# Backend → Frontend contract for analysis results.
# All classes are immutable (frozen=True) and thread-safe.
#
# Exports:
#   - HandEvaluation - Single hand evaluation results
#   - MatrixPayload - Complete analysis matrix (169 hands)
#   - CellDisplay - Rendering-ready display data
#   - PrecomputeProgress - Progress tracking for long computations

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
from aof_gto_browser_ii.shared.models.input_context import PositionContext
from aof_gto_browser_ii.shared.models.enums import MetricType
from aof_gto_browser_ii.shared.domain.hand_range import HandRange


@dataclass(frozen=True)
class HandEvaluation:
    """Single hand evaluation results from Monte Carlo simulation.

    Contains all metrics for one poker hand's performance against an opponent range.
    Used as values in MatrixPayload.cells dictionary (hand key is the dict key).

    FR-009: HandEvaluation with equity, EV, probabilities, and simulation metadata.
    """

    equity: float
    equity_std: float = 0.0
    ev: float = 0.0
    win_probability: float = 0.0
    tie_probability: float = 0.0
    lose_probability: float = 0.0
    win_money: float = 0.0
    lose_money: float = 0.0
    num_simulations: int = 0
    is_computed: bool = True

    def __post_init__(self):
        """Validate HandEvaluation fields."""
        # FR-016: Include actual vs expected values in error messages

        # Equity validation (0.0-1.0)
        if not (0.0 <= self.equity <= 1.0):
            raise ValueError(f"equity must be 0.0-1.0, got {self.equity}")

        # Equity standard deviation validation (>= 0)
        if self.equity_std < 0:
            raise ValueError(f"equity_std must be >= 0, got {self.equity_std}")

        # Probability validations (0.0-1.0)
        for prob_name, prob_value in [
            ("win_probability", self.win_probability),
            ("tie_probability", self.tie_probability),
            ("lose_probability", self.lose_probability)
        ]:
            if not (0.0 <= prob_value <= 1.0):
                raise ValueError(f"{prob_name} must be 0.0-1.0, got {prob_value}")

        # Money validations (>= 0)
        if self.win_money < 0:
            raise ValueError(f"win_money must be >= 0, got {self.win_money}")
        if self.lose_money < 0:
            raise ValueError(f"lose_money must be >= 0, got {self.lose_money}")

        # Simulation count validation
        if self.is_computed and self.num_simulations < 0:
            raise ValueError(f"num_simulations must be >= 0 when is_computed=True, got {self.num_simulations}")
        if not self.is_computed and self.num_simulations < 0:
            raise ValueError(f"num_simulations must be >= 0 when is_computed=False, got {self.num_simulations}")


@dataclass(frozen=True)
class MatrixPayload:
    """Complete analysis results for all 169 poker hands.

    Contains evaluation results for every possible starting hand against an opponent range.
    Used as the primary response from backend analysis services.

    FR-010: MatrixPayload with cells dict, query context, and precomputed statistics
    FR-021: Hand keys use canonical poker notation (AA, AKs, AKo, etc.)

    The cells dict maps hand keys to HandEvaluation objects. All 169 canonical
    poker hands must be present (13 pairs + 78 suited + 78 unsuited combinations).

    Examples:
        # Access specific hand evaluation
        aa_eval = matrix.get_hand("AA")
        print(f"AA equity: {aa_eval.equity}")

        # Get all pairs
        pairs = matrix.get_hands_by_type("pairs")
        print(f"Found {len(pairs)} pair combinations")

        # Check if all hands computed
        if matrix.all_computed:
            print(f"Analysis complete: {matrix.total_simulations} simulations")
    """

    cells: Dict[str, HandEvaluation]
    query_context: PositionContext
    opponent_range: Optional[HandRange] = None
    metric_type: MetricType = MetricType.EQUITY
    average_equity: float = 0.0
    average_equity_pairs: float = 0.0
    average_equity_suited: float = 0.0
    average_equity_unsuited: float = 0.0
    median_equity: float = 0.0
    all_computed: bool = True
    total_simulations: int = 0
    computed_at: str = ""

    def __post_init__(self):
        """Validate MatrixPayload fields."""
        # FR-016: Include actual vs expected values in error messages

        # Must have exactly 169 hands
        expected_hands = self._generate_all_hand_keys()
        if len(self.cells) != 169:
            raise ValueError(f"Matrix must have 169 hands, got {len(self.cells)}")

        # Verify all expected hands present
        actual_hands = set(self.cells.keys())
        if actual_hands != expected_hands:
            missing = expected_hands - actual_hands
            extra = actual_hands - expected_hands
            error_msg = f"Matrix hand keys mismatch. "
            if missing:
                error_msg += f"Missing: {sorted(missing)[:5]}... "  # Show first 5
            if extra:
                error_msg += f"Extra: {sorted(extra)[:5]}... "  # Show first 5
            raise ValueError(error_msg)

        # All values are valid HandEvaluation objects
        for hand_key, evaluation in self.cells.items():
            if not isinstance(evaluation, HandEvaluation):
                raise ValueError(f"Cell {hand_key} must be HandEvaluation, got {type(evaluation)}")

        # Query context validation
        if not isinstance(self.query_context, PositionContext):
            raise ValueError(f"query_context must be PositionContext, got {type(self.query_context)}")

        # Opponent range validation
        if self.opponent_range is not None and not isinstance(self.opponent_range, HandRange):
            raise ValueError(f"opponent_range must be HandRange or None, got {type(self.opponent_range)}")

        # Metric type validation
        if not isinstance(self.metric_type, MetricType):
            raise ValueError(f"metric_type must be MetricType enum, got {type(self.metric_type)}")

        # Statistics validation (0.0-1.0 for equity values)
        for stat_name, stat_value in [
            ("average_equity", self.average_equity),
            ("average_equity_pairs", self.average_equity_pairs),
            ("average_equity_suited", self.average_equity_suited),
            ("average_equity_unsuited", self.average_equity_unsuited),
            ("median_equity", self.median_equity)
        ]:
            if not (0.0 <= stat_value <= 1.0):
                raise ValueError(f"{stat_name} must be 0.0-1.0, got {stat_value}")

        # Total simulations validation
        if self.total_simulations < 0:
            raise ValueError(f"total_simulations must be >= 0, got {self.total_simulations}")

        # Computed_at validation (should be ISO format if provided)
        if self.computed_at and not self._is_valid_iso_timestamp(self.computed_at):
            raise ValueError(f"computed_at must be valid ISO timestamp, got '{self.computed_at}'")

    @staticmethod
    def _generate_all_hand_keys() -> set[str]:
        """Generate all 169 poker hand keys in canonical FR-021 format."""
        hands = set()
        ranks = "AKQJT98765432"

        # Pairs: AA, KK, QQ, JJ, TT, 99, 88, 77, 66, 55, 44, 33, 22
        for rank in ranks:
            hands.add(f"{rank}{rank}")

        # Suited combinations: AKs, AQs, AJs, ..., 32s
        for i in range(len(ranks)):
            for j in range(i + 1, len(ranks)):
                high_rank = ranks[i]
                low_rank = ranks[j]
                hands.add(f"{high_rank}{low_rank}s")

        # Unsuited combinations: AKo, AQo, AJo, ..., 32o
        for i in range(len(ranks)):
            for j in range(i + 1, len(ranks)):
                high_rank = ranks[i]
                low_rank = ranks[j]
                hands.add(f"{high_rank}{low_rank}o")

        return hands

    @staticmethod
    def _is_valid_iso_timestamp(timestamp: str) -> bool:
        """Check if timestamp is valid ISO 8601 format."""
        try:
            from datetime import datetime
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return True
        except ValueError:
            return False

    def get_hand(self, hand_key: str) -> HandEvaluation:
        """Get evaluation for specific hand key.

        Args:
            hand_key: Hand key in FR-021 format (e.g., "AKs", "22")

        Returns:
            HandEvaluation for the requested hand

        Raises:
            KeyError: If hand_key not found in matrix
        """
        if hand_key not in self.cells:
            available_keys = sorted(list(self.cells.keys())[:5])  # Show first 5
            raise KeyError(f"Hand '{hand_key}' not found. Available: {available_keys}...")
        return self.cells[hand_key]

    def get_hands_by_type(self, hand_type: str) -> Dict[str, HandEvaluation]:
        """Get all hands of specified type.

        Args:
            hand_type: One of 'pairs', 'suited', 'unsuited'

        Returns:
            Dict mapping hand keys to evaluations

        Raises:
            ValueError: If hand_type not recognized
        """
        if hand_type not in ('pairs', 'suited', 'unsuited'):
            raise ValueError(f"hand_type must be 'pairs', 'suited', or 'unsuited', got '{hand_type}'")

        result = {}
        for hand_key, evaluation in self.cells.items():
            if len(hand_key) == 2:  # Pairs: "AA", "KK", etc.
                if hand_type == 'pairs':
                    result[hand_key] = evaluation
            elif hand_key.endswith('s'):  # Suited: "AKs", "AQs", etc.
                if hand_type == 'suited':
                    result[hand_key] = evaluation
            elif hand_key.endswith('o'):  # Unsuited: "AKo", "AQo", etc.
                if hand_type == 'unsuited':
                    result[hand_key] = evaluation

        return result


@dataclass(frozen=True)
class CellDisplay:
    """Rendering-ready data for displaying a poker hand cell in the UI.

    Contains all information needed to render a single cell in the poker matrix,
    including colors, text, and interaction state.

    FR-011: CellDisplay with rendering hints and display properties.
    """

    hand_key: str
    metric_value: float
    display_text: str
    background_color: tuple[int, int, int]
    text_color: tuple[int, int, int]
    border_color: tuple[int, int, int]
    is_computed: bool = True
    confidence: float = 1.0
    show_border: bool = False
    highlight_level: int = 0
    is_hovering: bool = False
    is_selected: bool = False
    opacity: float = 1.0
    tooltip_text: Optional[str] = None
    secondary_text: Optional[str] = None

    def __post_init__(self):
        """Validate CellDisplay fields."""
        # FR-016: Include actual vs expected values in error messages

        # Hand key validation (must be valid poker hand in FR-021 format)
        if not self._is_valid_hand_key(self.hand_key):
            raise ValueError(f"hand_key must be valid poker hand (FR-021 format), got '{self.hand_key}'")

        # Color validation (RGB tuples with components 0-255)
        for color_name, color_value in [
            ("background_color", self.background_color),
            ("text_color", self.text_color),
            ("border_color", self.border_color)
        ]:
            if not self._is_valid_rgb_tuple(color_value):
                raise ValueError(f"{color_name} must be RGB tuple with components 0-255, got {color_value}")

        # Confidence validation (0.0-1.0)
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

        # Highlight level validation (0-3)
        if not (0 <= self.highlight_level <= 3):
            raise ValueError(f"highlight_level must be 0-3, got {self.highlight_level}")

        # Opacity validation (0.0-1.0)
        if not (0.0 <= self.opacity <= 1.0):
            raise ValueError(f"opacity must be 0.0-1.0, got {self.opacity}")

    @staticmethod
    def _is_valid_hand_key(hand_key: str) -> bool:
        """Check if hand_key follows FR-021 canonical format."""
        if not hand_key or len(hand_key) < 2 or len(hand_key) > 3:
            return False

        # Check ranks are valid
        valid_ranks = set("AKQJT98765432")
        if len(hand_key) == 2:  # Pair: "AA", "KK", etc.
            return len(hand_key) == 2 and hand_key[0] == hand_key[1] and hand_key[0] in valid_ranks
        elif len(hand_key) == 3:  # Combo: "AKs", "AKo", etc.
            rank1, rank2, suit = hand_key[0], hand_key[1], hand_key[2]
            return (rank1 in valid_ranks and rank2 in valid_ranks and
                    suit in ('s', 'o') and rank1 != rank2)  # No pairs in combos

        return False

    @staticmethod
    def _is_valid_rgb_tuple(color: tuple) -> bool:
        """Check if color is valid RGB tuple (3 ints, each 0-255)."""
        if not isinstance(color, tuple) or len(color) != 3:
            return False
        return all(isinstance(c, int) and 0 <= c <= 255 for c in color)


@dataclass(frozen=True)
class PrecomputeProgress:
    """Progress tracking for long-running matrix precomputation.

    Used to show progress updates during expensive analysis operations.
    Session-based tracking allows resuming interrupted computations.

    FR-012: PrecomputeProgress with session tracking and progress metrics.
    """

    session_id: str
    total_hands: int = 169
    hands_completed: int = 0
    percent_complete: float = 0.0
    estimated_seconds_remaining: int = 0
    is_complete: bool = False

    def __post_init__(self):
        """Validate PrecomputeProgress fields."""
        # FR-016: Include actual vs expected values in error messages

        # Session ID validation
        if not self.session_id or not self.session_id.strip():
            raise ValueError("session_id must be non-empty string")
        if len(self.session_id.strip()) != len(self.session_id):
            raise ValueError("session_id must not have leading/trailing whitespace")

        # Total hands validation (should be 169 for standard poker)
        if self.total_hands != 169:
            raise ValueError(f"total_hands should be 169 for standard poker, got {self.total_hands}")

        # Hands completed validation
        if self.hands_completed < 0:
            raise ValueError(f"hands_completed must be >= 0, got {self.hands_completed}")
        if self.hands_completed > self.total_hands:
            raise ValueError(f"hands_completed ({self.hands_completed}) cannot exceed total_hands ({self.total_hands})")

        # Percent complete validation (fractional 0.0-1.0, not percentage)
        if not (0.0 <= self.percent_complete <= 1.0):
            raise ValueError(f"percent_complete must be 0.0-1.0 (fractional), got {self.percent_complete}")

        # Consistency validation
        if self.is_complete and self.percent_complete < 1.0:
            raise ValueError(f"is_complete=True but percent_complete ({self.percent_complete}) < 1.0")
        if not self.is_complete and self.percent_complete >= 1.0:
            raise ValueError(f"is_complete=False but percent_complete ({self.percent_complete}) >= 1.0")

        # Estimated seconds remaining validation
        if self.estimated_seconds_remaining < 0:
            raise ValueError(f"estimated_seconds_remaining must be >= 0, got {self.estimated_seconds_remaining}")

    @property
    def progress_percentage(self) -> int:
        """Get progress as integer percentage (0-100) for display."""
        return int(self.percent_complete * 100)

    @property
    def hands_remaining(self) -> int:
        """Get number of hands still to be computed."""
        return self.total_hands - self.hands_completed

    def with_progress_update(self, hands_completed: int, estimated_seconds_remaining: int) -> "PrecomputeProgress":
        """Create new progress instance with updated completion status.

        Args:
            hands_completed: New total hands completed
            estimated_seconds_remaining: Updated time estimate

        Returns:
            New PrecomputeProgress instance with updated values
        """
        new_percent_complete = hands_completed / self.total_hands
        new_is_complete = new_percent_complete >= 1.0

        return PrecomputeProgress(
            session_id=self.session_id,
            total_hands=self.total_hands,
            hands_completed=hands_completed,
            percent_complete=new_percent_complete,
            estimated_seconds_remaining=estimated_seconds_remaining,
            is_complete=new_is_complete
        )