# rc.5 external-repository interoperability corpus

This directory is the implementation-neutral shared corpus for protocol
1.0.0-rc.5. It is generated from the accepted specification and
the released conformance vectors; it contains no Curator- or csk-specific
harness adapter.

`case-manifest.json` is the entry point. Repository bundles use
`raw-git-object-bundle-v1`: full raw object bytes, object IDs, refs,
snapshot bytes, modes, and expected build-source identities. A downstream
harness may materialize those bytes as an operation-private HTTP/SSH test
remote or as an inert local store, but it must not rewrite object, ref, or
snapshot bytes. Physical cache, staging, receipt, and lock paths remain
implementation-specific.

Regenerate and verify from the repository root:

```text
go run ./tools/generate-external-repository-corpus -root .
go test ./tools/generate-external-repository-corpus
```

`manifest.json` hashes every other corpus file. `source-inventory.json`
pins the exact accepted specification/schema/vector inputs. Expected receipt
and marker files are copied byte-for-byte from the rc.5 conformance suite.
