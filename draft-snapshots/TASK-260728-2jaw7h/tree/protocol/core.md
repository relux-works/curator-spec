# Curator Protocol Core 1.0

This document is normative. It defines the portable objects and deterministic
algorithms shared by conforming Curator Protocol managers. Tool-specific state
and user interfaces are defined outside the core.

## 1. Data model and versioning

Protocol JSON MUST be UTF-8 without a byte-order mark. Parsers MUST reject
duplicate object keys, invalid UTF-8, trailing non-whitespace data, and values
that violate the applicable schema under `../schemas/v1/`.

JSON object member order and insignificant whitespace have no meaning unless a
section explicitly defines canonical bytes. Array order is significant unless
the field is declared set-like. Writers MUST emit the current schema version;
readers MUST reject unsupported versions with an upgrade error and MUST NOT
infer a newer schema from its fields.

Schemas define structural validity. The semantic checks in this document are
additional and REQUIRED.

Manifest schemas 1 through 6, the `go-v1` driver, build receipt schema 1,
install marker schemas 1 and 2, conformance claim schemas 1 and 2, and protocol
`1.0.0-rc.4` are frozen compatibility surfaces. Implementations MUST NOT
reinterpret, broaden, relabel, or infer schema-7 behavior from any of them.
External build repositories are introduced only by the separately versioned
schema-7/rc.5 surfaces defined below.

Manifest schema 7, build receipt schema 2, install marker schema 3, conformance
claim schema 3, and `skill-build.json` schema 1 are likewise frozen against the
toolchain requirement contract: it is introduced only by manifest schema 8 and
`skill-build.json` schema 2, and it re-versions nothing else. Every earlier
schema keeps its exact bytes and its exact package surface.

### 1.1 Compatibility identifiers

The filenames `Skillfile.json`, `Skillfile.dev.json`, `agent-skill.json`,
`skill-build.json`, `.csk-install.json`, `.csk-managed.json`, and project root
`.agents/` are portable protocol identifiers. A manager MUST read and write
those exact names. The filename `csk-skill.json` is a reserved legacy alias for
`agent-skill.json`: managers MUST continue to read it throughout protocol 1.x,
but writers MUST emit only `agent-skill.json`. `skill-build.json` is not a
skill-manifest alias; it is valid only as the external-repository descriptor
defined in section 4.2.2, at schema 1 or schema 2.

Machine-home directories, cache names, executable names, global environment
variables, and managed comment text are implementation-specific. A manager
MUST NOT write machine-local state into another manager's home unless the user
explicitly selected that location.

## 2. Portable identifiers and paths

Skill names, command names, MCP server names, agent identifiers, and adapter
ledger entries MUST match:

```text
^[A-Za-z0-9][A-Za-z0-9._-]*$
```

They MUST additionally satisfy the portable filename rules below. Comparison
is case-sensitive even on a case-insensitive filesystem.

A portable relative path:

1. is a non-empty Unicode string encoded as UTF-8;
2. uses `/` separators and contains no `\`, NUL, or control character;
3. is not absolute and has no empty, `.` or `..` component;
4. has no component ending in a space or `.` and no component containing `:`;
5. has no component whose case-insensitive basename before its first `.` is
   `CON`, `PRN`, `AUX`, `NUL`, `COM1` through `COM9`, or `LPT1` through `LPT9`.

Implementations MUST preserve Unicode scalar values exactly and MUST NOT apply
normalization during hashing or comparison. Filesystem extraction MUST detect
two protocol paths that map to one platform path and fail before writing.

## 3. Skill packages

A skill package is a git snapshot or a directory within one. Its root MUST
contain `SKILL.md` with YAML frontmatter containing non-empty `name` and
`description` strings. The frontmatter `name` MUST equal the declared skill
name. `triggers`, when present, is a list of non-empty strings.

An installer MUST NOT execute package-provided code while resolving,
validating, auditing, or installing a skill. Schema 6 and 7 build commands are
the only compilation extensions to this rule: a manager MAY pass validated
untrusted Go source bytes to the closed `go-v1` or `go-repository-v1` driver in
section 4.2, but MUST NOT transfer execution control to a package- or
repository-selected program, argument vector, environment, hook, plugin,
generator, build recipe, signer, or compiled output.

### 3.1 Context selection

Only these root entries are eligible for agent-facing context:

```text
SKILL.md
agents/
references/
.skill_triggers/
assets/
templates/
examples/
data/
```

`scripts/` is additionally eligible only when the package exports no commands.
At every depth the following names or glob patterns MUST be excluded:

```text
.git .github .gitlab-ci.yml .venv __pycache__ *.pyc node_modules
tests test __tests__ README* CHANGELOG* LICENSE* Makefile
setup.py pyproject.toml requirements*.txt .DS_Store .gitignore
```

Directories declared in `runtime_roots` or `build_roots` are excluded as whole
subtrees even if nested under an eligible context root. The `build_roots`
exclusion is computed from the validated manifest before locale rendering,
cache lookup, or any compiler command. It is therefore identical for a real
build, a build-cache hit, and dry-run. Build roots MUST NOT be copied into the
commit-keyed runtime store or any installed context, and generated artifacts
MUST remain outside agent-facing context.

An external build repository is never part of the consuming skill snapshot.
Its descriptor, source, object database, frozen snapshot, build root, and
generated artifact MUST NOT enter agent-facing context or the commit-keyed
runtime store. This exclusion is unconditional and identical for a real build,
cache hit, dry-run, status, and repair.

Selection uses protocol paths, sorts selected files by Unicode scalar value of
their POSIX path, rejects links, and copies regular file bytes without newline
conversion.

### 3.2 Localization

Localization is inactive when no locale is selected. When
`locales/metadata.json` exists it MUST contain an object `locales`; when
`.skill_triggers/` exists it MUST be a directory. A consistent locale has both
`locales[locale]` and `.skill_triggers/<locale>.md`. At least one consistent
locale is REQUIRED when either localization surface exists.

A locale selector is 1 through 64 ASCII letters, digits, or hyphens, starts and
ends with a letter or digit, and is compared case-sensitively without
normalization. Every `locales` member name MUST be a locale selector and its
value MUST be an object. This deliberately uses a safe BCP 47-compatible
surface without attempting language-tag canonicalization.

For a selected consistent locale, a manager replaces only the `description`
and `triggers` values in installed `SKILL.md`, preserving `name` and body. List
items beginning with `- ` outside fenced code blocks form the trigger list.
When present, `agents/openai.yaml` is rendered from `display_name`,
`short_description`, and `default_prompt`. If the selected locale is
unavailable, source context is installed unchanged and a warning lists the
available consistent locales. The warning is emitted even for an otherwise
current installation.

## 4. Skill manifest

`agent-skill.json` is OPTIONAL for a pure context skill and otherwise conforms
to exactly one of `agent-skill-v1.schema.json` through
`agent-skill-v8.schema.json`. The legacy filename `csk-skill.json` has exactly
the same object shape and schema-version semantics through
`csk-skill-v8.schema.json`.

Readers resolve manifests in this order:

1. When only `agent-skill.json` exists, read it.
2. When only `csk-skill.json` exists, read it as a legacy manifest.
3. When both exist, parse and validate both independently. They MUST represent
   equal JSON values: object member order and insignificant whitespace are
   ignored, array order and JSON value types remain significant. If equal,
   `agent-skill.json` is authoritative. If unequal, the reader MUST fail with
   `conflicting_skill_manifests` and MUST NOT install either value.
4. The existence of an invalid modern manifest is an error and MUST NOT fall
   back to the other filename or to `agents/runtime.json`.

| Schema | Added behavior |
|---|---|
| 1 | exported script and system commands |
| 2 | `runtime_roots`, command dependencies, strict top-level fields |
| 3 | REQUIRED capability declaration |
| 4 | transitive skill requirements |
| 5 | MCP server requirements |
| 6 | declarative compiled commands and context-excluded `build_roots` |
| 7 | first-class external build repositories and `go-repository-v1` |
| 8 | REQUIRED toolchain requirement on every build command |

Version gates are downward: a field introduced by a later version MUST be
rejected in an earlier one. Schema 1 preserves its deployed extension behavior;
schemas 2 through 8 reject unknown fields. Schema 1 through 5 MUST reject
`build_roots`, a command with `type: "build"`, and every build-only field.
Schema 1 through 6 MUST reject `build_repositories`, `repository`, `target`,
and `go-repository-v1`. Schema 1 through 7 MUST reject `toolchain`, whether
top-level or on a command. Their script, system, runtime-root, capability,
dependency, context, hash, `go-v1`, receipt-v1, and marker-v1/v2 behavior is
unchanged.

Schema 8 changes exactly one thing: every build command carries a REQUIRED
`toolchain` requirement (section 4.2.3). It re-versions no receipt, marker,
claim, execution policy, or fingerprint algorithm, and it admits no new driver.
Schemas 6 and 7 keep their exact package surface and gain the same two-stage
preflight without gaining a field, because a command that declares no
requirement takes its driver's registry baseline.

### 4.1 Runtime roots and commands

Every runtime root and script command path MUST be a portable relative path
that exists in the snapshot. Runtime roots MUST name directories, be unique,
and be pairwise disjoint. For schema 2 and later, every script command path
MUST fall within one declared runtime root when any roots are declared.

A script command declares at least one of `unix_path` and `win_path`. A system
command declares a non-empty bare executable name and MAY include a hint. A
missing system command fails installation with the hint. The command name is
the shim name and one active name has exactly one owner.

### 4.2 Build roots and the closed `go-v1` command

`build_roots` and local `go-v1` commands exist in manifest schemas 6 and 7.
Schema 7 retains their exact schema-6 meaning so that local and external
commands may coexist. Every local build root MUST be a portable relative path
other than `.`, MUST name a real, link-free directory in the immutable raw
skill snapshot, and MUST be unique and pairwise disjoint. No local build root
may equal, contain, or be contained by a runtime root. Every declared local
build root MUST be referenced by at least one local build command.

A build command has exactly this package-controlled surface:

```json
{"type":"build","driver":"go-v1","source_dir":"build/cmd/tool"}
```

The object MUST contain exactly `type`, `driver`, and `source_dir`; the driver
MUST be the closed identifier `go-v1`. `source_dir` MUST be a real, link-free
directory below exactly one declared build root and MAY equal that root, but
MUST NOT be `.`. The containing build root is the command's `build_root`; it
MUST contain `go.mod` directly, and that file MUST be the nearest ancestor
`go.mod` of `source_dir`. An intervening module is invalid.

The manager MUST derive the artifact-relative path solely from the command
name: `bin/<command>` on Unix and `bin/<command>.exe` on Windows. A package
MUST NOT select a program, arguments, environment, tags, flags, toolchain,
output path, build script, hook, plugin, generator, or post-build action.
Unsupported drivers MUST fail without falling back to a system command or
generic build facility. Build commands participate in existing activation,
dependency-command selection, portable-name collision, shim collision, and
provider-first closure rules exactly like script commands. Within one closure
node, active build command names MUST be processed in Unicode-scalar lexical
order.

`go-v1` builds exactly one native executable from exactly one package named
`main`. The toolchain MUST be Go 1.23 or newer, operator-trusted rather than
package-selected, and from a release family tested by the manager against the
`go-v1` conformance vectors. The module is the declared build root, dependency
resolution is vendor-only and networkless, and workspaces, toolchain switching,
cross-compilation, PGO, cgo, package-controlled assembly, host objects,
generators, tests, plugins, overlays, external linking, and libgcc fallback are
forbidden.

The manager MUST run every source-aware Go command inside the fixed
`manager-worker-v1` process graph defined in section 4.2.1, never through a
shell or a joined command string. The package-independent bootstrap probes below
read no package byte and MAY run directly from the manager parent. Once per
operation the manager MUST use exactly these package-independent argument
vectors from a manager-owned empty directory as the working directory. Neither
the parent nor the worker MAY alter, extend, reorder, or repeat them. The
bootstrap environment MUST start empty except for
indispensable operating-system process variables; use operation-private user,
configuration, cache, and temporary roots; set `GOENV=off` and
`GOTOOLCHAIN=local`, `LC_ALL=C`, and `LANG=C`; and contain no inherited `GOROOT`
or target:

```text
go telemetry off
go version
go env -json GOROOT GOHOSTOS GOHOSTARCH GOOS GOARCH GO386 GOAMD64 GOARM GOARM64 GOMIPS GOMIPS64 GOPPC64 GORISCV64 GOWASM GOTELEMETRY GOTELEMETRYDIR
```

For every active build command, with canonical `source_dir` as the working
directory, it MUST then use exactly:

```text
go list -mod=vendor -deps -json -buildvcs=false -compiler=gc -pgo=off .
go build -mod=vendor -trimpath -buildvcs=false -buildmode=exe -compiler=gc -pgo=off -ldflags=-linkmode=internal -libgcc=none -o <manager-staging-artifact> .
```

Each line above denotes an argument vector; the `-ldflags=...` value is one
argument and the output is the manager-derived staging path. During bootstrap
and command builds, the environment MUST set `GOPATH`, `GOMODCACHE`, `GOCACHE`,
`GOTMPDIR`, `HOME`, `XDG_CONFIG_HOME`, `PATH`, and `TMPDIR` below
operation-private roots, with `PATH` naming a manager-owned empty directory. On
Windows, `APPDATA`, `LOCALAPPDATA`, `USERPROFILE`, `TEMP`, and `TMP` MUST also
be private.

After the bootstrap probes, the environment MUST retain the bootstrap settings
and add the resolved `GOROOT`, native `GOOS`/`GOARCH`, exactly one applicable
trusted tuning variable, and `GO111MODULE=on`, `GOFLAGS=` (empty), `GOPROXY=off`,
`GOSUMDB=off`, `GOPRIVATE=` (empty), `GONOPROXY=none`, `GONOSUMDB=none`,
`GOVCS=*:off`, `GOWORK=off`, `CGO_ENABLED=0`, `GO_EXTLINK_ENABLED=0`,
and `GOEXPERIMENT=` (empty). It MUST verify `GOTELEMETRY == "off"` and that
`GOTELEMETRYDIR` is below the operation-private platform configuration root.
Package or ambient Go, compiler, linker, and executable-search variables MUST
NOT be inherited.

The complete `go list` stream MUST contain exactly one non-`DepOnly` root with
`Name == "main"`, no incomplete result, and no `Error` or `DepsErrors`. Only a
result with both `Standard == true` and `Goroot == true` is a trusted toolchain
package; its directory and every listed input MUST stay below the fingerprinted
`GOROOT`. Every other result and its package directory, module file, active Go
file, and embedded input MUST stay below the command's build root. Every result
MUST have empty `SysoFiles`; every result with `Standard == false` MUST also
have empty `CgoFiles`, `CFiles`, `CXXFiles`, `MFiles`, `HFiles`, `FFiles`,
`SFiles`, `SwigFiles`, and `SwigCXXFiles`. Every active non-standard `GoFiles`
file MUST be a regular file below the build root and MUST NOT contain the exact
ASCII bytes
`//go:cgo_import_dynamic`. Any failure occurs before `go build`.

