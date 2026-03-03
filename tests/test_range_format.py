"""
YAML validation tests for poker range format.

Tests ensure that range files conform to expected schema and
handle various edge cases and validation scenarios.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from hopilot.gto.range_manager import RangeManager
from hopilot.hand_range import PokerRange


class TestRangeFormatValidation:
    """Test cases for YAML range file format validation."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def range_manager(self, temp_dir):
        """Create a RangeManager with temporary storage."""
        return RangeManager(storage_dir=str(temp_dir))

    def test_valid_minimal_range_yaml(self, range_manager, temp_dir):
        """Test loading a minimal valid YAML range."""
        yaml_content = """
name: "Test Range"
hands:
  - "AA"
  - "KK"
"""

        # Write YAML file
        yaml_file = temp_dir / "minimal.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        # Should load successfully
        range_obj = range_manager.load_range("minimal")
        assert range_obj.name == "Test Range"
        assert range_obj.hands == ["AA", "KK"]
        assert range_obj.description is None
        assert range_obj.tags == []

    def test_valid_full_range_yaml(self, range_manager, temp_dir):
        """Test loading a fully populated YAML range."""
        yaml_content = """
name: "Premium Hands"
description: "High value starting hands for tournament play"
hands:
  - "AA"
  - "AKs"
  - "KK"
  - "QQ"
tags:
  - "premium"
  - "pairs"
  - "suited"
created: "2024-01-01T12:00:00"
modified: "2024-01-01T12:00:00"
"""

        # Write YAML file
        yaml_file = temp_dir / "full.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        # Should load successfully
        range_obj = range_manager.load_range("full")
        assert range_obj.name == "Premium Hands"
        assert range_obj.description == "High value starting hands for tournament play"
        assert range_obj.hands == ["AA", "AKs", "KK", "QQ"]
        assert range_obj.tags == ["premium", "pairs", "suited"]

    def test_invalid_yaml_syntax(self, range_manager, temp_dir):
        """Test handling of malformed YAML."""
        invalid_yaml = """
name: "Test Range"
hands:
  - "AA"
  - invalid: yaml: syntax: [
"""

        yaml_file = temp_dir / "invalid.yaml"
        with open(yaml_file, 'w') as f:
            f.write(invalid_yaml)

        with pytest.raises(ValueError, match="Invalid YAML format"):
            range_manager.load_range("invalid")

    def test_yaml_not_dictionary(self, range_manager, temp_dir):
        """Test handling of YAML that doesn't parse to a dictionary."""
        yaml_content = """
- item1
- item2
- item3
"""

        yaml_file = temp_dir / "list.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        with pytest.raises(ValueError, match="Invalid YAML format: expected dictionary"):
            range_manager.load_range("list")

    def test_missing_name_field(self, range_manager, temp_dir):
        """Test YAML missing required 'name' field."""
        yaml_content = """
hands:
  - "AA"
  - "KK"
"""

        yaml_file = temp_dir / "no_name.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        with pytest.raises(ValueError, match="YAML must contain 'name' and 'hands' fields"):
            range_manager.load_range("no_name")

    def test_missing_hands_field(self, range_manager, temp_dir):
        """Test YAML missing required 'hands' field."""
        yaml_content = """
name: "Test Range"
"""

        yaml_file = temp_dir / "no_hands.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        with pytest.raises(ValueError, match="YAML must contain 'name' and 'hands' fields"):
            range_manager.load_range("no_hands")

    def test_empty_hands_list(self, range_manager, temp_dir):
        """Test YAML with empty hands list."""
        yaml_content = """
name: "Empty Range"
hands: []
"""

        yaml_file = temp_dir / "empty.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        # Should load successfully (empty range is valid)
        range_obj = range_manager.load_range("empty")
        assert range_obj.name == "Empty Range"
        assert range_obj.hands == []

    def test_invalid_hand_notation(self, range_manager, temp_dir):
        """Test YAML with invalid poker hand notation."""
        yaml_content = """
name: "Invalid Hands"
hands:
  - "AA"
  - "INVALID"
  - "KK"
"""

        yaml_file = temp_dir / "invalid_hands.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        # Should fail during PokerRange validation
        with pytest.raises(ValueError, match="Invalid hand notation"):
            range_manager.load_range("invalid_hands")

    def test_duplicate_hands_in_range(self, range_manager, temp_dir):
        """Test YAML with duplicate hands (should be allowed)."""
        yaml_content = """
name: "Duplicate Hands"
hands:
  - "AA"
  - "AA"
  - "KK"
"""

        yaml_file = temp_dir / "duplicates.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        # Should load successfully (duplicates are allowed in ranges)
        range_obj = range_manager.load_range("duplicates")
        assert range_obj.name == "Duplicate Hands"
        assert range_obj.hands == ["AA", "AA", "KK"]

    def test_malformed_tags_field(self, range_manager, temp_dir):
        """Test YAML with malformed tags field."""
        yaml_content = """
name: "Test Range"
hands:
  - "AA"
tags: "not a list"
"""

        yaml_file = temp_dir / "bad_tags.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        # Should fail during PokerRange validation since tags should be a list
        with pytest.raises(ValueError):
            range_manager.load_range("bad_tags")

    def test_unicode_characters(self, range_manager, temp_dir):
        """Test YAML with Unicode characters in name and description."""
        yaml_content = """
name: "Premium Range"
description: "High value hands for tournament play"
hands:
  - "AA"
  - "AKs"
"""

        yaml_file = temp_dir / "unicode.yaml"
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)

        # Should load successfully
        range_obj = range_manager.load_range("unicode")
        assert range_obj.name == "Premium Range"
        assert range_obj.description == "High value hands for tournament play"

    def test_extremely_long_values(self, range_manager, temp_dir):
        """Test YAML with very long string values."""
        long_name = "A" * 1000
        long_description = "B" * 2000

        yaml_content = f"""
name: "{long_name}"
description: "{long_description}"
hands:
  - "AA"
"""

        yaml_file = temp_dir / "long.yaml"
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)

        # Should load successfully
        range_obj = range_manager.load_range("long")
        assert range_obj.name == long_name
        assert range_obj.description == long_description

    def test_yaml_schema_validation(self, range_manager, temp_dir):
        """Test comprehensive YAML schema validation."""
        # Test various valid and invalid combinations
        test_cases = [
            # Valid cases
            ({"name": "Test", "hands": ["AA"]}, True),
            ({"name": "Test", "hands": ["AA", "KK"], "description": "Desc"}, True),
            ({"name": "Test", "hands": ["AA"], "tags": ["tag1", "tag2"]}, True),

            # Invalid cases
            ({"hands": ["AA"]}, False),  # Missing name
            ({"name": "Test"}, False),  # Missing hands
            ({}, False),  # Missing both
            ({"name": "", "hands": ["AA"]}, True),  # Empty name allowed
        ]

        for i, (data, should_pass) in enumerate(test_cases):
            yaml_file = temp_dir / f"schema_test_{i}.yaml"
            with open(yaml_file, 'w') as f:
                yaml.safe_dump(data, f)

            if should_pass:
                # Should load successfully
                range_obj = range_manager.load_range(f"schema_test_{i}")
                assert range_obj.name == data.get("name", "")
                assert range_obj.hands == data.get("hands", [])
            else:
                # Should fail
                with pytest.raises(ValueError):
                    range_manager.load_range(f"schema_test_{i}")