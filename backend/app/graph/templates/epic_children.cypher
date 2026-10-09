// Epic progress: distinct non-cancelled eligible leaf work items under
// confirmed hierarchy. Empty denominator yields unavailable progress.
MATCH (e:Epic {tenant_id: $tenant_id, id: $epic_id})-[:HAS_TASK]->(child:Task)
WHERE child.is_deleted = false AND e.tenant_id = $tenant_id
OPTIONAL MATCH (child)-[:HAS_TASK]->(leaf:Task)
  WHERE leaf.is_deleted = false AND leaf.tenant_id = $tenant_id
WITH child, count(DISTINCT leaf) AS grandchildren,
     collect(DISTINCT CASE WHEN leaf.is_deleted = false THEN leaf.id END) AS leaf_ids
WITH child,
     CASE WHEN grandchildren = 0 THEN true ELSE false END AS is_leaf,
     child.id AS id, child.status AS status, child.raw_status AS raw_status
WITH collect({id: id, status: status, raw_status: raw_status, is_leaf: is_leaf}) AS members
RETURN members
