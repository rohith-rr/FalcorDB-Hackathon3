// Exact scoped task lookup: zero/one result expected; two matches are a data
// conflict detected by the caller (budget 2).
MATCH (t:Task {tenant_id: $tenant_id, project_id: $project_id, external_key: $task_key})
WHERE t.is_deleted = false
RETURN t.id AS task_id, t.external_key AS external_key, t.status AS status,
       t.raw_status AS raw_status, t.work_item_type AS work_item_type,
       t.assignee_ids AS assignee_ids, t.repository_ids AS repository_ids
LIMIT 3
