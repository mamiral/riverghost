import os
import tempfile

import pytest

from hopilot.database import DatabaseConnection
from hopilot.gto.database_repository import DatabaseRepository


class TestDatabaseRepositoryPrecomputePersistence:
    @pytest.fixture(scope="function")
    def test_db(self):
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

    def test_precompute_job_session_and_scenario_link_persistence(self, test_db):
        repo = DatabaseRepository(test_db)

        job_session_id = repo.create_precompute_job_session(
            scenario_fingerprint="test-fingerprint",
            requested_scenarios=2,
        )
        assert job_session_id > 0

        session = repo.get_precompute_job_session(job_session_id)
        assert session is not None
        assert session.run_state == "RUNNING"
        assert session.requested_scenarios == 2
        assert session.completed_scenarios == 0
        assert session.failed_scenarios == 0

        scenario_link_id = repo.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=0,
            scenario_key="UTG:ALL_IN-FOLD-FOLD-FOLD:EV:False",
            scenario_contract={"selected_position": "UTG"},
            status="PENDING",
        )
        assert scenario_link_id > 0

        links = repo.get_scenario_run_links_for_job(job_session_id)
        assert len(links) == 1
        assert links[0].scenario_index == 0
        assert links[0].status == "PENDING"

        repo.update_scenario_run_link(
            scenario_link_id,
            status="RUNNING",
        )
        updated_link = repo.get_scenario_run_link(scenario_link_id)
        assert updated_link is not None
        assert updated_link.status == "RUNNING"

        repo.update_precompute_job_session(
            job_session_id,
            completed_scenarios=1,
            failed_scenarios=0,
        )
        session = repo.get_precompute_job_session(job_session_id)
        assert session.completed_scenarios == 1
        assert session.failed_scenarios == 0

    def test_get_scenario_run_links_for_job_returns_ordered_links(self, test_db):
        repo = DatabaseRepository(test_db)

        job_session_id = repo.create_precompute_job_session(
            scenario_fingerprint="ordered-fingerprint",
            requested_scenarios=3,
        )

        repo.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=2,
            scenario_key="third",
            scenario_contract={"selected_position": "BTN"},
            status="PENDING",
        )
        repo.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=0,
            scenario_key="first",
            scenario_contract={"selected_position": "UTG"},
            status="PENDING",
        )
        repo.create_scenario_run_link(
            job_session_id=job_session_id,
            scenario_index=1,
            scenario_key="second",
            scenario_contract={"selected_position": "MP"},
            status="PENDING",
        )

        links = repo.get_scenario_run_links_for_job(job_session_id)
        assert [link.scenario_key for link in links] == ["first", "second", "third"]