Below the worker, the manager and the worker MUST start no program other than
the fingerprinted `go` executable, which in turn runs fingerprinted regular
executables below `GOROOT/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/`. This is a
manager-selection and identity rule: the manager selects every program it starts
and verifies each identity before use. Neither the manager nor the worker MAY
write to the frozen source snapshot or to `GOROOT`, and both identities MUST be
re-verified after the last child exits; a change rejects the operation before
publication. Section 4.2.1 states exactly which portable mechanism carries each
of these rules and which stronger kernel-enforced guarantee is deferred. The one
output MUST be a bounded regular file inside manager staging. The manager MUST
hash it, set manager-defined executable permissions, and MUST NOT execute it for
validation, version discovery, smoke testing, post-processing, receipt
generation, rollback, or any other reason.

#### 4.2.1 Portable `manager-worker-v1` execution policy

Every source-aware `go-v1` and `go-repository-v1` operation runs under exactly
one named execution policy. Protocol 1.0 defines exactly one, the portable
`manager-worker-v1` policy, and every conforming manager MUST implement it on
macOS and Windows. The policy identity is a normative cache, receipt, marker,
and claim input. It is never a package-visible option, a host label, or an
operator preference.

The fixed process graph is:

```text
manager parent
  -> identity-verified manager-owned worker
       -> fingerprinted <GOROOT>/bin/go
            -> fingerprinted regular executables below
               <GOROOT>/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/
```

The worker is an exact re-execution of the installed manager executable in one
fixed hidden mode. It is an implementation boundary, not a user-visible command
surface and not a package-selected program. No package file, manifest value,
descriptor value, environment value, `PATH` lookup, shell, or user option
selects the worker executable or its mode. An implementation that cannot
distribute an equivalent identity-verified worker MUST state the exact
executable graph it verifies instead and MUST treat every mutable component of
that graph, including an interpreter and an installed package tree, as trusted
computing base.

One worker session performs exactly one `go list`, waits while the parent
validates the complete package graph, accepts exactly one authenticated build
permit, and performs exactly one `go build`. The session state machine admits
no retry, second list, second build, additional executable, shell, VCS, module
download, generator, test, run, or tool request; any other message tears the
session down without starting a compiler.

The following controls are mandatory on every supported host, and they are the
only controls whose absence rejects an operation:

- the fixed offline vendored-Go behavior, argument vectors, environment, and
  canonical working directories defined above;
- a fixed manager-selected process graph: within this execution boundary the
  manager and the worker start only the four nodes above and no other program;
- operation-private user, configuration, cache, temporary, staging, and output
  roots resolved independently of package data;
- a frozen source snapshot that neither the manager nor the worker writes to;
- a manager-derived artifact path, a bounded wall-clock deadline over the whole
  worker domain, bounded and redacted combined output, and one bounded regular
  artifact;
- closed standard input and release of unrelated descriptors or handles before
  Go starts;
- worker executable identity verification before launch, an in-session identity
  proof bound to a fresh session nonce, and re-verification of the worker,
  source-snapshot, and fingerprinted toolchain identities after the last child
  exits and before publication;
- termination and joining of the complete worker domain before the operation
  returns;
- application of every native control that the rc.5 native-control inventory
  below marks available for the host platform; and
- exactly one closed `capability-evidence-v1` record per operation.

A manager that cannot apply all of them MUST reject the build with
`build_execution_control_unavailable` before starting the worker or Go.

Each mandatory control is a manager-enforced mechanism, not a kernel-enforced
guarantee. This specification states both sides so that neither a reader nor an
implementation can mistake one for the other:

| Portable mechanism | What it means | What it does not mean | Deferred guarantee |
|---|---|---|---|
| `network: "none"` in the canonical policy | fixed offline Go module, proxy, checksum-database, and version-control configuration, and no manager-initiated or Go-initiated network access for dependency resolution or the build | kernel-enforced network denial for the worker domain or its descendants | `total-network-denial` |
| frozen snapshot plus identity re-verification | the manager freezes the validated snapshot, neither the manager nor the worker writes to it or to `GOROOT`, and a change to either before publication rejects the operation | kernel-enforced read-only presentation of the snapshot or toolchain to descendants | `read-only-source-and-toolchain` |
| fixed manager-selected graph plus identity verification | within this execution boundary the manager and worker start only the fixed four-node graph, package data cannot select or add a program, and every started program's identity is verified before and after execution | kernel-enforced allowlisting of the exact executable paths a descendant may run | `exact-executable-allowlisting` |
| manager-private roots plus artifact verification | every manager-directed write target is an operation-private root and the single artifact is verified in private staging before publication | kernel-enforced confinement of every descendant write to the private build roots | `private-build-root-only-writes` |
| parent-enforced deadline, output, and artifact bounds | the parent bounds wall-clock time, combined output, and artifact size over the worker domain and applies every available inventory control | hard aggregate process, memory, disk, time, and output bounds over every descendant | `hard-aggregate-descendant-resource-bounds` |
| mandatory-control preflight | the operation rejects before the worker when a mandatory portable control cannot be applied | terminal rejection before the worker when a hardened capability is absent | `fail-closed-capability-preflight` |

The rc.5 native-control inventory is exhaustive and normative per platform. Its
authority is the `native_control_inventory` section of
`conformance/v1/vectors/go-host-execution-policy.json`, version
`rc5-native-control-inventory-v1`:

| Control | macOS | Windows |
|---|---|---|
| `descendant-domain-termination` | available: process group and session teardown | available: Job Object kill-on-close |
| `active-process-count-limit` | unavailable: `no-private-aggregate-domain` | available: Job Object active-process limit |
| `aggregate-memory-limit` | unavailable: `no-private-aggregate-domain` | available: Job Object process and job memory limit |
| `per-file-size-limit` | available: `RLIMIT_FSIZE` | unavailable: `no-private-aggregate-domain` |
| `inherited-handle-restriction` | available: close-on-exec plus explicit descriptor release | available: explicit handle inheritance list |

A manager MUST apply exactly the controls the inventory marks available for its
platform, MUST NOT apply or report a control outside the inventory, and MUST NOT
substitute a host label for the availability probe. Availability MUST be probed
once per operation before worker launch; a cached, inherited, or configured
result is not a probe. Adding, removing, or re-scoping an entry requires a new
inventory version. That is a specification revision, not an execution-policy
revision, because inventory membership never enters a build input, an artifact,
or any hashed identity.

Host capability evidence is exactly one closed `capability-evidence-v1` record
per operation. The record contains exactly `record_version`, `execution_policy`,
`platform`, and `controls`. `platform` is `macos` or `windows`. `controls`
contains exactly one entry per inventory control, and each entry contains
exactly `name`, `availability`, `status`, and `probed_at`. `availability` is
`available` or `unavailable`, `status` is `applied` or `unavailable`, and
`probed_at` is `pre-worker-launch`.

Each condition below is an error, not a permitted variation:

| Condition | Diagnostic |
|---|---|
| an `available` control reported with a status other than `applied` | `build_execution_capability_evidence_invalid` |
| an `unavailable` control reported with a status other than `unavailable` | `build_execution_capability_evidence_invalid` |
| a missing, duplicated, or extra control entry | `build_execution_capability_evidence_invalid` |
| an unknown `record_version` | `build_execution_capability_evidence_invalid` |
| availability not probed once per operation before worker launch | `build_execution_capability_evidence_invalid` |
| a deferred hardened guarantee named as a control entry | `build_execution_hardened_claim_forbidden` |
| an `execution_policy` other than `manager-worker-v1` | `build_execution_hardened_claim_forbidden` |

The record is result-only. It is exposed in install, dry-run plan, and status
results, and it MUST NOT appear in a cache key, receipt input, marker record, or
claim, because portable cache identity is defined by the mandatory controls that
every conforming host applies.

