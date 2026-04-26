#!/usr/bin/env python3
"""
Prototype: Solver writing raw game states to database.

Validates the GameStates-first architecture end-to-end:
  1. Run Monte Carlo simulations for a specific hero hand
  2. Solver writes one GameState row per iteration (not aggregated)
  3. Verify each row has player hole cards, board, outcome, hand strength
  4. Confirm game replay is possible from raw data

Run from project root:
    python prototyping/solver_prototype.py
"""

import sys
import random
from pathlib import Path

# Add python dir to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from hopilot.poker_analyzer import PokerAnalyzer
from hopilot.database.persistence.database import DatabasePersistenceStrategy
from hopilot.db import initialize_database, get_session
from hopilot.models.game_state import GameState
from hopilot.models.player import Player


NUM_SIMULATIONS = 20
HERO_HAND = ['As', 'Ks']
NUM_OPPONENTS_MIN = 1
NUM_OPPONENTS_MAX = 3


def main():
    # Initialize database connection
    db_url = "sqlite:///python/hopilot/data/normalized_poker.db"
    print(f"Initializing database: {db_url}")
    initialize_database(db_url)
    
    # Create all tables from ORM models
    from hopilot.models.base import BaseModel
    from hopilot.db import _engine
    BaseModel.metadata.create_all(_engine)
    print("Database tables created")

    # Snapshot existing row counts so we can validate this run via deltas.
    setup_session = get_session()
    game_states_before = setup_session.query(GameState).count()
    players_before = setup_session.query(Player).count()
    game_state_max_id_before = setup_session.query(GameState.id).order_by(GameState.id.desc()).first()
    player_max_id_before = setup_session.query(Player.id).order_by(Player.id.desc()).first()
    game_state_max_id_before = game_state_max_id_before[0] if game_state_max_id_before else 0
    player_max_id_before = player_max_id_before[0] if player_max_id_before else 0
    setup_session.close()
    
    persistence = DatabasePersistenceStrategy()
    analyzer = PokerAnalyzer()

    print(
        f"Running {NUM_SIMULATIONS} simulations for hero: {HERO_HAND} "
        f"vs random opponents in [{NUM_OPPONENTS_MIN}, {NUM_OPPONENTS_MAX}]"
    )
    print("-" * 60)

    successful_runs = 0
    simulated_opponent_counts = []

    for _ in range(NUM_SIMULATIONS):
        num_opponents = random.randint(NUM_OPPONENTS_MIN, NUM_OPPONENTS_MAX)
        iteration_result = analyzer.calculate_odds_random_opponents(
            hero_hole_cards=HERO_HAND,
            board_cards=[],
            num_opponents=num_opponents,
            num_simulations=1,
            persistence=persistence
        )
        if iteration_result and iteration_result.get('valid_simulations', 0) > 0:
            successful_runs += 1
            simulated_opponent_counts.append(num_opponents)

    # --- Query database to verify raw data was written ---

    assert successful_runs > 0, "No valid simulations completed"

    session = get_session()
    game_states_query = session.query(GameState).all()
    players_query = session.query(Player).all()
    
    # Convert to dict for compatibility with assertion logic
    game_states = {gs.id: {
        'id': gs.id,
        'outcome': gs.outcome,
        'board_cards': gs.board_cards_str.split(',') if gs.board_cards_str else [],
        'pot_size': gs.pot_size,
        'round': gs.round
    } for gs in game_states_query}
    
    players = {p.id: {
        'id': p.id,
        'game_state_id': p.game_state_id,
        'position': p.position,
        'hole_cards': p.hole_cards.split(',') if p.hole_cards else [],
        'stack_size': p.stack_size,
        'is_hero': p.is_hero,
        'final_strength': p.final_strength
    } for p in players_query}

    new_game_states = {
        gs_id: gs for gs_id, gs in game_states.items() if gs_id > game_state_max_id_before
    }
    new_players = {
        p_id: p for p_id, p in players.items() if p_id > player_max_id_before
    }

    game_states_after = len(game_states)
    players_after = len(players)
    game_states_inserted = game_states_after - game_states_before
    players_inserted = players_after - players_before

    assert game_states_inserted == successful_runs, (
        f"Expected {successful_runs} new game states, got {game_states_inserted}"
    )

    # Each game state has players_per_game = 1 hero + opponents for that iteration
    expected_players = sum(1 + opp_count for opp_count in simulated_opponent_counts)
    assert players_inserted == expected_players, (
        f"Expected {expected_players} new player rows, got {players_inserted}"
    )

    # Verify hero is marked correctly in every game
    hero_players = [p for p in new_players.values() if p['is_hero']]
    hero_rows_inserted = players_inserted - sum(opp_count for opp_count in simulated_opponent_counts)
    assert hero_rows_inserted == successful_runs, (
        f"Expected {successful_runs} new hero rows, got {hero_rows_inserted}"
    )

    # Verify hand strength is stored
    assert all(p['final_strength'] is not None for p in new_players.values()), (
        "Some player rows are missing final_strength"
    )

    # Verify all outcomes are valid
    valid_outcomes = {'WIN', 'TIE', 'LOSS'}
    for gs in new_game_states.values():
        assert gs['outcome'] in valid_outcomes, f"Invalid outcome: {gs['outcome']}"

    # Verify board cards are stored (5 cards per game state)
    for gs in new_game_states.values():
        assert len(gs['board_cards']) == 5, (
            f"Expected 5 board cards, got {len(gs['board_cards'])}: {gs['board_cards']}"
        )

    # --- Print summary ---

    wins = sum(1 for gs in new_game_states.values() if gs['outcome'] == 'WIN')
    ties = sum(1 for gs in new_game_states.values() if gs['outcome'] == 'TIE')
    losses = sum(1 for gs in new_game_states.values() if gs['outcome'] == 'LOSS')

    print(f"Game states inserted: {game_states_inserted}")
    print(f"Player rows inserted: {players_inserted}")
    print(f"Game states total:    {game_states_after}")
    print(f"Player rows total:    {players_after}")
    print(f"Opponents requested:  [{NUM_OPPONENTS_MIN}, {NUM_OPPONENTS_MAX}]")
    print(f"Opponents sampled:    {simulated_opponent_counts}")
    print(f"Outcomes:             {wins}W / {ties}T / {losses}L")
    print(f"Equity (from raw):    {wins / len(new_game_states):.3f}")
    print(f"Database file:        {db_url.replace('sqlite:///', '')}")
    print()

    # --- Game replay: show first 3 iterations ---
    print("Game replay (first 3 iterations):")
    print("-" * 60)
    for gs_id in sorted(new_game_states)[:3]:
        gs = new_game_states[gs_id]
        gs_players = [p for p in new_players.values() if p['game_state_id'] == gs_id]
        hero = next(p for p in gs_players if p['is_hero'])
        opponents = [p for p in gs_players if not p['is_hero']]

        print(f"  Game #{gs_id}  outcome={gs['outcome']}")
        print(f"    Board:  {' '.join(gs['board_cards'])}")
        print(f"    Hero:   {hero['hole_cards']}  strength={hero['final_strength']}")
        for opp in opponents:
            print(f"    Opp:    {opp['hole_cards']}  strength={opp['final_strength']}")
        print()

    print("All assertions passed. Prototype successful.")
    session.close()


if __name__ == '__main__':
    main()
