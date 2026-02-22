from typing import Optional

from .config import AppConfig, load_config


class CardLayout:
    def __init__(
        self, game_mode: str = "rush_n_cash", config: Optional[AppConfig] = None
    ):
        if config is None:
            try:
                config = load_config()
            except FileNotFoundError:
                from .config import DEFAULT_CONFIG

                config = DEFAULT_CONFIG

        if game_mode not in config.game_modes:
            available_modes = list(config.game_modes.keys())
            raise ValueError(
                f"Unknown game mode: {game_mode}. Available modes: {available_modes}"
            )

        self.game_mode = game_mode
        self.slots = config.game_modes[game_mode].slots.copy()
        self.tolerance = 20  # pixels tolerance for assignment

    def get_board_bboxes(self):
        """Get list of board card bounding boxes (x1,y1,x2,y2)"""
        board_slots = ["flop_1", "flop_2", "flop_3", "turn", "river"]
        return [
            self.slots[slot][:4] for slot in board_slots
        ]  # Exclude angle for board cards

    def get_hole_bboxes(self):
        """Get list of hole card bounding boxes (x1,y1,x2,y2,angle)"""
        hole_slots = ["hero_hole_1", "hero_hole_2"]
        return [self.slots[slot] for slot in hole_slots]  # Include angle for hole cards
