#!/usr/bin/env python3
"""
Create SQL views and reports for AOF GTO database analysis.

This script creates 4 comprehensive views:
1. matrix_display_view - Equity rankings and EV displays per hand
2. convergence_analysis_view - Equity progression over time per hand
3. jackpot_frequency_view - Frequency % and payout impact analysis
4. game_replay_view - Full hand history with all players and actions
"""

import sqlite3
from pathlib import Path


def create_views(db_path: str = "aof_analysis.db") -> None:
    """Create all database views for analysis and reporting."""
    
    # Verify database exists
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("CREATING AOF DATABASE VIEWS AND REPORTS")
    print("=" * 70)
    
    # ========================================================================
    # VIEW 1: MATRIX DISPLAY VIEW
    # ========================================================================
    # Displays equity and EV rankings for the 13x13 hand matrix
    print("\n[1/4] Creating matrix_display_view...")
    
    cursor.execute("DROP VIEW IF EXISTS matrix_display_view")
    cursor.execute("""
        CREATE VIEW matrix_display_view AS
        SELECT
            hm.simulation_id,
            hm.id as matrix_id,
            mc.row_index,
            mc.col_index,
            (SELECT hole_cards FROM players 
             WHERE game_state_id IN 
               (SELECT id FROM game_states WHERE cell_id = mc.id)
             LIMIT 1) as sample_hand,
            COUNT(DISTINCT gs.id) as total_games,
            COUNT(DISTINCT CASE WHEN gs.outcome = 'hero_win' THEN gs.id END) as hero_wins,
            ROUND(COUNT(DISTINCT CASE WHEN gs.outcome = 'hero_win' THEN gs.id END) * 100.0 / 
                  COUNT(DISTINCT gs.id), 2) as win_percentage,
            ROUND(AVG(am.equity), 4) as avg_equity,
            ROUND(AVG(am.ev), 2) as avg_ev,
            am.convergence_status,
            MAX(gs.timestamp) as last_updated
        FROM hand_matrices hm
        JOIN matrix_cells mc ON hm.id = mc.matrix_id
        LEFT JOIN game_states gs ON mc.id = gs.cell_id
        LEFT JOIN aggregated_metrics am ON mc.id = am.cell_id
        GROUP BY hm.id, mc.id, mc.row_index, mc.col_index
        ORDER BY hm.simulation_id, mc.row_index, mc.col_index
    """)
    
    # ========================================================================
    # VIEW 2: CONVERGENCE ANALYSIS VIEW  
    # ========================================================================
    # Tracks equity progression over time for convergence assessment
    print("[2/4] Creating convergence_analysis_view...")
    
    cursor.execute("DROP VIEW IF EXISTS convergence_analysis_view")
    cursor.execute("""
        CREATE VIEW convergence_analysis_view AS
        SELECT
            hm.simulation_id,
            mc.row_index,
            mc.col_index,
            (SELECT hole_cards FROM players 
             WHERE game_state_id IN 
               (SELECT id FROM game_states WHERE cell_id = mc.id)
             LIMIT 1) as hand,
            COUNT(DISTINCT gs.id) as total_games,
            MIN(gs.timestamp) as first_game_time,
            MAX(gs.timestamp) as last_game_time,
            ROUND((julianday(MAX(gs.timestamp)) - julianday(MIN(gs.timestamp))) * 24, 2) as hours_elapsed,
            ROUND(COUNT(DISTINCT gs.id) / 
                  NULLIF((julianday(MAX(gs.timestamp)) - julianday(MIN(gs.timestamp))) * 24, 0), 2) as games_per_hour,
            ROUND(AVG(CASE WHEN gs.outcome = 'hero_win' THEN 1.0 ELSE 0.0 END), 4) as running_win_rate,
            am.equity as final_equity,
            am.convergence_status,
            CASE 
                WHEN COUNT(DISTINCT gs.id) < 100 THEN 'INITIAL'
                WHEN COUNT(DISTINCT gs.id) < 500 THEN 'CONVERGENCE'
                WHEN COUNT(DISTINCT gs.id) >= 500 THEN 'STABLE'
            END as stability_stage
        FROM hand_matrices hm
        JOIN matrix_cells mc ON hm.id = mc.matrix_id
        LEFT JOIN game_states gs ON mc.id = gs.cell_id
        LEFT JOIN aggregated_metrics am ON mc.id = am.cell_id
        GROUP BY hm.simulation_id, mc.id, mc.row_index, mc.col_index
        ORDER BY hm.simulation_id, total_games DESC, mc.row_index, mc.col_index
    """)
    
    # ========================================================================
    # VIEW 3: JACKPOT FREQUENCY VIEW
    # ========================================================================
    # Analyzes jackpot frequency and EV impact per hand
    print("[3/4] Creating jackpot_frequency_view...")
    
    cursor.execute("DROP VIEW IF EXISTS jackpot_frequency_view")
    cursor.execute("""
        CREATE VIEW jackpot_frequency_view AS
        SELECT
            hm.simulation_id,
            mc.row_index,
            mc.col_index,
            (SELECT hole_cards FROM players 
             WHERE game_state_id IN 
               (SELECT id FROM game_states WHERE cell_id = mc.id)
             LIMIT 1) as hand,
            COUNT(DISTINCT gs.id) as total_games_for_hand,
            COUNT(DISTINCT jp.id) as jackpot_hits,
            ROUND(COUNT(DISTINCT jp.id) * 100.0 / COUNT(DISTINCT gs.id), 2) as jackpot_frequency_pct,
            jp.jackpot_type,
            COUNT(DISTINCT jp.id) as jackpot_count_by_type,
            ROUND(AVG(jp.payout_amount), 2) as avg_payout_per_type,
            ROUND(SUM(jp.payout_amount), 2) as total_payouts_generated,
            ROUND(SUM(jp.payout_amount) / COUNT(DISTINCT gs.id), 2) as ev_from_jackpots,
            MAX(jp.created_at) as last_jackpot_hit
        FROM hand_matrices hm
        JOIN matrix_cells mc ON hm.id = mc.matrix_id
        LEFT JOIN game_states gs ON mc.id = gs.cell_id
        LEFT JOIN jackpots jp ON gs.id = jp.game_state_id
        GROUP BY hm.simulation_id, mc.id, mc.row_index, mc.col_index, jp.jackpot_type
        ORDER BY hm.simulation_id, mc.row_index, mc.col_index, jackpot_frequency_pct DESC
    """)
    
    # ========================================================================
    # VIEW 4: GAME REPLAY VIEW
    # ========================================================================
    # Full hand history with all players and actions
    print("[4/4] Creating game_replay_view...")
    
    cursor.execute("DROP VIEW IF EXISTS game_replay_view")
    cursor.execute("""
        CREATE VIEW game_replay_view AS
        SELECT
            gs.id as game_id,
            gs.cell_id,
            mc.row_index,
            mc.col_index,
            hm.simulation_id,
            gs.num_players,
            gs.timestamp,
            gs.pot_size,
            gs.outcome,
            bc.cards as board_cards,
            (SELECT GROUP_CONCAT(
                CASE WHEN p.is_hero = 1 
                     THEN '[HERO] ' || p.position || ':' || p.hole_cards
                     ELSE '[VILL] ' || p.position || ':' || p.hole_cards
                END,
                ' | '
             )
             FROM players p 
             WHERE p.game_state_id = gs.id) as all_players,
            (SELECT GROUP_CONCAT(
                p.position || ':' || b.action_type || '(' || b.amount || 'BB)',
                ' -> '
             )
             FROM bets b
             JOIN players p ON b.player_id = p.id
             WHERE b.game_state_id = gs.id
             ORDER BY b.created_at) as action_sequence,
            (SELECT COUNT(*) FROM bets WHERE game_state_id = gs.id) as total_actions,
            (SELECT COUNT(*) FROM jackpots WHERE game_state_id = gs.id) as jackpot_events,
            gs.created_at
        FROM game_states gs
        JOIN matrix_cells mc ON gs.cell_id = mc.id
        JOIN hand_matrices hm ON mc.matrix_id = hm.id
        LEFT JOIN board_cards bc ON gs.board_cards_id = bc.id
        ORDER BY hm.simulation_id, gs.timestamp DESC
    """)
    
    conn.commit()
    print("\n" + "=" * 70)
    print("ALL VIEWS CREATED SUCCESSFULLY")
    print("=" * 70)
    
    # ========================================================================
    # DEMONSTRATE VIEWS WITH SAMPLE QUERIES
    # ========================================================================
    print("\n" + "=" * 70)
    print("VIEW 1: MATRIX DISPLAY VIEW - Sample Equity Rankings")
    print("=" * 70)
    print("\nTop 5 hands by equity with highest win percentage:\n")
    
    cursor.execute("""
        SELECT 
            simulation_id,
            row_index || 'x' || col_index as cell,
            sample_hand,
            total_games,
            win_percentage,
            avg_equity
        FROM matrix_display_view
        WHERE total_games > 0
        ORDER BY avg_equity DESC
        LIMIT 5
    """)
    
    headers = ["Sim", "Cell", "Hand", "Games", "Win%", "Equity"]
    print(f"{headers[0]:<4} {headers[1]:<6} {headers[2]:<8} {headers[3]:<8} {headers[4]:<8} {headers[5]:<8}")
    print("-" * 50)
    for row in cursor.fetchall():
        print(f"{row[0]:<4} {row[1]:<6} {row[2]:<8} {row[3]:<8} {row[4]:<8.2f} {row[5]:<8.4f}")
    
    # ========================================================================
    print("\n" + "=" * 70)
    print("VIEW 2: CONVERGENCE ANALYSIS VIEW - Stability Status")
    print("=" * 70)
    print("\nHands grouped by stability stage:\n")
    
    cursor.execute("""
        SELECT 
            stability_stage,
            COUNT(*) as hand_count,
            ROUND(AVG(running_win_rate), 4) as avg_win_rate,
            ROUND(AVG(games_per_hour), 2) as avg_speed,
            ROUND(AVG(CAST(hours_elapsed as FLOAT)), 2) as avg_duration
        FROM convergence_analysis_view
        WHERE total_games > 0
        GROUP BY stability_stage
        ORDER BY CASE 
            WHEN stability_stage = 'INITIAL' THEN 1
            WHEN stability_stage = 'CONVERGENCE' THEN 2
            WHEN stability_stage = 'STABLE' THEN 3
        END
    """)
    
    headers = ["Stage", "Count", "Win Rate", "Games/HR", "Hours"]
    print(f"{headers[0]:<15} {headers[1]:<8} {headers[2]:<12} {headers[3]:<12} {headers[4]:<12}")
    print("-" * 60)
    for row in cursor.fetchall():
        if row[0]:
            print(f"{row[0]:<15} {row[1]:<8} {row[2]:<12.4f} {row[3]:<12.2f} {row[4]:<12.2f}")
    
    # ========================================================================
    print("\n" + "=" * 70)
    print("VIEW 3: JACKPOT FREQUENCY VIEW - Top Jackpot Hands")
    print("=" * 70)
    print("\nTop 5 hands by jackpot frequency:\n")
    
    cursor.execute("""
        SELECT 
            row_index || 'x' || col_index as cell,
            hand,
            total_games_for_hand,
            jackpot_frequency_pct,
            total_payouts_generated,
            ev_from_jackpots
        FROM jackpot_frequency_view
        WHERE jackpot_frequency_pct > 0
        GROUP BY cell, hand
        ORDER BY jackpot_frequency_pct DESC
        LIMIT 5
    """)
    
    headers = ["Cell", "Hand", "Games", "Freq%", "Total$", "EV$"]
    print(f"{headers[0]:<6} {headers[1]:<8} {headers[2]:<8} {headers[3]:<8} {headers[4]:<12} {headers[5]:<10}")
    print("-" * 55)
    for row in cursor.fetchall():
        print(f"{row[0]:<6} {row[1]:<8} {row[2]:<8} {row[3]:<8.2f} ${row[4]:<11.2f} ${row[5]:<9.2f}")
    
    # ========================================================================
    print("\n" + "=" * 70)
    print("VIEW 4: GAME REPLAY VIEW - Latest Games with Actions")
    print("=" * 70)
    print("\nLast 3 games with full action sequences:\n")
    
    cursor.execute("""
        SELECT 
            game_id,
            row_index || 'x' || col_index as cell,
            num_players,
            total_actions,
            outcome,
            action_sequence
        FROM game_replay_view
        ORDER BY game_id DESC
        LIMIT 3
    """)
    
    for idx, row in enumerate(cursor.fetchall(), 1):
        game_id, cell, num_players, actions, outcome, action_seq = row
        print(f"Game {game_id} (Cell {cell}, {num_players} players, {actions} actions):")
        print(f"  Outcome: {outcome}")
        if action_seq:
            print(f"  Actions: {action_seq}")
        else:
            print(f"  Actions: None")
        print()
    
    # ========================================================================
    print("=" * 70)
    print("VIEWS QUERY SUMMARY")
    print("=" * 70)
    
    # Count records in each view
    views = [
        "matrix_display_view",
        "convergence_analysis_view", 
        "jackpot_frequency_view",
        "game_replay_view"
    ]
    
    print("\nView record counts:\n")
    for view_name in views:
        cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
        count = cursor.fetchone()[0]
        print(f"  {view_name:<35} {count:>8} records")
    
    print("\n" + "=" * 70)
    print("View creation and demonstration complete!")
    print("=" * 70 + "\n")
    
    conn.close()


if __name__ == "__main__":
    create_views()
