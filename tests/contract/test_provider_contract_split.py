import os
import sys
import tempfile

# Add python directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

from hopilot.gto.browser_database_provider import BrowserDatabaseProvider
from hopilot.gto.normalized_db_provider import NormalizedDatabaseProvider
from hopilot.gto.analytics_repository import AnalyticsRepository
from hopilot.gto.simulation_repository import SimulationRepository


def test_browser_provider_exposes_split_repositories(tmp_path):
    db_path = tmp_path / 'browser_provider_contract.db'
    db_url = f"sqlite:///{db_path}"

    provider = BrowserDatabaseProvider(database_url=db_url)

    assert hasattr(provider, 'simulation_repository')
    assert hasattr(provider, 'analytics_repository')
    assert isinstance(provider.simulation_repository, SimulationRepository)
    assert isinstance(provider.analytics_repository, AnalyticsRepository)
    assert hasattr(provider, 'database_repository')
    assert hasattr(provider.database_repository, 'connection')
    assert provider.database_repository.database_url == db_url


def test_normalized_provider_exposes_analytics_repository(tmp_path):
    db_path = tmp_path / 'normalized_provider_contract.db'
    db_url = f"sqlite:///{db_path}"

    provider = NormalizedDatabaseProvider(database_url=db_url)

    assert hasattr(provider, 'repository')
    assert isinstance(provider.repository, AnalyticsRepository)
    assert callable(getattr(provider.repository, 'get_strategy_matrix', None))
    assert callable(getattr(provider.repository, 'get_convergence_data', None))
