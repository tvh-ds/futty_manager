import csv
import json
import sqlite3
from pathlib import Path

from scout.master_missing import fill_missing


def test_fill_after_merge_preserves_observed_values_and_tracks_unrecorded_zeros(tmp_path):
    columns = [{'id': 'shots', 'label': 'shots'}, {'id': 'assists', 'label': 'assists'}]
    (tmp_path/'columns.json').write_text(json.dumps(columns))
    (tmp_path/'manifest.json').write_text(json.dumps({'outputs': {}, 'limitations': []}))
    with sqlite3.connect(tmp_path/'master.sqlite') as con:
        con.executescript('''CREATE TABLE players(master_row TEXT PRIMARY KEY,league TEXT,names_json TEXT,sources_json TEXT);
            CREATE TABLE columns(column_id TEXT PRIMARY KEY);
            CREATE TABLE cells(master_row TEXT,column_id TEXT,value REAL,status TEXT,provenance_json TEXT,
                               PRIMARY KEY(master_row,column_id));''')
        con.executemany('INSERT INTO players VALUES(?,?,?,?)',
            [('a', 'England', '["A"]', '["opta:a"]'), ('b', 'England', '["B"]', '["pitchapi:b"]')])
        con.executemany('INSERT INTO columns VALUES(?)', [('shots',), ('assists',)])
        con.executemany('INSERT INTO cells VALUES(?,?,?,?,?)',
                        [('a','shots',10,'resolved_by_priority','[]'), ('a','assists',0,'observed','[]'),
                         ('b','shots',None,'unavailable','[]')])
    for name in ('players.csv','master_players.csv'):
        with (tmp_path/name).open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['master_row','league','season','names','source_ids','shots','assists'])
            writer.writerow(['a','England','2025/26','A','opta:a',10,0])
            writer.writerow(['b','England','2025/26','B','pitchapi:b','',''])
    summary = fill_missing(tmp_path)
    revision = Path(summary['revision_path'])
    assert summary['zero_filled'] == 2
    with sqlite3.connect(revision/'master.sqlite') as con:
        assert con.execute("SELECT value,status FROM cells WHERE master_row='a' AND column_id='shots'").fetchone() == (10,'resolved_by_priority')
        assert con.execute("SELECT value,status FROM cells WHERE master_row='a' AND column_id='assists'").fetchone() == (0,'observed')
        assert con.execute("SELECT COUNT(*) FROM cells WHERE value=0 AND status='unrecorded_zero'").fetchone()[0] == 2
    with (revision/'master_players.csv').open(newline='') as stream:
        records = list(csv.DictReader(stream))
    assert float(records[1]['shots']) == float(records[1]['assists']) == 0
    assert fill_missing(revision)['zero_filled'] == 0
    assert fill_missing(tmp_path) == summary
    with sqlite3.connect(tmp_path/'master.sqlite') as con:
        assert con.execute("SELECT value FROM cells WHERE master_row='b'").fetchone() == (None,)
