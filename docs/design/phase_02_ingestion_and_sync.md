# Phase 2: structured ingestion and source synchronization

Status: planned. Depends on Phase 1.

## Outcome

Live Plane task data, Google Docs content, GitHub change/review metadata and supported exports become one graph with explicit mappings and declared coverage. Importing the same snapshot does not create duplicate relationships. Source mode is retained per source.

## Proposed files

```text
backend/app/ingestion/{normalize,reconcile,manifest,snapshots}.py
backend/app/ingestion/{event_log,event_batches,incident_projection}.py
backend/app/associations/{periods,candidates}.py
backend/app/connectors/{github,plane,google_docs,jira_export,markdown}.py
scripts/import_sources.py
schemas/relationship_manifest.json
tests/ingestion/test_normalization.py
tests/ingestion/test_reconciliation.py
tests/connectors/test_github_reads.py
tests/connectors/{test_plane_reads,test_google_docs_reads}.py
```

The demo connector scope requires live read-only Plane, Google Docs and GitHub adapters; Jira JSON/CSV import and Markdown/document manifests remain supported. The [source-adapter specification](source_adapters.md) defines authentication, mappings, interfaces, failure behavior and the live gate. Live Jira OAuth, arbitrary PDF extraction, comment NER, native Plane dependency enumeration and inferred dependencies are deferred. A labeled export fallback does not satisfy the live integration gate.

## Mapping contract

Use one versioned manifest containing `tenant_id`, source scope, snapshot reference, confirmed `links`, delivery groups, `revision_effects` and coverage declarations. Each link contains source/destination logical IDs, schema edge type, method, authority and evidence reference. A delivery group contains its task ID, implementation revision(s), optional confirmed integration/restoration alternatives, mapping source and completeness. Revision effects use `RevisionEffectRecord` from [contracts](contracts.md), including explicit resolved-revert IDs and provenance; resolve symbolic effect revisions with the same Git fixture builder as deliveries. Validate effect references and reject global delivery-reversion flags.

Add `identity_bindings` using the shared `IdentityBinding` type and task-activity coverage declarations when discovery is configured. Missing bindings do not prevent importing task history, but they prevent temporal author matching. Keep a promoted association's confirming actor/time/evidence distinct from its earlier model suggestion.

Example shape, with symbolic revisions resolved by the fixture builder before ingest:

```json
{
  "schema_version": 1,
  "tenant_id": "demo",
  "links": [
    {
      "from": "demo:jira:PAY:PAY-API",
      "edge": "DEPENDS_ON",
      "to": "demo:jira:PAY:PAY-BACKEND",
      "authority": "CONFIRMED",
      "link_method": "MANIFEST",
      "source_record_ref": "fixtures/payments/links.json#api-backend"
    }
  ]
}
```

Task keys in PR descriptions or branch conventions can propose associations. A precise provider reference can confirm a task-to-PR association, but neither a keyword nor a branch name confirms dependency direction or complete delivery. An operator/source-owned manifest establishes those missing semantics.

When identifiers/explicit associations are absent, [task-branch discovery](task_branch_association.md) uses assignment/in-progress work periods and mapped author activity to construct candidates for Clef in Phase 4. Retain activity events, identity bindings, competing-task periods, author/committer timestamps, changed paths and pinned heads. Phase 2 prepares evidence without needing model credentials; the model's later output is an inferred candidate association, never a delivery mapping.

## Coding sequence

1. Normalize epics, stories/tasks, all assignees and parent relations from Plane reads or exports, using explicit type/status mappings. Read paginated assignment/status activities and reconstruct `TaskWorkPeriod` intervals for discovery; retain unknown starts and gaps. Typed dependencies, identity bindings and repository/delivery bindings require the verified demo manifest. Preserve raw status/priority and source time. Distinguish cancelled work from done work.
2. Read repository identity, default/stable configuration, live refs, individual PR details and individual reviews from GitHub. Handle pagination; record missing pages, scope errors and rate limits as incomplete coverage. Never equate PR `CLOSED` with merged.
3. Retain PR head/base repository IDs and SHAs, merge time/revision and review commit/state. Determine applicable current review state through explicit provider/policy rules; an old approval is not a current-head approval.
   For discovery, retain mapped author IDs, separate authored/committed times, per-head commit membership, shared/inherited activity and bounded changed-file summaries. Never use an activity actor, pusher or committer as a substitute for author identity. Respect the discovery scope/history limits and report incomplete candidate retrieval.
