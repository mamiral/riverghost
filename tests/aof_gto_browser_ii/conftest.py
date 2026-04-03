"""Shared test fixtures for domain model tests."""

import pytest
from aof_gto_browser_ii.shared.domain.card import Card, Rank, Suit


@pytest.fixture
def ace_spades():
    """Ace of Spades card."""
    return Card(Rank.ACE, Suit.SPADES)


@pytest.fixture
def king_hearts():
    """King of Hearts card."""
    return Card(Rank.KING, Suit.HEARTS)


@pytest.fixture
def queen_diamonds():
    """Queen of Diamonds card."""
    return Card(Rank.QUEEN, Suit.DIAMONDS)


@pytest.fixture
def jack_clubs():
    """Jack of Clubs card."""
    return Card(Rank.JACK, Suit.CLUBS)


@pytest.fixture
def two_spades():
    """Two of Spades card."""
    return Card(Rank.TWO, Suit.SPADES)


@pytest.fixture
def sample_cards(ace_spades, king_hearts, queen_diamonds, jack_clubs, two_spades):
    """List of sample cards for testing."""
    return [ace_spades, king_hearts, queen_diamonds, jack_clubs, two_spades]


@pytest.fixture
def all_ranks():
    """All possible ranks."""
    return list(Rank)


@pytest.fixture
def all_suits():
    """All possible suits."""
    return list(Suit)