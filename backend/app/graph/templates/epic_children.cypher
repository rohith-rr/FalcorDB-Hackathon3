// One bounded epic-membership frontier page. GraphQueryService walks these
// pages with a visited set instead of enumerating every path, under one
// projection admission, and applies the global sentinel to eligible leaves.
// Paging by application ID preserves wide frontiers and arbitrary depth.
// Cancelled ancestors remain traversable; cancelled children still make
// their parent an intermediate story rather than an eligible leaf.
MATCH (e:Epic {tenant_id: $tenant_id, id: $epic_id})
WHERE e.is_deleted = false
WITH e
MATCH (parent {tenant_id: $tenant_id})-[r:HAS_TASK]->(member:Task {tenant_id: $tenant_id})
WHERE parent.id IN $frontier_ids AND parent.is_deleted = false
  AND (parent = e OR 'Task' IN labels(parent))
  AND r.is_deleted = false AND r.authority = 'CONFIRMED' AND r.tenant_id = $tenant_id
  AND member.is_deleted = false
  AND ($after_id IS NULL OR member.id > $after_id)
WITH DISTINCT member
ORDER BY member.id
LIMIT $limit
OPTIONAL MATCH (member)-[hc:HAS_TASK]->(child:Task {tenant_id: $tenant_id})
WHERE hc.is_deleted = false AND hc.authority = 'CONFIRMED' AND hc.tenant_id = $tenant_id
  AND child.is_deleted = false
RETURN member.id AS id, member.status AS status, member.raw_status AS raw_status,
       count(child) > 0 AS has_live_children
ORDER BY id
