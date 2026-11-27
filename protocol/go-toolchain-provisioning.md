# Manager-Provisioned Go Toolchain

This document is normative for managers that implement [CIP-0040](../cips/CIP-0040-manager-provisioned-go-toolchain.md).
It defines automatic provisioning of a manager-owned Go toolchain for `go-v1`
and `go-repository-v1` compilation when no operator-selected Go toolchain is
present on the host.

## 1. Selection precedence

When preparing a `go-v1` or `go-repository-v1` build operation, a conforming
manager MUST resolve the Go executable in this exact order:

1. **Explicit `CURATOR_GO` or `GOROOT`:** if either environment variable is
   non-empty, the manager MUST use it directly and MUST NOT fall back to system
   roots or auto-download when it is invalid, absent, or fails probes.
2. **Existing sealed provisioned root:** `<manager-home>/tools/store/go/<pinned-version>/<os>-<arch>/go/bin/go`
   verified against its `.curator-tool-receipt.json` metadata.
3. **Standard trusted host roots (optional reuse):** fixed absolute locations
   (such as `/opt/homebrew/opt/go/libexec`, `/usr/local/go`, `/usr/lib/go` on
   Unix) canonicalized without reading caller `PATH`. A host root whose family
   is outside the manager's tested `go-v1` families is skipped.
4. **Automatic verified download:** unless `CURATOR_NO_AUTO_TOOLCHAIN=1` is set,
   the manager downloads the manager-pinned official Go archive for the current
   `<os>-<arch>` from `https://go.dev/dl/` and installs it into the sealed store
   path of step 2.

Caller `PATH` and package/manifest files MUST NEVER select a Go toolchain.

## 2. Pinned official release metadata

The manager ships exact pinned archive metadata for supported native platforms
(`darwin-arm64`, `darwin-amd64`, `linux-amd64`, `linux-arm64`). Every pin MUST
belong to a release family tested by the manager against the `go-v1`
conformance vectors (for example `1.25.5`).

Each entry fixes:

- `version`: exact Go version string (e.g. `1.25.5`);
- `platform`: `<os>-<arch>`;
- `url`: official `https://go.dev/dl/go<version>.<os>-<arch>.tar.gz` URL;
- `sha256`: lowercase 64-hex SHA-256 digest of the archive bytes.

## 3. Verification and sealed store layout

Before extracting any archive byte, the manager MUST verify the full downloaded
archive against the pinned SHA-256 digest. A digest mismatch MUST delete
temporary files and refuse with `toolchain_provisioning_digest_mismatch`.

Extraction MUST reject:

- absolute paths or paths containing `..` components;
- symbolic links whose resolved target escapes the staging directory;
- device nodes, FIFOs, and unknown archive entry types.

The extracted tree is published atomically into:

```text
<manager-home>/tools/store/go/<version>/<os>-<arch>/go
```

with private directory mode `0700` on POSIX, accompanied by a sibling
`.curator-tool-receipt.json` conforming to
[`tool-receipt-v1.schema.json`](../schemas/tool-provisioning-v1/tool-receipt-v1.schema.json).

## 4. Closed `go-v1` driver handoff

The resolved `<GOROOT>/bin/go` executable MUST be passed to the closed `go-v1`
driver as an explicit toolchain selection. Provisioning does not bypass
[Manager profile section 2.2](../profiles/manager.md#22-closed-go-v1-toolchain-and-process-graph)
probes or [Core section 8.2](core.md#82-go-toolchain-identity)
`curator-go-toolchain-v1` fingerprinting.