The portable policy does not provide, and a conforming implementation MUST NOT
claim, these hardened guarantees: `total-network-denial`;
`read-only-source-and-toolchain`; `private-build-root-only-writes`;
`hard-aggregate-descendant-resource-bounds`; `exact-executable-allowlisting`;
and `fail-closed-capability-preflight`. They are specified separately by the
hardened execution profile tracked as `STORY-260728-327soo`. None of the six
names may appear in the mandatory-control set, the native-control inventory, or
a capability-evidence record.

There is exactly one portable failure boundary. A mandatory portable control
that cannot be applied rejects the operation with
`build_execution_control_unavailable` before the worker starts and publishes
nothing. An unavailable inventory native control, and the absence of any of the
six deferred hardened guarantees, MUST NOT reject a portable build, MUST NOT
produce a diagnostic, and MUST NOT prevent publication; a portable operation
MUST NOT record any of them as applied.

Package-controlled bytes remain compiler input only. They MUST NOT select or
modify the manager or worker executable, hidden mode, or identity; the Go or
tool executable paths; any argument vector, environment value, working
directory, build tag, or flag; the applied controls, limits, or permitted roots;
the worker protocol messages or the parent's build permit; the graph-validation
result, artifact verifier, cache key, receipt, marker, or claim; or any hook,
plugin, generator, post-build action, or publication step. Generator comments
and PGO paths remain inert input and MUST NOT cause a command to run.

A different execution contract requires a different execution-policy identity.
Because the identity is part of the canonical build input, a portable entry, a
pre-revision candidate entry, and a future hardened entry produce different
logical cache keys and cannot alias.

#### 4.2.2 Schema-7 external repositories and `go-repository-v1`

Manifest schema 7 MAY contain a strict top-level `build_repositories` map keyed
by portable identifiers. Each declaration MUST contain exactly `git` and
`locked_commit` and MAY contain `tag`. Every declaration MUST be selected by at
least one active or inactive command in the same manifest.

`locked_commit` MUST contain exactly `object_format` and `hex`.
`object_format` MUST be `sha1` or `sha256`; `hex` MUST be the complete lowercase
commit object ID for that format, respectively 40 or 64 hexadecimal
characters. A declaration MUST NOT use a branch, range, abbreviated ID,
`HEAD`, revision expression, or package-selected local path. When present,
`tag` MUST satisfy section 6.3 and is an assertion in addition to, not instead
of, the immutable full commit lock.

A schema-7 external build command has exactly this package-controlled surface:

```json
{
  "type": "build",
  "driver": "go-repository-v1",
  "repository": "golden-tools",
  "target": "golden-tool"
}
```

The command MUST select exactly one declared repository and exactly one target
from the effective commit's root `skill-build.json`. The command and
descriptor target drivers MUST both equal `go-repository-v1`. An unknown or
mismatched driver MUST fail before artifact-cache lookup or compiler execution
and MUST NOT fall back to `go-v1`, a script, a system command, or a generic
build facility.

The descriptor filename and location are fixed and manager-neutral:
`skill-build.json` at the repository root, and nothing else. A manager MUST NOT
read, accept, or search for a descriptor under any other filename, in any other
directory, or under an implementation-specific name, and MUST NOT treat any
such file as an alias for the descriptor.

`skill-build.json` schema 1 is strict and contains exactly
`schema_version: 1` and a non-empty `targets` map keyed by portable identifiers.
Each `go-repository-v1` target MUST contain exactly `driver`, `build_root`, and
`source_dir`.

Schema 2 changes exactly one thing and adds no other member: a target MAY
additionally carry the OPTIONAL `toolchain` requirement of section 4.2.3. The
repository owns the descriptor version. A manager reads schema 1 and schema 2
and MUST NOT fall back between them: an unknown descriptor version fails
`build_descriptor_schema_unsupported`, and a target naming a driver the
descriptor version does not admit fails `build_descriptor_driver_unsupported`. A
schema-1 descriptor declares no requirement, so its target contributes nothing
to the intersection and the consuming manifest requirement alone narrows the
baseline. These paths are relative to the repository root. The single
value `.` MAY identify the repository root; every other value MUST be a
portable relative path. `source_dir` MUST equal or be below `build_root`.
`build_root` MUST contain `go.mod` directly, and that file MUST be the nearest
ancestor `go.mod` of `source_dir`.

Targets MAY share one build root. A nested module is admitted only when the
selected target names its root and satisfies the nearest-module rule. Managers
MUST NOT discover modules, targets, commands, or outputs. Every non-standard
module, package, source, embed, and vendor input selected by the fixed
`go list` graph MUST remain below the selected build root. Input MUST NOT come
from the consuming skill, another external repository, a sibling or parent
module, a host module cache, a workspace, or the network.

The whole external snapshot is validated, hashed, and audited. Only the
selected build root is compiler-visible, and no external repository byte is
agent-facing or runtime-copied. Allowing `build_root: "."` here MUST NOT change
the schema-6 prohibition on a local `build_root` equal to `.`.

The consuming manifest command key is the sole executable name. The manager
MUST derive `bin/<command>` on Unix or `bin/<command>.exe` on Windows and MUST
derive private staging and shim paths independently of package data. Neither
the command nor descriptor MAY select a program, argv, environment, flag,
compiler tag, toolchain executable, output name or path, install destination,
alias, PATH edit, signing identity, credential, hook, plugin, generator, build
recipe, post-build action, fallback, or secondary artifact. The schema-8 and
descriptor schema-2 `toolchain` requirement is not an exception: it is a version
constraint over a manager-trusted set and never a selector (section 4.2.3.4).

`go-repository-v1` reuses the exact `go-v1` trusted toolchain identity, native
target, process vectors, environment, `manager-worker-v1` execution policy,
two-stage toolchain preflight, vendor-only dependency checks, compiler directive and native-input rejection,
internal-link policy, staging rules, resource controls, and
no-artifact-execution rule. It MUST NOT reinterpret or widen any of those rules. Its external acquisition, audit subject, receipt
schema, and marker state are distinct as defined in sections 6, 9, and 10.

#### 4.2.3 Toolchain requirements and two-stage preflight

Every compiled build command declares which toolchain it needs and which
versions of it are acceptable. Nothing a package declares can select *where* a
toolchain comes from. The extended rationale, the upstream grammar analysis, and
the full vector inventory are in
[`docs/compiled-build-toolchain-requirements.md`](../docs/compiled-build-toolchain-requirements.md);
the rules below are normative.

##### 4.2.3.1 The toolchain registry

The manager owns an exhaustive, versioned `toolchain-registry-v1` document. It
is the only mapping from a driver to a toolchain, and it MUST NOT be derived
from a driver name, a language name, a file extension, or package data. The
closed toolchain identifiers are `go`, `rust`, `swift`, `kotlin`, and `jdk`.
`jdk` is companion-only: a package MUST NOT name it, which is why the wire
identifier set omits it.

A **complete** entry declares exactly `toolchain_id`, `status`, `drivers`,
`companions`, `platforms`, `primary_relpath`, `probe`, `normalization`,
`fingerprint_algorithm`, `baseline`, `compatibility`, and `metadata_sources`. A
**reserved** entry declares only its identifier, its owning task, and OPTIONAL
companions and expected metadata sources; reservation is not admission, and a
reserved identifier is not a supported toolchain.

`primary_relpath` and `probe` are declared per operating system. An entry is
well-formed only when both are declared for every operating system in its
`platforms` set, and neither is declared outside it. Neither has a default. A
relpath or probe declared outside that set is unreachable and MUST fail the
release gate, and a missing one MUST fail it too. That totality obligation is
what makes the Stage A host-pair check of section 4.2.3.5 total.

`normalization` MUST be anchored, MUST match at most one candidate in bounded
output, MUST be locale-independent, and MUST NOT guess. Ambiguous or unmatched
output is `build_toolchain_version_undetermined`, never a default.

`compatibility` is a closed set of release families the manager has tested
against that driver's conformance vectors. It is a manager policy value and
never wire data. A resolved release is admitted only when its family is an exact
member; a family merely ordered after a member is not a member. A manager MAY
add a family only after testing it against the driver's vectors, and MUST NOT
derive membership from version ordering, from the effective requirement, from
probe output, or from any package or repository byte. Conformance vectors
declare the set as fixture input, so a vector outcome is deterministic across
managers.

The `go` entry declares `bin/go` (`bin/go.exe` on Windows), the section 4.2
bootstrap probe vectors, field 2 of normalized `go version` output under
`^go(\d+)\.(\d+)(?:\.(\d+))?(.*)$` with an absent patch of `0` and a non-empty
trailing remainder marking a prerelease, `curator-go-toolchain-v1`, the baseline
`at_least 1.23.0`, the family set `{(1, 23)}` at `(major, minor)` granularity,
the six `(linux|macos|windows, amd64|arm64)` pairs, and the `go` and `toolchain`
directives of `go.mod`. It adds no process invocation and no argument-vector
form: the five Go argument vectors of section 4.2 remain exactly five.

##### 4.2.3.2 The requirement object

A canonical version is `major.minor.patch` matching
`^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$` with each component at
most `999999`. No `v`, `go`, or `swift-` prefix, no prerelease, no build
metadata, no leading zeros, no wildcard. Order is lexicographic over the triple.

`toolchain` contains exactly `id` and `version`. `version` contains exactly
`kind` plus that kind's own fields:

```json
{"id": "go", "version": {"kind": "at_least", "min": "1.23.0"}}
{"id": "go", "version": {"kind": "range", "min": "1.23.0", "below": "1.25.0"}}
{"id": "go", "version": {"kind": "exact", "equals": "1.23.4"}}
```

`id` MUST equal the driver's registry primary toolchain. For `range`, `min`
MUST be strictly below `below`. Neither rule is expressible as a schema keyword,
so both are `build_toolchain_requirement_invalid` at validation, with the
violation tokens `id_not_primary` and `range_bounds_not_ordered`.

Placement:

- manifest schema 8, local build command: `toolchain` is REQUIRED alongside
  `type`, `driver`, `source_dir`;
- manifest schema 8, external build command: `toolchain` is REQUIRED alongside
  `type`, `driver`, `repository`, `target`;
- `skill-build.json` schema 2 target: `toolchain` is OPTIONAL;
- manifest schemas 6 and 7 and descriptor schema 1: no field. They MUST reject
  one, and they take the driver's registry baseline instead.

Intervals are `[V, V]` for `exact`, `[V, +inf)` for `at_least`, and `[V, W)` for
`range`. The effective requirement is the registry baseline intersected with the
manifest requirement and the descriptor requirement, over the sources present.
Intersection takes the maximum lower bound, always inclusive, and the minimum
upper bound, preferring exclusive on a tie. It is associative and commutative,
so source order is irrelevant. An empty intersection is
`build_toolchain_requirement_unsatisfiable` and MUST be detected without probing
the host, so it fails identically on every machine.

A resolved version satisfies the effective requirement when it is not a
prerelease and lies inside the interval. Satisfying it is necessary and not
sufficient: `compatibility` is a separate gate that no intersection participates
in, and a requirement can neither widen nor narrow it.

A prerelease host toolchain satisfies nothing:
`build_toolchain_prerelease_unsupported`. A requirement literal can never
express one.

##### 4.2.3.3 Trusted resolution

The manager looks for a toolchain root in exactly two declaration channels and
in no other place: `operator_config`, entries in manager-owned owner-protected
configuration state, and `bundled`, the roots shipped inside the manager
distribution. `operator_config` precedes `bundled`, and exactly one entry is
selected for an identifier.

