"""
Model test data factories and fixtures.

Provides factory functions to create test data for database models
(Simulation, HandMatrix, MatrixCell, etc.) to replace cache mocks.

BLOCKED BY: None (stands alone)
BLOCKS: T020, T040 (integration tests) - uses model fixtures
"""

import random
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from hopilot.logging_config import get_logger
from hopilot.models import (
    AggregatedMetric,
    Base,
    Bet,
    GameState,
    HandMatrix,
    Jackpot,
    MatrixCell,
    Player,
    Simulation,
)

logger = get_logger(__name__)

# Poker constants
POSITIONS = [
    "BB",
    "SB",
    "UTG",
    "UTG+1",
    "UTG+2",
    "MP",
    "MP+1",
    "CO",
    "BTN",
]

ACTIONS = [
    "fold",
    "check",
    "bet",
    "call",
    "raise",
    "all_in",
]

CARD_RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"]
CARD_SUITS = ["s", "h", "d", "c"]  # spades, hearts, diamonds, clubs

POKER_HANDS = [
    "AA", "AK", "AQ", "AJ", "AT", "A9", "A8", "A7", "A6", "A5", "A4", "A3", "A2",
    "KK", "KQ", "KJ", "KT", "K9", "K8", "K7", "K6", "K5", "K4", "K3", "K2",
    "QQ", "QJ", "QT", "Q9", "Q8", "Q7", "Q6", "Q5", "Q4", "Q3", "Q2",
    "JJ", "JT", "J9", "J8", "J7", "J6", "J5", "J4", "J3", "J2",
    "TT", "T9", "T8", "T7", "T6", "T5", "T4", "T3", "T2",
    "99", "98", "97", "96", "95", "94", "93", "92",
    "88", "87", "86", "85", "84", "83", "82",
    "77", "76", "75", "74", "73", "72",
    "66", "65", "64", "63", "62",
    "55", "54", "53", "52",
    "44", "43", "42",
    "33", "32",
    "22",
]


