"""
GameState model for poker analysis database.

Represents detailed records of each simulated hand with outcomes
and references to all related entities.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from hopilot.models.base import BaseModel


class GameState(BaseModel):
    """
    Represents a single simulated poker hand.

    Contains all information about a hand simulation including
    players, bets, board cards, and outcome.
    """

    __tablename__ = "game_states"

    timestamp = Column(DateTime, nullable=False, index=True)
    round = Column(String(10), default="preflop", nullable=False)
    pot_size = Column(Numeric(10, 2), nullable=False)
    board_cards_str = Column(String(100), nullable=True)  # Comma-separated board cards (e.g., "As,Ks,Qd,Jh,Th")
    outcome = Column(String(20), nullable=True)

    # Composite indexes for analytical query optimization
    __table_args__ = (
        Index('ix_game_states_timestamp_outcome', 'timestamp', 'outcome'),
    )

    # Relationships
    players = relationship("Player", cascade="all, delete-orphan", overlaps="game_state")

    def __init__(self, **kwargs):
        """Initialize game state with validation."""
        super().__init__(**kwargs)

    def _validate(self) -> None:
        """Validate game state data."""
        if not self.timestamp:
            raise ValueError("Timestamp is required")

        if self.pot_size < 0:
            raise ValueError("Pot size cannot be negative")

        if self.round not in ["preflop"]:
            raise ValueError("Round must be 'preflop' for all-in-or-fold games")

    @property
    def hero_player(self):
        """Get the hero player."""
        for player in self.players:
            if player.is_hero:
                return player
        return None

    @property
    def villain_player(self):
        """Get the villain player."""
        for player in self.players:
            if not player.is_hero:
                return player
        return None

    @property
    def player_count(self) -> int:
        """Get number of players in this game state."""
        return len(self.players)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with computed fields."""
        result = super().to_dict()
        result["player_count"] = self.player_count
        return result

    def to_dict_with_relationships(self) -> Dict[str, Any]:
        """
        Convert to dictionary including all relationships.
        
        This provides a complete serialized representation of the game state
        with all related entities for efficient storage and transmission.
        
        Returns:
            Dictionary with game state and all related data
        """
        result = self.to_dict()
        
        # Add related entities
        result["players"] = [player.to_dict() for player in self.players]
        
        return result

    def to_json(self) -> str:
        """
        Serialize game state to JSON string.
        
        Returns:
            JSON string with complete game state data
        """
        return super().to_json()

    def to_json_with_relationships(self) -> str:
        """
        Serialize complete game state with relationships to JSON.
        
        This is the efficient serialization method for SIM-002 that includes
        all related entities in a single JSON document for storage.
        
        Returns:
            JSON string with complete game state and relationships
        """
        import json
        return json.dumps(self.to_dict_with_relationships(), default=str)

    @classmethod
    def from_dict_with_relationships(cls, data: Dict[str, Any], session):
        """
        Deserialize complete game state with relationships from dictionary.
        
        Args:
            data: Dictionary with game state and relationship data
            session: SQLAlchemy session for database operations
            
        Returns:
            GameState instance with all relationships populated
        """
        from hopilot.models.player import Player
        from hopilot.models.bet import Bet
        from hopilot.models.board_card import BoardCard
        from hopilot.models.jackpot import Jackpot
        
        # Create game state
        game_state_data = {k: v for k, v in data.items() 
                          if k not in ['players', 'bets', 'board_cards', 'jackpots']}
        game_state = cls.from_dict(game_state_data)
        session.add(game_state)
        session.flush()  # Get ID
        
        # Create board cards if present
        if data.get('board_cards'):
            board_card = BoardCard.from_dict(data['board_cards'])
            game_state.board_cards_id = board_card.id
            session.add(board_card)
        
        # Create players
        for player_data in data.get('players', []):
            player_data['game_state_id'] = game_state.id
            player = Player.from_dict(player_data)
            session.add(player)
            
            # Create bets for this player
            for bet_data in data.get('bets', []):
                if bet_data.get('player_id') == player_data.get('id'):
                    bet_data['game_state_id'] = game_state.id
                    bet_data['player_id'] = player.id
                    bet = Bet.from_dict(bet_data)
                    session.add(bet)
            
            # Create jackpots for this player
            for jackpot_data in data.get('jackpots', []):
                if jackpot_data.get('player_id') == player_data.get('id'):
                    jackpot_data['game_state_id'] = game_state.id
                    jackpot_data['player_id'] = player.id
                    jackpot = Jackpot.from_dict(jackpot_data)
                    session.add(jackpot)
        
        session.flush()
        return game_state

    @classmethod
    def from_json_with_relationships(cls, json_str: str, session):
        """
        Deserialize complete game state with relationships from JSON.
        
        Args:
            json_str: JSON string with complete game state data
            session: SQLAlchemy session for database operations
            
        Returns:
            GameState instance with all relationships populated
        """
        import json
        data = json.loads(json_str)
        return cls.from_dict_with_relationships(data, session)

    def to_pickle_with_relationships(self) -> bytes:
        """
        Serialize complete game state with relationships to pickle.
        
        This is the most efficient serialization method for SIM-002,
        providing fast serialization/deserialization with complete data.
        
        Returns:
            Pickle bytes with complete game state and relationships
        """
        import pickle
        return pickle.dumps(self.to_dict_with_relationships())

    @classmethod
    def from_pickle_with_relationships(cls, pickle_bytes: bytes, session):
        """
        Deserialize complete game state with relationships from pickle.
        
        Args:
            pickle_bytes: Pickle bytes with complete game state data
            session: SQLAlchemy session for database operations
            
        Returns:
            GameState instance with all relationships populated
        """
        import pickle
        data = pickle.loads(pickle_bytes)
        return cls.from_dict_with_relationships(data, session)

    def to_compressed_pickle_with_relationships(self) -> bytes:
        """
        Serialize complete game state with relationships to compressed pickle.
        
        This provides the most efficient storage method for SIM-002,
        balancing speed and compression for minimal overhead.
        
        Returns:
            Compressed pickle bytes with complete game state data
        """
        import gzip
        import pickle
        data = self.to_dict_with_relationships()
        return gzip.compress(pickle.dumps(data))

    @classmethod
    def from_compressed_pickle_with_relationships(cls, compressed_bytes: bytes, session):
        """
        Deserialize complete game state with relationships from compressed pickle.
        
        Args:
            compressed_bytes: Compressed pickle bytes
            session: SQLAlchemy session for database operations
            
        Returns:
            GameState instance with all relationships populated
        """
        import gzip
        import pickle
        data = pickle.loads(gzip.decompress(compressed_bytes))
        return cls.from_dict_with_relationships(data, session)

    def __repr__(self) -> str:
        """String representation."""
        return f"<GameState(id={self.id}, cell_id={self.cell_id}, pot={self.pot_size}, outcome={self.outcome})>"