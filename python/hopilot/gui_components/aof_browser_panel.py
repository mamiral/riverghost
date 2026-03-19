from concurrent.futures import Future, ThreadPoolExecutor
import os
from pathlib import Path
import pygame
import yaml
from typing import List, Dict, Any, Optional

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_browser_state import AoFBrowserViewState
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiPrecomputeRunSession, GuiRunState
from hopilot.gui_components.aof_action_selector import AoFActionSelector
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
        self.provider = AoFBrowserDataProvider(fixture_path=fixture_path, database_url=database_url)
        self.runner = AoFPrecomputeRunner(self.provider, getattr(self.provider, "_cache_store", None))
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
        self.precompute_executor: ThreadPoolExecutor | None = None
        self.precompute_futures: dict[Future, int] = {}
        self.precompute_payload_persisted = False

        # Attempt to restore previous session
        self._restore_precompute_checkpoint_if_available()

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
        self.payload = self.provider.get_matrix_payload(
            self.state.selected_position,
            self.state.selected_metric,
            self.state.position_actions,
            allow_compute=False,
        )
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
        self.convergence_panel = ConvergencePanel(convergence_x, convergence_y, convergence_w, convergence_h)

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

    def _refresh(self):
        # Check if database provider is available
        if hasattr(self.provider, '_database_provider') and self.provider._database_provider is not None:
            # Database mode - handle async loading
            if not self.is_loading:
                self.is_loading = True
                self._start_async_refresh()
        else:
            # Legacy cache/solver mode - synchronous
            self.payload = self.provider.get_matrix_payload(
                self.state.selected_position,
                self.state.selected_metric,
                self.state.position_actions,
                allow_compute=False,
            )
            self._invalidate_selected_cell_if_needed()
            self.state.status_message = self.payload.get("status_message")
            self.selected_cell_detail = self._build_selected_cell_detail_model()
            self._load_convergence_data()

    def _start_async_refresh(self):
        """Start async database refresh in background thread."""
        import threading
        import asyncio

        def async_refresh():
            try:
                # Create new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Get payload from database provider
                payload = self.provider.get_matrix_payload(
                    self.state.selected_position,
                    self.state.selected_metric,
                    self.state.position_actions,
                    allow_compute=False,
                )

                # Post result to main thread
                import pygame
                pygame.event.post(pygame.event.Event(pygame.USEREVENT, {
                    "type": "database_refresh",
                    "payload": payload,
                    "success": True
                }))

            except Exception as e:
                self.logger.error(f"Async refresh failed: {e}")
                import pygame
                pygame.event.post(pygame.event.Event(pygame.USEREVENT, {
                    "type": "database_refresh",
                    "error": str(e),
                    "success": False
                }))

        # Start background thread
        thread = threading.Thread(target=async_refresh, daemon=True)
        thread.start()

    def _handle_async_refresh_result(self, data: dict) -> None:
        """Handle result from async database refresh."""
        if data.get("success"):
            self.payload = data["payload"]
            self._invalidate_selected_cell_if_needed()
            self.state.status_message = self.payload.get("status_message")
            self.selected_cell_detail = self._build_selected_cell_detail_model()
            self._load_convergence_data()
        else:
            self.state.status_message = f"Database error: {data.get('error', 'Unknown error')}"

        self.is_loading = False

    def _load_convergence_data(self):
        """Load convergence data for current position/action or selected cell."""
        if not hasattr(self, 'convergence_panel') or self.convergence_panel is None:
            self.logger.warning("Convergence panel not initialized, skipping convergence data loading")
            return
            
        try:
            current_action = self.state.get_position_action(self.state.selected_position)
            
            # If a cell is selected, show cell-specific convergence data
            if self.state.selected_cell is not None:
                cell_convergence_data = self._generate_cell_convergence_data()
                if cell_convergence_data:
                    row, col, hand_key = self.state.selected_cell
                    self.convergence_panel.set_convergence_data(
                        cell_convergence_data,
                        f"{self.state.selected_position} - {hand_key}",
                        current_action
                    )
                    return
            
            # Try database first for position-level convergence
            if hasattr(self.provider, '_database_provider') and self.provider._database_provider is not None:
                if hasattr(self.provider._database_provider, 'get_convergence_data'):
                    convergence_data = self.provider._database_provider.get_convergence_data(
                        self.state.selected_position,
                        self.state.position_actions
                    )
                    if convergence_data:
                        self.convergence_panel.set_convergence_data(
                            convergence_data,
                            self.state.selected_position,
                            current_action
                        )
                        return
            
            # Fallback: generate mock convergence data from current payload
            mock_data = self._generate_mock_convergence_data()
            if mock_data:
                self.convergence_panel.set_convergence_data(
                    mock_data,
                    self.state.selected_position,
                    current_action
                )
            else:
                self.convergence_panel.set_convergence_data([], "", "")
                
        except Exception as e:
            self.logger.warning(f"Failed to load convergence data: {e}")
            if hasattr(self, 'convergence_panel') and self.convergence_panel is not None:
                self.convergence_panel.set_convergence_data([], "", "")

    def _generate_cell_convergence_data(self) -> List[Dict[str, Any]]:
        """Generate mock convergence data for the selected cell."""
        if self.state.selected_cell is None:
            return []
        
        row, col, hand_key = self.state.selected_cell
        cell = self._find_payload_cell(row, col)
        
        if cell is None or cell.get("status") != "AVAILABLE" or cell.get("value") is None:
            return []
        
        # Use the cell's current equity value as the final converged value
        final_equity = float(cell["value"])
        
        # Generate convergence points showing progression toward the cell's final equity
        simulation_counts = [100, 500, 1000, 2500, 5000, 10000, 25000, 50000]
        convergence_data = []
        
        for i, sim_count in enumerate(simulation_counts):
            if i == 0:
                # Start with some noise around the final value
                equity = final_equity + (0.1 * (0.5 - i/len(simulation_counts)))
            else:
                # Gradually converge to final value with decreasing variance
                noise = 0.03 * (1 - i/len(simulation_counts)) * (0.5 - i/len(simulation_counts))
                equity = final_equity + noise
            
            # Ensure equity stays within reasonable bounds
            equity = max(0.0, min(1.0, equity))
            
            convergence_data.append({
                "num_simulations": sim_count,
                "average_equity": equity,
                "timestamp": None  # Mock data doesn't have timestamps
            })
        
        return convergence_data

    def _generate_mock_convergence_data(self) -> List[Dict[str, Any]]:
        """Generate mock convergence data for demonstration purposes."""
        # Check if we have any computed cells in the current payload
        cells = self.payload.get("cells", [])
        available_cells = [cell for cell in cells if cell.get("status") == "AVAILABLE" and cell.get("value") is not None]
        
        if not available_cells:
            return []
        
        # Calculate average equity from available cells
        equities = [cell["value"] for cell in available_cells]
        final_equity = sum(equities) / len(equities)
        
        # Generate convergence points showing progression toward final equity
        # Simulate convergence over different simulation counts
        simulation_counts = [100, 500, 1000, 2500, 5000, 10000, 25000, 50000]
        convergence_data = []
        
        for i, sim_count in enumerate(simulation_counts):
            if i == 0:
                # Start with some noise around the final value
                equity = final_equity + (0.1 * (0.5 - i/len(simulation_counts)))
            else:
                # Gradually converge to final value with decreasing variance
                noise = 0.05 * (1 - i/len(simulation_counts)) * (0.5 - i/len(simulation_counts))
                equity = final_equity + noise
            
            # Ensure equity stays within reasonable bounds
            equity = max(0.0, min(1.0, equity))
            
            convergence_data.append({
                "num_simulations": sim_count,
                "average_equity": equity,
                "timestamp": None  # Mock data doesn't have timestamps
            })
        
        return convergence_data

    def _invalidate_selected_cell_if_needed(self) -> None:
        if self.state.selected_cell is None:
            return
        row, col, hand_key = self.state.selected_cell
        cell = self._find_payload_cell(row, col)
        if cell is None or str(cell.get("hand_key", "")) != str(hand_key):
            self.state.clear_selected_cell()
            self.state.status_message = "Selected cell cleared after context refresh"
            self._load_convergence_data()  # Update convergence plot back to position-level

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
        # Try to restore without requiring current scenario to match
        if self.runner.store is None:
            return
        latest_run_id = self.runner.store.get_latest_run_id(statuses=(GuiRunState.RUNNING.value, GuiRunState.PAUSED.value))
        if latest_run_id is None:
            return
        
        restored = self.runner.restore_gui_session(run_id=int(latest_run_id), scenario_fingerprint="")
        if restored is None:
            return
        
        # Parse the stored fingerprint to restore scenario context
        import json
        try:
            context_data = json.loads(restored.scenario_fingerprint)
            if context_data and context_data.get("position"):
                # Apply the saved scenario to the UI
                self.state.set_position(context_data["position"])
                if context_data.get("metric"):
                    self.state.set_metric(context_data["metric"])
                if context_data.get("position_actions"):
                    for pos, action in context_data["position_actions"].items():
                        self.state.set_position_action(pos, action)
        except (json.JSONDecodeError, KeyError):
            self.logger.warning("Failed to parse scenario fingerprint during restoration")
        
        # Now set the precompute session with the restored scenario
        precompute_context = self._build_current_context()
        self.precompute_context = precompute_context
        self.precompute_session = restored
        
        # Try to load cached payload for the restored session
        cached_payload = self.provider.get_matrix_payload(
            self.state.selected_position,
            self.state.selected_metric,
            self.state.position_actions,
            allow_compute=False,
        )
        if cached_payload and cached_payload.get("cells"):
            self.payload = cached_payload
            self.selected_cell_detail = self._build_selected_cell_detail_model()
            self._load_convergence_data()  # Load convergence data for restored results
        
        self.state.status_message = "Precompute checkpoint restored"

    def _build_current_context(self) -> dict:
        return self.provider._build_context(  # pylint: disable=protected-access
            position=self.state.selected_position,
            metric=self.state.selected_metric,
            position_actions=self.state.position_actions,
        )

    def _start_precompute(self) -> None:
        self.precompute_context = self._build_current_context()
        fingerprint = self.runner.build_scenario_fingerprint(self.precompute_context)
        self.precompute_session = self.runner.create_gui_session(
            simulations_per_cell=self.precompute_simulations_per_cell,
            scenario_fingerprint=fingerprint,
            total_cells=169,
        )
        self.runner.transition_session_state(self.precompute_session, GuiRunState.RUNNING)
        self.runner.bind_gui_run(self.precompute_session)
        if self.precompute_executor is None:
            self.precompute_executor = ThreadPoolExecutor(max_workers=self.precompute_max_workers, thread_name_prefix="aof-precompute")
        self._cancel_pending_precompute_futures()
        self.precompute_payload_persisted = False
        self.payload = {
            "context": dict(self.precompute_context),
            "cells": [
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
            ],
            "status_message": "Precompute started",
        }
        self.selected_cell_detail = self._build_selected_cell_detail_model()
        self.state.status_message = "Precompute started"

    def _persist_completed_precompute_payload(self) -> None:
        if self.precompute_payload_persisted:
            return
        if self.precompute_context is None:
            return
        store = getattr(self.provider, "_cache_store", None)
        if store is None:
            self.precompute_payload_persisted = True
            return

        try:
            runtime_signature = self.provider._runtime_signature(self.precompute_context)  # pylint: disable=protected-access
            solver_key = self.provider._build_solver_equivalence_key(self.precompute_context)  # pylint: disable=protected-access
            payload = {
                "context": dict(self.precompute_context),
                "cells": list(self.payload.get("cells", [])),
                "status_message": self.payload.get("status_message"),
            }
            store.upsert_payload(solver_key, payload, runtime_signature)
            # Drop stale in-memory misses so subsequent cache-only reads hit persisted rows.
            self.provider.clear_cache()
            request_key = self.provider._build_cache_key(self.precompute_context)  # pylint: disable=protected-access
            self.provider._cache[request_key] = payload  # pylint: disable=protected-access
            self.precompute_payload_persisted = True
            self.state.status_message = "Precompute completed and cache saved"
            self.logger.info(
                "AoF gui precompute event=gui_precompute_payload_persisted fields=%s",
                {
                    "run_id": self.precompute_session.run_id if self.precompute_session else None,
                    "scenario_key_hash": solver_key,
                    "cells": len(payload.get("cells", [])),
                },
            )
        except Exception as exc:  # pragma: no cover - defensive persistence guard
            self.logger.warning("Failed to persist threaded precompute payload: %s", exc)

    def _cancel_pending_precompute_futures(self) -> None:
        """Cancel pending futures and reset cell index to reprocess them on resume.
        
        When futures are cancelled due to pause, we must track which cells had pending
        work and reset next_cell_index to the minimum, otherwise those cells are skipped
        on resume (Bug: cells skipped when PAUSE/RESUME).
        """
        if self.precompute_futures:
            # Get all pending cell indices before clearing
            pending_cell_indices = list(self.precompute_futures.values())
            min_pending_index = min(pending_cell_indices)
            
            # Cancel all futures
            for future in list(self.precompute_futures.keys()):
                future.cancel()
            
            # Reset next_cell_index to the minimum pending cell
            # This ensures cancelled cells will be reprocessed on resume
            if self.precompute_session and min_pending_index < self.precompute_session.next_cell_index:
                self.logger.info(
                    f"Resetting next_cell_index from {self.precompute_session.next_cell_index} to "
                    f"{min_pending_index} to reprocess {len(pending_cell_indices)} cancelled cells"
                )
                self.precompute_session.next_cell_index = min_pending_index
        
        self.precompute_futures.clear()

    def _tick_precompute(self) -> None:
        if self.precompute_session is None or self.precompute_context is None:
            return

        for future in list(self.precompute_futures.keys()):
            if not future.done():
                continue
            cell_index = self.precompute_futures.pop(future, 0)
            try:
                cell, status_message = future.result()
            except Exception as exc:  # pragma: no cover - defensive thread result guard
                row = int(cell_index) // 13
                col = int(cell_index) % 13
                cell = {
                    "row": row,
                    "col": col,
                    "hand_key": self.provider._matrix_keys[row][col],  # pylint: disable=protected-access
                    "value": None,
                    "status": "ERROR",
                    "display": "-",
                }
                status_message = str(exc)

            self.runner.apply_gui_cell_result(
                session=self.precompute_session,
                context=self.precompute_context,
                cell=cell,
                status_message=status_message,
            )
            index = int(cell["row"]) * 13 + int(cell["col"])
            self.payload["cells"][index] = cell
            self.payload["context"] = dict(self.precompute_context)
            self.payload["status_message"] = self.precompute_context.get("status_message")

        self.selected_cell_detail = self._build_selected_cell_detail_model()
        self._load_convergence_data()  # Update convergence plot with new data

        if self.precompute_session.run_state == GuiRunState.COMPLETED and not self.precompute_futures:
            self._persist_completed_precompute_payload()
            if self.state_machine_controller:
                self.state_machine_controller.mark_completed()
            return

        if self.precompute_session.run_state == GuiRunState.FAILED:
            if self.state_machine_controller:
                self.state_machine_controller.mark_failed()
            return

        if self.precompute_session.run_state != GuiRunState.RUNNING:
            return

        if self.precompute_executor is None:
            self.precompute_executor = ThreadPoolExecutor(max_workers=self.precompute_max_workers, thread_name_prefix="aof-precompute")

        while (
            len(self.precompute_futures) < self.precompute_max_workers
            and self.precompute_session.next_cell_index < self.precompute_session.total_cells
            and self.precompute_session.run_state == GuiRunState.RUNNING
        ):
            idx = int(self.precompute_session.next_cell_index)
            self.precompute_session.next_cell_index = idx + 1
            self.runner.mark_gui_dispatch(self.precompute_session)

            context_copy = dict(self.precompute_context)
            if "position_actions" in context_copy and isinstance(context_copy["position_actions"], dict):
                context_copy["position_actions"] = dict(context_copy["position_actions"])
            future = self.precompute_executor.submit(self.runner.compute_gui_cell, context=context_copy, cell_index=idx)
            self.precompute_futures[future] = idx

        processed = self.precompute_session.completed_cells + self.precompute_session.failed_cells
        if (
            processed >= self.precompute_session.total_cells
            and not self.precompute_futures
            and self.precompute_session.run_state == GuiRunState.RUNNING
        ):
            self.runner.transition_session_state(self.precompute_session, GuiRunState.COMPLETED)
            self.runner.mark_gui_dispatch(self.precompute_session)
            self.state.status_message = "Precompute completed"

        if self.precompute_session.run_state == GuiRunState.COMPLETED and not self.precompute_futures:
            self._persist_completed_precompute_payload()

    def handle_event(self, event):
        if event.type == pygame.USEREVENT:
            # Handle async database refresh completion
            if hasattr(event, 'data') and event.data.get('type') == 'database_refresh':
                self._handle_async_refresh_result(event.data)
                return True

        # Route state machine events if controller is attached
        if hasattr(self, 'state_machine_controller') and self.state_machine_controller:
            state_machine_result = self._handle_state_machine_event(event)
            if state_machine_result is not None:
                return state_machine_result

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.precompute_worker_buttons.get("down") and self.precompute_worker_buttons["down"].collidepoint(event.pos):
                if not self.precompute_futures and (self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING):
                    self.precompute_max_workers = max(1, self.precompute_max_workers - 1)
                    if self.precompute_executor is not None:
                        self.precompute_executor.shutdown(wait=False)
                        self.precompute_executor = None
                    self.state.status_message = f"Workers set to {self.precompute_max_workers}"
                    return True
            if self.precompute_worker_buttons.get("up") and self.precompute_worker_buttons["up"].collidepoint(event.pos):
                if not self.precompute_futures and (self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING):
                    self.precompute_max_workers = min(16, self.precompute_max_workers + 1)
                    if self.precompute_executor is not None:
                        self.precompute_executor.shutdown(wait=False)
                        self.precompute_executor = None
                    self.state.status_message = f"Workers set to {self.precompute_max_workers}"
                    return True
            if self.precompute_sim_buttons.get("down") and self.precompute_sim_buttons["down"].collidepoint(event.pos):
                if not self.precompute_futures and (self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING):
                    step = self._simulation_step_size(self.precompute_simulations_per_cell, getattr(event, "button", 1))
                    self.precompute_simulations_per_cell = self._clamp_precompute_simulations(self.precompute_simulations_per_cell - step)
                    self.state.status_message = f"Simulations per cell set to {self.precompute_simulations_per_cell}"
                    return True
            if self.precompute_sim_buttons.get("up") and self.precompute_sim_buttons["up"].collidepoint(event.pos):
                if not self.precompute_futures and (self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING):
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
                    self.pause_precompute()
                    return True
            if self.precompute_buttons.get("resume") and self.precompute_buttons["resume"].collidepoint(event.pos):
                if self.precompute_session and self.precompute_session.run_state == GuiRunState.PAUSED:
                    try:
                        self.runner.resume_gui_session(self.precompute_session, current_context=self._build_current_context())
                        self.state.status_message = "Precompute resumed"
                    except ValueError:
                        self.state.status_message = "Resume blocked: scenario changed"
                    return True
            if self.precompute_buttons.get("stop") and self.precompute_buttons["stop"].collidepoint(event.pos):
                if self.precompute_session and self.precompute_session.run_state in (GuiRunState.RUNNING, GuiRunState.PAUSED):
                    self.stop_precompute()
                    # For direct button clicks (not via state machine), clear session to allow fresh start
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

    def stop_precompute(self) -> bool:
        """Stop precompute operation and transition to stopped state.

        Does NOT immediately clear the session - that's handled by the state 
        machine's clear_session_data() callback on reset. This allows the state
        machine to check all_work_done() before clearing the session.

        Returns:
            True if stopped successfully
        """
        try:
            if self.precompute_session and self.precompute_session.run_state in (GuiRunState.RUNNING, GuiRunState.PAUSED):
                if self.precompute_session.run_state == GuiRunState.RUNNING:
                    self.runner.stop_gui_session(self.precompute_session)
                self._cancel_pending_precompute_futures()
                # Mark as COMPLETED so all_work_done() returns True for state machine transition
                if self.precompute_session.run_state != GuiRunState.COMPLETED:
                    self.runner.transition_session_state(self.precompute_session, GuiRunState.COMPLETED)
                # Persist results computed so far when stopping (prevent data loss on exit)
                self._persist_completed_precompute_payload()
                # DO NOT clear session here - state machine's all_work_done() checks session state
                # Session will be cleared by clear_session_data() callback on COMPLETED->IDLE transition
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
        if self.precompute_executor is not None:
            self.precompute_executor.shutdown(wait=False)
            self.precompute_executor = None
        self.precompute_futures.clear()
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

        title = self.font.render("AoF GTO Solution Browser", True, (245, 245, 245))
        screen.blit(title, title.get_rect(center=(self.width // 2, 14)))

        self.action_selector.draw(
            screen,
            self.small_font,
            self.state.selected_position,
            self.state.position_actions or {},
        )
        self.metric_dropdown.draw(screen, self.font, self.state.selected_metric)

        self.matrix.draw(screen, self.small_font, self.payload["cells"], self.state.selected_metric)
        self.cell_detail_panel.draw(screen, self.small_font, self.selected_cell_detail)
        if hasattr(self, 'convergence_panel') and self.convergence_panel is not None:
            self.convergence_panel.draw(screen)

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
            loading_y = self.top_margin + self.control_h - 8
            if self.state.status_message:
                loading_y -= 24  # Position above status message if present
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

        worker_enabled = not self.precompute_futures and (
            self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING
        )
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
