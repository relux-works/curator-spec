# Curator Manager Profile 1.0

This document is normative for implementations claiming the **manager**
conformance class. It defines behavior around the portable objects in the
protocol core. It does not prescribe an executable name or machine-home path.

## 1. Machine state and configuration

Each manager selects its own `<manager-home>`, user-config environment
variable, and system-config path. It MUST document them and MUST keep its
caches, runtime store, audit state, and global/hybrid state below that home.
Different implementations do not share machine-local state by default.

The logical user configuration conforms to `manager-config-v1.schema.json` and
contains a source root, project registrations, manager defaults, source
allowlist, audit policy, and pinned registries. The configuration file SHOULD be
readable and writable only by its owner where the platform supports
permissions.

Managers MUST reject unknown configuration fields and apply schema defaults
before use. `projects` member names, `project_alias`, and `checkout_alias` are
portable identifiers; the latter two default to the member name when absent or
null. They are derived machine matching keys, distinct from the operator-facing
Unicode `Skillfile.json` `project.alias`. Agent lists are sets of portable
identifiers. `preferred_locale: null` means no machine preference.

An audit registry requires `name` and canonical `url`; `public_keys` defaults to
an empty set and `enabled` defaults to true. A registry with no pinned key is
not trusted and produces a warning. Registry record cache TTL defaults to 3600
seconds, offline grace to 604800 seconds, snapshot maximum age to 604800
seconds, and future clock skew to 300 seconds. Zero cache TTL disables fresh
cache hits; zero offline grace disables stale fallback; zero clock skew permits
no future offset. The backend request limit defaults to 1048576 bytes and MUST
NOT exceed 10485760 bytes.

An OPTIONAL system configuration conforms to `system-config-v1.schema.json`
and is merged before parsing the effective user configuration:

1. `locked` contains only `audit_registries`,
   `disable_builtin_registries`, `allowed_sources`, and `audit`;
2. a locked key MUST be set by the system file and overrides a user value with
   a warning naming the system file;
3. an unlocked system key is a default and a user value wins;
4. malformed or unreadable enforced configuration fails closed.

Configuration writes MUST use a same-directory temporary file followed by
atomic replacement. Implementations SHOULD serialize concurrent writers with a
per-config lock and MUST never expose a partially written JSON object.

## 2. Installation lifecycle

The manager MUST implement installation as read-only planning, optional private
compilation, and one serialized publication transaction. This lifecycle applies
to project, global, and hybrid installation, upgrade, and repair. Package code
MUST NOT execute during any phase; the closed `go-v1` compiler process graph
below is the only exception to passing package bytes to a trusted tool.

### 2.1 Read-only planning and source gates

For each operation the manager performs these phases in order:

1. load `Skillfile.json`, or skip an absent manifest, and determine effective
   agents and locale;
2. verify generated project and adapter paths are ignored by git, load
   development substitutions, reject them under strict audit, and add
   applicable hybrid declarations;
3. resolve every ref to an immutable raw snapshot and validate its complete
   tree before reading a build-cache entry or starting any Go process;
4. parse and validate both manifest names according to Protocol Core section
   4, validate link-free disjoint runtime roots, build roots, and source
   directories, and derive every artifact-relative path from its command name;
5. exclude every build root as a whole subtree from agent context before
   locale rendering and from commit-keyed runtime copying, identically for a
   real build, cache hit, and dry run;
6. compute `curator-build-source-v1` over every regular file in each fully
   validated raw snapshot, including a package-provided root
   `.csk-install.json`, and freeze that snapshot instance until its last build
   child exits;
7. build the provider-first dependency closure, apply source allowlists and
   snapshot checks, validate every skill package, reject command, shim,
   portable-path, case-folding, and platform-path collisions, and verify system,
   legacy command, and MCP requirements;
8. run source-audit policy, resolve trusted registries and attestations, reject
   revocation or strict unknown results, and apply moved-tag policy; and
9. only after all preceding gates pass, resolve and fingerprint a trusted
   toolchain, derive build inputs and logical cache keys, validate the protected
   cache boundary, and inspect eligible receipts and artifacts read-only.

