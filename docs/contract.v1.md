# Amplifier portability contract entry point — v1

Status: local contract candidate describing existing APIs and inherited approved
direction. Family promises retain their existing authority; proposed detached
consumer integration is separately labelled below. No upstream AHP/ACP schema is
redefined here. [Vision](VISION.md) states the purpose and ownership.

## Authority and public boundary

[Family vision](https://github.com/microsoft/amplifier-unified/blob/625af2f2832fafc8152f6078061d626f160362a4/docs/architecture/VISION.md)
and the following versioned family contracts are the inherited direction. The
links identify the reviewed coordinator revision, not deployed adoption.

| Inherited clauses | Application in this repository |
| --- | --- |
| [CB1–6](https://github.com/microsoft/amplifier-unified/blob/625af2f2832fafc8152f6078061d626f160362a4/contracts/component-boundaries.v1.md) | Independent library inputs/outputs, one owner per rule, owned checkout and exact package evidence |
| [AP3/AP6](https://github.com/microsoft/amplifier-unified/blob/625af2f2832fafc8152f6078061d626f160362a4/contracts/agent-protocol.v1.md) | Preserve native identity, exclusive authority and legacy records; never replay failed resume |
| [WS1/WS3–5](https://github.com/microsoft/amplifier-unified/blob/625af2f2832fafc8152f6078061d626f160362a4/contracts/working-set.v1.md) | Retained canonical bytes, selected detail, explicit byte budgets and scoped index reads |
| [HP1/HP5/HP6](https://github.com/microsoft/amplifier-unified/blob/625af2f2832fafc8152f6078061d626f160362a4/contracts/host-protocol.v1.md) | Optional negotiated integration, truthful unavailable behavior and no resubmission of uncertain work; migration remains outside AHP core |
| [CS1/CS2/CS4/CS7](https://github.com/microsoft/amplifier-unified/blob/625af2f2832fafc8152f6078061d626f160362a4/contracts/client-state.v1.md) | Exact host/target/command identity, private view ownership and canonical/native execution boundaries |
| [CX4/CX6/CX7](https://github.com/microsoft/amplifier-unified/blob/625af2f2832fafc8152f6078061d626f160362a4/contracts/client-experience.v1.md) | Caller UI exposes ownership, progress, omissions and unsupported capabilities honestly |
| [CD1–6](https://github.com/microsoft/amplifier-unified/blob/625af2f2832fafc8152f6078061d626f160362a4/contracts/client-development.v1.md) | Declare consumer impact; distinguish source, installed, actual-peer and deployment evidence |

[AHP](https://microsoft.github.io/agent-host-protocol/) and
[ACP](https://agentclientprotocol.com/) own their wire semantics. This library is
not either protocol server. Its APIs are `TransferNode`, capsule capture/restore,
owner evidence codec and `PayloadStore`; implementation schemas remain in
[protocol.py](../src/amplifier_portability/protocol.py),
[capsule.py](../src/amplifier_portability/capsule.py),
[evidence.py](../src/amplifier_portability/evidence.py) and
[payload contract v1](payload-contract.v1.md), rather than copied definitions.

## Public promises and falsifiers

| Promise | Observable falsifier and executable checks |
| --- | --- |
| LP1: authenticate exact transfer identity and preserve a single execution owner through staged ready/release/activation | Another transfer's signed receipt releases work, or lost activation permits source reclaim: [protocol tests](../tests/test_portability_protocol.py), `test_valid_signatures_cannot_substitute_a_different_transfer`, `test_lost_activation_acknowledgement_never_allows_source_reclaim` |
| LP2: reconcile duplicates and uncertain boundaries without repeating effects | Restart or retry reconstructs state by replay: [protocol tests](../tests/test_portability_protocol.py), `test_restart_marks_unconfirmed_effects_unknown_without_replay`, `test_receive_duplicate_never_replays_destination_work` |
| LP3: preserve exact selected workspace and owner-evidence bytes, reject unsafe paths/known credential shapes, and require partial review | Capture changes source or canonical text is reserialized: [capsule tests](../tests/test_portability_capsule.py), `test_carry_dirty_preserves_staged_unstaged_untracked_and_source`; [index/evidence tests](../tests/test_portability_index.py), `test_evidence_preserves_foreign_number_serialization_and_scans_decoded_fields` |
| LP4: receipt admission uses scoped indexed metadata; explicit rebuild/export never becomes an ordinary historical scan | Selected fence reads unrelated receipts or hydrates a full history: [index tests](../tests/test_portability_index.py), `test_selected_fence_and_pages_never_read_unrelated_canonical_files`, `test_25k_latest_query_is_indexed_and_metadata_only` |
| LP5: immutable historical payload copies stay bounded, independently verifiable and inactive; validate all metadata totals before any body audit | Oversized declared selections read bodies before refusal, missing chunks claim availability, or a page reads unrelated bodies: [payload tests](../tests/test_portability_payloads.py), `test_audit_preflights_all_metadata_before_any_body_read`, `test_lost_transport_has_no_success_and_resume_copies_only_immutable_bytes`, `test_selected_page_does_not_read_unrelated_pages_or_bodies` |

## Consumer obligations and proposed integration

Consumers explicitly pair hosts and bind signer, source, destination, native
session, generation, command identity and capsule hash to the same transfer.
They verify native exclusion and destination runtime/account readiness locally,
retain irreversible source release evidence and inspect unknown outcomes on both
hosts. Historical observation alone never authorizes admission or replay.
Credential scanning detects known shapes only; callers still authorize and review
selected content and supply network/security policy. Export does not delete source
history. Private client drafts are not implicitly shared by this library.

The proposed detached resource seam is detailed in [payload contract v1](payload-contract.v1.md):
negotiated support, exact signed plan/transfer/evidence binding, trusted complete
audit, independently verified inactive import and signed-release activation.
It is a consumer integration requirement, not a self-ratified new AHP action.
Resource consumer limits (500 records/200-character ids) must be negotiated against
producer limits (10,000 ids/1,024 UTF-8 bytes); refuse or create a newly reviewed
selection with explicit omissions, never truncate or silently shorten identities.

## Acceptance and remaining evidence

[Predecessor qualification](qualification-20261003.json) records 0.1.1 full installed
suites (187 on each Python version), a 10.8 MB independent payload probe and actual
two-native-host signed-transfer compatibility with shared read-only dependencies.
[0.1.2 successor qualification](qualification-successor-20261003.json) records
24 targeted source and independently installed tests on Python 3.11/3.13, including
the aggregate-budget regression. Those exact records do not establish every
promise for every caller or successor deployment. `QUALIFICATION.json` at the
repository root remains the historical extraction receipt, not latest acceptance.

Detached signed-plan product composition, browser/agent interaction, remote host,
physical device, real account and live adoption remain unqualified here. The
family/distribution owner assembles public packages and records those outcomes.
Documentation-only successors preserve sealed implementation archives and record
source equality; they do not claim another runtime test or package adoption.
