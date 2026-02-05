"""
Card recognition and matching functionality for poker cards.
Provides color-based suite detection and template-based rank matching.
"""

import cv2
import numpy as np
import os
from pathlib import Path


def load_rank_templates(templates_dir):
    """Load rank templates and normalize to 0-1 range like test_template_matching.py"""
    templates = {}
    for file in os.listdir(templates_dir):
        if file.endswith(('.png', '.jpg', '.jpeg')):
            template_path = os.path.join(templates_dir, file)
            template = cv2.imread(template_path)
            if template is None:
                print(f"Error: Failed to load template {template_path}")
                continue

            # Convert to grayscale if needed
            if len(template.shape) == 3:
                template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            else:
                template_gray = template

            # Normalize to 0-1 range (assuming it's already binary 0-255)
            template_norm = template_gray.astype(np.float32) / 255.0

            name = os.path.splitext(file)[0]
            templates[name] = template_norm
            print(f"Loaded rank template: {name} {template.shape} -> {template_norm.shape}")

    return templates


def convert_to_white_hot(image, threshold=200):
    """Convert image to 1-bit white hot (white pixels become 1, others 0)"""
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Create binary mask where white pixels (> threshold) are 255, others are 0
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    # Convert to 1-bit (0 or 1)
    binary_1bit = (binary / 255).astype(np.uint8)

    return binary_1bit


def match_template_correlation(image_normalized, template, method=cv2.TM_CCOEFF_NORMED):
    """Perform template matching using correlation like test_template_matching.py"""
    # Ensure image is large enough for template
    if image_normalized.shape[0] < template.shape[0] or image_normalized.shape[1] < template.shape[1]:
        return None

    # Perform template matching
    result = cv2.matchTemplate(image_normalized, template, method)

    # Get best match
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # Calculate confidence - shift to 0-1 range
    confidence = (max_val + 1.0) / 2.0

    return max_val, confidence


def get_top_matches_correlation(normalized_image, templates, n=3):
    """Get top matches using correlation-based template matching"""
    matches = []
    for name, template in templates.items():
        result = match_template_correlation(normalized_image, template)
        if result is not None:
            score, confidence = result
            matches.append((name, score, confidence))
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:n]


def detect_card_color(bgr_value):
    """Detect the specific color of a card based on BGR values"""
    b, g, r = int(bgr_value[0]), int(bgr_value[1]), int(bgr_value[2])

    # White/bright pixels first (text/symbols) - exclude from color voting
    # Very strict white threshold since card backgrounds are bright but tinted
    if r > 245 and g > 245 and b > 245:
        return "white"

    # Blue (diamonds) - for average background color, blue should dominate
    if b > 100 and b > r + 20 and b > g + 20:
        return "blue"

    # Red (hearts) - for average background color, red should dominate
    if r > 100 and r > b + 20 and r > g + 20:
        return "red"

    # Green (clubs) - for average background color, green should dominate
    if g > 100 and g > r + 20 and g > b + 20:
        return "green"

    # Black (spades) - for average background color, all channels should be low
    if r < 80 and g < 80 and b < 80:
        return "black"

    # Everything else is unknown
    return "unknown"


def classify_suite(image):
    """Classify suite based on background color analysis, return suite name"""
    # Crop suite area: y=20 to bottom, full width
    suite_crop = image[20:, :]

    # Average all non-white pixels in the suite area for robust color detection
    h, w = suite_crop.shape[:2]

    # Collect all non-white pixels for averaging
    background_pixels = []

    for i in range(h):
        for j in range(w):
            pixel_bgr = suite_crop[i, j]
            b, g, r = int(pixel_bgr[0]), int(pixel_bgr[1]), int(pixel_bgr[2])

            # Exclude very bright/white pixels (symbols)
            if not (r > 128 and g > 128 and b > 128):
                background_pixels.append(pixel_bgr)

    if len(background_pixels) > 0:
        # Calculate average BGR of background pixels
        avg_bgr = np.mean(background_pixels, axis=0)

        # Classify based on the average background color
        color = detect_card_color(avg_bgr)

        # Map color to suite
        if color == "blue":
            suite_name = "diamonds"
        elif color == "red":
            suite_name = "hearts"
        elif color == "green":
            suite_name = "clubs"
        elif color == "black":
            suite_name = "spades"
        else:
            suite_name = "unknown"
    else:
        suite_name = "unknown"

    # Crop rank area for processing
    rank_crop = image[0:18, :]

    return suite_name, rank_crop


