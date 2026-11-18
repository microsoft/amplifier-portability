import json,sqlite3,uuid
from pathlib import Path
import pytest
from amplifier_portability.protocol import TransferNode,durable
from amplifier_portability.index import IndexMigrationRequired
from amplifier_portability.evidence import envelope,verify,canonical_bytes

def record(i=1,**kw):
    return dict(id=str(uuid.uuid4()),sessionId='selected',generation=i,createdAt=float(i),updatedAt=float(i),source='a',destination='b',direction='outgoing',phase='prepared',revision=1,inputsReplayed=False,**kw)

def test_selected_fence_and_pages_never_read_unrelated_canonical_files(tmp_path,monkeypatch):
    node=TransferNode(tmp_path,'Test');rows=[record(i) for i in range(1,4)]
    for row in rows:node.save(row)
    unrelated=record();unrelated['sessionId']='other';node.save(unrelated)
    node.path(unrelated['id']).write_text('unrelated history corrupt but not selected')
    def deny(*args,**kwargs):raise AssertionError('No canonical history hydration on metadata paths')
    with monkeypatch.context() as patch:
        patch.setattr(Path,'read_text',deny);patch.setattr(Path,'glob',deny)
        assert node.fenced('selected') is True
        assert node.latest('selected')['generation']==3
        first=node.page(sid='selected',limit=2);assert len(first['items'])==2
        last=node.page(sid='selected',cursor=first['nextCursor'],limit=2);assert len(last['items'])==1
    node.save({**rows[0],'phase':'cancelled'})
    with pytest.raises(ValueError,match='stale'):node.page(sid='selected',cursor=first['nextCursor'])

def test_interrupted_canonical_write_cannot_hide_changed_fence(tmp_path,monkeypatch):
    import amplifier_portability.protocol as protocol
    node=TransferNode(tmp_path,'Test');row=record();row['phase']='active';node.save(row)
    write=protocol.durable
    def lost(path,value):write(path,value);raise OSError('lost durable acknowledgement')
    with monkeypatch.context() as patch:
        patch.setattr(protocol,'durable',lost)
        with pytest.raises(OSError):node.save({**row,'phase':'released'})
    restarted=TransferNode(tmp_path,'Test');assert restarted.fenced('selected')
    assert restarted.latest('selected')['phase']=='released'

def test_absent_uncertain_write_and_legacy_index_require_explicit_maintenance(tmp_path):
    node=TransferNode(tmp_path,'Test');row=record();node.index.prepare(row)
    with pytest.raises(ValueError,match='unresolved'):node.fenced('selected')
    durable(node.path(row['id']),row)
    assert node.fenced('selected')
    for path in tmp_path.glob('receipts.sqlite3*'):path.unlink()
    legacy=TransferNode(tmp_path,'Test')
    with pytest.raises(IndexMigrationRequired):legacy.fenced('selected')
    assert legacy.rebuild_index()=={'indexed':1,'replayed':False}
    assert legacy.latest('selected')['id']==row['id']

def test_25k_latest_query_is_indexed_and_metadata_only(tmp_path):
    node=TransferNode(tmp_path,'Test')
    with node.index.connect() as db:
        for i in range(25000):
            row=record(i);row['sessionId']='history-'+str(i);node.index.put(db,row)
        row=record();node.index.put(db,row)
        plan=' '.join(str(x) for x in db.execute('EXPLAIN QUERY PLAN SELECT body FROM rows WHERE session=? ORDER BY generation DESC,created DESC,id DESC LIMIT 1',('selected',)))
    assert 'rows_latest' in plan and 'SCAN' not in plan and 'TEMP' not in plan
    assert node.fenced('selected')

def test_evidence_unicode_integrity_bounds_and_partial_review():
    value=envelope('operations',3,{'z':'\u96ea','a':[1,True,None]})
    assert value['bodyJson'].encode()==b'{"a":[1,true,null],"z":"\xe9\x9b\xaa"}'
    assert verify(value)==value
    with pytest.raises(ValueError):verify({**value,'bodyJson':'{}'})
    with pytest.raises(ValueError):envelope('operations',3,{'n':float('nan')})
    partial=envelope('operations',3,{},omissions=[{'kind':'output','reason':'byte-limit'}])
    with pytest.raises(ValueError,match='preview'):verify(partial)
    assert verify(partial,accept_partial=True)['executionAuthority'] is False


