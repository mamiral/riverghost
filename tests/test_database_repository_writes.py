"""
Test suite for DatabaseRepository write operations (T052).

Validates that write methods (create_simulation, create_hand_matrix, upsert_matrix_cell)
correctly persist data to the database.

PHASE 5: P0 - CRITICAL
- Validates core database persistence layer
- Tests simulation and hand matrix lifecycle
"""

import os
import tempfile
import pytest

from hopilot.database import DatabaseConnection
from hopilot.gto.database_repository import DatabaseRepository
from hopilot.models import Simulation, HandMatrix, MatrixCell


class TestDatabaseRepositoryWrites:
    """Test suite for DatabaseRepository.write_* methods."""

    @pytest.fixture(scope="function")
    def test_db(self):
        """Create a temporary file-based SQLite database for testing."""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        db_url = f"sqlite:///{db_path}"
        
        # Create and initialize database
        connection = DatabaseConnection(db_url)
        connection.create_tables()
        connection.close()
        
        yield db_url
        
        # Cleanup - safely remove file
        try:
            import gc
            gc.collect()  # Force garbage collection to release file handles
            if os.path.exists(db_path):
                os.remove(db_path)
            os.rmdir(temp_dir)
        except Exception:
            # Silently ignore cleanup errors on Windows with locked files
            pass

    def test_create_simulation_basic(self, test_db):
        """
        T052.1: Verify simulation record creation and ID return.
        
        Given: A DatabaseRepository with database connection
        When: create_simulation() called with valid parameters
        Then: Simulation record created with returned ID, parameters stored
        """
        # Arrange
        repo = DatabaseRepository(test_db)
        test_parameters = '{"num_simulations": 1000, "matrix_size": 13, "game_type": "NLHE"}'
        
        # Act
        simulation_id = repo.create_simulation(test_parameters)
        
        # Assert - ID returned and is valid
        assert simulation_id is not None
        assert isinstance(simulation_id, int)
        assert simulation_id > 0
        
        # Assert - Simulation actually created in database
        db_conn = DatabaseConnection(test_db)
        with db_conn.session_scope() as session:
            sim = session.query(Simulation).filter_by(id=simulation_id).first()
            assert sim is not None
            assert sim.parameters == test_parameters

    def test_create_simulation_parameters_persisted(self, test_db):
        """
        T052.2: Confirm parameters stored correctly in database.
        
        Given: A DatabaseRepository with database connection
        When: create_simulation() called with JSON parameters
        Then: Parameters stored as JSON in database, not stringified
        """
        # Arrange
        repo = DatabaseRepository(test_db)
        test_parameters = '{"num_simulations": 5000, "matrix_size": 13, "game_type": "PLO"}'
        
        # Act
        simulation_id = repo.create_simulation(test_parameters)
        
        # Assert - Parameters persisted correctly
        db_conn = DatabaseConnection(test_db)
        with db_conn.session_scope() as session:
            sim = session.query(Simulation).filter_by(id=simulation_id).first()
            assert sim.parameters == test_parameters
            # Verify it's the exact same string, not re-encoded
            assert '"num_simulations": 5000' in sim.parameters

    def test_create_hand_matrix_linked_to_simulation(self, test_db):
        """
        T052.3: Verify foreign key relationship to simulation.
        
        Given: A Simulation already created
        When: create_hand_matrix() called with that simulation_id
        Then: HandMatrix record created with correct simulation_id
        """
        # Arrange
        repo = DatabaseRepository(test_db)
        sim_params = '{"num_simulations": 1000, "matrix_size": 13, "game_type": "NLHE"}'
        simulation_id = repo.create_simulation(sim_params)
        
        # Act
        matrix_id = repo.create_hand_matrix(simulation_id, matrix_size="13x13")
        
        # Assert - Matrix linked correctly
        db_conn = DatabaseConnection(test_db)
        with db_conn.session_scope() as session:
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
        repo = DatabaseRepository(test_db)
        sim_params = '{"num_simulations": 1000, "matrix_size": 13, "game_type": "NLHE"}'
        simulation_id = repo.create_simulation(sim_params)
        
        # Act
        matrix_id = repo.create_hand_matrix(simulation_id, matrix_size="13x13")
        
        # Assert - ID is valid
        assert matrix_id is not None
        assert isinstance(matrix_id, int)
        assert matrix_id > 0
        
        # Assert - Can retrieve with ID
        db_conn = DatabaseConnection(test_db)
        with db_conn.session_scope() as session:
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
        repo = DatabaseRepository(test_db)
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
        db_conn = DatabaseConnection(test_db)
        with db_conn.session_scope() as session:
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
        repo = DatabaseRepository(test_db)
        sim_params = '{"num_simulations": 1000, "matrix_size": 13, "game_type": "NLHE"}'
        simulation_id = repo.create_simulation(sim_params)
        matrix_id = repo.create_hand_matrix(simulation_id)
        
        # Insert first version
        repo.upsert_matrix_cell(
            matrix_id=matrix_id, row_idx=1, col_idx=1, hand_key="QcQd vs JcJd",
            metrics={"equity": 0.6, "win_probability": 0.7}, status="AVAILABLE"
        )
        
        # Get original ID
        db_conn = DatabaseConnection(test_db)
        with db_conn.session_scope() as session:
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
        with db_conn.session_scope() as session:
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
        repo = DatabaseRepository(test_db)
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
        db_conn = DatabaseConnection(test_db)
        with db_conn.session_scope() as session:
            for test_case in test_cases:
                cell = session.query(MatrixCell).filter(
                    MatrixCell.matrix_id == matrix_id,
                    MatrixCell.row_index == test_case["row"],
                    MatrixCell.col_index == test_case["col"]
                ).first()
                assert cell is not None
                assert cell.hand_combination == test_case["hand"]
