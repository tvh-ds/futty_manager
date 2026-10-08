import csv
import json
import sqlite3
from pathlib import Path

import pytest

from scout import master_snapshot
from scout.master_missing import fill_missing
from scout.master_priority import resolve_master
from scout.source_audit import checksum


@pytest.fixture
def snapshot(tmp_path):
    folder = tmp_path / 'original'
    folder.mkdir()
    (folder / 'columns.json').write_text('[{"id":"shots","label":"Shots"}]')
    (folder / 'manifest.json').write_text('{"outputs":{},"limitations":[]}')
    with sqlite3.connect(folder / 'master.sqlite') as con:
        con.executescript('''CREATE TABLE players(master_row TEXT PRIMARY KEY,league TEXT,names_json TEXT,sources_json TEXT);
            CREATE TABLE columns(column_id TEXT PRIMARY KEY,members_json TEXT);
            CREATE TABLE cells(master_row TEXT,column_id TEXT,value REAL,status TEXT,provenance_json TEXT,
                PRIMARY KEY(master_row,column_id));
            CREATE TABLE observations(master_row TEXT,provider TEXT,player_id TEXT,field TEXT,sample TEXT,status TEXT,value_json TEXT);''')
        con.execute('INSERT INTO players VALUES(?,?,?,?)', ('one|England', 'England', '["One"]', '["opta:1"]'))
        con.execute('INSERT INTO columns VALUES(?,?)', ('shots', '[["opta","shots"]]'))
        origins = [{'provider': p, 'player_id': '1', 'field': 'shots', 'sample': 'season'} for p in ('opta', 'pitchapi')]
        con.execute('INSERT INTO cells VALUES(?,?,?,?,?)', ('one|England', 'shots', None, 'source_conflict', json.dumps(origins)))
        con.executemany('INSERT INTO observations VALUES(?,?,?,?,?,?,?)',
            [('one|England', p, '1', 'shots', 'season', 'numeric', str(v)) for p, v in [('opta', 0), ('pitchapi', 5)]])
    for name in ('players.csv', 'master_players.csv'):
        with (folder / name).open('w', newline='') as stream:
            csv.writer(stream).writerows([['master_row','league','season','names','source_ids','shots'],
                ['one|England','England','2025/26','One','opta:1','']])
    return folder


def fingerprints(folder):
    return {p.name: checksum(p) for p in folder.iterdir() if p.is_file()}


def test_priority_revision_is_consistent_and_retry_reuses_it(snapshot):
    original = fingerprints(snapshot)
    result = resolve_master(snapshot)
    revision = Path(result['revision_path'])
    assert result['resolved'] == 1
    assert resolve_master(snapshot) == result
    manifest = master_snapshot.validate_revision(revision)
    assert manifest['transition']['status'] == 'complete'
    with sqlite3.connect(revision / 'master.sqlite') as con:
        assert con.execute('SELECT value,status FROM cells').fetchone() == (0, 'resolved_by_priority')
    assert fingerprints(snapshot) == original


@pytest.mark.parametrize('failure_point', ['write_exports', 'validate_revision'])
def test_interruption_preserves_input_and_retry_finishes(snapshot, monkeypatch, failure_point):
    original = fingerprints(snapshot)
    operation = getattr(master_snapshot, failure_point)
    def fail(*args, **kwargs):
        raise OSError('injected interruption')
    monkeypatch.setattr(master_snapshot, failure_point, fail)
    with pytest.raises(OSError, match='interruption'):
        resolve_master(snapshot)
    assert fingerprints(snapshot) == original
    failed = list(snapshot.parent.glob('.original.priority-*/FAILED.json'))
    assert len(failed) == 1
    assert json.loads(failed[0].read_text())['status'] == 'incomplete'
    monkeypatch.setattr(master_snapshot, failure_point, operation)
    assert master_snapshot.validate_revision(Path(resolve_master(snapshot)['revision_path']))


def test_concurrent_writer_is_rejected(snapshot):
    with master_snapshot.writer_guard(snapshot), pytest.raises(RuntimeError, match='Another master transition'):
        fill_missing(snapshot)


def test_completed_revision_tampering_is_rejected(snapshot):
    revision = Path(resolve_master(snapshot)['revision_path'])
    (revision / 'players.csv').write_text('corrupt')
    with pytest.raises(ValueError, match='checksum mismatch'):
        resolve_master(snapshot)
