"""
Test suite for DatabaseRepository CRUD operations (TEST-001).

Validates that all CRUD methods (create, read, update, delete) for GameStates,
Players, Bets, BoardCards, and Jackpots work correctly with proper validation.

PHASE 1: P1 - CRITICAL
- Validates core database CRUD layer
- Tests data integrity constraints
- Comprehensive coverage of all entity operations
"""

import os
import tempfile
import pytest
from typing import Dict, Any

from hopilot.database import DatabaseConnection
from hopilot.gto.database_repository import DatabaseRepository, DataIntegrityError
from hopilot.models import GameState, Player, Bet, BoardCard, Jackpot, MatrixCell


class TestDatabaseRepositoryCRUD:
    """Test suite for DatabaseRepository CRUD operations."""

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

    @pytest.fixture
    def repo(self, test_db):
        """Create a DatabaseRepository instance."""
        return DatabaseRepository(test_db)

    # ============================================================================
    # HELPER METHODS
    # ============================================================================

    def _create_test_matrix_cell(self, repo: DatabaseRepository) -> int:
        """Create a test matrix cell for game state dependencies."""
        # Create a minimal simulation and hand matrix first
        sim_params = '{"num_simulations": 1000, "matrix_size": "13x13", "game_type": "NLHE"}'
        sim_id = repo.create_simulation(sim_params)
        matrix_id = repo.create_hand_matrix(sim_id)

        # Create matrix cell directly (avoiding upsert_matrix_cell issues)
        with repo.connection.session_scope() as session:
            from hopilot.models import MatrixCell
            cell = MatrixCell(
                matrix_id=matrix_id,
                row_index=0,
                col_index=0,
                hand_combination="AA vs Random"
            )
            session.add(cell)
            session.flush()
            return cell.id

    def _create_test_board_card(self, repo: DatabaseRepository) -> int:
        """Create a test board card for game state dependencies."""
        return repo.create_board_card({
            'flop1': 'As', 'flop2': 'Ks', 'flop3': 'Qs',
            'turn': 'Js', 'river': 'Ts'
        })

    def _create_test_game_state(self, repo: DatabaseRepository) -> int:
        """Create a test game state for dependent entity tests."""
        cell_id = self._create_test_matrix_cell(repo)
        board_id = self._create_test_board_card(repo)

        return repo.create_game_state({
            'cell_id': cell_id,
            'pot_size': 1000,
            'board_cards_id': board_id
        })

    def _create_test_player(self, repo: DatabaseRepository) -> int:
        """Create a test player for dependent entity tests."""
        game_state_id = self._create_test_game_state(repo)

        return repo.create_player({
            'game_state_id': game_state_id,
            'position': 'Hero',
            'hole_cards': 'AcAd',
            'stack_size': 5000
        })

    # ============================================================================
    # GAMESTATES CRUD TESTS
    # ============================================================================

    def test_create_game_state_success(self, repo):
        """Test successful game state creation."""
        cell_id = self._create_test_matrix_cell(repo)
        board_id = self._create_test_board_card(repo)

        game_state_data = {
            'cell_id': cell_id,
            'pot_size': 1500,
            'board_cards_id': board_id,
            'round': 'preflop'  # Must be preflop for this model
        }

        game_state_id = repo.create_game_state(game_state_data)

        assert game_state_id is not None
        assert isinstance(game_state_id, int)
        assert game_state_id > 0

        # Verify in database
        with repo.connection.session_scope() as session:
            gs = session.query(GameState).filter(GameState.id == game_state_id).first()
            assert gs is not None
            assert gs.cell_id == cell_id
            assert gs.pot_size == 1500
            assert gs.board_cards_id == board_id
            assert gs.round == 'preflop'

    def test_create_game_state_validation_errors(self, repo):
        """Test game state creation with validation errors."""
        # Missing required fields
        with pytest.raises(DataIntegrityError, match="Missing required field"):
            repo.create_game_state({'pot_size': 1000})

        # Invalid foreign key
        with pytest.raises(DataIntegrityError, match="MatrixCell with ID 999 does not exist"):
            repo.create_game_state({
                'cell_id': 999,
                'pot_size': 1000,
                'board_cards_id': 1
            })

        # Negative pot size
        cell_id = self._create_test_matrix_cell(repo)
        board_id = self._create_test_board_card(repo)
        with pytest.raises(DataIntegrityError, match="Pot size cannot be negative"):
            repo.create_game_state({
                'cell_id': cell_id,
                'pot_size': -100,
                'board_cards_id': board_id
            })

        # Invalid round
        with pytest.raises(DataIntegrityError, match="Round must be"):
            repo.create_game_state({
                'cell_id': cell_id,
                'pot_size': 1000,
                'board_cards_id': board_id,
                'round': 'invalid'
            })

    def test_get_game_state_success(self, repo):
        """Test successful game state retrieval."""
        game_state_id = self._create_test_game_state(repo)

        result = repo.get_game_state(game_state_id)

        assert result is not None
        assert result['id'] == game_state_id
        assert 'pot_size' in result
        assert 'board_cards' in result

    def test_get_game_state_not_found(self, repo):
        """Test game state retrieval for non-existent ID."""
        result = repo.get_game_state(999)
        assert result is None

    def test_update_game_state_success(self, repo):
        """Test successful game state update."""
        game_state_id = self._create_test_game_state(repo)

        updates = {'pot_size': 2000, 'round': 'turn', 'outcome': 'hero_win'}
        success = repo.update_game_state(game_state_id, updates)

        assert success is True

        # Verify in database
        with repo.connection.session_scope() as session:
            gs = session.query(GameState).filter(GameState.id == game_state_id).first()
            assert gs.pot_size == 2000
            assert gs.round == 'turn'
            assert gs.outcome == 'hero_win'

    def test_update_game_state_validation_errors(self, repo):
        """Test game state update with validation errors."""
        game_state_id = self._create_test_game_state(repo)

        # Invalid pot size
        with pytest.raises(DataIntegrityError, match="Pot size cannot be negative"):
            repo.update_game_state(game_state_id, {'pot_size': -500})

        # Invalid round
        with pytest.raises(DataIntegrityError, match="Round must be"):
            repo.update_game_state(game_state_id, {'round': 'invalid'})

    def test_update_game_state_not_found(self, repo):
        """Test game state update for non-existent ID."""
        with pytest.raises(DataIntegrityError, match="GameState with ID 999 does not exist"):
            repo.update_game_state(999, {'pot_size': 2000})

    def test_delete_game_state_success(self, repo):
        """Test successful game state deletion."""
        game_state_id = self._create_test_game_state(repo)

        success = repo.delete_game_state(game_state_id)
        assert success is True

        # Verify deleted
        with repo.connection.session_scope() as session:
            gs = session.query(GameState).filter(GameState.id == game_state_id).first()
            assert gs is None

    def test_delete_game_state_not_found(self, repo):
        """Test game state deletion for non-existent ID."""
        with pytest.raises(DataIntegrityError, match="GameState with ID 999 does not exist"):
            repo.delete_game_state(999)

    # ============================================================================
    # PLAYERS CRUD TESTS
    # ============================================================================

    def test_create_player_success(self, repo):
        """Test successful player creation."""
        game_state_id = self._create_test_game_state(repo)

        player_data = {
            'game_state_id': game_state_id,
            'position': 'UTG',
            'hole_cards': 'KhQh',
            'stack_size': 2500,
            'is_hero': True
        }

        player_id = repo.create_player(player_data)

        assert player_id is not None
        assert isinstance(player_id, int)
        assert player_id > 0

        # Verify in database
        with repo.connection.session_scope() as session:
            player = session.query(Player).filter(Player.id == player_id).first()
            assert player is not None
            assert player.game_state_id == game_state_id
            assert player.position == 'UTG'
            assert player.hole_cards == 'KhQh'
            assert player.stack_size == 2500
            assert player.is_hero is True

    def test_create_player_validation_errors(self, repo):
        """Test player creation with validation errors."""
        # Missing required fields
        with pytest.raises(DataIntegrityError, match="Missing required field"):
            repo.create_player({'position': 'UTG'})

        # Invalid game_state_id
        with pytest.raises(DataIntegrityError, match="GameState with ID 999 does not exist"):
            repo.create_player({
                'game_state_id': 999,
                'position': 'UTG',
                'hole_cards': 'AsKs',
                'stack_size': 1000
            })

        # Empty position
        game_state_id = self._create_test_game_state(repo)
        with pytest.raises(DataIntegrityError, match="Position cannot be empty"):
            repo.create_player({
                'game_state_id': game_state_id,
                'position': '',
                'hole_cards': 'AsKs',
                'stack_size': 1000
            })

        # Invalid hole cards format
        with pytest.raises(DataIntegrityError, match="Hole cards must be 4 characters"):
            repo.create_player({
                'game_state_id': game_state_id,
                'position': 'UTG',
                'hole_cards': 'AsK',  # Too short
                'stack_size': 1000
            })

        # Negative stack size
        with pytest.raises(DataIntegrityError, match="Stack size cannot be negative"):
            repo.create_player({
                'game_state_id': game_state_id,
                'position': 'UTG',
                'hole_cards': 'AsKs',
                'stack_size': -100
            })

    def test_update_player_success(self, repo):
        """Test successful player update."""
        player_id = self._create_test_player(repo)

        updates = {'position': 'MP', 'stack_size': 3000, 'is_hero': False}
        success = repo.update_player(player_id, updates)

        assert success is True

        # Verify in database
        with repo.connection.session_scope() as session:
            player = session.query(Player).filter(Player.id == player_id).first()
            assert player.position == 'MP'
            assert player.stack_size == 3000
            assert player.is_hero is False

    def test_update_player_validation_errors(self, repo):
        """Test player update with validation errors."""
        player_id = self._create_test_player(repo)

        # Empty position
        with pytest.raises(DataIntegrityError, match="Position cannot be empty"):
            repo.update_player(player_id, {'position': ''})

        # Invalid hole cards
        with pytest.raises(DataIntegrityError, match="Hole cards must be 4 characters"):
            repo.update_player(player_id, {'hole_cards': 'As'})

        # Negative stack size
        with pytest.raises(DataIntegrityError, match="Stack size cannot be negative"):
            repo.update_player(player_id, {'stack_size': -500})

    def test_update_player_not_found(self, repo):
        """Test player update for non-existent ID."""
        with pytest.raises(DataIntegrityError, match="Player with ID 999 does not exist"):
            repo.update_player(999, {'position': 'MP'})

    def test_delete_player_success(self, repo):
        """Test successful player deletion."""
        player_id = self._create_test_player(repo)

        success = repo.delete_player(player_id)
        assert success is True

        # Verify deleted
        with repo.connection.session_scope() as session:
            player = session.query(Player).filter(Player.id == player_id).first()
            assert player is None

    def test_delete_player_not_found(self, repo):
        """Test player deletion for non-existent ID."""
        with pytest.raises(DataIntegrityError, match="Player with ID 999 does not exist"):
            repo.delete_player(999)

    # ============================================================================
    # BETS CRUD TESTS
    # ============================================================================

    def test_create_bet_success(self, repo):
        """Test successful bet creation."""
        game_state_id = self._create_test_game_state(repo)
        player_id = self._create_test_player(repo)

        bet_data = {
            'game_state_id': game_state_id,
            'player_id': player_id,
            'amount': 500,
            'action_type': 'raise',
            'round': 'flop'
        }

        bet_id = repo.create_bet(bet_data)

        assert bet_id is not None
        assert isinstance(bet_id, int)
        assert bet_id > 0

        # Verify in database
        with repo.connection.session_scope() as session:
            bet = session.query(Bet).filter(Bet.id == bet_id).first()
            assert bet is not None
            assert bet.game_state_id == game_state_id
            assert bet.player_id == player_id
            assert bet.amount == 500
            assert bet.action_type == 'raise'
            assert bet.round == 'flop'

    def test_create_bet_validation_errors(self, repo):
        """Test bet creation with validation errors."""
        # Missing required fields
        with pytest.raises(DataIntegrityError, match="Missing required field"):
            repo.create_bet({'amount': 100})

        # Invalid game_state_id
        with pytest.raises(DataIntegrityError, match="GameState with ID 999 does not exist"):
            repo.create_bet({
                'game_state_id': 999,
                'player_id': 1,
                'amount': 100
            })

        # Invalid player_id
        game_state_id = self._create_test_game_state(repo)
        with pytest.raises(DataIntegrityError, match="Player with ID 999 does not exist"):
            repo.create_bet({
                'game_state_id': game_state_id,
                'player_id': 999,
                'amount': 100
            })

        # Zero amount
        player_id = self._create_test_player(repo)
        with pytest.raises(DataIntegrityError, match="Bet amount must be positive"):
            repo.create_bet({
                'game_state_id': game_state_id,
                'player_id': player_id,
                'amount': 0
            })

        # Invalid action type
        with pytest.raises(DataIntegrityError, match="Action type must be"):
            repo.create_bet({
                'game_state_id': game_state_id,
                'player_id': player_id,
                'amount': 100,
                'action_type': 'invalid'
            })

        # Invalid round
        with pytest.raises(DataIntegrityError, match="Round must be"):
            repo.create_bet({
                'game_state_id': game_state_id,
                'player_id': player_id,
                'amount': 100,
                'round': 'invalid'
            })

    def test_update_bet_success(self, repo):
        """Test successful bet update."""
        # Create a bet first
        game_state_id = self._create_test_game_state(repo)
        player_id = self._create_test_player(repo)

        bet_data = {
            'game_state_id': game_state_id,
            'player_id': player_id,
            'amount': 200,
            'action_type': 'call'
        }
        bet_id = repo.create_bet(bet_data)

        # Update it
        updates = {'amount': 400, 'action_type': 'raise', 'round': 'turn'}
        success = repo.update_bet(bet_id, updates)

        assert success is True

        # Verify in database
        with repo.connection.session_scope() as session:
            bet = session.query(Bet).filter(Bet.id == bet_id).first()
            assert bet.amount == 400
            assert bet.action_type == 'raise'
            assert bet.round == 'turn'

    def test_update_bet_validation_errors(self, repo):
        """Test bet update with validation errors."""
        # Create a bet first
        game_state_id = self._create_test_game_state(repo)
        player_id = self._create_test_player(repo)
        bet_id = repo.create_bet({
            'game_state_id': game_state_id,
            'player_id': player_id,
            'amount': 100
        })

        # Invalid amount
        with pytest.raises(DataIntegrityError, match="Bet amount must be positive"):
            repo.update_bet(bet_id, {'amount': 0})

        # Invalid action type
        with pytest.raises(DataIntegrityError, match="Action type must be"):
            repo.update_bet(bet_id, {'action_type': 'invalid'})

        # Invalid round
        with pytest.raises(DataIntegrityError, match="Round must be"):
            repo.update_bet(bet_id, {'round': 'invalid'})

    def test_update_bet_not_found(self, repo):
        """Test bet update for non-existent ID."""
        with pytest.raises(DataIntegrityError, match="Bet with ID 999 does not exist"):
            repo.update_bet(999, {'amount': 200})

    def test_delete_bet_success(self, repo):
        """Test successful bet deletion."""
        # Create a bet first
        game_state_id = self._create_test_game_state(repo)
        player_id = self._create_test_player(repo)
        bet_id = repo.create_bet({
            'game_state_id': game_state_id,
            'player_id': player_id,
            'amount': 100
        })

        success = repo.delete_bet(bet_id)
        assert success is True

        # Verify deleted
        with repo.connection.session_scope() as session:
            bet = session.query(Bet).filter(Bet.id == bet_id).first()
            assert bet is None

    def test_delete_bet_not_found(self, repo):
        """Test bet deletion for non-existent ID."""
        with pytest.raises(DataIntegrityError, match="Bet with ID 999 does not exist"):
            repo.delete_bet(999)

    # ============================================================================
    # BOARDCARDS CRUD TESTS
    # ============================================================================

    def test_create_board_card_success(self, repo):
        """Test successful board card creation."""
        board_card_data = {
            'flop1': 'Ah', 'flop2': 'Kd', 'flop3': 'Qc',
            'turn': 'Js', 'river': 'Tc'
        }

        board_card_id = repo.create_board_card(board_card_data)

        assert board_card_id is not None
        assert isinstance(board_card_id, int)
        assert board_card_id > 0

        # Verify in database
        with repo.connection.session_scope() as session:
            bc = session.query(BoardCard).filter(BoardCard.id == board_card_id).first()
            assert bc is not None
            assert bc.flop1 == 'Ah'
            assert bc.flop2 == 'Kd'
            assert bc.flop3 == 'Qc'
            assert bc.turn == 'Js'
            assert bc.river == 'Tc'

    def test_create_board_card_validation_errors(self, repo):
        """Test board card creation with validation errors."""
        # Missing required fields
        with pytest.raises(DataIntegrityError, match="Missing required field"):
            repo.create_board_card({'flop1': 'As'})

    def test_update_board_card_success(self, repo):
        """Test successful board card update."""
        board_card_id = self._create_test_board_card(repo)

        updates = {'flop1': 'Ac', 'turn': 'Jd'}
        success = repo.update_board_card(board_card_id, updates)

        assert success is True

        # Verify in database
        with repo.connection.session_scope() as session:
            bc = session.query(BoardCard).filter(BoardCard.id == board_card_id).first()
            assert bc.flop1 == 'Ac'
            assert bc.turn == 'Jd'

    def test_update_board_card_not_found(self, repo):
        """Test board card update for non-existent ID."""
        with pytest.raises(DataIntegrityError, match="BoardCard with ID 999 does not exist"):
            repo.update_board_card(999, {'flop1': 'As'})

    def test_delete_board_card_success(self, repo):
        """Test successful board card deletion."""
        board_card_id = self._create_test_board_card(repo)

        success = repo.delete_board_card(board_card_id)
        assert success is True

        # Verify deleted
        with repo.connection.session_scope() as session:
            bc = session.query(BoardCard).filter(BoardCard.id == board_card_id).first()
            assert bc is None

    def test_delete_board_card_not_found(self, repo):
        """Test board card deletion for non-existent ID."""
        with pytest.raises(DataIntegrityError, match="BoardCard with ID 999 does not exist"):
            repo.delete_board_card(999)

    # ============================================================================
    # JACKPOTS CRUD TESTS
    # ============================================================================

    def test_create_jackpot_success(self, repo):
        """Test successful jackpot creation."""
        game_state_id = self._create_test_game_state(repo)
        player_id = self._create_test_player(repo)

        jackpot_data = {
            'game_state_id': game_state_id,
            'player_id': player_id,
            'jackpot_type': 'royal_flush',
            'payout_amount': 25000,
            'qualifying_cards': ['As', 'Ks', 'Qs', 'Js', 'Ts']
        }

        jackpot_id = repo.create_jackpot(jackpot_data)

        assert jackpot_id is not None
        assert isinstance(jackpot_id, int)
        assert jackpot_id > 0

        # Verify in database
        with repo.connection.session_scope() as session:
            jackpot = session.query(Jackpot).filter(Jackpot.id == jackpot_id).first()
            assert jackpot is not None
            assert jackpot.game_state_id == game_state_id
            assert jackpot.player_id == player_id
            assert jackpot.jackpot_type == 'royal_flush'
            assert jackpot.payout_amount == 25000
            assert jackpot.qualifying_cards == ['As', 'Ks', 'Qs', 'Js', 'Ts']

    def test_create_jackpot_validation_errors(self, repo):
        """Test jackpot creation with validation errors."""
        # Missing required fields
        with pytest.raises(DataIntegrityError, match="Missing required field"):
            repo.create_jackpot({'jackpot_type': 'royal_flush'})

        # Invalid game_state_id
        with pytest.raises(DataIntegrityError, match="GameState with ID 999 does not exist"):
            repo.create_jackpot({
                'game_state_id': 999,
                'player_id': 1,
                'jackpot_type': 'royal_flush',
                'payout_amount': 1000,
                'qualifying_cards': ['As']
            })

        # Invalid player_id
        game_state_id = self._create_test_game_state(repo)
        with pytest.raises(DataIntegrityError, match="Player with ID 999 does not exist"):
            repo.create_jackpot({
                'game_state_id': game_state_id,
                'player_id': 999,
                'jackpot_type': 'royal_flush',
                'payout_amount': 1000,
                'qualifying_cards': ['As']
            })

        # Zero payout amount
        player_id = self._create_test_player(repo)
        with pytest.raises(DataIntegrityError, match="Payout amount must be positive"):
            repo.create_jackpot({
                'game_state_id': game_state_id,
                'player_id': player_id,
                'jackpot_type': 'royal_flush',
                'payout_amount': 0,
                'qualifying_cards': ['As']
            })

        # Empty qualifying cards
        with pytest.raises(DataIntegrityError, match="Qualifying cards must be a non-empty list"):
            repo.create_jackpot({
                'game_state_id': game_state_id,
                'player_id': player_id,
                'jackpot_type': 'royal_flush',
                'payout_amount': 1000,
                'qualifying_cards': []
            })

        # Empty jackpot type
        with pytest.raises(DataIntegrityError, match="Jackpot type cannot be empty"):
            repo.create_jackpot({
                'game_state_id': game_state_id,
                'player_id': player_id,
                'jackpot_type': '',
                'payout_amount': 1000,
                'qualifying_cards': ['As']
            })

    def test_update_jackpot_success(self, repo):
        """Test successful jackpot update."""
        # Create a jackpot first
        game_state_id = self._create_test_game_state(repo)
        player_id = self._create_test_player(repo)
        jackpot_id = repo.create_jackpot({
            'game_state_id': game_state_id,
            'player_id': player_id,
            'jackpot_type': 'straight_flush',
            'payout_amount': 15000,
            'qualifying_cards': ['As', 'Ks', 'Qs', 'Js', 'Ts']
        })

        # Update it
        updates = {'jackpot_type': 'royal_flush', 'payout_amount': 30000}
        success = repo.update_jackpot(jackpot_id, updates)

        assert success is True

        # Verify in database
        with repo.connection.session_scope() as session:
            jackpot = session.query(Jackpot).filter(Jackpot.id == jackpot_id).first()
            assert jackpot.jackpot_type == 'royal_flush'
            assert jackpot.payout_amount == 30000

    def test_update_jackpot_validation_errors(self, repo):
        """Test jackpot update with validation errors."""
        # Create a jackpot first
        game_state_id = self._create_test_game_state(repo)
        player_id = self._create_test_player(repo)
        jackpot_id = repo.create_jackpot({
            'game_state_id': game_state_id,
            'player_id': player_id,
            'jackpot_type': 'straight_flush',
            'payout_amount': 1000,
            'qualifying_cards': ['As']
        })

        # Invalid payout amount
        with pytest.raises(DataIntegrityError, match="Payout amount must be positive"):
            repo.update_jackpot(jackpot_id, {'payout_amount': -100})

        # Empty qualifying cards
        with pytest.raises(DataIntegrityError, match="Qualifying cards must be a non-empty list"):
            repo.update_jackpot(jackpot_id, {'qualifying_cards': []})

        # Empty jackpot type
        with pytest.raises(DataIntegrityError, match="Jackpot type cannot be empty"):
            repo.update_jackpot(jackpot_id, {'jackpot_type': ''})

    def test_update_jackpot_not_found(self, repo):
        """Test jackpot update for non-existent ID."""
        with pytest.raises(DataIntegrityError, match="Jackpot with ID 999 does not exist"):
            repo.update_jackpot(999, {'payout_amount': 2000})

    def test_delete_jackpot_success(self, repo):
        """Test successful jackpot deletion."""
        # Create a jackpot first
        game_state_id = self._create_test_game_state(repo)
        player_id = self._create_test_player(repo)
        jackpot_id = repo.create_jackpot({
            'game_state_id': game_state_id,
            'player_id': player_id,
            'jackpot_type': 'royal_flush',
            'payout_amount': 1000,
            'qualifying_cards': ['As']
        })

        success = repo.delete_jackpot(jackpot_id)
        assert success is True

        # Verify deleted
        with repo.connection.session_scope() as session:
            jackpot = session.query(Jackpot).filter(Jackpot.id == jackpot_id).first()
            assert jackpot is None

    def test_delete_jackpot_not_found(self, repo):
        """Test jackpot deletion for non-existent ID."""
        with pytest.raises(DataIntegrityError, match="Jackpot with ID 999 does not exist"):
            repo.delete_jackpot(999)

    # ============================================================================
    # BULK OPERATIONS TESTS
    # ============================================================================

    def test_create_players_bulk_success(self, repo):
        """Test successful bulk player creation."""
        game_state_id = self._create_test_game_state(repo)

        players_data = [
            {
                'game_state_id': game_state_id,
                'position': 'UTG',
                'hole_cards': 'AsKs',
                'stack_size': 1000
            },
            {
                'game_state_id': game_state_id,
                'position': 'MP',
                'hole_cards': 'QhJd',
                'stack_size': 1500,
                'is_hero': True
            }
        ]

        player_ids = repo.create_players_bulk(players_data)

        assert len(player_ids) == 2
        assert all(isinstance(pid, int) and pid > 0 for pid in player_ids)

        # Verify in database
        with repo.connection.session_scope() as session:
            players = session.query(Player).filter(Player.id.in_(player_ids)).all()
            assert len(players) == 2
            positions = {p.position for p in players}
            assert positions == {'UTG', 'MP'}

    def test_create_bets_bulk_success(self, repo):
        """Test successful bulk bet creation."""
        game_state_id = self._create_test_game_state(repo)
        player_id = self._create_test_player(repo)

        bets_data = [
            {
                'game_state_id': game_state_id,
                'player_id': player_id,
                'amount': 100,
                'action_type': 'call'
            },
            {
                'game_state_id': game_state_id,
                'player_id': player_id,
                'amount': 300,
                'action_type': 'raise',
                'round': 'flop'
            }
        ]

        bet_ids = repo.create_bets_bulk(bets_data)

        assert len(bet_ids) == 2
        assert all(isinstance(bid, int) and bid > 0 for bid in bet_ids)

        # Verify in database
        with repo.connection.session_scope() as session:
            bets = session.query(Bet).filter(Bet.id.in_(bet_ids)).all()
            assert len(bets) == 2
            amounts = {b.amount for b in bets}
            assert amounts == {100, 300}

    def test_create_jackpots_bulk_success(self, repo):
        """Test successful bulk jackpot creation."""
        game_state_id = self._create_test_game_state(repo)
        player_id = self._create_test_player(repo)

        jackpots_data = [
            {
                'game_state_id': game_state_id,
                'player_id': player_id,
                'jackpot_type': 'royal_flush',
                'payout_amount': 10000,
                'qualifying_cards': ['As', 'Ks', 'Qs', 'Js', 'Ts']
            },
            {
                'game_state_id': game_state_id,
                'player_id': player_id,
                'jackpot_type': 'straight_flush',
                'payout_amount': 5000,
                'qualifying_cards': ['9s', '8s', '7s', '6s', '5s']
            }
        ]

        jackpot_ids = repo.create_jackpots_bulk(jackpots_data)

        assert len(jackpot_ids) == 2
        assert all(isinstance(jid, int) and jid > 0 for jid in jackpot_ids)

        # Verify in database
        with repo.connection.session_scope() as session:
            jackpots = session.query(Jackpot).filter(Jackpot.id.in_(jackpot_ids)).all()
            assert len(jackpots) == 2
            types = {j.jackpot_type for j in jackpots}
            assert types == {'royal_flush', 'straight_flush'}