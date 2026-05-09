"""
Incremental aggregation service for convergence tracking.

Processes game states in batches while emitting convergence events,
enabling real-time monitoring of metric convergence during aggregation.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import selectinload

from hopilot.database import DatabaseConnection
from hopilot.hand_range import HandRange
from hopilot.gto.aof_hand_matrix import hand_key_from_index, hand_coordinates_from_hole_cards
from hopilot.gto.convergence_events import ConvergenceData, ConvergenceEventEmitter
from hopilot.logging_config import get_logger
from hopilot.models.game_state import GameState
from hopilot.models.player import Player
from hopilot.poker_analyzer import PokerAnalyzer

logger = get_logger(__name__)


class IncrementalAggregationService:
    """
    Service for incremental aggregation with convergence tracking.

    Processes game states in configurable batches, calculating metrics
    and emitting convergence events at specified intervals.
    """

    def __init__(
        self,
        db_connection: DatabaseConnection,
        poker_analyzer: PokerAnalyzer,
        event_emitter: Optional[ConvergenceEventEmitter] = None,
        emit_interval: int = 100
    ) -> None:
        """
        Initialize incremental aggregation service.

        Args:
            db_connection: Database connection for game state access
            poker_analyzer: Poker analyzer for metric calculations
            event_emitter: Optional event emitter for convergence tracking
            emit_interval: Sample count interval for convergence emissions
        """
        self.db_connection = db_connection
        self.poker_analyzer = poker_analyzer
        self.event_emitter = event_emitter or ConvergenceEventEmitter()
        self.emit_interval = emit_interval

    def aggregate_cell_incremental(
        self,
        cell_id: int,
        hand_key: str,
        simulation_id: int,
        pot_size: float,
        bet_amount: float,
        raw_start: int,
        raw_end: int,
        batch_size: int = None
    ) -> Dict[str, float]:
        """
        Perform incremental aggregation for a matrix cell with convergence tracking.

        Args:
            cell_id: Matrix cell ID to aggregate
            hand_key: Hand combination key (e.g. "AA")
            simulation_id: Simulation ID
            pot_size: Pot size for EV calculations
            bet_amount: Bet amount for the simulation
            raw_start: Start ID of raw game states
            raw_end: End ID of raw game states
            batch_size: Number of game states to process per batch

        Returns:
            Final aggregated metrics for the cell
        """
        logger.info(f"Starting incremental aggregation for cell {cell_id} ({hand_key}), simulation {simulation_id}")

        if batch_size is None:
            batch_size = self.emit_interval

        total_samples = 0
        running_stats = {
            'wins': 0,
            'ties': 0,
            'total': 0,
            'equity': 0.0,
            'ev': 0.0
        }

        # Process game states in batches
        offset = 0
        while True:
            # Get next batch of game states
            game_states = self._get_game_states_batch(hand_key, raw_start, raw_end, batch_size, offset)
            if not game_states:
                break

            # Process batch and update running statistics
            batch_stats = self._process_batch(game_states, pot_size, bet_amount)
            running_stats = self._update_running_stats(running_stats, batch_stats)
            total_samples += len(game_states)
            offset += batch_size

            # Emit convergence event if interval reached
            if total_samples % self.emit_interval == 0:
                self._emit_convergence_update(cell_id, simulation_id, total_samples, running_stats, pot_size, bet_amount)

        # Calculate final metrics
        final_metrics = self._calculate_final_metrics(running_stats, pot_size, bet_amount)
        final_metrics['sample_count'] = total_samples

        logger.info(f"Completed incremental aggregation for cell {cell_id}: {total_samples} samples")
        return final_metrics

    def _get_game_states_batch(
        self,
        hand_key: str,
        raw_start: int,
        raw_end: int,
        batch_size: int,
        offset: int
    ) -> List[GameState]:
        """
        Get a batch of game states for the specified hand and run range.
        Uses database-level filtering for Hero hole cards to ensure all hands are found.
        """
        # Expand hand_key (e.g., 'AKs') to all component hole_cards (e.g., ['AsKs', 'AhKh', ...])
        # HandRange.parse_shorthand returns List[Tuple[str, str]]
        hand_tuples = HandRange.parse_shorthand(hand_key)
        hole_cards_list = ["".join(tup) for tup in hand_tuples]

        with self.db_connection.session_scope() as session:
            # JOIN GameState with Player to filter by hole_cards in SQL
            query = session.query(GameState)\
                .join(Player)\
                .filter(
                    GameState.id >= raw_start,
                    GameState.id <= raw_end,
                    Player.is_hero == True,
                    Player.hole_cards.in_(hole_cards_list)
                )\
                .options(selectinload(GameState.players))\
                .order_by(GameState.id)\
                .offset(offset)\
                .limit(batch_size)
            
            game_states = query.all()
            
            if game_states:
                logger.info(f"Found {len(game_states)} matches for {hand_key} at offset {offset}")

            return game_states

    def _process_batch(
        self,
        game_states: List[GameState],
        pot_size: float,
        bet_amount: float
    ) -> Dict[str, int]:
        """
        Process a batch of game states and calculate win/tie statistics.

        Args:
            game_states: List of game states to process
            pot_size: Pot size for calculations
            bet_amount: Bet amount for calculations

        Returns:
            Dictionary with wins, ties, and total counts
        """
        wins = 0
        ties = 0

        for game_state in game_states:
            outcome = (game_state.outcome or "").strip().upper()
            if outcome == "WIN":
                wins += 1
            elif outcome == "TIE":
                ties += 1

        return {
            'wins': wins,
            'ties': ties,
            'total': len(game_states)
        }

    def _update_running_stats(
        self,
        current_stats: Dict[str, float],
        batch_stats: Dict[str, int]
    ) -> Dict[str, float]:
        """
        Update running statistics with new batch results.

        Args:
            current_stats: Current running statistics
            batch_stats: Statistics from the new batch

        Returns:
            Updated running statistics
        """
        return {
            'wins': current_stats['wins'] + batch_stats['wins'],
            'ties': current_stats['ties'] + batch_stats['ties'],
            'total': current_stats['total'] + batch_stats['total']
        }

    def _calculate_final_metrics(self, stats: Dict[str, float], pot_size: float, bet_amount: float) -> Dict[str, float]:
        """
        Calculate final aggregated metrics from running statistics.

        Args:
            stats: Running statistics
            pot_size: Pot size for EV calculation
            bet_amount: Amount the hero must call or risk

        Returns:
            Final metrics dictionary
        """
        total = stats['total']
        if total == 0:
            return {'equity': 0.0, 'ev': 0.0, 'win_probability': 0.0}

        wins = stats['wins']
        ties = stats['ties']
        equity = (wins + 0.5 * ties) / total
        win_probability = wins / total
        loss_probability = 1.0 - win_probability - (ties / total)

        ev = win_probability * (pot_size + bet_amount) - loss_probability * bet_amount

        return {
            'equity': equity,
            'ev': ev,
            'win_probability': win_probability
        }

    def _emit_convergence_update(
        self,
        cell_id: int,
        simulation_id: int,
        sample_count: int,
        stats: Dict[str, float],
        pot_size: float,
        bet_amount: float
    ) -> None:
        """
        Emit a convergence update event.

        Args:
            cell_id: Matrix cell ID
            simulation_id: Simulation ID
            sample_count: Current sample count
            stats: Current running statistics
            pot_size: Pot size for EV calculation
            bet_amount: Amount the hero must call or risk
        """
        metrics = self._calculate_final_metrics(stats, pot_size, bet_amount)
        equity = metrics['equity']
        ev = metrics['ev']
        win_probability = metrics['win_probability']

        # Create convergence data
        data = ConvergenceData(
            cell_id=cell_id,
            simulation_id=simulation_id,
            sample_count=sample_count,
            equity=equity,
            win_probability=win_probability,
            ev=ev,
            timestamp=datetime.now().isoformat()
        )

        # Emit the event
        self.event_emitter.emit_convergence_update(data)