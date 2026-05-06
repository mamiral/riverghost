from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator


class GameModeConfig(BaseModel):
    """Configuration for a specific poker game mode."""

    slots: Dict[str, List[float]] = Field(
        ..., description="Card slot positions [x1, y1, x2, y2, angle]"
    )

    @field_validator("slots")
    @classmethod
    def validate_slots(cls, v):
        required_slots = [
            "hero_hole_1",
            "hero_hole_2",
            "flop_1",
            "flop_2",
            "flop_3",
            "turn",
            "river",
        ]
        for slot in required_slots:
            if slot not in v:
                raise ValueError(
                    f"Required slot '{slot}' missing from game mode configuration"
                )
        return v


class DetectionConfig(BaseModel):
    """Configuration for card detection."""

    confidence_threshold: float = Field(
        0.1, ge=0.0, le=1.0, description="Minimum confidence for card detection"
    )
    template_dir: str = Field(
        "templates", description="Directory containing card templates"
    )
    max_image_dimension: int = Field(
        1000, description="Maximum dimension for image resizing"
    )


class CaptureConfig(BaseModel):
    """Configuration for screen capture."""

    fps: int = Field(30, ge=1, le=120, description="Target frames per second")
    region_buffer: int = Field(20, ge=0, description="Buffer around capture region")


class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = Field("INFO", description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format"
    )


class SweepConfig(BaseModel):
    """Configuration for matrix sweep execution."""

    write_queue_maxsize: int = Field(
        15000,
        ge=1,
        description="Maximum size of the raw sweep write queue for persistence backpressure management",
    )


class AppConfig(BaseModel):
    """Main application configuration."""

    game_modes: Dict[str, GameModeConfig] = Field(
        ..., description="Available game mode configurations"
    )
    detection: DetectionConfig = Field(
        default_factory=DetectionConfig, description="Detection settings"  # type: ignore
    )
    capture: CaptureConfig = Field(
        default_factory=CaptureConfig, description="Capture settings"  # type: ignore
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging settings"  # type: ignore
    )
    sweep: SweepConfig = Field(
        default_factory=SweepConfig,
        description="Settings for matrix sweep execution",
    )


def load_config(config_path: Optional[Union[str, Path]] = None) -> AppConfig:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"

    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    with open(config_file, "r") as f:
        data = yaml.safe_load(f)

    return AppConfig(**data)


# Default configuration for fallback
DEFAULT_CONFIG = AppConfig(
    game_modes={
        "rush_n_cash": GameModeConfig(
            slots={
                "hero_hole_1": [27, 668, 46, 693, -5.0],
                "hero_hole_2": [64, 666, 83, 691, 5.0],
                "flop_1": [69, 415, 86, 449, 0.0],
                "flop_2": [124, 415, 143, 450, 0.0],
                "flop_3": [179, 415, 198, 450, 0.0],
                "turn": [234, 415, 253, 450, 0.0],
                "river": [290, 415, 309, 450, 0.0],
            }
        )
    }
)
