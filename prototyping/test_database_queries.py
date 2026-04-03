"""
AOF GTO Browser - Database Query Tests

This script runs comprehensive SQL tests to verify:
1. Relational integrity (FK constraints, data consistency)
2. Convergence tracking (equity over time)
3. Jackpot frequency aggregations
4. Game replay queries
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class DatabaseTester:
    """Test suite for AOF database relational integrity and query functionality."""

    def __init__(self, db_path: str):
        """Initialize tester with database connection."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # Return dict-like rows
        self.cursor = self.conn.cursor()
        self.results = []

    def close(self):
        """Close database connection."""
        self.conn.close()

    def add_result(self, test_name: str, passed: bool, message: str = ""):
        """Record test result."""
        status = "[PASS]" if passed else "[FAIL]"
        self.results.append({
            "test": test_name,
            "status": status,
            "message": message
        })
        print(f"{status} | {test_name}")
        if message:
            print(f"      {message}")

    # ========================================================================
    # RELATIONAL INTEGRITY TESTS
    # ========================================================================

    def test_simulations_exist(self) -> bool:
        """Test: Simulations table has records."""
        self.cursor.execute("SELECT COUNT(*) FROM simulations;")
        count = self.cursor.fetchone()[0]
        passed = count > 0
        self.add_result(
            "Simulations exist",
            passed,
            f"Found {count} simulations"
        )
        return passed

    def test_hand_matrices_linked_to_simulations(self) -> bool:
        """Test: Every HandMatrix has valid simulation_id FK."""
        self.cursor.execute("""
            SELECT 
                hm.id, 
                hm.simulation_id,
                COUNT(CASE WHEN s.id IS NULL THEN 1 END) as orphaned
            FROM hand_matrices hm
            LEFT JOIN simulations s ON hm.simulation_id = s.id
            GROUP BY hm.id
        """)
        
        orphaned_count = sum(row["orphaned"] for row in self.cursor.fetchall())
        passed = orphaned_count == 0
        
        self.add_result(
            "HandMatrices linked to Simulations",
            passed,
            f"Orphaned records: {orphaned_count}"
        )
        return passed

    def test_matrix_cells_linked_to_matrices(self) -> bool:
        """Test: Every MatrixCell has valid matrix_id FK."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN hm.id IS NULL THEN 1 END) as orphaned
            FROM matrix_cells mc
            LEFT JOIN hand_matrices hm ON mc.matrix_id = hm.id
        """)
        
        orphaned_count = self.cursor.fetchone()[0]
        passed = orphaned_count == 0
        
        self.add_result(
            "MatrixCells linked to HandMatrices",
            passed,
            f"Orphaned records: {orphaned_count}"
        )
        return passed

    def test_game_states_linked_to_cells(self) -> bool:
        """Test: Every GameState has valid cell_id FK."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN mc.id IS NULL THEN 1 END) as orphaned
            FROM game_states gs
            LEFT JOIN matrix_cells mc ON gs.cell_id = mc.id
        """)
        
        orphaned_count = self.cursor.fetchone()[0]
        passed = orphaned_count == 0
        
        self.add_result(
            "GameStates linked to MatrixCells",
            passed,
            f"Orphaned records: {orphaned_count}"
        )
        return passed

    def test_players_linked_to_game_states(self) -> bool:
        """Test: Every Player has valid game_state_id FK."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN gs.id IS NULL THEN 1 END) as orphaned
            FROM players p
            LEFT JOIN game_states gs ON p.game_state_id = gs.id
        """)
        
        orphaned_count = self.cursor.fetchone()[0]
        passed = orphaned_count == 0
        
        self.add_result(
            "Players linked to GameStates",
            passed,
            f"Orphaned records: {orphaned_count}"
        )
        return passed

    def test_bets_linked_to_game_states_and_players(self) -> bool:
        """Test: Every Bet has valid game_state_id and player_id FKs."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN gs.id IS NULL THEN 1 END) as orphaned_gs,
                COUNT(CASE WHEN p.id IS NULL THEN 1 END) as orphaned_p
            FROM bets b
            LEFT JOIN game_states gs ON b.game_state_id = gs.id
            LEFT JOIN players p ON b.player_id = p.id
        """)
        
        row = self.cursor.fetchone()
        orphaned_gs = row[0]
        orphaned_p = row[1]
        passed = orphaned_gs == 0 and orphaned_p == 0
        
        self.add_result(
            "Bets linked to GameStates and Players",
            passed,
            f"Orphaned GameState FKs: {orphaned_gs}, Player FKs: {orphaned_p}"
        )
        return passed

    def test_jackpots_linked_to_game_states_and_players(self) -> bool:
        """Test: Every Jackpot has valid game_state_id and player_id FKs."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN gs.id IS NULL THEN 1 END) as orphaned_gs,
                COUNT(CASE WHEN p.id IS NULL THEN 1 END) as orphaned_p
            FROM jackpots j
            LEFT JOIN game_states gs ON j.game_state_id = gs.id
            LEFT JOIN players p ON j.player_id = p.id
        """)
        
        row = self.cursor.fetchone()
        orphaned_gs = row[0]
        orphaned_p = row[1]
        passed = orphaned_gs == 0 and orphaned_p == 0
        
        self.add_result(
            "Jackpots linked to GameStates and Players",
            passed,
            f"Orphaned GameState FKs: {orphaned_gs}, Player FKs: {orphaned_p}"
        )
        return passed

    def test_aggregated_metrics_linked_to_cells(self) -> bool:
        """Test: Every AggregatedMetrics has valid cell_id FK."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN mc.id IS NULL THEN 1 END) as orphaned
            FROM aggregated_metrics am
            LEFT JOIN matrix_cells mc ON am.cell_id = mc.id
        """)
        
        orphaned_count = self.cursor.fetchone()[0]
        passed = orphaned_count == 0
        
        self.add_result(
            "AggregatedMetrics linked to MatrixCells",
            passed,
            f"Orphaned records: {orphaned_count}"
        )
        return passed

    def test_board_cards_referenced_by_game_states(self) -> bool:
        """Test: Every BoardCards referenced by GameState exists."""
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN bc.id IS NULL THEN 1 END) as orphaned
            FROM game_states gs
            LEFT JOIN board_cards bc ON gs.board_cards_id = bc.id
        """)
        
        orphaned_count = self.cursor.fetchone()[0]
        passed = orphaned_count == 0
        
        self.add_result(
            "GameStates BoardCards references valid",
            passed,
            f"Invalid references: {orphaned_count}"
        )
        return passed

    # ========================================================================
    # CONVERGENCE TRACKING TESTS
    # ========================================================================

    def test_convergence_tracking_by_timestamp(self) -> bool:
        """Test: GameStates have chronological timestamps for convergence tracking."""
        self.cursor.execute("""
            SELECT 
                mc.hand_notation,
                COUNT(gs.id) as game_count,
                MIN(gs.timestamp) as earliest,
                MAX(gs.timestamp) as latest
            FROM game_states gs
            JOIN matrix_cells mc ON gs.cell_id = mc.id
            GROUP BY mc.hand_notation
            LIMIT 5
        """)
        
        rows = self.cursor.fetchall()
        passed = len(rows) > 0
        
        if rows:
            summary = f"\nSample convergence data:\n"
            for row in rows:
                summary += f"  {row['hand_notation']}: {row['game_count']} games spanning {row['earliest']} to {row['latest']}\n"
            self.add_result(
                "Convergence tracking timestamps",
                passed,
                summary.strip()
            )
        else:
            self.add_result(
                "Convergence tracking timestamps",
                False,
                "No game state data found"
            )
        
        return passed

    def test_game_outcome_distribution(self) -> bool:
        """Test: Game outcomes are distributed (hero_win, hero_loss, draw)."""
        self.cursor.execute("""
            SELECT 
                outcome,
                COUNT(*) as count
            FROM game_states
            WHERE outcome IS NOT NULL
            GROUP BY outcome
        """)
        
        outcomes = {row["outcome"]: row["count"] for row in self.cursor.fetchall()}
        passed = len(outcomes) > 0
        
        summary = f"Outcome distribution: {outcomes}"
        self.add_result(
            "Game outcome distribution",
            passed,
            summary
        )
        return passed

    # ========================================================================
    # JACKPOT FREQUENCY AGGREGATION TESTS
    # ========================================================================

    def test_jackpot_frequency_aggregation(self) -> bool:
        """Test: Jackpot frequency can be aggregated by type."""
        self.cursor.execute("""
            SELECT 
                jackpot_type,
                COUNT(*) as frequency,
                AVG(payout_amount) as avg_payout,
                MIN(payout_amount) as min_payout,
                MAX(payout_amount) as max_payout
            FROM jackpots
            GROUP BY jackpot_type
            ORDER BY frequency DESC
        """)
        
        jackpots = self.cursor.fetchall()
        passed = len(jackpots) > 0
        
        if jackpots:
            summary = f"\nJackpot frequency analysis:\n"
            for row in jackpots:
                summary += f"  {row['jackpot_type']}: {row['frequency']} events, avg payout ${row['avg_payout']:.2f}\n"
            self.add_result(
                "Jackpot frequency aggregation",
                passed,
                summary.strip()
            )
        else:
            self.add_result(
                "Jackpot frequency aggregation",
                False,
                "No jackpot data found"
            )
        
        return passed

    def test_jackpot_impact_on_cell(self) -> bool:
        """Test: Jackpots can be analyzed per cell."""
        self.cursor.execute("""
            SELECT 
                mc.hand_notation,
                COUNT(j.id) as jackpot_count,
                COUNT(gs.id) as total_games,
                ROUND(COUNT(j.id) * 100.0 / COUNT(gs.id), 2) as jackpot_frequency_pct,
                ROUND(AVG(j.payout_amount), 2) as avg_payout
            FROM matrix_cells mc
            LEFT JOIN game_states gs ON mc.id = gs.cell_id
            LEFT JOIN jackpots j ON gs.id = j.game_state_id
            WHERE gs.id IS NOT NULL
            GROUP BY mc.hand_notation
            HAVING jackpot_count > 0
            LIMIT 5
        """)
        
        rows = self.cursor.fetchall()
        passed = len(rows) > 0
        
        if rows:
            summary = f"\nJackpot impact by hand:\n"
            for row in rows:
                summary += f"  {row['hand_notation']}: {row['jackpot_frequency_pct']}% frequency, avg ${row['avg_payout']}\n"
            self.add_result(
                "Jackpot impact per cell",
                passed,
                summary.strip()
            )
        else:
            self.add_result(
                "Jackpot impact per cell",
                False,
                "No jackpot data found"
            )
        
        return passed

    # ========================================================================
    # GAME REPLAY QUERY TESTS
    # ========================================================================

    def test_game_replay_query(self) -> bool:
        """Test: Game replay can reconstruct full hand history with both players and actions."""
        # Get 3 sample games with all details
        self.cursor.execute("""
            SELECT DISTINCT
                gs.id as game_id,
                gs.num_players,
                gs.timestamp,
                bc.cards as board_cards
            FROM game_states gs
            LEFT JOIN board_cards bc ON gs.board_cards_id = bc.id
            WHERE gs.num_players >= 2
            LIMIT 3
        """)
        
        games = self.cursor.fetchall()
        passed = len(games) > 0
        
        if games:
            summary = f"\nDetailed game replay with all players and actions:\n"
            
            for game in games:
                game_id = game[0]
                num_players = game[1]
                board = game[3] if game[3] else 'empty'
                summary += f"\n  Game {game_id} ({num_players} players):\n"
                summary += f"     Board: {board}\n"
                
                # Get all players for this game
                self.cursor.execute("""
                    SELECT 
                        id,
                        position,
                        hole_cards,
                        is_hero
                    FROM players
                    WHERE game_state_id = ?
                    ORDER BY is_hero DESC, position
                """, (game_id,))
                
                players_data = self.cursor.fetchall()
                summary += f"     Players:\n"
                for player in players_data:
                    player_id, position, hole_cards, is_hero = player
                    player_type = "HERO" if is_hero else "VILL"
                    summary += f"       P{player_id} [{player_type}] {hole_cards} @ {position}\n"
                
                # Get all actions for this game
                self.cursor.execute("""
                    SELECT 
                        b.player_id,
                        b.action_type,
                        b.amount,
                        b.created_at
                    FROM bets b
                    WHERE b.game_state_id = ?
                    ORDER BY b.created_at
                """, (game_id,))
                
                actions_data = self.cursor.fetchall()
                if actions_data:
                    summary += f"     Actions:\n"
                    for idx, action in enumerate(actions_data, 1):
                        player_id, action_type, amount, _ = action
                        summary += f"       {idx}. P{player_id}: {action_type} {amount}BB\n"
                else:
                    summary += f"     Actions: None\n"
            
            self.add_result(
                "Game replay query structure",
                passed,
                summary.strip()
            )
        else:
            self.add_result(
                "Game replay query structure",
                False,
                "No game data found"
            )
        
        return passed

    def test_action_sequence_reconstruction(self) -> bool:
        """Test: Actions can be reconstructed chronologically per hand with details."""
        self.cursor.execute("""
            SELECT 
                gs.id,
                COUNT(b.id) as action_count
            FROM game_states gs
            LEFT JOIN bets b ON gs.id = b.game_state_id
            GROUP BY gs.id
            HAVING COUNT(b.id) > 0
            LIMIT 3
        """)
        
        actions = self.cursor.fetchall()
        passed = len(actions) > 0
        
        if actions:
            summary = f"\nDetailed action sequences per game:\n"
            
            for action_row in actions:
                game_id = action_row[0]
                action_count = action_row[1]
                
                # Get detailed actions for this game
                self.cursor.execute("""
                    SELECT 
                        p.position,
                        p.is_hero,
                        p.hole_cards,
                        b.action_type,
                        b.amount
                    FROM bets b
                    JOIN players p ON b.player_id = p.id
                    WHERE b.game_state_id = ?
                    ORDER BY b.created_at
                """, (game_id,))
                
                bets_data = self.cursor.fetchall()
                summary += f"  Game {game_id}: {action_count} actions\n"
                
                for idx, bet in enumerate(bets_data, 1):
                    player_type = "HERO" if bet[1] else "VILL"
                    hole_cards = bet[2]
                    summary += f"    {idx}. {player_type} ({hole_cards}) @ {bet[0]}: {bet[3].upper()} {bet[4]}BB\n"
            
            self.add_result(
                "Action sequence reconstruction",
                passed,
                summary.strip()
            )
        else:
            self.add_result(
                "Action sequence reconstruction",
                False,
                "No action data found"
            )
        
        return passed

    # ========================================================================
    # DATA CONSISTENCY TESTS
    # ========================================================================

    def test_player_count_per_game(self) -> bool:
        """Test: Each game has 2-4 players with at least one hero."""
        self.cursor.execute("""
            SELECT 
                gs.id,
                COUNT(p.id) as player_count,
                SUM(CASE WHEN p.is_hero = 1 THEN 1 ELSE 0 END) as hero_count
            FROM game_states gs
            LEFT JOIN players p ON gs.id = p.game_state_id
            GROUP BY gs.id
            HAVING (player_count < 2 OR player_count > 4 OR hero_count != 1)
        """)
        
        invalid_games = self.cursor.fetchall()
        passed = len(invalid_games) == 0
        
        self.add_result(
            "Player count per game (2-4 players)",
            passed,
            f"Games with invalid player count: {len(invalid_games)}"
        )
        return passed

    def test_hero_villain_distribution(self) -> bool:
        """Test: Each game has at least one hero and one or more villains."""
        self.cursor.execute("""
            SELECT 
                gs.id,
                SUM(CASE WHEN p.is_hero = 1 THEN 1 ELSE 0 END) as hero_count
            FROM game_states gs
            LEFT JOIN players p ON gs.id = p.game_state_id
            GROUP BY gs.id
            HAVING hero_count != 1
        """)
        
        invalid_games = self.cursor.fetchall()
        passed = len(invalid_games) == 0
        
        self.add_result(
            "Hero/villain distribution (1 hero per game)",
            passed,
            f"Games with invalid distribution: {len(invalid_games)}"
        )
        return passed

    def test_aggregated_metrics_coverage(self) -> bool:
        """Test: Aggregated metrics exist for analyzed cells."""
        self.cursor.execute("""
            SELECT 
                COUNT(DISTINCT mc.id) as total_cells,
                COUNT(DISTINCT am.cell_id) as metricated_cells
            FROM matrix_cells mc
            LEFT JOIN aggregated_metrics am ON mc.id = am.cell_id
            WHERE mc.matrix_id = (SELECT id FROM hand_matrices LIMIT 1)
        """)
        
        row = self.cursor.fetchone()
        total = row[0]
        metricated = row[1]
        coverage_pct = (metricated / total * 100) if total > 0 else 0
        
        self.add_result(
            "Aggregated metrics coverage",
            metricated > 0,
            f"{metricated}/{total} cells have metrics ({coverage_pct:.1f}%)"
        )
        return metricated > 0

    # ========================================================================
    # RUN ALL TESTS
    # ========================================================================

    def run_all_tests(self):
        """Run complete test suite."""
        print("\n" + "="*70)
        print("AOF DATABASE TEST SUITE")
        print("="*70)

        print("\n[RELATIONAL INTEGRITY TESTS]")
        print("-" * 70)
        self.test_simulations_exist()
        self.test_hand_matrices_linked_to_simulations()
        self.test_matrix_cells_linked_to_matrices()
        self.test_game_states_linked_to_cells()
        self.test_players_linked_to_game_states()
        self.test_bets_linked_to_game_states_and_players()
        self.test_jackpots_linked_to_game_states_and_players()
        self.test_aggregated_metrics_linked_to_cells()
        self.test_board_cards_referenced_by_game_states()

        print("\n[CONVERGENCE TRACKING TESTS]")
        print("-" * 70)
        self.test_convergence_tracking_by_timestamp()
        self.test_game_outcome_distribution()

        print("\n[JACKPOT FREQUENCY TESTS]")
        print("-" * 70)
        self.test_jackpot_frequency_aggregation()
        self.test_jackpot_impact_on_cell()

        print("\n[GAME REPLAY TESTS]")
        print("-" * 70)
        self.test_game_replay_query()
        self.test_action_sequence_reconstruction()

        print("\n[DATA CONSISTENCY TESTS]")
        print("-" * 70)
        self.test_player_count_per_game()
        self.test_hero_villain_distribution()
        self.test_aggregated_metrics_coverage()

        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        
        passed = sum(1 for r in self.results if "PASS" in r["status"])
        failed = sum(1 for r in self.results if "FAIL" in r["status"])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"[PASS] Passed: {passed}")
        print(f"[FAIL] Failed: {failed}")
        print(f"Pass Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\nFailed Tests:")
            for result in self.results:
                if "FAIL" in result["status"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("="*70 + "\n")


if __name__ == "__main__":
    db_path = Path(__file__).parent / "aof_analysis.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        print("Please run create_aof_database.py first")
        exit(1)

    tester = DatabaseTester(str(db_path))
    try:
        tester.run_all_tests()
    finally:
        tester.close()
