"""
Persistence strategies for GameState storage.

This package implements the Strategy pattern for pluggable persistence behaviors
in the genuine GameStates-first architecture.
"""

from .base import GameStatePersistence
from .database import DatabasePersistenceStrategy
from .mock import MockPersistenceStrategy
from .memory import InMemoryPersistenceStrategy
from .batching import BatchingPersistenceStrategy
from .queue import QueuePersistenceStrategy

__all__ = [
    'GameStatePersistence',
    'DatabasePersistenceStrategy', 
    'MockPersistenceStrategy',
    'InMemoryPersistenceStrategy',
    'BatchingPersistenceStrategy',
    'QueuePersistenceStrategy',
]