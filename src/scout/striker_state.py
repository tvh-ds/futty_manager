"""Private monthly-runner state; content addressed, verified before restoration.

No container creation, subscription changes, public artifacts or stored secrets.
The cloud pointer changes only after an immutable state archive was uploaded.
"""
import hashlib
import io
import json
import re
import uuid
import zipfile
from pathlib import Path

MAX_BYTES = 256_000_000
MAX_FILES = 25_000
RELEASE = r"strikers-\d{6}-[a-f0-9]{12}"
RELEASE_FILES = {"bronze.json", "silver.parquet", "gold.parquet", "profiles.json", "manifest.json"}
PROVIDER_FILE = r"(?:checkpoint|[a-f0-9]{64}-[a-f0-9]{64})\.json"


def allowed_path(name):
    return (name in {"active.json", "refresh-status.json"}
            or re.fullmatch(rf"releases/{RELEASE}/(?:{'|'.join(re.escape(f) for f in RELEASE_FILES)})", name)
            or re.fullmatch(rf"provider/\d{{4}}-\d{{2}}/{PROVIDER_FILE}", name))


def validate_files(files):
    """Validate both archive integrity and each completed release's manifest."""
    if len(files) > MAX_FILES or sum(len(v) for v in files.values()) > MAX_BYTES:
        raise ValueError("Striker state exceeds bounded snapshot size")
    if any(not allowed_path(name) for name in files):
        raise ValueError("Unexpected state file path")
    folders = {name.rsplit('/', 1)[0] for name in files if name.startswith('releases/')}
    for folder in folders:
        manifest = json.loads(files.get(f'{folder}/manifest.json', b'null'))
        if (not isinstance(manifest, dict) or manifest.get('id') != folder.split('/')[1]
                or not isinstance(manifest.get('files'), dict)
                or set(manifest['files']) != RELEASE_FILES - {'manifest.json'}):
            raise ValueError("Incomplete striker release manifest")
        for name, checksum in manifest['files'].items():
            content = files.get(f'{folder}/{name}')
            if content is None or hashlib.sha256(content).hexdigest() != checksum:
                raise ValueError("Striker release checksum mismatch")
    if 'active.json' in files:
        pointer = json.loads(files['active.json'])
        release_id = pointer.get('release_id') if isinstance(pointer, dict) else None
        if not isinstance(release_id, str) or not re.fullmatch(RELEASE, release_id):
            raise ValueError("Invalid active striker state pointer")
        if f'releases/{release_id}/manifest.json' not in files:
            raise ValueError("Active striker release missing from state")


def pack_state(root: Path):
    if root.is_symlink() or root.is_junction():
        raise ValueError("State root must not be a symbolic link")
    files = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or path.is_junction() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("State must not contain symbolic links")
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        if not allowed_path(name):
            raise ValueError("Unexpected local state file")
        # A killed refresh can leave an unpublished, partial release directory.
        if name.startswith('releases/') and not (path.parent / 'manifest.json').exists():
            continue
        if path.stat().st_size > MAX_BYTES or sum(map(len, files.values())) + path.stat().st_size > MAX_BYTES:
            raise ValueError("Striker state exceeds bounded snapshot size")
        files[name] = path.read_bytes()
    validate_files(files)
    manifest = {'schema': 1, 'files': {name: hashlib.sha256(v).hexdigest() for name, v in files.items()}}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('state-manifest.json', json.dumps(manifest, sort_keys=True))
        for name, content in files.items():
            archive.writestr(name, content)
    data = buffer.getvalue()
    if len(data) > MAX_BYTES:
        raise ValueError("Striker archive exceeds bounded snapshot size")
    return data


