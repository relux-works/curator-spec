# CIP-0040: Manager-provisioned Go toolchain for `go-v1` builds

- **Status:** Accepted (operator, 2026-11-27)
- **Owner:** Ivan Oparin
- **Created:** 2026-11-27
- **Related:** [CIP-0007](CIP-0007-manager-provisioned-cli-tools.md) (manager-provisioned CLI tools); [Core section 8.2](../protocol/core.md#82-go-toolchain-identity); [Manager profile section 2.2](../profiles/manager.md#22-closed-go-v1-toolchain-and-process-graph); [Go toolchain provisioning](../protocol/go-toolchain-provisioning.md)
- **Affects:** `protocol/go-toolchain-provisioning.md`, `curator` (`internal/toolprov`, `internal/install`, `internal/envprofile`)

## Summary

A fresh macOS or Ubuntu Linux workstation with only `curator` installed cannot
compile skills that declare `go-v1` commands unless an operator manually
installs a compatible Go toolchain and sets `CURATOR_GO` or `GOROOT`. This CIP
specifies automatic, closed, SHA-256-verified provisioning of an official Go
release into `<manager-home>/tools/store/go/<version>/<os>-<arch>/go` whenever
no operator-selected Go toolchain (`CURATOR_GO` / `GOROOT`) or trusted host Go
root is present.

## Motivation and user stories

1. A new user installs `curator` on a clean macOS or Ubuntu machine without Go,
   runs `curator profile install <profile-url>`, and launches an agent profile
   whose skills ship Go source (`go-v1`). Compilation succeeds automatically
   without asking the user to install Go manually.
2. An operator who explicitly pins `CURATOR_GO` or `GOROOT` retains strict,
   fail-closed control: an invalid or mismatched explicit selector refuses
   rather than silently downloading a toolchain.
3. Offline or hermetic environments can disable automatic downloads with
   `CURATOR_NO_AUTO_TOOLCHAIN=1`.

## Current state

`profiles/manager.md` section 2.2 requires `go-v1` to select `<GOROOT>/bin/go`
independently of package inputs and never from caller `PATH`, verifying the
root with three fixed probe vectors and `curator-go-toolchain-v1`
fingerprinting. `curator`'s `internal/godriver` accepts only explicit
`CURATOR_GO` or `GOROOT` (or `build.Default.GOROOT` when present on the host).
On machines without Go installed, `go-v1` installs fail until the operator
manually provisions Go.

## Design

### Options considered

1. **Require manual Go installation:** preserves zero-download behavior but
   breaks zero-prerequisite profile onboarding on fresh macOS/Ubuntu hosts.
2. **Search caller `PATH` for `go`:** violates `profiles/manager.md` section
   2.2 because caller `PATH` may contain wrappers, shims, or untrusted binaries.
3. **Manager-provisioned sealed Go store (Recommended):** keep `godriver`
   strict and closed; add a manager-owned bootstrap layer that resolves:
   1. Explicit `CURATOR_GO` or `GOROOT` (strict, no fallback on failure).
   2. Existing sealed manager-provisioned root at
      `<manager-home>/tools/store/go/<pinned>/<os>-<arch>/go`.
   3. Standard operator-trusted system Go roots (`/opt/homebrew/opt/go/libexec`,
      `/usr/local/go`, `/usr/lib/go`) resolved canonically without consulting
      caller `PATH`.
   4. Automatic download of the manager-pinned official Go archive from
      `https://go.dev/dl/go<version>.<os>-<arch>.tar.gz` verified against
      exact built-in SHA-256 digests for `darwin-arm64`, `darwin-amd64`,
      `linux-amd64`, and `linux-arm64`, atomically extracted into the private
      `0700` store root with a `.curator-tool-receipt.json` record.

### Recommendation

Adopt Option 3. The provisioned `<GOROOT>/bin/go` is passed into `godriver`
through the existing explicit `CuratorGo` selector so every existing probe,
allowlisted family check, and `curator-go-toolchain-v1` fingerprint executes
unchanged.

## Security considerations

- **No package influence:** skill manifests, profile manifests, and build
  repositories cannot select the Go version, archive URL, or digest.
- **Exact SHA-256 verification:** download bytes are streamed and verified
  against hardcoded official `go.dev` release SHA-256 digests before any
  extraction runs; mismatches delete staging and fail closed.
- **Archive containment:** tar extraction rejects absolute paths, `..`
  components, symlinks escaping the extraction root, device nodes, and FIFOs.
- **Private atomic publication:** extraction stages into a private temporary
  directory under `<manager-home>/tools/store/go/` and publishes via atomic
  rename with mode `0700`.
- **Same closed `godriver` verification:** after provisioning, `godriver` still
  executes its closed probe vectors and `curator-go-toolchain-v1` fingerprint.

## Compatibility and migration

Fully backward-compatible. Machines with `CURATOR_GO`, `GOROOT`, or a trusted
system Go installation keep their existing selection. Existing `godriver`
conformance tests that pass explicit `godriver.Config` remain unaffected.

## Specification changes

- Add [Go toolchain provisioning](../protocol/go-toolchain-provisioning.md).
- Record `CIP-0040` in [CIP index](README.md) and
  [platform contract disposition](platform-contract-disposition.md).

## Implementation plan

1. Add `internal/toolprov` Go toolchain resolver and verified downloader in
   `curator` supporting `darwin-arm64`, `darwin-amd64`, `linux-amd64`, and
   `linux-arm64`.
2. Wire `EnsureGoToolchain` at the manager build boundary (`internal/install`
   and profile command root compilation) while preserving strict explicit
   `CURATOR_GO` / `GOROOT` refusal semantics.
3. Add unit tests covering explicit-selector precedence, SHA-256 mismatch
   refusal, archive traversal refusal, and real store provisioning via local
   HTTP fixtures, plus a clean-room E2E test with `go` absent from `PATH`.

## Test plan

- Unit tests with local HTTP server serving a tar.gz fixture and verifying:
  matching SHA-256 succeeds and writes `.curator-tool-receipt.json`; bad
  SHA-256 refuses and leaves no store entry; `../` tar path refuses;
  `CURATOR_NO_AUTO_TOOLCHAIN=1` refuses without network access; explicit
  `CURATOR_GO` bypasses auto-download.
- End-to-end profile installation test with `CURATOR_HOME` isolated and host
  `go` removed from `PATH` and `GOROOT` unset.

## Open questions for the operator

None. Operator approved built-in pinned Go provisioning for macOS and Ubuntu
Linux on 2026-11-27.
