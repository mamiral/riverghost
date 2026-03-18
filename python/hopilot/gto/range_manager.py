"""
Range Manager for YAML-based Poker Range Persistence

This module provides functionality to save and load poker hand ranges
in YAML format with validation and error handling.
"""

import os
from typing import List, Optional, Dict, Any
from pathlib import Path
import yaml
from hopilot.logging_config import get_logger
from hopilot.hand_range import PokerRange

logger = get_logger(__name__)


class RangeManager:
    """
    Manages persistence of poker hand ranges in YAML format.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize range manager with storage location.

        Args:
            storage_dir: Directory for YAML files (default: config/ranges/)
        """
        if storage_dir is None:
            # Default to config/ranges relative to the hopilot package
            hopilot_dir = Path(__file__).parent
            storage_dir = hopilot_dir.parent / "config" / "ranges"
        
        self.storage_dir = Path(storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"RangeManager initialized with storage dir: {self.storage_dir}")

    def save_range(self, range_obj: PokerRange, filename: Optional[str] = None) -> str:
        """
        Save a poker range to YAML file.

        Args:
            range_obj: PokerRange instance to save
            filename: Optional filename (default: generated from range name)

        Returns:
            Path to saved file

        Raises:
            IOError: If file cannot be written
            ValueError: If range_obj is invalid
        """
        if not isinstance(range_obj, PokerRange):
            raise ValueError("range_obj must be a PokerRange instance")

        if filename is None:
            # Generate filename from range name
            filename = self._sanitize_filename(range_obj.name) + ".yaml"
        
        if not filename.endswith('.yaml'):
            filename += '.yaml'

        file_path = self.storage_dir / filename

        try:
            # Convert to dict for YAML serialization
            range_dict = {
                'name': range_obj.name,
                'description': range_obj.description,
                'hands': range_obj.hands,
                'tags': range_obj.tags,
                'created': range_obj.created.isoformat(),
                'modified': range_obj.modified.isoformat()
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(range_dict, f, default_flow_style=False, sort_keys=False)

            logger.info(f"Saved range '{range_obj.name}' to {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Failed to save range to {file_path}: {e}")
            raise IOError(f"Failed to save range: {e}")

    def load_range(self, filename: str) -> PokerRange:
        """
        Load a poker range from YAML file.

        Args:
            filename: Name of YAML file (without .yaml extension if not included)

        Returns:
            PokerRange instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid or range data is malformed
        """
        if not filename.endswith('.yaml'):
            filename += '.yaml'

        file_path = self.storage_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Range file not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ValueError("Invalid YAML format: expected dictionary")

            # Validate required fields
            if 'name' not in data or 'hands' not in data:
                raise ValueError("YAML must contain 'name' and 'hands' fields")

            # Create PokerRange instance (validation happens in the model)
            range_obj = PokerRange(
                name=data['name'],
                description=data.get('description'),
                hands=data['hands'],
                tags=data.get('tags', [])
            )

            logger.info(f"Loaded range '{range_obj.name}' from {file_path}")
            return range_obj

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in {file_path}: {e}")
            raise ValueError(f"Invalid YAML format: {e}")
        except Exception as e:
            logger.error(f"Failed to load range from {file_path}: {e}")
            raise ValueError(f"Failed to load range: {e}")

    def list_ranges(self) -> List[str]:
        """
        List all available range files.

        Returns:
            List of range filenames (without .yaml extension)
        """
        try:
            yaml_files = list(self.storage_dir.glob("*.yaml"))
            range_names = [f.stem for f in yaml_files]
            return sorted(range_names)
        except Exception as e:
            logger.error(f"Failed to list ranges: {e}")
            return []

    def delete_range(self, filename: str) -> bool:
        """
        Delete a range file.

        Args:
            filename: Name of range file to delete

        Returns:
            True if deleted, False if not found

        Raises:
            IOError: If deletion fails
        """
        if not filename.endswith('.yaml'):
            filename += '.yaml'

        file_path = self.storage_dir / filename

        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            logger.info(f"Deleted range file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete range file {file_path}: {e}")
            raise IOError(f"Failed to delete range file: {e}")

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a range name for use as a filename.
        
        Args:
            name: Range name
            
        Returns:
            Sanitized filename (lowercase, hyphens instead of spaces/special chars)
        """
        import re
        # Convert to lowercase, replace spaces/special chars with hyphens
        sanitized = re.sub(r'[^a-zA-Z0-9]', '-', name.lower())
        # Remove multiple consecutive hyphens
        sanitized = re.sub(r'-+', '-', sanitized)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip('-')
        return sanitized or 'unnamed-range'