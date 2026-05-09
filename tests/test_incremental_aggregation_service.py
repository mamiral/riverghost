#!/usr/bin/env python3
"""Tests for the incremental aggregation service."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.database import DatabaseConnection
from hopilot.gto.game_state_repository import GameStateRepository
from hopilot.gto.incremental_aggregation_service import IncrementalAggregationService
from hopilot.poker_analyzer import PokerAnalyzer


def create_test_database(tmp_path):
    db_path = tmp_path / 'incremental_aggregation.db'
    db_url = f'sqlite:///{db_path}'
    connection = DatabaseConnection(db_url)
    connection.create_tables()
    return connection


@pytest.fixture
def database(tmp_path):
    connection = create_test_database(tmp_path)
    yield connection
    try:
        connection.close()
    except Exception:
        pass


def test_incremental_aggregation_uses_win_loss_probability(database):
    gs_repo = GameStateRepository(database)
    analyzer = PokerAnalyzer()
    service = IncrementalAggregationService(database, analyzer, emit_interval=1000)

    hero_hole_cards = 'AsKs'
    for outcome in ['win', 'win', 'loss', 'tie']:
        gs_repo.create_game_state({
            'pot_size': 15.0,
            'board_cards_str': 'QsJhTd9c8d',
            'round': 'preflop',
            'outcome': outcome,
            'players': [
                {
                    'position': 'UTG',
                    'hole_cards': hero_hole_cards,
                    'stack_size': 1000.0,
                    'is_hero': True,
                },
                {
                    'position': 'BTN',
                    'hole_cards': 'KdKh',
                    'stack_size': 1000.0,
                    'is_hero': False,
                }
            ]
        })

    result = service.aggregate_cell_incremental(
        cell_id=1,
        hand_key='AKs',
        simulation_id=1,
        pot_size=15.0,
        bet_amount=100.0,
        raw_start=1,
        raw_end=100,
        batch_size=10,
    )

    assert result['sample_count'] == 4
    assert result['win_probability'] == pytest.approx(0.5)
    assert result['equity'] == pytest.approx(0.625)
    assert result['ev'] == pytest.approx(32.5)
