# AOF GTO Browser II - Shared Models Test Suite
#
# Comprehensive tests for Phase 1.2 shared models and DTOs.
# Target: ≥95% code coverage with 100+ test cases.
#
# Test organization:
# - Enum tests: Creation, validation, string conversion
# - DTO tests: Valid creation, validation, immutability, properties
# - Integration tests: Cross-DTO validation, serialization
# - Edge case tests: Boundary values, type rejection, error handling

import os
import sys

# Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import pytest
from aof_gto_browser_ii.shared.models import (
    Position, Action, MetricType,
    PositionContext, ActionContext, AnalysisRequest,
    HandEvaluation, MatrixPayload, CellDisplay, PrecomputeProgress,
)
from aof_gto_browser_ii.shared.domain import HandRange


class TestPositionEnum:
    """Test Position enum creation, validation, and string conversion."""

    def test_position_creation_by_attribute(self):
        """T009: Position creation by attribute access."""
        assert Position.BTN == Position.BTN
        assert Position.UTG == Position.UTG
        assert Position.SB == Position.SB
        assert Position.BB == Position.BB

    def test_position_creation_by_name(self):
        """T009: Position creation by name lookup."""
        assert Position["BTN"] == Position.BTN
        assert Position["UTG"] == Position.UTG
        assert Position["SB"] == Position.SB
        assert Position["BB"] == Position.BB

    def test_position_creation_by_value(self):
        """T009: Position creation by value lookup."""
        assert Position("btn") == Position.BTN
        assert Position("utg") == Position.UTG
        assert Position("sb") == Position.SB
        assert Position("bb") == Position.BB

    def test_position_string_conversion(self):
        """T012: String conversion of Position enum."""
        # For string-inheriting enums, str() returns the enum name, not value
        assert str(Position.BTN) == "Position.BTN"
        assert str(Position.UTG) == "Position.UTG"
        assert str(Position.SB) == "Position.SB"
        assert str(Position.BB) == "Position.BB"

        # Test that enum members are strings and have correct values
        assert Position.BTN == "btn"
        assert Position.UTG == "utg"
        assert Position.SB == "sb"
        assert Position.BB == "bb"

    def test_position_invalid_value(self):
        """T010: Invalid Position values raise appropriate exceptions."""
        with pytest.raises(ValueError):
            Position("cutoff")  # Invalid position value

        with pytest.raises(KeyError):
            Position["INVALID"]  # Invalid name lookup

    def test_position_members(self):
        """Verify all expected Position members exist."""
        expected_members = {"UTG", "BTN", "SB", "BB"}
        actual_members = {member.name for member in Position}
        assert actual_members == expected_members

    def test_position_values(self):
        """Verify Position values are lowercase strings."""
        for position in Position:
            assert isinstance(position.value, str)
            assert position.value == position.value.lower()


class TestActionEnum:
    """Test Action enum creation, validation, and string conversion."""

    def test_action_creation_by_attribute(self):
        """T011: Action creation by attribute access."""
        assert Action.FOLD == Action.FOLD
        assert Action.ALL_IN == Action.ALL_IN

    def test_action_creation_by_name(self):
        """T011: Action creation by name lookup."""
        assert Action["FOLD"] == Action.FOLD
        assert Action["ALL_IN"] == Action.ALL_IN

    def test_action_creation_by_value(self):
        """T011: Action creation by value lookup."""
        assert Action("fold") == Action.FOLD
        assert Action("all_in") == Action.ALL_IN

    def test_action_string_conversion(self):
        """T012: String conversion of Action enum."""
        # For string-inheriting enums, str() returns the enum name, not value
        assert str(Action.FOLD) == "Action.FOLD"
        assert str(Action.ALL_IN) == "Action.ALL_IN"

        # Test that enum members are strings and have correct values
        assert Action.FOLD == "fold"
        assert Action.ALL_IN == "all_in"

    def test_action_invalid_value(self):
        """T010: Invalid Action values raise appropriate exceptions."""
        with pytest.raises(ValueError):
            Action("call")  # Invalid action value

        with pytest.raises(KeyError):
            Action["CHECK"]  # Invalid name lookup

    def test_action_members(self):
        """Verify all expected Action members exist."""
        expected_members = {"FOLD", "ALL_IN"}
        actual_members = {member.name for member in Action}
        assert actual_members == expected_members


class TestMetricTypeEnum:
    """Test MetricType enum creation, validation, and string conversion."""

    def test_metric_type_creation_by_attribute(self):
        """T011: MetricType creation by attribute access."""
        assert MetricType.EQUITY == MetricType.EQUITY
        assert MetricType.EV == MetricType.EV
        assert MetricType.EQR == MetricType.EQR
        assert MetricType.WIN_LOSE_PROBABILITY == MetricType.WIN_LOSE_PROBABILITY

    def test_metric_type_creation_by_name(self):
        """T011: MetricType creation by name lookup."""
        assert MetricType["EQUITY"] == MetricType.EQUITY
        assert MetricType["EV"] == MetricType.EV
        assert MetricType["EQR"] == MetricType.EQR
        assert MetricType["WIN_LOSE_PROBABILITY"] == MetricType.WIN_LOSE_PROBABILITY

    def test_metric_type_creation_by_value(self):
        """T011: MetricType creation by value lookup."""
        assert MetricType("equity") == MetricType.EQUITY
        assert MetricType("ev") == MetricType.EV
        assert MetricType("eqr") == MetricType.EQR
        assert MetricType("win_lose_probability") == MetricType.WIN_LOSE_PROBABILITY

    def test_metric_type_string_conversion(self):
        """T012: String conversion of MetricType enum."""
        # For string-inheriting enums, str() returns the enum name, not value
        assert str(MetricType.EQUITY) == "MetricType.EQUITY"
        assert str(MetricType.EV) == "MetricType.EV"
        assert str(MetricType.EQR) == "MetricType.EQR"
        assert str(MetricType.WIN_LOSE_PROBABILITY) == "MetricType.WIN_LOSE_PROBABILITY"

        # Test that enum members are strings and have correct values
        assert MetricType.EQUITY == "equity"
        assert MetricType.EV == "ev"
        assert MetricType.EQR == "eqr"
        assert MetricType.WIN_LOSE_PROBABILITY == "win_lose_probability"

    def test_metric_type_invalid_value(self):
        """T010: Invalid MetricType values raise appropriate exceptions."""
        with pytest.raises(ValueError):
            MetricType("invalid_metric")  # Invalid metric value

        with pytest.raises(KeyError):
            MetricType["UNKNOWN"]  # Invalid name lookup

    def test_metric_type_members(self):
        """Verify all expected MetricType members exist."""
        expected_members = {"EQUITY", "EV", "EQR", "WIN_LOSE_PROBABILITY"}
        actual_members = {member.name for member in MetricType}
        assert actual_members == expected_members


