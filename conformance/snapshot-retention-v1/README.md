# Snapshot-Cache Retention Conformance Vectors (`snapshot-retention-v1`)

Standalone decision vectors for manager profile section 10.1
([profiles/manager.md](../../profiles/manager.md#101-snapshot-cache-retention))
and the informative `curator cache prune` interface
([cli/curator.md](../../cli/curator.md), issue #75).

- `snapshot-retention.json` is generated deterministically by
  `tools/generate-vectors/snapshot_retention.go` and validated by
  `validate_snapshot_retention_vectors` in `tools/validate.py`.
- Kept outside frozen `conformance/v1/` so released `1.0.0-rc.13`/`rc.14`
  manifests and existing implementation conformance pins remain immutable until
  a downstream consumer adopts this family.
