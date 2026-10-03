import hashlib
import json
from pathlib import Path

import pytest

from amplifier_portability.evidence import canonical_bytes
from amplifier_portability.payloads import CHUNK_BYTES, PayloadStore


def seal(body):
    raw = canonical_bytes(body)
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bodyJson': raw.decode()}


def transfer(source, target, plan):
    body = source.verify_plan(plan, accept_partial=True)
    for descriptor in body['pages']:
        raw = source.read(descriptor['sha256'], descriptor['bytes'])
        target.put(raw, descriptor['sha256'])
        for row in json.loads(raw):
            for chunk in row.get('chunks', []):
                target.put(source.read(chunk['sha256'], chunk['bytes']), chunk['sha256'])


def test_large_attachment_two_independent_stores_exact_bytes_partial_review(tmp_path):
    source, target = [PayloadStore(tmp_path / side) for side in ('source', 'target')]
    path = tmp_path / 'attachment'
    raw = (b'\x00\xffcanonical body\r\n' * 600000) + b'end'
    assert len(raw) > 8 * 1024 * 1024
    path.write_bytes(raw)
    plan = source.build('resources', 'native-revision', [{'id': 'attachment-1', 'path': path}, {'id': 'offline-remote', 'reason': 'transport-expired; source retained'}])
    with pytest.raises(ValueError, match='preview'):
        source.page(plan)
    row = source.page(plan, accept_partial=True)['items'][0]
    assert b''.join(source.read(c['sha256'], c['bytes']) for c in row['chunks']) == raw
    transfer(source, target, plan)
    receipt = target.audit(plan, accept_partial=True)
    assert receipt['bytes'] == len(raw) and receipt['omitted'] == 1
    assert receipt['executionAuthority'] is False and receipt['replayed'] is False
    assert path.read_bytes() == raw
    assert 'path' not in row and str(tmp_path) not in plan['bodyJson']


def test_lost_transport_has_no_success_and_resume_copies_only_immutable_bytes(tmp_path):
    source, target = [PayloadStore(tmp_path / side) for side in ('a', 'b')]
    path = tmp_path / 'body'; path.write_bytes(b'first' * CHUNK_BYTES)
    plan = source.build('resources', 1, [{'id': 'body', 'path': path}])
    descriptor = source.verify_plan(plan)['pages'][0]
    target.put(source.read(descriptor['sha256'], descriptor['bytes']), descriptor['sha256'])
    with pytest.raises(FileNotFoundError):
        target.audit(plan)
    transfer(source, target, plan)
    assert target.audit(plan)['bytes'] == path.stat().st_size
    # Lost acknowledgement is reconciled by immutable identity; no new capture.
    transfer(source, target, plan)
    assert target.audit(plan)['sha256'] == plan['sha256']


def test_selected_page_does_not_read_unrelated_pages_or_bodies(tmp_path, monkeypatch):
    store = PayloadStore(tmp_path / 'store')
    plan = store.build('resources', 1, ({'id': str(i), 'reason': 'not selected'} for i in range(1000)))
    body = store.verify_plan(plan, accept_partial=True)
    assert len(body['pages']) == 40
    allowed = body['pages'][0]['sha256']
    original = store.read
    def selected(identity, size):
        assert identity == allowed
        return original(identity, size)
    monkeypatch.setattr(store, 'read', selected)
    page = store.page(plan, accept_partial=True)
    assert len(page['items']) == 25 and page['nextCursor'].startswith(plan['sha256'])
    other = store.build('resources', 2, [])
    with pytest.raises(ValueError, match='different'):
        store.page(other, cursor=page['nextCursor'])


def test_corrupt_page_chunk_and_whole_digest_are_refused(tmp_path):
    store = PayloadStore(tmp_path / 'store'); path = tmp_path / 'body'; path.write_bytes(b'exact')
    plan = store.build('resources', 1, [{'id': 'body', 'path': path}])
    row = store.page(plan)['items'][0]
    with pytest.raises(ValueError, match='Whole'):
        store.verify_resource({**row, 'sha256': '0' * 64})
    chunk = store.directory / row['chunks'][0]['sha256']; chunk.write_bytes(b'wrong')
    with pytest.raises(ValueError, match='integrity'):
        store.audit(plan)
    descriptor = store.verify_plan(plan)['pages'][0]
    (store.directory / descriptor['sha256']).write_bytes(b'[]')
    with pytest.raises(ValueError, match='integrity'):
        store.page(plan)


def test_secret_split_across_chunk_boundary_and_symlinks_refused(tmp_path):
    store = PayloadStore(tmp_path / 'store'); path = tmp_path / 'secret'
    path.write_bytes(b'.' * (CHUNK_BYTES - 4) + b'api_key=recognizable-secret')
    with pytest.raises(ValueError, match='credential'):
        store.build('resources', 1, [{'id': 'body', 'path': path}])
    link = tmp_path / 'link'; link.symlink_to(path)
    with pytest.raises(ValueError, match='links'):
        store.build('resources', 1, [{'id': 'body', 'path': link}])
    alias = tmp_path / 'alias'; alias.symlink_to(store.directory, target_is_directory=True)
    with pytest.raises(ValueError, match='links'):
        PayloadStore(alias)


