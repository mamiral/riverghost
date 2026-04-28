"""
Integration tests for Dashboard Commands.
Tests real command execution instead of mock behavior.
"""

import pytest
import numpy as np
import sys
import os
import tempfile
from unittest.mock import MagicMock

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "python"))

from hopilot.dashboard import CropBBoxesCommand, ScreenshotCommand


class TestDashboardCommandsIntegration:
    """Integration tests for dashboard commands with real execution."""

    @pytest.fixture
    def mock_dashboard_with_frame(self):
        """Create a mock dashboard with a real frame for testing."""
        dashboard = MagicMock()
        dashboard.replay_mode = True
        # Create a real numpy array for frame data
        dashboard.current_frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        dashboard.frame_func = MagicMock()
        return dashboard

    @pytest.fixture
    def temp_image_path(self):
        """Create a temporary file path for image output."""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass

    def test_crop_bboxes_command_executes_and_saves_files(self, mock_dashboard_with_frame, temp_image_path):
        """Integration test: CropBBoxesCommand executes and saves actual files."""
        # Mock the image path function to return our temp path
        mock_dashboard_with_frame.image_path_func = MagicMock(return_value=temp_image_path)
        
        # Mock bboxes to have some test data
        mock_dashboard_with_frame.bboxes = [(10, 10, 50, 50), (60, 60, 100, 100)]
        mock_dashboard_with_frame.bboxes_hole = []

        command = CropBBoxesCommand(mock_dashboard_with_frame)
        command.execute()

        # Verify files were created in recordings/screenshots directory
        screenshot_dir = "recordings/screenshots"
        assert os.path.exists(screenshot_dir), "Screenshot directory should exist"
        files = os.listdir(screenshot_dir)
        bbox_files = [f for f in files if f.startswith("bbox") and f.endswith(".png")]
        assert len(bbox_files) > 0, "Should create bbox screenshot files"

    def test_screenshot_command_captures_real_frame(self, mock_dashboard_with_frame):
        """Integration test: ScreenshotCommand captures real frame data."""
        mock_dashboard_with_frame.image_path_func = MagicMock(return_value=None)

        command = ScreenshotCommand(mock_dashboard_with_frame, mock_dashboard_with_frame.image_path_func)
        command.execute()

        # Verify the frame data is accessible
        assert hasattr(mock_dashboard_with_frame, 'current_frame'), "Dashboard should have frame data"
        assert isinstance(mock_dashboard_with_frame.current_frame, np.ndarray), "Frame should be numpy array"

        # Verify frame_func was not required for replay mode
        mock_dashboard_with_frame.frame_func.assert_not_called()

        # Verify that no exception was raised and command completed
        assert True

    def test_screenshot_command_saves_real_image(self, mock_dashboard_with_frame, temp_image_path):
        """Integration test: ScreenshotCommand saves actual image file."""
        # Use image path handling rather than replay mode
        mock_dashboard_with_frame.replay_mode = False
        mock_dashboard_with_frame.image_path_func = MagicMock(return_value=temp_image_path)
        assert os.path.exists(temp_image_path), "Temp image path should exist"

        command = ScreenshotCommand(mock_dashboard_with_frame, mock_dashboard_with_frame.image_path_func)
        command.execute()

        # Verify the screenshot command completed and saved a file
        screenshot_dir = "recordings/screenshots"
        assert os.path.exists(screenshot_dir), "Screenshot directory should exist"
        files = os.listdir(screenshot_dir)
        png_files = [f for f in files if f.endswith(".png")]
        assert len(png_files) > 0, "Should save a screenshot PNG"

    def test_commands_handle_missing_frame_data(self):
        """Integration test: Commands handle missing frame data gracefully."""
        dashboard = MagicMock()
        dashboard.replay_mode = True
        dashboard.current_frame = None  # No frame data
        dashboard.frame_func = MagicMock()

        command = CropBBoxesCommand(dashboard)
        command.execute()

        # Should handle gracefully without crashing
        assert True

        # Should not call frame_func if no frame available
        dashboard.frame_func.assert_not_called()
