# Amplifier portability

Reusable paired-host transfer, signed receipts and workspace capsules. Native runtime admission and network authorization belong to callers.

## Standalone qualification

Build with `uv build`. Install the wheel in a separate environment and run `python -m pytest tests`. Tests must not import Unified implementation or native runtime packages. `PROVENANCE.json` records extraction sources. The distribution owns host integration and real-account acceptance.

## Bounded public reads

`TransferNode.latest(session_id)` and `fenced(session_id)` read an indexed metadata
row; they never hydrate unrelated receipts. `page(sid=None, cursor=None,
limit=50, phases=None)` returns `{items,nextCursor,revision}`, at most 100 metadata
rows. Mutation invalidates existing cursors. `get(id)` remains the explicit full
receipt read. `records()` is a compatibility full export, never an admission path.
Startup recovery queries only transient receipt phases.

Canonical signed JSON files remain the evidence source. Before a canonical
write, a durable indexed pending entry is committed. An interrupted write is
reconciled only for the selected receipt; missing/unreadable evidence refuses
admission. Existing stores without an index require explicit `rebuild_index()`
maintenance. That operation scans receipts once with constant row memory and
never replays effects. Ordinary selected reads never initiate a historical scan.
Receipt files are owner-managed; external edits require explicit index rebuild.

## Owner evidence

`amplifier_portability.evidence` exposes `canonical_bytes`, `envelope`, and
`verify`. Canonical bytes are UTF-8 JSON, recursively sorted keys, compact
separators, `ensure_ascii=False`, with nonfinite numbers rejected. The SHA-256 and
byte count cover those exact body bytes. Each owner has an 8 MiB maximum; combined
capsule bounds still apply. Envelopes carry owner/version/revision/body, explicit
omissions and `executionAuthority:false`. Partial evidence requires explicit
preview acceptance. Paired-host authentication and owner-specific schemas remain
with the composition and evidence owner, respectively. Jobs, approvals, schedules,
client drafts and credentials gain no authority from historical evidence.