def unpack_state(data, checksum):
    if len(data) > MAX_BYTES or hashlib.sha256(data).hexdigest() != checksum:
        raise ValueError("Striker state archive checksum or size mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        names = [m.filename for m in members]
        if (len(members) > MAX_FILES + 1 or len(set(names)) != len(names)
                or sum(m.file_size for m in members) > MAX_BYTES
                or any(m.is_dir() or m.compress_type != zipfile.ZIP_STORED for m in members)
                or 'state-manifest.json' not in names):
            raise ValueError("Invalid or oversized striker state archive")
        if any(n != 'state-manifest.json' and not allowed_path(n) for n in names):
            raise ValueError("Unexpected archived state path")
        manifest = json.loads(archive.read('state-manifest.json'))
        expected = manifest.get('files') if isinstance(manifest, dict) else None
        if not isinstance(manifest, dict) or manifest.get('schema') != 1 or not isinstance(expected, dict) or set(expected) != set(names) - {'state-manifest.json'}:
            raise ValueError("Invalid striker state manifest")
        files = {name: archive.read(name) for name in expected}
        if any(hashlib.sha256(content).hexdigest() != expected[name] for name, content in files.items()):
            raise ValueError("Striker state member checksum mismatch")
    validate_files(files)
    return files


def restore_files(files, root: Path):
    """Install only into an empty runner directory; never replace local work."""
    validate_files(files)
    if root.is_symlink() or root.is_junction() or root.exists() and any(root.iterdir()):
        raise ValueError("Restore requires an empty state directory")
    root.parent.mkdir(parents=True, exist_ok=True)
    stage = root.parent / f'{root.name}-restore-{uuid.uuid4().hex}'
    stage.mkdir()
    for name, content in files.items():
        target = stage / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    if root.exists():
        root.rmdir()  # Empty directory only, verified above; never recursive.
    stage.replace(root)


def private_container(account):
    from azure.identity import AzureCliCredential
    from azure.storage.blob import BlobServiceClient
    if not re.fullmatch(r'[a-z0-9]{3,24}', account):
        raise ValueError("Invalid Azure storage account")
    service = BlobServiceClient(f'https://{account}.blob.core.windows.net', credential=AzureCliCredential(),
                               retry_total=2, connection_timeout=10, read_timeout=60)
    container = service.get_container_client('backups')
    if container.get_container_properties().get('public_access') is not None:
        raise ValueError("Striker runner state requires a private container")
    return container


def read_blob(blob, maximum, etag=None):
    from azure.core import MatchConditions
    if blob.get_blob_properties().size > maximum:
        raise ValueError("Private state blob exceeds size limit")
    buffer = io.BytesIO()
    conditions = {'etag': etag, 'match_condition': MatchConditions.IfNotModified} if etag else {}
    for chunk in blob.download_blob(**conditions).chunks():
        if buffer.tell() + len(chunk) > maximum:
            raise ValueError("Private state download exceeds size limit")
        buffer.write(chunk)
    return buffer.getvalue()


def restore_cloud(root: Path, container):
    from azure.core.exceptions import ResourceNotFoundError
    pointer_blob = container.get_blob_client('striker-state/current.json')
    try:
        etag = pointer_blob.get_blob_properties().etag
        document = json.loads(read_blob(pointer_blob, 4096, etag))
    except ResourceNotFoundError:
        return {'restored': False, 'etag': None, 'reason': 'No private state pointer exists'}
    checksum = document.get('sha256') if isinstance(document, dict) else None
    if not isinstance(checksum, str) or document.get('schema') != 1 or not re.fullmatch(r'[a-f0-9]{64}', checksum):
        raise ValueError("Invalid private state pointer")
    data = read_blob(container.get_blob_client(f'striker-state/snapshots/{checksum}.zip'), MAX_BYTES)
    restore_files(unpack_state(data, checksum), root)
    return {'restored': True, 'sha256': checksum, 'etag': etag}


def save_cloud(root: Path, container, expected_etag):
    from azure.core import MatchConditions
    from azure.core.exceptions import ResourceExistsError
    pointer_blob = container.get_blob_client('striker-state/current.json')
    data = pack_state(root)
    checksum = hashlib.sha256(data).hexdigest()
    archive = container.get_blob_client(f'striker-state/snapshots/{checksum}.zip')
    try:
        archive.upload_blob(data, overwrite=False)
    except ResourceExistsError:
        if hashlib.sha256(read_blob(archive, MAX_BYTES)).hexdigest() != checksum:
            raise ValueError("Existing immutable state archive is corrupt") from None
    document = json.dumps({'schema': 1, 'sha256': checksum}).encode()
    if expected_etag is None:
        pointer_blob.upload_blob(document, overwrite=False)
    else:
        pointer_blob.upload_blob(document, overwrite=True, etag=expected_etag, match_condition=MatchConditions.IfNotModified)
    return {'saved': True, 'sha256': checksum, 'bytes': len(data)}
