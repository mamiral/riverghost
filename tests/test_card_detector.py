import pytest
import numpy as np
import cv2
import os
import sys
from unittest.mock import patch, MagicMock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))
from hopilot.card_detector import CardDetector, CardDetectionError


class TestCardDetector:
    """Test cases for CardDetector class"""

    @pytest.fixture
    def detector(self):
        """Create a CardDetector instance for testing"""
        return CardDetector()

    def test_init_valid(self):
        """Test CardDetector initialization with valid parameters"""
        detector = CardDetector(templates_dir="templates", game_mode="rush_n_cash")
        assert detector.templates_dir == "templates"
        assert detector.game_mode == "rush_n_cash"
        assert detector.layout is not None
        assert detector.card_matcher is not None

    def test_init_invalid_templates_dir(self):
        """Test CardDetector initialization with invalid templates_dir"""
        with pytest.raises(ValueError, match="templates_dir must be a non-empty string"):
            CardDetector(templates_dir="")

        with pytest.raises(ValueError, match="templates_dir must be a non-empty string"):
            CardDetector(templates_dir=None)

    def test_classify_card_none_input(self, detector):
        """Test classify_card with None input"""
        result = detector.classify_card(None)
        assert result is None

    def test_classify_card_empty_image(self, detector):
        """Test classify_card with empty image"""
        empty_image = np.array([])
        result = detector.classify_card(empty_image)
        assert result is None

    @patch('cv2.imread')
    def test_classify_card_invalid_path(self, mock_imread, detector):
        """Test classify_card with invalid image path"""
        mock_imread.return_value = None
        result = detector.classify_card("invalid/path.jpg")
        assert result is None

    def test_detect_cards_none_image(self, detector):
        """Test detect_cards with None image"""
        with pytest.raises(CardDetectionError, match="Image cannot be None"):
            detector.detect_cards(None)

    @patch('cv2.imread')
    def test_detect_cards_invalid_path(self, mock_imread, detector):
        """Test detect_cards with invalid image path"""
        mock_imread.return_value = None
        with pytest.raises(CardDetectionError, match="Failed to load image"):
            detector.detect_cards("invalid/path.jpg")

    def test_detect_cards_empty_image(self, detector):
        """Test detect_cards with empty image"""
        empty_image = np.array([])
        with pytest.raises(CardDetectionError, match="Image is empty"):
            detector.detect_cards(empty_image)

    def test_is_card_like_none_image(self, detector):
        """Test is_card_like with None image"""
        result = detector.is_card_like(None)
        assert result is False

    def test_is_card_like_empty_image(self, detector):
        """Test is_card_like with empty image"""
        empty_image = np.array([])
        result = detector.is_card_like(empty_image)
        assert result is False

    def test_is_card_like_low_contrast(self, detector):
        """Test is_card_like with low contrast image"""
        # Create a low contrast image (all pixels same value)
        low_contrast = np.full((100, 100, 3), 128, dtype=np.uint8)
        result = detector.is_card_like(low_contrast)
        assert result is False

    def test_is_card_like_high_contrast(self, detector):
        """Test is_card_like with high contrast image"""
        # Create a high contrast image with many edges (checkerboard pattern)
        high_contrast = np.zeros((100, 100, 3), dtype=np.uint8)
        # Create a checkerboard pattern that will have lots of edges
        for i in range(0, 100, 10):
            for j in range(0, 100, 10):
                if (i + j) // 10 % 2 == 0:
                    high_contrast[i:i+10, j:j+10] = 255
        result = detector.is_card_like(high_contrast)
        assert result is True

    @patch('cv2.imread')
    def test_calibrate_positions_invalid_image(self, mock_imread, detector):
        """Test calibrate_positions with invalid image"""
        mock_imread.return_value = None
        result = detector.calibrate_positions("invalid/path.jpg")
        assert result is None

    def test_calibrate_positions_with_manual_coords(self, detector):
        """Test calibrate_positions with manual coordinates"""
        # Create a mock image
        mock_image = np.zeros((1000, 1000, 3), dtype=np.uint8)

        manual_coords = {"hero_hole_1": (100, 200)}
        result = detector.calibrate_positions(mock_image, manual_coords)

        # Should return a dictionary with assignments
        assert isinstance(result, dict)
        assert "hero_hole_1" in result


if __name__ == "__main__":
    pytest.main([__file__])