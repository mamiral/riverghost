class CardLayout:
    def __init__(self, game_mode="rush_n_cash"):
        # Game mode configurations with bounding boxes (x1, y1, x2, y2, angle)
        self.game_modes = {
            "rush_n_cash": {
                'hero_hole_1': (27, 668, 46, 693, -5.0),  # hole_A
                'hero_hole_2': (64, 666, 83, 691, 5.0),   # hole_B
                'flop_1': (69, 415, 86, 449, 0.0),        # flop1
                'flop_2': (124, 415, 143, 450, 0.0),      # flop2
                'flop_3': (179, 415, 198, 450, 0.0),      # flop3
                'turn': (234, 415, 253, 450, 0.0),        # turn
                'river': (290, 415, 309, 450, 0.0)        # river
            }
        }
        
        self.set_game_mode(game_mode)
        self.tolerance = 20  # pixels tolerance for assignment

    def set_game_mode(self, game_mode):
        """Set the current game mode"""
        if game_mode not in self.game_modes:
            raise ValueError(f"Unknown game mode: {game_mode}")
        self.game_mode = game_mode
        self.slots = self.game_modes[game_mode]

    def get_board_bboxes(self):
        """Get list of board card bounding boxes (x1,y1,x2,y2)"""
        board_slots = ['flop_1', 'flop_2', 'flop_3', 'turn', 'river']
        return [self.slots[slot][:4] for slot in board_slots]  # Exclude angle for board cards

    def get_hole_bboxes(self):
        """Get list of hole card bounding boxes (x1,y1,x2,y2,angle)"""
        hole_slots = ['hero_hole_1', 'hero_hole_2']
        return [self.slots[slot] for slot in hole_slots]  # Include angle for hole cards