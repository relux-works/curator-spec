# Security policy

## Reporting

Report suspected vulnerabilities privately to `ivan@relux.works`. Include the
affected protocol section or schema, a minimal reproducer, and the security
impact. Do not include secrets, private registry records, or production keys.

Acknowledgement is targeted within three business days. Coordinated disclosure
and release timing depend on severity and whether deployed implementations need
updates before publication.

## Security model

The protocol treats skill repositories, manifests, registry responses, cache
entries, and bundles as untrusted input. Conforming implementations MUST apply
the parsing limits and validation rules in the normative documents before
using paths, signatures, references, or configuration values.

Repository control includes source, both manifest spellings, a package-provided
root `.csk-install.json`, `go.mod`, `go.sum`, `vendor/`, build constraints,
compiler directives, embedded inputs, assembly, host objects, filenames, and
file sizes. Build receipts, artifacts, stale markers, and candidate cache bytes
are also untrusted parser and hash input until admitted through the protected
cache boundary below.

The protocol provides integrity, provenance, revocation, rollback detection,
and deterministic installation. Capability declarations and source auditing
are review and policy surfaces; they are not runtime sandboxes. A successful
audit or registry attestation does not make skill-provided code safe to execute
without the consuming agent's own isolation and authorization controls.

## Compile-only build boundary

Manifest schema 6 does not introduce package hooks. It admits only untrusted Go
source as compiler input to the closed, manager-owned `go-v1` process described
in `protocol/core.md`. During install, update, repair, status, garbage
collection, and dry-run, a conforming manager:

- MUST NOT invoke a package-provided executable, script, shell command,
  interpreter entry point, shared library, test, package-manager hook, build
  backend, or arbitrary build recipe;
- MUST NOT accept or derive package-controlled executable names, argument
  arrays, environment variables, flags, tags, linker/compiler options,
  toolchains, output names or paths, build scripts, pre/post-build actions, or
  output-selection rules;
- MUST NOT load package-produced code as a compiler or manager plugin, macro,
  annotation processor, source generator, loader, or procedural extension;
- MUST NOT use `sh -c`, `cmd.exe /c`, PowerShell, or any other shell to create a
  build command;
- MUST NOT run `go generate`, `go run`, `go test`, `go install`, `go get`, any
  `go mod` mutation/download command, or a package-selected VCS/network helper;
- MUST NOT invoke or fall back to cgo, an external compiler/linker, libgcc
  discovery, package-controlled assembly, host objects, or a dynamic import
  requested by `//go:cgo_import_dynamic` in active non-standard Go source;
- MUST NOT execute the built output for version discovery, smoke testing,
  post-processing, receipt generation, rollback, validation, or any other
  install-time purpose; and
- MAY perform fixed parsing, hashing, copying, permission changes, and schema
  validation in manager code, and MAY pass validated untrusted source bytes to
  the exact operator-trusted `go-v1` compiler pipeline.

The manager therefore MUST NOT invoke package Make, CMake, Ninja, or Meson
recipes; Cargo build scripts or procedural macros; SwiftPM manifests, plugins,
or macros; Maven or Gradle plugins/tasks; MSBuild tasks or Roslyn generators;
npm lifecycle scripts, Node bundler configuration, loaders, or plugins; Python
PEP 517 build backends; or comparable executable build-system surfaces. There
is no generic-hook fallback when a package cannot fit `go-v1`. A future driver
requires a new closed identifier and independent security review.

`go-v1` forces internal linking and disables libgcc lookup, cgo, PGO,
workspaces, toolchain switching, non-standard assembly, host objects, and the
active non-standard `//go:cgo_import_dynamic` directive. If the native target
or dependency graph cannot build within that surface, installation fails. A
manager MUST reject a build when it cannot enforce the fixed environment,
network denial, source/context separation, native target, and process graph;
it MUST NOT approximate the contract.

### Compiler-input trust boundary

Compile-only does not mean trusted source or an invulnerable compiler. Malicious
source may exploit parser/compiler defects or exhaust CPU, memory, disk,
processes, diagnostic output, or filesystem traversal. The selected Go
toolchain, manager, operating system, hashing/canonicalization code, and
manager-owned policy/staging roots are trusted; package source and compiler
diagnostics are not. Source is read-only to children, standard input is closed,
and stdout/stderr MUST be bounded and redacted before presentation. Managers
MUST apply filesystem and network denial plus time, memory, disk, process-count,
and output limits where the host supports them. The compiled artifact remains
untrusted package code until a user later invokes the installed command under
the consuming environment's authorization and isolation policy.

### Protected-cache trust boundary

Receipt and marker SHA-256 values establish deterministic consistency and
currentness; they are not signatures, MACs, registry attestations, or
independent proof that `go-v1` produced an artifact. Persistent reuse is
permitted only inside manager-created state whose ownership, private
permissions or DACL, containment, file type, and link safety are revalidated
on every lookup and before locked publication/commit. A self-consistent receipt
outside that boundary is attacker-controlled and MUST be treated as a miss.
Managers that cannot enforce the boundary MUST disable persistent reuse and
rebuild from the revalidated snapshot; they MUST NOT repair permissions and
adopt pre-existing candidate bytes.

The v1 boundary assumes an adversary cannot mutate protected state as the
manager's operating-system principal or as a trusted administrator. Arbitrary
same-principal code execution, administrator/root or kernel compromise, and
hostile storage below the operating system are outside this install-time
invariant because they can replace the manager and markers as well as receipts.
Deployments that cannot accept that assumption MUST disable persistent cache
reuse. Authenticated cross-principal artifact provenance would require a future
protocol; a plain receipt hash does not provide it.

Client snapshot high-water state is security state. It is stored separately
from disposable registry responses, written atomically before acceptance, and
included in protected machine backups. Existing corruption or a failed write
is fail-closed. Loss of all local state still requires an out-of-band
authenticated checkpoint or explicit operator rebootstrap; signatures alone
cannot prove that a newly presented snapshot is not an old valid view.

Registry trust anchors are distributed out of band. Removing a key from the
pinned set revokes trust in signatures made solely by that key. Key rotation
and incident behavior are defined in `protocol/registry.md`. The production
registry threat model, including replay, rollback, equivocation, cursor abuse,
resource exhaustion, credential compromise, crash recovery, and backup
rollback, is normative in `profiles/registry-service.md`.

## Release review

Stable protocol releases require:

1. schema and vector CI on all supported operating systems;
2. both conforming clients passing the same released vectors;
3. review of changes to canonicalization, hashing, signatures, snapshots,
   transparency logs, source identities, and path handling;
4. a signed release tag and immutable release artifacts.

`1.0.0-rc.2` is not promoted to stable until an independent security review
and an independent interoperability review conform to
`reviews/review-report-v2.schema.json`. Each report identifies the reviewed
candidate commit and a public authorship trail. Stable release CI rejects open
critical or high findings and rejects normative changes made after either
review. See `RELEASE.md` for the complete gate.
