# Historical payload manifest v1

Producer: public `amplifier_portability.payloads.PayloadStore`. Consumers: an
explicitly negotiated paired-host adapter and the resource evidence owner. This
is an additive library contract, not an AHP/ACP core method or a change to signed
transfer receipt v1. Consumers must advertise support before including a plan.
Unsupported peers retain explicit reviewed body omissions; absence is not success.

A plan contains exact UTF-8 `bodyJson` and its SHA-256. The caller binds this exact
plan to the authenticated signed capsule and transfer identity, source/destination
and owner revision. Hashes establish integrity, not authorization. The store does
not authenticate peers, resolve remote URIs, acquire native fences, or invoke work.
Paths and credentials are not transport locators. Each selected resource has a
stable owner-supplied id, or an explicit omission reason. Canonical native bytes
remain the source owner's authority and are never rewritten by this library.

The root describes immutable content-addressed JSON pages. Pages describe immutable
binary chunks and whole-body SHA-256/size. Source files are streamed unchanged and
checked for concurrent mutation. Bodies never enter the root or ordinary metadata
page reads. Independent receivers call `put(bytes, expected_sha256)` for each
selected page/chunk. Duplicate byte delivery is idempotent and never overwrites an
existing different object. A lost acknowledgement is reconciled by immutable
identity, not by recapturing content or replaying work.

Bounds: 10,000 selected ids; 25 rows and 256 KiB per manifest page; 256 KiB per
chunk; 64 MiB per body; 1 GiB combined bodies; 2 MiB exact root. Oversized or unsafe
selections refuse sealing. The caller may build another reviewed selection with
explicit omissions; automatic truncation is forbidden. Cursors bind to one exact
immutable root hash. Selected page reads load one page and zero body chunks.
Explicit `audit` streams every included body to check whole hashes, unique ids,
counts and aggregate bytes, holding only bounded chunks/pages plus selected ids.
It preflights every bounded metadata page, unique id and aggregate declared byte
budget before reading any body. A second bounded page pass verifies bodies only
after metadata qualifies. It is a review/qualification operation, never an
ordinary admission path.

All plans, rows and audit receipts have `executionAuthority:false`. Omitted rows
remain omitted even after a successful audit. Partial plans require explicit
`accept_partial=True` following caller-owned preview/review. Missing/corrupt pages
or chunks refuse audit; there is no invented complete/available receipt. Transport
expiration/unavailability is a caller-observed reason, never an automatic retry.
Staged bytes, expired leases and unknown execution receipts do not authorize
activation. The original signed ready/release chain and native fences still govern
execution, independently of inactive historical bodies.

A consumer must verify the authenticated plan, audit received selections before
claiming availability, retain explicit omissions, and import into the resource
owner's inactive historical namespace. It must not turn imported artifacts into
live Canvas state, jobs, schedules, approvals or model input. Product review UI,
resource URI mapping, account authorization, transport deadlines, retention and
activation orchestration stay with their owners. Failure leaves inactive orphan
blobs for caller-managed retention; this library deletes no source or history.

Qualification boundary: standalone installed tests prove the payload mechanism.
Two actual native-host signed transfer, product adapter composition, browser/device,
remote account and deployed adoption require separate receipts. A passing library
test does not establish those outcomes.

For Unified integration, the proposed private resource-owner port must bind the
already-staged `evidenceHash`, exact `planHash`, `transferId`, `sourceHost`,
`destinationHost` and owner revision. Authenticated pages bind resource ids to
whole-byte hashes. The trusted composition performs audit; a client-supplied
Boolean verification claim is insufficient. Selected historical reads become
available only after the existing independently verified signed release. This
proposed consumer port is not implemented or qualified by the library PR.

Consumer limits must be negotiated before selection. The current resource-owner
candidate accepts at most 500 records and 200 characters per resource id, while
this library allows 10,000 ids and 1,024 UTF-8 bytes per id. Composition must refuse
an incompatible selection or produce a newly reviewed compatible selection with
explicit omissions. It must never shorten ids or silently drop records.
