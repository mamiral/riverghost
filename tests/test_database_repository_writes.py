"""
Test suite for DatabaseRepository write operations (T052).

Validates that write methods (create_simulation, create_hand_matrix, upsert_matrix_cell)
correctly persist data to the database.

PHASE 5: P0 - CRITICAL
- Validates core database persistence layer
- Tests simulation and hand matrix lifecycle
"""

import json
import os
import pytest
from sqlalchemy import text

from hopilot.database import DatabaseConnection
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.simulation_repository import SimulationRepository
from hopilot.models import Simulation, HandMatrix, MatrixCell


class TestDatabaseRepositoryWrites:
    """Test suite for DatabaseRepository.write_* methods."""

    @pytest.fixture(scope="function")
    def test_db(self):
        """Create an in-memory SQLite database for write tests."""
        conn = DatabaseConnection("sqlite:///:memory:")
        conn.create_tables()
        yield conn
        conn.close()

    def test_create_simulation_basic(self, test_db):
        """
        T052.1: Verify simulation record creation and ID return.
        
        Given: A DatabaseRepository with database connection
        When: create_simulation() called with valid parameters
        Then: Simulation record created with returned ID, parameters stored
        """
        # Arrange
        repo = SimulationRepository(test_db)
        test_parameters = '{"num_simulations": 1000, "matrix_size": 13, "game_type": "NLHE"}'
        
        # Act
        simulation_id = repo.create_simulation(test_parameters)
        
        # Assert - ID returned and is valid
        assert simulation_id is not None
        assert isinstance(simulation_id, int)
        assert simulation_id > 0
        
        # Assert - Simulation actually created in database
        # db query uses test_db directly
        with test_db.session_scope() as session:
            sim = session.query(Simulation).filter_by(id=simulation_id).first()
            assert sim is not None
            assert sim.parameters == json.loads(test_parameters)

    def test_create_simulation_parameters_persisted(self, test_db):
        """
        T052.2: Confirm parameters stored correctly in database.
        
        Given: A DatabaseRepository with database connection
        When: create_simulation() called with JSON parameters
        Then: Parameters stored as JSON in database, not stringified
        """
        # Arrange
        repo = SimulationRepository(test_db)
        test_parameters = '{"num_simulations": 5000, "matrix_size": 13, "game_type": "PLO"}'
        
        # Act
        simulation_id = repo.create_simulation(test_parameters)
        
        # Assert - Parameters persisted correctly
        # db query uses test_db directly
        with test_db.session_scope() as session:
            sim = session.query(Simulation).filter_by(id=simulation_id).first()
            assert sim.parameters == json.loads(test_parameters)
            assert sim.parameters['num_simulations'] == 5000

    def test_create_player_persists_hand_call_and_final_strength(self, test_db):
        """Verify GameStateRepository.create_player stores hand metadata."""
        repository = GameStateRepository(test_db)

        game_state_id = repository.create_game_state(
            {
                "pot_size": 100.0,
                "board_cards_str": "As,Kd,5c,??,??",
                "outcome": "hero_win",
            }
        )

        player_id = repository.create_player(
            {
                "game_state_id": game_state_id,
                "position": "hero",
                "hole_cards": "AsKh",
                "stack_size": 100.0,
                "is_hero": True,
                "hand_class": "pair",
                "final_strength": 100,
            }
        )

        with test_db.session_scope() as session:
            row = session.execute(text(
                "SELECT hand_class, final_strength FROM players WHERE id = :id"
            ), {"id": player_id}).fetchone()

        assert row is not None
        assert row[0] == "PAIR"
        assert row[1] == 100

    def test_create_hand_matrix_linked_to_simulation(self, test_db):
        """
        T052.3: Verify foreign key relationship to simulation.
        
        Given: A Simulation already created
        When: create_hand_matrix() called with that simulation_id
        Then: HandMatrix record created with correct simulation_id
        """
        # Arrange
        repo = SimulationRepository(test_db)
        sim_params = '{"num_simulations": 1000, "matrix_size": 13, "game_type": "NLHE"}'
        simulation_id = repo.create_simulation(sim_params)
        
        # Act
        matrix_id = repo.create_hand_matrix(simulation_id, matrix_size="13x13")
        
        # Assert - Matrix linked correctly
        # db query uses test_db directly
        with test_db.session_scope() as session:
            matrix = session.query(HandMatrix).filter_by(id=matrix_id).first()
            assert matrix is not None
            assert matrix.simulation_id == simulation_id
            assert matrix.matrix_size == "13x13"

    def test_create_hand_matrix_returns_id(self, test_db):
        """
        T052.4: Confirm matrix ID returned after creation.
        
        Given: A Simulation already created
        When: create_hand_matrix() called
        Then: Valid matrix ID returned and usable
        """
        # Arrange
        repo = SimulationRepository(test_db)
        sim_params = '{"num_simulations": 1000, "matrix_size": 13, "game_type": "NLHE"}'
        simulation_id = repo.create_simulation(sim_params)
        
        # Act
        matrix_id = repo.create_hand_matrix(simulation_id, matrix_size="13x13")
        
        # Assert - ID is valid
        assert matrix_id is not None
        assert isinstance(matrix_id, int)
        assert matrix_id > 0
        
        # Assert - Can retrieve with ID
        # db query uses test_db directly
        with test_db.session_scope() as session:
            matrix = session.query(HandMatrix).filter_by(id=matrix_id).first()
            assert matrix is not None

    def test_upsert_matrix_cell_insert_new(self, test_db):
        """
        T052.5: Insert new cell with hand combination.
        
        Given: A HandMatrix already created
        When: upsert_matrix_cell() called with new row/col
        Then: MatrixCell created with hand combination
        """
        # Arrange
        repo = SimulationRepository(test_db)
        sim_params = '{"num_simulations": 1000, "matrix_size": 13, "game_type": "NLHE"}'
        simulation_id = repo.create_simulation(sim_params)
        matrix_id = repo.create_hand_matrix(simulation_id)
        
        # Act
        repo.upsert_matrix_cell(
            matrix_id=matrix_id,
            row_idx=0,
            col_idx=0,
            hand_key="AcAd vs KcKd",
            metrics={"equity": 0.75, "win_probability": 0.8},
            status="AVAILABLE"
        )
        
        # Assert - Cell created with hand combination
        # db query uses test_db directly
        with test_db.session_scope() as session:
            cell = session.query(MatrixCell).filter(
                MatrixCell.matrix_id == matrix_id,
                MatrixCell.row_index == 0,
                MatrixCell.col_index == 0
            ).first()
            assert cell is not None
            assert cell.hand_combination == "AcAd vs KcKd"

    def test_upsert_matrix_cell_update_existing(self, test_db):
        """
        T052.6: Update existing cell preserves data, updates hand combination.
        
        Given: A MatrixCell already created
        When: upsert_matrix_cell() called with same row/col (update)
        Then: Cell updated with new hand combination
        """
        # Arrange
        repo = SimulationRepository(test_db)
        sim_params = '{"num_simulations": 1000, "matrix_size": 13, "game_type": "NLHE"}'
        simulation_id = repo.create_simulation(sim_params)
        matrix_id = repo.create_hand_matrix(simulation_id)
        
        # Insert first version
        repo.upsert_matrix_cell(
            matrix_id=matrix_id, row_idx=1, col_idx=1, hand_key="QcQd vs JcJd",
            metrics={"equity": 0.6, "win_probability": 0.7}, status="AVAILABLE"
        )
        
        # Get original ID
        # db query uses test_db directly
        with test_db.session_scope() as session:
            cell_v1 = session.query(MatrixCell).filter(
                MatrixCell.matrix_id == matrix_id,
                MatrixCell.row_index == 1,
                MatrixCell.col_index == 1
            ).first()
            cell_id_v1 = cell_v1.id
        
        # Act - Update same cell
        repo.upsert_matrix_cell(
            matrix_id=matrix_id, row_idx=1, col_idx=1, hand_key="QcQd vs JcJd (updated)",
            metrics={"equity": 0.65, "win_probability": 0.75}, status="AVAILABLE"
        )
        
        # Assert - Same cell updated
        with test_db.session_scope() as session:
            cell_v2 = session.query(MatrixCell).filter(
                MatrixCell.matrix_id == matrix_id,
                MatrixCell.row_index == 1,
                MatrixCell.col_index == 1
            ).first()
            assert cell_v2.id == cell_id_v1  # Same cell
            assert cell_v2.hand_combination == "QcQd vs JcJd (updated)"

    def test_upsert_matrix_cell_all_metrics_stored(self, test_db):
        """
        T052.7: Validate multiple cells stored correctly.
        
        Given: A HandMatrix created
        When: upsert_matrix_cell() called multiple times
        Then: All cells persisted with correct hand combinations
        """
        # Arrange
        repo = SimulationRepository(test_db)
        sim_params = '{"num_simulations": 1000, "matrix_size": 13, "game_type": "NLHE"}'
        simulation_id = repo.create_simulation(sim_params)
        matrix_id = repo.create_hand_matrix(simulation_id)
        
        # Test with different hand combinations
        test_cases = [
            {"row": 0, "col": 0, "hand": "AcAd vs KcKd"},
            {"row": 0, "col": 1, "hand": "AcAd vs QcQd"},
            {"row": 1, "col": 0, "hand": "KcKd vs AcAd"},
        ]
        
        for i, test_case in enumerate(test_cases):
            # Act
            repo.upsert_matrix_cell(
                matrix_id=matrix_id,
                row_idx=test_case["row"],
                col_idx=test_case["col"],
                hand_key=test_case["hand"],
                metrics={"equity": 0.5 + i * 0.1, "win_probability": 0.6 + i * 0.1},
                status="AVAILABLE"
            )
        
        # Assert - All cells stored correctly
        # db query uses test_db directly
        with test_db.session_scope() as session:
            for test_case in test_cases:
                cell = session.query(MatrixCell).filter(
                    MatrixCell.matrix_id == matrix_id,
                    MatrixCell.row_index == test_case["row"],
                    MatrixCell.col_index == test_case["col"]
                ).first()
                assert cell is not None
                assert cell.hand_combination == test_case["hand"]

    def test_game_state_players_bets_jackpots_in_memory(self, test_db):
        """Verify GameState, Player, Bet, and Jackpot writes on an in-memory database."""
        repository = GameStateRepository(test_db)

        game_state_id = repository.create_game_state(
            {
                "pot_size": 150.0,
                "board_cards_str": "As,Kd,5c,??,??",
                "outcome": "hero_win",
                "players": [
                    {
                        "position": "hero",
                        "hole_cards": "AsKh",
                        "stack_size": 200.0,
                        "is_hero": True,
                    },
                    {
                        "position": "villain",
                        "hole_cards": "KdQh",
                        "stack_size": 200.0,
                        "is_hero": False,
                    },
                ],
            }
        )

        state = repository.get_game_state(game_state_id)
        assert state is not None
        assert state["pot_size"] == 150.0
        assert state["board_cards_str"] == "As,Kd,5c,??,??"
        assert state["outcome"] == "hero_win"
        assert len(state["players"]) == 2

        hero_player = next(p for p in state["players"] if p["position"] == "hero")
        villain_player = next(p for p in state["players"] if p["position"] == "villain")

        assert hero_player["hole_cards"] == "AsKh"
        assert hero_player["stack_size"] == 200.0
        assert hero_player["is_hero"] is True

        assert villain_player["hole_cards"] == "KdQh"
        assert villain_player["stack_size"] == 200.0
        assert villain_player["is_hero"] is False

        hero_bet_id = repository.create_bet(
            {
                "game_state_id": game_state_id,
                "player_id": hero_player["id"],
                "amount": 150.0,
                "action_type": "raise",
                "round": "preflop",
            }
        )
        assert hero_bet_id > 0

        jackpot_id = repository.create_jackpot(
            {
                "game_state_id": game_state_id,
                "player_id": hero_player["id"],
                "jackpot_type": "royal_flush",
                "payout_amount": 500.0,
                "qualifying_cards": ["As", "Kh"],
            }
        )
        assert jackpot_id > 0

        state = repository.get_game_state(game_state_id)
        assert len(state["bets"]) == 1
        assert len(state["jackpots"]) == 1

        bet = state["bets"][0]
        assert bet["player_id"] == hero_player["id"]
        assert bet["amount"] == 150.0
        assert bet["action_type"] == "raise"
        assert bet["round"] == "preflop"

        jackpot = state["jackpots"][0]
        assert jackpot["jackpot_type"] == "royal_flush"
        assert jackpot["payout_amount"] == 500.0
        assert jackpot["qualifying_cards"] == ["As", "Kh"]

        with test_db.session_scope() as session:
            game_state_count = session.execute(text("SELECT COUNT(*) FROM game_states")).scalar()
            player_count = session.execute(text("SELECT COUNT(*) FROM players")).scalar()
            bet_count = session.execute(text("SELECT COUNT(*) FROM bets")).scalar()
            jackpot_count = session.execute(text("SELECT COUNT(*) FROM jackpots")).scalar()

        assert game_state_count == 1
        assert player_count == 2
        assert bet_count == 1
        assert jackpot_count == 1