Forbidden origins, exhaustively: the ambient or user `PATH`; any package or
repository byte; a runtime root; a project directory including `.agents/bin`;
any shim or wrapper; a manifest or descriptor value; an inherited environment
variable, including `GOROOT`, `RUSTUP_HOME`, `CARGO_HOME`, `RUSTC`,
`SWIFT_EXEC`, `TOOLCHAINS`, `JAVA_HOME`, `KOTLIN_HOME`, and `PATH`; and any
version-manager shim or wrapper, including `rustup`, `asdf`, `mise`, `sdkman`,
`swiftly`, and `jenv`. An operator MAY configure the concrete root a version
manager produced; the manager resolves that root directly and never through the
shim. `PATH` is not a channel, so a toolchain reachable only through it is not
declared at all and its presence on the host cannot change any outcome.

The primary executable MUST be a regular executable file at the entry's
`primary_relpath` inside the tree being fingerprinted, never a wrapper and never
outside that tree. Resolved identity is exactly
`{algorithm, version, primary_relpath, content_sha256}`. Location is not
portable identity. Fingerprinting proves stability across an operation and
identity across operations; it does not prove upstream authenticity, and this
version verifies no toolchain signature. A `content_sha256` in a receipt MUST
NOT be read as provenance.

##### 4.2.3.4 Two package surfaces

Package and repository data reach the manager on two surfaces and the exclusion
rule reads differently on each.

**The manager-defined wire surface** is the manifest build command and the
`skill-build.json` descriptor target. Curator owns these field sets and they are
closed. No field naming an executable path, toolchain root, download URL,
mirror, channel or track, distribution version manager, install or
package-manager command, environment override, `PATH` edit, credential,
keyring, checksum, or trust root exists on this surface, and no schema version
may add one. That constraint is an authoring obligation on this specification
rather than a runtime code, and the release gate enforces it by enumerating the
published build-command and descriptor-target property names.

Two rejections apply here and are partitioned by *what* fails, never by what a
value looks like. A key outside the closed field set is the existing schema
rejection of section 4 and carries no `build_toolchain_*` code. A value in a
field of the closed set that does not match that field's closed grammar —
including a `version` literal carrying a path, prefix, URL, mirror, track, or
command — is `build_toolchain_requirement_invalid`.
`build_toolchain_package_influence_forbidden` therefore never fires on the wire
surface: deciding that a malformed literal is smuggled influence rather than
merely malformed would require inferring intent from a byte string, and two
conforming managers would infer differently.

**Source-ecosystem metadata** is the files the source ecosystem owns, read at
Stage B. Curator does not own those field sets, so each registry entry declares
a closed disposition table assigning every field it reads exactly one
disposition: `forbidden` when the value is a resolution input — an executable
path, toolchain root, URL, mirror, registry, credential, install command,
environment override, or trust root — `compared` when it is a version-domain
assertion about the already-resolved toolchain, and `ignored` otherwise. A field
absent from the table is `ignored`. A channel- or track-valued field on this
surface is `compared`, never `forbidden`, precisely because Curator refuses to
honor it.

Within Stage B for one build command the manager MUST evaluate every
`forbidden`-disposition field first, then every `compared` field, each group in
Unicode-scalar lexical order of relative source path and then of field path. The
first failure is the reported diagnostic.

A field whose value space spans dispositions declares a **value classifier**
instead: an ordered, exhaustive list of classes, each carrying exactly one
disposition and one outcome. Classes are matched in declaration order and the
first match wins. Every classifier MUST end with a catch-all class, so
classification is total. `forbidden` classes MUST be declared before `compared`
and `ignored` classes. At most one class matches the field being absent, and it
is declared first; it classifies no value, so it does not participate in that
precedence. A classifier MUST consult nothing but the field's own value and the
already-resolved toolchain version.

##### 4.2.3.5 Stage A — platform, availability, version

Stage A runs immediately after manifest parsing and build-command validation,
for every distinct toolchain in the plan, in Unicode-scalar lexical order of
toolchain identifier, once per operation, memoized only in operation-private
state. For each toolchain, in this order, first failure reported:

1. compute the effective requirement from the registry baseline, the manifest,
   and any descriptor source readable at this point, rejecting an empty
   intersection;
2. verify the host `(operating_system, architecture)` pair is in the entry's
   `platforms` set; otherwise `build_toolchain_platform_unsupported` with
   `check` `host_pair`. This step reads only manager-owned registry data and the
   host pair: no declaration, no filesystem, no probe, no package byte;
3. resolve and verify the toolchain root in three ordered sub-steps whose inputs
   are disjoint:
   - **3a, declaration presence.** Look up the identifier in `operator_config`
     and then `bundled` and select the first entry found. This test reads
     presence and nothing else. If neither channel carries an entry,
     `build_toolchain_unavailable`. This sub-step is the only producer of that
     code, and it produces no other;
   - **3b, origin admissibility.** Classify the entry — its value together with
     the state holding it. A value that names or defers to a forbidden origin
     rather than a concrete root, or an `operator_config` state that is not
     owner-protected, is `build_toolchain_untrusted` with `substep` `origin` and
     the matched `origin_class`. This sub-step reads no filesystem object;
   - **3c, shape.** Classify the filesystem object the entry denotes. A declared
     root that does not exist, an absent, non-regular or non-executable
     `primary_relpath`, one that resolves outside the fingerprinted tree, or one
     that is on disk a wrapper or version-manager shim, is
     `build_toolchain_untrusted` with `substep` `shape`;
4. run the entry probe from a manager-owned empty working directory under the
   operation-private environment;
5. normalize to the canonical triple and reject a prerelease;
6. verify the toolchain's own reported host target equals the manager's native
   target; cross-compilation stays forbidden and a difference is
   `build_toolchain_platform_unsupported` with `check` `native_target`;
7. evaluate the effective requirement;
8. evaluate the entry's `compatibility` set.

A declared-but-broken root is always `build_toolchain_untrusted`, including when
the declared root directory does not exist at all; routing it to `unavailable`
would make the reported code depend on how far the manager happened to get. A
host that has the toolchain installed and on `PATH` with no entry in either
channel is `build_toolchain_unavailable` from 3a, not `untrusted`.

Stage A MUST complete before external repository acquisition, before build-cache
lookup, and before any persistent mutation. It reads no package byte beyond the
already-validated manifest. Tree fingerprinting MAY stay in the later phase for
cost, but MUST cover the same resolved root, and the version bound into the
fingerprint MUST equal the version Stage A normalized; a difference is
`build_toolchain_changed`. Failure of any toolchain in the plan fails the
operation.

A descriptor requirement is not readable at Stage A for an external command,
because the descriptor arrives with the repository. Stage A therefore gates on
baseline ∩ manifest, and the descriptor requirement joins at Stage B. This is
the only ordering asymmetry, and the consuming manifest requirement is REQUIRED
precisely so the cheap gate always has something to evaluate. Stage A's other
verdicts — the host pair, the declaration, the probe, the normalized version,
the native target, and `compatibility` — are final, because no descriptor byte
can reach the data they are decided from.

##### 4.2.3.6 Stage B — source-metadata cross-check

Stage B runs per active build command after local snapshot validation, or after
exact external acquisition and audit, and before the manager reads an
artifact-cache candidate or starts a compiler child. Its steps are ordered and
the first failure is the reported diagnostic:

1. **re-compute the effective requirement**, now including the descriptor
   requirement. An empty intersection is
   `build_toolchain_requirement_unsatisfiable`;
2. **re-evaluate the resolved version** — the one Stage A normalized, unchanged
   — against that interval. A version outside it is
   `build_toolchain_incompatible`;
3. **file-shape gate** over each `metadata_sources` file present in the
   validated tree. A file the ecosystem's own grammar rejects, including a
   directive or key the ecosystem permits at most once appearing more than once,
   is `build_toolchain_metadata_mismatch` with `assertion` `unclassifiable`.
   Files are evaluated in Unicode-scalar lexical order of relative source path;
4. every `forbidden` disposition and `forbidden` value class;
5. every `compared` disposition and `compared` value class.

Steps 1 and 2 are what make the descriptor asymmetry safe: without step 2 a
descriptor could narrow the interval to a non-empty range excluding the
already-resolved host and nothing would reject it. The file-shape gate precedes
steps 4 and 5 by necessity — a field that cannot be extracted cannot be
classified. `compatibility` is deliberately not re-evaluated at Stage B. The
descriptor's own requirement is validated inside the acquisition audit, before
Stage B, so a malformed descriptor requirement is
`build_toolchain_requirement_invalid` at validation.

##### 4.2.3.7 Go metadata classifiers

The Go command accepts a directive value through two independent layers, and
upstream acceptance in a position is their conjunction. Writing `INT` for
`(0|[1-9][0-9]*)`:

| Grammar | Layer and position | Definition |
|---|---|---|
| `goModVersionShape` | shape, whole `go` directive value | `^([1-9][0-9]*)\.(0\|[1-9][0-9]*)(\.(0\|[1-9][0-9]*))?([a-z]+[0-9]+)?$` |
| `goToolchainNameShape` | shape, whole `toolchain` directive value | `^default$\|^go1($\|\.)` |
| `goSemanticVersion` | semantic, a version wherever upstream represents one | `^INT(\.INT(\.INT\|[a-z]+(INT)?)?)?$` |

The `go` directive admits `goModVersionShape` ∧ `goSemanticVersion`. The
`toolchain` directive admits `goToolchainNameShape` ∧ (`default` ∨ version part
∈ `goSemanticVersion`), where the version part is the maximal prefix, after a
leading `go`, containing no `-`, space, or tab. The two shape and semantic
layers are incomparable in both directions, so neither alone is the contract: a
patch plus a prerelease suffix matches the shape layer and is unrepresentable,
and a bare major is representable and outside the `go` directive's shape.

An admitted value yields a **base triple** with absent components `0` and a
prerelease flag from the trailing `[a-z]+` group. Comparison against the
resolved toolchain uses the base triple only. This is exact rather than
approximate: the two canonicalizations can differ from Go's own order only for a
comparand strictly between a bare language version and its own release, and
every such value is a prerelease, which Stage A step 5 already rejected.

`go.mod` `go` directive, ordered, first match wins, total:

| # | Class | Match | Disposition | Outcome |
|---|---|---|---|---|
| 1 | absent | the directive is not present | — | no assertion; permitted |
| 2 | release literal | both layers, no prerelease group | `compared` | base triple above resolved → `build_toolchain_metadata_mismatch`; at or below → permitted |
| 3 | prerelease literal | both layers, with a prerelease group | `compared` | same base-triple comparison as class 2 |
| 4 | unclassifiable | anything else | `compared` | `build_toolchain_metadata_mismatch`, `assertion` `unclassifiable` |

The `go` directive has no `forbidden` class: its Go-defined value space is a
version and nothing else, so a value carrying a path separator is class 4 and
never package influence. A future release such as `go 1.99.0` is class 2 and
fails on the comparison in that class's own outcome, carrying a derived
canonical assertion rather than the `unclassifiable` token.

`go.mod` `toolchain` directive, ordered, first match wins, total:

