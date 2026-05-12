from pathlib import Path
from typing import Dict, Any
import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PrecomputeConfig(BaseModel):
    """Configuration for precompute operations in AOF GTO Browser."""

    model_config = ConfigDict(validate_assignment=True)

    max_workers: int = Field(default=4, ge=1, le=16, description="Thread pool size for concurrent processing")
    simulations_per_cell: int = Field(default=1000, ge=100, le=50000, description="Base number of simulations per cell")
    bb: float = Field(default=1.0, gt=0, description="Big blind size for EV/EQR calculations")
    rake: float = Field(default=0.0, ge=0, le=1, description="Rake percentage (0.0 to 1.0)")
    convergence_tracking_enabled: bool = Field(default=False, description="Enable convergence tracking during aggregation")
    convergence_emit_interval: int = Field(default=100, ge=10, le=1000, description="Sample count interval for convergence emissions")

    @property
    def sb(self) -> float:
        """Small blind, derived from big blind."""
        return 0.5 * self.bb

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
            simulations_per_cell=aof_config.get('num_simulations', 1000),
            bb=aof_config.get('bb', 1.0),
            rake=aof_config.get('rake', 0.0),
            convergence_tracking_enabled=aof_config.get('convergence_tracking_enabled', False),
            convergence_emit_interval=aof_config.get('convergence_emit_interval', 100)
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'max_workers': self.max_workers,
            'simulations_per_cell': self.simulations_per_cell,
            'bb': self.bb,
            'rake': self.rake,
            'convergence_tracking_enabled': self.convergence_tracking_enabled,
            'convergence_emit_interval': self.convergence_emit_interval
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

