import sys
from pathlib import Path

import pygame

from hopilot.gui_components.aof_browser_panel import AoFBrowserPanel
from hopilot.gui_components.precompute_config import PrecomputeConfig
from hopilot.gui_components.state_machine_controller import StateMachineController
from hopilot.logging_config import get_logger


class GuiApplication:
    TARGET_FPS = 60

    def __init__(self, width: int = 1200, height: int = 800, fixture_path: str | None = None, database_url: str | None = None):
        self.logger = get_logger(__name__)
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("HoPilot - AoF GTO Browser")
        self.clock = pygame.time.Clock()
        self.panel = AoFBrowserPanel(width, height, fixture_path=fixture_path, database_url=database_url)

        # Initialize state machine integration
        self._init_state_machine()

    def _init_state_machine(self):
        """Initialize and attach state machine controller."""
        # Load configuration
        config_path = Path(__file__).resolve().parents[2] / "config" / "gto_defaults.yaml"
        config = PrecomputeConfig.from_yaml(config_path)

        # Create and attach state machine controller
        self.state_machine_controller = StateMachineController(panel=self.panel, config=config)
        self.panel.set_state_machine_controller(self.state_machine_controller)

        self.logger.info("State machine integration initialized")

    def handle_event(self, event) -> bool:
        if event.type == pygame.QUIT:
            return False
        self.panel.handle_event(event)
        return True

    def draw(self):
        self.screen.fill((27, 40, 34))
        self.panel.draw(self.screen)
        pygame.display.flip()

    def run(self):
        running = True
        try:
            while running:
                for event in pygame.event.get():
                    if not self.handle_event(event):
                        running = False
                self.draw()
                if not pygame.display.get_active():
                    running = False
                self.clock.tick(self.TARGET_FPS)
        finally:
            if self.panel is not None:
                try:
                    self.panel.shutdown()
                except Exception as exc:
                    self.logger.error("Failed to shut down panel on exit: %s", exc)
            pygame.quit()
            sys.exit(0)


if __name__ == "__main__":
    import argparse
    import yaml

    parser = argparse.ArgumentParser(description="HoPilot AoF GTO Browser")
    parser.add_argument("--fixture-path", help="Path to fixture data file")
    parser.add_argument("--database-url", help="Database URL for normalized schema (e.g., sqlite:///path/to/db)")
    args = parser.parse_args()

    # Load default database URL from config if not provided
    database_url = args.database_url
    if database_url is None:
        try:
            config_path = Path(__file__).resolve().parents[2] / "config" / "gto_defaults.yaml"
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
            if "database" in config_data and "url" in config_data["database"]:
                database_url = config_data["database"]["url"]
                
                # Convert relative sqlite path to absolute
                if database_url.startswith("sqlite:///"):
                    rel_path = database_url.replace("sqlite:///", "")
                    # Resolve relative to project root (parents[2] from the module location)
                    abs_path = (Path(__file__).resolve().parents[2] / rel_path).resolve()
                    database_url = f"sqlite:///{abs_path}"
                    print(f"Using default database URL from config: {database_url}")
                else:
                    print(f"Using default database URL from config: {database_url}")
            else:
                database_url = "sqlite:///:memory:"
                print("Database config not found, using in-memory database")
        except Exception as e:
            database_url = "sqlite:///:memory:"
            print(f"Warning: Could not load config, using in-memory database: {e}")

    app = GuiApplication(
        fixture_path=args.fixture_path,
        database_url=database_url
    )
    app.run()