| # | Class | Match | Disposition | Outcome |
|---|---|---|---|---|
| 1 | absent | the directive is not present | — | no assertion; permitted |
| 2 | path-bearing name | the value contains `/` or `\` | `forbidden` | `build_toolchain_package_influence_forbidden` |
| 3 | custom-distribution name | `goToolchainNameShape` with a non-empty suffix | `forbidden` | `build_toolchain_package_influence_forbidden` |
| 4 | `default` | the value is exactly `default` | `compared` | permitted and never honored |
| 5 | release name | `goToolchainNameShape` and a version part in `goSemanticVersion` with no prerelease group | `compared` | base triple above resolved → `build_toolchain_metadata_mismatch`; at or below → permitted and never honored |
| 6 | prerelease name | as class 5, with a prerelease group | `compared` | same base-triple comparison as class 5 |
| 7 | unclassifiable | anything else | `compared` | `build_toolchain_metadata_mismatch`, `assertion` `unclassifiable` |

`toolchain default` is permitted and never honored, because it asserts exactly
what Curator unconditionally does. A custom-distribution suffix names a specific
vendor build — *where* the toolchain comes from — which is what `forbidden` is
reserved for, so classes 2 and 3 precede 4 through 7 and a value whose version
part would compare cleanly is still refused. `toolchain go1` is class 5 and
compares as `(1, 0, 0)`, because upstream reads it that way.

A repeated `go` or `toolchain` directive is not a classifier case at all: it is a
file-shape defect that yields no value to classify, and it is
`build_toolchain_metadata_mismatch` from the Stage B file-shape gate. The `go`
entry's metadata sources are exactly these two directives. A `go.work` file is
deliberately not a metadata source, because section 4.2 already fixes
`GOWORK=off` and a workspace file is therefore inert.

Curator's alignment with the Go command is two properties rather than one
equality. **P1, no widening:** every value Curator compares is one the Go
command admits in that position. **P2, no narrowing outside the security
partition:** every value the Go command admits and that Curator does not
classify as package influence is compared. Set equality is unsatisfiable and
deliberately so, because upstream accepts custom-distribution names that class 3
refuses.

##### 4.2.3.8 Cache, dry-run, and status

Neither stage may be skipped by a cache hit, a dry run, or an offline mode. A
cache hit is reachable only after both stages pass, so no hit can bypass the
effective requirement or the `compatibility` gate. A toolchain that fails Stage A
fails the operation there: cache lookup is never reached, no candidate is
consulted, nothing is rebuilt, and no mutation occurs. A toolchain that passes
Stage A and fails Stage B fails there, still before the first cache candidate is
read and before any compiler child starts. A toolchain that passes both stages
while a cache candidate was built under a different toolchain identity is a
plain cache miss, because the resolved identity is part of the cache key. There
is no "cache hit with an incompatible toolchain" path to rebuild from.

Dry run runs both stages, reports an affected command as `blocked` with the
typed diagnostic, returns failure, and leaves no mutation. `unsupported`
continues to mean an unknown driver and MUST NOT be reused for a toolchain
failure. Read-only status and audit report a Stage A or Stage B failure as a
finding and MUST NOT mark an otherwise valid marker non-current because of it.
Install, upgrade, repair, and coverage-claiming audit fail before mutation.

The effective requirement, the `compatibility` set, and the guidance catalog are
gates rather than build inputs: none of them enters a cache key, receipt,
marker, or claim, so changing one never invalidates an artifact. The resolved
toolchain identity does, exactly as it already did for `go-v1`.

##### 4.2.3.9 Diagnostics

Twelve codes, each with named firing sites:

| Code | Firing site | Trigger |
|---|---|---|
| `build_toolchain_requirement_invalid` | validation | malformed object, unknown identifier, identifier not the driver's primary, a value outside its field's closed grammar, prerelease literal, `min` not below `below` |
| `build_toolchain_requirement_unsatisfiable` | validation; B step 1 | empty intersection, before and after the descriptor requirement joins |
| `build_toolchain_unavailable` | A step 3a | no entry for the identifier in either declaration channel |
| `build_toolchain_untrusted` | A step 3b; A step 3c | the entry's value or holding state is inadmissible; the root or primary it names is missing, non-regular, non-executable, a wrapper or shim, or outside the fingerprinted tree |
| `build_toolchain_version_undetermined` | A step 4 | probe output unbounded, unmatched, or ambiguous |
| `build_toolchain_prerelease_unsupported` | A step 5 | resolved toolchain is a prerelease, nightly, beta, or development snapshot |
| `build_toolchain_platform_unsupported` | A step 2; A step 6 | host pair outside `platforms`; reported host target differs from the native target |
| `build_toolchain_incompatible` | A step 7; B step 2 | resolved release outside the effective requirement of that stage |
| `build_toolchain_untested_release` | A step 8 | resolved release family outside the entry's `compatibility` set |
| `build_toolchain_metadata_mismatch` | B step 3; B step 5 | a metadata file the ecosystem's grammar rejects; a `compared` field or value class incompatible with the resolved toolchain, or unclassifiable |
| `build_toolchain_package_influence_forbidden` | B step 4 | a `forbidden` metadata field or value class |
| `build_toolchain_changed` | A; publication | resolved identity or version changed during the operation |

A code MUST NOT carry prose guidance or a URL of its own; it carries a
`guidance_id`.

The payload is a discriminated union keyed by the firing site, defined by
[`toolchain-diagnostic-v1.schema.json`](../schemas/v1/toolchain-diagnostic-v1.schema.json):
a payload carries exactly the values established at the site where it fires, and
because every stage's steps are totally ordered, the established set is a
function of the site. Nothing is optional by judgment and there are no
sentinels. A firing site is `(code, stage, discriminant)`, where `stage` is one
of `validation`, `A`, `B`, `publication`, and exactly two codes declare a
discriminant: `untrusted` declares `substep`, `platform_unsupported` declares
`check`.

`code`, `stage`, `driver`, `toolchain_id`, and `guidance_id` are REQUIRED in
every payload. `effective_requirement` is present exactly when its own stage's
interval computation completed before the site; `resolved_version` and
`prerelease` exactly when Stage A normalization did. `source_ref` is
`{surface, location}` with `surface` one of `manifest`, `descriptor`,
`registry`, or `source_metadata`, and appears only in `requirement_invalid`,
`metadata_mismatch`, `package_influence_forbidden`, and once inside each element
of the `requirement_unsatisfiable` `fragments` array. The `registry` surface
names the baseline, which is a contributing source of the intersection and
therefore has to be nameable when it is the bound that failed.

`requirement_invalid` fires before a requirement exists, so it carries a
location and a closed `violation` token instead of a requirement, and it MUST
NOT echo the offending value: the payload never reproduces an unvalidated
package byte. `requirement_unsatisfiable` has no effective interval, so it
carries the individually validated `fragments` plus the two bounds whose
ordering failed, each naming every source achieving it in Unicode-scalar order
of `source_ref`; the payload is therefore independent of the order in which
sources were read.

##### 4.2.3.10 Guidance and no auto-install

The manager owns a versioned `toolchain-guidance-catalog-v1`. Each entry is
`{guidance_id, toolchain_id, reason, platform, guidance_class, primary_source,
summary, active}` plus `superseded_by` when retired. `reason` is exactly the
diagnostic code's `build_toolchain_` suffix, so the mapping is the identity and
cannot drift. `guidance_class` fixes the admissible origin of `primary_source`:
`host` is the language's own official origin, `configuration` the manager's own
operator documentation origin, and `authoring` this specification's published
origin. In every class `primary_source` is a manager-trusted origin — never a
package, a repository, a mirror, a third-party installer script, or a command
the manager runs. Guidance is text plus URL only, and no skill or repository can
override catalog content.

Identifiers are `toolchain.<toolchain_id>.<reason>.<platform>.r<N>`, with
`platform` one of `linux`, `macos`, `windows`, `any`, and `N` a decimal revision
with no leading zeros, strictly increasing per
`(toolchain_id, reason, platform)` tuple. A published identifier is immutable;
any change of meaning, origin, or class is a new entry at the next revision,
with the old entry setting `active: false` and `superseded_by` to the new
identifier. `superseded_by` MUST name an existing entry of the same tuple at a
strictly greater revision. At most one entry per tuple is active, and retired
entries are retained so an older diagnostic's identifier stays resolvable.

Selection resolves the tuple, not the identifier: the exact
`(toolchain_id, reason, platform)` active entry, else the
`(toolchain_id, reason, any)` active entry. The emitted diagnostic carries the
resolved identifier including its revision. Selection always has a
`toolchain_id` to key on, including for a requirement whose declared `id` is
absent or outside the closed set, because the diagnostic resolves guidance under
the driver's registry primary toolchain.

A published catalog version is immutable in whole, and every change is a
transition to the next version. Across a transition, an entry present in N is
present in N+1 with identical `guidance_id`, `toolchain_id`, `reason`,
`platform`, `guidance_class`, `primary_source`, and `summary`; N+1 may add the
next revision of an existing tuple or revision `1` of a new tuple; an active
entry may be retired with a successor of the same tuple at a greater revision,
or without one only when the coverage gate no longer requires its tuple.
Removing an entry, changing an immutable member, reactivating a retired entry,
setting `superseded_by` on an entry active in N+1, and retiring the last active
entry of a still-required tuple are all inadmissible.

The catalog MUST be total over supported toolchains × all twelve reasons ×
supported platforms, where a supported toolchain is one with a complete registry
entry. Coverage is defined by the selection function: an active exact entry
covers its operating system, and an active `any` entry covers every operating
system not covered by an exact one. All three shapes are valid — a single `any`
entry, one exact entry per operating system, and a hybrid of a fallback plus
overrides. The release gate checks that every operating system in the
toolchain's registry `platforms` set resolves to exactly one active entry, and
that every active entry is reachable: an exact entry for an operating system
outside that set, and an `any` entry shadowed by exact entries for every one of
them, both fail.

This version never downloads, installs, updates, activates, or switches a
toolchain, and specifically not through `rustup`, `swiftly`, `sdkman`, `asdf`,
`mise`, Homebrew, `winget`, the Gradle wrapper, or `GOTOOLCHAIN`. A missing or
incompatible toolchain is an installation error with a typed code and a guidance
identifier. Introducing auto-install requires a new decision, a new trust model
for installer code, and its own review.

### 4.3 Capabilities

Schema 3 and later require `capabilities`. Capabilities are an audit surface,
not a runtime sandbox:

- `network`: `"none"` or unique host globs without whitespace or path syntax;
- `filesystem`: `"repo"`, `"home-config"`, or unique portable paths;
- `exec`: `"none"` or unique bare executable names;
- `secrets`: `"none"` or unique non-empty secret identifiers;
- `env_read`: unique environment-variable names;
- `prompt_scope`: an OPTIONAL non-empty purpose statement.

Missing OPTIONAL capability fields take their schema defaults.

### 4.4 Dependencies

`dependencies.commands` contains system requirements. Its legacy `type:
"skill"` form remains readable, does not create a shim, and produces a
migration warning.

Each `dependencies.skills` entry contains `git`, exact `ref`, activation
`mode`, and OPTIONAL command narrowing. `ref.kind` is `tag` or `revision`;
branch and range syntax is forbidden. `mode` is `full` (default), `runtime`, or
`context`. `commands` is valid only in runtime mode, is non-empty when present,
and names exported script or build commands of the provider. Build commands are
available only from schema 6 or 7 providers; schemas 1 through 5 retain
script-only command narrowing. Duplicates are rejected.

Each `dependencies.mcp_servers` entry requires a non-empty `hint`, MAY document
`transport` as `stdio` or `http`, and uses `required_in` `any` (default) or
`all`.

If neither modern manifest filename exists, `agents/runtime.json` MAY be read
as the legacy object `{ "commands": { <name>: <portable-relative-path> } }`.
Writers MUST NOT create this legacy form.

## 5. Project manifests

`Skillfile.json` conforms to `skillfile-v1.schema.json`. It contains unique
skill declarations and exactly one of `tag`, `branch`, or `revision` for each
skill. `source` is a portable relative path below the manager's configured
source root. `git` is used when the source repository is absent. Branches are
permitted only for direct project declarations and development substitutions.

`project.alias`, when present, is a non-empty, case-sensitive Unicode label of
at most 128 characters with no control characters. It is an operator-facing
matching label, not a filesystem identifier, and therefore MAY contain spaces.

Effective agents are selected in this order: manifest `agents`, registered
project agents, manager defaults. Effective locale is manifest `locale`, then
the manager preference.

`Skillfile.dev.json` conforms to `skillfile-dev-v1.schema.json` or
`skillfile-dev-v2.schema.json` and is never committed. Schema 1 retains only
skill substitutions and MUST reject external-repository substitutions. Schema
2 retains the `substitutions` map and MAY add the strict
`build_repository_substitutions` map. Its outer key is the consuming skill and
its inner key is a repository identifier declared by that skill.

Each skill substitution remains exactly one of a local Git checkout `path` or
`git` plus exact `ref`. Each external-repository substitution MUST be exactly
one operator project-relative local Git `path`, or `git` plus one structured
exact `ref` whose form is `revision`, `tag`, or `branch` under section 6.3.
Package data MUST NOT create or alter a substitution.

A local external substitution resolves relative to the canonical project root
and selects the repository's exact committed `HEAD`; dirty, staged, and
untracked worktree bytes MUST NOT become compiler input. A substitution
replaces acquisition only. It MUST NOT change repository identifier,
descriptor target, driver, command name, output, compiler policy, credential,
or signer. Strict audit MUST reject any substitution. Advisory audit MUST
report it and audit the exact effective snapshot. Substitution state MUST be
recorded in marker v3; removal, path/ref change, or selected-commit movement
MUST make the installation non-current.

## 6. Sources and snapshots

### 6.1 Canonical source identity

Network git sources use a canonical identity. Local paths and `file:` URLs have
no network identity. Protocol 1.0 network URLs:

- use `ssh`, `git`, `http`, or `https`, or SCP form `[user@]host:path`;
- have an ASCII host matching `[A-Za-z0-9][A-Za-z0-9.-]*`;
- contain no explicit port, password, query, fragment, percent escape, or
  backslash;
- contain a non-empty portable repository path with no whitespace, `%`, `?`,
  or `#` character;
