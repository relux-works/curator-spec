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

### 1.1 Compatibility identifiers

The filenames `Skillfile.json`, `Skillfile.dev.json`, `agent-skill.json`,
`.csk-install.json`, `.csk-managed.json`, and project root `.agents/` are
portable protocol identifiers. A manager MUST read and write those exact names.
The filename `csk-skill.json` is a reserved legacy alias for
`agent-skill.json`: managers MUST continue to read it throughout protocol 1.x,
but writers MUST emit only `agent-skill.json`.

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
validating, auditing, or installing a skill. Schema 6 build commands are the
only compilation extension to this rule: a manager MAY pass untrusted Go
source bytes to the closed `go-v1` driver in section 4.2, but MUST NOT transfer
execution control to a package-selected program, argument vector, environment,
hook, plugin, generator, build recipe, or compiled output.

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
`agent-skill-v6.schema.json`. The legacy filename `csk-skill.json` has exactly
the same object shape and schema-version semantics through
`csk-skill-v6.schema.json`.

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

Version gates are downward: a field introduced by a later version MUST be
rejected in an earlier one. Schema 1 preserves its deployed extension behavior;
schemas 2 through 6 reject unknown fields. In particular, schema 1 through 5
MUST reject `build_roots`, a command with `type: "build"`, and every build-only
field. Their script, system, runtime-root, capability, dependency, context,
hash, and marker-v1 behavior is unchanged.

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

`build_roots` and build commands exist only in manifest schema 6. Every build
root MUST be a portable relative path other than `.`, MUST name a real,
link-free directory in the immutable raw snapshot, and MUST be unique and
pairwise disjoint. No build root may equal, contain, or be contained by a
runtime root. Every declared build root MUST be referenced by at least one
build command.

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

The manager MUST invoke the resolved `<GOROOT>/bin/go` directly, never through
a shell or joined command string. Once per operation it MUST use exactly these
package-independent argument vectors from a manager-owned empty directory as
the working directory. The bootstrap environment MUST start empty except for
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

Only the fingerprinted `go` executable and its regular executable children
below fingerprinted `GOROOT/pkg/tool/<GOHOSTOS>_<GOHOSTARCH>/` may start. The
source snapshot MUST be read-only to child processes and unchanged until the
last child exits. The one output MUST be a bounded regular file inside manager
staging. The manager MUST hash it, set manager-defined executable permissions,
and MUST NOT execute it for validation, version discovery, smoke testing,
post-processing, receipt generation, rollback, or any other reason.

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
available only from schema 6 providers; schemas 1 through 5 retain script-only
command narrowing. Duplicates are rejected.

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

`Skillfile.dev.json` conforms to `skillfile-dev-v1.schema.json` and is never
committed. Each substitution is exactly one of a local git checkout `path` or
`git` plus exact `ref`. A substitution replaces every requirement of that name,
skips its normal unification check, is recorded in the marker, and causes
strict audit mode to fail.

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

For each active build command, the manager MUST construct a logical build-input
object containing schema version 1, driver, the `curator-build-source-v1`
identity, `build_root`, command name, `source_dir`, native GOOS/GOARCH/tuning,
the complete `curator-go-toolchain-v1` identity, and these fixed policy values:

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
  "telemetry": "off-private"
}
```

The logical cache key is:

```text
"sha256:" || lowercase_hex(SHA-256(CCJ-1(build_input)))
```

`CCJ-1` is defined in `registry.md`; the input bytes have no BOM,
insignificant whitespace, or terminal LF. A semantic change to arguments,
environment, sandbox-relevant policy, receipt interpretation, or output rules
requires a new driver identifier or an explicit versioned cache-key policy.

Each immutable logical entry contains exactly one manager-derived artifact and
a strict build-receipt schema 1. The receipt contains its schema version,
logical cache key, the complete build input, and artifact-relative path,
SHA-256, and byte length. Stored receipt bytes MUST equal `CCJ-1(receipt)`
exactly. Define:

```text
receipt_sha256 = "sha256:" ||
  lowercase_hex(SHA-256(exact_stored_receipt_bytes))
```

Before reuse, a reader MUST open a regular singly linked receipt without
following links, recanonicalize it, and require exact stored-byte equality;
recompute the build-source identity before opening the candidate; recompute and
match the cache key and entire expected input; require the manager-derived
artifact path; and open, bound, hash, and size-check one regular singly linked
artifact without following links. It MUST reject unknown receipt fields or
unsupported receipt, driver, build-source, and toolchain versions. It MUST NOT
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

Dry-run MAY validate the raw snapshot and build-root exclusion, compute build
source and trusted-toolchain identity, and inspect protected entries read-only.
It MUST NOT invoke `go list`, `go build`, a compiler, or linker; create Go
caches, a persistent memo, a mutation lock or journal; publish, quarantine,
repair, or adopt cache bytes; copy build roots into runtime; or mutate
installation, registry, audit, marker, shim, adapter, or consumer state. A
cache hit MUST use the same static context exclusion and, after exact receipt
validation, MUST NOT run source-aware Go commands.

## 10. Install markers

Every installed closure node has `.csk-install.json`. Managers MUST read marker
schemas 1 and 2, MUST write schema 2 on every installation mutation, and MAY
continue to regard a valid marker-v1 installation as current for a schema 1
through 5 package. Marker v1 retains its existing shape and meaning.

Marker v2 permits `skill_schema_version` through 6 and requires sorted
`build_roots` and a `builds` object, including empty values for installations
without active compiled commands. `build_source` is REQUIRED exactly when
`builds` is non-empty and MUST otherwise be absent. Each lexically ordered
`builds` entry records driver, logical cache key, `receipt_sha256`, artifact
SHA-256, and manager-derived artifact-relative path. A build shim MUST target
the immutable cache artifact selected by the effective plan and marker, not the
commit-keyed script runtime store.

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
the declared build roots and static context exclusion to match; the fully
validated raw snapshot's `build_source` to match the effective plan and every
receipt input; each logical cache key and manager-derived artifact path to
match; and every referenced receipt/artifact to validate below a currently
verified manager-protected boundary. A missing raw snapshot, prompt-visible or
runtime-copied build-root file, untrusted boundary, corrupt receipt/artifact,
wrong target or toolchain, or mismatched source identity makes the installation
non-current. Repair MUST rebuild from a revalidated snapshot into protected
state rather than adopt candidate bytes.

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
