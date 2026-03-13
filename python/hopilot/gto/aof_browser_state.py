from dataclasses import dataclass

POSITIONS = ("UTG", "BTN", "SB", "BB")
ACTIONS = ("FOLD", "ALL_IN")
METRICS = ("WIN_LOSE_PROBABILITY", "EV", "EQUITY", "EQR")


@dataclass
class AoFBrowserViewState:
    selected_position: str = "UTG"
    position_actions: dict[str, str] | None = None
    selected_metric: str = "WIN_LOSE_PROBABILITY"
    hover_hand: str | None = None
    status_message: str | None = None

    def __post_init__(self) -> None:
        if self.position_actions is None:
            self.position_actions = {position: "FOLD" for position in POSITIONS}

    def set_position(self, position: str) -> None:
        if position not in POSITIONS:
            raise ValueError(f"Unsupported position: {position}")
        self.selected_position = position

    def set_position_action(self, position: str, action: str) -> None:
        if position not in POSITIONS:
            raise ValueError(f"Unsupported position: {position}")
        if action not in ACTIONS:
            raise ValueError(f"Unsupported action: {action}")
        if self.position_actions is None:
            self.position_actions = {p: "FOLD" for p in POSITIONS}
        self.position_actions[position] = action

    def get_position_action(self, position: str) -> str:
        if self.position_actions is None:
            self.position_actions = {p: "FOLD" for p in POSITIONS}
        return self.position_actions.get(position, "FOLD")

    def active_players(self) -> int:
        if self.position_actions is None:
            return 0
        return sum(1 for action in self.position_actions.values() if action == "ALL_IN")

    def set_metric(self, metric: str) -> None:
        if metric not in METRICS:
            raise ValueError(f"Unsupported metric: {metric}")
        self.selected_metric = metric