- produce a canonical `host/path` identity of at most 4096 Unicode scalar
  values.

Canonicalization lowercases the host, removes user and transport, trims outer
path slashes, and removes one case-sensitive trailing `.git`. Repository path
case is preserved. The result is `host/path`. Invalid network forms MUST be
rejected, not treated as local.

Allowlist matching is segment-aware: identity `h/a/b` matches prefix `h/a` but
not `h/a-evil`. An empty allowlist permits all network identities. Local
sources bypass the network allowlist.

### 6.2 Git safety and references

Git execution MUST restrict protocols to `file`, `git`, `http`, `https`, and
`ssh`; refuse empty or dash-prefixed operands; and place untrusted operands
after `--` where supported. Submodules are unsupported. Archive extraction
MUST reject symbolic links, hard links, path escapes, duplicate platform paths,
and entries exceeding implementation limits documented by the manager.

Tags resolve `refs/tags/<value>^{commit}`. Revisions resolve
`<value>^{commit}`. Branches prefer `refs/remotes/origin/<value>` and then a
local head. A resolved commit is the full lowercase hexadecimal object id
returned by git. Snapshots are immutable regular-file trees produced from that
commit.

### 6.3 External repository source identity and exact lock

Schema-7 external repository declarations use section 6.1 canonicalization
narrowed to HTTPS and SSH. HTTPS MUST have the form `https://host/path` and
MUST NOT contain userinfo. SSH MUST have the URI form
`ssh://[user@]host/path` or SCP form `[user@]host:path`. An SSH username is
OPTIONAL ASCII matching `[A-Za-z0-9][A-Za-z0-9._-]{0,63}` and is removed from
canonical identity. A declaration MUST NOT use `git`, `http`, `file`, another
scheme, an explicit port, password, query, fragment, percent escape, backslash,
empty path component, `.` component, or `..` component.

The host is lowercased and the path case is preserved. Leading and trailing
slashes and exactly one case-sensitive trailing `.git` are removed. The
canonical identity is `host/path` and MUST be no more than 4096 Unicode scalar
values. Transport spelling and a permitted SSH username do not change that
identity. The declared source records identity kind `network-git`, this value,
and transport `https` or `ssh`.

For `go-repository-v1`, the raw SSH repository path is further restricted to
ASCII letters, digits, `.`, `_`, `-`, and `/`, with the same non-empty,
no-`.`/no-`..` component rules. A quote, whitespace, shell metacharacter,
escape, or non-ASCII byte MUST be rejected before Git or SSH starts. HTTPS
retains the Unicode path grammar above.

A manifest tag is the name below `refs/tags/` and MUST:

1. encode to 1 through 255 UTF-8 bytes of valid Unicode scalar text;
2. neither start nor end with `/`, contain `//`, nor end with `.`;
3. have no slash component starting with `.` or ending with `.lock`;
4. contain none of NUL, ASCII control bytes, DEL, space, `~`, `^`, `:`, `?`,
   `*`, `[`, or backslash;
5. contain neither `..` nor `@{` and not equal the single character `@`; and
6. make the exact constructed `refs/tags/<tag>` pass the protocol equivalent
   of `git check-ref-format` without normalization.

A manager MUST NOT pass a tag as an unqualified revision expression. An
operator network substitution MUST use exactly one structured ref:

- `revision` is a full lowercase object ID for the effective repository object
  format;
- `tag` uses the grammar above and selects only `refs/tags/<value>`; or
- `branch` uses the same safe-name grammar and selects only
  `refs/heads/<value>`.

No other revision, peel, reflog, range, or normalization syntax is admitted.

The declared full object ID is immutable. For an unsubstituted source, its
object format MUST equal the effective repository format and the named object
MUST be a commit. A substitution MUST leave that declaration unchanged while
effective state records the substituted repository's actual object format and
full commit. An unsubstituted declaration without `tag` MUST acquire only
`<full-locked-oid>:refs/curator/locked`. An unsubstituted declaration with
`tag` MUST instead acquire only
`refs/tags/<tag>:refs/curator/tag` in fresh operation-private state, recompute
and peel the exact lightweight or annotated-tag chain, and require its terminal
commit to equal the full lock. Server policy permitting or denying direct
object-ID wants MUST NOT alter the tagged flow.

The outer annotated tag object MUST name the requested tag. Every annotated
tag target MUST be exactly `tag` or `commit`; the actual object type MUST match
that declaration. The chain MUST contain no repeated full object ID and no more
than 16 annotated tag objects. A lightweight tag MUST point directly to a
commit. The selected commit, tag records, and terminal object IDs MUST be
recomputed under the declared object format before equality is accepted.

The manager MUST NOT fall back between the tagged and untagged forms or to a
branch, all-tags fetch, alternate ref, configured refspec, named remote, clone,
checkout, archive, or source-selected fetch behavior. A tag terminating at a
different commit MUST fail `build_repository_ref_moved`. A missing,
inaccessible, or transport-unavailable exact source MUST fail
`build_repository_source_unavailable`. Malformed or incomplete fetched objects
retain the semantic failures in section 6.5 rather than being reported as a
successful source or cache result.

### 6.4 Declared and effective external source state

Every `go-repository-v1` command binds a declared state and an effective state.
Declared state MUST contain:

- the repository identifier;
- canonical `network-git` identity and transport;
- immutable `locked_commit.object_format` and full `locked_commit.hex`; and
- OPTIONAL tag.

Effective state MUST contain:

- exact identity kind and value;
- transport when the source is network Git;
- actual object format and full commit;
- Boolean `substituted`;
- typed substitution state when substituted; and
- `curator-build-source-v1` over the exact frozen snapshot.

For an unsubstituted source, `substituted` MUST be false, substitution data
MUST be absent, effective identity MUST equal declared identity, and effective
object format and commit MUST equal the lock. For a substitution, `substituted`
MUST be true and substitution type MUST be exactly `local-path` or
`network-git`; declared state MUST remain present and unchanged.

A network substitution uses the same canonical identity and transport grammar
and records its structured exact ref. A local substitution has identity kind
`operator-local-git`, no transport, and value:

```text
"sha256:" || lowercase_hex(SHA-256(CCJ-1({
  "algorithm": "curator-operator-local-git-v1",
  "project": <canonical-project-identity>,
  "selector": <normalized-project-relative-selector>
})))
```

The selector uses `/`, preserves Unicode scalar values without normalization,
removes `.` components, cancels an ordinary component followed by `..`,
preserves unmatched leading `..`, and contains no empty component. This
identity MUST NOT expose an absolute host path and MUST NOT be treated as a
network source identity or authorization token. The actual object format, full
commit, and build-source digest remain authoritative for the selected bytes.

### 6.5 Raw-object snapshot and audit equivalence

The external repository object database and its configuration are untrusted
transport input. A manager MUST use an operator-trusted, fingerprinted Git
release family, manager-owned private repository/configuration, clean
environment, fixed child graph, transport and credential policy, and bounded
raw-object reader. Repository data MUST NOT select or extend Git, SSH, HTTPS,
credential, proxy, helper, upload-pack, hook, filter, LFS, submodule,
alternate, replace, graft, checkout, archive, maintenance, or lazy-fetch
behavior.

HTTPS MUST verify TLS and MUST NOT follow redirects. SSH MUST use an operator-
trusted OpenSSH executable, operator-selected known-hosts and authentication
state, an empty manager-owned SSH configuration, and a manager-owned wrapper
that accepts only the validated destination and exact upload-pack command.
Package and repository data MUST NOT select a credential, identity file, agent,
known-hosts file, proxy/jump/local command, timeout, forwarding, control
socket, TTY, SSH option, or remote command.

Network acquisition and a local substitution MUST converge on the same
manager-owned raw-object proof. Local-substitution v1 MUST admit only an
ordinary non-bare files-ref worktree with a link-free `.git` directory directly
below its root. It MUST parse admitted configuration, refs, loose objects, and
paired pack versions 2 or 3 with index version 2 as bounded data and MUST NOT
execute source-repository Git behavior. Gitfiles, linked worktrees, bare
repositories, reftable or unknown extensions, unsafe links/layout, unsupported
pack/index state, alternates, promisor state, grafts, replace refs, shallow
state, optional pack sidecars, and incomplete object stores MUST fail closed.

The manager MUST independently recompute the object-format hash of every
consumed commit, tag, tree, and blob. It MUST parse the selected commit and
bounded annotated-tag chain with one byte grammar on both source paths, prove
the complete reachable tree/blob graph, reject links, gitlinks, special files,
invalid or colliding paths, and reject every non-empty blob below 1024 bytes
accepted by parser family `git-lfs-pointer-parser-v3.7.1`. It MUST NOT hydrate
LFS data or obtain a missing object from the network, an alternate, a checkout,
or a filter.

Known failures MUST remain distinguishable:

- unsafe local gitfile, bare, linked-worktree, layout, format, and object-
  container cases use respectively
  `build_repository_local_gitfile_unsupported`,
  `build_repository_local_bare_unsupported`,
  `build_repository_local_linked_worktree_unsupported`,
  `build_repository_local_layout_unsafe`,
  `build_repository_local_format_unsupported`, and
  `build_repository_local_object_format_unsupported`;
