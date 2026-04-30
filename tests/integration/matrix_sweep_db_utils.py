"""Helpers for matrix-sweep integration tests using the real ORM schema."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from hopilot.gto.aof_hand_matrix import iter_canonical_matrix_cells
from hopilot.gto.matrix_sweep_contract import build_run_parameters, mark_raw_sweep_complete
from hopilot.hand_range import HandRange
from hopilot.models import GameState, Player
from tests.fixtures.database_fixtures import DatabaseTestFixture


DEFAULT_MATRIX_SWEEP_CONTRACT = {
    "selected_position": "UTG",
    "hero_action": "all_in",
    "position_actions": {"UTG": "all_in", "BB": "call"},
    "active_players": ["UTG", "BB"],
    "num_opponents": 1,
    "pot_size": 20.0,
    "bet_amount": 10.0,
    "sims_per_combo": 1,
    "matrix_size": "13x13",
    "game_type": "nlhe",
    "run_kind": "matrix_sweep",
}


def create_matrix_sweep_db_fixture(*, use_temp: bool = True) -> DatabaseTestFixture:
    """Create a database fixture suitable for matrix-sweep persistence tests."""
    return DatabaseTestFixture(use_temp=use_temp)


def build_matrix_sweep_contract(**overrides: Any) -> dict[str, Any]:
    """Return a canonical test scenario contract with caller overrides applied."""
    contract = dict(DEFAULT_MATRIX_SWEEP_CONTRACT)
    contract.update(overrides)
    return contract


def seed_matrix_sweep_raw_run(
    repository,
    *,
    scenario_contract: dict[str, Any] | None = None,
    include_unmapped_hero_record: bool = False,
) -> dict[str, Any]:
    """Seed one completed raw sweep boundary with one persisted hero row per canonical cell."""
    contract = build_matrix_sweep_contract(**(scenario_contract or {}))
    raw_start = repository.get_latest_game_state_id() + 1
    parameters = build_run_parameters(contract, raw_game_state_id_start=raw_start)
    simulation_id = repository.create_matrix_sweep_simulation(parameters)

    base_timestamp = datetime(2026, 4, 26, tzinfo=timezone.utc)
    outcome_cycle = ("WIN", "TIE", "LOSS")

    with repository.db_connection.session_scope() as session:
        for index, (_, _, hand_key) in enumerate(iter_canonical_matrix_cells()):
            game_state = GameState(
                timestamp=base_timestamp + timedelta(seconds=index),
                round="preflop",
                pot_size=contract["pot_size"],
                board_cards_str="",
                outcome=outcome_cycle[index % len(outcome_cycle)],
            )
            session.add(game_state)
            session.flush()

            card_one, card_two = HandRange.parse_shorthand(hand_key)[0]
            session.add(
                Player(
                    game_state_id=game_state.id,
                    position=contract["selected_position"],
                    hole_cards=f"{card_one}{card_two}",
                    stack_size=100.0,
                    is_hero=True,
                )
            )
            session.add(
                Player(
                    game_state_id=game_state.id,
                    position="BB",
                    hole_cards="7s2h",
                    stack_size=100.0,
                    is_hero=False,
                )
            )

        if include_unmapped_hero_record:
            game_state = GameState(
                timestamp=base_timestamp + timedelta(seconds=1000),
                round="preflop",
                pot_size=contract["pot_size"],
                board_cards_str="",
                outcome="WIN",
            )
            session.add(game_state)
            session.flush()
            created_at = datetime.now(timezone.utc)
            session.execute(
                text(
                    """
                    INSERT INTO players (game_state_id, position, hole_cards, stack_size, is_hero, created_at, updated_at)
                    VALUES (:game_state_id, :position, :hole_cards, :stack_size, :is_hero, :created_at, :updated_at)
                    """
                ),
                {
                    "game_state_id": game_state.id,
                    "position": contract["selected_position"],
                    "hole_cards": "XxYy",
                    "stack_size": 100.0,
                    "is_hero": True,
                    "created_at": created_at,
                    "updated_at": created_at,
                },
            )

    raw_end = repository.get_latest_game_state_id()
    raw_counts = repository.get_run_raw_counts(raw_start, raw_end)
    parameters = mark_raw_sweep_complete(
        parameters,
        raw_game_state_id_end=raw_end,
        raw_rows_written=raw_counts["raw_game_states"],
        raw_players_written=raw_counts["raw_players"],
        failed_combinations=0,
    )
    repository.update_matrix_sweep_simulation(
        simulation_id,
        parameters=parameters,
        end_timestamp=base_timestamp + timedelta(seconds=2000),
    )

    return {
        "simulation_id": simulation_id,
        "scenario_contract": contract,
        "raw_game_state_id_start": raw_start,
        "raw_game_state_id_end": raw_end,
        "raw_counts": raw_counts,
    }