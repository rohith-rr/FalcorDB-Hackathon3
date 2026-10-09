// Work periods for one task: the intersection of assignment and in-progress
// intervals per assignee, with interval accuracy/coverage. Unknown intervals
// cannot be treated as complete.
MATCH (t:Task {tenant_id: $tenant_id, id: $task_id})-[r:HAS_WORK_PERIOD]->(w:TaskWorkPeriod)
WHERE t.is_deleted = false AND r.is_deleted = false
  AND w.tenant_id = $tenant_id AND w.is_deleted = false
RETURN w.id AS period_id, w.task_id AS task_id, w.assignee_id AS assignee_id,
       w.valid_from AS valid_from, w.valid_to AS valid_to,
       w.time_accuracy AS time_accuracy, w.coverage AS coverage,
       w.observed_at AS observed_at, w.identity_binding_id AS identity_binding_id
ORDER BY w.valid_from, period_id
LIMIT 51
