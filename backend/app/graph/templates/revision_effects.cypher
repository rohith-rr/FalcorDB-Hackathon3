// Revision effects for the requested delivery ids in one repository, with
// their effect/affected commits and resolving links. Their effect edges must
// match the stored SHAs; reapplications require RESOLVES_REVERT references.
// Every relationship is bound and must be ACTIVE CONFIRMED: a reimport
// tombstones removed effect mappings or resolving links, and withdrawn
// effects or resolved reverts must not surface as current evidence just
// because the relationship record still exists (graph_schema.md
// #identity-provenance-and-source-ownership: active traversal excludes
// tombstones and candidates). Endpoints must be live too.
MATCH (e:RevisionEffect {tenant_id: $tenant_id, repository_id: $repository_id})
WHERE e.is_deleted = false AND e.delivery_id IN $delivery_ids
OPTIONAL MATCH (e)-[ea:EFFECT_AT]->(ec:Commit)
  WHERE ea.is_deleted = false AND ea.authority = 'CONFIRMED'
    AND ea.tenant_id = $tenant_id
    AND ec.is_deleted = false AND ec.tenant_id = $tenant_id
OPTIONAL MATCH (e)-[ar:AFFECTS_REVISION]->(ac:Commit)
  WHERE ar.is_deleted = false AND ar.authority = 'CONFIRMED'
    AND ar.tenant_id = $tenant_id
    AND ac.is_deleted = false AND ac.tenant_id = $tenant_id
OPTIONAL MATCH (e)-[rr:RESOLVES_REVERT]->(rv:RevisionEffect)
  WHERE rr.is_deleted = false AND rr.authority = 'CONFIRMED'
    AND rr.tenant_id = $tenant_id
    AND rv.is_deleted = false AND rv.tenant_id = $tenant_id
RETURN e.id AS effect_id, e.effect_kind AS effect_kind,
       e.effect_commit_sha AS effect_commit_sha,
       e.affected_revision_shas AS affected_revision_shas,
       e.coverage AS coverage, e.authority AS authority,
       e.mapping_version AS mapping_version,
       ec.sha AS effect_commit_resolved,
       collect(DISTINCT ac.sha) AS affected_resolved,
       collect(DISTINCT rv.id) AS resolves_revert_ids
ORDER BY effect_id
LIMIT 51
