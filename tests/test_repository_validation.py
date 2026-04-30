from hopilot.database import DatabaseConnection
from hopilot.gto.repository_validation import validate_game_state_data, validate_player_data
from hopilot.models import GameState


def test_validate_game_state_data_rejects_missing_fields(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'validation.db'}"
    connection = DatabaseConnection(database_url)
    connection.create_tables()

    invalid_payload = {
        "pot_size": 100,
    }

    with connection.session_scope() as session:
        try:
            validate_game_state_data(invalid_payload, session)
            assert False, "Expected ValueError for missing board_cards_str"
        except ValueError as exc:
            assert "board_cards_str" in str(exc)


def test_validate_player_data_rejects_invalid_hole_cards(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'validation.db'}"
    connection = DatabaseConnection(database_url)
    connection.create_tables()

    from datetime import datetime

    with connection.session_scope() as session:
        game_state = GameState(timestamp=datetime(2024, 1, 1), round="preflop", pot_size=10, board_cards_str="AsKsQhJh")
        session.add(game_state)
        session.flush()

        invalid_player = {
            "game_state_id": game_state.id,
            "position": "UTG",
            "hole_cards": "ABC",
            "stack_size": 100,
        }

        try:
            validate_player_data(invalid_player, session)
            assert False, "Expected ValueError for invalid hole_cards"
        except ValueError as exc:
            assert "Hole cards" in str(exc)
