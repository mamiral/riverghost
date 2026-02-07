import os
import sys
import cv2
import numpy as np
from .card_layout import CardLayout
from .card_matcher import CardMatcher
import logging
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class CardDetectionError(Exception):
    """Raised when card detection fails."""
    pass


class CardDetector:
    def __init__(self, templates_dir: str = 'templates', game_mode: str = "rush_n_cash"):
        if not templates_dir or not isinstance(templates_dir, str):
            raise ValueError("templates_dir must be a non-empty string")

        self.layout = CardLayout(game_mode)
        self.templates_dir = templates_dir
        self.game_mode = game_mode
        self.card_matcher = CardMatcher()
        logger.info(f"CardDetector initialized with CardMatcher. Rank templates loaded: {len(self.card_matcher.rank_templates)}")

    def classify_card(self, card_image: Union[str, np.ndarray]) -> Optional[str]:
        """Classify a single card image using CardMatcher"""
        if card_image is None:
            logger.warning("Card image is None")
            return None

        try:
            if isinstance(card_image, str):
                card_image = cv2.imread(card_image)
                if card_image is None:
                    logger.error(f"Failed to load image from path: {card_image}")
                    return None

            if card_image.size == 0:
                logger.warning("Card image is empty")
                return None

            # Ensure we have 3 channels
            if len(card_image.shape) == 2:
                card_image = cv2.cvtColor(card_image, cv2.COLOR_GRAY2BGR)

            logger.debug(f"Classifying card image of shape {card_image.shape}")

            # Use CardMatcher methods
            from .card_matcher import classify_suite

            # Classify suite
            suite_name, rank_crop = classify_suite(card_image)

            # Match rank
            rank_result = self.card_matcher._match_rank(rank_crop)

            if suite_name and suite_name != "unknown" and rank_result["rank"]:
                card_name = f"{rank_result['rank']}{suite_name[0]}"  # e.g., "As", "Qh"
                return card_name

            logger.debug("Card classification failed - no valid rank/suite detected")
            return None

        except Exception as e:
            logger.error(f"Error classifying card: {e}")
            return None

    def detect_cards(self, image: Union[str, np.ndarray], conf: float = 0.1) -> Dict[str, Optional[Tuple[str, float, List[int]]]]:
        """
        Detect cards in an image (path or numpy array).
        Returns dict of slot -> (name, conf, xyxy) or None
        """
        try:
            if image is None:
                raise CardDetectionError("Image cannot be None")

            if isinstance(image, str):
                image = cv2.imread(image)
                if image is None:
                    raise CardDetectionError(f"Failed to load image from path: {image}")

            if image.size == 0:
                raise CardDetectionError("Image is empty")

            # Ensure we have 3 channels
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

            logger.debug(f"Detecting cards in image of shape {image.shape}")

            assignments: Dict[str, Optional[Tuple[str, float, List[int]]]] = {slot: None for slot in self.layout.slots}

            for slot, bbox in self.layout.slots.items():
                try:
                    if len(bbox) == 5:
                        x1, y1, x2, y2, angle = bbox
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    else:
                        x1, y1, x2, y2 = bbox
                        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                        angle = 0.0

                    if 'hole' in slot:
                        logger.debug(f"Checking slot {slot} at bbox ({x1},{y1},{x2},{y2}) angle {angle}")

                    # Check bounds
                    if x1 >= image.shape[1] or y1 >= image.shape[0] or x2 <= x1 or y2 <= y1:
                        logger.debug(f"Invalid bbox for slot {slot}: ({x1},{y1},{x2},{y2})")
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
                            logger.debug(f"Empty sub-image for rotated crop in slot {slot}")
                            continue
                        rel_center = (center[0] - x1_bb, center[1] - y1_bb)
                        M = cv2.getRotationMatrix2D(rel_center, angle, 1.0)
                        rotated_sub = cv2.warpAffine(sub, M, (x2_bb - x1_bb, y2_bb - y1_bb))
                        card_crop = rotated_sub[int(rel_center[1] - size[1]/2):int(rel_center[1] + size[1]/2),
                                               int(rel_center[0] - size[0]/2):int(rel_center[0] + size[0]/2)]
                        if card_crop.size == 0:
                            logger.debug(f"Empty card crop after rotation for slot {slot}")
                            continue

                    # Basic validation: check if crop has card-like properties
                    # Skip validation for hole cards as they may be rotated
                    if 'hole' not in slot and not self.is_card_like(card_crop):
                        logger.debug(f"Card crop for slot {slot} does not look like a card")
                        continue

                    card_name = self.classify_card(card_crop)

                    if 'hole' in slot:
                        logger.info(f"  {slot} classified as: {card_name}")

                    if card_name:
                        # Use the bbox for xyxy
                        xyxy = [x1, y1, x2, y2]
                        assignments[slot] = (card_name, 0.9, xyxy)  # High confidence for template matches

                except Exception as e:
                    logger.error(f"Error processing slot {slot}: {e}")
                    continue

            detected_count = sum(1 for v in assignments.values() if v is not None)
            logger.info(f"Detected {detected_count} cards")

            return assignments

        except CardDetectionError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in detect_cards: {e}")
            raise CardDetectionError(f"Card detection failed: {e}") from e

    def is_card_like(self, image: np.ndarray) -> bool:
        """Check if an image region looks like it contains a card"""
        try:
            if image is None or image.size == 0:
                logger.debug("Image is None or empty")
                return False

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

            # Check contrast (standard deviation)
            contrast = np.std(gray)
            if contrast < 30:  # Too low contrast
                logger.debug(f"Low contrast detected: {contrast}")
                return False

            # Check for edges (cards should have structure)
            edges = cv2.Canny(gray, 100, 200)
            edge_ratio = np.sum(edges > 0) / image.size
            if edge_ratio < 0.01:  # Too few edges
                logger.debug(f"Low edge ratio detected: {edge_ratio}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error in is_card_like: {e}")
            return False

    def calibrate_positions(self, image_path: Union[str, np.ndarray], manual_coords: Optional[Dict[str, Tuple[int, int]]] = None) -> Optional[Dict[str, Optional[Tuple[str, float, List[int]]]]]:
        """
        Help calibrate card positions by detecting cards in a screenshot.
        manual_coords: dict of slot -> (x, y) to override defaults
        """
        try:
            if manual_coords:
                self.layout.slots.update(manual_coords)

            image = cv2.imread(image_path) if isinstance(image_path, str) else image_path
            if image is None:
                logger.error("Failed to load image")
                return None

            logger.info(f"Image size: {image.shape[1]}x{image.shape[0]}")
            logger.info("Current slot positions:")
            for slot, bbox in self.layout.slots.items():
                if len(bbox) >= 4:
                    x1, y1, x2, y2 = bbox[:4]
                    logger.info(f"  {slot}: ({x1}, {y1}, {x2}, {y2})")

            # Test detection
            assignments = self.detect_cards(image)
            logger.info("\nDetection results:")
            for slot, card_data in assignments.items():
                if card_data:
                    logger.info(f"  {slot}: {card_data[0]}")
                else:
                    logger.info(f"  {slot}: None")

            return assignments

        except Exception as e:
            logger.error(f"Error in calibrate_positions: {e}")
            return None

