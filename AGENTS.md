# Library boundary

This codebase is yours: what it's for and how it's built are your call, and you'll keep building on it.

Read README.md, docs/VISION.md, docs/contract.v1.md and PROVENANCE.json before changes. Keep runtime and client ownership outside this library. Preserve histories and unknown outcomes; never replay effects to reconstruct state. Build a wheel, test it in an isolated consumer, and run the contract tests before claiming completion. Do not import sibling source trees. Public integration contracts belong with their owning API.

For documentation-only successors, preserve sealed implementation artifacts and record source-file equality; do not rebuild or rerun runtime tests when executable source and contracts are unchanged. Proposed cross-owner obligations remain proposals until their owners approve composition.
