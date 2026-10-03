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
    assert canonical_bytes(value['body'])==b'{"a":[1,true,null],"z":"\xe9\x9b\xaa"}'
    assert verify(value)==value
    with pytest.raises(ValueError):verify({**value,'body':{}})
    with pytest.raises(ValueError):envelope('operations',3,{'n':float('nan')})
    partial=envelope('operations',3,{},omissions=[{'kind':'output','reason':'byte-limit'}])
    with pytest.raises(ValueError,match='preview'):verify(partial)
    assert verify(partial,accept_partial=True)['executionAuthority'] is False
