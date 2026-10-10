// Implementation PR/branch links for one task: planned/observed implementation
// branches and explicitly linked implementation PRs with their base targets.
// A current PR head does not automatically prove the accepted task
// implementation. Each association returns its OWN row (kind-tagged union):
// aggregating every branch/PR association into one row per task hides
// arbitrarily many members from the row-budget sentinel, so overflow could
// never be detected. Removed (tombstoned) links and inactive endpoints are
// excluded. Sentinel: <=51 rows per kind, template budget 50.
MATCH (t:Task {tenant_id: $tenant_id, id: $task_id})-[r:IMPLEMENTED_IN]->(b:Branch)
WHERE t.is_deleted = false AND r.is_deleted = false AND r.tenant_id = $tenant_id
  AND b.tenant_id = $tenant_id AND b.is_deleted = false
RETURN t.id AS task_id, r.id AS edge_id, 'IMPLEMENTED_IN' AS edge_kind,
       r.link_method AS link_method, r.authority AS authority,
       b.id AS branch_id, b.ref AS branch_ref, b.head_sha AS branch_head_sha,
       null AS pr_id, null AS pr_number, null AS pr_state, null AS pr_draft,
       null AS pr_head_sha, null AS pr_base_ref,
       null AS target_branch_id, null AS repository_id
ORDER BY edge_id
LIMIT 51
UNION ALL
MATCH (t:Task {tenant_id: $tenant_id, id: $task_id})-[r:IMPLEMENTED_BY]->(pr:PullRequest)
WHERE t.is_deleted = false AND r.is_deleted = false AND r.tenant_id = $tenant_id
  AND pr.tenant_id = $tenant_id AND pr.is_deleted = false
OPTIONAL MATCH (pr)-[tg:TARGETS]->(base:Branch)
  WHERE tg.is_deleted = false AND tg.tenant_id = $tenant_id
    AND base.is_deleted = false AND base.tenant_id = $tenant_id
OPTIONAL MATCH (pr)-[ir:IN_REPOSITORY]->(repo:Repository)
  WHERE ir.is_deleted = false AND ir.tenant_id = $tenant_id
    AND repo.is_deleted = false AND repo.tenant_id = $tenant_id
RETURN t.id AS task_id, r.id AS edge_id, 'IMPLEMENTED_BY' AS edge_kind,
       r.link_method AS link_method, r.authority AS authority,
       null AS branch_id, null AS branch_ref, null AS branch_head_sha,
       pr.id AS pr_id, pr.number AS pr_number, pr.state AS pr_state, pr.draft AS pr_draft,
       pr.head_sha AS pr_head_sha, pr.base_ref AS pr_base_ref,
       base.id AS target_branch_id, repo.id AS repository_id
ORDER BY edge_id
LIMIT 51