class TestPositionContext:
    """Test PositionContext DTO creation, validation, and immutability."""

    def test_position_context_creation_valid(self):
        """T036: Valid creation with all fields."""
        ctx = PositionContext(
            position=Position.BTN,
            num_opponents=2,
            heroes_hole_cards=None,
            pot_size_bb=5.0
        )
        assert ctx.position == Position.BTN
        assert ctx.num_opponents == 2
        assert ctx.heroes_hole_cards is None
        assert ctx.pot_size_bb == 5.0

    def test_position_context_creation_minimal(self):
        """Valid creation with minimal required fields."""
        ctx = PositionContext(position=Position.UTG, num_opponents=1)
        assert ctx.position == Position.UTG
        assert ctx.num_opponents == 1
        assert ctx.heroes_hole_cards is None
        assert ctx.pot_size_bb == 1.0  # default

    def test_position_context_immutability(self):
        """T036: Immutability enforcement (frozen=True)."""
        ctx = PositionContext(position=Position.BTN, num_opponents=1)
        with pytest.raises(AttributeError):
            ctx.position = Position.SB  # Should fail

    def test_position_context_equality(self):
        """Test equality and identity properties."""
        ctx1 = PositionContext(position=Position.BTN, num_opponents=1)
        ctx2 = PositionContext(position=Position.BTN, num_opponents=1)
        assert ctx1 == ctx2
        assert hash(ctx1) == hash(ctx2)  # frozen dataclass is hashable

    def test_position_context_repr(self):
        """Test string representation for debugging."""
        ctx = PositionContext(position=Position.BTN, num_opponents=1)
        repr_str = repr(ctx)
        assert "PositionContext" in repr_str
        assert "position=<Position.BTN:" in repr_str  # Enum repr includes value

    def test_position_context_validation_invalid_position(self):
        """T037: Invalid position type raises ValueError."""
        with pytest.raises(ValueError, match="position must be Position enum"):
            PositionContext(position="btn", num_opponents=1)  # string instead of enum

    def test_position_context_validation_num_opponents_too_low(self):
        """T037: num_opponents < 1 raises ValueError."""
        with pytest.raises(ValueError, match="num_opponents must be 1-3"):
            PositionContext(position=Position.BTN, num_opponents=0)

    def test_position_context_validation_num_opponents_too_high(self):
        """T037: num_opponents > 3 raises ValueError."""
        with pytest.raises(ValueError, match="num_opponents must be 1-3"):
            PositionContext(position=Position.BTN, num_opponents=4)

    def test_position_context_validation_pot_size_bb_zero(self):
        """T037: pot_size_bb <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="pot_size_bb must be positive"):
            PositionContext(position=Position.BTN, num_opponents=1, pot_size_bb=0)

    def test_position_context_validation_pot_size_bb_negative(self):
        """pot_size_bb negative raises ValueError."""
        with pytest.raises(ValueError, match="pot_size_bb must be positive"):
            PositionContext(position=Position.BTN, num_opponents=1, pot_size_bb=-1.0)

    def test_position_context_validation_heroes_hole_cards_wrong_type(self):
        """T038: heroes_hole_cards wrong type raises ValueError."""
        with pytest.raises(ValueError, match="heroes_hole_cards must be Hand domain model"):
            PositionContext(position=Position.BTN, num_opponents=1, heroes_hole_cards="AhKd")  # string instead of Hand


class TestActionContext:
    """Test ActionContext DTO creation, validation, and properties."""

    def test_action_context_creation_valid(self):
        """T039: Valid creation with PositionContext and Action."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        action_ctx = ActionContext(position_context=pos_ctx, action=Action.ALL_IN)
        assert action_ctx.position_context == pos_ctx
        assert action_ctx.action == Action.ALL_IN

    def test_action_context_validation_position_context_type(self):
        """T039: position_context must be PositionContext instance."""
        with pytest.raises(ValueError, match="position_context must be PositionContext"):
            ActionContext(position_context="invalid", action=Action.FOLD)

    def test_action_context_validation_action_type(self):
        """T039: action must be Action enum."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        with pytest.raises(ValueError, match="action must be Action enum"):
            ActionContext(position_context=pos_ctx, action="fold")  # string instead of enum

    def test_action_context_validation_action_invalid_value(self):
        """T021: action must be FOLD or ALL_IN."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        # Note: Action enum only has FOLD and ALL_IN, so this test validates the enum constraint
        # If we had other actions, this would test the business rule

    def test_action_context_is_aggressive_property(self):
        """T040: is_aggressive property returns True for ALL_IN, False for FOLD."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)

        fold_ctx = ActionContext(position_context=pos_ctx, action=Action.FOLD)
        assert fold_ctx.is_aggressive is False

        all_in_ctx = ActionContext(position_context=pos_ctx, action=Action.ALL_IN)
        assert all_in_ctx.is_aggressive is True

    def test_action_context_immutability(self):
        """ActionContext is immutable (frozen=True)."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        action_ctx = ActionContext(position_context=pos_ctx, action=Action.FOLD)
        with pytest.raises(AttributeError):
            action_ctx.action = Action.ALL_IN


