import os
import cv2
import numpy as np
from card_layout import CardLayout
from card_matcher import CardMatcher

class CardDetector:
    def __init__(self, templates_dir='templates'):
        self.layout = CardLayout()
        self.templates_dir = templates_dir
        self.card_matcher = CardMatcher()
        print(f"CardDetector initialized with CardMatcher. Rank templates loaded: {len(self.card_matcher.rank_templates)}")

    def classify_card(self, card_image):
        """Classify a single card image using CardMatcher"""
        if isinstance(card_image, str):
            card_image = cv2.imread(card_image)
            if card_image is None:
                return None

        if card_image.size == 0:
            print("  Card image is empty")
            return None

        # Ensure we have 3 channels
        if len(card_image.shape) == 2:
            card_image = cv2.cvtColor(card_image, cv2.COLOR_GRAY2BGR)

        print(f"  Classifying card image of shape {card_image.shape}")

        # Use CardMatcher methods
        from card_matcher import classify_suite
        
        # Classify suite
        suite_name, rank_crop = classify_suite(card_image)
        
        # Match rank
        rank_result = self.card_matcher._match_rank(rank_crop)

        if suite_name and suite_name != "unknown" and rank_result["rank"]:
            card_name = f"{rank_result['rank']}{suite_name[0]}"  # e.g., "As", "Qh"
            return card_name
        return None

    def detect_cards(self, image, conf=0.1):
        """
        Detect cards in an image (path or numpy array).
        Returns dict of slot -> (name, conf, xyxy) or None
        """
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                print("ERROR: Failed to load image")
                return {}

        assignments = {slot: None for slot in self.layout.slots}

        print(f"Detecting cards in image of shape {image.shape}")

        for slot, bbox in self.layout.slots.items():
            if len(bbox) == 5:
                x1, y1, x2, y2, angle = bbox
            else:
                x1, y1, x2, y2 = bbox
                angle = 0.0
            
            if 'hole' in slot:
                print(f"Checking slot {slot} at bbox ({x1},{y1},{x2},{y2}) angle {angle}")
            
            # Check bounds
            if x1 >= image.shape[1] or y1 >= image.shape[0] or x2 <= x1 or y2 <= y1:
                continue

            if angle == 0.0:
                # Normal crop
                card_crop = image[y1:y2, x1:x2]
            else:
                # Rotated crop, similar to CropBBoxesCommand
                center = ((x1 + x2) / 2, (y1 + y2) / 2)
                size = (x2 - x1, y2 - y1)
                rect = (center, size, angle)
                box = cv2.boxPoints(rect)
                x1_bb = int(min(box[:, 0]))
                y1_bb = int(min(box[:, 1]))
                x2_bb = int(max(box[:, 0]))
                y2_bb = int(max(box[:, 1]))
                sub = image[y1_bb:y2_bb, x1_bb:x2_bb]
                if sub.size == 0:
                    continue
                rel_center = (center[0] - x1_bb, center[1] - y1_bb)
                M = cv2.getRotationMatrix2D(rel_center, angle, 1.0)
                rotated_sub = cv2.warpAffine(sub, M, (x2_bb - x1_bb, y2_bb - y1_bb))
                card_crop = rotated_sub[int(rel_center[1] - size[1]/2):int(rel_center[1] + size[1]/2), 
                                       int(rel_center[0] - size[0]/2):int(rel_center[0] + size[0]/2)]
                if card_crop.size == 0:
                    continue

            # Basic validation: check if crop has card-like properties
            # Skip validation for hole cards as they may be rotated
            if 'hole' not in slot and not self.is_card_like(card_crop):
                continue

            card_name = self.classify_card(card_crop)
            
            if 'hole' in slot:
                print(f"  {slot} classified as: {card_name}")

            if card_name:
                # Use the bbox for xyxy
                xyxy = [x1, y1, x2, y2]
                assignments[slot] = (card_name, 0.9, xyxy)  # High confidence for template matches

        print(f"Detected {sum(1 for v in assignments.values() if v is not None)} cards")
        
        return assignments

    def is_card_like(self, image):
        """Check if an image region looks like it contains a card"""
        if image.size == 0:
            return False
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        # Check contrast (standard deviation)
        contrast = np.std(gray)
        if contrast < 30:  # Too low contrast
            return False
            
        # Check for edges (cards should have structure)
        edges = cv2.Canny(gray, 100, 200)
        edge_ratio = np.sum(edges > 0) / image.size
        if edge_ratio < 0.01:  # Too few edges
            return False
            
        return True

    def calibrate_positions(self, image_path, manual_coords=None):
        """
        Help calibrate card positions by detecting cards in a screenshot.
        manual_coords: dict of slot -> (x, y) to override defaults
        """
        if manual_coords:
            self.layout.slots.update(manual_coords)

        image = cv2.imread(image_path) if isinstance(image_path, str) else image_path
        if image is None:
            print("Failed to load image")
            return

        print(f"Image size: {image.shape[1]}x{image.shape[0]}")
        print("Current slot positions:")
        for slot, (x, y) in self.layout.slots.items():
            print(f"  {slot}: ({x}, {y})")

        # Test detection
        assignments = self.detect_cards(image)
        print("\nDetection results:")
        for slot, card_data in assignments.items():
            if card_data:
                print(f"  {slot}: {card_data[0]}")
            else:
                print(f"  {slot}: None")

        return assignments

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Calibrate card positions for HoPilot')
    parser.add_argument('--image', help='Path to poker table screenshot')
    parser.add_argument('--coords', nargs='*', help='Manual coordinates as slot=x,y (e.g., hero_hole_1=100,200)')
    parser.add_argument('--test-hopilot', action='store_true', help='Test with HoPilot-style processing')
    args = parser.parse_args()

    if args.test_hopilot:
        # Test HoPilot-style processing
        detector = CardDetector()
        # Simulate a frame capture (you would replace this with actual capture)
        print("Testing HoPilot-style detection...")
        print("Note: Replace the image loading below with actual frame capture")
        # For testing, you can load a screenshot here
        # image = cv2.imread('path/to/screenshot.png')
        # assignments = detector.detect_cards(image)
        print("To test: modify this script to load your poker table screenshot")

    elif args.image:
        detector = CardDetector()

        # Parse manual coordinates
        manual_coords = {}
        if args.coords:
            for coord_str in args.coords:
                slot, coords = coord_str.split('=')
                x, y = map(int, coords.split(','))
                manual_coords[slot] = (x, y)

        detector.calibrate_positions(args.image, manual_coords)
    else:
        print("Usage:")
        print("  python card_detector.py --image path/to/screenshot.png [--coords hero_hole_1=100,200 ...]")
        print("  python card_detector.py --test-hopilot")