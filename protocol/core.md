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

The filenames `Skillfile.json`, `Skillfile.dev.json`, `csk-skill.json`,
`.csk-install.json`, `.csk-managed.json`, and project root `.agents/` are
portable protocol identifiers. A manager MUST read and write those exact names.

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
validating, auditing, or installing a skill.

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

Directories declared in `runtime_roots` are excluded even if nested under an
eligible context root. Selection uses protocol paths, sorts selected files by
Unicode scalar value of their POSIX path, rejects links, and copies regular
file bytes without newline conversion.

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

`csk-skill.json` is OPTIONAL for a pure context skill and otherwise conforms to
exactly one of `csk-skill-v1.schema.json` through
`csk-skill-v5.schema.json`.

| Schema | Added behavior |
|---|---|
| 1 | exported script and system commands |
| 2 | `runtime_roots`, command dependencies, strict top-level fields |
| 3 | REQUIRED capability declaration |
| 4 | transitive skill requirements |
| 5 | MCP server requirements |

Version gates are downward: a field introduced by a later version MUST be
rejected in an earlier one. Schema 1 preserves its deployed extension behavior;
schemas 2 through 5 reject unknown fields.

### 4.1 Runtime roots and commands

Every runtime root and script command path MUST be a portable relative path
that exists in the snapshot. Runtime roots MUST name directories, be unique,
and be pairwise disjoint. For schema 2 and later, every script command path
MUST fall within one declared runtime root when any roots are declared.

A script command declares at least one of `unix_path` and `win_path`. A system
command declares a non-empty bare executable name and MAY include a hint. A
missing system command fails installation with the hint. The command name is
the shim name and one active name has exactly one owner.

### 4.2 Capabilities

Schema 3 and later require `capabilities`. Capabilities are an audit surface,
not a runtime sandbox:

- `network`: `"none"` or unique host globs without whitespace or path syntax;
- `filesystem`: `"repo"`, `"home-config"`, or unique portable paths;
- `exec`: `"none"` or unique bare executable names;
- `secrets`: `"none"` or unique non-empty secret identifiers;
- `env_read`: unique environment-variable names;
- `prompt_scope`: an OPTIONAL non-empty purpose statement.

Missing OPTIONAL capability fields take their schema defaults.

### 4.3 Dependencies

`dependencies.commands` contains system requirements. Its legacy `type:
"skill"` form remains readable, does not create a shim, and produces a
migration warning.

Each `dependencies.skills` entry contains `git`, exact `ref`, activation
`mode`, and OPTIONAL command narrowing. `ref.kind` is `tag` or `revision`;
branch and range syntax is forbidden. `mode` is `full` (default), `runtime`, or
`context`. `commands` is valid only in runtime mode, is non-empty when present,
and names exported script commands of the provider. Duplicates are rejected.

Each `dependencies.mcp_servers` entry requires a non-empty `hint`, MAY document
`transport` as `stdio` or `http`, and uses `required_in` `any` (default) or
`all`.

If no modern manifest exists, `agents/runtime.json` MAY be read as the legacy
object `{ "commands": { <name>: <portable-relative-path> } }`. Writers MUST
NOT create this legacy form.

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

## 9. Install markers

Every installed closure node has `.csk-install.json` conforming to
`install-marker-v1.schema.json`. `locale` is always present and is a string or
`null`. Required set-like arrays are always arrays, including when empty.

The following arrays are set-like and writers sort them by Unicode scalar
value: `agents`, `commands`, `dependencies`, `files`, `requirements`,
`runtime_roots`, `requirers`, `activation.commands`, and every MCP agent list.
Object member order and whitespace are not significant.

An installation is current only when the marker schema is supported; ref kind,
ref, commit, locale, agents, activation, substitution, MCP findings, and
attestation match the effective plan; and the installed content hash matches
`content_sha256`. Unsupported or unreadable markers are not current. A moved
tag is a warning, or an error under strict-tag policy.

The marker is not a signature and MUST NOT be used as an authorization token.
Registry attestations are reverified from signed records when fresh trust is
required.

## 10. Adapter ledger

Every managed adapter root contains `.csk-managed.json` conforming to
`adapter-ledger-v1.schema.json`. `entries` is a sorted unique list of skill
names owned by the manager in that adapter root. A manager MUST remove only
entries in its preceding ledger and MUST fail rather than overwrite an
unmanaged conflicting entry.
