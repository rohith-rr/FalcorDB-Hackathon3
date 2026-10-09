# Design revision record

Date: 2026-10-09. Scope: approved design corrections and live adapter planning. Application implementation has not started; this workspace is not a Git repository.

## Review findings resolved in the specifications

| Finding | Revised requirement | Future implementation evidence |
| --- | --- | --- |
| P2: interrupted imports can expose overwritten records under the old marker | [Phase 1](phase_01_graph_and_fixtures.md#snapshot-consistency) persists dirty state/generation before mutation, blocks reads across restart, and requires a full validated rebuild | Failure halfway through upserts, between nodes/edges and before publication; application/database restart; failed and repeated recovery; concurrent request invalidation |
| P2: global delivery reversion rejects usable feature histories | [Schema](graph_schema.md#revision-effects-and-candidate-history) records revert/reapplication revisions and evaluates applicability against each candidate head | Stable merge/revert plus unchanged feature; explicit complete restoration; later revert; partial/ambiguous effects; cache invalidation |
| Missing Plane/Google Docs integration planning | [Source adapters](source_adapters.md) specifies required live reads, provider identities/mappings, multi-assignee tasks, versioned document tabs/sections, failure behavior and labeled exports | Both actual live smoke checks and source-backed task/document citations; export-only fallback leaves the full gate incomplete |

The [contracts](contracts.md), master design, implementation index, all phase gates and SRE/resource guidance carry these requirements. Original sprint estimates are provisional. The archived original draft is preserved.

## Documentation validation

Local documentation checks passed: 20 Markdown documents, 110 relative links, 12 heading anchors and one JSON example; fenced blocks are balanced. An obsolete-guidance scan found no active global delivery-reversion flag, marker-only recovery or optional-live adapter completion policy. Required import/effect/adapter contract and acceptance coverage was also checked. A final semantic pass confirmed partial reapplication records remain representable as uncertainty rather than being rejected or treated as complete restoration.

Archived original SHA-256: `5152b97014014fcbd28a1527a60dd078266e483ccaed9dc95ed149551a04b0a6`.

Runtime database/Git tests and live adapter calls are not part of this documentation revision and have not passed or run. No provider accounts, source records, notifications or deployed services were changed. There is no Git diff/commit to report because the workspace has no Git repository; review the updated documents directly.
