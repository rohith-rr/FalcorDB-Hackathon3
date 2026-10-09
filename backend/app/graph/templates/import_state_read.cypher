// Durable per-projection ImportState readback (control metadata; not domain
// data). Missing record => UNINITIALIZED handled by the caller.
MATCH (c:ImportControl {graph_name: $graph_name, projection_id: $projection_id})
RETURN c.state AS state, c.generation AS generation,
       c.active_snapshot_id AS active_snapshot_id,
       c.pending_bundle_id AS pending_bundle_id,
       c.pending_bundle_hash AS pending_bundle_hash,
       c.last_published_at AS last_published_at,
       c.updated_at AS updated_at,
       c.last_failure AS last_failure
LIMIT 2
