from dataclasses import dataclass
from typing import Optional
from aof_gto_browser_ii.shared.domain.hand import Hand


@dataclass(frozen=True)
class EquityResult:
    """Immutable equity result from poker hand analysis.

    Represents the equity (expected value) of a poker hand against opponents,
    calculated through Monte Carlo simulations or other analysis methods.

    Probabilities must sum to 1.0 ± 0.01 to account for floating-point precision.
    """

    hand: Hand
    equity: float  # 0.0-1.0, overall equity (win_prob + 0.5 * draw_prob)
    win_prob: float  # 0.0-1.0, probability of winning
    draw_prob: float  # 0.0-1.0, probability of drawing
    loss_prob: float  # 0.0-1.0, probability of losing
    num_simulations: int  # >= 1000

    def __post_init__(self) -> None:
        """Validate equity result constraints after initialization."""
        # Validate probability ranges
        for prob_name, prob_value in [
            ("win_prob", self.win_prob),
            ("draw_prob", self.draw_prob),
            ("loss_prob", self.loss_prob),
            ("equity", self.equity)
        ]:
            if not (0.0 <= prob_value <= 1.0):
                raise ValueError(f"{prob_name} must be between 0.0 and 1.0, got {prob_value}")

        # Validate probability sum (allow for floating-point precision)
        prob_sum = self.win_prob + self.draw_prob + self.loss_prob
        if not (0.99 <= prob_sum <= 1.01):
            raise ValueError(
                f"Probabilities must sum to 1.0 ± 0.01, got {prob_sum} "
                f"(win_prob={self.win_prob}, draw_prob={self.draw_prob}, loss_prob={self.loss_prob})"
            )

        # Validate equity calculation (equity should be win_prob + 0.5 * draw_prob)
        expected_equity = self.win_prob + 0.5 * self.draw_prob
        if not (abs(self.equity - expected_equity) < 0.001):  # Small tolerance for floating-point
            raise ValueError(
                f"Equity must equal win_prob + 0.5 * draw_prob, "
                f"expected {expected_equity}, got {self.equity}"
            )

        # Validate simulation count
        if self.num_simulations < 1000:
            raise ValueError(f"num_simulations must be >= 1000, got {self.num_simulations}")

    @property
    def win_percent(self) -> str:
        """Win probability as formatted percentage string."""
        return f"{self.win_prob * 100:.2f}%"

    @property
    def draw_percent(self) -> str:
        """Draw probability as formatted percentage string."""
        return f"{self.draw_prob * 100:.2f}%"

    @property
    def loss_percent(self) -> str:
        """Loss probability as formatted percentage string."""
        return f"{self.loss_prob * 100:.2f}%"

    @property
    def equity_percent(self) -> str:
        """Equity as formatted percentage string."""
        return f"{self.equity * 100:.2f}%"

    @classmethod
    def from_monte_carlo(
        cls,
        hand: Hand,
        wins: int,
        draws: int,
        losses: int,
        total_simulations: int
    ) -> "EquityResult":
        """Create EquityResult from Monte Carlo simulation counts.

        Args:
            hand: The poker hand being analyzed
            wins: Number of simulations where hand won
            draws: Number of simulations where hand drew
            losses: Number of simulations where hand lost
            total_simulations: Total number of simulations run

        Returns:
            EquityResult with computed probabilities

        Raises:
            ValueError: If counts don't match total_simulations or other validation fails
        """
        if wins + draws + losses != total_simulations:
            raise ValueError(
                f"Win/draw/loss counts ({wins}/{draws}/{losses}) must sum to total_simulations ({total_simulations})"
            )

        win_prob = wins / total_simulations
        draw_prob = draws / total_simulations
        loss_prob = losses / total_simulations
        equity = win_prob + 0.5 * draw_prob

        return cls(
            hand=hand,
            equity=equity,
            win_prob=win_prob,
            draw_prob=draw_prob,
            loss_prob=loss_prob,
            num_simulations=total_simulations
        )

    def __str__(self) -> str:
        """String representation showing hand and equity."""
        return f"{self.hand} ({self.equity_percent})"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"EquityResult(hand={self.hand}, equity={self.equity:.4f}, "
            f"win_prob={self.win_prob:.4f}, draw_prob={self.draw_prob:.4f}, "
            f"loss_prob={self.loss_prob:.4f}, num_simulations={self.num_simulations})"
        )