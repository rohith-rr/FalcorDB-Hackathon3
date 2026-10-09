// One dependency frontier step for iterative traversal. Returns explicit edge
// properties (not just destination names); sentinel budget 200, LIMIT 201.
MATCH (t:Task)-[r:DEPENDS_ON]->(d:Task)
WHERE t.id IN $frontier_ids AND t.tenant_id = $tenant_id
  AND d.tenant_id = $tenant_id AND r.tenant_id = $tenant_id
  AND t.is_deleted = false AND d.is_deleted = false AND r.is_deleted = false
  AND r.authority = 'CONFIRMED'
RETURN t.id AS source_id, r.id AS edge_id, r.dependency_kind AS dependency_kind,
       r.link_method AS link_method, r.source_record_ref AS source_record_ref,
       d.id AS target_id, d.external_key AS target_key, d.status AS target_status
LIMIT 201
