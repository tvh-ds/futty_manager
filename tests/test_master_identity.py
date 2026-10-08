import csv
import json
import sqlite3
from pathlib import Path

from scout.master_identity import choose_cell, identity_groups, merge_names


def test_name_merge_normalizes_accents_but_keeps_leagues_separate():
    rows = [{'row': 'a', 'league': 'England', 'names': ['José Silva']},
            {'row': 'b', 'league': 'England', 'names': ['Jose Silva']},
            {'row': 'c', 'league': 'Spain', 'names': ['Jose Silva']}]
    assert sorted(len(g) for g in identity_groups(rows)) == [1, 2]


def test_cell_priority_keeps_zero_even_when_other_row_is_more_complete():
    candidates = [{'provider': 'pitchapi', 'value': 20, 'coverage': 100, 'original_row': 'a'},
                  {'provider': 'opta', 'value': 0, 'coverage': 5, 'original_row': 'b'}]
    assert choose_cell(candidates)['value'] == 0


def test_merge_unions_features_selects_priority_and_preserves_raw_rows(tmp_path):
    columns = [{'id': 'shots', 'label': 'shots'}, {'id': 'assists', 'label': 'assists'}]
    (tmp_path/'columns.json').write_text(json.dumps(columns))
    (tmp_path/'manifest.json').write_text(json.dumps({'outputs': {}, 'limitations': [], 'master_rows': 3}))
    with sqlite3.connect(tmp_path/'master.sqlite') as con:
        con.executescript('''CREATE TABLE players(master_row TEXT PRIMARY KEY,league TEXT,names_json TEXT,sources_json TEXT);
            CREATE TABLE columns(column_id TEXT PRIMARY KEY);
            CREATE TABLE cells(master_row TEXT,column_id TEXT,value REAL,status TEXT,provenance_json TEXT,PRIMARY KEY(master_row,column_id));
            CREATE TABLE observations(provider TEXT,player_id TEXT,league TEXT,season TEXT,master_row TEXT,field TEXT,scope TEXT,sample TEXT,status TEXT,value_json TEXT);''')
        con.executemany('INSERT INTO columns VALUES(?)', [('shots',), ('assists',)])
        for row, provider, name in [('a', 'opta', 'José Silva'), ('b', 'pitchapi', 'Jose Silva'), ('c', 'understat', 'JOSE SILVA')]:
            con.execute('INSERT INTO players VALUES(?,?,?,?)', (row, 'England', json.dumps([name]), json.dumps([provider+':1'])))
            con.execute('INSERT INTO observations VALUES(?,?,?,?,?,?,?,?,?,?)', (provider, '1', 'England', '2025/26', row, 'shots', 'aggregate', '1', 'numeric', '10'))
        for row, provider, col, val in [('a','opta','shots',10), ('b','pitchapi','shots',8), ('c','understat','shots',12), ('c','understat','assists',0)]:
            con.execute('INSERT INTO cells VALUES(?,?,?,?,?)', (row,col,val,'observed',json.dumps([{'provider':provider}])))
    for name in ('players.csv', 'master_players.csv'):
        with (tmp_path/name).open('w',newline='') as stream:
            writer=csv.writer(stream)
            writer.writerow(['master_row','league','season','names','source_ids','shots','assists'])
    report = merge_names(tmp_path)
    revision = Path(report['revision_path'])
    assert report['rows_after'] == 1 and report['duplicates_removed'] == 2
    with sqlite3.connect(revision/'master.sqlite') as con:
        assert con.execute("SELECT value,selected_provider FROM cells WHERE column_id='shots'").fetchone() == (10, 'opta')
        assert con.execute("SELECT value,selected_provider FROM cells WHERE column_id='assists'").fetchone() == (0, 'understat')
        assert con.execute('SELECT COUNT(DISTINCT master_row) FROM observations').fetchone()[0] == 3
        assert con.execute('SELECT COUNT(DISTINCT master_row) FROM observations_canonical').fetchone()[0] == 1
        assert con.execute('SELECT COUNT(*) FROM players_pre_name_merge').fetchone()[0] == 3
    assert merge_names(revision)['duplicates_removed'] == 0
    assert merge_names(tmp_path) == report
    with sqlite3.connect(tmp_path/'master.sqlite') as con:
        assert con.execute('SELECT COUNT(*) FROM players').fetchone()[0] == 3
