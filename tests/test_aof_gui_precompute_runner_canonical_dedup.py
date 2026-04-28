import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.aof_hand_matrix import iter_canonical_matrix_cells
from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.gto.matrix_sweep_contract import build_run_parameters, mark_raw_sweep_complete


def test_canonical_dedup_reuses_persisted_cells_with_request_local_context(tmp_path):
    """Test that canonical deduplication reuses persisted cells for same scenario."""
    db_path = str(tmp_path / "aof_gui_canonical.sqlite3")
    database_url = f"sqlite:///{db_path}"
    provider = BrowserDatabaseProvider(database_url=database_url)
    
    # Populate database with test data for canonical scenario
    repo = provider.database_repository
    from hopilot.models import MatrixCell, AggregatedMetric
    with repo.connection.session_scope() as session:
        # Create a completed matrix sweep simulation with scenario contract metadata
        contract = build_run_parameters({
            "selected_position": "UTG",
            "hero_action": "ALL_IN",
            "position_actions": {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
            "active_players": ["UTG", "BTN"],
            "num_opponents": 1,
            "pot_size": 20.0,
            "bet_amount": 10.0,
            "sims_per_combo": 120,
            "matrix_size": "13x13",
            "game_type": "cash",
            "run_kind": "matrix_sweep",
        })
        sim_id = repo.create_matrix_sweep_simulation(contract)
        matrix_id = repo.create_hand_matrix(sim_id)

        # Insert a full canonical matrix so the provider can build a complete payload
        aa_cell = None
        for row, col, hand_key in iter_canonical_matrix_cells():
            cell = MatrixCell(
                matrix_id=matrix_id,
                row_index=row,
                col_index=col,
                hand_combination=hand_key,
            )
            session.add(cell)
            session.flush()
            if hand_key == "AA":
                aa_cell = cell

        assert aa_cell is not None
        # Add metrics for EV and WIN_LOSE_PROBABILITY in the same aggregated row
        metrics = AggregatedMetric(
            cell_id=aa_cell.id,
            ev=0.75,
            win_probability=0.82,
            sample_count=1000,
            last_updated="2026-01-01T00:00:00+00:00"
        )
        session.add(metrics)

    # Update the simulation to a completed run so it will be found by contract lookup
    contract = mark_raw_sweep_complete(contract, raw_game_state_id_end=1, raw_rows_written=1, raw_players_written=1, failed_combinations=0)
    repo.update_matrix_sweep_simulation(sim_id, parameters=contract, end_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))

    # Test deduplication: same scenario should reuse persisted data
    payload_a = provider.get_matrix_payload(
        position="UTG",
        metric="EV",
        position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
    )

    payload_b = provider.get_matrix_payload(
        position="UTG",
        metric="WIN_LOSE_PROBABILITY",
        position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "FOLD", "BB": "FOLD"},
    )

    # Verify context is correct
    assert payload_a["context"]["position"] == "UTG"
    assert payload_a["context"]["metric"] == "EV"
    assert payload_b["context"]["position"] == "UTG"
    assert payload_b["context"]["metric"] == "WIN_LOSE_PROBABILITY"
    
    # Verify deduplication worked - both payloads should have the AA cell with correct values
    aa_cell_a = next((cell for cell in payload_a["cells"] if cell.get("hand_key") == "AA"), None)
    aa_cell_b = next((cell for cell in payload_b["cells"] if cell.get("hand_key") == "AA"), None)
    
    assert aa_cell_a is not None, "AA cell should be present in EV payload"
    assert aa_cell_b is not None, "AA cell should be present in WIN_LOSE_PROBABILITY payload"
    assert aa_cell_a["value"] == 0.75, "AA EV value should be 0.75"
    assert aa_cell_b["value"] == 0.82, "AA WIN_LOSE_PROBABILITY value should be 0.82"


def test_uncontested_payload_not_reused_for_contested_scenario(tmp_path):
    """Test that uncontested payloads are not incorrectly reused for contested scenarios."""
    db_path = str(tmp_path / "aof_gui_canonical_separation.sqlite3")
    database_url = f"sqlite:///{db_path}"
    provider = BrowserDatabaseProvider(database_url=database_url)
    
    # Populate database with uncontested scenario data
    repo = provider.database_repository
    from hopilot.models import MatrixCell, AggregatedMetric
    with repo.connection.session_scope() as session:
        # Create a completed matrix sweep simulation with scenario contract metadata
        contract = build_run_parameters({
            "selected_position": "BB",
            "hero_action": "ALL_IN",
            "position_actions": {"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"},
            "active_players": ["UTG", "BTN", "SB", "BB"],
            "num_opponents": 3,
            "pot_size": 20.0,
            "bet_amount": 10.0,
            "sims_per_combo": 120,
            "matrix_size": "13x13",
            "game_type": "cash",
            "run_kind": "matrix_sweep",
        })
        sim_id = repo.create_matrix_sweep_simulation(contract)
        matrix_id = repo.create_hand_matrix(sim_id)

        # Insert a full canonical matrix so the provider can build a complete payload
        aa_cell = None
        for row, col, hand_key in iter_canonical_matrix_cells():
            cell = MatrixCell(
                matrix_id=matrix_id,
                row_index=row,
                col_index=col,
                hand_combination=hand_key,
            )
            session.add(cell)
            session.flush()
            if hand_key == "AA":
                aa_cell = cell

        assert aa_cell is not None
        # Add metrics for uncontested WIN_LOSE_PROBABILITY
        uncontested_metric = AggregatedMetric(
            cell_id=aa_cell.id,
            win_probability=0.95,  # High win probability in uncontested scenario
            sample_count=1000,
            last_updated="2026-01-01T00:00:00+00:00"
        )
        session.add(uncontested_metric)

    contract = mark_raw_sweep_complete(contract, raw_game_state_id_end=1, raw_rows_written=1, raw_players_written=1, failed_combinations=0)
    repo.update_matrix_sweep_simulation(sim_id, parameters=contract, end_timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc))

    # Test uncontested scenario (all players all-in)
    uncontested = provider.get_matrix_payload(
        position="BB",
        metric="WIN_LOSE_PROBABILITY",
        position_actions={"UTG": "ALL_IN", "BTN": "ALL_IN", "SB": "ALL_IN", "BB": "ALL_IN"},
    )

    # Test different contested scenario (some players folded)
    contested = provider.get_matrix_payload(
        position="SB",
        metric="WIN_LOSE_PROBABILITY",
        position_actions={"UTG": "FOLD", "BTN": "FOLD", "SB": "FOLD", "BB": "FOLD"},
    )

    # Verify contexts are different
    assert uncontested["context"]["position"] == "BB"
    assert contested["context"]["position"] == "SB"
    assert uncontested["context"]["position_actions"] != contested["context"]["position_actions"]
    
    # Verify uncontested scenario has data (from database)
    aa_uncontested = next((cell for cell in uncontested["cells"] if cell.get("hand_key") == "AA"), None)
    assert aa_uncontested is not None, "AA should be present in uncontested payload"
    assert aa_uncontested["value"] == 0.95, "AA should have high win probability in uncontested scenario"
    
    # Verify contested scenario doesn't incorrectly reuse uncontested data
    # Since no data exists for contested scenario, it should return MISSING status or empty cells
    # The key test is that it doesn't return the uncontested data
    aa_contested = next((cell for cell in contested["cells"] if cell.get("hand_key") == "AA"), None)
    if aa_contested is not None:
        # If AA cell exists in contested, it should NOT have the uncontested value
        assert aa_contested["value"] != 0.95, "Contested scenario should not reuse uncontested data"
