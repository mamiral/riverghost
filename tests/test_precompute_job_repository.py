import os
import tempfile

import pytest

from hopilot.database import DatabaseConnection
from hopilot.gto.precompute_job_repository import PrecomputeJobRepository


@pytest.fixture(scope="function")
def test_db_url():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test.db")
    db_url = f"sqlite:///{db_path}"
    connection = DatabaseConnection(db_url)
    connection.create_tables()
    connection.close()
    yield db_url
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)
    except Exception:
        pass


def test_precompute_job_repository_session_lifecycle(test_db_url):
    repo = PrecomputeJobRepository(DatabaseConnection(test_db_url))

    job_session_id = repo.create_precompute_job_session("fingerprint-1", 3)
    assert job_session_id > 0

    job_session = repo.get_precompute_job_session(job_session_id)
    assert job_session is not None
    assert job_session.requested_scenarios == 3
    assert job_session.completed_scenarios == 0

    repo.update_precompute_job_session(job_session_id, run_state="RUNNING", completed_scenarios=1)
    updated = repo.get_precompute_job_session(job_session_id)
    assert updated.run_state == "RUNNING"
    assert updated.completed_scenarios == 1


def test_precompute_job_repository_scenario_links(test_db_url):
    repo = PrecomputeJobRepository(DatabaseConnection(test_db_url))

    job_session_id = repo.create_precompute_job_session("fingerprint-2", 2)
    link_id = repo.create_scenario_run_link(
        job_session_id=job_session_id,
        scenario_index=0,
        scenario_key="scenario-0",
        scenario_contract={"selected_position": "UTG"},
        status="PENDING",
    )
    assert link_id > 0

    links = repo.get_scenario_run_links_for_job(job_session_id)
    assert len(links) == 1
    assert links[0].scenario_key == "scenario-0"

    repo.update_scenario_run_link(link_id, status="RUNNING")
    updated_link = repo.get_scenario_run_links_for_job(job_session_id)[0]
    assert updated_link.status == "RUNNING"
