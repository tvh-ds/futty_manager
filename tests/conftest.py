import pytest
from fastapi.testclient import TestClient

from scout.api import create_app
from scout.database import Base, connect
from scout.demo import demonstration
from scout.engine import RecruitmentEngine
from scout.releases import publish, write_bundle
from scout.settings import Settings


@pytest.fixture(scope="session")
def cohort():
    return demonstration()


@pytest.fixture(scope="session")
def recruitment(cohort):
    return RecruitmentEngine(*cohort)


@pytest.fixture()
def client(tmp_path, cohort):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    database = connect(url)
    Base.metadata.create_all(database)
    path = write_bundle(tmp_path / "releases", *cohort)
    publish(database, path)
    with TestClient(create_app(Settings(database_url=url, serve_private_evidence=False))) as value:
        yield value
