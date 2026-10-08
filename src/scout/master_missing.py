"""Apply the user-requested numeric zero label after merging and source selection."""
import json
from datetime import UTC, datetime
from pathlib import Path

from scout.master_snapshot import SnapshotChange, transition
from scout.source_audit import checksum

VERSION = 'unrecorded-master-zero-v1'


def fill_missing(folder: Path):
    return transition(folder, 'zero-fill', VERSION, _fill, __file__)


def _fill(con):
    missing = con.execute('''SELECT COUNT(*) FROM players p CROSS JOIN columns c
        LEFT JOIN cells x ON x.master_row=p.master_row AND x.column_id=c.column_id
        WHERE x.value IS NULL''').fetchone()[0]
    if not missing:
        return SnapshotChange({'zero_filled': 0, 'remaining_missing': 0}, 'zero-fill.json')
    evidence = json.dumps([{'evidence': 'unrecorded', 'policy_version': VERSION,
                            'stage': 'after_feature_union_and_source_priority'}])
    if 'selected_provider' not in {r[1] for r in con.execute('PRAGMA table_info(cells)')}:
        con.execute('ALTER TABLE cells ADD COLUMN selected_provider TEXT')
    with con:
        con.execute('''CREATE TABLE missing_cells_before_zero AS
            SELECT * FROM cells WHERE value IS NULL''')
        con.execute('''UPDATE cells SET value=0,status='unrecorded_zero',selected_provider=NULL
                       WHERE value IS NULL''')
        con.execute('''INSERT INTO cells(master_row,column_id,value,status,provenance_json,selected_provider)
            SELECT p.master_row,c.column_id,0,'unrecorded_zero',?,NULL
            FROM players p CROSS JOIN columns c
            LEFT JOIN cells x ON x.master_row=p.master_row AND x.column_id=c.column_id
            WHERE x.master_row IS NULL''', (evidence,))
    total = con.execute('SELECT COUNT(*) FROM players').fetchone()[0] * con.execute('SELECT COUNT(*) FROM columns').fetchone()[0]
    assert con.execute('SELECT COUNT(*) FROM cells').fetchone()[0] == total
    assert con.execute('SELECT COUNT(*) FROM cells WHERE value IS NULL').fetchone()[0] == 0
    summary = {'version': VERSION, 'created_at': datetime.now(UTC).isoformat(),
               'zero_filled': missing, 'remaining_missing': 0, 'numeric_cells': total,
               'code_sha256': checksum(__file__), 'status': 'unrecorded_zero',
               'rule': 'After source union and priority selection, all unrecorded numeric master values are labelled zero; original evidence remains unchanged.'}
    return SnapshotChange(summary, 'zero-fill.json', metadata={'missing_value_policy': summary},
        limitations=('Unrecorded numeric master values are labelled 0 by user instruction; unrecorded_zero status distinguishes these from observed zeros.',))