- missing or incomplete graph bytes use
  `build_repository_incomplete_source`;
- malformed commit/tag semantics use
  `build_repository_git_object_semantics_invalid`; and
- a matched Git LFS pointer uses `build_repository_git_lfs_unsupported`.

After raw-object proof, the manager MUST materialize exact blob bytes as one
immutable regular-file snapshot. Before audit success, artifact-cache lookup,
or a compiler child, it MUST validate the complete snapshot, compute
`curator-build-source-v1`, parse the root descriptor, validate the selected
target and module containment, and freeze that snapshot instance until the last
build child exits.

The consuming skill and each effective external repository are independent
audit subjects. The external audit subject MUST bind declared and effective
identity, object format, full effective commit, complete build-source digest,
descriptor target, substitution state, and successful exact-tag assertion when
applicable. Skill evidence MUST NOT attest an external repository; external
evidence MUST NOT attest the skill. Audit-cache reuse requires exact subject
tuple equality and MUST NOT bypass snapshot admission.

For each external repository subject, the manager MUST independently apply the
applicable allowlist, revocation, registry, tag-lock, and audit-policy gates.
Every applicable gate MUST succeed before artifact-cache lookup or compiler
work. A gate decision for the consuming skill or another external repository
MUST NOT be reused for that subject.

This ordering applies to real builds, claimed cache hits, and dry-runs that
claim source or audit coverage. A syntax-only offline operation that cannot
obtain the exact snapshot MAY warn `build_repository_unverified_offline`, but
MUST NOT claim source, audit, cache, receipt, marker, artifact, or installation
coverage. Install, update, repair, and coverage-claiming audit MUST fail
`build_repository_source_unavailable` before mutation when the exact source
cannot be obtained and audited.

## 7. Closure resolution

Direct declarations enter as `full` requirements from synthetic consumer
`<project>`. Processing a provider adds its skill requirements.

Within one closure, one skill name MUST resolve to exactly one commit and one
canonical source identity. Different identities or commits fail with every
relevant requirement chain. Different refs resolving to one commit unify.
Cycles fail and name the cycle.

Activation is edge-based. Context is active when any incoming edge is `full`
or `context`. All commands are active when any edge is `full`; otherwise the
active set is the union of runtime edges, narrowed where requested.

Provider order is deterministic Kahn topological order: among currently ready
providers select the lexicographically smallest skill name by Unicode scalar
value. The synthetic project is not emitted. Diagnostic requirement chains use
the lexicographically smallest complete chain when multiple chains are equal
in length.

## 8. Content hashes

The Curator content hash is calculated over regular files excluding the marker
itself. For each selected file in sorted protocol-path order, append:

```text
UTF8(path) || 0x00 || file_bytes
```

Join adjacent records with one additional `0x00`, hash the resulting byte
string with SHA-256, encode lowercase hexadecimal, and prefix `sha256:`. The
empty tree hashes the empty byte string. File mode, owner, timestamp, and
filesystem-native separator are not hashed. Readers MUST reject duplicate
protocol paths rather than hash one arbitrarily.

### 8.1 Build-source identity

The installed-tree `content_sha256` above remains unchanged and excludes root
`.csk-install.json`. It MUST NOT be used as compiled-artifact identity.
Compiled commands instead bind the fully validated immutable raw snapshot with
algorithm identifier `curator-build-source-v1`, including every regular file
and any package-provided root `.csk-install.json`.

Snapshot validation MUST occur before build-cache lookup or any Go command.
The snapshot MUST contain only directories and regular files; links, special
files, invalid protocol paths, duplicate encoded paths, and platform path
collisions are invalid. For every regular file, convert its relative protocol
path to `/` separators without normalization and encode its Unicode scalar
values as UTF-8. Sort those path bytes in unsigned bytewise order. Initialize
SHA-256 with exact ASCII `curator-build-source-v1` followed by `0x00`, then
append for each file:

```text
ASCII("F") || uint64be(path_byte_length) || path_utf8 ||
uint64be(content_byte_length) || file_bytes
```

Prefix the lowercase digest with `sha256:`. An empty snapshot hashes only the
domain prefix. Modes, ownership, timestamps, ACLs, and extended attributes are
not inputs. Implementations MUST NOT substitute the marker-excluding content
hash with an empty exclusion list: `curator-build-source-v1` is domain-separated
and length-framed. The validated snapshot instance MUST remain byte-for-byte
unchanged until the last build child exits.

### 8.2 Go toolchain identity

Every `go-v1` cache input MUST identify its operator-trusted toolchain with
algorithm `curator-go-toolchain-v1`. Resolve the launcher independently of the
package and before entering a package-controlled directory. It MAY be bundled
with the manager or selected by trusted operator configuration, but MUST NOT
come from the repository, a runtime root, project `.agents/bin`, the user
`PATH`, or a manifest. Require it to be the regular executable
`<resolved-goroot>/bin/go` (`bin/go.exe` on Windows), not a wrapper or an
executable outside the tree being fingerprinted. A clean `go env GOROOT` probe
MUST resolve to the same root.

Walk `GOROOT` without following links; the root itself is not a record.
Relative components MUST contain valid
Unicode scalar values; encode `/`-joined paths as UTF-8 without case folding or
normalization and reject duplicate encoded paths and special files. Symlinks
MUST be relative, non-dangling, and resolve within `GOROOT`, and their referents
have independent tree records. Sort path bytes in unsigned bytewise order.
Initialize SHA-256 with exact ASCII
`curator-go-toolchain-v1` followed by `0x00`, then append for every entry:

```text
kind || uint64be(path_byte_length) || path_utf8 ||
uint64be(payload_byte_length) || payload
```

`kind` is ASCII `D`, `F`, or `L`; directory payload is empty, file payload is
the exact bytes, and link payload is the exact UTF-8 `readlink` value. Hard
links are independent regular-file records. Normalize `go version` stdout by
requiring at most 4096 bytes and exactly one terminal LF, optionally preceded
by CR, removing that terminator, and rejecting any other CR, LF, NUL, empty, or
invalid UTF-8 content. Append it as one final `V` record with an empty path.
Prefix the lowercase digest with `sha256:`.

Permissions, ownership, timestamps, ACLs, and extended attributes are not hash
inputs, but `bin/go` and each invoked `pkg/tool/<host>/` child MUST be regular
and executable at use time. The tree MUST remain unchanged through the last
child exit. The logical identity also records normalized `go_version` and
`go_relpath: "bin/go"`; toolchain location is not portable identity.

## 9. Compiled-artifact cache and receipts

### 9.1 Local `go-v1` receipt schema 1

For each active local `go-v1` command, the manager MUST construct a logical
build-input object containing schema version 1, driver, the
`curator-build-source-v1` identity, `build_root`, command name, `source_dir`,
native GOOS/GOARCH/tuning, the complete `curator-go-toolchain-v1` identity, and
these fixed policy values:

```json
{
  "module_mode": "vendor",
  "network": "none",
  "workspace": false,
  "cgo": false,
  "compiler_directives": "reject-nonstandard-cgo-import-dynamic-v1",
  "target_mode": "native",
  "link_mode": "internal",
  "libgcc": "none",
  "package_assembly": false,
  "host_objects": false,
  "telemetry": "off-private",
  "execution_policy": "manager-worker-v1"
}
```

`execution_policy` is the exact execution-policy identity of section 4.2.1. It
is REQUIRED, closed to the single portable value in protocol 1.0, and never
derived from a host label, a capability probe, or package data.

`network: "none"` denotes the fixed offline Go module, proxy, checksum-database,
and version-control configuration of section 4.2 and the absence of any
manager-initiated or Go-initiated network access for dependency resolution or
the build. It is not a claim of kernel-enforced network denial for the worker
domain; that guarantee is `total-network-denial`, deferred by section 4.2.1.

The logical cache key is:

```text
"sha256:" || lowercase_hex(SHA-256(CCJ-1(build_input)))
```

`CCJ-1` is defined in `registry.md`; the input bytes have no BOM,
insignificant whitespace, or terminal LF. A semantic change to arguments,
environment, execution policy, receipt interpretation, or output rules requires
a new driver identifier or an explicit versioned execution-policy revision.
Because `execution_policy` is inside the hashed input, an entry produced under a
different execution contract, or under a pre-revision input that carried no
execution policy at all, MUST miss and MUST NOT alias a portable entry. Host
capability evidence is not an input: a manager MUST NOT add it to, or infer it
from, the cache key.

Each immutable logical entry contains exactly one manager-derived artifact and
a strict build-receipt schema 1. The receipt contains its schema version,
logical cache key, the complete build input, and artifact-relative path,
SHA-256, and byte length. Stored receipt bytes MUST equal `CCJ-1(receipt)`
exactly. Define:

```text
receipt_sha256 = "sha256:" ||
  lowercase_hex(SHA-256(exact_stored_receipt_bytes))
```

### 9.2 External `go-repository-v1` receipt schema 2

Each active external command MUST use build receipt schema 2. Its logical input
MUST contain:

- schema version 2 and driver `go-repository-v1`;
- repository identifier;
- declared canonical `network-git` identity, transport, immutable object
  format and full commit lock, and OPTIONAL tag;
- effective identity, transport when applicable, actual object format, full
  commit, `substituted`, typed substitution when present, and external
  `curator-build-source-v1`;
- descriptor path fixed to `skill-build.json` and selected target;
- consuming manifest command name, selected `build_root`, and `source_dir`;
- native GOOS/GOARCH/tuning and complete `curator-go-toolchain-v1`; and
- the policy object from section 9.1 plus
  `"source_kind":"locked-external-git-v1"`.

For `substituted: false`, effective identity, object format, and commit MUST
equal the declaration and substitution MUST be absent. If declared `tag` is
present, a writer MUST NOT publish the receipt until that same operation's
exact-tag acquisition and manager-computed peel prove the terminal commit
equals the full lock. The receipt MUST NOT contain a self-asserted trust,
provenance, or `tag_verified` field.

For `substituted: true`, the declaration remains unchanged and effective source
MUST describe the actual compiled snapshot. A local substitution uses identity
kind `operator-local-git` and substitution `{"type":"local-path"}`. A network
substitution uses identity kind `network-git`, canonical value and transport,
and typed structured ref. A substituted receipt's declared tag is declaration
history only; it MUST NOT claim that the declared remote tag was consulted.

The schema-2 logical cache key is the SHA-256 of `CCJ-1` over the complete
input. The receipt MUST retain the complete input, logical cache key,
manager-derived artifact-relative path, artifact SHA-256, and byte length in
exact canonical bytes. Different declared or effective states, substitutions,
commands, targets, build roots, source directories, native targets,
toolchains, execution policies, or policy revisions MUST NOT alias.

### 9.3 Shared protected-cache rules

Before reuse, a reader MUST open a regular singly linked receipt without
following links, recanonicalize it, and require exact stored-byte equality;
recompute the build-source identity before opening the candidate; recompute and
match the cache key and entire expected input; require the manager-derived
artifact path; and open, bound, hash, and size-check one regular singly linked
artifact without following links. It MUST reject unknown receipt fields or
unsupported receipt, driver, build-source, toolchain, and execution-policy
identities. An entry whose execution policy is absent or is not the policy the
reader implements is a miss, never a hit and never an upgrade. It MUST NOT
execute the artifact.

