import pytest
import sys
import os

# Add the python directory to the path so we can import hopilot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))

from hopilot.card_assignment_manager import CardAssignmentManager


class TestCardAssignmentManager:
    """Unit tests for CardAssignmentManager."""

    @pytest.fixture
    def card_manager(self):
        """Create a CardAssignmentManager instance for testing."""
        return CardAssignmentManager()

    def test_initialization(self, card_manager):
        """Test that CardAssignmentManager initializes correctly."""
        assert card_manager.hero_cards == [None, None]
        assert card_manager.hero_range is None
        assert card_manager.villain_cards == []
        assert card_manager.villain_ranges == []
        assert card_manager.board_cards == [None, None, None, None, None]

    def test_set_hero_card(self, card_manager):
        """Test setting hero cards."""
        # Set first card
        card_manager.set_hero_card(0, "As")
        assert card_manager.hero_cards[0] == "As"
        assert card_manager.hero_cards[1] is None

        # Setting a card should clear range
        card_manager.set_hero_range("AA")
        assert card_manager.hero_range == "AA"
        card_manager.set_hero_card(0, "Ks")
        assert card_manager.hero_range is None
        assert card_manager.hero_cards[0] == "Ks"

    def test_set_hero_range(self, card_manager):
        """Test setting hero range."""
        # Set range
        card_manager.set_hero_range("AA")
        assert card_manager.hero_range == "AA"

        # Setting a range should clear specific cards
        card_manager.set_hero_card(0, "As")
        card_manager.set_hero_card(1, "Ah")
        card_manager.set_hero_range("AKs")
        assert card_manager.hero_cards == [None, None]
        assert card_manager.hero_range == "AKs"

    def test_set_villain_card(self, card_manager):
        """Test setting villain cards."""
        # Set villain card
        card_manager.set_villain_card(0, 0, "Ks")
        assert len(card_manager.villain_cards) == 1
        assert card_manager.villain_cards[0][0] == "Ks"
        assert card_manager.villain_cards[0][1] is None

        # Setting a card should clear range
        card_manager.set_villain_range(0, "AA")
        assert card_manager.villain_ranges[0] == "AA"
        card_manager.set_villain_card(0, 0, "Qs")
        assert card_manager.villain_ranges[0] is None
        assert card_manager.villain_cards[0][0] == "Qs"

    def test_set_villain_range(self, card_manager):
        """Test setting villain range."""
        # Set range
        card_manager.set_villain_range(0, "AKs")
        assert len(card_manager.villain_ranges) == 1
        assert card_manager.villain_ranges[0] == "AKs"

        # Setting a range should clear specific cards
        card_manager.set_villain_card(0, 0, "As")
        card_manager.set_villain_card(0, 1, "Kh")
        card_manager.set_villain_range(0, "QQ")
        assert card_manager.villain_cards[0] == [None, None]
        assert card_manager.villain_ranges[0] == "QQ"

    def test_set_board_card(self, card_manager):
        """Test setting board cards."""
        card_manager.set_board_card(0, "Qd")
        assert card_manager.board_cards[0] == "Qd"

    def test_get_blocked_cards_with_specific_cards(self, card_manager):
        """Test that specific card assignments block those cards."""
        # Set some specific cards
        card_manager.set_hero_card(0, "As")
        card_manager.set_villain_card(0, 0, "Ks")
        card_manager.set_board_card(0, "Qd")

        blocked = card_manager.get_blocked_cards()
        assert "As" in blocked
        assert "Ks" in blocked
        assert "Qd" in blocked

    def test_get_blocked_cards_with_ranges(self, card_manager):
        """Test that ranges block their constituent cards."""
        # Set ranges
        card_manager.set_hero_range("33")
        card_manager.set_villain_range(0, "AA")

        blocked = card_manager.get_blocked_cards()
        # 3's from hero range
        assert "3s" in blocked
        assert "3h" in blocked
        assert "3d" in blocked
        assert "3c" in blocked
        # A's from villain range
        assert "As" in blocked
        assert "Ah" in blocked
        assert "Ad" in blocked
        assert "Ac" in blocked

    def test_can_assign_card(self, card_manager):
        """Test card assignment validation."""
        # Initially all cards should be assignable
        assert card_manager.can_assign_card("As") is True

        # After assigning a card, it should be blocked
        card_manager.set_hero_card(0, "As")
        assert card_manager.can_assign_card("As") is False
        assert card_manager.can_assign_card("Ks") is True

    def test_can_assign_range(self, card_manager):
        """Test range assignment validation."""
        # Initially all ranges should be assignable
        assert card_manager.can_assign_range("AA") is True
        assert card_manager.can_assign_range("AKs") is True

        # Ranges can overlap
        card_manager.set_hero_range("AA")
        assert card_manager.can_assign_range("AA") is True  # Overlapping ranges allowed

        # But specific cards block ranges
        card_manager.set_hero_card(0, "As")
        assert card_manager.can_assign_range("AA") is False  # As is specifically assigned

    def test_get_available_cards(self, card_manager):
        """Test getting available cards."""
        all_cards = {f"{rank}{suit}" for rank in "23456789TJQKA" for suit in "shcd"}
        available = card_manager.get_available_cards()
        assert len(available) == 52  # All cards available initially

        # After assigning some cards
        card_manager.set_hero_card(0, "As")
        available = card_manager.get_available_cards()
        assert "As" not in available
        assert len(available) == 51

    def test_get_hero_state(self, card_manager):
        """Test getting hero state."""
        state = card_manager.get_hero_state()
        assert state == {'cards': [None, None], 'range': None}

        card_manager.set_hero_range("AA")
        state = card_manager.get_hero_state()
        assert state == {'cards': [None, None], 'range': "AA"}

    def test_get_villain_state(self, card_manager):
        """Test getting villain state."""
        state = card_manager.get_villain_state(0)
        assert state == {'cards': [None, None], 'range': None}

        card_manager.set_villain_range(0, "AKs")
        state = card_manager.get_villain_state(0)
        assert state == {'cards': [None, None], 'range': "AKs"}

    def test_get_board_state(self, card_manager):
        """Test getting board state."""
        state = card_manager.get_board_state()
        assert state == [None, None, None, None, None]

        card_manager.set_board_card(0, "Qd")
        state = card_manager.get_board_state()
        assert state[0] == "Qd"

    def test_observer_pattern(self, card_manager):
        """Test observer notifications."""
        notifications = []

        def observer():
            notifications.append(True)

        card_manager.add_observer(observer)

        # Should notify on changes
        card_manager.set_hero_card(0, "As")
        assert len(notifications) == 1

        card_manager.set_hero_range("AA")
        assert len(notifications) == 2

        # Remove observer
        card_manager.remove_observer(observer)
        card_manager.set_hero_card(0, "Ks")
        assert len(notifications) == 2  # No new notification

    def test_card_blocking_after_range_to_specific_conversion(self, card_manager):
        """Test that cards selected after range conversion are properly blocked in other positions."""
        # Set hero range to "33"
        card_manager.set_hero_range("33")
        
        # Verify all 3's are blocked
        blocked_cards = card_manager.get_blocked_cards()
        assert "3s" in blocked_cards
        assert "3h" in blocked_cards
        assert "3d" in blocked_cards
        assert "3c" in blocked_cards
        
        # Now set a specific hero card "3s" - this should clear the range
        card_manager.set_hero_card(0, "3s")
        
        # Verify range is cleared
        hero_state = card_manager.get_hero_state()
        assert hero_state['range'] is None
        assert hero_state['cards'][0] == "3s"
        
        # Verify "3s" is still blocked (now by the specific card assignment)
        blocked_cards = card_manager.get_blocked_cards()
        assert "3s" in blocked_cards
        
        # Verify other 3's are now available (since range was cleared)
        assert "3h" not in blocked_cards
        assert "3d" not in blocked_cards
        assert "3c" not in blocked_cards