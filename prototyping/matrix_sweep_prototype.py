#!/usr/bin/env python3
"""
Prototype: Phase 2 - Matrix Sweep

For each of the 169 canonical hand types, expands to all specific dealt
combos and runs SIMS_PER_COMBO Monte Carlo simulations with a fixed
NUM_OPPONENTS count. Writes raw GameState rows (GameStates-first), then
aggregates into: Simulation -> HandMatrix -> MatrixCell -> AggregatedMetric.

Run from project root:
    python prototyping/matrix_sweep_prototype.py
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.database.persistence.database import DatabasePersistenceStrategy
from hopilot.db import initialize_database, get_session
from hopilot.models.base import BaseModel
from hopilot.models.aggregated_metric import AggregatedMetric
from hopilot.models.game_state import GameState
from hopilot.models.hand_matrix import HandMatrix
from hopilot.models.matrix_cell import MatrixCell
from hopilot.models.player import Player
from hopilot.models.simulation import Simulation
from hopilot.hand_range import HandRange

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_URL = "sqlite:///python/hopilot/data/normalized_poker.db"
NUM_OPPONENTS = 1    # Fixed for this scenario — no randomisation across the run
SIMS_PER_COMBO = 10  # Simulations per specific dealt combo

# Standard 13x13 matrix rank ordering (index 0 = Ace = highest)
MATRIX_RANKS = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']


# ---------------------------------------------------------------------------
# Matrix helpers
# ---------------------------------------------------------------------------

def cell_shorthand(row: int, col: int) -> str:
    """Return canonical hand type for matrix position (row, col)."""
    r1, r2 = MATRIX_RANKS[row], MATRIX_RANKS[col]
    if row == col:
        return f"{r1}{r2}"        # diagonal  → pair e.g. "AA"
    elif row < col:
        return f"{r1}{r2}s"       # upper-right → suited e.g. "AKs"
    else:
        return f"{r2}{r1}o"       # lower-left  → offsuit e.g. "AKo"
        #   col is the higher-rank index (smaller) → MATRIX_RANKS[col] first


def hole_cards_to_cell(hole_cards_str: str) -> tuple:
    """
    Map stored hole_cards string back to (row, col, shorthand).

    Player.hole_cards is stored as 4-char concatenation (no separator),
    e.g. 'AsKs', 'AsKh', 'AsAc'.  See Player._is_valid_hole_cards.

    Examples:
        "AsKs" -> (0, 1, "AKs")
        "AsKh" -> (1, 0, "AKo")
        "AsAc" -> (0, 0, "AA")
    """
    if len(hole_cards_str) != 4:
        raise ValueError(f"Expected 4-char hole_cards, got {len(hole_cards_str)!r}: {hole_cards_str!r}")
    c1, c2 = hole_cards_str[:2], hole_cards_str[2:]
    r1, s1 = c1[0], c1[1]
    r2, s2 = c2[0], c2[1]
    i1 = MATRIX_RANKS.index(r1)
    i2 = MATRIX_RANKS.index(r2)

    # Normalise so i1 is the higher-rank index (lower number)
    if i1 > i2:
        r1, s1, i1, r2, s2, i2 = r2, s2, i2, r1, s1, i1

    if i1 == i2:      # pair
        return i1, i2, f"{r1}{r2}"
    elif s1 == s2:    # suited
        return i1, i2, f"{r1}{r2}s"
    else:             # offsuit — row is the lower-rank index (i2 > i1)
        return i2, i1, f"{r1}{r2}o"


# ---------------------------------------------------------------------------
# Phase A: Sweep
# ---------------------------------------------------------------------------

def run_sweep(analyzer: PokerAnalyzer, persistence: DatabasePersistenceStrategy) -> datetime:
    """
    Iterate all 169 cells, expand to specific combos, run SIMS_PER_COMBO sims
    per combo.  Writes raw GameState rows via persistence.

    Returns:
        sweep_start datetime (UTC) for Simulation record.
    """
    sweep_start = datetime.utcnow()
    print(f"\nPhase A: Sweep — 169 cells × combos × {SIMS_PER_COMBO} sims, {NUM_OPPONENTS} opponent(s)")
    print("-" * 70)

    total_combos = 0
    total_sims = 0
    failed_combos = 0

    for row in range(13):
        for col in range(13):
            shorthand = cell_shorthand(row, col)
            # parse_shorthand returns List[Tuple[str, str]]
            # NOTE: _expand_pair returns 12 ordered combos for 6 unique pairs —
            # this doubles pair sims but equity averages correctly; acceptable for prototype.
            combos = HandRange.parse_shorthand(shorthand)

            for card1, card2 in combos:
                result = analyzer.calculate_odds_random_opponents(
                    hero_hole_cards=[card1, card2],
                    board_cards=[],
                    num_opponents=NUM_OPPONENTS,
                    num_simulations=SIMS_PER_COMBO,
                    persistence=persistence,
                )
                if result and result.get('valid_simulations', 0) > 0:
                    total_sims += result['valid_simulations']
                else:
                    failed_combos += 1
                total_combos += 1

        print(f"  Row {MATRIX_RANKS[row]}: 13 cells done")

    sweep_end = datetime.utcnow()
    elapsed = (sweep_end - sweep_start).total_seconds()
    print(
        f"\nSweep done: {total_combos} combos | {total_sims} valid sims | "
        f"{failed_combos} failed | {elapsed:.1f}s"
    )
    return sweep_start, sweep_end


# ---------------------------------------------------------------------------
# Phase B: Aggregate
# ---------------------------------------------------------------------------

def run_aggregation(gs_max_id_before: int, sweep_start: datetime, sweep_end: datetime) -> None:
    """
    Read newly inserted GameState + hero Player rows, group by canonical hand
    type, compute equity, then write Simulation/HandMatrix/MatrixCell/AggregatedMetric.
    """
    print(f"\nPhase B: Aggregate — grouping into MatrixCell + AggregatedMetric")
    print("-" * 70)

    session = get_session()

    new_game_states = (
        session.query(GameState)
        .filter(GameState.id > gs_max_id_before)
        .all()
    )
    print(f"  New GameState rows: {len(new_game_states)}")

    gs_outcome = {gs.id: gs.outcome for gs in new_game_states}
    new_gs_ids = [gs.id for gs in new_game_states]

    hero_players = (
        session.query(Player)
        .filter(Player.game_state_id.in_(new_gs_ids), Player.is_hero == True)
        .all()
    )

    # Accumulate wins/ties/total per canonical hand type
    cell_stats: dict = {}
    for player in hero_players:
        try:
            row, col, shorthand = hole_cards_to_cell(player.hole_cards)
        except (ValueError, IndexError) as e:
            print(f"  WARNING: Could not map hole_cards={player.hole_cards!r}: {e}")
            continue

        if shorthand not in cell_stats:
            cell_stats[shorthand] = {'row': row, 'col': col, 'wins': 0, 'ties': 0, 'total': 0}

        outcome = gs_outcome.get(player.game_state_id, '')
        cell_stats[shorthand]['total'] += 1
        if outcome == 'WIN':
            cell_stats[shorthand]['wins'] += 1
        elif outcome == 'TIE':
            cell_stats[shorthand]['ties'] += 1

    print(f"  Unique cells covered: {len(cell_stats)} / 169")

    # Create Simulation
    sim = Simulation(
        name=f"matrix_sweep_{sweep_start.strftime('%Y%m%d_%H%M%S')}",
        start_timestamp=sweep_start,
        end_timestamp=sweep_end,
        parameters={
            'num_simulations': SIMS_PER_COMBO,
            'matrix_size': '13x13',
            'game_type': 'nlhe',
            'num_opponents': NUM_OPPONENTS,
        },
    )
    session.add(sim)
    session.flush()

    # Create HandMatrix
    hand_matrix = HandMatrix(simulation_id=sim.id, matrix_size='13x13')
    session.add(hand_matrix)
    session.flush()

    # Create MatrixCell + AggregatedMetric per cell
    cells_written = 0
    for shorthand, stats in cell_stats.items():
        wins = stats['wins']
        ties = stats['ties']
        total = stats['total']
        equity = (wins + 0.5 * ties) / total if total > 0 else None
        win_probability = wins / total if total > 0 else None

        cell = MatrixCell(
            matrix_id=hand_matrix.id,
            row_index=stats['row'],
            col_index=stats['col'],
            hand_combination=f"{shorthand} vs {NUM_OPPONENTS}opp",
        )
        session.add(cell)
        session.flush()

        metric = AggregatedMetric(
            cell_id=cell.id,
            equity=equity,
            win_probability=win_probability,
            last_updated=datetime.utcnow().isoformat(),
        )
        session.add(metric)
        cells_written += 1

    session.commit()
    print(f"  MatrixCells + AggregatedMetrics written: {cells_written}")
    print(f"  Simulation ID: {sim.id} | HandMatrix ID: {hand_matrix.id}")

    # Print top 10 cells by equity
    top = (
        session.query(MatrixCell, AggregatedMetric)
        .join(AggregatedMetric, MatrixCell.id == AggregatedMetric.cell_id)
        .filter(MatrixCell.matrix_id == hand_matrix.id)
        .order_by(AggregatedMetric.equity.desc())
        .limit(10)
        .all()
    )
    print(f"\n  Top 10 cells by equity ({NUM_OPPONENTS} opp, {SIMS_PER_COMBO} sims/combo):")
    print(f"  {'Hand':<10} {'Equity':>8} {'WinProb':>8} {'Sims':>6}")
    print(f"  {'-'*10} {'-'*8} {'-'*8} {'-'*6}")
    for cell, metric in top:
        hand_label = cell.hand_combination.split(' vs ')[0]
        eq = float(metric.equity) if metric.equity is not None else 0.0
        wp = float(metric.win_probability) if metric.win_probability is not None else 0.0
        sims = cell_stats.get(hand_label, {}).get('total', '?')
        print(f"  {hand_label:<10} {eq:>8.4f} {wp:>8.4f} {sims:>6}")

    session.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    initialize_database(DB_URL)

    from hopilot.db import _engine
    BaseModel.metadata.create_all(_engine)
    print(f"Database: {DB_URL}")

    # Snapshot max game_state id before the sweep for delta-based reads
    setup_session = get_session()
    row = setup_session.query(GameState.id).order_by(GameState.id.desc()).first()
    gs_max_id_before = row[0] if row else 0
    setup_session.close()

    persistence = DatabasePersistenceStrategy()
    analyzer = PokerAnalyzer()

    sweep_start, sweep_end = run_sweep(analyzer, persistence)

    # Release the persistence session before opening a new one for aggregation
    persistence.close()

    run_aggregation(gs_max_id_before, sweep_start, sweep_end)


if __name__ == "__main__":
    main()