Snapshot validation MUST reject links, special files, invalid protocol paths,
duplicate encoded paths, and platform path collisions. A build root MUST be a
real link-free directory below the snapshot, MUST NOT be `.`, MUST be disjoint
from every runtime root, and MUST contain the nearest ancestor `go.mod` of each
of its commands' `source_dir` values. Every declared build root MUST be used.
Generated artifacts remain only in manager-owned staging and immutable cache
state and MUST NOT become agent-facing context.

Audit and registry gates therefore precede both persistent cache lookup and
compilation. Neither a cache hit nor a dry run may bypass source validation,
static context exclusion, build-source hashing, closure construction, collision
checks, audit, attestation, revocation, or moved-tag evaluation.

### 2.2 Closed `go-v1` toolchain and process graph

A conforming manager MUST support an operator-trusted Go 1.23 release family
that it has tested against the `go-v1` conformance vectors. It MAY allowlist
additional Go release families only after testing those families against the
same vectors. It MUST reject a pre-1.23, malformed, package-selected, or
otherwise unknown release, including a newer release merely ordered after a
known one. The launcher is selected independently of the package and MUST be
the regular executable `<GOROOT>/bin/go` (`bin/go.exe` on Windows), never a
wrapper, repository file, runtime command, project shim, manifest value, or
executable found through the user `PATH`.

Before entering a package-controlled directory, the manager creates an
operation-private probe root. From a manager-owned empty working directory it
invokes the resolved `go` executable directly with exactly these first three
argument vectors, once per operation:

```text
[<resolved-go>, "telemetry", "off"]
[<resolved-go>, "version"]
[<resolved-go>, "env", "-json", "GOROOT", "GOHOSTOS", "GOHOSTARCH", "GOOS", "GOARCH", "GO386", "GOAMD64", "GOARM", "GOARM64", "GOMIPS", "GOMIPS64", "GOPPC64", "GORISCV64", "GOWASM", "GOTELEMETRY", "GOTELEMETRYDIR"]
```

The manager requires the probed `GOROOT` to equal the independently resolved
root, normalizes the bounded single-line `go version` output, verifies the
native host and target values, and only then fingerprints the selected tree
using `curator-go-toolchain-v1` as defined by Protocol Core section 8.2.

For each active build command, in provider-first closure order and then
Unicode-scalar lexical command order within a node, it invokes exactly these
two further argument vectors from the command's canonical `source_dir`:

```text
[<resolved-go>, "list", "-mod=vendor", "-deps", "-json", "-buildvcs=false", "-compiler=gc", "-pgo=off", "."]
[<resolved-go>, "build", "-mod=vendor", "-trimpath", "-buildvcs=false", "-buildmode=exe", "-compiler=gc", "-pgo=off", "-ldflags=-linkmode=internal -libgcc=none", "-o", <manager-staging-artifact>, "."]
```

These are the only five Go argument-vector forms. The `-ldflags=...` value and
manager-derived staging path are each one argument. The manager MUST NOT use a
shell, command string, response file, package pattern, package-selected
executable, environment value, argument, tag, flag, output path, build recipe,
hook, plugin, generator, overlay, post-build action, or fallback command.

The bootstrap environment starts empty except for indispensable operating
system process variables. It sets `GOENV=off`, `GOTOOLCHAIN=local`, `LC_ALL=C`,
and `LANG=C`, contains no inherited `GOROOT` or target, and sets `GOPATH`,
`GOMODCACHE`, `GOCACHE`, `GOTMPDIR`, `HOME`, `XDG_CONFIG_HOME`, `PATH`, and
`TMPDIR` below operation-private roots. `PATH` names a manager-owned empty
directory. On Windows, `APPDATA`, `LOCALAPPDATA`, `USERPROFILE`, `TEMP`, and
`TMP` are also private. The manager MUST verify that `GOTELEMETRY` is `off` and
that `GOTELEMETRYDIR` is below the private platform configuration root.

