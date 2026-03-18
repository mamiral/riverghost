from pathlib import Path
from typing import Dict, Any
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PrecomputeConfig(BaseModel):
    """Configuration for precompute operations in AOF GTO Browser."""

    model_config = ConfigDict(validate_assignment=True)

    max_workers: int = Field(default=4, ge=1, le=16, description="Thread pool size for concurrent processing")
    simulations_per_cell: int = Field(default=1000, ge=100, le=50000, description="Base number of simulations per cell")

    @property
    def step_sizes(self) -> Dict[str, int]:
        """Adjustment step sizes for UI controls."""
        return {
            'coarse': 1000 if self.simulations_per_cell < 5000 else 5000,
            'fine': 100 if self.simulations_per_cell < 5000 else 500
        }

    @classmethod
    def from_yaml(cls, config_path: Path) -> 'PrecomputeConfig':
        """Load configuration from YAML file."""
        if not config_path.exists():
            return cls()

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            print(f"Warning: Failed to parse config file {config_path}: {e}")
            return cls()

        aof_config = data.get('aof_browser_runtime', {})

        return cls(
            max_workers=aof_config.get('precompute_max_workers'),
            simulations_per_cell=aof_config.get('num_simulations', 1000)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'max_workers': self.max_workers,
            'simulations_per_cell': self.simulations_per_cell
        }

    def update(self, **kwargs) -> None:
        """Update configuration values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @field_validator('max_workers')
    @classmethod
    def validate_max_workers(cls, v):
        """Validate max_workers is within allowed range."""
        if not isinstance(v, int) or v < 1 or v > 16:
            raise ValueError('max_workers must be an integer between 1 and 16')
        return v

    @field_validator('simulations_per_cell')
    @classmethod
    def validate_simulations_per_cell(cls, v):
        """Validate simulations_per_cell is within allowed range."""
        if not isinstance(v, int) or v < 100 or v > 50000:
            raise ValueError('simulations_per_cell must be an integer between 100 and 50000')
        return v

