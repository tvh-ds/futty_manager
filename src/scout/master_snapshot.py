"""Private master revision lifecycle; policies mutate only a staged database."""
import csv
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from itertools import zip_longest
from pathlib import Path

from scout.master_export import export_named, safe_cell
from scout.real_data import read_json
from scout.source_audit import checksum


@dataclass
class SnapshotChange:
    summary: dict
    audit_name: str
    audit: dict | None = None
    metadata: dict = field(default_factory=dict)
    limitations: tuple[str, ...] = ()
    remove_limitations: tuple[str, ...] = ()


@contextmanager
def writer_guard(source):
    """OS-owned lock releases even if the process exits; no stale PID guessing."""
    path = source.parent / (source.name + '.transition.lock')
    if path.is_symlink():
        raise ValueError('Snapshot lock cannot be a symbolic link')
    with path.open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError('Another master transition owns this snapshot') from error
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def verify_checksums(folder, manifest):
    for name, expected in manifest.get('outputs', {}).items():
        if Path(name).name != name or not (folder / name).is_file() or (folder / name).is_symlink():
            raise ValueError('Invalid snapshot artifact path')
        if checksum(folder / name) != expected:
            raise ValueError(f'Snapshot checksum mismatch: {name}')


def write_exports(folder):
    columns = read_json(folder / 'columns.json')
    ids = [c['id'] for c in columns]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate master columns')
    with closing(sqlite3.connect(folder / 'master.sqlite')) as con, (folder / 'players.csv').open(
            'w', encoding='utf-8', newline='') as stream:
        if con.execute('PRAGMA integrity_check').fetchone() != ('ok',):
            raise ValueError('Master database integrity check failed')
        if con.execute('SELECT COUNT(*) FROM cells WHERE master_row NOT IN (SELECT master_row FROM players)').fetchone()[0]:
            raise ValueError('Orphaned master cells')
        if con.execute('SELECT COUNT(*) FROM cells WHERE column_id NOT IN (SELECT column_id FROM columns)').fetchone()[0]:
            raise ValueError('Unknown master cell columns')
        if set(ids) != {r[0] for r in con.execute('SELECT column_id FROM columns')}:
            raise ValueError('Column registry differs from database')
        writer = csv.writer(stream)
        writer.writerow(['master_row', 'league', 'season', 'names', 'source_ids', *ids])
        for row, league, names, sources in con.execute(
                'SELECT master_row,league,names_json,sources_json FROM players ORDER BY master_row'):
            cells = dict(con.execute('SELECT column_id,value FROM cells WHERE master_row=?', (row,)))
            writer.writerow([row, league, '2025/26', ' | '.join(json.loads(names)),
                             ' | '.join(json.loads(sources)), *[cells.get(cid) for cid in ids]])
    # Only the private staging directory is rewritten; the source stays intact.
    export_named(folder, overwrite=True)


def validate_revision(folder, *, allow_staging=False):
    if (folder / 'FAILED.json').exists() or ((folder / 'STAGING.json').exists() and not allow_staging):
        raise ValueError('Snapshot transition is incomplete')
    manifest = read_json(folder / 'manifest.json')
    if manifest.get('transition', {}).get('status') != ('staging' if allow_staging else 'complete'):
        raise ValueError('Snapshot transition is not complete')
    verify_checksums(folder, manifest)
    with closing(sqlite3.connect(folder / 'master.sqlite')) as con:
        expected = con.execute('SELECT COUNT(*) FROM players').fetchone()[0]
        if manifest['master_rows'] != expected:
            raise ValueError('Manifest player count differs from database')
    with (folder / 'players.csv').open(encoding='utf-8', newline='') as stream:
        rows = csv.reader(stream)
        header = next(rows)
        count = 0
        for row in rows:
            if len(row) != len(header):
                raise ValueError('Malformed stable export row')
            count += 1
        if count != expected:
            raise ValueError('Stable export does not match snapshot')
    labels = {c['id']: c['label'] for c in read_json(folder / 'columns.json')}
    with (folder / 'master_players.csv').open(encoding='utf-8', newline='') as named, (
            folder / 'players.csv').open(encoding='utf-8', newline='') as stable:
        a, b = csv.reader(named), csv.reader(stable)
        if next(a) != [safe_cell(labels.get(h, h)) for h in next(b)]:
            raise ValueError('Readable export headers do not match registry')
        for readable, raw in zip_longest(a, b):
            if readable is None or raw is None or readable != [safe_cell(v) for v in raw]:
                raise ValueError('Readable export does not match snapshot')
    return manifest