After the probes, the build environment retains those settings and adds only
the resolved `GOROOT`, native `GOOS` and `GOARCH`, exactly one applicable
trusted architecture-tuning variable returned by the fixed probe, and:

```text
GO111MODULE=on
GOFLAGS=
GOPROXY=off
GOSUMDB=off
GOPRIVATE=
GONOPROXY=none
GONOSUMDB=none
GOVCS=*:off
GOWORK=off
CGO_ENABLED=0
GO_EXTLINK_ENABLED=0
GOEXPERIMENT=
```

No ambient or package Go, compiler, assembler, linker, telemetry,
executable-search, workspace, proxy, authentication, or tuning variable may be
inherited. `GOOS` and `GOARCH` MUST equal the probed host target; cross-builds
are unsupported. Module resolution is vendor-only and networkless. The manager
MUST NOT download, tidy, vendor, generate, test, run, install, or fetch a
package, use a workspace or PGO profile, or switch toolchains. A `go.mod`
version or `toolchain` directive that would require switching to an untrusted or
unallowlisted toolchain is rejected rather than downloaded or approximated.

Only the fingerprinted `go` executable and regular executable children below
the fingerprinted `GOROOT/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/` may start. The
source snapshot is read-only to every child and the toolchain and snapshot MUST
remain unchanged until the last child exits. No shell, VCS client, network
helper, external compiler, assembler, linker, libgcc helper, or other process
may enter the graph.

### 2.3 Dependency and artifact preflight

On a real cache miss, the fixed `go list` command MUST complete before the
corresponding `go build`. Its complete JSON stream MUST cover the root and every
active dependency, contain exactly one non-`DepOnly` root named `main`, contain
no incomplete result, `Error`, or `DepsErrors`, and select no tests.

Only a result with both `Standard == true` and `Goroot == true` is a trusted
toolchain package. Its directory and every listed source, module, and embedded
input MUST remain below the fingerprinted `GOROOT`. Every other result, its
package directory, module file, active Go file, and every active embedded input
MUST be a regular file below the command's build root. Escaped, missing,
linked, special, or out-of-root input is rejected.

Every result MUST have empty `SysoFiles`. Every non-standard result MUST also
have empty `CgoFiles`, `CFiles`, `CXXFiles`, `MFiles`, `HFiles`, `FFiles`,
`SFiles`, `SwigFiles`, and `SwigCXXFiles`. Thus cgo, package-controlled C, C++,
Objective-C, Fortran, assembly, SWIG, and host objects are rejected throughout
the active dependency graph. Each active non-standard `GoFiles` file is scanned
as exact bytes and rejected if it contains `//go:cgo_import_dynamic`. Any
violation fails before `go build`.

The fixed build forces the native gc compiler, disabled PGO and cgo, and
internal linking with no libgcc. If internal linking cannot produce the output,
the command fails; there is no external-link or libgcc fallback. The only
output is the manager-derived `bin/<command>` or `bin/<command>.exe` at a
bounded regular file in operation staging. The manager hashes it and applies
manager-defined executable permissions but MUST NOT execute it for validation,
version discovery, smoke testing, post-processing, receipt generation,
rollback, repair, or recovery.

### 2.4 Build cache and dry-run planning

For each active build command, the manager derives the complete build input,
logical cache key, canonical receipt, receipt hash, and artifact-relative path
exactly as specified by Protocol Core section 9. Persistent reuse is permitted
only below an implementation-specific cache boundary resolved independently of
package input and proven manager-created, manager-owned, privately mutable,
contained, regular-file-only, and link-safe. The manager verifies that boundary
and every entry component on each lookup and again under the manager-home
mutation lock. A manager unable to prove the boundary MUST disable persistent
reuse.

A candidate hit is accepted only after the manager recomputes build-source
identity, cache key, complete expected input, exact canonical receipt bytes and
hash, manager-derived artifact path, artifact hash, and byte length without
following links or executing the artifact. Unknown fields or unsupported
receipt, driver, build-source, or toolchain versions are rejected. Internally
consistent bytes outside the protected boundary are not provenance: a real
operation rebuilds from the revalidated snapshot into new protected state,
dry-run reports `would-rebuild-untrusted-cache`, and status is non-current.

