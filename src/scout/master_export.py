"""Readable CSV companion to the stable-ID master export."""
import csv
import json
import math
from pathlib import Path

from scout.real_data import read_json
from scout.source_audit import checksum


def safe_cell(value):
    # Source names are untrusted text; opening the export must not execute formulas.
    try:
        if math.isfinite(float(value)):
            return value
    except ValueError:
        pass
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else value


def export_named(folder: Path, *, overwrite=False):
    target = folder / 'master_players.csv'
    if target.exists() and not overwrite:
        raise FileExistsError('Readable master export already exists')
    columns = read_json(folder / 'columns.json')
    labels = {c['id']: c['label'] for c in columns}
    with (folder / 'players.csv').open(encoding='utf-8', newline='') as source, target.open('w', encoding='utf-8', newline='') as dest:
        reader, writer = csv.reader(source), csv.writer(dest)
        headers = next(reader)
        named = [labels.get(header, header) for header in headers]
        if len(set(named)) != len(named):
            raise ValueError('Non-unique readable headers')
        writer.writerow([safe_cell(h) for h in named])
        for row in reader:
            writer.writerow([safe_cell(value) for value in row])
    manifest = read_json(folder / 'manifest.json')
    manifest['outputs'][target.name] = checksum(target)
    manifest['readable_export'] = {'code_sha256': checksum(__file__),
                                   'formula_escape': 'Text beginning with formula markers is prefixed with an apostrophe.'}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    return target
