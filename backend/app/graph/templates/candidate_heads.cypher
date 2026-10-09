// Candidate heads for one repository: every live branch with its observed
// head commit, plus the configured stable ref marker. One active HEAD_AT per
// branch is enforced at publication.
MATCH (repo:Repository {tenant_id: $tenant_id, id: $repository_id})-[hb:HAS_BRANCH]->(b:Branch)
WHERE hb.is_deleted = false AND hb.tenant_id = $tenant_id
  AND b.is_deleted = false AND b.exists = true
MATCH (b)-[h:HEAD_AT]->(c:Commit)
WHERE h.is_deleted = false AND h.tenant_id = $tenant_id AND c.is_deleted = false
RETURN b.id AS branch_id, b.ref AS ref, b.head_sha AS head_sha,
       b.is_protected AS is_protected, c.sha AS head_commit_sha,
       c.committed_at AS head_committed_at
ORDER BY ref
LIMIT 51
