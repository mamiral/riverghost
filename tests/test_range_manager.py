"""
Unit tests for RangeManager functionality.

Tests cover saving, loading, listing, and deleting poker hand ranges
in YAML format with proper validation and error handling.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, mock_open
from hopilot.gto.range_manager import RangeManager
from hopilot.hand_range import PokerRange


class TestRangeManager:
    """Test cases for RangeManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def range_manager(self, temp_dir):
        """Create a RangeManager with temporary storage."""
        return RangeManager(storage_dir=str(temp_dir))

    @pytest.fixture
    def sample_range(self):
        """Create a sample PokerRange for testing."""
        return PokerRange(
            name="Premium Pairs",
            description="High pocket pairs for tournament play",
            hands=["AA", "KK", "QQ", "JJ"],
            tags=["premium", "pairs", "tournament"]
        )

    def test_init_default_storage(self):
        """Test RangeManager initialization with default storage."""
        manager = RangeManager()
        expected_path = Path(__file__).parent.parent / "python" / "hopilot" / "config" / "ranges"
        assert manager.storage_dir == expected_path

    def test_init_custom_storage(self, temp_dir):
        """Test RangeManager initialization with custom storage."""
        manager = RangeManager(storage_dir=str(temp_dir))
        assert manager.storage_dir == temp_dir

    def test_save_range_auto_filename(self, range_manager, sample_range):
        """Test saving a range with auto-generated filename."""
        file_path = range_manager.save_range(sample_range)

        # Check file was created
        assert os.path.exists(file_path)

        # Check filename generation
        expected_name = "premium-pairs.yaml"
        assert file_path.endswith(expected_name)

    def test_save_range_custom_filename(self, range_manager, sample_range):
        """Test saving a range with custom filename."""
        custom_name = "my_custom_range.yaml"
        file_path = range_manager.save_range(sample_range, filename=custom_name)

        assert file_path.endswith(custom_name)
        assert os.path.exists(file_path)

    def test_save_range_invalid_type(self, range_manager):
        """Test saving invalid range type raises error."""
        with pytest.raises(ValueError, match="range_obj must be a PokerRange instance"):
            range_manager.save_range("not a range")

    def test_load_range_success(self, range_manager, sample_range):
        """Test loading a range successfully."""
        # Save first
        file_path = range_manager.save_range(sample_range)

        # Load it back
        loaded_range = range_manager.load_range("premium-pairs")

        assert loaded_range.name == sample_range.name
        assert loaded_range.description == sample_range.description
        assert loaded_range.hands == sample_range.hands
        assert loaded_range.tags == sample_range.tags

    def test_load_range_file_not_found(self, range_manager):
        """Test loading non-existent range raises error."""
        with pytest.raises(FileNotFoundError, match="Range file not found"):
            range_manager.load_range("nonexistent")

    def test_load_range_invalid_yaml(self, range_manager, temp_dir):
        """Test loading invalid YAML raises error."""
        # Create invalid YAML file
        invalid_file = temp_dir / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            f.write("invalid: yaml: content: [\n")

        with pytest.raises(ValueError, match="Invalid YAML format"):
            range_manager.load_range("invalid")

    def test_load_range_missing_required_fields(self, range_manager, temp_dir):
        """Test loading YAML with missing required fields."""
        # Create YAML missing 'hands' field
        invalid_file = temp_dir / "missing_hands.yaml"
        with open(invalid_file, 'w') as f:
            f.write("name: Test Range\n")

        with pytest.raises(ValueError, match="YAML must contain 'name' and 'hands' fields"):
            range_manager.load_range("missing_hands")

    def test_list_ranges_empty(self, range_manager):
        """Test listing ranges when none exist."""
        ranges = range_manager.list_ranges()
        assert ranges == []

    def test_list_ranges_with_files(self, range_manager, sample_range):
        """Test listing ranges with existing files."""
        # Save multiple ranges
        range_manager.save_range(sample_range)
        range2 = PokerRange(name="Broadway Cards", hands=["AKs", "AQs", "AJs"])
        range_manager.save_range(range2)

        ranges = range_manager.list_ranges()
        assert len(ranges) == 2
        assert "broadway-cards" in ranges
        assert "premium-pairs" in ranges
        assert ranges == sorted(ranges)  # Should be sorted

    def test_delete_range_success(self, range_manager, sample_range):
        """Test deleting a range successfully."""
        # Save first
        range_manager.save_range(sample_range)

        # Delete it
        result = range_manager.delete_range("premium-pairs")
        assert result is True

        # Verify it's gone
        ranges = range_manager.list_ranges()
        assert "premium-pairs" not in ranges

    def test_delete_range_not_found(self, range_manager):
        """Test deleting non-existent range returns False."""
        result = range_manager.delete_range("nonexistent")
        assert result is False

    def test_sanitize_filename(self, range_manager):
        """Test filename sanitization."""
        test_cases = [
            ("Premium Pairs", "premium-pairs"),
            ("Broadway Cards!", "broadway-cards"),
            ("Test---Range", "test-range"),
            ("", "unnamed-range"),
            ("A B C", "a-b-c"),
            ("123 Test", "123-test"),
        ]

        for input_name, expected in test_cases:
            result = range_manager._sanitize_filename(input_name)
            assert result == expected

    def test_save_load_roundtrip(self, range_manager):
        """Test that save/load preserves all data correctly."""
        original = PokerRange(
            name="Complex Range",
            description="A range with many hands and tags",
            hands=["AA", "AKs", "AQs", "AJs", "ATs", "AKo", "KK", "QQ"],
            tags=["mixed", "broadway", "premium"]
        )

        # Save and load
        range_manager.save_range(original)
        loaded = range_manager.load_range("complex-range")

        # Compare all fields
        assert loaded.name == original.name
        assert loaded.description == original.description
        assert loaded.hands == original.hands
        assert loaded.tags == original.tags
        # Note: created/modified times will differ slightly due to serialization

    @patch('builtins.open', new_callable=mock_open)
    def test_save_range_io_error(self, mock_file, range_manager, sample_range):
        """Test handling of IO errors during save."""
        mock_file.side_effect = IOError("Disk full")

        with pytest.raises(IOError, match="Failed to save range"):
            range_manager.save_range(sample_range)

    @patch('pathlib.Path.unlink')
    def test_delete_range_io_error(self, mock_unlink, range_manager, temp_dir):
        """Test handling of IO errors during delete."""
        # Create a file first
        test_file = temp_dir / "test.yaml"
        test_file.touch()

        mock_unlink.side_effect = OSError("Permission denied")

        with pytest.raises(IOError, match="Failed to delete range file"):
            range_manager.delete_range("test")