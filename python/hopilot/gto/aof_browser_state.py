from dataclasses import dataclass
from typing import Any

POSITIONS = ("UTG", "BTN", "SB", "BB")
ACTIONS = ("FOLD", "ALL_IN")
METRICS = ("WIN_LOSE_PROBABILITY", "EV", "EQUITY")


def preset_position_actions(selected_position: str) -> dict[str, str]:
    """
    Returns the canonical AoF scenario for a given hero position.
    In AoF GTO browsing, for a given Hero position, there is only ONE canonical scenario.
    """
    if selected_position not in POSITIONS:
        raise ValueError(f"Unsupported selected position: {selected_position}")
    if selected_position == "UTG":
        return {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"}
    if selected_position == "BTN":
        return {"UTG": "FOLD", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"}
    if selected_position == "SB":
        return {"UTG": "FOLD", "BTN": "FOLD", "SB": "ALL_IN", "BB": "ALL_IN"}
    return {"UTG": "FOLD", "BTN": "FOLD", "SB": "FOLD", "BB": "ALL_IN"}


@dataclass
class AoFBrowserViewState:
    selected_position: str = "UTG"
    selected_metric: str = "WIN_LOSE_PROBABILITY"
    selected_cell: tuple[int, int, str] | None = None
    hover_hand: str | None = None
    status_message: str | None = None

    @property
    def position_actions(self) -> dict[str, str]:
        """Derived from position - canonical AoF scenario."""
        return preset_position_actions(self.selected_position)

    def set_position(self, position: str) -> None:
        if position not in POSITIONS:
            raise ValueError(f"Unsupported position: {position}")
        self.selected_position = position
        # Clear selected cell when position changes to prevent stale convergence data warnings
        self.clear_selected_cell()

    def set_position_action(self, position: str, action: str) -> None:
        """
        No-op in simplified contract. Actions are derived from HERO position.
        Kept for backward compatibility with GUI components if needed, but ignores input.
        """
        pass

    def get_position_action(self, position: str) -> str:
        return self.position_actions.get(position, "FOLD")

    def active_players(self) -> int:
        return sum(1 for action in self.position_actions.values() if action == "ALL_IN")

    def set_metric(self, metric: str) -> None:
        if metric not in METRICS:
            raise ValueError(f"Unsupported metric: {metric}")
        self.selected_metric = metric
        # Clear selected cell when metric changes to prevent stale convergence data warnings
        self.clear_selected_cell()

    def set_selected_cell(self, row: int, col: int, hand_key: str) -> None:
        if row < 0 or row > 12:
            raise ValueError(f"Selected row out of bounds: {row}")
        if col < 0 or col > 12:
            raise ValueError(f"Selected col out of bounds: {col}")
        if not hand_key:
            raise ValueError("hand_key must be non-empty")
        self.selected_cell = (int(row), int(col), str(hand_key))

    def clear_selected_cell(self) -> None:
        self.selected_cell = None


def normalize_position_actions(position_actions: dict[str, str] | None) -> dict[str, str]:
    normalized: dict[str, str] = {position: "FOLD" for position in POSITIONS}
    if not position_actions:
        return normalized
    for position, action in position_actions.items():
        if position not in POSITIONS:
            raise ValueError(f"Unsupported position in context: {position}")
        if action not in ACTIONS:
            raise ValueError(f"Unsupported action in context: {action}")
        normalized[position] = action
    return normalized


def validate_metric(metric: str) -> str:
    if metric not in METRICS:
        raise ValueError(f"Unsupported metric: {metric}")
    return metric


def build_browser_context(
    selected_position: str,
    metric: str,
    num_simulations: int,
    timeout_ms: int,
    strict_current_action: bool = False,
) -> dict[str, Any]:
    """
    Builds a simplified browser context based on Hero position.
    Redundant parameters (pot_size, bet_amount, position_actions) are removed
    as they are derived from Hero position or global config.
    """
    if selected_position not in POSITIONS:
        raise ValueError(f"Unsupported selected position: {selected_position}")
    validate_metric(metric)
    if num_simulations <= 0:
        raise ValueError("num_simulations must be positive")
    if timeout_ms <= 0:
        raise ValueError("timeout_ms must be positive")

    actions = preset_position_actions(selected_position)
    active_players = sum(1 for action in actions.values() if action == "ALL_IN")
    selected_action = actions[selected_position]

    return {
        "position": selected_position,
        "action": selected_action,
        "metric": metric,
        "position_actions": actions,
        "active_players": active_players,
        "num_simulations": int(num_simulations),
        "timeout_ms": int(timeout_ms),
        "run_kind": "matrix_sweep"
    }