A dry run performs all read-only planning and package-independent toolchain
probes above, rechecks generation digests for every shared target it consulted,
and removes all operation-private state before returning. It reports, per build
command, `cache-hit`, `would-preflight-and-build`,
`would-rebuild-untrusted-cache`, `corrupt`, or `unsupported`. A cache miss is
`would-preflight-and-build` because dry-run MUST NOT run `go list`, `go build`,
a compiler, or a linker.

A dry run acquires no project, cache-build, or manager-home mutation lock and
performs no recovery write, quarantine, permission repair, cache publication,
GC, or other persistent mutation. It MUST leave unchanged every existing or
potential persistent source checkout; snapshot, response, toolchain memo,
module, build, runtime, or audit cache; audit, registry, revocation, and
rollback state; configuration file; lock file; journal; backup; marker; shim;
environment file; context or runtime tree; adapter ledger or mirror; consumer
ledger; and GC metadata. Network reads and removable temporary workspaces are
permitted, but no temporary probe, Go cache, or staging directory may remain
after return. Read-only inspection MUST avoid changing access times where the
platform provides a no-atime facility.

### 2.5 Private build and serialized publication

A real single-project operation holds its project operation lock from planning
through handoff. A multi-project operation acquires project locks by canonical
project identity in unsigned UTF-8 byte order. These locks serialize planning
for the affected project targets but do not authorize shared-state mutation.

After read-only planning, the manager builds every miss and verifies every
artifact and canonical receipt in operation-private staging outside the
manager-home mutation lock. Optional per-key build locks are an optimization;
the manager holds at most one at a time and releases it before acquiring the
home lock. If any preflight or build fails, it removes the operation staging.
No recovery, cache publication, quarantine, permission repair, journal
mutation, target swap, or GC may occur before every current-operation miss is
built and verified. Any preflight or build failure MUST preserve the
installation, consumers, and live caches byte-for-byte as they were when the
operation began.

After all private builds succeed, the manager acquires the exclusive
manager-home mutation lock shared by project, global, hybrid, runtime, adapter,
consumer, build-cache publication, recovery, repair, and GC paths. While
holding it, the manager:

1. recovers every incomplete journal;
2. revalidates the protected cache boundary, every candidate or competing
   winner entry, every shared generation, target owner, and expected preimage
   used by the plan after recovery;
3. releases the lock and restarts from the earliest affected read or build when
   recovery or revalidation changes closure, activation, cache trust, required
   key, target ownership, expected preimage, or any other plan assumption;
4. atomically publishes missing staged entries into protected state as complete
   immutable directories, never merging into an existing entry; and
5. creates one durable rollback journal for the whole manager-home transaction.

If another operation published the same key first, the manager validates the
winner under the lock. It discards a byte-identical staged loser; differing
bytes for one logical key are a determinism or corruption error. A corrupt live
entry may be quarantined or replaced only under this lock from an already
verified staged build. An untrusted old boundary is never made private and then
adopted; a new protected boundary receives freshly rebuilt bytes.

The one journal records a unique transaction identifier, canonical project
identity, and, for every mutable target, its canonical target identifier,
expected generation or preimage digest, backup path, desired digest, and commit
state. Targets commit in these deterministic classes:

1. project and global contexts and markers;
2. runtime, shim, and environment targets;
3. adapter ledgers and hybrid or global mirrors;
4. stale managed removals; and
5. the machine-wide consumer ledger last.

Canonical identifiers are sorted unsigned-bytewise within a class. Backups
remain until all target swaps and the consumer ledger are durable. Recording
the consumer last prevents a failed installation from advertising state that
was not installed and prevents concurrent projects from losing ledger updates.

