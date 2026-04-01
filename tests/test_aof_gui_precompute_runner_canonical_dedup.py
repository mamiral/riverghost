import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider


def test_canonical_dedup_reuses_persisted_cells_with_request_local_context(tmp_path):
    """Test that canonical deduplication reuses persisted cells for same scenario."""
    db_path = str(tmp_path / "aof_gui_canonical.sqlite3")
    database_url = f"sqlite:///{db_path}"
    provider = BrowserDatabaseProvider(database_url=database_url)
    
    # Populate database with test data for canonical scenario
    repo = provider.database_repository
    session = repo.session
    
    # Create simulation and matrix
    sim_id = repo.create_simulation('{"num_simulations": 1000, "game_type": "NLHE"}')
    matrix_id = repo.create_hand_matrix(sim_id)
    
    # Create board
    board_id = repo.create_board_card({
        'flop1': 'As', 'flop2': 'Ks', 'flop3': 'Qs',
        'turn': 'Js', 'river': 'Ts'
    })
    
    # Insert test data for AA hand
    from hopilot.models import MatrixCell, AggregatedMetric
    aa_cell = MatrixCell(
        matrix_id=matrix_id,
        row_idx=0,  # AA is typically at (0,0)
        col_idx=0,
        hand_combination="AA",
        board_id=board_id
    )
    session.add(aa_cell)
    session.flush()  # Get the cell ID
    
    # Add metrics for EV
    ev_metric = AggregatedMetric(
        cell_id=aa_cell.id,
        metric_type="EV",
        value=0.75,
        sample_count=1000
    )
    session.add(ev_metric)
    
    # Add metrics for WIN_LOSE_PROBABILITY  
    wlp_metric = AggregatedMetric(
        cell_id=aa_cell.id,
        metric_type="WIN_LOSE_PROBABILITY",
        value=0.82,
        sample_count=1000
    )
    session.add(wlp_metric)
    session.commit()

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
    session = repo.session
    
    # Create simulation and matrix for uncontested scenario
    sim_id = repo.create_simulation('{"num_simulations": 1000, "game_type": "NLHE"}')
    matrix_id = repo.create_hand_matrix(sim_id)
    
    # Create board
    board_id = repo.create_board_card({
        'flop1': 'As', 'flop2': 'Ks', 'flop3': 'Qs',
        'turn': 'Js', 'river': 'Ts'
    })
    
    # Insert test data for uncontested scenario (all players all-in)
    from hopilot.models import MatrixCell, AggregatedMetric
    aa_cell = MatrixCell(
        matrix_id=matrix_id,
        row_idx=0,
        col_idx=0,
        hand_combination="AA",
        board_id=board_id
    )
    session.add(aa_cell)
    session.flush()
    
    # Add metrics for uncontested WIN_LOSE_PROBABILITY
    uncontested_metric = AggregatedMetric(
        cell_id=aa_cell.id,
        metric_type="WIN_LOSE_PROBABILITY",
        value=0.95,  # High win probability in uncontested scenario
        sample_count=1000
    )
    session.add(uncontested_metric)
    session.commit()

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
