class CardLayout:
    def __init__(self):
        # Fixed coordinates for card slots (x, y) - placeholders, calibrate in real use
        self.slots = {
            'hero_hole_1': (500, 350),
            'hero_hole_2': (525, 350),
            'flop_1': (532, 350),
            'flop_2': (576, 350),
            'flop_3': (621, 350),
            'turn': (665, 350),
            'river': (710, 350)
        }
        self.tolerance = 20  # pixels tolerance for assignment

    def assign_cards(self, detected_cards):
        """
        Assign detected cards to slots based on position.
        detected_cards: list of (name, conf, xyxy) tuples, sorted left to right.
        Returns dict of slot -> (name, conf) or None if empty.
        """
        assignments = {slot: None for slot in self.slots}
        slot_order = ['hero_hole_1', 'hero_hole_2', 'flop_1', 'flop_2', 'flop_3', 'turn', 'river']

        for i, (name, conf, xyxy) in enumerate(detected_cards[:len(slot_order)]):
            slot = slot_order[i]
            assignments[slot] = (name, conf, xyxy)

        return assignments

    def update_slots_from_detections(self, detections_over_time):
        """
        Optional: Update slot coordinates by averaging positions over multiple frames.
        detections_over_time: list of lists of (x, y) for each slot.
        """
        for slot in self.slots:
            if detections_over_time[slot]:
                avg_x = sum(x for x, y in detections_over_time[slot]) / len(detections_over_time[slot])
                avg_y = sum(y for x, y in detections_over_time[slot]) / len(detections_over_time[slot])
                self.slots[slot] = (avg_x, avg_y)