If cache publication or any target swap fails, the manager keeps the home lock
and restores journaled targets in exact reverse commit order. Before restoring
a target it requires the current digest to equal the journal's desired digest;
a mismatch is implementation corruption and MUST NOT overwrite unknown state.
A transaction-owned cache entry may be removed during rollback only after a
fresh locked mark proves that no valid marker or journal references it.
Retaining an unreferenced immutable entry is always safe. Existing valid cache
entries are never modified during rollback, and the built artifact is never a
rollback program or verifier.

After a successful commit the manager durably removes backups and marks or
removes the journal, then runs runtime, snapshot, and compiled-artifact cache GC
while still holding the home lock. GC failure is reported as a maintenance
warning and does not roll back the successful installation. The manager
releases the manager-home lock before releasing project locks.

Lock ordering is fixed: project operation locks in canonical order, then at
most one optional cache-build lock, which is released, then the manager-home
mutation lock. A process MUST NOT acquire a project or cache-build lock while
holding the home lock. A standalone recovery or standalone GC acquires only the
home lock; recovery within install or repair occurs only after private builds,
under the home lock already ordered after the project locks. Private validation
and compilation may run concurrently for independent projects; shared
publication, commit, rollback, recovery, repair, and GC are serialized.

### 2.6 Recovery and repair

Recovery runs under the manager-home mutation lock before any new shared
mutation. Within install or repair it runs only in the serialized publication
phase after every private build succeeds; it MUST NOT run as a pre-build pass.
It scans every incomplete journal by transaction identifier rather than by the
project that triggered recovery, verifies target preimages and desired digests,
and either completes a wholly uncommitted publication or restores committed
targets in exact reverse order. Backups are retained until recovery or rollback
succeeds. No transaction releases the home lock between its first target swap
and durable success or reverse rollback, so recovery cannot overwrite a later
project's successful commit or lose a consumer-ledger update.

Repair uses the same immutable-source validation, context exclusion,
build-source digest, closure, audit and registry gates, fixed toolchain and
process graph, private build, cache publication, and journaled commit sequence
as install. It MUST rebuild a missing, corrupt, wrong-target, wrong-toolchain,
or untrusted compiled entry from a revalidated snapshot into protected state.
It MUST NOT adopt candidate bytes or authenticate them by changing permissions,
recalculating a marker, or accepting a self-consistent receipt.

An upgrade resolves and fetches only the selected scope's direct declarations
and their transitive dependency closure. An operation over several projects
MUST deduplicate fetches of the same checkout. A global-scope upgrade fetches
only the global dependency closure. A separate update operation MAY fetch all
managed source repositories.

The managed `.gitignore` comment is implementation-specific. Conformance
depends on the generated paths being ignored, not on comment spelling.

## 3. Runtime and project environment

Runtime files are machine-local and keyed by skill name and resolved commit.
Context installs under `.agents/skills/<name>/`; command shims install under
`.agents/bin/`. Runtime-only nodes receive a marker-only directory and are not
mirrored into agent adapters.

Runtime roots are copied atomically. An existing commit-keyed entry MAY be
reused only after verifying that every required path exists. Command launchers
MUST be self-contained: executing a portable direct command location MUST NOT
depend on shell activation or a user profile. A launcher prepends the project
or global command directory, directories containing resolved declared system
dependencies, and any implementation runtime directories required by the
command. It preserves the inherited `PATH`, forwards arguments without
reinterpretation, and returns the child command's exit status.

Build roots MUST NOT be copied into the commit-keyed runtime store. A build
command launcher targets the immutable compiled-artifact cache entry selected
by the effective plan and marker, never a source-tree output or the
commit-keyed script runtime entry. Before writing a launcher, the manager MUST
revalidate the referenced protected cache boundary, receipt, and artifact.

On Unix a launcher is either a relative symlink when no environment
augmentation is required or an executable POSIX-shell wrapper. On Windows it
is a `.cmd` wrapper that safely quotes the runtime path, disables delayed
expansion while constructing its environment, forwards all arguments, and
returns the child status. Stale launchers owned by the previous plan are
removed.

`.agents/env.sh` and `.agents/env.ps1` prepend `.agents/bin` to `PATH` and set
the portable `CSK_PROJECT_ROOT` to the resolved project root. They MUST locate
themselves rather than rely on the caller's current directory. A manager MAY
also set tool-specific variables.