def test_evidence_preserves_foreign_number_serialization_and_scans_decoded_fields():
    import hashlib
    from amplifier_portability.evidence import decode_body
    value=envelope('resources',1,{})
    raw=b'{"a":1.0,"tiny":1e-7}'
    foreign={**value,'bodyJson':raw.decode(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    assert decode_body(foreign)=={'a':1.0,'tiny':1e-7}
    for raw in (b'{"apiKey":"dangerous-value"}',b'{"x":1,"x":2}'):
        bad={**value,'bodyJson':raw.decode(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        with pytest.raises(ValueError):verify(bad)


@pytest.mark.parametrize('damage',['rows','metadata','ready','revision'])
def test_partial_index_requires_explicit_rebuild_without_startup_history_scan(tmp_path,monkeypatch,damage):
    node=TransferNode(tmp_path,'Test');row=record();row['phase']='unknown';node.save(row)
    before=node.path(row['id']).read_bytes()
    with sqlite3.connect(node.index.path) as db:
        if damage in {'ready','revision'}:db.execute('DELETE FROM metadata WHERE key=?',(damage,))
        else:db.execute('DROP TABLE '+damage)
    def deny(*args,**kwargs):raise AssertionError('Partial schema detection must not scan canonical history')
    with monkeypatch.context() as patch:
        patch.setattr('amplifier_portability.index.os.scandir',deny)
        restarted=TransferNode(tmp_path,'Test')
        with pytest.raises(IndexMigrationRequired):restarted.fenced('selected')
        with pytest.raises(IndexMigrationRequired):restarted.page()
    assert node.path(row['id']).read_bytes()==before
    assert restarted.rebuild_index()=={'indexed':1,'replayed':False}
    assert restarted.fenced('selected') and restarted.latest('selected')['phase']=='unknown'
    assert node.path(row['id']).read_bytes()==before
    assert TransferNode(tmp_path,'Test').fenced('selected')


def test_rebuild_preserves_pending_write_without_canonical_receipt(tmp_path):
    node=TransferNode(tmp_path,'Test');row=record();node.index.prepare(row)
    with sqlite3.connect(node.index.path) as db:db.execute('DROP TABLE rows')
    restarted=TransferNode(tmp_path,'Test')
    with pytest.raises(IndexMigrationRequired,match='unresolved'):restarted.rebuild_index()
    with sqlite3.connect(node.index.path) as db:
        assert db.execute('SELECT id,session FROM pending').fetchall()==[(row['id'],'selected')]
    with pytest.raises(IndexMigrationRequired):restarted.fenced('selected')
    durable(node.path(row['id']),row)
    assert restarted.rebuild_index()=={'indexed':1,'replayed':False}
    assert restarted.fenced('selected')


def test_partial_schema_in_open_index_refuses_false_empty(tmp_path):
    node=TransferNode(tmp_path,'Test');row=record();node.save(row)
    with sqlite3.connect(node.index.path) as db:db.execute('DROP TABLE rows')
    with pytest.raises(IndexMigrationRequired):node.fenced('selected')
    assert node.rebuild_index()=={'indexed':1,'replayed':False}
    assert node.fenced('selected')


@pytest.mark.parametrize('operation',['startup','rebuild'])
def test_maintenance_fence_commits_before_partial_schema_repair(tmp_path,monkeypatch,operation):
    from amplifier_portability.index import ReceiptIndex
    node=TransferNode(tmp_path,'Test');row=record();node.save(row)
    with sqlite3.connect(node.index.path) as db:db.execute('DROP TABLE rows')
    schema=ReceiptIndex.schema
    def interrupted(db):
        schema(db)
        raise OSError('lost schema repair acknowledgement')
    with monkeypatch.context() as patch:
        patch.setattr(ReceiptIndex,'schema',staticmethod(interrupted))
        with pytest.raises(OSError):
            if operation=='startup':TransferNode(tmp_path,'Test')
            else:node.rebuild_index()
    restarted=TransferNode(tmp_path,'Test')
    with pytest.raises(IndexMigrationRequired):restarted.fenced('selected')
    assert restarted.rebuild_index()=={'indexed':1,'replayed':False}
    assert restarted.fenced('selected')


@pytest.mark.parametrize('suffix',['','-wal','-shm','-journal'])
def test_index_fifo_refuses_before_sqlite_open(tmp_path,monkeypatch,suffix):
    import os
    from types import SimpleNamespace
    from amplifier_portability.index import ReceiptIndex
    if suffix:
        with sqlite3.connect(tmp_path/'receipts.sqlite3') as db:db.execute('CREATE TABLE fixture(id)')
    path=tmp_path/('receipts.sqlite3'+suffix);os.mkfifo(path)
    def deny(*args,**kwargs):raise AssertionError('Non-regular storage must not open SQLite')
    with monkeypatch.context() as patch:
        patch.setattr(sqlite3,'connect',deny)
        with pytest.raises(IndexMigrationRequired,match='regular'):ReceiptIndex(SimpleNamespace(directory=tmp_path))
    assert path.is_fifo()


@pytest.mark.parametrize('outcome',['healthy','partial','exception'])
def test_preflight_connections_close_without_garbage_collection(tmp_path,monkeypatch,outcome):
    import amplifier_portability.index as module
    node=TransferNode(tmp_path,'Test')
    if outcome=='partial':
        with sqlite3.connect(node.index.path) as db:db.execute('DROP TABLE rows')
    connect=sqlite3.connect;held=[]
    def tracked(*args,**kwargs):
        db=connect(*args,**kwargs)
        if kwargs.get('uri') and '?mode=ro' in str(args[0]):held.append(db)
        return db
    def fail(db):raise RuntimeError('interrupted schema inspection')
    with monkeypatch.context() as patch:
        patch.setattr(sqlite3,'connect',tracked)
        if outcome=='exception':patch.setattr(module,'complete',fail)
        for _ in range(12):
            if outcome=='exception':
                with pytest.raises(RuntimeError):TransferNode(tmp_path,'Test')
            else:TransferNode(tmp_path,'Test')
    assert len(held)==12
    # Strong references prevent collection from hiding missing close calls.
    for db in held:
        with pytest.raises(sqlite3.ProgrammingError,match='closed'):db.execute('SELECT 1')


def test_recover_upgrades_json_first_receipts_without_rewriting_confirmed_history(tmp_path):
    node=TransferNode(tmp_path,'Test')
    phases=['preparing','staging','releasing','activating','prepared','ready',
            'released','active','cancelled','discarded','unknown']
    rows=[]
    for phase in phases:
        row=record();row.update(phase=phase,sessionId=phase,foreign={'exact':[1.0,'雪']})
        durable(node.path(row['id']),row);rows.append(row)
    # The predecessor wrote canonical JSON, with no SQLite lookup or pending log.
    for path in tmp_path.glob('receipts.sqlite3*'):path.unlink()
    before={row['id']:node.path(row['id']).read_bytes() for row in rows}
    restarted=TransferNode(tmp_path,'Test')
    with pytest.raises(IndexMigrationRequired):restarted.fenced('released')
    restarted.recover()
    for row in rows:
        current=restarted.get(row['id'])
        if row['phase'] in phases[:4]:
            assert current['phase']=='unknown' and current['previousPhase']==row['phase']
            assert current['revision']==row['revision']+1
            assert {k:current[k] for k in row if k not in {'phase','revision','updatedAt'}}=={
                k:v for k,v in row.items() if k not in {'phase','revision','updatedAt'}}
        else:
            assert restarted.path(row['id']).read_bytes()==before[row['id']]
        assert current['inputsReplayed'] is False
        assert restarted.fenced(row['sessionId']) is (row['phase'] not in {'active','cancelled'})
    recovered={row['id']:restarted.path(row['id']).read_bytes() for row in rows}
    TransferNode(tmp_path,'Test').recover()
    assert recovered=={row['id']:restarted.path(row['id']).read_bytes() for row in rows}


@pytest.mark.parametrize('damage',['rows','metadata','ready','revision'])
def test_recover_restores_derived_state_with_intact_pending_intent(tmp_path,damage):
    node=TransferNode(tmp_path,'Test');row=record();row['phase']='released';node.save(row)
    before=node.path(row['id']).read_bytes()
    with sqlite3.connect(node.index.path) as db:
        if damage in {'ready','revision'}:db.execute('DELETE FROM metadata WHERE key=?',(damage,))
        else:db.execute('DROP TABLE '+damage)
    restarted=TransferNode(tmp_path,'Test');restarted.recover()
    assert restarted.fenced('selected') and restarted.latest('selected')['phase']=='released'
    assert restarted.path(row['id']).read_bytes()==before


@pytest.mark.parametrize('restart',[False,True])
def test_lost_pending_table_refuses_recovery_without_mutating_database(tmp_path,restart):
    node=TransferNode(tmp_path,'Test');row=record();node.save(row)
    with sqlite3.connect(node.index.path) as db:db.execute('DROP TABLE pending')
    db.close()
    before=node.index.path.read_bytes();canonical=node.path(row['id']).read_bytes()
    with pytest.raises(IndexMigrationRequired,match='intent'):
        if restart:TransferNode(tmp_path,'Test')
        else:node.recover()
    assert node.index.path.read_bytes()==before
    assert node.path(row['id']).read_bytes()==canonical
    with pytest.raises(IndexMigrationRequired,match='intent'):node.rebuild_index()


def test_recovery_keeps_missing_canonical_pending_write_fenced(tmp_path):
    node=TransferNode(tmp_path,'Test');row=record();row['phase']='preparing';node.index.prepare(row)
    with sqlite3.connect(node.index.path) as db:db.execute('DROP TABLE rows')
    restarted=TransferNode(tmp_path,'Test')
    with pytest.raises(IndexMigrationRequired,match='unresolved'):restarted.recover()
    with sqlite3.connect(node.index.path) as db:
        assert db.execute('SELECT id,session FROM pending').fetchall()==[(row['id'],'selected')]
    with pytest.raises(IndexMigrationRequired):restarted.fenced('selected')
    assert not node.path(row['id']).exists()
    durable(node.path(row['id']),row)
    restarted.recover()
    assert restarted.get(row['id'])['previousPhase']=='preparing'
    assert restarted.latest('selected')['phase']=='unknown' and restarted.fenced('selected')


def test_corrupt_database_is_not_discarded_as_derived_state(tmp_path):
    node=TransferNode(tmp_path,'Test');row=record();node.save(row)
    canonical=node.path(row['id']).read_bytes()
    node.index.path.write_bytes(b'unreadable database may contain unresolved write intent')
    before=node.index.path.read_bytes()
    with pytest.raises(sqlite3.DatabaseError):TransferNode(tmp_path,'Test')
    assert node.index.path.read_bytes()==before and node.path(row['id']).read_bytes()==canonical


def test_healthy_recovery_reads_only_transient_receipts(tmp_path,monkeypatch):
    node=TransferNode(tmp_path,'Test');terminal=record();node.save(terminal)
    transient=record();transient['phase']='staging';node.save(transient)
    node.path(terminal['id']).write_text('unrelated terminal receipt is never hydrated')
    read=Path.read_text;seen=[]
    def selected(path,*args,**kwargs):
        assert path==node.path(transient['id']);seen.append(path)
        return read(path,*args,**kwargs)
    def deny(*args,**kwargs):raise AssertionError('Healthy recovery must not scan history')
    with monkeypatch.context() as patch:
        patch.setattr(Path,'read_text',selected);patch.setattr('amplifier_portability.index.os.scandir',deny)
        node.recover()
    assert seen==[node.path(transient['id'])]
    assert node.get(transient['id'])['phase']=='unknown'


@pytest.mark.parametrize('failure',['canonical-json','canonical-identity','index-write'])
def test_failed_lookup_recovery_stays_fenced_and_can_resume_without_replay(tmp_path,monkeypatch,failure):
    from amplifier_portability.index import ReceiptIndex
    node=TransferNode(tmp_path,'Test');row=record();row['phase']='preparing';node.save(row)
    canonical=node.path(row['id']).read_bytes()
    with sqlite3.connect(node.index.path) as db:db.execute('DROP TABLE rows')
    restarted=TransferNode(tmp_path,'Test')
    put=ReceiptIndex.put
    def interrupted(db,value):
        put(db,value)
        raise OSError('interrupted lookup preparation')
    with monkeypatch.context() as patch:
        if failure=='canonical-json':node.path(row['id']).write_text('invalid retained JSON')
        elif failure=='canonical-identity':node.path(row['id']).write_text(json.dumps({**row,'id':str(uuid.uuid4())}))
        else:patch.setattr(ReceiptIndex,'put',staticmethod(interrupted))
        failed_bytes=node.path(row['id']).read_bytes()
        with pytest.raises((ValueError,OSError)):restarted.recover()
    with pytest.raises(IndexMigrationRequired):restarted.fenced('selected')
    if failure.startswith('canonical-'):
        assert node.path(row['id']).read_bytes()==failed_bytes
        node.path(row['id']).write_bytes(canonical)
    else:assert node.path(row['id']).read_bytes()==canonical
    resumed=TransferNode(tmp_path,'Test');resumed.recover()
    restored=resumed.get(row['id'])
    assert restored['phase']=='unknown' and restored['previousPhase']=='preparing'
    assert restored['inputsReplayed'] is False and resumed.fenced('selected')
