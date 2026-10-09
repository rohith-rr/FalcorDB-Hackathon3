// Individual reviews of PRs linked to one task: reviewer, state, submitted
// time, reviewed SHA and provider state including dismissal. Never flattened
// into an unversioned aggregate review string.
MATCH (t:Task {tenant_id: $tenant_id, id: $task_id})-[by:IMPLEMENTED_BY]->(pr:PullRequest)
WHERE by.is_deleted = false AND by.tenant_id = $tenant_id AND t.is_deleted = false
MATCH (rv:Review)-[rev:REVIEWS]->(pr)
WHERE rev.is_deleted = false AND rev.tenant_id = $tenant_id
  AND rv.tenant_id = $tenant_id AND rv.is_deleted = false
OPTIONAL MATCH (rv)-[rc:REVIEWED_COMMIT]->(c:Commit)
  WHERE rc.is_deleted = false AND c.tenant_id = $tenant_id
RETURN rv.id AS review_id, rv.reviewer_id AS reviewer_id, rv.state AS state,
       rv.submitted_at AS submitted_at, rv.commit_sha AS reviewed_sha,
       rv.dismissal_type AS dismissal_type, rv.dismissal_reason AS dismissal_reason,
       pr.id AS pr_id, pr.state AS pr_state, c.sha AS reviewed_commit_node_sha
ORDER BY review_id
LIMIT 51
