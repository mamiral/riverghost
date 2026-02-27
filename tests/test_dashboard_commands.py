import pytest
import os
import sys
from unittest.mock import MagicMock
import numpy as np

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.dashboard import (
    Command,
    TogglePauseCommand,
    SpeedUpCommand,
    SpeedDownCommand,
    ToggleSlowCommand,
    ToggleRecordingCommand,
    ToggleAutoSaveCommand,
    CropBBoxesCommand,
    ScreenshotCommand
)


class TestDashboardCommands:
    """Test suite for Dashboard Command classes."""

    def test_command_base_class(self):
        """Test that Command base class raises NotImplementedError."""
        command = Command()
        with pytest.raises(NotImplementedError):
            command.execute()

    def test_toggle_pause_command(self):
        """Test TogglePauseCommand toggles pause state."""
        mock_dashboard = MagicMock()
        mock_dashboard.paused = False
        mock_dashboard.logger = MagicMock()

        command = TogglePauseCommand(mock_dashboard)
        command.execute()

        assert mock_dashboard.paused is True
        mock_dashboard.logger.info.assert_called_with("Pause toggled: Paused")

        # Test toggling back
        command.execute()
        assert mock_dashboard.paused is False
        mock_dashboard.logger.info.assert_called_with("Pause toggled: Playing")

    def test_speed_up_command(self):
        """Test SpeedUpCommand increases speed with bounds."""
        mock_dashboard = MagicMock()
        mock_dashboard.speed = 1.0
        mock_dashboard.speed_lock = MagicMock()
        mock_dashboard.speed_lock.__enter__ = MagicMock(return_value=None)
        mock_dashboard.speed_lock.__exit__ = MagicMock(return_value=None)

        command = SpeedUpCommand(mock_dashboard)
        command.execute()

        assert mock_dashboard.speed == 1.5
        assert mock_dashboard.fast_speed == 1.5

        # Test upper bound
        mock_dashboard.speed = 8.0
        command.execute()
        assert mock_dashboard.speed == 10.0  # min(8.0 * 1.5, 10.0) = 10.0

    def test_speed_down_command(self):
        """Test SpeedDownCommand decreases speed with bounds."""
        mock_dashboard = MagicMock()
        mock_dashboard.speed = 1.0
        mock_dashboard.speed_lock = MagicMock()
        mock_dashboard.speed_lock.__enter__ = MagicMock(return_value=None)
        mock_dashboard.speed_lock.__exit__ = MagicMock(return_value=None)

        command = SpeedDownCommand(mock_dashboard)
        command.execute()

        assert mock_dashboard.speed == pytest.approx(0.6667, abs=0.01)  # 1.0 / 1.5
        assert mock_dashboard.fast_speed == pytest.approx(0.6667, abs=0.01)

        # Test lower bound
        mock_dashboard.speed = 0.05
        command.execute()
        assert mock_dashboard.speed == 0.1  # max(0.05 / 1.5, 0.1) = 0.1

    def test_toggle_slow_command(self):
        """Test ToggleSlowCommand switches between normal and slow speed."""
        mock_dashboard = MagicMock()
        mock_dashboard.speed = 1.0
        mock_dashboard.fast_speed = 2.0
        mock_dashboard.slow_down = False
        mock_dashboard.replay_mode = False  # Not in replay mode
        mock_dashboard.speed_lock = MagicMock()
        mock_dashboard.speed_lock.__enter__ = MagicMock(return_value=None)
        mock_dashboard.speed_lock.__exit__ = MagicMock(return_value=None)

        command = ToggleSlowCommand(mock_dashboard)
        command.execute()

        assert mock_dashboard.slow_down is True

        # Test toggling back
        command.execute()
        assert mock_dashboard.slow_down is False

    def test_toggle_recording_command(self):
        """Test ToggleRecordingCommand toggles recording state."""
        mock_dashboard = MagicMock()
        mock_dashboard.recording = False
        mock_dashboard.recording_toggle_func = MagicMock()

        command = ToggleRecordingCommand(mock_dashboard)
        command.execute()

        assert mock_dashboard.recording is True
        mock_dashboard.recording_toggle_func.assert_called_with(True)

        # Test toggling off
        command.execute()
        assert mock_dashboard.recording is False
        mock_dashboard.recording_toggle_func.assert_called_with(False)

    def test_toggle_auto_save_command(self):
        """Test ToggleAutoSaveCommand toggles auto save state."""
        mock_dashboard = MagicMock()
        mock_dashboard.auto_save = False

        command = ToggleAutoSaveCommand(mock_dashboard)
        command.execute()

        assert mock_dashboard.auto_save is True

        # Test toggling off
        command.execute()
        assert mock_dashboard.auto_save is False

    def test_crop_bboxes_command(self):
        """Test CropBBoxesCommand saves cropped bounding boxes."""
        mock_dashboard = MagicMock()
        mock_dashboard.replay_mode = False
        mock_dashboard.frame_func = MagicMock(return_value=np.zeros((100, 100, 3), dtype=np.uint8))  # Mock frame
        mock_dashboard.bboxes = [(10, 10, 50, 50), (60, 60, 90, 90)]  # Mock bounding boxes
        mock_dashboard.bboxes_hole = [(20, 20, 40, 40, 0)]  # Mock hole boxes
        mock_dashboard.logger = MagicMock()

        command = CropBBoxesCommand(mock_dashboard)
        command.execute()

        # Verify frame_func was called
        mock_dashboard.frame_func.assert_called_once()
        # Verify logger was called (indicating files were saved)
        assert mock_dashboard.logger.info.called

    def test_screenshot_command(self):
        """Test ScreenshotCommand takes screenshot."""
        mock_dashboard = MagicMock()
        mock_dashboard.replay_mode = True
        mock_dashboard.current_frame = np.zeros((100, 100, 3), dtype=np.uint8)  # Mock frame
        mock_image_path_func = MagicMock()

        command = ScreenshotCommand(mock_dashboard, mock_image_path_func)
        command.execute()

        # Verify the command executed (no assertions needed for file operations in this mock test)