def transition(source: Path, operation: str, version: str, policy, code_path):
    """Return a completed revision, never activate or mutate the input snapshot."""
    source = source.resolve(strict=True)
    with writer_guard(source):
        manifest = read_json(source / 'manifest.json')
        verify_checksums(source, manifest)
        if (source / 'FAILED.json').exists() or (source / 'STAGING.json').exists():
            raise ValueError('Cannot transition an incomplete snapshot')
        if any(p.is_symlink() for p in source.iterdir()):
            raise ValueError('Snapshot artifacts cannot be symbolic links')
        inputs = {p.name: checksum(p) for p in source.iterdir() if p.is_file()}
        # Source is immutable by contract. sqlite backup below still handles WAL.
        identity = hashlib.sha256(json.dumps({'inputs': inputs, 'operation': operation,
            'version': version, 'policy_code': checksum(code_path), 'lifecycle_code': checksum(__file__),
            'export_code': checksum(Path(__file__).with_name('master_export.py'))}, sort_keys=True).encode()).hexdigest()
        target = source.parent / f'{source.name}.{operation}-{identity[:16]}'
        if target.is_symlink():
            raise ValueError('Snapshot revision cannot be a symbolic link')
        if target.exists():
            prior = validate_revision(target)
            if prior.get('transition', {}).get('identity') != identity:
                raise ValueError('Completed revision has incompatible transition identity')
            return {**prior['transition']['summary'], 'revision_path': str(target)}
        stage = Path(tempfile.mkdtemp(prefix=f'.{source.name}.{operation}-', dir=source.parent))
        try:
            (stage / 'STAGING.json').write_text(json.dumps({'parent': str(source), 'operation': operation,
                'identity': identity, 'status': 'incomplete'}), encoding='utf-8')
            for file in source.iterdir():
                if file.is_symlink():
                    raise ValueError('Snapshot artifacts cannot be symbolic links')
                if file.is_file() and file.name not in ('master.sqlite', 'master.sqlite-wal', 'master.sqlite-shm'):
                    shutil.copy2(file, stage / file.name)
            with closing(sqlite3.connect(f'{(source / "master.sqlite").as_uri()}?mode=ro', uri=True)) as original:
                with closing(sqlite3.connect(stage / 'master.sqlite')) as copied:
                    original.backup(copied)
            with closing(sqlite3.connect(stage / 'master.sqlite')) as con, con:
                change = policy(con)
            (stage / change.audit_name).write_text(json.dumps(change.audit or change.summary, indent=2,
                ensure_ascii=False, allow_nan=False), encoding='utf-8')
            manifest.update(change.metadata)
            manifest['limitations'] = [s for s in manifest.get('limitations', [])
                if not any(fragment in s for fragment in change.remove_limitations)]
            manifest['limitations'] += [s for s in change.limitations if s not in manifest['limitations']]
            with closing(sqlite3.connect(stage / 'master.sqlite')) as con, con:
                manifest['master_rows'] = con.execute('SELECT COUNT(*) FROM players').fetchone()[0]
                manifest['cell_status'] = dict(con.execute('SELECT status,COUNT(*) FROM cells GROUP BY status'))
            manifest['transition'] = {'identity': identity, 'operation': operation, 'version': version,
                'parent': str(source), 'inputs': inputs, 'summary': change.summary, 'status': 'staging'}
            # Recompute every existing output after policies and export generation.
            manifest['outputs'] = {}
            (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
            write_exports(stage)
            manifest = read_json(stage / 'manifest.json')
            manifest['outputs'] = {p.name: checksum(p) for p in stage.iterdir()
                if p.is_file() and p.name not in ('manifest.json', 'STAGING.json')}
            (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False,
                allow_nan=False), encoding='utf-8')
            validate_revision(stage, allow_staging=True)
            if {p.name: checksum(p) for p in source.iterdir() if p.is_file()} != inputs:
                raise ValueError('Source snapshot changed during transition')
            # Same parent filesystem. Failed staging remains separate from target.
            if stage.resolve().parent != source.parent or target.parent != source.parent:
                raise ValueError('Revision target is outside the snapshot directory')
            manifest['transition']['status'] = 'complete'
            (stage / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False,
                allow_nan=False), encoding='utf-8')
            (stage / 'STAGING.json').unlink()
            stage.rename(target)
            return {**change.summary, 'revision_path': str(target)}
        except Exception as error:
            (stage / 'FAILED.json').write_text(json.dumps({'status': 'incomplete', 'operation': operation,
                'parent': str(source), 'error_type': type(error).__name__}), encoding='utf-8')
            raise