Project command availability for agents MUST NOT depend on a user shell
profile. The portable direct command locations are
`<project>/.agents/bin/<command>` on Unix and
`<project>\.agents\bin\<command>.cmd` on Windows. A manager SHOULD warn when
prompt-visible skill instructions infer an installed command from its source
runtime path or omit shell-neutral shim resolution.

A manager SHOULD publish forwarding shims for global commands into a safe,
writable directory that is already on the user `PATH`. It MUST NOT overwrite
an unmanaged entry. When no safe directory exists, it retains the canonical
global shims and warns with the canonical location and optional shell
activation path. Forwarding locations and their ownership records are
machine-local and implementation-specific.

## 4. Install scopes

### 4.1 Project

Project declarations materialize inside the project checkout. Different
projects may install different commits independently.

### 4.2 Global

Global declarations use a machine-local `Skillfile.json`, context store,
runtime shims, and environment files. Their physical location is
implementation-specific. Global adapters mirror to each selected agent's home
discovery directory. Global command precedence is below project shims and above
the pre-activation system `PATH`.

### 4.3 Hybrid

A hybrid manifest extends Skillfile schema 1 with REQUIRED per-skill `targets`.
A target is a project alias, exact resolved path, or path glob. The glob syntax
is `/`-separated and implements only `*`, `?`, and `**`; matching is
case-sensitive and does not depend on the host OS.

Applicable hybrid declarations join the project closure. Precedence is
project, hybrid, global. Project declarations shadow hybrid declarations with a
message. Hybrid-only closure nodes render once in a machine store with the
machine locale and are mirrored into targeted project adapters without writing
skill context into the project checkout.

## 5. Agent adapters

The standard agent identifiers and discovery surfaces are:

| Agent | Project surface | Global surface |
|---|---|---|
| `claude_code` | `.claude/skills` | `~/.claude/skills` |
| `codex_cli` | `.codex/skills` | `~/.codex/skills` |
| `cursor` | `.cursor/rules` | `~/.cursor/rules` |
| `gemini` | `.gemini/skills` | `~/.gemini/skills` |
| `opencode` | native `.agents/skills` | `~/.agents/skills` |
| `windsurf` | native `.agents/skills` | `~/.agents/skills` |

Adapter entries are symlinks, copies, or automatic symlink-with-copy-fallback.
Every root carries the adapter ledger from Protocol Core section 11. Refresh is
atomic per entry. Unknown agent identifiers produce a warning and no output.

## 6. MCP requirements

MCP verification is read-only. A manager MUST NOT launch, install, enable, or
modify an MCP server while checking a skill requirement.

| Agent | Project surface | User surface |
|---|---|---|
| `claude_code` | `.mcp.json` | `~/.claude.json` |
| `cursor` | `.cursor/mcp.json` | `~/.cursor/mcp.json` |
| `codex_cli` | `.codex/config.toml` | `~/.codex/config.toml` |
| `gemini` | `.gemini/settings.json` | `~/.gemini/settings.json` |
| `opencode` | `opencode.json`, `opencode.jsonc` | `~/.config/opencode/opencode.json(c)` |
| `windsurf` | none | `~/.codeium/windsurf/mcp_config.json` |

JSON surfaces use `mcpServers`, Codex TOML uses `mcp_servers`, and OpenCode uses
`mcp`. A disabled entry does not count. Missing or malformed files configure no
servers and produce a warning naming the file.

`required_in: any` succeeds when at least one target agent configures the
server. `all` requires every target. Failures name missing agents and include
the declared hint. Markers record sorted agents where each server was found.

A configured stdio server whose command is absent from `PATH` produces a
warning when every discovered entry is positively stdio. Project-only server
configuration produces a checkout-trust warning.

## 7. Source audit policy

Source audit is a machine-local policy layer. Detectors and analysis backends
may differ; decisions do not.