if __name__ == "__main__":
    import argparse

    try:
        parser = argparse.ArgumentParser(description='Calibrate card positions for HoPilot')
        parser.add_argument('--image', help='Path to poker table screenshot')
        parser.add_argument('--coords', nargs='*', help='Manual coordinates as slot=x,y (e.g., hero_hole_1=100,200)')
        parser.add_argument('--test-hopilot', action='store_true', help='Test with HoPilot-style processing')
        args = parser.parse_args()

        if args.test_hopilot:
            # Test HoPilot-style processing
            detector = CardDetector()
            # Simulate a frame capture (you would replace this with actual capture)
            logger.info("Testing HoPilot-style detection...")
            logger.info("Note: Replace the image loading below with actual frame capture")
            # For testing, you can load a screenshot here
            # image = cv2.imread('path/to/screenshot.png')
            # assignments = detector.detect_cards(image)
            logger.info("To test: modify this script to load your poker table screenshot")

        elif args.image:
            detector = CardDetector()

            # Parse manual coordinates
            manual_coords = {}
            if args.coords:
                for coord_str in args.coords:
                    try:
                        slot, coords = coord_str.split('=')
                        x, y = map(int, coords.split(','))
                        manual_coords[slot] = (x, y)
                    except ValueError as e:
                        logger.error(f"Invalid coordinate format: {coord_str}. Expected slot=x,y")
                        continue

            detector.calibrate_positions(args.image, manual_coords)
        else:
            print("Usage:")
            print("  python card_detector.py --image path/to/screenshot.png [--coords hero_hole_1=100,200 ...]")
            print("  python card_detector.py --test-hopilot")

    except Exception as e:
        logger.error(f"Error in main: {e}")
        sys.exit(1)