def test_aggregate_lies_duplicates_and_authority_refused(tmp_path):
    store = PayloadStore(tmp_path / 'store'); path = tmp_path / 'body'; path.write_bytes(b'exact')
    plan = store.build('resources', 1, [{'id': 'body', 'path': path}])
    body = store.verify_plan(plan)
    with pytest.raises(ValueError, match='aggregate'):
        store.audit(seal({**body, 'bytes': 1}))
    with pytest.raises(ValueError, match='Historical'):
        store.verify_plan(seal({**body, 'executionAuthority': True}))
    descriptor = body['pages'][0]
    duplicate = {**body, 'pages': [descriptor, descriptor], 'items': 2, 'bytes': 10}
    with pytest.raises(ValueError, match='Duplicate'):
        store.audit(seal(duplicate))
    with pytest.raises(ValueError, match='Unique'):
        store.build('resources', 1, [{'id': 'same', 'reason': 'offline'}, {'id': 'same', 'reason': 'offline'}])


def test_empty_body_manifest_and_exact_put(tmp_path):
    store = PayloadStore(tmp_path / 'store'); path = tmp_path / 'empty'; path.write_bytes(b'')
    assert store.audit(store.build('resources', 1, []))['items'] == 0
    plan = store.build('resources', 1, [{'id': 'empty', 'path': path}])
    assert store.audit(plan)['bytes'] == 0
    with pytest.raises(ValueError, match='integrity'):
        store.put(b'wrong', '0' * 64)
    with pytest.raises(ValueError, match='bound'):
        store.put(b'x' * (CHUNK_BYTES + 1))


def test_capture_mutation_refuses_sealing_and_preserves_source(tmp_path, monkeypatch):
    import os
    store = PayloadStore(tmp_path / 'store'); path = tmp_path / 'body'; path.write_bytes(b'original')
    original = os.fstat
    calls = 0
    def changed(fd):
        nonlocal calls
        value = original(fd)
        calls += 1
        if calls == 2:
            from types import SimpleNamespace
            return SimpleNamespace(st_size=value.st_size, st_mtime_ns=value.st_mtime_ns + 1, st_ctime_ns=value.st_ctime_ns)
        return value
    monkeypatch.setattr(os, 'fstat', changed)
    with pytest.raises(ValueError, match='changed'):
        store.build('resources', 1, [{'id': 'body', 'path': path}])
    assert path.read_bytes() == b'original'


@pytest.mark.parametrize('delta', [
    {'version': True}, {'items': True}, {'bytes': -1}, {'omitted': 1},
    {'pages': [{'sha256': '0' * 64, 'bytes': 262145, 'items': 1}]},
])
def test_foreign_plan_invalid_bounds_refused(tmp_path, delta):
    store = PayloadStore(tmp_path / 'store')
    body = store.verify_plan(store.build('resources', 1, []))
    with pytest.raises(ValueError):
        store.verify_plan(seal({**body, **delta}), accept_partial=True)


def test_resource_bounds_and_duplicate_json_are_rejected(tmp_path):
    store = PayloadStore(tmp_path / 'store')
    plan = store.build('resources', 1, [])
    raw = plan['bodyJson'][:-1] + ',"version":1}'
    with pytest.raises(ValueError, match='Duplicate'):
        store.verify_plan({'bodyJson': raw, 'sha256': hashlib.sha256(raw.encode()).hexdigest()})
    row = {'id': 'body', 'executionAuthority': False, 'disposition': 'included',
           'sha256': '0' * 64, 'bytes': True, 'chunks': []}
    with pytest.raises(ValueError, match='bound'):
        store.verify_resource(row)
    path = tmp_path / 'large'
    with path.open('wb') as stream:
        stream.truncate(64 * 1024 * 1024 + 1)
    with pytest.raises(ValueError, match='omission'):
        store.build('resources', 1, [{'id': 'large', 'path': path}])
    assert path.stat().st_size == 64 * 1024 * 1024 + 1


@pytest.mark.parametrize('case', ['over-budget', 'understated-total', 'wrong-omissions', 'duplicate'])
def test_audit_preflights_all_metadata_before_any_body_read(tmp_path, monkeypatch, case):
    from amplifier_portability.payloads import MAX_RESOURCE_BYTES, MAX_TOTAL_BYTES
    store = PayloadStore(tmp_path / 'store')
    chunk = {'sha256': '0' * 64, 'bytes': CHUNK_BYTES}
    count = 17 if case == 'over-budget' else 2
    rows = [{'id': f'resource-{i}', 'executionAuthority': False, 'disposition': 'included',
             'bytes': MAX_RESOURCE_BYTES, 'sha256': '0' * 64,
             'chunks': [chunk] * (MAX_RESOURCE_BYTES // CHUNK_BYTES)} for i in range(count)]
    if case == 'duplicate':
        rows[-1]['id'] = rows[0]['id']
    pages = []
    for offset in range(0, len(rows), 10):
        selected = rows[offset:offset + 10]; raw = canonical_bytes(selected)
        pages.append({'sha256': store.put(raw), 'bytes': len(raw), 'items': len(selected)})
    total = MAX_TOTAL_BYTES if case == 'over-budget' else MAX_RESOURCE_BYTES * count
    if case == 'understated-total':
        total -= 1
    omitted = 1 if case == 'wrong-omissions' else 0
    plan = seal({'version': 1, 'owner': 'resources', 'revision': 1, 'items': count,
                 'bytes': total, 'omitted': omitted, 'pages': pages,
                 'executionAuthority': False, 'disposition': 'partial' if omitted else 'complete'})
    calls = []
    def body_read(row):
        calls.append(row['id'])
        raise AssertionError('Body verification must follow complete metadata preflight')
    monkeypatch.setattr(store, 'verify_resource', body_read)
    with pytest.raises(ValueError, match='aggregate|Duplicate'):
        store.audit(plan, accept_partial=True)
    assert calls == []
