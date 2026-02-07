class CardLayout:
    def __init__(self):
        # Fixed bounding boxes for card slots (x1, y1, x2, y2, angle) - calibrated to dashboard bboxes
        self.slots = {
            'hero_hole_1': (27, 668, 46, 693, -5.0),  # hole_A
            'hero_hole_2': (64, 666, 83, 691, 5.0),   # hole_B
            'flop_1': (69, 415, 86, 449, 0.0),        # flop1
            'flop_2': (124, 415, 143, 450, 0.0),      # flop2
            'flop_3': (179, 415, 198, 450, 0.0),      # flop3
            'turn': (234, 415, 253, 450, 0.0),        # turn
            'river': (290, 415, 309, 450, 0.0)        # river
        }
        self.tolerance = 20  # pixels tolerance for assignment