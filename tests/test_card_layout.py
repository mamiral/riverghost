import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from hopilot.card_layout import CardLayout
from hopilot.config import AppConfig, GameModeConfig


class TestCardLayout:
    """Test suite for CardLayout class."""

    def test_card_layout_init_default(self):
        """Test CardLayout initialization with default parameters."""
        layout = CardLayout()
        assert layout.game_mode == "rush_n_cash"
        assert layout.tolerance == 20
        assert isinstance(layout.slots, dict)

    def test_card_layout_init_custom_game_mode(self):
        """Test CardLayout initialization with custom game mode."""
        layout = CardLayout(game_mode="rush_n_cash")
        assert layout.game_mode == "rush_n_cash"

    @patch('hopilot.card_layout.load_config')
    def test_card_layout_init_with_config(self, mock_load_config):
        """Test CardLayout initialization with provided config."""
        mock_config = MagicMock()
        mock_config.game_modes = {
            "test_mode": MagicMock(slots={"slot1": [1, 2, 3, 4, 5]})
        }

        layout = CardLayout(game_mode="test_mode", config=mock_config)
        assert layout.game_mode == "test_mode"
        mock_load_config.assert_not_called()

    @patch('hopilot.card_layout.load_config')
    def test_card_layout_init_config_fallback(self, mock_load_config):
        """Test CardLayout initialization with config fallback to DEFAULT_CONFIG."""
        # Simulate FileNotFoundError
        mock_load_config.side_effect = FileNotFoundError()

        with patch('hopilot.config.DEFAULT_CONFIG') as mock_default_config:
            mock_default_config.game_modes = {
                "rush_n_cash": MagicMock(slots={"slot1": [1, 2, 3, 4, 5]})
            }

            layout = CardLayout()
            assert layout.game_mode == "rush_n_cash"
            mock_load_config.assert_called_once()

    def test_card_layout_init_invalid_game_mode(self):
        """Test CardLayout initialization with invalid game mode raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CardLayout(game_mode="invalid_mode")

        assert "Unknown game mode: invalid_mode" in str(exc_info.value)
        assert "Available modes:" in str(exc_info.value)

    @patch('hopilot.card_layout.load_config')
    def test_card_layout_init_invalid_game_mode_with_config(self, mock_load_config):
        """Test CardLayout initialization with invalid game mode and custom config."""
        mock_config = MagicMock()
        mock_config.game_modes = {
            "valid_mode": MagicMock(slots={"slot1": [1, 2, 3, 4, 5]})
        }

        with pytest.raises(ValueError) as exc_info:
            CardLayout(game_mode="invalid_mode", config=mock_config)

        assert "Unknown game mode: invalid_mode" in str(exc_info.value)
        assert "Available modes: ['valid_mode']" in str(exc_info.value)

    def test_card_layout_get_board_bboxes(self):
        """Test get_board_bboxes returns correct bounding boxes."""
        layout = CardLayout()

        # Mock the slots to have predictable values
        layout.slots = {
            "flop_1": [10, 20, 30, 40, 5],
            "flop_2": [50, 60, 70, 80, 5],
            "flop_3": [90, 100, 110, 120, 5],
            "turn": [130, 140, 150, 160, 5],
            "river": [170, 180, 190, 200, 5]
        }

        bboxes = layout.get_board_bboxes()
        expected = [
            [10, 20, 30, 40],    # flop_1 (angle excluded)
            [50, 60, 70, 80],    # flop_2
            [90, 100, 110, 120], # flop_3
            [130, 140, 150, 160], # turn
            [170, 180, 190, 200]  # river
        ]
        assert bboxes == expected

    def test_card_layout_get_hole_bboxes(self):
        """Test get_hole_bboxes returns correct bounding boxes with angles."""
        layout = CardLayout()

        # Mock the slots to have predictable values
        layout.slots = {
            "hero_hole_1": [10, 20, 30, 40, 5],
            "hero_hole_2": [50, 60, 70, 80, 15]
        }

        bboxes = layout.get_hole_bboxes()
        expected = [
            [10, 20, 30, 40, 5],   # hero_hole_1 (angle included)
            [50, 60, 70, 80, 15]   # hero_hole_2
        ]
        assert bboxes == expected

    def test_card_layout_slots_copy(self):
        """Test that slots are copied to prevent external modification."""
        original_layout = CardLayout()
        original_slots = original_layout.slots.copy()

        # Modify the original slots
        if "flop_1" in original_layout.slots:
            original_layout.slots["flop_1"] = [999, 999, 999, 999, 999]

        # Create new layout - should not be affected
        new_layout = CardLayout()
        assert new_layout.slots == original_slots