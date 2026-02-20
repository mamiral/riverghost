#!/usr/bin/env python3
"""
Simulation convergence analysis script.
Runs Monte Carlo simulations for a fixed hand matchup and records
win probability estimates at regular intervals.
"""

import csv
import sys
import os
import time
from typing import List, Dict, Optional

# Add the python directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "python"))

from hopilot.poker_analyzer import PokerAnalyzer


def run_convergence_analysis(
    hero_hole_cards: List[str],
    villain_hole_cards: List[str],
    max_simulations: int = 250000,
    checkpoint_interval: int = 1000,
    output_file: str = "simulation_convergence.csv"
) -> None:
    """
    Run Monte Carlo simulations and record win probability at regular intervals.

    Args:
        hero_hole_cards: Hero's 2 hole cards (e.g., ['As', 'Kh'])
        villain_hole_cards: Villain's 2 hole cards (e.g., ['Qd', 'Jd'])
        max_simulations: Maximum number of simulations to run
        checkpoint_interval: How often to record results (every N simulations)
        output_file: CSV file to write results to
    """
    print(f"Starting convergence analysis:")
    print(f"  Hero: {hero_hole_cards}")
    print(f"  Villain: {villain_hole_cards}")
    print(f"  Max simulations: {max_simulations}")
    print(f"  Checkpoint interval: {checkpoint_interval}")
    print(f"  Output file: {output_file}")
    print()

    analyzer = PokerAnalyzer()

    # Initialize counters
    total_wins = 0
    total_ties = 0
    total_valid = 0

    # Write CSV header
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'simulations_run',
            'win_probability',
            'tie_probability',
            'loss_probability',
            'total_wins',
            'total_ties',
            'total_valid',
            'timestamp'
        ])

    start_time = time.time()

    # Run simulations in batches
    for batch_start in range(0, max_simulations, checkpoint_interval):
        batch_size = min(checkpoint_interval, max_simulations - batch_start)

        print(f"Running simulations {batch_start + 1} to {batch_start + batch_size}...")

        # Run one batch of simulations
        result = analyzer.calculate_odds(
            hero_hole_cards,
            [villain_hole_cards],
            [],  # No board cards (preflop)
            batch_size
        )

        if result is None:
            print(f"  ERROR: Simulation batch failed!")
            continue

        # Accumulate results
        batch_wins = int(result['win_probability'] * batch_size)
        batch_ties = int(result['tie_probability'] * batch_size)
        batch_valid = batch_size  # Assume all simulations in batch are valid

        total_wins += batch_wins
        total_ties += batch_ties
        total_valid += batch_valid

        # Calculate current probabilities
        current_simulations = batch_start + batch_size
        win_prob = total_wins / total_valid if total_valid > 0 else 0
        tie_prob = total_ties / total_valid if total_valid > 0 else 0
        loss_prob = 1 - win_prob - tie_prob

        # Write to CSV
        with open(output_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                current_simulations,
                f"{win_prob:.6f}",
                f"{tie_prob:.6f}",
                f"{loss_prob:.6f}",
                total_wins,
                total_ties,
                total_valid,
                time.time() - start_time
            ])

        # Progress report
        elapsed = time.time() - start_time
        rate = current_simulations / elapsed if elapsed > 0 else 0
        print(f"  Completed: {current_simulations}/{max_simulations} simulations")
        print(f"  Current win prob: {win_prob:.4f}")
        print(f"  Rate: {rate:.0f} sim/sec")
        print()

    total_elapsed = time.time() - start_time
    print(f"Analysis complete!")
    print(f"  Total time: {total_elapsed:.1f} seconds")
    print(f"  Final win probability: {total_wins/total_valid:.4f}")
    print(f"  Results saved to: {output_file}")


if __name__ == "__main__":
    # Default test case: Aces vs Kings (should be ~82% win rate)
    hero = ["As", "Ad"]      # Pocket Aces
    villain = ["Ks", "Kh"]   # Pocket Kings

    # You can modify these parameters
    run_convergence_analysis(
        hero_hole_cards=hero,
        villain_hole_cards=villain,
        max_simulations=250000,  # Full analysis run
        checkpoint_interval=1000,
        output_file="aces_vs_kings_convergence.csv"
    )