4. Import Google Docs or Markdown metadata/content with source URL, version, hash, type and explicit task links. Preserve all tabs, section anchors, lists and table structure; detect metadata/content version races. Reject missing bytes for a document marked retrievable. A superseded runbook is retained for history but excluded from default procedural guidance.
5. Resolve/validate manifests against normalized source nodes before graph mutation. Surface duplicate task keys, dangling links/effect references, conflicting ownership, unknown dependency kinds and incomplete deliveries in an import report.
6. Persist full reconciled per-projection bundles and immutable content, then publish through Phase 1 owner-specific gates/fences. Preserve tombstones/audits and referenced cross-projection identities; protect newer source state from stale reimports. A post-mutation failure blocks reads needing that projection until full owned-projection recovery.
7. Add targeted refresh for refs, PRs and reviews involved in a branch query. Reconcile persisted changes into a full rebuild bundle through the same import gate; transient live verification remains request evidence and cannot directly mutate graph records. Maintain a small local read-only Git mirror or provider-backed ancestry adapter in Phase 3.

GitHub documents authoritative PR fields in its [pull request API](https://docs.github.com/en/rest/pulls/pulls) and review records in its [review API](https://docs.github.com/en/rest/pulls/reviews). Implement read operations only in this phase. Current provider access/version settings are recorded at implementation time.

## Prototype sync policy

Manual full import plus targeted refresh is sufficient for the demo. Default live branch evidence TTL is 60 seconds, configurable; a recommendation also refreshes/revalidates heads before being issued. A source unavailable during required refresh cannot borrow fixture evidence and call it live. Imports retain their observation age and cannot masquerade as a refreshed source.

Incident inputs use the [durable event batching policy](graph_publication.md#durable-incident-batching): fixed 30-second windows (configurable 15-30), bounded caps/backpressure and at least 15 seconds of READY time between normal publications. Persist receipts/jobs before acknowledgment, coalesce only projection updates, and retain distinct audit events. Apply idempotent INCIDENT deltas with retained full recovery bundles; never rebuild STRUCTURAL for an alert or lifecycle receipt. Persist/reconcile consumed log positions and reconstruct timers after restart.

Coverage flags distinguish `COMPLETE`, `PARTIAL`, `UNKNOWN` for task dependencies, deliveries, repository refs and review retrieval. Complete means complete within the declared source/scope, not complete company knowledge. If a source cannot enumerate dependencies completely, commands require an explicit verified manifest for the relevant scope.

Implement the [persistent source-access registry](source_adapters.md#persistent-source-access-handling) independently of graph publication. A denied/unavailable source can invalidate access to retained content even when import preparation aborts and the graph stays READY. Version source/resource access, persist restrictions across restart and restore access only after successful authorized recheck. Transport failure remains a freshness/coverage issue. Later explicit ingestion batches may project retained association audits; inference queries never publish their own candidates. Revalidate access/inputs and preserve inference observation time/generation/expiry separately from the new projection snapshot.

## Validation and completion gate

Verify repeated imports, updated refs, closed-unmerged PRs, dismissed reviews, duplicate names in different repositories, missing source pages, deleted documents and malformed manifest/effect mappings. Source failures during preparation preserve the previous snapshot at its original age; failures after dirty publication block reads until a successful full rebuild. Never interpret incomplete source enumeration as deletion. Inspect the import report and sample a normalized task/PR/review/document path against its source record. Run the source-adapter contract checks and Phase 1 interruption/restart cases.

Verify work periods across reassignment, status changes/reopening, multiple assignees and time zones; a lone current snapshot or generic update timestamp must not fabricate history. Author/time candidates retain exact head/commit evidence, and unrelated inherited commits or missing identities cannot create confirmed links. Repeated imports of the same evidence are idempotent; changed periods/heads invalidate discovery caches.

Completion requires valid Payments/TLS imported snapshots with confirmed delivery/dependency scope and provenance, plus actual live Plane and Google Docs smoke results and source-backed task/document citations as specified in [source adapters](source_adapters.md#acceptance-and-completion-record). Missing credentials/provider availability leave the live gate incomplete. A fixture/export-only mode remains usable but labeled as a partial deliverable.

## SRE extension

Add a durably accepted event receiver and background investigation job, with separate duplicate-delivery and related-alert grouping rules. Normalize deployment/artifact, catalog, on-call, customer-use and measurement records from explicit synthetic/exported sources first. Preserve event/receipt/effective times, scope and partial coverage. Live receivers require their actual provider authentication/payload contract. Refresh deployment and effective on-call state before an action or notification; a previously valid schedule or artifact record is not automatically current. The [integration plan](sre_integration_plan.md) defines replay/restart checks and later live sources.

Gate: continuous/trickling arrivals cannot extend a fixed window or create back-to-back publications outside cadence; caps retain previously accepted events, duplicate deliveries add no work, and restart after publication/before position acknowledgment causes no duplicate projection. Measure pending age, batch size, read-blocked fraction and freshness. INCIDENT DIRTY blocks incident-backed investigation while structural-only queries continue. An accepted but unprojected event is shown as pending coverage, never silently incorporated into a current brief.
