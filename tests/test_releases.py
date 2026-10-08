import json

import pytest

from scout.database import Base, connect, load_active
from scout.releases import publish, read_bundle, rollback, validate_release, write_bundle


def test_tampering_does_not_activate_new_release(tmp_path, cohort):
    database = connect(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(database)
    original = write_bundle(tmp_path / "releases", *cohort)
    publish(database, original)
    release, players, teams = cohort
    next_release = release.model_copy(update={"id": "synthetic-second"})
    second = write_bundle(tmp_path / "releases", next_release, players, teams)
    second.write_text('{}')
    with pytest.raises(ValueError, match="checksum"):
        publish(database, second)
    assert load_active(database)[0].id == release.id


def test_release_activation_and_rollback(tmp_path, cohort):
    database = connect(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(database)
    release, players, teams = cohort
    publish(database, write_bundle(tmp_path, release, players, teams))
    second = release.model_copy(update={"id": "synthetic-second"})
    publish(database, write_bundle(tmp_path, second, players, teams))
    assert load_active(database)[0].id == second.id
    rollback(database, release.id)
    assert load_active(database)[0].id == release.id


def test_publication_gate_is_not_bypassed_by_complete_fixtures(cohort):
    release, players, teams = cohort
    real = release.model_copy(update={"kind": "real"})
    with pytest.raises(ValueError, match="permission"):
        validate_release(real, players, teams)


def test_changed_release_id_content_is_rejected(tmp_path, cohort):
    release, players, teams = cohort
    write_bundle(tmp_path, release, players, teams)
    modified = release.model_copy(update={"limitations": ["different"]})
    with pytest.raises(ValueError, match="immutable"):
        write_bundle(tmp_path, modified, players, teams)


def test_permission_flag_cannot_relabel_synthetic_evidence(cohort):
    release, players, teams = cohort
    real = release.model_copy(update={"kind": "real", "publication_approved": True,
                                      "publication_evidence": "documented permission"})
    with pytest.raises(ValueError, match="sourced observations"):
        validate_release(real, players, teams)


def test_incompatible_feature_version_refused(tmp_path, cohort):
    release, players, teams = cohort
    with pytest.raises(ValueError, match="Incompatible"):
        write_bundle(tmp_path, release.model_copy(update={"feature_version": "v999"}), players, teams)


def test_bundle_reproduces_contracts(tmp_path, cohort):
    path = write_bundle(tmp_path, *cohort)
    release, players, teams, checksum = read_bundle(path)
    assert release == cohort[0]
    assert {player.id for player in players} == {player.id for player in cohort[1]}
    assert len(checksum) == 64
    assert json.loads(path.read_text())["release"]["kind"] == "synthetic"


def test_serving_snapshot_corruption_is_detected(tmp_path, cohort):
    from sqlalchemy.orm import Session

    from scout.database import ReleaseRow
    database = connect(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(database)
    publish(database, write_bundle(tmp_path, *cohort))
    with Session(database) as session, session.begin():
        row = session.get(ReleaseRow, cohort[0].id)
        row.manifest = {**row.manifest, "source": "corrupted"}
    with pytest.raises(ValueError, match="snapshot checksum"):
        load_active(database)
