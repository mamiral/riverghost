"""
Tests for card matching functionality using pytest.
Tests use the validation data moved to tests/data directory.
"""

import pytest
import os
from pathlib import Path
from python.hopilot.card_matcher import CardMatcher, detect_card_color, classify_suite
import cv2
import numpy as np


class TestCardMatcher:
    """Test suite for CardMatcher class"""

    @pytest.fixture
    def card_matcher(self):
        """Fixture to provide CardMatcher instance"""
        return CardMatcher(templates_dir='python/hopilot/templates')

    @pytest.fixture
    def test_data_dir(self):
        """Fixture to provide path to test data"""
        return Path(__file__).parent / 'data'

    def test_card_matcher_initialization(self, card_matcher):
        """Test that CardMatcher initializes correctly"""
        assert isinstance(card_matcher, CardMatcher)
        assert hasattr(card_matcher, 'rank_templates')
        assert isinstance(card_matcher.rank_templates, dict)

    def test_recognize_card_structure(self, card_matcher):
        """Test that recognize_card returns proper structure"""
        # Test with non-existent file
        result = card_matcher.recognize_card('nonexistent.png')
        assert result['suite'] is None
        assert result['rank'] is None
        assert result['success'] is False
        assert 'error' in result

    @pytest.mark.parametrize("suite_name", ["clubs", "diamonds", "hearts", "spades"])
    def test_suite_recognition_accuracy(self, card_matcher, test_data_dir, suite_name):
        """Test suite recognition accuracy using validation data"""
        suite_dir = test_data_dir / suite_name
        if not suite_dir.exists():
            pytest.skip(f"Suite directory {suite_name} not found in test data")

        correct_predictions = 0
        total_predictions = 0

        # Test a sample of cards from each suite
        for rank_dir in suite_dir.iterdir():
            if not rank_dir.is_dir():
                continue

            # Test up to 3 cards per rank to keep tests fast
            card_files = list(rank_dir.glob('*.png'))[:3]

            for card_file in card_files:
                result = card_matcher.recognize_card(card_file)
                total_predictions += 1

                if result['suite'] == suite_name:
                    correct_predictions += 1

        if total_predictions > 0:
            accuracy = correct_predictions / total_predictions
            # Allow some tolerance for recognition errors
            assert accuracy >= 0.8, f"Suite {suite_name} recognition accuracy too low: {accuracy:.2f}"

    def test_rank_recognition(self, card_matcher, test_data_dir):
        """Test that rank recognition works for known cards"""
        # Test a few specific cards
        test_cases = [
            ("clubs", "A"),
            ("diamonds", "K"),
            ("hearts", "Q"),
            ("spades", "J"),
        ]

        for expected_suite, expected_rank in test_cases:
            # Find any file in that directory
            card_files = list((test_data_dir / expected_suite / expected_rank).glob('*.png'))
            if not card_files:
                continue
            full_path = card_files[0]

            result = card_matcher.recognize_card(full_path)

            # Check that we got some result
            assert result['rank'] is not None, f"Failed to recognize rank for {full_path}"
            assert result['rank_score'] > 0, f"Rank score should be positive for {full_path}"


class TestColorDetection:
    """Test color detection functions"""

    @pytest.mark.parametrize("bgr,color", [
        ([255, 255, 255], "white"),  # White pixels
        ([0, 0, 200], "red"),        # Red dominant (BGR: B=0, G=0, R=200)
        ([0, 200, 0], "green"),      # Green dominant (BGR: B=0, G=200, R=0)
        ([200, 0, 0], "blue"),       # Blue dominant (BGR: B=200, G=0, R=0)
        ([30, 30, 30], "black"),     # Dark pixels
        ([100, 100, 100], "unknown"), # Gray/unknown
    ])
    def test_detect_card_color(self, bgr, color):
        """Test color detection with various BGR values"""
        result = detect_card_color(np.array(bgr))
        assert result == color

    def test_classify_suite_structure(self):
        """Test that classify_suite returns proper structure"""
        # Create a dummy image
        dummy_image = np.zeros((40, 20, 3), dtype=np.uint8)

        suite_name, rank_crop = classify_suite(dummy_image)

        assert isinstance(suite_name, str)
        assert rank_crop.shape[0] == 18  # Should be cropped to top 18 pixels
        assert rank_crop.shape[2] == 3   # Should be BGR


class TestTemplateMatching:
    """Test template matching functionality"""

    @pytest.fixture
    def sample_templates(self):
        """Create sample templates for testing"""
        templates = {}
        # Create simple 5x5 templates
        for name in ['A', 'K', 'Q', 'J']:
            template = np.random.rand(5, 5).astype(np.float32)
            templates[name] = template
        return templates

    def test_template_loading(self):
        """Test that templates can be loaded"""
        matcher = CardMatcher()
        # Should load templates if templates directory exists
        assert isinstance(matcher.rank_templates, dict)

    def test_correlation_matching(self, sample_templates):
        """Test correlation-based template matching"""
        from python.hopilot.card_matcher import match_template_correlation

        # Create a test image larger than template
        test_image = np.random.rand(10, 10).astype(np.float32)

        result = match_template_correlation(test_image, sample_templates['A'])
        assert result is not None
        score, confidence = result
        assert isinstance(score, float)
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1