from datetime import datetime

from hopilot.database import DatabaseConnection
from hopilot.gto.unit_of_work import UnitOfWork
from hopilot.models import GameState


def test_unit_of_work_commits_transaction(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    connection = DatabaseConnection(database_url)
    connection.create_tables()

    with UnitOfWork(connection) as uow:
        session = uow.session
        game_state = GameState(timestamp=datetime.utcnow(), round="preflop", pot_size=10, board_cards_str="AsKsQhJh")
        session.add(game_state)

    with connection.session_scope() as session:
        result = session.query(GameState).first()
        assert result is not None
        assert float(result.pot_size) == 10.0


def test_unit_of_work_rolls_back_on_exception(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    connection = DatabaseConnection(database_url)
    connection.create_tables()

    try:
        with UnitOfWork(connection) as uow:
            session = uow.session
            game_state = GameState(timestamp=datetime.utcnow(), round="preflop", pot_size=15, board_cards_str="KsQhJhTd")
            session.add(game_state)
            raise RuntimeError("force rollback")
    except RuntimeError:
        pass

    with connection.session_scope() as session:
        rows = session.query(GameState).all()
        assert rows == []
