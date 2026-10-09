// Current accessible documents linked to one task: incoming SPECIFIES /
// GOVERNS_PROCESS edges with document version, content hash/path and status.
// Excerpt rendering reads the versioned content store, never the node title.
MATCH (d)-[r]->(t:Task {tenant_id: $tenant_id, id: $task_id})
WHERE t.is_deleted = false AND r.is_deleted = false AND r.authority = 'CONFIRMED'
  AND (type(r) = 'SPECIFIES' OR type(r) = 'GOVERNS_PROCESS')
  AND d.tenant_id = $tenant_id AND d.is_deleted = false
  AND (d:DesignDoc OR d:ProcessDoc)
RETURN labels(d) AS doc_labels, d.id AS document_id, d.title AS title,
       d.version AS version, d.content_hash AS content_hash,
       d.content_path AS content_path, d.doc_status AS doc_status,
       d.document_type AS document_type, type(r) AS link_type,
       r.observed_at AS observed_at
ORDER BY document_id
LIMIT 51