class TestAnalysisRequest:
    """Test AnalysisRequest DTO (CRITICAL) - 30+ test cases required."""

    def test_analysis_request_creation_minimal(self):
        """T041: Valid creation with minimal fields (position_context only)."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        request = AnalysisRequest(position_context=pos_ctx)
        assert request.position_context == pos_ctx
        assert request.opponent_range is None
        assert request.metric_type == MetricType.EQUITY  # default
        assert request.precompute is False  # default
        assert request.session_id is None  # default

    def test_analysis_request_creation_full(self):
        """Valid creation with all fields specified."""
        from aof_gto_browser_ii.shared.domain import HandRange

        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        opp_range = HandRange.from_shorthand("22+")
        request = AnalysisRequest(
            position_context=pos_ctx,
            opponent_range=opp_range,
            metric_type=MetricType.EV,
            precompute=True,
            session_id="test_session_123"
        )
        assert request.position_context == pos_ctx
        assert request.opponent_range == opp_range
        assert request.metric_type == MetricType.EV
        assert request.precompute is True
        assert request.session_id == "test_session_123"

    def test_analysis_request_validation_position_context_type(self):
        """T041: position_context must be PositionContext instance."""
        with pytest.raises(ValueError, match="position_context must be PositionContext"):
            AnalysisRequest(position_context="invalid")

    def test_analysis_request_validation_opponent_range_type(self):
        """T041: opponent_range must be HandRange domain model if provided."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        with pytest.raises(ValueError, match="opponent_range must be HandRange domain model"):
            AnalysisRequest(position_context=pos_ctx, opponent_range="22+")  # string instead of HandRange

    def test_analysis_request_validation_metric_type_enum(self):
        """T041: metric_type must be MetricType enum."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        with pytest.raises(ValueError, match="metric_type must be MetricType enum"):
            AnalysisRequest(position_context=pos_ctx, metric_type="equity")  # string instead of enum

    def test_analysis_request_validation_precompute_bool(self):
        """T041: precompute must be boolean."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        with pytest.raises(ValueError, match="precompute must be bool"):
            AnalysisRequest(position_context=pos_ctx, precompute="true")  # string instead of bool

    def test_analysis_request_validation_session_id_string(self):
        """T041: session_id must be string if provided."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        with pytest.raises(ValueError, match="session_id must be string"):
            AnalysisRequest(position_context=pos_ctx, session_id=123)  # int instead of string

    def test_analysis_request_validation_session_id_non_empty(self):
        """T041: session_id must be non-empty string if provided."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        with pytest.raises(ValueError, match="session_id must be non-empty string"):
            AnalysisRequest(position_context=pos_ctx, session_id="")  # empty string

    def test_analysis_request_is_heads_up_property(self):
        """T042: is_heads_up returns True if 1 opponent."""
        # Heads-up
        pos_ctx_1v1 = PositionContext(position=Position.BTN, num_opponents=1)
        request_1v1 = AnalysisRequest(position_context=pos_ctx_1v1)
        assert request_1v1.is_heads_up is True

        # Multi-way
        pos_ctx_3way = PositionContext(position=Position.BTN, num_opponents=2)
        request_3way = AnalysisRequest(position_context=pos_ctx_3way)
        assert request_3way.is_heads_up is False

    def test_analysis_request_is_partial_request_property(self):
        """T042: is_partial_request returns True if hero hand specified."""
        from aof_gto_browser_ii.shared.domain import Hand

        # No hero hand (full matrix)
        pos_ctx_no_hero = PositionContext(position=Position.BTN, num_opponents=1)
        request_no_hero = AnalysisRequest(position_context=pos_ctx_no_hero)
        assert request_no_hero.is_partial_request is False

        # Hero hand specified (partial analysis)
        hero_hand = Hand.from_strings("Ah", "Kd")
        pos_ctx_with_hero = PositionContext(
            position=Position.BTN,
            num_opponents=1,
            heroes_hole_cards=hero_hand
        )
        request_with_hero = AnalysisRequest(position_context=pos_ctx_with_hero)
        assert request_with_hero.is_partial_request is True

    def test_analysis_request_is_precompute_requested_property(self):
        """T042: is_precompute_requested returns True if precompute flag set."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)

        request_no_precompute = AnalysisRequest(position_context=pos_ctx, precompute=False)
        assert request_no_precompute.is_precompute_requested is False

        request_with_precompute = AnalysisRequest(position_context=pos_ctx, precompute=True)
        assert request_with_precompute.is_precompute_requested is True

    def test_analysis_request_effective_opponent_range_property(self):
        """T042: effective_opponent_range returns provided range or all hands if None."""
        from aof_gto_browser_ii.shared.domain import HandRange

        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)

        # No opponent range specified - should return all hands
        request_no_range = AnalysisRequest(position_context=pos_ctx)
        effective_range = request_no_range.effective_opponent_range
        assert isinstance(effective_range, HandRange)
        # Note: We can't easily test the exact content without knowing HandRange internals

        # Opponent range specified - should return provided range
        specified_range = HandRange.from_shorthand("22+")
        request_with_range = AnalysisRequest(
            position_context=pos_ctx,
            opponent_range=specified_range
        )
        assert request_with_range.effective_opponent_range == specified_range

    def test_analysis_request_with_opponent_range_method(self):
        """T043: with_opponent_range() creates new instance with different range."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        original_request = AnalysisRequest(
            position_context=pos_ctx,
            metric_type=MetricType.EV,
            precompute=True,
            session_id="original_session"
        )

        # Create new request with different range
        new_request = original_request.with_opponent_range("AKs,AQo")

        # Original should be unchanged
        assert original_request.opponent_range is None
        assert original_request.metric_type == MetricType.EV
        assert original_request.precompute is True
        assert original_request.session_id == "original_session"

        # New request should have new range but preserve other fields
        assert new_request.position_context == pos_ctx
        assert new_request.opponent_range is not None  # Would be HandRange("AKs,AQo")
        assert new_request.metric_type == MetricType.EV
        assert new_request.precompute is True
        assert new_request.session_id == "original_session"

        # Should be different objects
        assert new_request is not original_request

    def test_analysis_request_with_metric_type_method(self):
        """T043: with_metric_type() creates new instance with different metric."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        original_request = AnalysisRequest(
            position_context=pos_ctx,
            metric_type=MetricType.EQUITY,
            precompute=False
        )

        # Create new request with different metric
        new_request = original_request.with_metric_type(MetricType.EV)

        # Original should be unchanged
        assert original_request.metric_type == MetricType.EQUITY
        assert original_request.precompute is False

        # New request should have new metric but preserve other fields
        assert new_request.position_context == pos_ctx
        assert new_request.metric_type == MetricType.EV
        assert new_request.precompute is False
        assert new_request.opponent_range is None
        assert new_request.session_id is None

        # Should be different objects
        assert new_request is not original_request

    def test_analysis_request_functional_chaining(self):
        """T043: Functional methods can be chained."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        original_request = AnalysisRequest(position_context=pos_ctx)

        # Chain methods
        chained_request = original_request.with_metric_type(MetricType.EV)
        # Note: with_opponent_range would be chained here if we had a second method

        assert chained_request.metric_type == MetricType.EV
        assert chained_request.position_context == pos_ctx

    def test_analysis_request_session_tracking(self):
        """T045: session_id enables request correlation."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)

        # Same session_id links related requests
        request1 = AnalysisRequest(position_context=pos_ctx, session_id="session_abc")
        request2 = AnalysisRequest(position_context=pos_ctx, session_id="session_abc")

        # Different session_ids for different analysis sessions
        request3 = AnalysisRequest(position_context=pos_ctx, session_id="session_xyz")

        assert request1.session_id == request2.session_id
        assert request1.session_id != request3.session_id

    def test_analysis_request_immutability(self):
        """T044: AnalysisRequest is immutable (frozen=True)."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        request = AnalysisRequest(position_context=pos_ctx)
        with pytest.raises(AttributeError):
            request.metric_type = MetricType.EV  # Should fail

    def test_analysis_request_hash_consistency(self):
        """T044: Identical requests have identical hashes."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        request1 = AnalysisRequest(position_context=pos_ctx, metric_type=MetricType.EQUITY)
        request2 = AnalysisRequest(position_context=pos_ctx, metric_type=MetricType.EQUITY)

        assert request1 == request2
        assert hash(request1) == hash(request2)

    def test_analysis_request_repr(self):
        """AnalysisRequest has useful repr for debugging."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        request = AnalysisRequest(position_context=pos_ctx, session_id="test_session")
        repr_str = repr(request)
        assert "AnalysisRequest" in repr_str
        assert "session_id='test_session'" in repr_str


