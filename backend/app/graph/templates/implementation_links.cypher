// Implementation PR/branch links for one task: planned/observed implementation
// branches, explicitly linked PRs and their base targets. A current PR head
// does not automatically prove the accepted task implementation.
MATCH (t:Task {tenant_id: $tenant_id, id: $task_id})
WHERE t.is_deleted = false
OPTIONAL MATCH (t)-[bi:IMPLEMENTED_IN]->(b:Branch)
  WHERE bi.is_deleted = false AND bi.tenant_id = $tenant_id
OPTIONAL MATCH (t)-[by:IMPLEMENTED_BY]->(pr:PullRequest)
  WHERE by.is_deleted = false AND by.tenant_id = $tenant_id
OPTIONAL MATCH (pr)-[tg:TARGETS]->(base:Branch)
  WHERE tg.is_deleted = false AND tg.tenant_id = $tenant_id
OPTIONAL MATCH (pr)-[inr:IN_REPOSITORY]->(repo:Repository)
  WHERE inr.is_deleted = false AND inr.tenant_id = $tenant_id
RETURN t.id AS task_id,
       collect(DISTINCT CASE WHEN b IS NULL THEN null
                             ELSE {branch_id: b.id, ref: b.ref, head_sha: b.head_sha,
                                   link_method: bi.link_method, authority: bi.authority}
                        END) AS implemented_in,
       collect(DISTINCT CASE WHEN pr IS NULL THEN null
                             ELSE {pr_id: pr.id, number: pr.number, state: pr.state,
                                   draft: pr.draft, head_sha: pr.head_sha,
                                   base_ref: pr.base_ref,
                                   target_branch: CASE WHEN base IS NULL THEN null ELSE base.id END,
                                   repository: CASE WHEN repo IS NULL THEN null ELSE repo.id END,
                                   link_method: by.link_method, authority: by.authority}
                        END) AS implemented_by
LIMIT 2
