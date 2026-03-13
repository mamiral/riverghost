from dataclasses import dataclass

POSITIONS = ("UTG", "BTN", "SB", "BB")
ACTIONS = ("FOLD", "ALL_IN")
METRICS = ("WIN_LOSE_PROBABILITY", "EV", "EQUITY", "EQR")


@dataclass
class AoFBrowserViewState:
    selected_position: str = "UTG"
    selected_action: str = "FOLD"
    selected_metric: str = "WIN_LOSE_PROBABILITY"
    hover_hand: str | None = None
    status_message: str | None = None

    def set_position(self, position: str) -> None:
        if position not in POSITIONS:
            raise ValueError(f"Unsupported position: {position}")
        self.selected_position = position

    def set_action(self, action: str) -> None:
        if action not in ACTIONS:
            raise ValueError(f"Unsupported action: {action}")
        self.selected_action = action

    def set_metric(self, metric: str) -> None:
        if metric not in METRICS:
            raise ValueError(f"Unsupported metric: {metric}")
        self.selected_metric = metric
