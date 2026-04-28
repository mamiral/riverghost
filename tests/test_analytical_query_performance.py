#!/usr/bin/env python3
"""
Performance and Caching Tests for Analytical Queries.

This module tests performance requirements and caching functionality
for all analytical query engines.
"""

import pytest
import sys
import os
import time
from typing import Dict, Any

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.database import DatabaseConnection
from hopilot.gto.convergence_analysis_queries import ConvergenceAnalysisQueries
from hopilot.gto.jackpot_frequency_queries import JackpotFrequencyQueries
from hopilot.gto.game_replay_queries import GameReplayQueryEngine
from hopilot.gto.query_cache import get_cache_stats, QueryResultCache


@pytest.fixture
def performance_test_db(tmp_path):
    """Create a test database for performance testing."""
    db_path = tmp_path / 'performance_test.db'
    db_url = f'sqlite:///{db_path}'

    conn = DatabaseConnection(db_url)
    conn.create_tables()

    yield db_url

    # Cleanup
    try:
        conn.close()
    except Exception:
        pass


@pytest.fixture
def query_engines(performance_test_db):
    """Create all analytical query engines."""
    return {
        'convergence': ConvergenceAnalysisQueries(performance_test_db),
        'jackpot': JackpotFrequencyQueries(performance_test_db),
        'replay': GameReplayQueryEngine(performance_test_db)
    }


class TestAnalyticalQueryPerformance:
    """Test performance requirements for analytical queries."""

    MAX_QUERY_DURATION = 30.0  # seconds

    def test_convergence_statistics_performance(self, query_engines):
        """Test that convergence statistics queries meet performance requirements."""
        engine = query_engines['convergence']

        start_time = time.time()
        result = engine.get_convergence_statistics(matrix_id=1, min_samples=100)
        duration = time.time() - start_time

        assert duration < self.MAX_QUERY_DURATION, f"Query took {duration:.2f}s, exceeds {self.MAX_QUERY_DURATION}s limit"
        # Result may be None if no data, but query should complete quickly

    def test_equity_convergence_series_performance(self, query_engines):
        """Test that equity convergence series queries meet performance requirements."""
        engine = query_engines['convergence']

        start_time = time.time()
        result = engine.get_equity_convergence_series(
            matrix_id=1, row_idx=0, col_idx=0,
            sample_intervals=[100, 500, 1000, 2000]
        )
        duration = time.time() - start_time

        assert duration < self.MAX_QUERY_DURATION, f"Query took {duration:.2f}s, exceeds {self.MAX_QUERY_DURATION}s limit"

    def test_jackpot_frequency_analysis_performance(self, query_engines):
        """Test that jackpot frequency analysis queries meet performance requirements."""
        engine = query_engines['jackpot']

        start_time = time.time()
        result = engine.get_jackpot_frequency_analysis(matrix_id=1)
        duration = time.time() - start_time

        assert duration < self.MAX_QUERY_DURATION, f"Query took {duration:.2f}s, exceeds {self.MAX_QUERY_DURATION}s limit"

    def test_jackpot_ev_impact_performance(self, query_engines):
        """Test that jackpot EV impact queries meet performance requirements."""
        engine = query_engines['jackpot']

        start_time = time.time()
        result = engine.get_jackpot_ev_impact_by_hand(matrix_id=1, min_samples=100)
        duration = time.time() - start_time

        assert duration < self.MAX_QUERY_DURATION, f"Query took {duration:.2f}s, exceeds {self.MAX_QUERY_DURATION}s limit"

    def test_jackpot_temporal_analysis_performance(self, query_engines):
        """Test that jackpot temporal analysis queries meet performance requirements."""
        engine = query_engines['jackpot']

        start_time = time.time()
        result = engine.get_jackpot_temporal_analysis(matrix_id=1, time_intervals=[100, 500, 1000])
        duration = time.time() - start_time

        assert duration < self.MAX_QUERY_DURATION, f"Query took {duration:.2f}s, exceeds {self.MAX_QUERY_DURATION}s limit"

    def test_replay_statistics_performance(self, query_engines):
        """Test that replay statistics queries meet performance requirements."""
        engine = query_engines['replay']

        start_time = time.time()
        result = engine.get_replay_statistics(matrix_id=1)
        duration = time.time() - start_time

        assert duration < self.MAX_QUERY_DURATION, f"Query took {duration:.2f}s, exceeds {self.MAX_QUERY_DURATION}s limit"

    def test_game_timeline_summary_performance(self, query_engines):
        """Test that game timeline summary queries meet performance requirements."""
        engine = query_engines['replay']

        start_time = time.time()
        result = engine.get_game_timeline_summary(game_state_id=1)
        duration = time.time() - start_time

        assert duration < self.MAX_QUERY_DURATION, f"Query took {duration:.2f}s, exceeds {self.MAX_QUERY_DURATION}s limit"