class ModelFactory:
    """Factory for creating test data models."""

    @staticmethod
    def create_simulation(
        session: Session,
        name: str = "test_simulation",
        num_hands: int = 1000,
        **kwargs
    ) -> Simulation:
        """
        Create a test simulation record.
        
        Args:
            session: SQLAlchemy session
            name: Simulation name
            num_hands: Number of hands simulated
            **kwargs: Additional fields (player_count, stack_size, etc.)
        
        Returns:
            Simulation instance (uncommitted to session)
        """
        sim = Simulation(
            name=name,
            num_hands=num_hands,
            player_count=kwargs.get("player_count", 6),
            stack_size=kwargs.get("stack_size", 100),
            blind_size=kwargs.get("blind_size", 1),
            **kwargs
        )
        session.add(sim)
        session.flush()  # Get the ID without committing
        logger.debug(f"Created simulation: {name} (id={sim.id})")
        return sim

    @staticmethod
    def create_hand_matrix(
        session: Session,
        simulation_id: int,
        matrix_size: str = "13x13",
        **kwargs
    ) -> HandMatrix:
        """
        Create a test hand matrix.
        
        Args:
            session: SQLAlchemy session
            simulation_id: Parent simulation ID
            matrix_size: Matrix dimensions (e.g., "13x13")
            **kwargs: Additional fields
        
        Returns:
            HandMatrix instance
        """
        matrix = HandMatrix(
            simulation_id=simulation_id,
            matrix_size=matrix_size,
            **kwargs
        )
        session.add(matrix)
        session.flush()
        logger.debug(f"Created hand matrix: sim_id={simulation_id}, size={matrix_size}")
        return matrix

    @staticmethod
    def create_matrix_cell(
        session: Session,
        hand_matrix_id: int,
        row: int,
        col: int,
        hand_name: str = "AA",
        ev_value: float = 1.5,
        action: str = "raise",
        **kwargs
    ) -> MatrixCell:
        """
        Create a test matrix cell (single hand in the matrix).
        
        Args:
            session: SQLAlchemy session
            hand_matrix_id: Parent matrix ID
            row: Row index (0-12)
            col: Column index (0-12)
            hand_name: Poker hand (e.g., "AA", "KQ", "94")
            ev_value: Expected value for this hand
            action: Recommended action (fold/check/bet/call/raise/all_in)
            **kwargs: Additional fields (win_rate, tie_rate, etc.)
        
        Returns:
            MatrixCell instance
        """
        cell = MatrixCell(
            hand_matrix_id=hand_matrix_id,
            row=row,
            col=col,
            hand_name=hand_name,
            ev_value=ev_value,
            action=action,
            win_rate=kwargs.get("win_rate", random.uniform(0.3, 0.7)),
            tie_rate=kwargs.get("tie_rate", random.uniform(0.0, 0.1)),
            lose_rate=kwargs.get("lose_rate", random.uniform(0.2, 0.5)),
            **kwargs
        )
        session.add(cell)
        session.flush()
        logger.debug(f"Created matrix cell: matrix_id={hand_matrix_id}, pos=({row},{col}), hand={hand_name}")
        return cell

    @staticmethod
    def create_player(
        session: Session,
        name: str = "hero",
        position: str = "BTN",
        stack_size: float = 100.0,
        **kwargs
    ) -> Player:
        """
        Create a test player record.
        
        Args:
            session: SQLAlchemy session
            name: Player name/identifier
            position: Table position
            stack_size: Starting stack
            **kwargs: Additional fields
        
        Returns:
            Player instance
        """
        player = Player(
            name=name,
            position=position,
            stack_size=stack_size,
            **kwargs
        )
        session.add(player)
        session.flush()
        logger.debug(f"Created player: {name} at {position} (stack={stack_size})")
        return player

    @staticmethod
    def create_board_card(
        session: Session,
        game_state_id: int,
        rank: str = "A",
        suit: str = "s",
        position: int = 0,
        **kwargs
    ) -> None:
        """
        Create a test board card placeholder by updating the parent game state's board_cards_str.
        
        Args:
            session: SQLAlchemy session
            game_state_id: Parent game state ID
            rank: Card rank (A,K,Q,J,T,9-2)
            suit: Card suit (s,h,d,c)
            position: Board position (0-4): flop1, flop2, flop3, turn, river
            **kwargs: Additional fields
        
        Returns:
            None
        """
        # Store board cards on the parent game state as a comma-separated string.
        game_state = session.query(GameState).filter(GameState.id == game_state_id).first()
        if not game_state:
            raise ValueError(f"GameState {game_state_id} does not exist")

        current_cards = []
        if game_state.board_cards_str:
            current_cards = game_state.board_cards_str.split(',')

        card_value = f"{rank}{suit}"
        if len(current_cards) <= position:
            current_cards.extend(['??'] * (position + 1 - len(current_cards)))
        current_cards[position] = card_value
        game_state.board_cards_str = ','.join(current_cards)

        session.add(game_state)
        session.flush()
        logger.debug(f"Added board card {card_value} at position {position} for GameState {game_state_id}")
        return game_state

    @staticmethod
    def create_game_state(
        session: Session,
        simulation_id: int,
        phase: str = "preflop",
        position: str = "BTN",
        action_player: str = "hero",
        **kwargs
    ) -> GameState:
        """
        Create a test game state record.
        
        Args:
            session: SQLAlchemy session
            simulation_id: Parent simulation ID
            phase: Game phase (preflop/flop/turn/river)
            position: Current position to act
            action_player: Player acting
            **kwargs: Additional fields
        
        Returns:
            GameState instance
        """
        state = GameState(
            simulation_id=simulation_id,
            phase=phase,
            position=position,
            action_player=action_player,
            **kwargs
        )
        session.add(state)
        session.flush()
        logger.debug(f"Created game state: sim_id={simulation_id}, phase={phase}, pos={position}")
        return state

    @staticmethod
    def create_aggregated_metric(
        session: Session,
        simulation_id: int,
        hand_name: str = "AA",
        metric_type: str = "win_rate",
        value: float = 0.65,
        **kwargs
    ) -> AggregatedMetric:
        """
        Create a test aggregated metric record.
        
        Args:
            session: SQLAlchemy session
            simulation_id: Parent simulation ID
            hand_name: Poker hand
            metric_type: Type of metric (win_rate/tie_rate/lose_rate/ev)
            value: Metric value
            **kwargs: Additional fields
        
        Returns:
            AggregatedMetric instance
        """
        metric = AggregatedMetric(
            simulation_id=simulation_id,
            hand_name=hand_name,
            metric_type=metric_type,
            value=value,
            **kwargs
        )
        session.add(metric)
        session.flush()
        logger.debug(f"Created metric: hand={hand_name}, type={metric_type}, value={value}")
        return metric


