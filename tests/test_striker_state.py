import hashlib
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scout import striker_state
from scout.striker_state import pack_state, restore_cloud, restore_files, save_cloud, unpack_state


def seed(root):
    provider = root / 'provider/2026-10'
    provider.mkdir(parents=True)
    (provider / 'checkpoint.json').write_text(json.dumps({'day': '2026-10-06', 'used': 12, 'completed': {}}))
    (root / 'refresh-status.json').write_text('{"activated": false}')


def zipped(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('state-manifest.json', json.dumps({'schema': 1, 'files': {
            name: hashlib.sha256(content).hexdigest() for name, content in files.items()}}))
        for name, content in files.items():
            archive.writestr(name, content)
    data = out.getvalue()
    return data, hashlib.sha256(data).hexdigest()


def test_private_state_roundtrip_preserves_quota_and_refuses_overwrite(tmp_path):
    original, restored = tmp_path / 'original', tmp_path / 'restored'
    seed(original)
    data = pack_state(original)
    files = unpack_state(data, hashlib.sha256(data).hexdigest())
    restore_files(files, restored)
    assert (restored / 'provider/2026-10/checkpoint.json').read_bytes() == (original / 'provider/2026-10/checkpoint.json').read_bytes()
    with pytest.raises(ValueError, match='empty'):
        restore_files(files, restored)


@pytest.mark.parametrize('name', ['../outside.json', '/absolute.json', 'provider/2026-10/../../secret.json',
                                 '.env', 'releases/bad-id/profiles.json'])
def test_snapshot_rejects_unexpected_paths_even_with_matching_checksums(name):
    data, checksum = zipped({name: b'secret'})
    with pytest.raises(ValueError, match='path'):
        unpack_state(data, checksum)


def test_snapshot_rejects_checksum_corruption_and_size(tmp_path, monkeypatch):
    seed(tmp_path / 'state')
    data = pack_state(tmp_path / 'state')
    with pytest.raises(ValueError, match='checksum'):
        unpack_state(data, '0' * 64)
    monkeypatch.setattr(striker_state, 'MAX_BYTES', 10)
    with pytest.raises(ValueError, match='size'):
        unpack_state(data, hashlib.sha256(data).hexdigest())


def test_duplicate_zip_members_rejected():
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as archive:
        archive.writestr('state-manifest.json', '{}')
        with pytest.warns(UserWarning):
            archive.writestr('state-manifest.json', '{}')
    data = out.getvalue()
    with pytest.raises(ValueError, match='Invalid'):
        unpack_state(data, hashlib.sha256(data).hexdigest())


def test_active_release_must_exist_and_be_intact():
    release = 'strikers-202610-' + '0' * 12
    with pytest.raises(ValueError, match='missing'):
        restore_files({'active.json': json.dumps({'release_id': release}).encode()}, Path('unused'))
    files = {f'releases/{release}/{name}': b'fixture' for name in striker_state.RELEASE_FILES - {'manifest.json'}}
    files[f'releases/{release}/manifest.json'] = json.dumps({'id': release, 'files': {
        name: '0' * 64 for name in striker_state.RELEASE_FILES - {'manifest.json'}}}).encode()
    data, checksum = zipped(files)
    with pytest.raises(ValueError, match='checksum'):
        unpack_state(data, checksum)


def test_incomplete_unpublished_release_not_persisted(tmp_path):
    seed(tmp_path / 'state')
    incomplete = tmp_path / 'state/releases/strikers-202610-000000000000'
    incomplete.mkdir(parents=True)
    (incomplete / 'bronze.json').write_text('[]')
    data = pack_state(tmp_path / 'state')
    files = unpack_state(data, hashlib.sha256(data).hexdigest())
    assert not any(name.startswith('releases/') for name in files)


class Blob:
    def __init__(self):
        self.data, self.version, self.fail = None, 0, False

    def get_blob_properties(self):
        from azure.core.exceptions import ResourceNotFoundError
        if self.data is None:
            raise ResourceNotFoundError('missing')
        return SimpleNamespace(size=len(self.data), etag=str(self.version))

    def download_blob(self, **kwargs):
        from azure.core.exceptions import ResourceModifiedError
        if kwargs.get('etag', str(self.version)) != str(self.version):
            raise ResourceModifiedError('changed')
        return SimpleNamespace(chunks=lambda: iter([self.data]))

    def upload_blob(self, data, overwrite, **kwargs):
        from azure.core.exceptions import ResourceExistsError, ResourceModifiedError
        if self.fail:
            raise RuntimeError('simulated transport failure')
        if self.data is not None and not overwrite:
            raise ResourceExistsError('exists')
        if kwargs.get('etag', str(self.version)) != str(self.version):
            raise ResourceModifiedError('changed')
        self.data, self.version = data, self.version + 1


@pytest.fixture
def container():
    pytest.importorskip('azure.core')
    blobs = {}
    return SimpleNamespace(get_blob_client=lambda name: blobs.setdefault(name, Blob()), blobs=blobs)


def test_cloud_state_restore_and_failed_save_keep_previous_pointer(tmp_path, container):
    first = tmp_path / 'first'
    seed(first)
    assert restore_cloud(first, container)['restored'] is False
    save_cloud(first, container, None)
    pointer = container.blobs['striker-state/current.json']
    old_pointer = pointer.data
    restored = tmp_path / 'restored'
    generation = restore_cloud(restored, container)
    assert generation['restored'] and generation['etag'] == '1'
    assert json.loads((restored / 'provider/2026-10/checkpoint.json').read_text())['used'] == 12
    (restored / 'refresh-status.json').write_text('{"failure":"schema change"}')
    pointer.fail = True
    with pytest.raises(RuntimeError):
        save_cloud(restored, container, generation['etag'])
    assert pointer.data == old_pointer
    assert restore_cloud(tmp_path / 'recovered', container)['restored']


def test_stale_runner_cannot_overwrite_newer_cloud_state(tmp_path, container):
    from azure.core.exceptions import ResourceModifiedError
    seed(tmp_path / 'first')
    save_cloud(tmp_path / 'first', container, None)
    old = restore_cloud(tmp_path / 'old', container)
    current = restore_cloud(tmp_path / 'current', container)
    (tmp_path / 'current/refresh-status.json').write_text('{"newer":true}')
    save_cloud(tmp_path / 'current', container, current['etag'])
    pointer = container.blobs['striker-state/current.json']
    newer = pointer.data
    with pytest.raises(ResourceModifiedError):
        save_cloud(tmp_path / 'old', container, old['etag'])
    assert pointer.data == newer


def test_corrupt_remote_archive_cannot_install_files(tmp_path, container):
    seed(tmp_path / 'original')
    saved = save_cloud(tmp_path / 'original', container, None)
    container.blobs[f"striker-state/snapshots/{saved['sha256']}.zip"].data = b'corrupt'
    target = tmp_path / 'restore'
    with pytest.raises(ValueError, match='checksum'):
        restore_cloud(target, container)
    assert not target.exists()


def test_public_container_is_rejected_without_modification(monkeypatch, container):
    from azure.storage.blob import BlobServiceClient
    container.get_container_properties = lambda: {'public_access': 'blob'}
    monkeypatch.setattr(BlobServiceClient, 'get_container_client', lambda self, name: container)
    with pytest.raises(ValueError, match='private'):
        striker_state.private_container('testonlyaccount')
    assert not container.blobs


def test_oversized_remote_pointer_rejected_before_restore(tmp_path, container):
    pointer = container.get_blob_client('striker-state/current.json')
    pointer.upload_blob(b' ' * 5000, overwrite=False)
    target = tmp_path / 'restore'
    with pytest.raises(ValueError, match='size'):
        restore_cloud(target, container)
    assert not target.exists()
