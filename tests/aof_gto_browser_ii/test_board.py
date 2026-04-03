import pytest
from aof_gto_browser_ii.shared.domain.board import Board
from aof_gto_browser_ii.shared.domain.card import Card, Rank, Suit


class TestBoard:
    """Test suite for Board domain model."""

    def test_construction_empty_board(self):
        """Test creating an empty board."""
        board = Board([])
        assert board.num_cards() == 0
        assert board.is_empty()
        assert not board.is_flop()
        assert not board.is_turn()
        assert not board.is_river()
        assert not board.is_complete()
        assert board.get_street() == "preflop"

    def test_construction_flop(self):
        """Test creating a flop board."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS)
        ]
        board = Board(cards)
        assert board.num_cards() == 3
        assert not board.is_empty()
        assert board.is_flop()
        assert not board.is_turn()
        assert not board.is_river()
        assert not board.is_complete()
        assert board.get_street() == "flop"

    def test_construction_turn(self):
        """Test creating a turn board."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS)
        ]
        board = Board(cards)
        assert board.num_cards() == 4
        assert board.is_turn()
        assert board.get_street() == "turn"

    def test_construction_river(self):
        """Test creating a river board."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.SPADES)
        ]
        board = Board(cards)
        assert board.num_cards() == 5
        assert board.is_river()
        assert board.is_complete()
        assert board.get_street() == "river"

    def test_validation_too_many_cards(self):
        """Test that boards with more than 5 cards raise ValueError."""
        cards = [Card(Rank.ACE, Suit.SPADES)] * 6
        with pytest.raises(ValueError, match="Board cannot have more than 5 cards"):
            Board(cards)

    def test_validation_duplicate_cards(self):
        """Test that duplicate cards raise ValueError."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.ACE, Suit.SPADES)  # Duplicate
        ]
        with pytest.raises(ValueError, match="Board contains duplicate card"):
            Board(cards)

    def test_from_strings(self):
        """Test creating board from string representations."""
        board = Board.from_strings(["As", "Kh", "Qd"])
        assert board.num_cards() == 3
        assert board.is_flop()
        expected_cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS)
        ]
        assert board.cards == expected_cards

    def test_from_strings_invalid_card(self):
        """Test that invalid card strings raise ValueError."""
        with pytest.raises(ValueError):
            Board.from_strings(["As", "Invalid", "Qd"])

    def test_to_strings(self):
        """Test converting board to string representations."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS)
        ]
        board = Board(cards)
        assert board.to_strings() == ["As", "Kh", "Qd"]

    def test_get_flop(self):
        """Test getting flop cards."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.SPADES)
        ]
        board = Board(cards)
        flop = board.get_flop()
        assert flop is not None
        assert flop == (cards[0], cards[1], cards[2])

    def test_get_flop_insufficient_cards(self):
        """Test getting flop when not enough cards."""
        board = Board([Card(Rank.ACE, Suit.SPADES)])
        assert board.get_flop() is None

    def test_get_turn(self):
        """Test getting turn card."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.SPADES)
        ]
        board = Board(cards)
        turn = board.get_turn()
        assert turn is not None
        assert turn == cards[3]

    def test_get_turn_insufficient_cards(self):
        """Test getting turn when not enough cards."""
        board = Board([Card(Rank.ACE, Suit.SPADES), Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.DIAMONDS)])
        assert board.get_turn() is None

    def test_get_river(self):
        """Test getting river card."""
        cards = [
            Card(Rank.ACE, Suit.SPADES),
            Card(Rank.KING, Suit.HEARTS),
            Card(Rank.QUEEN, Suit.DIAMONDS),
            Card(Rank.JACK, Suit.CLUBS),
            Card(Rank.TEN, Suit.SPADES)
        ]
        board = Board(cards)
        river = board.get_river()
        assert river is not None
        assert river == cards[4]

    def test_get_river_insufficient_cards(self):
        """Test getting river when not enough cards."""
        board = Board([Card(Rank.ACE, Suit.SPADES), Card(Rank.KING, Suit.HEARTS), Card(Rank.QUEEN, Suit.DIAMONDS), Card(Rank.JACK, Suit.CLUBS)])
        assert board.get_river() is None

    def test_contains_card(self):
        """Test checking if a card is on the board."""
        ace_spades = Card(Rank.ACE, Suit.SPADES)
        king_hearts = Card(Rank.KING, Suit.HEARTS)
        board = Board([ace_spades, king_hearts])

        assert board.contains_card(ace_spades)
        assert board.contains_card(king_hearts)
        assert not board.contains_card(Card(Rank.QUEEN, Suit.DIAMONDS))

    def test_all_board_cards(self):
        """Test getting copy of all board cards."""
        cards = [Card(Rank.ACE, Suit.SPADES), Card(Rank.KING, Suit.HEARTS)]
        board = Board(cards)
        board_cards = board.all_board_cards()
        assert board_cards == cards
        assert board_cards is not cards  # Should be a copy

    def test_immutability(self):
        """Test that Board is immutable."""
        board = Board([Card(Rank.ACE, Suit.SPADES)])
        with pytest.raises(AttributeError):
            board.cards = []  # Should fail

    def test_hashability(self):
        """Test that Board instances are hashable."""
        board1 = Board([Card(Rank.ACE, Suit.SPADES), Card(Rank.KING, Suit.HEARTS)])
        board2 = Board([Card(Rank.ACE, Suit.SPADES), Card(Rank.KING, Suit.HEARTS)])
        board3 = Board([Card(Rank.ACE, Suit.SPADES)])

        # Same boards should have same hash
        assert hash(board1) == hash(board2)
        # Different boards should have different hashes
        assert hash(board1) != hash(board3)

        # Should work in sets
        board_set = {board1, board2, board3}
        assert len(board_set) == 2  # board1 and board2 are equal

    def test_string_representations(self):
        """Test string representations."""
        board = Board.from_strings(["As", "Kh", "Qd"])
        assert str(board) == "As Kh Qd"
        assert repr(board) == "Board(cards=['As', 'Kh', 'Qd'])"

    def test_empty_board_string(self):
        """Test string representation of empty board."""
        board = Board([])
        assert str(board) == ""
        assert repr(board) == "Board(cards=[])"