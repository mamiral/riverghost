from typing import Any, Dict

from sqlalchemy.orm import Session

from hopilot.models import Bet, GameState, Jackpot, MatrixCell, Player


def _assert_entity_exists(session: Session, model: Any, entity_id: int, entity_name: str) -> None:
    exists = session.query(model.id).filter(model.id == entity_id).first() is not None
    if not exists:
        raise ValueError(f"{entity_name} with ID {entity_id} does not exist")


def validate_game_state_data(game_state_data: Dict[str, Any], session: Session) -> None:
    required_fields = ["pot_size", "board_cards_str"]
    for field in required_fields:
        if field not in game_state_data:
            raise ValueError(f"Missing required field: {field}")

    if game_state_data["pot_size"] < 0:
        raise ValueError("Pot size cannot be negative")

    if "round" in game_state_data and game_state_data["round"] not in ["preflop", "flop", "turn", "river"]:
        raise ValueError("Round must be 'preflop', 'flop', 'turn', or 'river'")

    if not isinstance(game_state_data["board_cards_str"], str):
        raise ValueError("board_cards_str must be a string")

    if "cell_id" in game_state_data:
        _assert_entity_exists(session, MatrixCell, game_state_data["cell_id"], "MatrixCell")


def validate_player_data(player_data: Dict[str, Any], session: Session) -> None:
    required_fields = ["game_state_id", "position", "hole_cards", "stack_size"]
    for field in required_fields:
        if field not in player_data:
            raise ValueError(f"Missing required field: {field}")

    _assert_entity_exists(session, GameState, player_data["game_state_id"], "GameState")

    if not player_data["position"] or not player_data["position"].strip():
        raise ValueError("Position cannot be empty")

    hole_cards = player_data["hole_cards"]
    if not isinstance(hole_cards, str) or len(hole_cards) != 4:
        raise ValueError("Hole cards must be 4 characters (rank+suit + rank+suit)")

    if player_data["stack_size"] < 0:
        raise ValueError("Stack size cannot be negative")


def validate_bet_data(bet_data: Dict[str, Any], session: Session) -> None:
    required_fields = ["player_id", "amount"]
    for field in required_fields:
        if field not in bet_data:
            raise ValueError(f"Missing required field: {field}")

    _assert_entity_exists(session, Player, bet_data["player_id"], "Player")

    if bet_data["amount"] < 0:
        raise ValueError("Bet amount cannot be negative")


def validate_jackpot_data(jackpot_data: Dict[str, Any], session: Session) -> None:
    required_fields = ["player_id", "payout_amount"]
    for field in required_fields:
        if field not in jackpot_data:
            raise ValueError(f"Missing required field: {field}")

    _assert_entity_exists(session, Player, jackpot_data["player_id"], "Player")

    if jackpot_data["payout_amount"] < 0:
        raise ValueError("Jackpot amount cannot be negative")
