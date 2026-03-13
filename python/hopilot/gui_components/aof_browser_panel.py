from concurrent.futures import Future, ThreadPoolExecutor
import os
from pathlib import Path
import pygame
import yaml

from hopilot.gto.aof_browser_data_provider import AoFBrowserDataProvider
from hopilot.gto.aof_browser_state import AoFBrowserViewState
from hopilot.gto.aof_precompute_runner import AoFPrecomputeRunner, GuiPrecomputeRunSession, GuiRunState
from hopilot.gui_components.aof_action_selector import AoFActionSelector
from hopilot.gui_components.aof_hand_matrix_panel import AoFHandMatrixPanel
from hopilot.gui_components.aof_metric_dropdown import AoFMetricDropdown
from hopilot.logging_config import get_logger


class AoFBrowserPanel:
    def __init__(self, width: int, height: int, fixture_path: str | None = None):
        self.logger = get_logger(__name__)
        self.width = width
        self.height = height
        self.state = AoFBrowserViewState()
        self.provider = AoFBrowserDataProvider(fixture_path=fixture_path)
        self.runner = AoFPrecomputeRunner(self.provider, getattr(self.provider, "_cache_store", None))
        self.precompute_session: GuiPrecomputeRunSession | None = None
        self.precompute_context: dict | None = None
        self.precompute_simulations_per_cell = 1000
        self.precompute_buttons: dict[str, pygame.Rect] = {}
        self.precompute_worker_buttons: dict[str, pygame.Rect] = {}
        self.precompute_max_workers = self._load_precompute_max_workers()
        self.precompute_executor: ThreadPoolExecutor | None = None
        self.precompute_futures: dict[Future, int] = {}
        self.precompute_payload_persisted = False

        self.top_margin = 20
        self.control_h = 190
        self.side_panel_w = 300
        self.outer_margin = 20
        self.side_x = self.width - self.side_panel_w + self.outer_margin
        self.side_w = self.side_panel_w - (self.outer_margin * 2)

        matrix_region_width = width - self.side_panel_w - (self.outer_margin * 2)
        self.action_selector = AoFActionSelector(self.outer_margin, self.top_margin + 28, width=matrix_region_width)
        self.metric_dropdown = AoFMetricDropdown(self.side_x, self.top_margin + 24, width=self.side_w)
        self.matrix = AoFHandMatrixPanel(self.outer_margin, self.top_margin + self.control_h + 10)
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
        self._restore_precompute_checkpoint_if_available()

    def _reflow_layout(self) -> None:
        self.side_x = self.width - self.side_panel_w + self.outer_margin
        self.side_w = self.side_panel_w - (self.outer_margin * 2)
        matrix_x = self.outer_margin
        matrix_y = self.top_margin + self.control_h + 10
        matrix_w = self.width - self.side_panel_w - (self.outer_margin * 2)
        matrix_h = self.height - matrix_y - self.outer_margin
        self.matrix.set_bounds(matrix_x, matrix_y, matrix_w, matrix_h)
        self.metric_dropdown.set_bounds(self.side_x, self.top_margin + 24, self.side_w)
        self._build_precompute_controls()

    def _build_precompute_controls(self) -> None:
        side_x = self.side_x
        start_y = self.top_margin + 56
        button_w = self.side_w
        button_h = 24
        gap = 6
        self.precompute_buttons = {
            "start": pygame.Rect(side_x, start_y, button_w, button_h),
            "pause": pygame.Rect(side_x, start_y + (button_h + gap), button_w, button_h),
            "resume": pygame.Rect(side_x, start_y + 2 * (button_h + gap), button_w, button_h),
            "stop": pygame.Rect(side_x, start_y + 3 * (button_h + gap), button_w, button_h),
        }
        worker_y = start_y + 4 * (button_h + gap) + 2
        self.precompute_worker_buttons = {
            "down": pygame.Rect(side_x, worker_y, 24, button_h),
            "up": pygame.Rect(side_x + button_w - 24, worker_y, 24, button_h),
        }

    def _default_precompute_workers(self) -> int:
        workers = os.cpu_count() or 2
        return max(1, min(4, workers))

    @staticmethod
    def _clamp_precompute_workers(raw_workers: int) -> int:
        return max(1, min(16, int(raw_workers)))

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
        self.payload = self.provider.get_matrix_payload(
            self.state.selected_position,
            self.state.selected_metric,
            self.state.position_actions,
            allow_compute=False,
        )
        self.state.status_message = self.payload.get("status_message")

    def _restore_precompute_checkpoint_if_available(self) -> None:
        context = self._build_current_context()
        fingerprint = self.runner.build_scenario_fingerprint(context)
        restored = self.runner.restore_latest_gui_session(scenario_fingerprint=fingerprint)
        if restored is None:
            return
        self.precompute_context = context
        self.precompute_session = restored
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
        for future in list(self.precompute_futures.keys()):
            future.cancel()
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

        if self.precompute_session.run_state == GuiRunState.COMPLETED and not self.precompute_futures:
            self._persist_completed_precompute_payload()
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

            if self.precompute_buttons.get("start") and self.precompute_buttons["start"].collidepoint(event.pos):
                if self.precompute_session is None or self.precompute_session.run_state in (GuiRunState.IDLE, GuiRunState.COMPLETED, GuiRunState.FAILED):
                    self._start_precompute()
                    return True
            if self.precompute_buttons.get("pause") and self.precompute_buttons["pause"].collidepoint(event.pos):
                if self.precompute_session and self.precompute_session.run_state == GuiRunState.RUNNING:
                    self.runner.pause_gui_session(self.precompute_session)
                    self._cancel_pending_precompute_futures()
                    self.state.status_message = "Precompute paused"
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
                if self.precompute_session and self.precompute_session.run_state == GuiRunState.RUNNING:
                    self.runner.stop_gui_session(self.precompute_session)
                    self._cancel_pending_precompute_futures()
                    self.state.status_message = "Precompute stopped"
                    return True

        if self.precompute_session and self.precompute_session.run_state in (GuiRunState.RUNNING, GuiRunState.STOPPING):
            # Guard scenario-defining controls while precompute is active.
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.state.status_message = "Scenario controls are locked while precompute is running"
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

        return False

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
        lines = [
            f"Position: {self.state.selected_position}",
            f"Action: {current_action}",
            f"Metric: {self.state.selected_metric.replace('_', ' ')}",
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
            status_y = self.top_margin + self.control_h - 8
            screen.blit(msg, msg.get_rect(center=(self.width // 2, status_y)))

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

        workers_label = self.small_font.render(f"Workers: {self.precompute_max_workers}", True, (210, 210, 210))
        screen.blit(workers_label, (self.side_x + 30, self.precompute_worker_buttons["down"].y + 4))

        for name, rect in self.precompute_worker_buttons.items():
            worker_enabled = not self.precompute_futures and (
                self.precompute_session is None or self.precompute_session.run_state != GuiRunState.RUNNING
            )
            color = (56, 98, 74) if worker_enabled else (56, 56, 56)
            pygame.draw.rect(screen, color, rect, border_radius=4)
            pygame.draw.rect(screen, (90, 90, 90), rect, 1, border_radius=4)
            symbol = "-" if name == "down" else "+"
            label = self.small_font.render(symbol, True, (240, 240, 240))
            screen.blit(label, label.get_rect(center=rect.center))

        for name, rect in self.precompute_buttons.items():
            enabled = True
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
