"""
Incremental aggregation service for convergence tracking.

Processes game states in batches while emitting convergence events,
enabling real-time monitoring of metric convergence during aggregation.
"""

from datetime import datetime
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import selectinload

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    tqdm = None

from hopilot.database import DatabaseConnection
from hopilot.hand_range import HandRange
from hopilot.gto.aof_hand_matrix import hand_key_from_index, hand_coordinates_from_hole_cards
from hopilot.gto.convergence_events import ConvergenceData, ConvergenceEventEmitter
from hopilot.logging_config import get_logger, timing_decorator
from hopilot.models.game_state import GameState
from hopilot.models.player import Player
from hopilot.poker_analyzer import PokerAnalyzer

logger = get_logger(__name__)


# Cache for hand range expansions to avoid repeated parsing
@lru_cache(maxsize=128)
def _cached_parse_shorthand(hand_key: str) -> Tuple[Tuple[str, str], ...]:
    """Cache hand range parsing results."""
    return tuple(HandRange.parse_shorthand(hand_key))


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
        emit_interval: int = 100,
        default_batch_size: int = 1000,
        bb: float = 1.0
    ) -> None:
        """
        Initialize incremental aggregation service.

        Args:
            db_connection: Database connection for game state access
            poker_analyzer: Poker analyzer for metric calculations
            event_emitter: Optional event emitter for convergence tracking
            emit_interval: Sample count interval for convergence emissions
            default_batch_size: Default batch size for database queries            bb: Big blind amount for posted blind adjustments        """
        self.db_connection = db_connection
        self.poker_analyzer = poker_analyzer
        self.event_emitter = event_emitter or ConvergenceEventEmitter()
        self.emit_interval = emit_interval
        self.default_batch_size = default_batch_size
        
        # Log connection pool info for monitoring
        engine = db_connection._engine
        if engine:
            pool = engine.pool
            logger.debug(f"Database connection pool: {type(pool).__name__}, size={getattr(pool, 'size', 'N/A')}")

    def aggregate_cell_incremental(
        self,
        cell_id: int,
        hand_key: str,
        simulation_id: int,
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
            bet_amount: Bet amount for the simulation
            raw_start: Start ID of raw game states
            raw_end: End ID of raw game states
            batch_size: Number of game states to process per batch (default: default_batch_size)

        Returns:
            Final aggregated metrics for the cell
        """
        logger.info(f"Starting incremental aggregation for cell {cell_id} ({hand_key}), simulation {simulation_id}")

        # Precompute hand range expansion once for the entire operation
        hand_tuples = _cached_parse_shorthand(hand_key)
        hole_cards_list = ["".join(tup) for tup in hand_tuples]

        if batch_size is None:
            batch_size = self.default_batch_size

        total_samples = 0
        running_stats = {
            'wins': 0,
            'ties': 0,
            'total': 0,
            'ev_sum': 0.0,
        }

        progress_bar = None
        if tqdm is not None:
            progress_bar = tqdm(
                desc=f"Aggregating cell {cell_id}:{hand_key}",
                unit="game",
                dynamic_ncols=True,
            )

        # Process game states in batches
        last_id = raw_start - 1  # Start before the first ID
        try:
            while True:
                # Get next batch of game states
                game_states = self._get_game_states_batch(hole_cards_list, raw_start, raw_end, batch_size, last_id)
                if not game_states:
                    break

                # Process batch and update running statistics
                batch_stats = self._process_batch(game_states, bet_amount)
                running_stats = self._update_running_stats(running_stats, batch_stats)
                total_samples += len(game_states)
                
                # Update last_id for cursor-based pagination
                last_id = game_states[-1].id

                if progress_bar is not None:
                    progress_bar.update(len(game_states))

                # Log batch processing statistics
                logger.info(f"Processed batch of {len(game_states)} games (total: {total_samples}) for cell {cell_id}")

                # Emit convergence event if interval reached
                if total_samples % self.emit_interval == 0:
                    self._emit_convergence_update(cell_id, simulation_id, total_samples, running_stats, bet_amount)

        finally:
            if progress_bar is not None:
                progress_bar.close()

        # Calculate final metrics
        final_metrics = self._calculate_final_metrics(running_stats, bet_amount)
        final_metrics['sample_count'] = total_samples

        # Log performance summary
        total_batches = (total_samples + batch_size - 1) // batch_size  # Ceiling division
        logger.info(f"Performance summary: {total_samples} samples processed in {total_batches} batches "
                   f"(avg {total_samples/total_batches:.1f} samples/batch)")

        return final_metrics

    @timing_decorator
    def _get_game_states_batch(
        self,
        hole_cards_list: List[str],
        raw_start: int,
        raw_end: int,
        batch_size: int,
        last_id: int
    ) -> List[GameState]:
        """
        Get a batch of game states for the specified hand and run range.
        Uses database-level filtering for Hero hole cards to ensure all hands are found.
        Uses cursor-based pagination for better performance.
        """
        with self.db_connection.session_scope() as session:
            # Use subquery for better query planning and performance
            # First get game_state_ids that match our criteria
            subquery = session.query(Player.game_state_id)\
                .filter(
                    Player.is_hero == True,
                    Player.hole_cards.in_(hole_cards_list)
                )\
                .subquery()

            # Then query GameState with cursor-based pagination
            query = session.query(GameState)\
                .filter(
                    GameState.id >= raw_start,
                    GameState.id <= raw_end,
                    GameState.id > last_id,  # Cursor-based pagination
                    GameState.id.in_(session.query(subquery.c.game_state_id))
                )\
                .options(selectinload(GameState.players))\
                .order_by(GameState.id)\
                .limit(batch_size)
            
            game_states = query.all()
            
            if game_states:
                logger.debug(f"Found {len(game_states)} matches starting after ID {last_id}")

            return game_states

    @timing_decorator
    def _process_batch(
        self,
        game_states: List[GameState],
        bet_amount: float
    ) -> Dict[str, float]:
        """
        Process a batch of game states and calculate win/tie statistics.

        Args:
            game_states: List of game states to process
            bet_amount: Bet amount for calculations

        Returns:
            Dictionary with wins, ties, total count, and EV sum
        """
        wins = 0
        ties = 0
        ev_sum = 0.0

        for game_state in game_states:
            outcome = (game_state.outcome or "").strip().upper()
            game_state_pot = float(game_state.pot_size)
            if outcome == "WIN":
                wins += 1
                ev_sum += game_state_pot
            elif outcome == "TIE":
                ties += 1
                ev_sum += (game_state_pot + bet_amount) / 2.0 - bet_amount
            else:
                ev_sum -= bet_amount

        return {
            'wins': wins,
            'ties': ties,
            'total': len(game_states),
            'ev_sum': ev_sum
        }

    def _update_running_stats(
        self,
        current_stats: Dict[str, float],
        batch_stats: Dict[str, float]
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
            'total': current_stats['total'] + batch_stats['total'],
            'ev_sum': current_stats['ev_sum'] + batch_stats['ev_sum']
        }

    def _calculate_final_metrics(self, stats: Dict[str, float], bet_amount: float) -> Dict[str, float]:
        """
        Calculate final aggregated metrics from running statistics.

        Args:
            stats: Running statistics
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
        ev = stats['ev_sum'] / total

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
        bet_amount: float
    ) -> None:
        """
        Emit a convergence update event.

        Args:
            cell_id: Matrix cell ID
            simulation_id: Simulation ID
            sample_count: Current sample count
            stats: Current running statistics
            bet_amount: Amount the hero must call or risk
        """
        metrics = self._calculate_final_metrics(stats, bet_amount)
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