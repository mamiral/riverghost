from enum import Enum
import os
import queue
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
import pygame
import yaml
from typing import Dict, Any, Optional

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.gto.aof_browser_state import AoFBrowserViewState, POSITIONS, METRICS, normalize_position_actions
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiPrecomputeRunSession, GuiRunState
from hopilot.gto.matrix_sweep_contract import RUN_STATUS_AGGREGATED
from hopilot.gto.convergence_analysis_queries import ConvergenceAnalysisQueries
from hopilot.gui_components.aof_action_selector import AoFActionSelector


class PanelState(Enum):
    LOADING = "LOADING"
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    NO_CONTEST = "NO_CONTEST"
    ERROR = "ERROR"


from hopilot.gui_components.aof_cell_detail_panel import AoFCellDetailPanel
from hopilot.gui_components.aof_hand_matrix_panel import AoFHandMatrixPanel
from hopilot.gui_components.aof_metric_dropdown import AoFMetricDropdown
from hopilot.gui_components.convergence_panel import ConvergencePanel
from hopilot.logging_config import get_logger


class AoFBrowserPanel:
    def __init__(self, width: int, height: int, fixture_path: str | None = None, database_url: str | None = None):
        self.logger = get_logger(__name__)
        self.width = width
        self.height = height
        self.state = AoFBrowserViewState()
        
        # Phase 4: Use minimal database provider (cache removed)
        if database_url is None:
            raise ValueError(
                "database_url is required for Phase 4 (cache removed). "
                "Provide via --database-url argument or configure in gto_defaults.yaml"
            )
        self.provider = BrowserDatabaseProvider(database_url=database_url)

        try:
            self.convergence_queries = ConvergenceAnalysisQueries(database_url)
        except Exception as exc:
            self.logger.error("Failed to initialize convergence analysis queries: %s", exc)
            self.convergence_queries = None

        try:
            self.runner = AoFPrecomputeRunner(self.provider, database_url)
        except Exception as exc:
            self.logger.error("Failed to initialize precompute runner: %s", exc)
            self.runner = None

        self.state_machine_controller = None
        self.precompute_session: GuiPrecomputeRunSession | None = None
        self.precompute_context: dict | None = None
        self.precompute_simulations_per_cell = 1000
        self.precompute_buttons: dict[str, pygame.Rect] = {}
        self.precompute_worker_buttons: dict[str, pygame.Rect] = {}
        self.precompute_worker_knob = pygame.Rect(0, 0, 0, 0)
        self.precompute_sim_buttons: dict[str, pygame.Rect] = {}
        self.precompute_sim_knob = pygame.Rect(0, 0, 0, 0)
        self.precompute_max_workers = self._load_precompute_max_workers()
        self.precompute_payload_persisted = False
        self.precompute_thread: threading.Thread | None = None
        self.precompute_executor: ThreadPoolExecutor | None = None
        self.precompute_futures: dict[Future, int] = {}
        self.precompute_stop_event = threading.Event()
        self._precompute_result_queue: queue.Queue[tuple[int, dict[str, Any], str | None]] = queue.Queue()
        self._precompute_session_lock = threading.Lock()

        self._last_error: str | None = None
        self._refresh_context: dict[str, Any] | None = None
        self._rerun_in_progress = False

        # Initialize payload with empty data
        self.payload = {
            "context": {},
            "cells": [],
            "status_message": "Initializing...",
        }
        self.selected_cell_detail = {}

        # Attempt to restore previous session
        self._restore_precompute_checkpoint_if_available()
        
        # Load any existing data from database
        self.is_loading = False
        self._refresh()

        self.top_margin = 20
        self.control_h = 190
        self.side_panel_w = 300
        self.middle_panel_w = 220
        self.middle_panel_gap = 12
        self.outer_margin = 20
        self.side_x = self.width - self.side_panel_w + self.outer_margin
        self.side_w = self.side_panel_w - (self.outer_margin * 2)

        matrix_region_width, detail_width = self._compute_column_widths(width)
        self.middle_panel_w = detail_width
        self.action_selector = AoFActionSelector(self.outer_margin, self.top_margin + 28, width=matrix_region_width)
        self.metric_dropdown = AoFMetricDropdown(self.side_x, self.top_margin + 24, width=self.side_w)
        self.matrix = AoFHandMatrixPanel(self.outer_margin, self.top_margin + 80)
        self.cell_detail_panel = AoFCellDetailPanel(self.outer_margin, self.top_margin + 80, self.middle_panel_w, 220)
        self.convergence_panel = ConvergencePanel(self.outer_margin, self.top_margin + 80, 400, 200)
        self._reflow_layout()
        self._build_precompute_controls()

        self.font = pygame.font.SysFont("arial", 18)
        self.small_font = pygame.font.SysFont("arial", 12)
        # Phase 3: Use database provider for data (forces database; no cache fallback)
        try:
            self.payload = self.provider.get_matrix_from_database(
                self.state.selected_position,
                self.state.selected_metric,
                self.state.position_actions,
                simulations_per_cell=self.precompute_simulations_per_cell,
                allow_compute=False,
            )
        except Exception as exc:
            self.logger.error("Failed to load initial payload from database: %s", exc)
            self._last_error = str(exc)
            self.payload = self._build_loading_payload({
                "position": self.state.selected_position,
                "metric": self.state.selected_metric,
                "position_actions": self.state.position_actions,
            })
            self.payload["status"] = PanelState.ERROR.value
            self.payload["status_message"] = f"Database error: {exc}"

        self.selected_cell_detail = self._build_selected_cell_detail_model()
        self._load_convergence_data()
        self._restore_precompute_checkpoint_if_available()

        # Database loading state
        self.is_loading = False
        self.loading_task = None

    def _reflow_layout(self) -> None:
        self.side_x = self.width - self.side_panel_w + self.outer_margin
        self.side_w = self.side_panel_w - (self.outer_margin * 2)
        matrix_x = self.outer_margin
        matrix_y = self.top_margin + 150  # Reduced spacing for action selector + controls
        matrix_w, detail_w = self._compute_column_widths(self.width)
        self.middle_panel_w = detail_w
        matrix_h = self.height - matrix_y - self.outer_margin - 220  # Leave space for convergence panel
        self.matrix.set_bounds(matrix_x, matrix_y, matrix_w, matrix_h)
        detail_x = self.matrix.x + self.matrix.width + self.middle_panel_gap
        self.cell_detail_panel.set_bounds(detail_x, matrix_y, self.middle_panel_w, matrix_h)

        # Position convergence panel below matrix/detail panels
        convergence_y = matrix_y + matrix_h + 10
        convergence_x = self.outer_margin
        convergence_w = self.width - self.side_panel_w - (self.outer_margin * 2)
        convergence_h = 200
        # Update bounds of existing panel instead of recreating
        self.convergence_panel.set_bounds(convergence_x, convergence_y, convergence_w, convergence_h)

        self.metric_dropdown.set_bounds(self.side_x, self.top_margin + 24, self.side_w)
        self._build_precompute_controls()

    def _compute_column_widths(self, total_width: int) -> tuple[int, int]:
        available = max(13 * 28 + 180, total_width - self.side_panel_w - self.middle_panel_gap - (self.outer_margin * 2))
        min_matrix = 13 * 28
        min_detail = 180
        preferred_detail = 220

        detail = min(preferred_detail, max(min_detail, int(available * 0.35)))
        matrix = max(min_matrix, available - detail)

        if matrix + detail > available:
            detail = max(min_detail, available - matrix)
        return matrix, detail

    def _build_precompute_controls(self) -> None:
        side_x = self.side_x
        vertical_gap = 8
        start_y = self.metric_dropdown.rect.bottom + vertical_gap
        button_w = self.side_w
        button_h = 24
        gap = vertical_gap
        self.precompute_buttons = {
            "start": pygame.Rect(side_x, start_y, button_w, button_h),
            "pause": pygame.Rect(side_x, start_y + (button_h + gap), button_w, button_h),
            "resume": pygame.Rect(side_x, start_y + 2 * (button_h + gap), button_w, button_h),
            "stop": pygame.Rect(side_x, start_y + 3 * (button_h + gap), button_w, button_h),
        }
        worker_y = self.precompute_buttons["stop"].bottom + vertical_gap
        knob_w = 52
        self.precompute_worker_knob = pygame.Rect(side_x, worker_y, knob_w, button_h)
        half_w = knob_w // 2
        self.precompute_worker_buttons = {
            "down": pygame.Rect(side_x, worker_y, half_w, button_h),
            "up": pygame.Rect(side_x + half_w, worker_y, knob_w - half_w, button_h),
        }

        sim_x = side_x + button_w - knob_w
        self.precompute_sim_knob = pygame.Rect(sim_x, worker_y, knob_w, button_h)
        self.precompute_sim_buttons = {
            "down": pygame.Rect(sim_x, worker_y, half_w, button_h),
            "up": pygame.Rect(sim_x + half_w, worker_y, knob_w - half_w, button_h),
        }
        self.control_h = (self.precompute_worker_knob.bottom - self.top_margin) + vertical_gap

    def _default_precompute_workers(self) -> int:
        workers = os.cpu_count() or 2
        return max(1, min(4, workers))

    @staticmethod
    def _clamp_precompute_workers(raw_workers: int) -> int:
        return max(1, min(16, int(raw_workers)))

    @staticmethod
    def _clamp_precompute_simulations(raw_simulations: int) -> int:
        return max(100, min(50000, int(raw_simulations)))

    @staticmethod
    def _simulation_step_size(current_simulations: int, mouse_button: int) -> int:
        coarse = int(mouse_button) == 3
        current = int(current_simulations)
        if coarse:
            return 1000 if current < 5000 else 5000
        return 100 if current < 5000 else 500

    def _load_precompute_max_workers(self) -> int:
        cfg_path = Path(__file__).resolve().parents[3] / "config" / "gto_defaults.yaml"
        fallback = self._default_precompute_workers()
        if not cfg_path.exists():
            return fallback
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            runtime_cfg = loaded.get("aof_browser_runtime", {})
            configured = runtime_cfg.get("precompute_max_workers")
            if configured is None:
                return fallback
            return self._clamp_precompute_workers(int(configured))
        except Exception as exc:
            self.logger.warning("Failed to load precompute_max_workers from config: %s", exc)
            return fallback

    def _load_convergence_target_points(self) -> int:
        """Load convergence target points from config."""
        cfg_path = Path(__file__).resolve().parents[3] / "config" / "gto_defaults.yaml"
        fallback = 8  # Default to 8 points
        if not cfg_path.exists():
            return fallback
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            runtime_cfg = loaded.get("aof_browser_runtime", {})
            configured = runtime_cfg.get("convergence_target_points")
            if configured is None:
                return fallback
            return max(2, min(50, int(configured)))  # Clamp between 2 and 50
        except Exception as exc:
            self.logger.warning("Failed to load convergence_target_points from config: %s", exc)
            return fallback

    def _refresh(self):
        # Phase 3: Always use database provider (no cache fallback)
        if self.is_loading:
            return

        if self.precompute_session is not None and self.precompute_session.run_state in (
            GuiRunState.RUNNING,
            GuiRunState.PAUSED,
            GuiRunState.STOPPING,
        ):
            self.logger.info("Context changed while precompute was active; stopping previous session")
            self.stop_precompute()
            self.reset_precompute()
            self._rerun_in_progress = False

        self.is_loading = True
        self._last_error = None
        self._refresh_context = self._build_current_context()
        self.payload = self._build_loading_payload({})
        self.state.status_message = "Loading from database..."
        self.selected_cell_detail = self._build_selected_cell_detail_model()
        self._start_async_refresh()

    def _start_async_refresh(self):
        """Start async database refresh in background thread."""
        import threading
        import asyncio

        request_context = dict(self._refresh_context or {})

        def async_refresh():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Phase 3: Use database provider directly (no cache fallback)
                payload = self.provider.get_matrix_from_database(
                    self.state.selected_position,
                    self.state.selected_metric,
                    self.state.position_actions,
                    simulations_per_cell=self.precompute_simulations_per_cell,
                    allow_compute=False,
                )

                # Post result to main thread
                import pygame
                pygame.event.post(pygame.event.Event(pygame.USEREVENT,
                    event_type="database_refresh",
                    payload=payload,
                    request_context=request_context,
                    success=True
                ))

            except Exception as e:
                self.logger.error(f"Async refresh failed: {e}")
                import pygame
                pygame.event.post(pygame.event.Event(pygame.USEREVENT,
                    event_type="database_refresh",
                    error=str(e),
                    request_context=request_context,
                    success=False
                ))

        # Start background thread
        thread = threading.Thread(target=async_refresh, daemon=True)
        thread.start()

    def _handle_async_refresh_result(self, event) -> None:
        """Handle result from async database refresh."""
        if getattr(event, 'request_context', None) != self._refresh_context:
            self.logger.debug("Discarding stale database refresh result")
            return

        if getattr(event, 'success', False):
            self._last_error = None
            self.payload = getattr(event, 'payload', {})
            self._invalidate_selected_cell_if_needed()
            self.state.status_message = self.payload.get("status_message")
            self.selected_cell_detail = self._build_selected_cell_detail_model()
            self._load_convergence_data()
        else:
            error_message = str(getattr(event, 'error', 'Unknown error'))
            self._last_error = error_message
            self.state.status_message = f"Database error: {error_message}"
            self.payload = self._build_loading_payload(self._refresh_context or self.payload.get("context", {}))
            self.payload["status"] = PanelState.ERROR.value
            self.payload["status_message"] = self.state.status_message
            self.selected_cell_detail = self._build_selected_cell_detail_model()

        self.is_loading = False

    def _load_convergence_data(self):
        """Load convergence data for selected cell using convergence analysis queries."""
        if self.convergence_queries is None:
            self.logger.warning("Convergence analysis queries unavailable, skipping convergence data loading")
            return
        if not hasattr(self, 'convergence_panel') or self.convergence_panel is None:
            self.logger.warning("Convergence panel not initialized, skipping convergence data loading")
            return

        try:
            # Only show convergence plot when a cell is selected
            if self.state.selected_cell is None:
                self.convergence_panel.set_convergence_data([], "", "")
                return

            row, col, hand_key = self.state.selected_cell

            # Get matrix ID from current payload context
            matrix_id = self.payload.get("context", {}).get("matrix_id")
            if not matrix_id:
                self.logger.debug("No matrix_id in payload context, cannot load convergence data")
                self.convergence_panel.set_convergence_data([], "", "")
                return

            # Get convergence data using the convergence analysis queries
            convergence_result = self.convergence_queries.get_equity_convergence_series(
                matrix_id=matrix_id,
                row_idx=row,
                col_idx=col,
                sample_intervals=[100, 250, 500, 1000, 2500, 5000, 10000]
            )

            if convergence_result and convergence_result.get('convergence_series'):
                # Convert the data format for the convergence panel
                convergence_data = []
                for point in convergence_result['convergence_series']:
                    convergence_data.append({
                        'sample_count': point['sample_count'],
                        'equity': point['equity'],
                        'timestamp': point.get('timestamp')
                    })

                position_action = self.state.get_position_action(self.state.selected_position)
                self.convergence_panel.set_convergence_data(
                    convergence_data,
                    f"{self.state.selected_position} - {hand_key}",
                    position_action,
                    self.state.selected_metric
                )

                self.logger.debug(f"Loaded convergence data: {len(convergence_data)} points for {hand_key}")
            else:
                self.logger.debug(f"No convergence data available for {hand_key}")
                self.convergence_panel.set_convergence_data([], "", "")

        except Exception as e:
            self.logger.warning(f"Failed to load convergence data: {e}", exc_info=True)
            if hasattr(self, 'convergence_panel') and self.convergence_panel is not None:
                self.convergence_panel.set_convergence_data([], "", "")

    def _invalidate_selected_cell_if_needed(self) -> None:
        if self.state.selected_cell is None:
            return
        row, col, hand_key = self.state.selected_cell
        cell = self._find_payload_cell(row, col)
        if cell is None or str(cell.get("hand_key", "")) != str(hand_key):
            self.state.clear_selected_cell()
            self.state.status_message = "Selected cell cleared after context refresh"
            self._load_convergence_data()  # Update convergence plot back to position-level

    def _build_loading_payload(self, context: Dict[str, Any] | None) -> Dict[str, Any]:
        """Build a placeholder payload used while waiting for database results."""
        loading_cells = []
        for row in range(13):
            for col in range(13):
                loading_cells.append({
                    "row": row,
                    "col": col,
                    "hand_key": self.provider._matrix_keys[row][col],  # pylint: disable=protected-access
                    "value": None,
                    "status": PanelState.LOADING.value,
                    "display": "-",
                })

        return {
            "context": dict(context or {}),
            "cells": loading_cells,
            "status": PanelState.LOADING.value,
            "status_message": "Loading...",
        }

    def _build_error_payload(self, context: Dict[str, Any] | None, message: str) -> Dict[str, Any]:
        error_cells = []
        for row in range(13):
            for col in range(13):
                error_cells.append({
                    "row": row,
                    "col": col,
                    "hand_key": self.provider._matrix_keys[row][col],
                    "value": None,
                    "status": PanelState.ERROR.value,
                    "display": "-",
                })

        return {
            "context": dict(context or {}),
            "cells": error_cells,
            "status": PanelState.ERROR.value,
            "status_message": message,
        }

    @property
    def panel_state(self) -> str:
        if self._last_error:
            return PanelState.ERROR.value
        if self.is_loading:
            return PanelState.LOADING.value

        payload_status = str(self.payload.get("status", "")).upper()
        if payload_status == PanelState.NO_CONTEST.value:
            return PanelState.NO_CONTEST.value
        if payload_status == PanelState.MISSING.value:
            return PanelState.MISSING.value
        if payload_status == PanelState.AVAILABLE.value:
            return PanelState.AVAILABLE.value

        return PanelState.LOADING.value

    @property
    def active_scenario_context(self) -> str:
        return (
            f"{self.state.selected_position}"
            f" / {self.state.get_position_action(self.state.selected_position)}"
            f" / {self.state.selected_metric.replace('_', ' ')}"
        )

    def _find_payload_cell(self, row: int, col: int) -> dict | None:
        index = int(row) * 13 + int(col)
        cells = self.payload.get("cells", [])
        if index < 0 or index >= len(cells):
            return None
        cell = cells[index]
        if int(cell.get("row", -1)) != int(row) or int(cell.get("col", -1)) != int(col):
            return None
        return cell

    def _build_selected_cell_detail_model(self) -> dict:
        if self.state.selected_cell is None:
            return {"selected": False, "status": "UNSELECTED", "status_message": "Select a matrix cell to inspect details."}

        row, col, hand_key = self.state.selected_cell
        cell = self._find_payload_cell(row, col)
        if cell is None:
            status = "MISSING"
            return {
                "selected": True,
                "row": row,
                "col": col,
                "hand_key": hand_key,
                "metric": self.state.selected_metric,
                "status": status,
                "value": None,
                "display_value": "-",
                "segments": [],
                "status_message": AoFCellDetailPanel.fallback_message_for_status(status),
            }

        metric = self.state.selected_metric
        status = str(cell.get("status", "MISSING"))
        metrics = cell.get("metrics") if isinstance(cell.get("metrics"), dict) else {}
        value = metrics.get(metric) if isinstance(metrics, dict) else cell.get("value")
        if value is None:
            value = cell.get("value")

        model = {
            "selected": True,
            "row": row,
            "col": col,
            "hand_key": str(cell.get("hand_key", hand_key)),
            "metric": metric,
            "status": status,
            "value": value,
            "display_value": str(cell.get("display", "-")),
            "segments": [],
            "status_message": None,
        }

        # Add aggregation metadata if available
        if cell.get("sample_count") is not None:
            model["sample_count"] = int(cell["sample_count"])
        if cell.get("confidence") is not None:
            model["confidence"] = float(cell["confidence"])

        if status != "AVAILABLE":
            model["status_message"] = AoFCellDetailPanel.fallback_message_for_status(status)
            return model

        def _metric_value(*keys: str, default: float = 0.0) -> float:
            for key in keys:
                if isinstance(metrics, dict) and metrics.get(key) is not None:
                    return float(metrics[key])
            return float(default)

        if metric == "WIN_LOSE_PROBABILITY":
            win = _metric_value("WIN", "WIN_PROBABILITY", default=float(value or 0.0))
            tie = _metric_value("TIE", "TIE_PROBABILITY", default=0.0)
            loss_value = metrics.get("LOSS") if isinstance(metrics, dict) else None
            if loss_value is None and isinstance(metrics, dict):
                loss_value = metrics.get("LOSS_PROBABILITY")
            if loss_value is None:
                loss = max(0.0, 1.0 - win - tie)
            else:
                loss = float(loss_value)
            total = max(0.0001, win + tie + loss)
            model["segments"] = [
                {
                    "label": "Win",
                    "value": win,
                    "display": f"{win * 100:.1f}%",
                    "weight": max(0.0, win / total),
                    "color_role": "positive",
                },
                {
                    "label": "Tie",
                    "value": tie,
                    "display": f"{tie * 100:.1f}%",
                    "weight": max(0.0, tie / total),
                    "color_role": "neutral",
                },
                {
                    "label": "Loss",
                    "value": loss,
                    "display": f"{loss * 100:.1f}%",
                    "weight": max(0.0, loss / total),
                    "color_role": "negative",
                },
            ]
        else:
            scalar_value = float(value) if value is not None else 0.0
            if metric in ("EQUITY", "EQR"):
                scalar_weight = max(0.0, min(1.0, scalar_value))
                scalar_display = f"{scalar_value * 100:.1f}%"
            else:
                scalar_weight = max(0.05, min(1.0, abs(scalar_value) / 3.0))
                scalar_display = f"{scalar_value:+.2f}"
            model["segments"] = [
                {
                    "label": metric,
                    "value": scalar_value,
                    "display": scalar_display,
                    "weight": scalar_weight,
                    "color_role": "neutral",
                }
            ]

        return model

    def _restore_precompute_checkpoint_if_available(self) -> None:
        """Phase 4: Restore context from latest database simulation."""
        try:
            # Query for the latest simulation
            import json
            with self.provider.database_repository.connection.session_scope() as session:
                from hopilot.models import Simulation
                latest_sim = session.query(Simulation).order_by(Simulation.created_at.desc()).first()
                if latest_sim:
                    params = latest_sim.parameters
                    if isinstance(params, str):
                        params = json.loads(params)
                    elif not isinstance(params, dict):
                        try:
                            params = dict(params)
                        except Exception:
                            params = {}
                    position = params.get("position") or params.get("selected_position")
                    action = params.get("action") or params.get("hero_action")
                    metric = params.get("metric", "WIN_LOSE_PROBABILITY")
                    position_actions = params.get("position_actions")

                    if position and position in POSITIONS:
                        self.state.set_position(position)
                        if position_actions and isinstance(position_actions, dict):
                            self.state.position_actions = normalize_position_actions(position_actions)
                        elif action:
                            self.state.set_position_action(position, action)

                        simulations_per_cell = (
                            params.get("simulations_per_cell")
                            or params.get("sims_per_combo")
                            or params.get("num_simulations")
                        )
                        if simulations_per_cell is not None:
                            try:
                                self.precompute_simulations_per_cell = int(simulations_per_cell)
                            except (TypeError, ValueError):
                                self.logger.warning(
                                    "Invalid simulations_per_cell in restored context: %s",
                                    simulations_per_cell,
                                )

                        if metric in METRICS:
                            self.state.set_metric(metric)
                        
                        self.logger.info(
                            f"Restored context from latest simulation: position={position}, action={action}, metric={metric}, position_actions={position_actions}, simulations_per_cell={simulations_per_cell}"
                        )
        except Exception as e:
            self.logger.warning(f"Failed to restore context from database: {e}")

    def _build_current_context(self) -> dict:
        return self.provider._build_context(  # pylint: disable=protected-access
            position=self.state.selected_position,
            metric=self.state.selected_metric,
            position_actions=self.state.position_actions,
            simulations_per_cell=self.precompute_simulations_per_cell,
            max_workers=self.precompute_max_workers,
        )

    def _build_scenario_contract(self, context: dict[str, Any]) -> dict[str, Any]:
        position_actions = dict(context.get("position_actions", {}))
        active_players = [
            position for position, action in position_actions.items() if action != "FOLD"
        ]
        if not active_players and context.get("position"):
            active_players = [context["position"]]

        simulations = (
            context.get("simulations_per_cell")
            or context.get("sims_per_combo")
            or context.get("num_simulations")
            or 1
        )

        return {
            "selected_position": str(context.get("position", "")),
            "hero_action": str(context.get("action", "")),
            "position_actions": position_actions,
            "active_players": active_players,
            "num_opponents": max(1, len(active_players) - 1),
            "pot_size": float(context.get("pot_size", 0.0)),
            "bet_amount": float(context.get("bet_amount", 0.0)),
            "sims_per_combo": int(simulations),
            "num_simulations": int(simulations),
            "matrix_size": "13x13",
            "game_type": str(context.get("game_type", "cash")),
            "run_kind": "matrix_sweep",
        }

    def _start_precompute(self) -> None:
        if self.runner is None:
            self.logger.error("Cannot start precompute: runner is not initialized")
            return

        self._last_error = None
        self.precompute_context = self._build_current_context()
        fingerprint = self.runner.build_scenario_fingerprint(self.precompute_context)
        self.precompute_session = self.runner.create_gui_session(
            simulations_per_cell=self.precompute_simulations_per_cell,
            scenario_fingerprint=fingerprint,
            total_cells=169,
        )
        
        self.runner.transition_session_state(self.precompute_session, GuiRunState.RUNNING)
        self.runner.bind_gui_run(self.precompute_session)
        self._cancel_pending_precompute_futures()
        self._clear_precompute_result_queue()
        self.precompute_stop_event.clear()
        self.precompute_thread = threading.Thread(
            target=self._run_matrix_sweep_background,
            daemon=True,
            name="precompute-background",
        )
        self.precompute_thread.start()
        self.precompute_payload_persisted = False

        start_from_available = (
            self.payload.get("status") == PanelState.AVAILABLE.value
            and self.payload.get("context") == self.precompute_context
        )

        cells = self.payload.get("cells", []) if start_from_available else [
            {
                "row": row,
                "col": col,
                "hand_key": self.provider._matrix_keys[row][col],  # pylint: disable=protected-access
                "value": None,
                "status": "MISSING",
                "display": "-",
            }
            for row in range(13)
            for col in range(13)
        ]

        self._rerun_in_progress = start_from_available
        self.payload = {
            "context": dict(self.precompute_context),
            "cells": cells,
            "status": PanelState.AVAILABLE.value if start_from_available else "MISSING",
            "status_message": "Recomputing available scenario..." if start_from_available else "Precompute started",
        }
        self.selected_cell_detail = self._build_selected_cell_detail_model()
        self.state.status_message = self.payload["status_message"]

    def _run_matrix_sweep_background(self) -> None:
        try:
            if self.precompute_context is None:
                return
            scenario_contract = self._build_scenario_contract(self.precompute_context)
            scenario_contract["stop_event"] = self.precompute_stop_event
            result = self.runner.run_matrix_sweep(scenario_contract)
            if self.precompute_session is not None:
                self.precompute_session.sim_id = result.get("simulation_id")
                self.precompute_session.matrix_id = result.get("matrix_id")
                if result.get("status") in ("aggregated", RUN_STATUS_AGGREGATED):
                    self.precompute_session.completed_cells = self.precompute_session.total_cells
                else:
                    self.precompute_session.failed_cells += 1
                    self.precompute_session.completed_cells = self.precompute_session.total_cells
        except Exception as exc:
            if self.precompute_session is not None:
                self.precompute_session.run_state = GuiRunState.FAILED
                self.precompute_session.status_message = str(exc)
            self.logger.error("Matrix sweep background thread failed: %s", exc, exc_info=True)
        finally:
            return

    def _persist_completed_precompute_payload(self) -> None:
        """Phase 4: Cache persistence removed. Precompute results are in database."""
        if self.precompute_payload_persisted:
            return
        self.precompute_payload_persisted = True
        self.state.status_message = "Precompute completed (database persisted)"

    def _on_precompute_future_done(
        self,
        future: Future,
        session: GuiPrecomputeRunSession,
        context: dict[str, Any],
        cell_index: int,
    ) -> None:
        """Handle individual GUI precompute futures when they complete."""
        if session is None or self.precompute_session is None:
            return
        if session.run_state != GuiRunState.RUNNING:
            return
        if future not in self.precompute_futures:
            return

        self.precompute_futures.pop(future, None)

        if future.cancelled():
            return

        try:
            result = future.result()
        except Exception as exc:
            self.logger.warning("Precompute future failed: %s", exc)
            return

        cell = None
        status_message = None
        if isinstance(result, tuple) and len(result) == 2:
            cell, status_message = result
        elif isinstance(result, dict):
            cell = result
        else:
            self.logger.warning("Unexpected precompute future result: %s", result)
            return

        if cell is None:
            return

        self._precompute_result_queue.put((cell_index, cell, status_message))

    def _cancel_pending_precompute_futures(self) -> None:
        if self.precompute_session is None:
            return

        if self.precompute_futures:
            pending_indices = list(self.precompute_futures.values())
            if pending_indices:
                min_pending_index = min(pending_indices)
                if self.precompute_session.next_cell_index > min_pending_index:
                    self.precompute_session.next_cell_index = min_pending_index

        for future in list(self.precompute_futures.keys()):
            try:
                future.cancel()
            except Exception:
                self.logger.debug("Failed to cancel precompute future", exc_info=True)
        self.precompute_futures.clear()

    def _clear_precompute_result_queue(self) -> None:
        """Clear any pending precompute result notifications."""
        while not self._precompute_result_queue.empty():
            try:
                self._precompute_result_queue.get_nowait()
            except queue.Empty:
                break


    def _tick_precompute(self) -> None:
        if self.precompute_session is None or self.precompute_context is None:
            return

        processed_results = False
        while True:
            try:
                cell_index, cell, status_message = self._precompute_result_queue.get_nowait()
            except queue.Empty:
                break
            self.payload["cells"][cell_index] = cell
            self.payload["context"] = dict(self.precompute_context or {})
            self.payload["status_message"] = self.precompute_context.get("status_message") if self.precompute_context else None
            processed_results = True

        if processed_results:
            self.selected_cell_detail = self._build_selected_cell_detail_model()
            self._load_convergence_data()  # Update convergence plot with new data

        if self.precompute_thread is not None and not self.precompute_thread.is_alive():
            self.precompute_thread = None
            if self.precompute_session and self.precompute_session.run_state == GuiRunState.RUNNING:
                self.runner.transition_session_state(self.precompute_session, GuiRunState.COMPLETED)
                self.runner.mark_gui_dispatch(self.precompute_session)
                self.state.status_message = "Precompute completed"
            self._refresh()

        if self.precompute_session.run_state == GuiRunState.COMPLETED:
            self._persist_completed_precompute_payload()
            if self.state_machine_controller:
                self.state_machine_controller.mark_completed()
            if self._rerun_in_progress:
                self._rerun_in_progress = False
                self._refresh()
            return

        if self.precompute_session.run_state == GuiRunState.FAILED:
            self._cancel_pending_precompute_futures()
            self._rerun_in_progress = False
            error_message = getattr(self.precompute_session, 'status_message', None) or 'Precompute failed'
            self._last_error = str(error_message)
            self.state.status_message = str(error_message)
            self.payload = self._build_error_payload(self.precompute_context, self.state.status_message)
            self.selected_cell_detail = self._build_selected_cell_detail_model()
            if self.state_machine_controller:
                self.state_machine_controller.mark_failed()
            return

        if self.precompute_session.run_state != GuiRunState.RUNNING:
            return

    def handle_event(self, event):
        if event.type == pygame.USEREVENT:
            # Handle async database refresh completion
            if hasattr(event, 'event_type') and event.event_type == 'database_refresh':
                self._handle_async_refresh_result(event)
                return True

        # Route state machine events if controller is attached
        if hasattr(self, 'state_machine_controller') and self.state_machine_controller:
            state_machine_result = self._handle_state_machine_event(event)
            if state_machine_result is not None:
                return state_machine_result

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.precompute_worker_buttons.get("down") and self.precompute_worker_buttons["down"].collidepoint(event.pos):
                if self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING:
                    self.precompute_max_workers = max(1, self.precompute_max_workers - 1)
                    self.state.status_message = f"Workers set to {self.precompute_max_workers}"
                    return True
            if self.precompute_worker_buttons.get("up") and self.precompute_worker_buttons["up"].collidepoint(event.pos):
                if self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING:
                    self.precompute_max_workers = min(16, self.precompute_max_workers + 1)
                    self.state.status_message = f"Workers set to {self.precompute_max_workers}"
                    return True
            if self.precompute_sim_buttons.get("down") and self.precompute_sim_buttons["down"].collidepoint(event.pos):
                if self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING:
                    step = self._simulation_step_size(self.precompute_simulations_per_cell, getattr(event, "button", 1))
                    self.precompute_simulations_per_cell = self._clamp_precompute_simulations(self.precompute_simulations_per_cell - step)
                    self.state.status_message = f"Simulations per cell set to {self.precompute_simulations_per_cell}"
                    return True
            if self.precompute_sim_buttons.get("up") and self.precompute_sim_buttons["up"].collidepoint(event.pos):
                if self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING:
                    step = self._simulation_step_size(self.precompute_simulations_per_cell, getattr(event, "button", 1))
                    self.precompute_simulations_per_cell = self._clamp_precompute_simulations(self.precompute_simulations_per_cell + step)
                    self.state.status_message = f"Simulations per cell set to {self.precompute_simulations_per_cell}"
                    return True

            if self.precompute_buttons.get("start") and self.precompute_buttons["start"].collidepoint(event.pos):
                if self.precompute_session is None or self.precompute_session.run_state in (GuiRunState.IDLE, GuiRunState.COMPLETED, GuiRunState.FAILED):
                    self._start_precompute()
                    return True
            if self.precompute_buttons.get("pause") and self.precompute_buttons["pause"].collidepoint(event.pos):
                if self.precompute_session and self.precompute_session.run_state == GuiRunState.RUNNING:
                    self.state.status_message = "Pause is unsupported for raw matrix sweep"
                    return True
            if self.precompute_buttons.get("resume") and self.precompute_buttons["resume"].collidepoint(event.pos):
                if self.precompute_session and self.precompute_session.run_state == GuiRunState.PAUSED:
                    self.state.status_message = "Resume is unsupported for raw matrix sweep"
                    return True
            if self.precompute_buttons.get("stop") and self.precompute_buttons["stop"].collidepoint(event.pos):
                if self.precompute_session and self.precompute_session.run_state == GuiRunState.RUNNING:
                    self.stop_precompute()
                    self.precompute_session = None
                    self.precompute_context = None
                    self.state.status_message = "Precompute stopped and reset"
                    return True

        if self.precompute_session and self.precompute_session.run_state in (GuiRunState.RUNNING, GuiRunState.STOPPING, GuiRunState.PAUSED):
            # Guard scenario-defining controls while precompute is active or paused.
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.state.status_message = "Scenario locked: pending precompute. Resume, stop, or wait for completion."
                return False

        position_action = self.action_selector.handle_event(event)
        if position_action:
            position, action = position_action
            self.state.set_position(position)
            if action:
                self.state.set_position_action(position, action)
            self._refresh()
            return True

        metric = self.metric_dropdown.handle_event(event, self.state.selected_metric)
        if metric:
            self.state.set_metric(metric)
            self._refresh()
            return True

        if event.type == pygame.MOUSEBUTTONDOWN:
            cell_indices = self.matrix.get_cell_indices_at(event.pos)
            if cell_indices is not None:
                row, col = cell_indices
                cell = self._find_payload_cell(row, col)
                if cell is not None:
                    self.state.set_selected_cell(row, col, str(cell.get("hand_key", "")))
                    self.selected_cell_detail = self._build_selected_cell_detail_model()
                    self._load_convergence_data()  # Update convergence plot for selected cell
                    return True

        # Handle convergence panel mouse interactions
        if hasattr(self, 'convergence_panel') and self.convergence_panel is not None:
            if event.type == pygame.MOUSEMOTION:
                if self.convergence_panel.handle_mouse_motion(event.pos[0], event.pos[1]):
                    return True
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.convergence_panel.handle_mouse_click(event.pos[0], event.pos[1], event.button):
                    return True

        return False

    # State Machine Integration Methods

    def set_state_machine_controller(self, controller) -> None:
        """Attach a state machine controller for managing precompute operations.

        Args:
            controller: StateMachineController instance to attach
        """
        self.state_machine_controller = controller
        controller.panel = self
        controller.update_config(controller.config)
        
        # Synchronize state machine state with any restored session
        if self.precompute_session:
            controller.sync_with_run_state(self.precompute_session.run_state)
            
        self.logger.info("State machine controller attached and synchronized")

    def update_precompute_config(self, config) -> None:
        """Update precompute configuration settings.

        Args:
            config: PrecomputeConfig with new settings
        """
        self.precompute_max_workers = config.max_workers
        self.precompute_simulations_per_cell = config.simulations_per_cell
        self.logger.info(f"Precompute config updated: workers={config.max_workers}, sims={config.simulations_per_cell}")

    def start_precompute(self) -> bool:
        """Start precompute operation through state machine.

        Returns:
            True if precompute started successfully
        """
        try:
            if self.precompute_session is None or self.precompute_session.run_state in (GuiRunState.IDLE, GuiRunState.COMPLETED, GuiRunState.FAILED):
                self._start_precompute()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to start precompute: {e}")
            return False

    def pause_precompute(self) -> bool:
        """Pause active precompute operation.

        Returns:
            True if paused successfully
        """
        try:
            if self.precompute_session and self.precompute_session.run_state == GuiRunState.RUNNING:
                self.runner.pause_gui_session(self.precompute_session)
                self._cancel_pending_precompute_futures()
                # Persist results computed so far when pausing (prevent data loss on exit)
                self._persist_completed_precompute_payload()
                self.state.status_message = "Precompute paused"
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to pause precompute: {e}")
            return False

    def resume_precompute(self) -> bool:
        """Resume paused precompute operation.

        Returns:
            True if resumed successfully
        """
        try:
            if self.precompute_session and self.precompute_session.run_state == GuiRunState.PAUSED:
                self.runner.resume_gui_session(self.precompute_session, current_context=self._build_current_context())
                self.state.status_message = "Precompute resumed"
                return True
            return False
        except ValueError as e:
            self.logger.warning(f"Resume blocked: {e}")
            self.state.status_message = "Resume blocked: scenario changed"
            return False
        except Exception as e:
            self.logger.error(f"Failed to resume precompute: {e}")
            return False

    def _shutdown_precompute_executor(self) -> None:
        if self.precompute_executor is None:
            return
        try:
            self.precompute_executor.shutdown(wait=False, cancel_futures=True)
        except Exception as exc:
            self.logger.warning("Failed to shut down precompute executor: %s", exc)
        finally:
            self.precompute_executor = None

    def shutdown(self) -> None:
        """Shut down any active precompute work and release executor resources."""
        try:
            if self.precompute_session and self.precompute_session.run_state in (GuiRunState.RUNNING, GuiRunState.PAUSED):
                self.stop_precompute()
        except Exception:
            self.logger.exception("Error stopping precompute during shutdown")
        self._cancel_pending_precompute_futures()
        self._clear_precompute_result_queue()
        self._shutdown_precompute_executor()
        self.precompute_session = None
        self.precompute_context = None

    def stop_precompute(self) -> bool:
        """Stop precompute operation and transition to stopped state."""
        try:
            if self.precompute_session and self.precompute_session.run_state in (GuiRunState.RUNNING, GuiRunState.PAUSED):
                self.runner.stop_gui_session(self.precompute_session)
                self._cancel_pending_precompute_futures()
                stop_event = getattr(self, 'precompute_stop_event', None)
                if stop_event is not None:
                    stop_event.set()
                thread = getattr(self, 'precompute_thread', None)
                if thread is not None:
                    thread.join(timeout=0)
                self._shutdown_precompute_executor()
                if self.precompute_session.run_state != GuiRunState.COMPLETED:
                    self.runner.transition_session_state(self.precompute_session, GuiRunState.COMPLETED)
                self._persist_completed_precompute_payload()
                self.state.status_message = "Precompute stopped"
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to stop precompute: {e}")
            return False

    def reset_precompute(self) -> None:
        """Reset precompute state to idle."""
        self.precompute_session = None
        self.precompute_context = None
        self.state.status_message = "Precompute reset"

    def get_precompute_status(self) -> Dict[str, Any]:
        """Get comprehensive precompute status information.

        Returns:
            Dictionary with current status and capabilities
        """
        from .precompute_config import PrecomputeConfig

        config = PrecomputeConfig(
            max_workers=self.precompute_max_workers,
            simulations_per_cell=self.precompute_simulations_per_cell
        )

        status = {
            'state': self.precompute_session.run_state.value if self.precompute_session else 'IDLE',
            'config': config.to_dict(),
            'can_start': self.precompute_session is None or self.precompute_session.run_state in (GuiRunState.IDLE, GuiRunState.COMPLETED, GuiRunState.FAILED),
            'can_pause': self.precompute_session is not None and self.precompute_session.run_state == GuiRunState.RUNNING,
            'can_resume': self.precompute_session is not None and self.precompute_session.run_state == GuiRunState.PAUSED,
            'can_stop': self.precompute_session is not None and self.precompute_session.run_state in (GuiRunState.RUNNING, GuiRunState.PAUSED),
        }

        if self.precompute_session:
            status['progress'] = {
                'completed_cells': self.precompute_session.completed_cells,
                'total_cells': self.precompute_session.total_cells,
                'failed_cells': self.precompute_session.failed_cells,
                'current_cell': self.precompute_session.current_cell_index,
            }

        return status

    def _handle_state_machine_event(self, event) -> Optional[bool]:
        """Handle events routed to the state machine controller.

        Args:
            event: Pygame event to process

        Returns:
            True if event was handled by state machine, None otherwise
        """
        if not hasattr(self, 'state_machine_controller') or not self.state_machine_controller:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Route precompute button clicks to state machine
            if self.precompute_buttons.get("start") and self.precompute_buttons["start"].collidepoint(event.pos):
                return self.state_machine_controller.trigger_event('start')
            elif self.precompute_buttons.get("pause") and self.precompute_buttons["pause"].collidepoint(event.pos):
                return self.state_machine_controller.trigger_event('pause')
            elif self.precompute_buttons.get("resume") and self.precompute_buttons["resume"].collidepoint(event.pos):
                return self.state_machine_controller.trigger_event('resume')
            elif self.precompute_buttons.get("stop") and self.precompute_buttons["stop"].collidepoint(event.pos):
                return self.state_machine_controller.trigger_event('stop')

        return None

    def draw(self, screen: pygame.Surface):
        self._reflow_layout()
        self._tick_precompute()

        title_text = f"AoF GTO Solution Browser [{self.panel_state}]"
        title = self.font.render(title_text, True, (245, 245, 245))
        screen.blit(title, title.get_rect(center=(self.width // 2, 14)))

        subtitle = self.small_font.render(self.active_scenario_context, True, (220, 220, 220))
        screen.blit(subtitle, (self.outer_margin, title.get_rect(center=(self.width // 2, 14)).bottom + 4))

        self.action_selector.draw(
            screen,
            self.small_font,
            self.state.selected_position,
            self.state.position_actions or {},
        )
        self.metric_dropdown.draw(screen, self.font, self.state.selected_metric)

        self.matrix.draw(screen, self.small_font, self.payload["cells"], self.state.selected_metric)

        available_cells = sum(1 for cell in self.payload.get("cells", []) if cell.get("status") == PanelState.AVAILABLE.value)
        if 0 < available_cells < 169:
            partial_label = self.small_font.render(f"{available_cells} / 169 AVAILABLE", True, (220, 220, 220))
            screen.blit(partial_label, (self.matrix.x, self.matrix.y - 34))

        self.cell_detail_panel.draw(screen, self.small_font, self.selected_cell_detail)
        if hasattr(self, 'convergence_panel') and self.convergence_panel is not None:
            self.convergence_panel.draw(screen)
            
            # Show tooltip for convergence panel
            tooltip_text = self.convergence_panel.get_tooltip_text()
            if tooltip_text:
                tooltip_font = pygame.font.SysFont("arial", 11)
                tooltip_surface = tooltip_font.render(tooltip_text, True, (0, 0, 0))
                tooltip_bg = pygame.Surface((tooltip_surface.get_width() + 8, tooltip_surface.get_height() + 4))
                tooltip_bg.fill((255, 255, 200))
                tooltip_bg.blit(tooltip_surface, (4, 2))
                
                # Position tooltip near mouse cursor
                mouse_x, mouse_y = pygame.mouse.get_pos()
                tooltip_x = mouse_x + 15
                tooltip_y = mouse_y - 10
                
                # Keep tooltip on screen
                tooltip_x = max(0, min(tooltip_x, self.width - tooltip_bg.get_width()))
                tooltip_y = max(0, min(tooltip_y, self.height - tooltip_bg.get_height()))
                
                screen.blit(tooltip_bg, (tooltip_x, tooltip_y))

        info_x = self.side_x
        info_y = self.top_margin + self.control_h + 10
        info_rect = pygame.Rect(info_x, info_y, self.side_w, 220)
        pygame.draw.rect(screen, (31, 31, 31), info_rect, border_radius=6)
        pygame.draw.rect(screen, (90, 90, 90), info_rect, 1, border_radius=6)

        ctx = self.payload.get("context", {})
        current_action = self.state.get_position_action(self.state.selected_position)
        status_counts: dict[str, int] = {}
        for cell in self.payload.get("cells", []):
            status = str(cell.get("status", "MISSING"))
            status_counts[status] = status_counts.get(status, 0) + 1
        total_cells = sum(status_counts.values())
        
        # Get state machine status
        state_machine_status = "No State Machine"
        if self.state_machine_controller:
            status_info = self.state_machine_controller.get_status_info()
            state_machine_status = f"State: {status_info.get('state', 'unknown').title()}"
        
        lines = [
            f"Position: {self.state.selected_position}",
            f"Action: {current_action}",
            f"Metric: {self.state.selected_metric.replace('_', ' ')}",
            state_machine_status,
            f"All-in players: {ctx.get('active_players', 0)}",
            (
                f"Cells: {total_cells} "
                f"A:{status_counts.get('AVAILABLE', 0)} "
                f"T:{status_counts.get('TIMEOUT', 0)} "
                f"M:{status_counts.get('MISSING', 0)} "
                f"E:{status_counts.get('ERROR', 0)}"
            ),
        ]
        for idx, line in enumerate(lines):
            text = self.font.render(line, True, (230, 230, 230))
            screen.blit(text, (info_rect.x + 12, info_rect.y + 14 + idx * 34))

        if self.state.status_message:
            msg = self.font.render(self.state.status_message, True, (255, 205, 100))
            status_y = self.matrix.y - 25
            screen.blit(msg, (self.matrix.x, status_y))

        # Show loading indicator when database is loading
        if self.is_loading:
            loading_msg = self.font.render("Loading from database...", True, (100, 200, 255))
            loading_y = self.matrix.y - 25  # Same Y as status message
            screen.blit(loading_msg, loading_msg.get_rect(center=(self.width // 2, loading_y)))

        precompute_state = "IDLE"
        snapshot = None
        if self.precompute_session is not None:
            precompute_state = self.precompute_session.run_state.value
            snapshot = self.runner.get_progress_snapshot(self.precompute_session)

        panel_y = info_rect.y + info_rect.height + 12
        panel_rect = pygame.Rect(info_rect.x, panel_y, info_rect.width, 164)
        pygame.draw.rect(screen, (31, 31, 31), panel_rect, border_radius=6)
        pygame.draw.rect(screen, (90, 90, 90), panel_rect, 1, border_radius=6)

        title = self.small_font.render("Precompute Runner", True, (220, 220, 220))
        screen.blit(title, (panel_rect.x + 10, panel_rect.y + 8))
        state_text = self.small_font.render(f"State: {precompute_state}", True, (200, 240, 200))
        screen.blit(state_text, (panel_rect.x + 10, panel_rect.y + 26))

        if snapshot is not None:
            progress = self.small_font.render(
                f"Progress: {snapshot['completed_cells']}/{snapshot['total_cells']}  Failures: {snapshot['failure_count']}",
                True,
                (210, 210, 210),
            )
            screen.blit(progress, (panel_rect.x + 10, panel_rect.y + 44))

        worker_enabled = self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING
        knob_color = (56, 98, 74) if worker_enabled else (56, 56, 56)
        pygame.draw.rect(screen, knob_color, self.precompute_worker_knob, border_radius=4)
        pygame.draw.rect(screen, (90, 90, 90), self.precompute_worker_knob, 1, border_radius=4)
        divider_x = self.precompute_worker_buttons["up"].x
        pygame.draw.line(
            screen,
            (90, 90, 90),
            (divider_x, self.precompute_worker_knob.y + 2),
            (divider_x, self.precompute_worker_knob.bottom - 2),
            1,
        )

        down_label = self.small_font.render("-", True, (240, 240, 240))
        up_label = self.small_font.render("+", True, (240, 240, 240))
        screen.blit(down_label, down_label.get_rect(center=self.precompute_worker_buttons["down"].center))
        screen.blit(up_label, up_label.get_rect(center=self.precompute_worker_buttons["up"].center))

        pygame.draw.rect(screen, knob_color, self.precompute_sim_knob, border_radius=4)
        pygame.draw.rect(screen, (90, 90, 90), self.precompute_sim_knob, 1, border_radius=4)
        sim_divider_x = self.precompute_sim_buttons["up"].x
        pygame.draw.line(
            screen,
            (90, 90, 90),
            (sim_divider_x, self.precompute_sim_knob.y + 2),
            (sim_divider_x, self.precompute_sim_knob.bottom - 2),
            1,
        )
        screen.blit(down_label, down_label.get_rect(center=self.precompute_sim_buttons["down"].center))
        screen.blit(up_label, up_label.get_rect(center=self.precompute_sim_buttons["up"].center))

        row_y = self.precompute_worker_knob.y + 4
        workers_label = self.small_font.render(f"Workers: {self.precompute_max_workers}", True, (210, 210, 210))
        screen.blit(workers_label, (self.precompute_worker_knob.right + 8, row_y))

        sims_label = self.small_font.render(f"Sims/cell: {self.precompute_simulations_per_cell}", True, (210, 210, 210))
        sims_x = self.precompute_sim_knob.x - sims_label.get_width() - 8
        screen.blit(sims_label, (sims_x, row_y))

        for name, rect in self.precompute_buttons.items():
            enabled = True
            if self.state_machine_controller:
                # Use state machine status to determine button enablement
                status_info = self.state_machine_controller.get_status_info()
                if name == "start":
                    enabled = status_info.get('can_start', False)
                elif name == "pause":
                    enabled = status_info.get('can_pause', False)
                elif name == "resume":
                    enabled = status_info.get('can_resume', False)
                elif name == "stop":
                    enabled = status_info.get('can_stop', False)
                elif name == "reset":
                    enabled = status_info.get('can_reset', True)  # Reset is always available
            else:
                # Fallback to session-based logic if no state machine
                if self.precompute_session is None:
                    enabled = name == "start"
                else:
                    state = self.precompute_session.run_state
                    if name == "start":
                        enabled = state in (GuiRunState.IDLE, GuiRunState.COMPLETED, GuiRunState.FAILED)
                    elif name == "pause":
                        enabled = state == GuiRunState.RUNNING
                    elif name == "resume":
                        enabled = state == GuiRunState.PAUSED
                    elif name == "stop":
                        enabled = state == GuiRunState.RUNNING

            color = (56, 98, 74) if enabled else (56, 56, 56)
            pygame.draw.rect(screen, color, rect, border_radius=4)
            pygame.draw.rect(screen, (90, 90, 90), rect, 1, border_radius=4)
            label = self.small_font.render(name.upper(), True, (240, 240, 240))
            screen.blit(label, label.get_rect(center=rect.center))

        if self._rerun_in_progress and self.precompute_session and self.precompute_session.run_state == GuiRunState.RUNNING:
            overlay = pygame.Surface((self.matrix.width, self.matrix.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (self.matrix.x, self.matrix.y))
            rerun_text = self.font.render("Recomputing available scenario...", True, (255, 255, 255))
            screen.blit(rerun_text, (self.matrix.x + 12, self.matrix.y + 12))