class ScenarioBuilder:
    """Builder for creating complete test scenarios with related data."""

    def __init__(self, session: Session):
        """
        Initialize scenario builder.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
        self.factory = ModelFactory()
        self._simulation: Optional[Simulation] = None
        self._matrix: Optional[HandMatrix] = None

    def create_full_scenario(
        self,
        name: str = "test_scenario",
        num_hands: int = 1000,
        position: str = "BTN",
        action: str = "raise",
    ) -> Dict:
        """
        Create a complete test scenario with simulation, matrix, and cells.
        
        Args:
            name: Scenario name
            num_hands: Number of hands simulated
            position: Negotiation position
            action: Default action in matrix
        
        Returns:
            Dict with 'simulation', 'matrix', 'cells' keys
        """
        # Create simulation
        self._simulation = self.factory.create_simulation(
            self.session,
            name=name,
            num_hands=num_hands,
        )
        
        # Create hand matrix
        self._matrix = self.factory.create_hand_matrix(
            self.session,
            simulation_id=self._simulation.id,
        )
        
        # Create matrix cells (populate 13x13 grid)
        cells = []
        for row in range(13):
            for col in range(13):
                hand = POKER_HANDS[row * 13 + col]
                cell = self.factory.create_matrix_cell(
                    self.session,
                    hand_matrix_id=self._matrix.id,
                    row=row,
                    col=col,
                    hand_name=hand,
                    ev_value=random.uniform(-2.0, 3.0),
                    action=action,
                )
                cells.append(cell)
        
        self.session.commit()
        
        return {
            "simulation": self._simulation,
            "matrix": self._matrix,
            "cells": cells,
        }

    def create_board_scenario(
        self,
        board_cards: List[Tuple[str, str]] = None,
    ) -> GameState:
        """
        Create a game state with board cards.
        
        Args:
            board_cards: List of (rank, suit) tuples for board
        
        Returns:
            GameState instance with board setup
        """
        if not self._simulation:
            self._simulation = self.factory.create_simulation(self.session)
        
        # Determine phase from number of board cards
        if not board_cards:
            board_cards = []
        
        phase_map = {
            0: "preflop",
            3: "flop",
            4: "turn",
            5: "river",
        }
        phase = phase_map.get(len(board_cards), "preflop")
        
        # Create game state
        state = self.factory.create_game_state(
            self.session,
            simulation_id=self._simulation.id,
            phase=phase,
        )
        
        # Create board cards
        for idx, (rank, suit) in enumerate(board_cards):
            self.factory.create_board_card(
                self.session,
                game_state_id=state.id,
                rank=rank,
                suit=suit,
                position=idx,
            )
        
        self.session.commit()
        return state

    def create_players_scenario(
        self,
        positions: List[str] = None,
    ) -> List[Player]:
        """
        Create multiple players at table.
        
        Args:
            positions: List of positions (default: standard table)
        
        Returns:
            List of Player instances
        """
        if not positions:
            positions = POSITIONS
        
        players = []
        for pos in positions:
            player = self.factory.create_player(
                self.session,
                name=pos,
                position=pos,
                stack_size=100.0,
            )
            players.append(player)
        
        self.session.commit()
        return players


class FixtureHelpers:
    """Utility functions for fixture creation."""

    @staticmethod
    def random_card_hand() -> str:
        """Generate a random poker hand."""
        return random.choice(POKER_HANDS)

    @staticmethod
    def random_hand_cards() -> Tuple[Tuple[str, str], Tuple[str, str]]:
        """
        Generate a random 2-card hole hand.
        
        Returns:
            Tuple of two (rank, suit) tuples
        """
        cards = random.sample(CARD_RANKS, 2)
        suits = random.sample(CARD_SUITS, 2)
        return ((cards[0], suits[0]), (cards[1], suits[1]))

    @staticmethod
    def random_community_cards(count: int = 3) -> List[Tuple[str, str]]:
        """
        Generate random community cards.
        
        Args:
            count: Number of cards (3 for flop, 4 for turn, 5 for river)
        
        Returns:
            List of (rank, suit) tuples
        """
        if count > 13:
            raise ValueError("Cannot have more than 13 unique ranks")
        
        ranks = random.sample(CARD_RANKS, count)
        suits = random.choices(CARD_SUITS, k=count)
        return list(zip(ranks, suits))

    @staticmethod
    def random_position() -> str:
        """Get a random table position."""
        return random.choice(POSITIONS)

    @staticmethod
    def random_action() -> str:
        """Get a random poker action."""
        return random.choice(ACTIONS)
