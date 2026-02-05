import os
import cv2
import numpy as np
from card_layout import CardLayout

class CardDetector:
    def __init__(self, templates_dir='../../templates'):
        self.layout = CardLayout()
        self.templates_dir = templates_dir
        self.suite_templates = {}
        self.rank_templates = {}
        self._load_templates()

    def _load_templates(self):
        """Load suite and rank templates for template matching"""
        # Load suite templates
        suites_dir = os.path.join(self.templates_dir, 'suites')
        if os.path.exists(suites_dir):
            red_suites = ['hearts', 'diamonds']
            black_suites = ['spades', 'clubs_orig']
            red_templates = {}
            black_templates = {}
            for file in os.listdir(suites_dir):
                if file.endswith(('.png', '.jpg', '.jpeg')):
                    template_path = os.path.join(suites_dir, file)
                    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        name = os.path.splitext(file)[0]
                        if name in red_suites:
                            red_templates[name] = template
                        elif name in black_suites:
                            # Map clubs_orig to clubs
                            suite_name = 'clubs' if name == 'clubs_orig' else name
                            black_templates[suite_name] = template
            self.suite_templates = {'red': red_templates, 'black': black_templates}
            print(f"Loaded suite templates - Red: {list(red_templates.keys())}, Black: {list(black_templates.keys())}")

        # Load rank templates
        ranks_dir = os.path.join(self.templates_dir, 'ranks')
        if os.path.exists(ranks_dir):
            normal_templates = {}
            edge_templates = {}
            contour_templates = {}
            for file in os.listdir(ranks_dir):
                if file.endswith(('.png', '.jpg', '.jpeg')):
                    template_path = os.path.join(ranks_dir, file)
                    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                    if template is not None:
                        name = os.path.splitext(file)[0]
                        # Store normal
                        normal_templates[name] = template
                        # Apply Canny edge detection
                        edges = cv2.Canny(template, 100, 200)
                        edge_templates[name] = edges
                        # Find contours
                        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if contours:
                            # Take the largest contour
                            main_contour = max(contours, key=cv2.contourArea)
                            contour_templates[name] = main_contour
            self.rank_templates = {
                'normal': normal_templates,
                'edges': edge_templates,
                'contours': contour_templates
            }
            print(f"Loaded rank templates: {len(normal_templates)} normal, {len(edge_templates)} edges, {len(contour_templates)} contours")

    def match_template(self, image, template, method=cv2.TM_CCOEFF_NORMED):
        """Template matching helper"""
        res = cv2.matchTemplate(image, template, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        return max_val, max_loc

    def match_shapes(self, contour1, contour2):
        """Shape matching helper"""
        return cv2.matchShapes(contour1, contour2, cv2.CONTOURS_MATCH_I1, 0)

    def get_top_matches(self, gray_image, templates, n=3):
        """Get top template matches"""
        matches = []
        for name, template in templates.items():
            if template.shape[0] > gray_image.shape[0] or template.shape[1] > gray_image.shape[1]:
                continue  # Skip if template is larger than image
            score, loc = self.match_template(gray_image, template)
            matches.append((name, score))
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:n]

    def is_red_color(self, bgr_value):
        """Check if color is red"""
        b, g, r = bgr_value
        return r > 50 and r > g and r > b

    def classify_card(self, card_image):
        """Classify a single card image using template matching"""
        if isinstance(card_image, str):
            card_image = cv2.imread(card_image)
            if card_image is None:
                return None

        if card_image.size == 0:
            return None

        # Ensure we have 3 channels
        if len(card_image.shape) == 2:
            card_image = cv2.cvtColor(card_image, cv2.COLOR_GRAY2BGR)

        # Crop rank: y=0 to 18, full width
        rank_crop = card_image[0:18, :]

        # Crop suite: y=20 to bottom, full width
        suite_crop = card_image[20:, :]

        # Determine if red or black
        h, w = suite_crop.shape[:2]
        center_y, center_x = h // 2, w // 2
        is_red = False
        if h >= 5 and w >= 5:
            y1 = max(0, center_y - 2)
            y2 = min(h, center_y + 3)
            x1 = max(0, center_x - 2)
            x2 = min(w, center_x + 3)
            patch = suite_crop[y1:y2, x1:x2]
            red_votes = 0
            total_pixels = (y2 - y1) * (x2 - x1)
            for i in range(y2 - y1):
                for j in range(x2 - x1):
                    pixel_bgr = patch[i, j]
                    if self.is_red_color(pixel_bgr):
                        red_votes += 1
            is_red = red_votes > total_pixels // 2

        # Convert suite to grayscale
        if len(suite_crop.shape) == 3:
            suite_gray = cv2.cvtColor(suite_crop, cv2.COLOR_BGR2GRAY)
        else:
            suite_gray = suite_crop

        # Match suite
        suite_templates = self.suite_templates['red'] if is_red else self.suite_templates['black']
        suite_top = self.get_top_matches(suite_gray, suite_templates)
        suite_name = None
        if suite_top and suite_top[0][1] >= 0.8:
            suite_name = suite_top[0][0]

        # Convert rank_crop to gray
        if len(rank_crop.shape) == 3:
            rank_gray = cv2.cvtColor(rank_crop, cv2.COLOR_BGR2GRAY)
        else:
            rank_gray = rank_crop

        # Match rank with fallbacks
        rank_name = None
        rank_top = self.get_top_matches(rank_gray, self.rank_templates['normal'])
        if rank_top and rank_top[0][1] >= 0.6:
            rank_name = rank_top[0][0]
        else:
            # Try with edges
            rank_edges_img = cv2.Canny(rank_gray, 100, 200)
            rank_top_edges = self.get_top_matches(rank_edges_img, self.rank_templates['edges'])
            if rank_top_edges and rank_top_edges[0][1] >= 0.6:
                rank_name = rank_top_edges[0][0]
            else:
                # Try with contours
                contours, _ = cv2.findContours(rank_edges_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    main_contour = max(contours, key=cv2.contourArea)
                    best_match = None
                    best_score = float('inf')
                    for name, template_contour in self.rank_templates['contours'].items():
                        score = self.match_shapes(main_contour, template_contour)
                        if score < best_score:
                            best_score = score
                            best_match = name
                    if best_score < 0.5:
                        rank_name = best_match

        if suite_name and rank_name:
            return f"{rank_name}{suite_name[0]}"  # e.g., "As", "Qh"
        return None

    def detect_cards(self, image, conf=0.1):
        """
        Detect cards in an image (path or numpy array).
        Returns dict of slot -> (name, conf) or None
        """
        if isinstance(image, str):
            image = cv2.imread(image)
            if image is None:
                print("ERROR: Failed to load image")
                return {}

        detected_cards = []
        card_size = (17, 34)  # width, height based on template_matcher

        for slot, (x, y) in self.layout.slots.items():
            # Check bounds first
            x1 = max(0, x - card_size[0] // 2)
            y1 = max(0, y - card_size[1] // 2)
            x2 = min(image.shape[1], x1 + card_size[0])
            y2 = min(image.shape[0], y1 + card_size[1])

            if x2 - x1 < 5 or y2 - y1 < 10:  # Too small
                continue

            if x1 >= image.shape[1] or y1 >= image.shape[0]:  # Outside bounds
                continue

            card_crop = image[y1:y2, x1:x2]

            card_name = self.classify_card(card_crop)

            if card_name:
                # Create bounding box for compatibility
                xyxy = [x1, y1, x2, y2]
                detected_cards.append((card_name, 0.9, xyxy))  # High confidence for template matches

        # Assign to slots
        assignments = self.layout.assign_cards(detected_cards)
        return assignments

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