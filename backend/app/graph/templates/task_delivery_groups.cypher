// Task delivery groups: confirmed required delivery revisions with role,
// coverage and optional integration equivalences. Branch names and PR titles
// alone are insufficient; these mappings are the evidence.
MATCH (t:Task {tenant_id: $tenant_id, id: $task_id})-[r:DELIVERED_BY]->(c:Commit)
WHERE t.is_deleted = false AND r.is_deleted = false AND r.authority = 'CONFIRMED'
  AND c.tenant_id = $tenant_id AND c.is_deleted = false
RETURN r.delivery_id AS delivery_id, r.role AS role,
       r.implementation_revision AS implementation_revision,
       r.coverage AS coverage, r.pr_id AS pr_id,
       r.equivalent_to_delivery_id AS equivalent_to_delivery_id,
       c.sha AS commit_sha, c.committed_at AS committed_at
ORDER BY delivery_id, role
LIMIT 51