For each snapshot a manager computes the raw-tree content hash, runs a static
canary, runs deterministic detectors, optionally invokes a configured backend,
and records findings. A canary failure always blocks. Cloud backends receive
only sources classified public by explicit policy; other egress attempts block.
Secret redaction is REQUIRED before permitted cloud egress.

Decisions are `allow`, `warn`, `block`, or `require_pin`:

- local hash or source revocation always blocks;
- strict mode requires an operator pin for pre-capability schemas;
- a verifiable finding at or above `fail_on` blocks in strict mode;
- advisory mode warns;
- backend failure blocks in strict mode and warns in advisory mode;
- `block` and `require_pin` fail installation.

Pins record content hash, operator identity, reason, and creation time. Pins do
not override local or registry revocation.

## 8. Shell activation

Shell activation is an OPTIONAL convenience for interactive users. A manager
MUST NOT require it for agent command execution and MUST NOT modify a user
shell profile without explicit user action.

Shell activation searches upward from the current directory for the nearest
`.agents/env.sh` or `.agents/env.ps1`. Entering or switching projects restores
the saved pre-project `PATH` before sourcing the new environment. Leaving all
projects restores that `PATH` and clears activation state. Nested projects use
the nearest environment.

Upward search MUST guarantee progress toward a filesystem root. A POSIX hook
MUST treat an empty or non-absolute `PWD` as no active project. Before sourcing
a newly selected project environment, a hook MUST establish an activation or
loading guard so directory changes performed by that environment cannot
re-enter the same activation. A POSIX hook running under Git Bash MUST accept
native Windows drive paths for manager configuration and global-environment
lookup.

Bash integrates through `PROMPT_COMMAND`; zsh integrates through `precmd` and
`chpwd`; PowerShell wraps the existing global `prompt` function while
preserving its output and invokes activation before each prompt. Hook
installation also invokes activation once immediately. Re-loading a hook MUST
NOT stack duplicate wrappers or PATH entries.

A CLI MAY cache generated hook code and print the shell-specific command that
sources it. This avoids starting the manager executable from every new shell.

Global activation is OPTIONAL and enabled by default by conforming CLI
profiles. It is sourced once per global environment version and has lower PATH
precedence than a project environment.

## 9. Idempotent machine bootstrap

A manager SHOULD expose a non-interactive operation that creates its machine
configuration only when it is absent. When the configuration path already
exists, this operation MUST succeed without parsing, rewriting, or changing
the existing file. An explicit overwrite operation and create-if-absent mode
MUST be mutually exclusive.

## 10. Status and garbage collection

Read-only status validates marker schema, recomputes content hashes, reports
manifest and activation drift, and MAY re-resolve registry attestations. A
check mode returns non-zero for drift without mutating state.

For a build-enabled marker, status additionally validates static build-root
context exclusion, recomputes `curator-build-source-v1` from the fully validated
raw snapshot, recomputes every build input and logical key, and validates every
referenced receipt and artifact below a currently verified manager-protected
boundary. A missing raw snapshot, context-visible or runtime-copied build-root
file, untrusted boundary, unsupported driver or toolchain, corrupt receipt or
artifact, wrong native target, or source, key, receipt, artifact-path, or
artifact-hash mismatch makes the installation non-current. Status MUST NOT
execute an artifact or mutate, quarantine, repair, or adopt cache state.

Garbage collection acquires only the manager-home mutation lock and first
revalidates every manager-protected cache boundary it will traverse. It scans
registered consumers and valid markers, marks every runtime and snapshot entry
referenced by an existing consumer, any supported valid marker (currently
marker v1 or marker v2), or an in-flight transaction journal, and marks every
logical build-cache entry referenced by a valid marker v2 or in-flight
transaction journal. It sweeps only unreferenced machine-local entries older
than the manager's documented grace period. Receipt content alone is neither
provenance nor a live reference. An unreadable consumer, marker, journal, or
unprovable cache boundary fails safe: uncertain entries are retained or
conservatively quarantined according to documented local policy and the
uncertainty is reported. GC MUST NOT execute or adopt entry content.