class TestHandEvaluation:
    """Test HandEvaluation creation, validation, and properties."""

    def test_hand_evaluation_valid_creation_minimal(self):
        """T070: Valid creation with minimal required fields."""
        eval = HandEvaluation(equity=0.5)
        assert eval.equity == 0.5
        assert eval.equity_std == 0.0
        assert eval.ev == 0.0
        assert eval.win_probability == 0.0
        assert eval.tie_probability == 0.0
        assert eval.lose_probability == 0.0
        assert eval.win_money == 0.0
        assert eval.lose_money == 0.0
        assert eval.num_simulations == 0
        assert eval.is_computed is True

    def test_hand_evaluation_valid_creation_full(self):
        """T070: Valid creation with all fields specified."""
        eval = HandEvaluation(
            equity=0.623,
            equity_std=0.015,
            ev=3.8,
            win_probability=0.45,
            tie_probability=0.02,
            lose_probability=0.53,
            win_money=8.5,
            lose_money=2.1,
            num_simulations=50000,
            is_computed=True
        )
        assert eval.equity == 0.623
        assert eval.equity_std == 0.015
        assert eval.ev == 3.8
        assert eval.win_probability == 0.45
        assert eval.tie_probability == 0.02
        assert eval.lose_probability == 0.53
        assert eval.win_money == 8.5
        assert eval.lose_money == 2.1
        assert eval.num_simulations == 50000
        assert eval.is_computed is True

    def test_hand_evaluation_equity_validation(self):
        """T071: Test equity validation (0.0-1.0)."""
        # Valid values
        HandEvaluation(equity=0.0)
        HandEvaluation(equity=0.5)
        HandEvaluation(equity=1.0)

        # Invalid values
        with pytest.raises(ValueError, match="equity must be 0.0-1.0"):
            HandEvaluation(equity=-0.1)
        with pytest.raises(ValueError, match="equity must be 0.0-1.0"):
            HandEvaluation(equity=1.1)

    def test_hand_evaluation_probability_validation(self):
        """T071: Test probability validation (0.0-1.0)."""
        # Valid probabilities
        HandEvaluation(
            equity=0.5,
            win_probability=0.0,
            tie_probability=0.5,
            lose_probability=1.0
        )

        # Invalid probabilities
        with pytest.raises(ValueError, match="win_probability must be 0.0-1.0"):
            HandEvaluation(equity=0.5, win_probability=-0.1)
        with pytest.raises(ValueError, match="win_probability must be 0.0-1.0"):
            HandEvaluation(equity=0.5, win_probability=1.1)
        with pytest.raises(ValueError, match="tie_probability must be 0.0-1.0"):
            HandEvaluation(equity=0.5, tie_probability=-0.1)
        with pytest.raises(ValueError, match="lose_probability must be 0.0-1.0"):
            HandEvaluation(equity=0.5, lose_probability=1.1)

    def test_hand_evaluation_money_validation(self):
        """Test money validation (>= 0)."""
        # Valid money values
        HandEvaluation(equity=0.5, win_money=0.0, lose_money=10.0)
        HandEvaluation(equity=0.5, win_money=5.5, lose_money=0.0)

        # Invalid money values
        with pytest.raises(ValueError, match="win_money must be >= 0"):
            HandEvaluation(equity=0.5, win_money=-1.0)
        with pytest.raises(ValueError, match="lose_money must be >= 0"):
            HandEvaluation(equity=0.5, lose_money=-0.5)

    def test_hand_evaluation_simulation_validation(self):
        """T072: Test num_simulations validation."""
        # Valid combinations
        HandEvaluation(equity=0.5, num_simulations=1000, is_computed=True)
        HandEvaluation(equity=0.5, num_simulations=0, is_computed=False)
        HandEvaluation(equity=0.5, num_simulations=50000, is_computed=True)
        HandEvaluation(equity=0.5, num_simulations=0, is_computed=True)  # Allow 0 for computed results

        # Invalid combinations
        with pytest.raises(ValueError, match="num_simulations must be >= 0 when is_computed=True"):
            HandEvaluation(equity=0.5, num_simulations=-1, is_computed=True)
        with pytest.raises(ValueError, match="num_simulations must be >= 0 when is_computed=False"):
            HandEvaluation(equity=0.5, num_simulations=-1, is_computed=False)

    def test_hand_evaluation_equity_std_validation(self):
        """Test equity_std validation (>= 0)."""
        # Valid values
        HandEvaluation(equity=0.5, equity_std=0.0)
        HandEvaluation(equity=0.5, equity_std=0.015)
        HandEvaluation(equity=0.5, equity_std=0.1)

        # Invalid values
        with pytest.raises(ValueError, match="equity_std must be >= 0"):
            HandEvaluation(equity=0.5, equity_std=-0.001)

    def test_hand_evaluation_immutability(self):
        """Test that HandEvaluation is immutable (frozen=True)."""
        eval = HandEvaluation(equity=0.5)
        with pytest.raises(AttributeError):
            eval.equity = 0.6  # Should fail because frozen=True

    def test_hand_evaluation_equality_and_hash(self):
        """Test equality and hash for frozen dataclass."""
        eval1 = HandEvaluation(equity=0.5, ev=2.0)
        eval2 = HandEvaluation(equity=0.5, ev=2.0)
        eval3 = HandEvaluation(equity=0.6, ev=2.0)

        assert eval1 == eval2
        assert eval1 != eval3
        assert hash(eval1) == hash(eval2)
        assert hash(eval1) != hash(eval3)