def match_template_correlation(image, template, method=cv2.TM_CCOEFF_NORMED):
    """Perform template matching and return score and confidence"""
    # Ensure image is large enough for template
    if image.shape[0] < template.shape[0] or image.shape[1] < template.shape[1]:
        return None

    # Perform template matching
    result = cv2.matchTemplate(image, template, method)

    # Get best match
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # Calculate confidence - use max_val directly since TM_CCOEFF_NORMED gives -1 to 1
    # Shift to 0-1 range and use as confidence
    confidence = (max_val + 1.0) / 2.0

    return max_val, confidence


def get_top_matches_correlation(image, templates, top_n=5):
    """Get top N template matches sorted by correlation score"""
    matches = []

    for template_name, template in templates.items():
        result = match_template_correlation(image, template)
        if result is not None:
            score, confidence = result
            matches.append((template_name, score, confidence))

    # Sort by score (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches[:top_n]


class CardMatcher:
    """Main class for card recognition and matching"""

    def __init__(self, templates_dir=None):
        """Initialize with rank templates"""
        if templates_dir is None:
            # Default to templates directory in the same directory as this module
            templates_dir = Path(__file__).parent / 'templates'
        
        self.rank_templates = {}
        if os.path.exists(templates_dir):
            self.rank_templates = load_rank_templates(templates_dir)

    def recognize_card(self, image_path):
        """
        Recognize a single card from image path

        Args:
            image_path (str or Path): Path to card image

        Returns:
            dict: Recognition results with keys:
                - 'suite': detected suite name
                - 'rank': detected rank name
                - 'rank_score': template matching score
                - 'rank_confidence': template matching confidence
                - 'success': True if both suite and rank were detected
        """
        image = cv2.imread(str(image_path))
        if image is None:
            return {
                'suite': None,
                'rank': None,
                'rank_score': 0.0,
                'rank_confidence': 0.0,
                'success': False,
                'error': f"Failed to read image: {image_path}"
            }

        # Classify suite
        suite_name, rank_crop = classify_suite(image)

        # Match rank
        rank_result = self._match_rank(rank_crop)

        return {
            'suite': suite_name,
            'rank': rank_result['rank'],
            'rank_score': rank_result['score'],
            'rank_confidence': rank_result['confidence'],
            'success': suite_name != "unknown" and rank_result['rank'] is not None,
            'error': None
        }

    def _match_rank(self, rank_crop):
        """Match rank using template correlation"""
        if not self.rank_templates:
            return {'rank': None, 'score': 0.0, 'confidence': 0.0}

        # Convert rank_crop to 1-bit white hot for correlation matching
        rank_1bit = convert_to_white_hot(rank_crop)

        # Match rank using correlation-based template matching
        rank_top = get_top_matches_correlation(rank_1bit.astype(np.float32), self.rank_templates)

        if rank_top and rank_top[0][1] >= 0.6:  # Using correlation score threshold
            rank_match, rank_score, confidence = rank_top[0]
            return {'rank': rank_match, 'score': rank_score, 'confidence': confidence}
        else:
            # Return best match even if below threshold
            if rank_top:
                rank_match, rank_score, confidence = rank_top[0]
                return {'rank': rank_match, 'score': rank_score, 'confidence': confidence}
            else:
                return {'rank': None, 'score': 0.0, 'confidence': 0.0}
