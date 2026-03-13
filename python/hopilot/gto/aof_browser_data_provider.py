from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from hopilot.gto.aof_browser_state import ACTIONS, METRICS, POSITIONS
from hopilot.gto.aof_hand_matrix import build_matrix_keys, format_metric_value


class AoFBrowserDataProvider:
    def __init__(self, fixture_path: str | None = None):
        self._matrix_keys = build_matrix_keys()
        self._data: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
        if fixture_path and Path(fixture_path).exists():
            with open(fixture_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            self._data = loaded.get("data", {})
        if not self._data:
            self._data = self._build_default_data()

    def _build_default_data(self) -> dict[str, dict[str, dict[str, dict[str, float]]]]:
        data: dict[str, dict[str, dict[str, dict[str, float]]]] = {}
        for p_i, position in enumerate(POSITIONS):
            data[position] = {}
            for a_i, action in enumerate(ACTIONS):
                data[position][action] = {}
                for m_i, metric in enumerate(METRICS):
                    metric_map: dict[str, float] = {}
                    for row in range(13):
                        for col in range(13):
                            key = self._matrix_keys[row][col]
                            strength = (13 - row + 13 - col) / 26.0
                            bias = (p_i * 0.03) + (a_i * 0.02) + (m_i * 0.01)
                            if metric == "EV":
                                value = (strength - 0.5) * 2.0 + bias
                            else:
                                value = min(0.99, max(0.01, strength + bias))
                            metric_map[key] = round(value, 4)
                    data[position][action][metric] = metric_map
        return data

    def get_matrix_payload(self, position: str, action: str, metric: str) -> dict[str, Any]:
        context = {"position": position, "action": action, "metric": metric}
        if position not in self._data or action not in self._data[position] or metric not in self._data[position][action]:
            return self._build_missing_payload(context)

        metric_map = self._data[position][action][metric]
        cells: list[dict[str, Any]] = []
        for row in range(13):
            for col in range(13):
                key = self._matrix_keys[row][col]
                value = metric_map.get(key)
                status = "AVAILABLE" if value is not None else "MISSING"
                cells.append(
                    {
                        "row": row,
                        "col": col,
                        "hand_key": key,
                        "value": value,
                        "status": status,
                        "display": format_metric_value(metric, value),
                    }
                )
        return {"context": context, "cells": cells}

    def _build_missing_payload(self, context: dict[str, str]) -> dict[str, Any]:
        cells: list[dict[str, Any]] = []
        metric = context["metric"]
        for row in range(13):
            for col in range(13):
                key = self._matrix_keys[row][col]
                cells.append(
                    {
                        "row": row,
                        "col": col,
                        "hand_key": key,
                        "value": None,
                        "status": "MISSING",
                        "display": format_metric_value(metric, None),
                    }
                )
        return {"context": context, "cells": cells}
