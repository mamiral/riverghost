#!/usr/bin/env python3
"""
Game Replay Query Engine.

This module implements queries to reconstruct complete poker game sequences
chronologically from stored GameStates, Players, Bets, and BoardCards data.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from sqlalchemy import text, func, and_, or_, asc, desc
from sqlalchemy.orm import Session, joinedload

from hopilot.database import DatabaseConnection
from hopilot.models import GameState, Player, Bet, HandMatrix, MatrixCell
from hopilot.performance_monitor import PerformanceMonitor
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.query_cache import cached_query
from hopilot.gto.replay_query_service import ReplayQueryService
from hopilot.gto.simulation_repository import SimulationRepository

logger = logging.getLogger(__name__)


class GameReplayQueryEngine:
    """
    Engine for reconstructing complete poker game sequences from stored data.

    This class provides methods to replay entire poker hands chronologically,
    including all betting actions, board reveals, and player decisions.
    """

    def __init__(self, database_url: str):
        """
        Initialize the game replay query engine.

        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url
        self.db_connection = DatabaseConnection(database_url)
        self.performance_monitor = PerformanceMonitor()

    def replay_game_sequence(
        self,
        game_state_id: int,
        include_player_details: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Reconstruct a complete game sequence for a single hand.

        Args:
            game_state_id: Specific GameState ID to replay
            include_player_details: Whether to include detailed player information

        Returns:
            Complete game sequence with chronological events
        """
        with self.performance_monitor.track_operation("replay_game_sequence"):
            service = ReplayQueryService(
                db_connection=self.db_connection,
                game_state_repository=GameStateRepository(self.db_connection),
                simulation_repository=SimulationRepository(self.db_connection),
            )
            result = service.replay_game_state(game_state_id)

            if result.get("status") != "AVAILABLE":
                if result.get("status") == "NOT_FOUND":
                    logger.warning(f"GameState {game_state_id} not found")
                    return None
                return None

            return {
                'game_state_id': result['game_state_id'],
                'hand_combination': result.get('hand_combination'),
                'final_outcome': result.get('outcome'),
                'final_pot_size': result.get('pot_size'),
                'sequence': result.get('sequence', []),
                'total_events': len(result.get('sequence', [])),
                'timestamp': result.get('timestamp')
            }

    def replay_games_by_hand_combination(
        self,
        matrix_id: int,
        hand_combination: str,
        limit: int = 10,
        chronological: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Replay multiple games for a specific hand combination.

        Args:
            matrix_id: Hand matrix ID
            hand_combination: Specific hand combination to filter by
            limit: Maximum number of games to return
            chronological: Whether to order by timestamp

        Returns:
            List of game sequences
        """
        with self.performance_monitor.track_operation("replay_games_by_hand"):
            with self.db_connection.session_scope() as session:
                # Find MatrixCell for this hand combination
                matrix_cell = session.query(MatrixCell).filter(
                    and_(
                        MatrixCell.matrix_id == matrix_id,
                        MatrixCell.hand_combination == hand_combination
                    )
                ).first()

                if not matrix_cell:
                    logger.warning(f"No MatrixCell found for hand combination '{hand_combination}' in matrix {matrix_id}")
                    return []

                # Get candidate GameStates and derive cell membership from hero hole cards
                candidate_states = (
                    session.query(GameState)
                    .options(joinedload(GameState.players))
                    .order_by(asc(GameState.timestamp) if chronological else desc(GameState.timestamp))
                    .all()
                )

                game_states = [
                    gs for gs in candidate_states
                    if self._game_state_matches_cell(gs, matrix_cell.row_index, matrix_cell.col_index)
                ][:limit]

                # Build sequences for each game
                results = []
                for gs in game_states:
                    sequence = self.replay_game_sequence(gs.id, include_player_details=False)
                    if sequence:
                        results.append(sequence)

                return results

    def _game_state_matches_cell(self, game_state: GameState, row_idx: int, col_idx: int) -> bool:
        hero_player = next((player for player in game_state.players if player.is_hero), None)
        if hero_player is None:
            return False

        try:
            from hopilot.gto.aof_hand_matrix import hand_coordinates_from_hole_cards
            row, col = hand_coordinates_from_hole_cards(hero_player.hole_cards)
        except Exception:
            return False

        return row == row_idx and col == col_idx

    @cached_query(ttl=600)  # Cache for 10 minutes
    def get_game_timeline_summary(
        self,
        game_state_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Get a high-level summary of game events without full details.

        Args:
            game_state_id: GameState ID to summarize

        Returns:
            Timeline summary with key events
        """
        with self.performance_monitor.track_operation("game_timeline_summary"):
            with self.db_connection.session_scope() as session:
                game_state = session.query(GameState).filter(GameState.id == game_state_id).first()
                if not game_state:
                    return None

                # Count events by type
                bet_count = session.query(func.count(Bet.id)).filter(Bet.game_state_id == game_state_id).scalar()
                player_count = session.query(func.count(Player.id)).filter(Player.game_state_id == game_state_id).scalar()
                board_card_count = len(self._parse_board_cards(game_state.board_cards_str))

                return {
                    'game_state_id': game_state_id,
                    'round': game_state.round,
                    'outcome': game_state.outcome,
                    'pot_size': float(game_state.pot_size),
                    'event_counts': {
                        'bets': bet_count or 0,
                        'players': player_count or 0,
                        'board_cards': board_card_count or 0
                    },
                    'timestamp': game_state.timestamp.isoformat() if game_state.timestamp else None
                }

    def _parse_board_cards(self, board_cards_str: Optional[str]) -> List[str]:
        if not board_cards_str:
            return []
        return [card.strip() for card in board_cards_str.split(',') if card.strip()]

    def _build_chronological_sequence(
        self,
        session: Session,
        game_state: GameState
    ) -> List[Dict[str, Any]]:
        """
        Build a chronological sequence of game events.

        Args:
            session: Database session
            game_state: GameState object with loaded relationships

        Returns:
            Chronologically ordered list of game events
        """
        events = []

        # Add game start event
        events.append({
            'event_type': 'game_start',
            'timestamp': game_state.timestamp.isoformat() if game_state.timestamp else None,
            'round': game_state.round,
            'data': {
                'pot_size': float(game_state.pot_size),
                'player_count': len(game_state.players) if game_state.players else 0
            }
        })

        # Add board card reveals (chronological by street)
        board_cards = self._parse_board_cards(game_state.board_cards_str)
        if board_cards:
            if len(board_cards) >= 3:
                events.append({
                    'event_type': 'board_reveal',
                    'timestamp': None,
                    'round': 'flop',
                    'data': {
                        'cards': board_cards[:3],
                        'street': 'flop'
                    }
                })
            if len(board_cards) >= 4:
                events.append({
                    'event_type': 'board_reveal',
                    'timestamp': None,
                    'round': 'turn',
                    'data': {
                        'card': board_cards[3],
                        'street': 'turn'
                    }
                })
            if len(board_cards) >= 5:
                events.append({
                    'event_type': 'board_reveal',
                    'timestamp': None,
                    'round': 'river',
                    'data': {
                        'card': board_cards[4],
                        'street': 'river'
                    }
                })

        # Add betting actions (chronological)
        if game_state.bets:
            # Sort bets by ID (assuming sequential creation) and round
            sorted_bets = sorted(game_state.bets, key=lambda b: (b.id, b.round))

            for bet in sorted_bets:
                events.append({
                    'event_type': 'bet',
                    'timestamp': None,  # Bets don't have individual timestamps
                    'round': bet.round,
                    'data': {
                        'player_id': bet.player_id,
                        'action': bet.action_type,
                        'amount': float(bet.amount) if bet.amount else 0.0
                    }
                })

        # Add game end event
        events.append({
            'event_type': 'game_end',
            'timestamp': None,  # Would need to be calculated from last event
            'round': game_state.round,
            'data': {
                'outcome': game_state.outcome,
                'final_pot_size': float(game_state.pot_size)
            }
        })

        return events

    @cached_query(ttl=600)  # Cache for 10 minutes
    def get_replay_statistics(
        self,
        matrix_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about available game replays.

        Args:
            matrix_id: Optional matrix ID to filter by

        Returns:
            Statistics about replayable games
        """
        with self.performance_monitor.track_operation("replay_statistics"):
            with self.db_connection.session_scope() as session:
                # Base query
                query = session.query(
                    func.count(GameState.id).label('total_games'),
                    func.count(func.distinct(GameState.id)).label('unique_hands'),
                    func.min(GameState.timestamp).label('earliest_game'),
                    func.max(GameState.timestamp).label('latest_game')
                )

                if matrix_id:
                    logger.warning(
                        "Matrix ID filtering is not supported for replay statistics due to lack "
                        "of a direct GameState-to-MatrixCell relationship."
                    )

                result = query.first()

                return {
                    'total_games': result.total_games or 0,
                    'unique_hand_combinations': result.unique_hands or 0,
                    'date_range': {
                        'earliest': result.earliest_game.isoformat() if result.earliest_game else None,
                        'latest': result.latest_game.isoformat() if result.latest_game else None
                    },
                    'matrix_id': matrix_id
                }