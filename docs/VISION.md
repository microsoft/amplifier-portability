# Amplifier portability vision

This library lets explicitly paired execution hosts move selected work without
replaying accepted or uncertain effects, losing native history, or creating two
execution owners. A successful handoff preserves native identity and exact bytes;
a missing receipt, unavailable body or incompatible destination stays visible.

This is a local expression of the approved 2026-10-02
[Unified family direction](https://github.com/microsoft/amplifier-unified/blob/625af2f2832fafc8152f6078061d626f160362a4/docs/architecture/VISION.md),
especially durable history, one execution authority, small selected reads,
independent ownership and truthful recovery. That coordinator reference was read
from the approved distribution checkout. This packet does not ratify new family
scope or claim deployed acceptance.

## Desired outcomes

- An explicit signed ready/release chain transfers one native execution identity;
  uncertain outcomes retain evidence and never trigger automatic work replay.
- Selected workspace changes and historical evidence preserve their original
  bytes. Source records remain retained; imported history does not acquire live
  job, approval, schedule, artifact or model-input authority.
- Receipt metadata and resource pages remain bounded and cold. One selected read
  does not hydrate unrelated histories or start a native runtime.
- Existing JSON receipt stores recover without a separate user maintenance step.
  Lookup preparation belongs at explicit startup recovery, under the existing
  store lock. Missing pending-write evidence remains an unresolved outcome.
- Independent callers can install and verify the library without Unified runtime
  imports. Incompatible peers refuse explicitly or accept a reviewed selection
  with explicit omissions, never silently discard required content.

## Scope and ownership

This repository owns signed paired-host receipt mechanisms, indexed receipt
reads, reviewed workspace capsules, exact-byte owner evidence and optional
immutable historical payload copies. Callers supply native writer exclusion,
admission, host authentication, transport, destination runtime/account checks,
resource import authority and user review. The native owner retains canonical
history; the resource owner retains canonical mutable resources. Private client
drafts, product UI, deployment and device/account acceptance have other owners.

Automatic transport retry, cross-engine history conversion, arbitrary-secret
confidentiality proof and automatic source/history deletion are outside this
library's scope. Detached resource consumption remains a proposed negotiated
integration: its private import port and signed-plan composition are not approved
by this local document or proven by the standalone library checks.

The [local contract entry point](contract.v1.md) maps public promises to executable
falsifiers, consumer obligations and the exact evidence boundaries.
