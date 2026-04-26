#!/usr/bin/env python3
"""
Replay persisted simulated games from the SQLite database.

Shows each game state in insertion order with:
- round and board cards
- hero/opponent hole cards
- hand class and final strength
- inferred winner(s) from final_strength (lower is stronger)

Run from project root:
    c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe prototyping/game_replay.py

Examples:
    c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe prototyping/game_replay.py --limit 10
    c:/Users/U446541/sandbox/riverghost/.venv/Scripts/python.exe prototyping/game_replay.py --from-id 21
"""

import argparse
import sys
from pathlib import Path
from typing import List

# Add python dir to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

from hopilot.db import initialize_database, get_session
from hopilot.models.game_state import GameState
from hopilot.models.player import Player

DEFAULT_DB_URL = "sqlite:///python/hopilot/data/normalized_poker.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay stored game states")
    parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="SQLAlchemy database URL")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of games to print")
    parser.add_argument("--from-id", type=int, default=1, help="Start replay from this game_state ID")
    parser.add_argument("--game-id", type=int, default=None, help="Replay a single specific game state ID")
    return parser.parse_args()


def _format_cards(board_cards_str: str) -> str:
    if not board_cards_str:
        return "(none)"
    return " ".join(board_cards_str.split(","))


def _infer_winners(players: List[Player]) -> List[Player]:
    strengths = [p.final_strength for p in players if p.final_strength is not None]
    if not strengths:
        return []
    best_strength = min(strengths)
    return [p for p in players if p.final_strength == best_strength]


def _player_label(player: Player) -> str:
    role = "Hero" if player.is_hero else "Opp"
    hand_class = player.hand_class.value if player.hand_class is not None else "unknown"
    return (
        f"{role:<4} {player.position:<6} cards={player.hole_cards:<4} "
        f"class={hand_class:<16} strength={player.final_strength}"
    )


def main() -> None:
    args = parse_args()

    initialize_database(args.db_url)
    session = get_session()

    try:
        if args.game_id is not None:
            query = session.query(GameState).filter(GameState.id == args.game_id)
        else:
            query = (
                session.query(GameState)
                .filter(GameState.id >= args.from_id)
                .order_by(GameState.id.asc())
                .limit(args.limit)
            )
        game_states = query.all()

        if not game_states:
            print("No game states found for the requested range.")
            return

        print(f"Replaying {len(game_states)} game(s) from {args.db_url}")
        print("=" * 80)

        for gs in game_states:
            players = (
                session.query(Player)
                .filter(Player.game_state_id == gs.id)
                .order_by(Player.is_hero.desc(), Player.position.asc())
                .all()
            )

            winners = _infer_winners(players)
            winner_positions = ", ".join(p.position for p in winners) if winners else "unknown"

            print(f"Game #{gs.id}")
            print(f"  timestamp: {gs.timestamp}")
            print(f"  round:     {gs.round}")
            print(f"  board:     {_format_cards(gs.board_cards_str)}")
            print(f"  outcome:   {gs.outcome}")
            print(f"  winners:   {winner_positions}")
            print("  players:")
            for p in players:
                print(f"    - {_player_label(p)}")
            print("-" * 80)

    finally:
        session.close()


if __name__ == "__main__":
    main()