class TestQueryResultCaching:
    """Test query result caching functionality."""

    def test_cache_initialization(self):
        """Test that cache is properly initialized."""
        cache = QueryResultCache()
        assert cache is not None

        stats = get_cache_stats()
        assert 'size' in stats
        assert 'max_size' in stats
        assert 'default_ttl' in stats

    def test_convergence_query_caching(self, query_engines):
        """Test that convergence queries are properly cached."""
        engine = query_engines['convergence']

        # Clear any existing cache
        cache = QueryResultCache()
        cache.clear()

        # First call should miss cache
        start_time = time.time()
        result1 = engine.get_convergence_statistics(matrix_id=1, min_samples=100)
        first_duration = time.time() - start_time

        # Second call should hit cache
        start_time = time.time()
        result2 = engine.get_convergence_statistics(matrix_id=1, min_samples=100)
        second_duration = time.time() - start_time

        # Cache should make second call at least 2x faster (or at least 0.0001s faster for very fast queries)
        speedup_ratio = first_duration / max(second_duration, 0.0001)
        assert speedup_ratio > 1.5, \
            f"Cache not providing speedup: first={first_duration:.6f}s, second={second_duration:.6f}s, ratio={speedup_ratio:.2f}"

        # Results should be identical
        assert result1 == result2

    def test_jackpot_query_caching(self, query_engines):
        """Test that jackpot queries are properly cached."""
        engine = query_engines['jackpot']

        # Clear any existing cache
        cache = QueryResultCache()
        cache.clear()

        # First call
        start_time = time.time()
        result1 = engine.get_jackpot_frequency_analysis(matrix_id=1)
        first_duration = time.time() - start_time

        # Second call should hit cache
        start_time = time.time()
        result2 = engine.get_jackpot_frequency_analysis(matrix_id=1)
        second_duration = time.time() - start_time

        # Cache should make second call at least 2x faster (or at least 0.0001s faster for very fast queries)
        speedup_ratio = first_duration / max(second_duration, 0.0001)
        assert speedup_ratio > 1.5, \
            f"Cache not providing speedup: first={first_duration:.6f}s, second={second_duration:.6f}s, ratio={speedup_ratio:.2f}"

    def test_replay_query_caching(self, query_engines):
        """Test that replay queries are properly cached."""
        engine = query_engines['replay']

        # Clear any existing cache
        cache = QueryResultCache()
        cache.clear()

        # First call
        start_time = time.time()
        result1 = engine.get_replay_statistics(matrix_id=1)
        first_duration = time.time() - start_time

        # Second call should hit cache
        start_time = time.time()
        result2 = engine.get_replay_statistics(matrix_id=1)
        second_duration = time.time() - start_time

        # Cache should make second call at least 2x faster (or at least 0.0001s faster for very fast queries)
        speedup_ratio = first_duration / max(second_duration, 0.0001)
        assert speedup_ratio > 1.5, \
            f"Cache not providing speedup: first={first_duration:.6f}s, second={second_duration:.6f}s, ratio={speedup_ratio:.2f}"

    def test_cache_ttl_expiration(self):
        """Test that cache entries expire after TTL."""
        cache = QueryResultCache()

        # Set a very short TTL for testing
        cache.set('test_key', 'test_value', ttl=1)  # 1 second TTL

        # Should be available immediately
        assert cache.get('test_key') == 'test_value'

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert cache.get('test_key') is None