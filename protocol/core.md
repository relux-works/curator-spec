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

### 1.1 Compatibility identifiers

The filenames `Skillfile.json`, `Skillfile.dev.json`, `agent-skill.json`,
`curator-build.json`, `.csk-install.json`, `.csk-managed.json`, and project root
`.agents/` are portable protocol identifiers. A manager MUST read and write
those exact names. The filename `csk-skill.json` is a reserved legacy alias for
`agent-skill.json`: managers MUST continue to read it throughout protocol 1.x,
but writers MUST emit only `agent-skill.json`. `curator-build.json` is not a
skill-manifest alias; it is valid only as the schema-7 external-repository
descriptor defined in section 4.2.1.

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
`agent-skill-v7.schema.json`. The legacy filename `csk-skill.json` has exactly
the same object shape and schema-version semantics through
`csk-skill-v7.schema.json`.

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

Version gates are downward: a field introduced by a later version MUST be
rejected in an earlier one. Schema 1 preserves its deployed extension behavior;
schemas 2 through 7 reject unknown fields. Schema 1 through 5 MUST reject
`build_roots`, a command with `type: "build"`, and every build-only field.
Schema 1 through 6 MUST reject `build_repositories`, `repository`, `target`,
and `go-repository-v1`. Their script, system, runtime-root, capability,
dependency, context, hash, `go-v1`, receipt-v1, and marker-v1/v2 behavior is
unchanged.

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

#### 4.2.1 Schema-7 external repositories and `go-repository-v1`

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
from the effective commit's root `curator-build.json`. The command and
descriptor target drivers MUST both equal `go-repository-v1`. An unknown or
mismatched driver MUST fail before artifact-cache lookup or compiler execution
and MUST NOT fall back to `go-v1`, a script, a system command, or a generic
build facility.

`curator-build.json` schema 1 is strict and contains exactly
`schema_version: 1` and a non-empty `targets` map keyed by portable identifiers.
Each `go-repository-v1` target MUST contain exactly `driver`, `build_root`, and
`source_dir`. These paths are relative to the repository root. The single
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
compiler tag, toolchain, output name or path, install destination, alias, PATH
edit, signing identity, credential, hook, plugin, generator, build recipe,
post-build action, fallback, or secondary artifact.

`go-repository-v1` reuses the exact `go-v1` trusted toolchain identity, native
target, process vectors, environment, vendor-only dependency checks, compiler
directive and native-input rejection, internal-link policy, staging rules,
resource controls, and no-artifact-execution rule. It MUST NOT reinterpret or
widen any of those rules. Its external acquisition, audit subject, receipt
schema, and marker state are distinct as defined in sections 6, 9, and 10.

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
- descriptor path fixed to `curator-build.json` and selected target;
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
toolchains, or policy revisions MUST NOT alias.

### 9.3 Shared protected-cache rules

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
its receipt schema version. A local `go-v1` entry MUST retain receipt schema 1
and marker-v2 entry semantics. An external `go-repository-v1` entry MUST record
receipt schema 2, repository identifier, declared identity and immutable lock,
OPTIONAL declared tag, effective identity, object format and full commit,
substitution state, external build-source identity, descriptor target, logical
cache key, `receipt_sha256`, artifact hash, and manager-derived artifact path.
No receipt or marker field MAY be inferred from a driver name.

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

A manager MUST NOT admit a future driver by widening `go-v1` or
`go-repository-v1`, accepting an unknown driver, or providing a generic build
or package-manager fallback.
