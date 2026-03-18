import os
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_precompute_runner import GuiRunState
from hopilot.gui_components.precompute_config import PrecomputeConfig
from hopilot.gui_components.state_machine_controller import StateMachineController
from hopilot.state_machine_config import SimulationState


@pytest.fixture
def panel_mock():
    panel = Mock()
    panel.precompute_session = None
    panel.start_precompute.return_value = True
    panel.pause_precompute.return_value = True
    panel.resume_precompute.return_value = True
    panel.stop_precompute.return_value = True
    return panel


@pytest.fixture
def controller(panel_mock):
    config = PrecomputeConfig(max_workers=2, simulations_per_cell=1000)
    return StateMachineController(panel=panel_mock, config=config)


def test_controller_initializes_idle_state(controller):
    status = controller.get_status_info()

    assert controller.get_current_state() == SimulationState.IDLE
    assert status["state"] == SimulationState.IDLE
    assert status["can_start"] is True
    assert status["can_pause"] is False
    assert status["can_resume"] is False
    assert status["can_stop"] is False


def test_controller_runs_start_pause_resume_stop_cycle(controller, panel_mock):
    assert controller.trigger_event("start") is True
    assert controller.get_current_state() == SimulationState.RUNNING
    panel_mock.start_precompute.assert_called_once_with()

    assert controller.trigger_event("pause") is True
    assert controller.get_current_state() == SimulationState.PAUSED
    panel_mock.pause_precompute.assert_called_once_with()

    assert controller.trigger_event("resume") is True
    assert controller.get_current_state() == SimulationState.RUNNING
    panel_mock.resume_precompute.assert_called_once_with()

    assert controller.trigger_event("stop") is True
    assert controller.get_current_state() == SimulationState.IDLE
    panel_mock.stop_precompute.assert_called_once_with()


def test_controller_updates_panel_config(controller, panel_mock):
    new_config = PrecomputeConfig(max_workers=4, simulations_per_cell=2500)

    controller.update_config(new_config)

    assert controller.config == new_config
    panel_mock.update_precompute_config.assert_called_once_with(new_config)


def test_controller_exposes_progress_from_panel(controller, panel_mock):
    panel_mock.precompute_session = SimpleNamespace(
        completed_cells=12,
        total_cells=169,
        failed_cells=3,
        run_state=GuiRunState.RUNNING,
    )

    status = controller.get_status_info()

    assert status["progress"] == {
        "completed_cells": 12,
        "total_cells": 169,
        "failed_cells": 3,
        "status": GuiRunState.RUNNING.value,
    }


def test_controller_can_sync_with_runner_states(controller):
    controller.sync_with_run_state(GuiRunState.PAUSED)
    assert controller.get_current_state() == SimulationState.PAUSED

    controller.mark_completed()
    assert controller.get_current_state() == SimulationState.COMPLETED

    controller.mark_failed()
    assert controller.get_current_state() == SimulationState.FAILED


def test_controller_rejects_unknown_event(controller):
    assert controller.trigger_event("bogus") is False


def test_state_machine_transitions_finish_under_100ms(panel_mock):
    controller = StateMachineController(
        panel=panel_mock,
        config=PrecomputeConfig(max_workers=2, simulations_per_cell=1000),
    )

    durations = []
    for event_name in ("start", "pause", "resume", "stop"):
        started = time.perf_counter()
        assert controller.trigger_event(event_name) is True
        durations.append(time.perf_counter() - started)

    assert max(durations) < 0.1