// Revision effects for the requested delivery ids in one repository, with
// their effect/affected commits and resolving links. Their effect edges must
// match the stored SHAs; reapplications require RESOLVES_REVERT references.
MATCH (e:RevisionEffect {tenant_id: $tenant_id, repository_id: $repository_id})
WHERE e.is_deleted = false AND e.delivery_id IN $delivery_ids
OPTIONAL MATCH (e)-[:EFFECT_AT]->(ec:Commit)
OPTIONAL MATCH (e)-[:AFFECTS_REVISION]->(ac:Commit)
OPTIONAL MATCH (e)-[:RESOLVES_REVERT]->(rv:RevisionEffect)
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
