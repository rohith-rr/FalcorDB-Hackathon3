// Scoped inferred association candidates for one task/repository. Candidate
// evidence stays OUT of confirmed delivery traversal; ordinary active
// traversal excludes tombstones and CANDIDATE edges, so this template is the
// only permitted read for inferred suggestions.
MATCH (t:Task {tenant_id: $tenant_id, id: $task_id})-[r:IMPLEMENTED_IN]->(b:Branch)
WHERE r.is_deleted = false AND r.link_method = 'INFERRED'
  AND r.authority = 'CANDIDATE' AND r.tenant_id = $tenant_id
  AND b.tenant_id = $tenant_id AND b.is_deleted = false
RETURN r.association_id AS association_id, b.id AS branch_id, b.ref AS ref,
       b.head_sha AS head_sha, r.pair_probability AS pair_probability,
       r.observed_at AS observed_at, r.valid_until AS valid_until,
       r.work_period_ids AS work_period_ids,
       r.matching_commit_shas AS matching_commit_shas
ORDER BY association_id
LIMIT 51