Persistent reuse is permitted only below manager-created, manager-protected
state resolved independently of package input. On every lookup and again under
the manager-home mutation lock, the manager MUST verify ownership, private
mutation permissions or DACL, containment, regular file types, and link safety
for the boundary and every entry component. An implementation that cannot
prove this boundary MUST disable persistent reuse. A real operation rebuilds
from the revalidated snapshot into newly established protected state; dry-run
reports `would-rebuild-untrusted-cache`; status is non-current. Self-consistent
receipt, marker, artifact, and hash bytes do not repair or authenticate an
untrusted boundary.

The logical cache key, exact receipt bytes, artifact-relative path, artifact
bytes/hash/size, and validation outcomes are portable. Manager-home paths,
physical cache-root and driver-directory names, receipt filenames, lock and
quarantine names, and storage backends are implementation-specific. A manager
MUST NOT infer portable paths such as `build-cache` or `.csk-build.json`.

Entries are built in operation-private staging and published atomically and
immutably under the manager-home mutation lock. Receipt hashes are deterministic
corruption/currentness identifiers, not signatures, MACs, attestations, or
proof of provenance. The verified protected-state boundary supplies local
provenance; registry audit continues to attest source, not the compiled result.

Dry-run MAY obtain, raw-validate, hash, and independently audit an exact
external snapshot in removable operation-private state; MAY validate local
build-root exclusion; MAY compute build-source and trusted-toolchain identity;
and MAY inspect protected entries read-only. It MUST NOT invoke `go list`,
`go build`, a compiler, or linker; create Go caches, a persistent repository or
snapshot, an audit response, a persistent memo, a mutation lock or journal;
publish, quarantine, repair, or adopt cache bytes; copy build roots into
runtime; or mutate installation, registry, audit, marker, shim, adapter, or
consumer state. A claimed external cache hit requires exact snapshot admission
and audit first. After exact receipt validation, a hit MUST NOT run
source-aware Go commands.

### 9.4 Protected external snapshots, deduplication, and garbage collection

The protected external snapshot key MUST contain the complete effective
identity kind and value, effective object format, full effective commit, and
external `curator-build-source-v1` digest. A manager MUST NOT omit, replace, or
infer any key component from declared state. Snapshot bytes MAY be
deduplicated only when every component of the complete snapshot key is equal.
Audit decisions remain subject-specific and MUST NOT be deduplicated or reused
merely because snapshot bytes or snapshot keys are equal.

Garbage collection MUST revalidate protected-cache boundaries and run under
the manager-home mutation lock. Its live roots MUST include:

- for every valid marker-v3 installation, each referenced local skill raw
  snapshot, complete external frozen-snapshot key, receipt/artifact key, and
  manager-generated shim relationship;
- every staged or published snapshot and artifact referenced by an in-flight
  transaction journal and needed for commit or rollback; and
- the roots already defined for valid marker-v1 and marker-v2 installations,
  whose behavior remains unchanged.

Receipt content alone MUST NOT make an entry live. If a marker or journal is
unreadable, or a cache boundary or possible reference cannot be proved,
garbage collection MUST conservatively retain the uncertain entries. It MUST
NOT execute or adopt source or artifact bytes, repair permissions to make
candidate bytes trusted, or infer liveness from an unvalidated partial record.
Physical snapshot, artifact, receipt, lock, journal, quarantine, and
garbage-collection paths remain implementation-specific.

## 10. Install markers

Every installed closure node has `.csk-install.json`. Managers supporting
schema 7 MUST read marker schemas 1, 2, and 3. They MUST write marker schema 2
for schema 1 through 6 installation mutations and marker schema 3 for schema 7
installation mutations. They MAY continue to regard a valid marker-v1
installation as current for a schema 1 through 5 package. Marker v1 and v2
retain their existing shapes and meanings.

Marker v2 permits `skill_schema_version` through 6 and requires sorted
`build_roots` and a `builds` object, including empty values for installations
without active compiled commands. `build_source` is REQUIRED exactly when
`builds` is non-empty and MUST otherwise be absent. Each lexically ordered
`builds` entry records driver, logical cache key, `receipt_sha256`, artifact
SHA-256, and manager-derived artifact-relative path. A build shim MUST target
the immutable cache artifact selected by the effective plan and marker, not the
commit-keyed script runtime store.

Marker v3 permits `skill_schema_version` through 7 and represents local-only,
external-only, and mixed command sets. Every build entry MUST explicitly record
its receipt schema version and its `execution_policy`, which MUST equal the
execution-policy identity inside the referenced receipt input. A local `go-v1`
entry MUST retain receipt schema 1 and marker-v2 entry semantics. An external
`go-repository-v1` entry MUST record receipt schema 2, repository identifier,
declared identity and immutable lock, OPTIONAL declared tag, effective identity,
object format and full commit, substitution state, external build-source
identity, descriptor target, logical cache key, `receipt_sha256`, artifact hash,
and manager-derived artifact path. No receipt or marker field MAY be inferred
from a driver name.

A marker-v2 build record keeps its frozen schema-6 shape and does not gain an
`execution_policy` member. Its execution-policy binding is transitive and
complete: the recorded logical cache key and `receipt_sha256` are computed over
an input that contains the execution-policy identity, so a record written under
one execution contract can never validate against another.

Marker-v3 top-level `build_source` and `build_roots` retain schema-6 meaning.
Top-level `build_source` is REQUIRED exactly when at least one active local
`go-v1` command exists and MUST otherwise be absent. External-only
installations MUST bind source per external build entry and MUST NOT use the
consuming skill's raw snapshot as external compiled-source identity. An
unsubstituted external entry MAY record declared tag only from a receipt whose
producing operation completed exact-tag acquisition and equality with the
immutable lock; the marker field is not independent proof.

`locale` is always present and is a string or `null`. Required set-like arrays
are always arrays, including when empty.

The following arrays are set-like and writers sort them by Unicode scalar
value: `agents`, `commands`, `dependencies`, `files`, `requirements`,
`runtime_roots`, `build_roots`, `requirers`, `activation.commands`, and every
MCP agent list. Writers sort `builds` keys by Unicode scalar value. Object
member order and whitespace are not significant.

An installation is current only when the marker schema is supported; ref kind,
ref, commit, locale, agents, activation, substitution, MCP findings, and
attestation match the effective plan; and the installed content hash matches
`content_sha256`. For a build-enabled marker, currentness additionally requires
the declared local build roots and static context exclusion to match; every
available local or external protected snapshot's `build_source` to match the
effective plan and receipt input; each logical cache key and manager-derived
artifact path to match; and every referenced receipt/artifact to validate below
a currently verified manager-protected boundary.

For external entries, currentness also requires declared and effective
identity, object format, full commit, target, and substitution state to match;
the external snapshot boundary and source digest to validate; the receipt
schema-2 relationship to match exactly; and the shim to select the protected
artifact. A missing snapshot that the marker claims should exist, prompt-
visible or runtime-copied external source, untrusted boundary, corrupt
receipt/artifact, wrong target or toolchain, or mismatched source identity
makes the installation non-current. When existing profile semantics
distinguish unavailable evidence from drift, a result MAY be `unknown`, but it
MUST NOT be current and a checking status command MUST return non-zero.

Read-only status MUST NOT contact an external remote merely to retest tag
availability or movement. It MUST NOT fetch, repair, quarantine, alter
permissions, refresh a snapshot, invoke a compiler or signer, or execute an
artifact. Repair MUST reacquire, validate, and audit the exact effective source
and MUST rebuild into protected state rather than adopt candidate bytes. For an
unsubstituted tagged source, repair MUST use only the exact-tag path and MUST
reprove terminal equality with the immutable lock; an old snapshot or direct-
object fetch MUST NOT substitute for that assertion.

Unsupported or unreadable markers are not current. A moved tag is a warning,
or an error under strict-tag policy.

The marker and its referenced receipt hashes are not signatures and MUST NOT be
used as authorization tokens or provenance proof. Registry attestations are
reverified from signed records when fresh trust is required.

## 11. Adapter ledger

Every managed adapter root contains `.csk-managed.json` conforming to
`adapter-ledger-v1.schema.json`. `entries` is a sorted unique list of skill
names owned by the manager in that adapter root. A manager MUST remove only
entries in its preceding ledger and MUST fail rather than overwrite an
unmanaged conflicting entry.

## 12. External build publication and closed extensions

### 12.1 Publication, shims, and rollback

All `go-repository-v1` compilation MUST occur in operation-private staging
before installation mutation. The manager MUST validate and hash the sole
manager-derived artifact, generate canonical receipt and marker bytes, and
publish immutable snapshots and artifacts only under the manager-home mutation
lock. The consumer ledger MUST commit last. A failure after publication begins
MUST roll committed targets back in reverse order while retaining that lock.
Pre-publication source, object, descriptor, audit, cache, or compiler failures
MUST leave live installation state unchanged.

One manifest command key MAY select the same descriptor target as another
command key, but each command MUST derive its own artifact name, cache input,
receipt, and shim. The repository MUST NOT request aliases, sidecars,
post-build copies, or secondary PATH entries. A build shim MUST be manager-
owned and point exactly to the marker-selected protected artifact. It MUST NOT
point into a Git object database, frozen source snapshot, checkout, staging
directory, or commit-keyed script runtime. Structural validation MUST NOT use a
shell, executable lookup, or execution of the built output.

### 12.2 Operator credentials and signing

Git/SSH/HTTPS executables, credentials, host-verification state, proxy policy,
timeouts, and authentication mode are operator-owned. They MUST NOT be
selected by a manifest, descriptor, repository, substitution, compiler
environment, receipt trust field, or marker. Source credentials MUST NOT enter
the compiler environment.

`go-repository-v1` revision 1 performs no manager post-signing, timestamping,
or notarization. Signing identities and notarization credentials are operator
or release-pipeline secrets and MUST NOT appear in a manifest, descriptor,
repository, receipt trust field, or marker. A platform policy requiring local
signing MUST reject the source-built artifact until a separately versioned and
reviewed signer profile defines the fixed signer identity, executable, argv,
entitlements/options, process graph, network policy, signed-byte and cache
identity, protected publication, and rollback rules.

### 12.3 Future closed-driver admission

The external Git envelope MAY be reused, but compiler semantics MUST NOT become
generic. Every future language driver requires a new closed identifier and an
independent protocol and security review. Its normative contract MUST define:

- complete compiler-visible input and dependency containment;
- a complete registry entry under section 4.2.3.1, including probe argument
  vectors, normalization rule, prerelease markers, root layout, primary
  executable relpath, fingerprint algorithm, companion toolchains, supported
  platforms, baseline, `compatibility` granularity and initial tested set, and a
  closed source-metadata disposition table whose two alignment properties are
  measured against that ecosystem's own command rather than asserted;
- trusted toolchain, sysroot, SDK, and runtime identity;
- fixed process graph, environment, arguments, flags, target, output, and
  signer boundary;
- offline dependency, source identity, link, and native-library policy;
- rejection of hooks, plugins, macros, generators, annotation processors,
  build tasks, recipes, response files, package linkers, and produced-program
  execution; and
- receipt/marker/cache identity, audit-before-build ordering, dry-run,
  publication, rollback/recovery, status, repair, garbage collection, and
  platform conformance vectors.

The same rule governs execution policies. A hardened execution profile MUST use
a new execution-policy identity, a new claim schema version that can express it,
and its own conformance vectors. It MUST NOT be admitted by widening the closed
`manager-worker-v1` constant, by treating an unknown execution policy as
compatible, or by upgrading a portable cache entry, receipt, marker, or claim in
place.

A manager MUST NOT admit a future driver by widening `go-v1` or
`go-repository-v1`, accepting an unknown driver, or providing a generic build
or package-manager fallback.