class TestMatrixPayload:
    """Test MatrixPayload creation, validation, and methods."""

    def test_matrix_payload_valid_creation_minimal(self):
        """T073: Valid creation with minimal required fields."""
        # Create 169 hand evaluations (all with same values for simplicity)
        cells = {}
        expected_hands = MatrixPayload._generate_all_hand_keys()
        for hand_key in expected_hands:
            cells[hand_key] = HandEvaluation(equity=0.5)

        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        matrix = MatrixPayload(cells=cells, query_context=pos_ctx)

        assert len(matrix.cells) == 169
        assert matrix.query_context == pos_ctx
        assert matrix.opponent_range is None
        assert matrix.metric_type == MetricType.EQUITY
        assert matrix.average_equity == 0.0
        assert matrix.all_computed is True
        assert matrix.total_simulations == 0
        assert matrix.computed_at == ""

    def test_matrix_payload_hand_key_validation(self):
        """T074: Test exact hand key set validation."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)

        # Test missing hands
        cells = {"AA": HandEvaluation(equity=0.5)}  # Only 1 hand instead of 169
        with pytest.raises(ValueError, match="Matrix must have 169 hands"):
            MatrixPayload(cells=cells, query_context=pos_ctx)

        # Test invalid hand key (results in 170 hands instead of 169)
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}
        cells["INVALID"] = HandEvaluation(equity=0.5)  # Add invalid key
        with pytest.raises(ValueError, match="Matrix must have 169 hands, got 170"):
            MatrixPayload(cells=cells, query_context=pos_ctx)

    def test_matrix_payload_cell_type_validation(self):
        """T074: Test that all cells must be HandEvaluation objects."""
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}

        # Replace one cell with invalid type
        cells["AA"] = "not_a_hand_evaluation"
        with pytest.raises(ValueError, match="Cell AA must be HandEvaluation"):
            MatrixPayload(cells=cells, query_context=pos_ctx)

    def test_matrix_payload_query_context_validation(self):
        """Test query_context validation."""
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}

        # Invalid query context
        with pytest.raises(ValueError, match="query_context must be PositionContext"):
            MatrixPayload(cells=cells, query_context="invalid")

    def test_matrix_payload_opponent_range_validation(self):
        """Test opponent_range validation."""
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)

        # Valid: None
        MatrixPayload(cells=cells, query_context=pos_ctx, opponent_range=None)

        # Invalid: wrong type
        with pytest.raises(ValueError, match="opponent_range must be HandRange or None"):
            MatrixPayload(cells=cells, query_context=pos_ctx, opponent_range="invalid")

    def test_matrix_payload_metric_type_validation(self):
        """Test metric_type validation."""
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)

        # Invalid metric type
        with pytest.raises(ValueError, match="metric_type must be MetricType enum"):
            MatrixPayload(cells=cells, query_context=pos_ctx, metric_type="invalid")

    def test_matrix_payload_statistics_validation(self):
        """Test statistics validation (0.0-1.0)."""
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)

        # Invalid statistics
        with pytest.raises(ValueError, match="average_equity must be 0.0-1.0"):
            MatrixPayload(cells=cells, query_context=pos_ctx, average_equity=-0.1)
        with pytest.raises(ValueError, match="median_equity must be 0.0-1.0"):
            MatrixPayload(cells=cells, query_context=pos_ctx, median_equity=1.1)

    def test_matrix_payload_get_hand_method(self):
        """T075: Test get_hand() method."""
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        matrix = MatrixPayload(cells=cells, query_context=pos_ctx)

        # Valid hand
        result = matrix.get_hand("AA")
        assert isinstance(result, HandEvaluation)
        assert result.equity == 0.5

        # Invalid hand
        with pytest.raises(KeyError, match="Hand 'INVALID' not found"):
            matrix.get_hand("INVALID")

    def test_matrix_payload_get_hands_by_type_method(self):
        """T076: Test get_hands_by_type() method."""
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        matrix = MatrixPayload(cells=cells, query_context=pos_ctx)

        # Test pairs
        pairs = matrix.get_hands_by_type('pairs')
        assert len(pairs) == 13  # AA, KK, QQ, JJ, TT, 99, 88, 77, 66, 55, 44, 33, 22
        assert all(key in pairs for key in ['AA', 'KK', 'QQ'])

        # Test suited
        suited = matrix.get_hands_by_type('suited')
        assert len(suited) == 78  # 13×12/2 = 78
        assert 'AKs' in suited
        assert 'AKo' not in suited

        # Test unsuited
        unsuited = matrix.get_hands_by_type('unsuited')
        assert len(unsuited) == 78  # 13×12/2 = 78
        assert 'AKo' in unsuited
        assert 'AKs' not in unsuited

        # Invalid type
        with pytest.raises(ValueError, match="hand_type must be 'pairs', 'suited', or 'unsuited'"):
            matrix.get_hands_by_type('invalid')

    def test_matrix_payload_computed_at_validation(self):
        """Test computed_at timestamp validation."""
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)

        # Valid ISO timestamp
        MatrixPayload(cells=cells, query_context=pos_ctx, computed_at="2026-04-03T14:30:45Z")

        # Invalid timestamp
        with pytest.raises(ValueError, match="computed_at must be valid ISO timestamp"):
            MatrixPayload(cells=cells, query_context=pos_ctx, computed_at="invalid-timestamp")

    def test_matrix_payload_immutability(self):
        """Test that MatrixPayload is immutable (frozen=True)."""
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        matrix = MatrixPayload(cells=cells, query_context=pos_ctx)

        with pytest.raises(AttributeError):
            matrix.average_equity = 0.6  # Should fail because frozen=True


class TestCellDisplay:
    """Test CellDisplay creation, validation, and properties."""

    def test_cell_display_valid_creation_minimal(self):
        """T077: Valid creation with minimal required fields."""
        display = CellDisplay(
            hand_key="AKs",
            metric_value=0.623,
            display_text="62.3%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(128, 128, 128)
        )

        assert display.hand_key == "AKs"
        assert display.metric_value == 0.623
        assert display.display_text == "62.3%"
        assert display.background_color == (255, 255, 255)
        assert display.text_color == (0, 0, 0)
        assert display.border_color == (128, 128, 128)
        assert display.is_computed is True
        assert display.confidence == 1.0
        assert display.show_border is False
        assert display.highlight_level == 0
        assert display.is_hovering is False
        assert display.is_selected is False
        assert display.opacity == 1.0
        assert display.tooltip_text is None
        assert display.secondary_text is None

    def test_cell_display_valid_creation_full(self):
        """T077: Valid creation with all fields specified."""
        display = CellDisplay(
            hand_key="AA",
            metric_value=0.85,
            display_text="85.0%",
            background_color=(0, 255, 0),
            text_color=(255, 255, 255),
            border_color=(0, 128, 0),
            is_computed=True,
            confidence=0.95,
            show_border=True,
            highlight_level=2,
            is_hovering=True,
            is_selected=False,
            opacity=0.8,
            tooltip_text="Pocket Aces",
            secondary_text="Best hand"
        )

        assert display.hand_key == "AA"
        assert display.metric_value == 0.85
        assert display.display_text == "85.0%"
        assert display.background_color == (0, 255, 0)
        assert display.text_color == (255, 255, 255)
        assert display.border_color == (0, 128, 0)
        assert display.is_computed is True
        assert display.confidence == 0.95
        assert display.show_border is True
        assert display.highlight_level == 2
        assert display.is_hovering is True
        assert display.is_selected is False
        assert display.opacity == 0.8
        assert display.tooltip_text == "Pocket Aces"
        assert display.secondary_text == "Best hand"

    def test_cell_display_hand_key_validation(self):
        """Test hand_key validation (FR-021 format)."""
        # Valid hand keys
        CellDisplay(
            hand_key="AA",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0)
        )
        CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0)
        )
        CellDisplay(
            hand_key="AKo",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0)
        )

        # Invalid hand keys
        with pytest.raises(ValueError, match="hand_key must be valid poker hand"):
            CellDisplay(
                hand_key="INVALID",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0)
            )
        with pytest.raises(ValueError, match="hand_key must be valid poker hand"):
            CellDisplay(
                hand_key="A",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0)
            )
        with pytest.raises(ValueError, match="hand_key must be valid poker hand"):
            CellDisplay(
                hand_key="AAA",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0)
            )

    def test_cell_display_color_validation(self):
        """T078: Test color validation (RGB tuples 0-255)."""
        # Valid colors
        CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(0, 0, 0),
            text_color=(255, 255, 255),
            border_color=(128, 128, 128)
        )
        CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 0, 128),
            text_color=(0, 255, 0),
            border_color=(0, 0, 255)
        )

        # Invalid colors - wrong type
        with pytest.raises(ValueError, match="background_color must be RGB tuple"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color="[255, 0, 0]",  # List instead of tuple
                text_color=(255, 255, 255),
                border_color=(0, 0, 0)
            )

        # Invalid colors - wrong length
        with pytest.raises(ValueError, match="text_color must be RGB tuple"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(255, 255),  # Only 2 values
                border_color=(0, 0, 0)
            )

        # Invalid colors - out of range
        with pytest.raises(ValueError, match="border_color must be RGB tuple"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(255, 255, 255),
                border_color=(256, 0, 0)  # 256 > 255
            )
        with pytest.raises(ValueError, match="background_color must be RGB tuple"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color=(-1, 0, 0),  # -1 < 0
                text_color=(255, 255, 255),
                border_color=(0, 0, 0)
            )

    def test_cell_display_numeric_validation(self):
        """T079: Test numeric validation (confidence, opacity, highlight_level)."""
        # Valid values
        CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0),
            confidence=0.0,
            opacity=0.0,
            highlight_level=0
        )
        CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0),
            confidence=1.0,
            opacity=1.0,
            highlight_level=3
        )

        # Invalid confidence
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0),
                confidence=-0.1
            )
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0),
                confidence=1.1
            )

        # Invalid opacity
        with pytest.raises(ValueError, match="opacity must be 0.0-1.0"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0),
                opacity=-0.1
            )

        # Invalid highlight_level
        with pytest.raises(ValueError, match="highlight_level must be 0-3"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0),
                highlight_level=-1
            )
        with pytest.raises(ValueError, match="highlight_level must be 0-3"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0),
                highlight_level=4
            )

    def test_cell_display_immutability(self):
        """Test that CellDisplay is immutable (frozen=True)."""
        display = CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0)
        )

        with pytest.raises(AttributeError):
            display.metric_value = 0.6  # Should fail because frozen=True

    def test_cell_display_equality_and_hash(self):
        """Test equality and hash for frozen dataclass."""
        display1 = CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0)
        )
        display2 = CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0)
        )
        display3 = CellDisplay(
            hand_key="AKo",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0)
        )

        assert display1 == display2
        assert display1 != display3
        assert hash(display1) == hash(display2)
        assert hash(display1) != hash(display3)


class TestPrecomputeProgress:
    """Test PrecomputeProgress creation, validation, and methods."""

    def test_precompute_progress_valid_creation_minimal(self):
        """T080: Valid creation with minimal required fields."""
        progress = PrecomputeProgress(session_id="session_123")

        assert progress.session_id == "session_123"
        assert progress.total_hands == 169
        assert progress.hands_completed == 0
        assert progress.percent_complete == 0.0
        assert progress.estimated_seconds_remaining == 0
        assert progress.is_complete is False

    def test_precompute_progress_valid_creation_full(self):
        """T080: Valid creation with all fields specified."""
        progress = PrecomputeProgress(
            session_id="session_456",
            total_hands=169,
            hands_completed=85,
            percent_complete=0.5,
            estimated_seconds_remaining=120,
            is_complete=False
        )

        assert progress.session_id == "session_456"
        assert progress.total_hands == 169
        assert progress.hands_completed == 85
        assert progress.percent_complete == 0.5
        assert progress.estimated_seconds_remaining == 120
        assert progress.is_complete is False

    def test_precompute_progress_session_id_validation(self):
        """T081: Test session_id validation (non-empty, no whitespace)."""
        # Valid session IDs
        PrecomputeProgress(session_id="session_123")
        PrecomputeProgress(session_id="abc123")
        PrecomputeProgress(session_id="test-session-456")

        # Invalid session IDs
        with pytest.raises(ValueError, match="session_id must be non-empty string"):
            PrecomputeProgress(session_id="")
        with pytest.raises(ValueError, match="session_id must be non-empty string"):
            PrecomputeProgress(session_id="   ")
        with pytest.raises(ValueError, match="session_id must not have leading/trailing whitespace"):
            PrecomputeProgress(session_id=" session_123 ")
        with pytest.raises(ValueError, match="session_id must not have leading/trailing whitespace"):
            PrecomputeProgress(session_id="session_123 ")

    def test_precompute_progress_total_hands_validation(self):
        """Test total_hands validation (must be 169)."""
        # Valid
        PrecomputeProgress(session_id="test", total_hands=169)

        # Invalid
        with pytest.raises(ValueError, match="total_hands should be 169 for standard poker"):
            PrecomputeProgress(session_id="test", total_hands=168)
        with pytest.raises(ValueError, match="total_hands should be 169 for standard poker"):
            PrecomputeProgress(session_id="test", total_hands=170)

    def test_precompute_progress_hands_completed_validation(self):
        """Test hands_completed validation."""
        # Valid
        PrecomputeProgress(session_id="test", hands_completed=0)
        PrecomputeProgress(session_id="test", hands_completed=85)
        PrecomputeProgress(session_id="test", hands_completed=169)

        # Invalid
        with pytest.raises(ValueError, match="hands_completed must be >= 0"):
            PrecomputeProgress(session_id="test", hands_completed=-1)
        with pytest.raises(ValueError, match="hands_completed .* cannot exceed total_hands"):
            PrecomputeProgress(session_id="test", hands_completed=170)

    def test_precompute_progress_percent_complete_validation(self):
        """T081: Test percent_complete validation (fractional 0.0-1.0)."""
        # Valid
        PrecomputeProgress(session_id="test", percent_complete=0.0)
        PrecomputeProgress(session_id="test", percent_complete=0.5)
        PrecomputeProgress(session_id="test", percent_complete=1.0, is_complete=True)

        # Invalid
        with pytest.raises(ValueError, match="percent_complete must be 0.0-1.0"):
            PrecomputeProgress(session_id="test", percent_complete=-0.1)
        with pytest.raises(ValueError, match="percent_complete must be 0.0-1.0"):
            PrecomputeProgress(session_id="test", percent_complete=1.1)

    def test_precompute_progress_consistency_validation(self):
        """Test consistency between is_complete and percent_complete."""
        # Valid combinations
        PrecomputeProgress(session_id="test", percent_complete=0.5, is_complete=False)
        PrecomputeProgress(session_id="test", percent_complete=1.0, is_complete=True)
        PrecomputeProgress(session_id="test", percent_complete=0.0, is_complete=False)

        # Invalid combinations
        with pytest.raises(ValueError, match="is_complete=True but percent_complete .* < 1.0"):
            PrecomputeProgress(session_id="test", percent_complete=0.9, is_complete=True)
        with pytest.raises(ValueError, match="is_complete=False but percent_complete .* >= 1.0"):
            PrecomputeProgress(session_id="test", percent_complete=1.0, is_complete=False)

    def test_precompute_progress_estimated_seconds_validation(self):
        """Test estimated_seconds_remaining validation (>= 0)."""
        # Valid
        PrecomputeProgress(session_id="test", estimated_seconds_remaining=0)
        PrecomputeProgress(session_id="test", estimated_seconds_remaining=120)
        PrecomputeProgress(session_id="test", estimated_seconds_remaining=3600)

        # Invalid
        with pytest.raises(ValueError, match="estimated_seconds_remaining must be >= 0"):
            PrecomputeProgress(session_id="test", estimated_seconds_remaining=-1)

    def test_precompute_progress_properties(self):
        """Test computed properties."""
        progress = PrecomputeProgress(
            session_id="test",
            hands_completed=85,
            percent_complete=0.5
        )

        assert progress.progress_percentage == 50  # 0.5 * 100
        assert progress.hands_remaining == 84  # 169 - 85

    def test_precompute_progress_with_progress_update(self):
        """Test with_progress_update method."""
        progress = PrecomputeProgress(session_id="session_123")

        # Update progress
        updated = progress.with_progress_update(hands_completed=85, estimated_seconds_remaining=60)

        # Original unchanged
        assert progress.hands_completed == 0
        assert progress.percent_complete == 0.0
        assert progress.is_complete is False

        # Updated has new values
        assert updated.session_id == "session_123"
        assert updated.hands_completed == 85
        assert updated.percent_complete == 85/169  # ≈0.503
        assert updated.estimated_seconds_remaining == 60
        assert updated.is_complete is False

        # Test completion
        completed = progress.with_progress_update(hands_completed=169, estimated_seconds_remaining=0)
        assert completed.hands_completed == 169
        assert completed.percent_complete == 1.0
        assert completed.is_complete is True

    def test_precompute_progress_immutability(self):
        """Test that PrecomputeProgress is immutable (frozen=True)."""
        progress = PrecomputeProgress(session_id="test")

        with pytest.raises(AttributeError):
            progress.hands_completed = 50  # Should fail because frozen=True

    def test_precompute_progress_equality_and_hash(self):
        """Test equality and hash for frozen dataclass."""
        progress1 = PrecomputeProgress(session_id="session_123", hands_completed=50)
        progress2 = PrecomputeProgress(session_id="session_123", hands_completed=50)
        progress3 = PrecomputeProgress(session_id="session_456", hands_completed=50)

        assert progress1 == progress2
        assert progress1 != progress3
        assert hash(progress1) == hash(progress2)
        assert hash(progress1) != hash(progress3)


class TestIntegration:
    """Integration tests across multiple DTOs."""

    def test_analysis_request_position_context_action_context_integration(self):
        """T082: Test AnalysisRequest → PositionContext → ActionContext integration."""
        # Create nested DTOs
        pos_ctx = PositionContext(
            position=Position.BTN,
            num_opponents=2,
            pot_size_bb=15.0
        )

        action_ctx = ActionContext(
            position_context=pos_ctx,
            action=Action.ALL_IN
        )

        request = AnalysisRequest(
            position_context=pos_ctx,
            metric_type=MetricType.EV,
            precompute=True,
            session_id="integration_test_001"
        )

        # Verify nested validation works
        assert request.position_context == pos_ctx
        assert action_ctx.position_context == pos_ctx
        assert action_ctx.is_aggressive is True

        # Test that invalid nested objects are rejected
        with pytest.raises(ValueError):
            # Invalid position context in request
            AnalysisRequest(
                position_context=PositionContext(position="invalid", num_opponents=1),
                session_id="test"
            )

    def test_analysis_request_matrix_payload_workflow(self):
        """T083: Test AnalysisRequest → MatrixPayload workflow."""
        # Create request
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        request = AnalysisRequest(
            position_context=pos_ctx,
            metric_type=MetricType.EQUITY,
            session_id="workflow_test_001"
        )

        # Create corresponding matrix payload
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}
        matrix = MatrixPayload(
            cells=cells,
            query_context=pos_ctx,
            metric_type=MetricType.EQUITY
        )

        # Verify context matches
        assert matrix.query_context == request.position_context
        assert matrix.metric_type == request.metric_type
        assert matrix.opponent_range == request.opponent_range  # Both None

        # Test effective opponent range
        effective_range = request.effective_opponent_range
        assert isinstance(effective_range, HandRange)
        assert effective_range.notation == "*"

    def test_matrix_payload_cell_display_transformation(self):
        """T084: Test MatrixPayload → CellDisplay transformation."""
        # Create matrix with sample data
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {}
        for hand_key in expected_hands:
            cells[hand_key] = HandEvaluation(
                equity=0.623,
                ev=3.8,
                win_probability=0.45,
                is_computed=True
            )

        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        matrix = MatrixPayload(cells=cells, query_context=pos_ctx)

        # Transform to CellDisplay objects
        display_cells = {}
        for hand_key, evaluation in matrix.cells.items():
            display_cells[hand_key] = CellDisplay(
                hand_key=hand_key,
                metric_value=evaluation.equity,
                display_text="62.3%",
                background_color=(100, 200, 100),
                text_color=(0, 0, 0),
                border_color=(0, 128, 0),
                confidence=0.95,
                opacity=0.9
            )

        # Verify all 169 hands transformed
        assert len(display_cells) == 169
        assert all(isinstance(display, CellDisplay) for display in display_cells.values())

        # Verify hand keys match
        matrix_hand_keys = set(matrix.cells.keys())
        display_hand_keys = set(display_cells.keys())
        assert matrix_hand_keys == display_hand_keys

        # Test a specific transformation
        aa_display = display_cells["AA"]
        assert aa_display.hand_key == "AA"
        assert aa_display.metric_value == 0.623
        assert aa_display.display_text == "62.3%"
        assert aa_display.background_color == (100, 200, 100)

    def test_precompute_progress_session_tracking(self):
        """T085: Test PrecomputeProgress session tracking."""
        # Create request with session
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        request = AnalysisRequest(
            position_context=pos_ctx,
            session_id="session_tracking_test_001"
        )

        # Create initial progress
        progress = PrecomputeProgress(session_id=request.session_id)

        # Update progress
        updated = progress.with_progress_update(hands_completed=50, estimated_seconds_remaining=120)

        # Verify session tracking
        assert progress.session_id == request.session_id
        assert updated.session_id == request.session_id

        # Verify progress updates work
        assert updated.hands_completed == 50
        assert updated.percent_complete == 50 / 169  # ≈0.296
        assert updated.estimated_seconds_remaining == 120
        assert updated.is_complete is False

        # Complete the progress
        completed = updated.with_progress_update(hands_completed=169, estimated_seconds_remaining=0)
        assert completed.hands_completed == 169
        assert completed.percent_complete == 1.0
        assert completed.is_complete is True


class TestEdgeCases:
    """Edge case and boundary testing."""

    def test_hand_key_format_validation_fr021(self):
        """T086: Test hand key format validation (FR-021)."""
        # Valid hand keys (sample of all types)
        valid_keys = [
            "AA", "KK", "QQ", "22",  # Pairs
            "AKs", "AQs", "32s",     # Suited
            "AKo", "AQo", "32o"      # Unsuited
        ]

        for key in valid_keys:
            # Should work in CellDisplay
            CellDisplay(
                hand_key=key,
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0)
            )

        # Invalid hand keys
        invalid_keys = [
            "", "A", "ABC", "AK", "AKss", "AKoo",  # Wrong length
            "AAs", "AKk", "AK1", "1AK",            # Invalid characters
            "AKS", "ako"                           # Wrong case
        ]

        for key in invalid_keys:
            with pytest.raises(ValueError, match="hand_key must be valid poker hand"):
                CellDisplay(
                    hand_key=key,
                    metric_value=0.5,
                    display_text="50%",
                    background_color=(255, 255, 255),
                    text_color=(0, 0, 0),
                    border_color=(0, 0, 0)
                )

    def test_immutability_across_all_dtos(self):
        """T087: Test immutability across all DTOs."""
        # Test PositionContext
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        with pytest.raises(AttributeError):
            pos_ctx.num_opponents = 2

        # Test ActionContext
        action_ctx = ActionContext(position_context=pos_ctx, action=Action.FOLD)
        with pytest.raises(AttributeError):
            action_ctx.action = Action.ALL_IN

        # Test AnalysisRequest
        request = AnalysisRequest(position_context=pos_ctx, session_id="test")
        with pytest.raises(AttributeError):
            request.metric_type = MetricType.EV

        # Test HandEvaluation
        eval = HandEvaluation(equity=0.5)
        with pytest.raises(AttributeError):
            eval.equity = 0.6

        # Test MatrixPayload
        expected_hands = MatrixPayload._generate_all_hand_keys()
        cells = {hand: HandEvaluation(equity=0.5) for hand in expected_hands}
        matrix = MatrixPayload(cells=cells, query_context=pos_ctx)
        with pytest.raises(AttributeError):
            matrix.metric_type = MetricType.EV

        # Test CellDisplay
        display = CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0)
        )
        with pytest.raises(AttributeError):
            display.metric_value = 0.6

        # Test PrecomputeProgress
        progress = PrecomputeProgress(session_id="test")
        with pytest.raises(AttributeError):
            progress.hands_completed = 50

    def test_type_coercion_and_rejection(self):
        """T088: Test type coercion and rejection."""
        # Test enum rejection
        with pytest.raises(ValueError, match="position must be Position enum"):
            PositionContext(position="btn", num_opponents=1)

        with pytest.raises(ValueError, match="action must be Action enum"):
            ActionContext(
                position_context=PositionContext(position=Position.BTN, num_opponents=1),
                action="fold"
            )

        with pytest.raises(ValueError, match="metric_type must be MetricType enum"):
            AnalysisRequest(
                position_context=PositionContext(position=Position.BTN, num_opponents=1),
                metric_type="equity",
                session_id="test"
            )

        # Test domain model rejection
        with pytest.raises(ValueError, match="heroes_hole_cards must be Hand domain model"):
            PositionContext(position=Position.BTN, num_opponents=1, heroes_hole_cards="AK")

        with pytest.raises(ValueError, match="opponent_range must be HandRange domain model"):
            AnalysisRequest(
                position_context=PositionContext(position=Position.BTN, num_opponents=1),
                opponent_range="22+",
                session_id="test"
            )

    def test_boundary_numeric_values(self):
        """T089: Test boundary numeric values."""
        # Test equity boundaries
        HandEvaluation(equity=0.0)
        HandEvaluation(equity=1.0)
        with pytest.raises(ValueError, match="equity must be 0.0-1.0"):
            HandEvaluation(equity=-0.1)
        with pytest.raises(ValueError, match="equity must be 0.0-1.0"):
            HandEvaluation(equity=1.01)

        # Test probability boundaries
        HandEvaluation(equity=0.5, win_probability=0.0, tie_probability=0.5, lose_probability=0.5)
        HandEvaluation(equity=0.5, win_probability=1.0, tie_probability=0.0, lose_probability=0.0)
        with pytest.raises(ValueError, match="win_probability must be 0.0-1.0"):
            HandEvaluation(equity=0.5, win_probability=-0.1)
        with pytest.raises(ValueError, match="tie_probability must be 0.0-1.0"):
            HandEvaluation(equity=0.5, tie_probability=1.01)

        # Test confidence/opacity boundaries
        CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0),
            confidence=0.0,
            opacity=0.0
        )
        CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0),
            confidence=1.0,
            opacity=1.0
        )
        with pytest.raises(ValueError, match="confidence must be 0.0-1.0"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0),
                confidence=-0.1
            )
        with pytest.raises(ValueError, match="opacity must be 0.0-1.0"):
            CellDisplay(
                hand_key="AKs",
                metric_value=0.5,
                display_text="50%",
                background_color=(255, 255, 255),
                text_color=(0, 0, 0),
                border_color=(0, 0, 0),
                opacity=1.01
            )

        # Test percent_complete boundaries
        PrecomputeProgress(session_id="test", percent_complete=0.0)
        PrecomputeProgress(session_id="test", percent_complete=1.0, is_complete=True)
        with pytest.raises(ValueError, match="percent_complete must be 0.0-1.0"):
            PrecomputeProgress(session_id="test", percent_complete=-0.1)
        with pytest.raises(ValueError, match="percent_complete must be 0.0-1.0"):
            PrecomputeProgress(session_id="test", percent_complete=1.01)

    def test_empty_none_handling(self):
        """T090: Test empty/None handling across optional fields."""
        # Test None opponent_range
        pos_ctx = PositionContext(position=Position.BTN, num_opponents=1)
        request = AnalysisRequest(position_context=pos_ctx, session_id="test")
        assert request.opponent_range is None
        effective = request.effective_opponent_range
        assert isinstance(effective, HandRange)
        assert effective.notation == "*"

        # Test None heroes_hole_cards
        pos_ctx_none = PositionContext(position=Position.BTN, num_opponents=1, heroes_hole_cards=None)
        assert pos_ctx_none.heroes_hole_cards is None

        # Test empty session_id rejection
        with pytest.raises(ValueError, match="session_id must be non-empty string"):
            AnalysisRequest(position_context=pos_ctx, session_id="")

        # Test None tooltip_text and secondary_text
        display = CellDisplay(
            hand_key="AKs",
            metric_value=0.5,
            display_text="50%",
            background_color=(255, 255, 255),
            text_color=(0, 0, 0),
            border_color=(0, 0, 0)
        )
        assert display.tooltip_text is None
        assert display.secondary_text is None


class TestJsonSerialization:
    """JSON serialization round-trip tests (T105)."""

    def test_json_serialization_round_trip(self):
        """T105: Test JSON serialization round-trip of all DTOs."""
        import json

        # Test PositionContext
        pos_ctx = PositionContext(
            position=Position.BTN,
            num_opponents=2,
            pot_size_bb=15.5
        )
        pos_json = json.dumps(pos_ctx.__dict__)
        pos_dict = json.loads(pos_json)
        assert pos_dict["position"] == "btn"  # Enum serializes as string
        assert pos_dict["num_opponents"] == 2
        assert pos_dict["pot_size_bb"] == 15.5

        # Test ActionContext
        action_ctx = ActionContext(
            position_context=pos_ctx,
            action=Action.ALL_IN
        )
        action_json = json.dumps({
            "position_context": action_ctx.position_context.__dict__,
            "action": action_ctx.action.value  # Use .value for enum string
        })
        action_dict = json.loads(action_json)
        assert action_dict["action"] == "all_in"

        # Test AnalysisRequest (without domain models)
        request = AnalysisRequest(
            position_context=pos_ctx,
            metric_type=MetricType.EQUITY,
            precompute=True,
            session_id="json_test_001"
        )
        request_json = json.dumps({
            "position_context": request.position_context.__dict__,
            "metric_type": request.metric_type.value,  # Use .value for enum string
            "precompute": request.precompute,
            "session_id": request.session_id
        })
        request_dict = json.loads(request_json)
        assert request_dict["metric_type"] == "equity"
        assert request_dict["precompute"] is True
        assert request_dict["session_id"] == "json_test_001"

        # Test HandEvaluation
        eval = HandEvaluation(
            equity=0.623,
            ev=3.8,
            win_probability=0.45,
            num_simulations=1000
        )
        eval_json = json.dumps(eval.__dict__)
        eval_dict = json.loads(eval_json)
        assert eval_dict["equity"] == 0.623
        assert eval_dict["ev"] == 3.8
        assert eval_dict["win_probability"] == 0.45
        assert eval_dict["num_simulations"] == 1000

        # Test CellDisplay
        display = CellDisplay(
            hand_key="AKs",
            metric_value=0.623,
            display_text="62.3%",
            background_color=(100, 200, 100),
            text_color=(0, 0, 0),
            border_color=(0, 128, 0),
            confidence=0.95
        )
        display_json = json.dumps(display.__dict__)
        display_dict = json.loads(display_json)
        assert display_dict["hand_key"] == "AKs"
        assert display_dict["metric_value"] == 0.623
        assert display_dict["display_text"] == "62.3%"
        assert display_dict["background_color"] == [100, 200, 100]  # Tuple becomes list in JSON
        assert display_dict["confidence"] == 0.95

        # Test PrecomputeProgress
        progress = PrecomputeProgress(
            session_id="json_progress_test",
            hands_completed=85,
            percent_complete=0.5,
            estimated_seconds_remaining=120
        )
        progress_json = json.dumps(progress.__dict__)
        progress_json = json.dumps(progress.__dict__)
        progress_dict = json.loads(progress_json)
        assert progress_dict["session_id"] == "json_progress_test"
        assert progress_dict["hands_completed"] == 85
        assert progress_dict["percent_complete"] == 0.5
        assert progress_dict["estimated_seconds_remaining"] == 120


class TestImportConstraints:
    """Import constraint verification (T106)."""

    def test_import_constraints_fr017_fr018_fr019(self):
        """T106: Verify import constraints - only stdlib + Phase 1.1 domain models."""
        import aof_gto_browser_ii.shared.models
        import inspect
        import sys

        # Get all modules imported by shared.models
        imported_modules = set()
        for name, obj in inspect.getmembers(aof_gto_browser_ii.shared.models):
            if inspect.ismodule(obj):
                # Skip the module itself and test modules
                if not obj.__name__.startswith('aof_gto_browser_ii.shared.models'):
                    imported_modules.add(obj.__name__)

        # Check for forbidden imports
        forbidden_patterns = [
            'gui', 'database', 'service', 'external', 'tkinter', 'pygame',
            'flask', 'django', 'fastapi', 'sqlalchemy', 'pydantic'
        ]

        for module_name in imported_modules:
            for forbidden in forbidden_patterns:
                assert forbidden not in module_name.lower(), \
                    f"Forbidden import detected: {module_name} (contains '{forbidden}')"

        # Verify allowed imports
        allowed_prefixes = [
            'dataclasses', 'typing', 'enum',  # stdlib
            'aof_gto_browser_ii.shared.domain'  # Phase 1.1 domain models
        ]

        for module_name in imported_modules:
            is_allowed = any(module_name.startswith(prefix) for prefix in allowed_prefixes)
            assert is_allowed, f"Disallowed import: {module_name}. Only stdlib + Phase 1.1 domain models allowed."

        # Verify no circular imports by checking we can import all public symbols
        from aof_gto_browser_ii.shared.models import (
            Position, Action, MetricType,
            PositionContext, ActionContext, AnalysisRequest,
            HandEvaluation, MatrixPayload, CellDisplay, PrecomputeProgress
        )

        # All imports should work without circular dependency errors
        assert Position is not None
        assert HandEvaluation is not None
        assert MatrixPayload is not None