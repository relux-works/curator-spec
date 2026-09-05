# Environments protocol

This document is normative for the agent-environments capability, revision 1.
It extends, and does not reinterpret, the portable objects in
[`core.md`](core.md) and the manager behavior in
[`../profiles/manager.md`](../profiles/manager.md). It adds new identities and
widens no object defined there. Section references of the form "core §N" name
`core.md`; "manager §N" names the manager profile.

A manager MAY omit this capability entirely and remains a conforming skill
manager. A manager that implements it MUST implement the complete closed
revision-1 surface defined here: partial adapter sets, partial form support,
partial source-kind support, or partial marker semantics are not a
conforming subset. Launcher internals, MCP write management into native
homes, settings fragments, and hooks are outside this document; each returns
under its own review.

This text is the revision-1 rewrite authorized by Decision 0012 (context
packages and semver-locked closures), with the Decision 0013 launch contract
and the pre-implementation review's resolutions folded in. The document stays
revision 1: no implementation claimed the earlier text and no tag carried it.
Only the generation-header type line bumps, to `curator-root-context-v2`, so
that the retired and the replacement vector sets are unambiguous.

**Verified and docs-confidence facts.** Where this document states a tool
fact — a flag spelling, a file the tool reads, a write behavior — the fact is
either **verified**, meaning reproduced on the installed release named in
section 7.9, or **docs-confidence**, meaning recorded from vendor
documentation or source reading and not yet reproduced. A docs-confidence
fact is labeled as such where it is stated and verifies against the pinned
tool release before the conformance vectors that depend on it freeze; it is
never presented as verified. A verified fact that later fails to reproduce is
corrected through the section 7.9 erratum path.

## 1. Environment profiles and sources

An **environment profile** is a named, versioned set of global agent context
installed from a declared source. A profile is exactly: a **root context
package** (section 2), the **lock** that resolution produced for it (section
1.3), and the **machine overlays** declared for it (section 6). Through its
lock a profile carries an ordered root context (section 3), a set of skills
resolved through the unchanged core closure, audit, and runtime machinery,
and a set of MCP declarations (section 2.2) — and no other surface in
revision 1. Surfaces not defined by this revision (settings, prompts,
subagents, hooks, memory, MCP configuration in native homes) MUST NOT be
declared, materialized, or inferred from profile data.

Profile names are portable identifiers under core §2. Comparison is
case-sensitive. Two installed profiles MUST NOT share a name.

The closed set of revision-1 source kinds is:

- **`git`** — a network git source under the core §6.1 canonical identity and
  the core §6.2 git safety rules. The declaration carries exactly one of
  `range`, `tag`, or `revision`. `range` is a version range under section
  1.4 and selects among the source's version tags; `tag` uses the core §6.3
  tag grammar and selects only `refs/tags/<value>`; `revision` is a full
  lowercase commit object id. Branch tracking does not exist for profile
  roots: a moving pointer with no version is what a range expresses better,
  and a repository that tags no versions installs by `--revision` or by a
  non-version `--tag`. A `git` declaration MAY carry `directory`, a portable
  relative path naming the package's directory within the snapshot; absent,
  the package root is the snapshot root. The resolved commit is recorded in
  the lock as the member's pin. Strict-tag policy carries over unchanged: a
  moved tag is a warning, or an error under strict-tag policy (core §10),
  detected at `profile update` (section 9.2) and never at use time.
- **`local`** — reserved for exactly one builtin migration profile per
  machine (section 9.4). A `local` profile has no git identity, no ref, and
  no effective commit; the store key of its synthesized root is the core §8
  content hash of its current state, called its **state hash** below.
- **`path`** — an operator-local package directory named by an absolute
  path, or by a project-relative path when the operation runs inside a
  project. The operand names a directory whose root contains
  `agent-context.json`; the section 2 and section 3 shapes apply unchanged.
  Installation copies the directory's tree into the profile store as an
  immutable snapshot and never reads the source directory again: later
  edits to the source directory change nothing until the operator
  reinstalls, and nothing about a `path` source is ever fetched from a
  network. The snapshot contains only directories and regular files under
  the core §6.2 archive discipline — a symbolic link, hard link, special
  file, or platform path collision in the tree is `profile_source_invalid`.
  A root-level `.git` entry is excluded from the snapshot; a `.git` entry
  anywhere below the root is `profile_source_invalid`. A `path` package
  has no git identity, no ref, and no resolved commit; its store key and
  pin are the core §8 content hash of the snapshot — a state hash, exactly
  the `local` pin shape. Its manifest `version` is authoritative and no tag
  check applies. A `path` declaration that carries `range`, `tag`,
  `branch`, `revision`, or `directory` is `profile_source_invalid`. A
  `path` package serves as a profile root or as an overlay (section 6);
  a package's `requires` (section 2) never names a `path` source.

Profiles are data end to end. No file in a package snapshot is executed,
sourced, or interpreted as configuration for the manager itself. No adapter,
materializer, form, mode, or channel is ever selected by package bytes;
every such selection comes from the closed adapter registry (section 7) and
machine configuration.

### 1.1 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| source kind not `git`, `local`, or `path` | `profile_source_kind_unsupported` |
| invalid canonical identity, ref form, range grammar, or ref grammar; `branch` on any declaration; a ref, range, or `directory` on a `path` declaration; a `path` operand naming a non-directory; a snapshot-tree discipline violation | `profile_source_invalid` |
| `path` operand names no existing filesystem entry | `profile_source_path_missing` |
| `path` operand names a directory that cannot be read | `profile_source_path_unreadable` |
| profile name violates the core §2 grammar | `profile_name_invalid` |
| operation names a profile that is not installed | `profile_unknown` |
| no candidate satisfies a name's effective constraint, or a final constraint is unsatisfied (names every requirer, its range or exact form, and the candidates considered) | `context_range_conflict` |
| manifest `version` differs from the version of the tag the package was resolved from | `context_version_mismatch` |
| root `weights` map names a package also named on a root requirement edge with a weight | `context_weights_duplicate` |
| root `weights` map names a package outside the closure | `context_weight_unknown` |

A missing `path` operand and an unreadable one are different facts (the
section 8.4 discipline): `profile_source_path_missing` never fires on a
failed read, and `profile_source_path_unreadable` never fires on absence.

### 1.2 Snapshot bytes

A snapshot produced from a commit MUST contain, for every regular-file entry
of the commit's tree, exactly the committed blob bytes, and no other entry.
Working-tree conversion (`core.autocrlf`, the `text` and `eol` attributes,
clean/smudge filters, `ident`) and attribute-driven archive processing
(`export-subst`, `export-ignore`) MUST NOT alter, add, or omit any entry: the
snapshot is a function of the commit object graph alone, never of the
acquiring machine's git configuration or of the repository's attributes. This
capability requires it for `git` profile snapshots, for the context modules
they carry, and for the profile-scoped skill snapshots resolved through the
core closure; it is what core §6.2 ("snapshots are immutable regular-file
trees produced from that commit") and core §6.5 ("materialize exact blob
bytes") already require of external-repository snapshots, stated here for the
environments surfaces because this document may not amend core.

Consequently the core §8 content hash of a snapshot, the `path` and `local`
state hash, the effective pin, and every identity bound to one of those
hashes are independent of platform and of git configuration; the section 5.6
cross-platform hash equality rests on this premise.

A `path` snapshot copies the directory's bytes as they are — there is no
commit, and nothing is normalized in either direction: a working-directory
checkout that a `text=auto` conversion left with platform line endings is
snapshotted with those endings.

No diagnostic accompanies this rule. A manager that cannot produce exact
committed bytes has no conforming acquisition path for the commit and MUST
NOT install a snapshot of it.

> Non-normative. Extraction from the object database (`git ls-tree -r` with
> `git cat-file --batch`, or a raw-object reader under core §6.5) satisfies
> the rule; `git archive` does not, because it applies `core.autocrlf`,
> `text`/`eol`, and `export-subst`/`export-ignore` to its output. A manager
> whose skill snapshots come through the same acquisition path as its profile
> snapshots satisfies the rule for both at once. The conformance vector in
> `vectors/snapshot-acquisition.json` commits a tree carrying `* text=auto`,
> an `export-subst` entry, and LF, CRLF, and mixed-ending files, and requires
> the same content hash under `core.autocrlf=true` and `false`.

### 1.3 The lock is the identity

Resolution (section 1.4) produces the profile **lock**: a strict schema-1
object, `context-lock-v1`, naming the root and listing every closure member
— context packages, skills, and MCP declarations, the root and the overlays
among them. Each member records its `kind` (exactly `context`, `mcp`, or
`skill`), `name`, canonical source identity (`source`; absent for a `path`
package) and, when declared, its `directory` within the snapshot; its
resolved `version` (absent for a skill pinned exactly whose source carries
no version tag peeling to that commit); its pin — `commit`, or
`state_sha256` for a `path` package, never both; its effective `weight`
(section 6); its `required_by` list — the sorted names of its direct
requirers, empty for the root and, for an overlay, the sorted names of any
members that also require it; and `overlay`, true
exactly for a machine overlay. Members are sorted by (`kind`, `name`),
bytewise. A `path` member's source path stays in machine configuration and
the environment marker; it never enters the lock, so the lock hash is the
same on every machine that locks the same bytes.

The lock is machine state below the manager home, never repository content.
Its CCJ-1 bytes ([`registry.md`](registry.md) §1) hashed with SHA-256 are
the **lock hash**, spelled `sha256:<64 lowercase hex>`. The lock hash is the
profile's **effective pin** everywhere this document binds a profile to an
identity: the generation header (section 5.1), the environment marker
(section 8.2), the launch fragment (section 10.2), `profile list` (section
12), and the `ax` extension key that records the profile pin
(`works.relux.curator.profile-pin`, Decision 0013 Decision 6.4).

`profile install` resolves and writes the lock; `profile update` re-resolves
and writes a new lock only when the new closure passes the always-strict
audit of section 9.1 in full (section 9.2). Nothing re-resolves implicitly:
`profile use`, `profile sync`, `env resolve`, and status read the lock they
find.

The lock is a record, not a signature: it MUST NOT be used as an
authorization token or provenance proof (core §10 discipline).

### 1.4 Versions, ranges, and resolution

**Versions.** Version tags are strict Semantic Versioning 2.0 with a
mandatory `v` prefix: `v<major>.<minor>.<patch>[-<prerelease>]`, under the
core §6.3 tag grammar. Build metadata is not admitted: a tag carrying
`+<build>` is not a version candidate. A tag that does not parse is not a
version candidate and is silently outside every range; it remains
addressable by the exact `tag` form. Versions are totally ordered by the
SemVer 2.0 precedence rule (`1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-beta <
1.0.0`). Because build metadata is excluded and tag names are unique within
a repository, no two candidates of one source share a version, so "the
highest satisfying candidate" is always unique.

**Ranges.** The range grammar is closed. Its semantics are those of
node-semver (the npm implementation; README sections "Caret Ranges", "Tilde
Ranges", "X-Ranges", "Prerelease Tags", recorded against 7.7.4), restricted
as stated. A range is one or more **comparator sets** joined by `||`; a
candidate satisfies the range when it satisfies any set. A comparator set is
one or more primitives joined by whitespace; a candidate satisfies the set
when it satisfies every primitive. Primitives:

- an exact version `1.2.3` (equivalent to `=1.2.3`);
- a comparator `>=`, `>`, `<=`, `<`, or `=` followed by a version or a
  partial version;
- a caret range `^<version-or-partial>`;
- a tilde range `~<version-or-partial>`;
- an x-range: a partial version (`1`, `1.2`) or one with `x`, `X`, or `*`
  in a component (`1.x`, `1.2.x`); the bare `*`, `x`, or `X` matches every
  stable version.

Partial versions coerce as node-semver coerces them: a partial names the
interval of the versions that complete it, so `1.2` and `=1.2` mean
`>=1.2.0 <1.3.0-0`; `>=2.1` means `>=2.1.0`; `>1.2` means `>=1.3.0`;
`<3` means `<3.0.0-0`; `<=1.2` means `<1.3.0-0`. A caret admits every
change that does not alter the leftmost non-zero component of
`major.minor.patch`: `^1.2.3` is `>=1.2.3 <2.0.0-0`; `^0.2.3` is
`>=0.2.3 <0.3.0-0`; `^0.0.3` is `>=0.0.3 <0.0.4-0`; with fewer components
the missing ones are free — `^1.4` is `>=1.4.0 <2.0.0-0`, `^0.1` is
`>=0.1.0 <0.2.0-0`, `^0` is `>=0.0.0 <1.0.0-0`. A tilde admits patch
changes when a minor is given and minor changes when it is not: `~1.2.3`
is `>=1.2.3 <1.3.0-0`, `~1.2` is `>=1.2.0 <1.3.0-0`, `~1` is
`>=1.0.0 <2.0.0-0`. Every exclusive upper bound produced by these rules is
spelled `<X.Y.Z-0` — the lowest prerelease of the bound — so that a
prerelease of the bound version falls outside it: `v3.0.0-rc.1` does not
satisfy `<3`, and `latest` never lands on it.

Two npm forms are excluded: hyphen ranges (`1.2.3 - 2.3.4`) are not
admitted, and `v` is not admitted inside a range — a range is over
versions, a tag carries the prefix. The spelling `latest` is a Curator
spelling equivalent to `*`. `*`, `x`, `X`, and `latest` select the highest
**stable** version. A range that does not parse is `profile_source_invalid`.

**Prereleases.** A version with a prerelease satisfies a range only when
some primitive of a satisfied comparator set names a prerelease on the same
`major.minor.patch`: `2.0.0-rc.1` satisfies `^2.0.0-rc.0` and
`>=2.0.0-rc.0`; `2.1.0-rc.1` satisfies neither; `2.0.0-rc.1` satisfies none
of `*`, `>=1.0.0`, `<3`. An operator who wants a prerelease names one. There
is no machine-wide prerelease admission switch in revision 1.

**Resolution.** Resolution is the core §7 closure with its admission rule
generalized from exact refs to constraints. Every requirement on one
package name MUST agree on the canonical source identity (unchanged). A
requirement contributes a **constraint**: a `range` as written; an exact
`tag` or `revision` as a fixed candidate. The **effective constraint** of a
name is the intersection of every current constraint on it; an exact
constraint fixes the name's only candidate — that commit, carrying the
version section 2 defines (the manifest `version` for context and MCP
packages; for a skill, the version of the highest version tag of its source
that peels to that commit, or no version) — and every range on the name
MUST admit that version. Two exact constraints on one name MUST peel to one
commit (core §7, unchanged; different refs resolving to one commit unify).
The candidates of a name are the source's version tags, peeled under core
§6.3.

The algorithm is fixed so that two managers lock identically:

1. **Seed.** The constraint set holds the root's install declaration
   (section 9.1) and every overlay declaration (section 6), each attributed
   to the machine; the root and each overlay are pending names.
2. **Select and expand.** While a pending name exists, take the
   lexicographically smallest (Unicode scalar value order, as core §7).
   Compute its effective constraint; if no candidate satisfies it — an
   empty intersection, a source whose version tags all fall outside it, or a
   source with no version tags — fail `context_range_conflict` naming every
   requirer with its range or exact form and the candidate versions
   considered. Select the highest candidate satisfying it — for a `||`
   disjunction, the highest candidate satisfying any member — and expand the
   manifest at that commit: every requirement it declares is added to the
   constraint set, attributed to this name at this version, and every name
   whose constraint set changed becomes pending.
3. **Re-select downward.** When an added constraint excludes the currently
   selected version of an already-expanded name, that name is re-selected
   to the highest remaining candidate not above its previous selection;
   every constraint attributed to its previous selection is dropped, and
   the name is re-expanded. A member left with no constraint — no
   requirer — leaves the closure with everything it contributed. A name's
   selection never increases within one resolution, even when the
   constraint that lowered it is later dropped, and a name that re-enters
   after leaving re-enters at or below its last selection. Selections
   therefore only decrease and the candidate sets are finite, so the loop
   terminates.
4. **Check.** Every constraint in the final set MUST be satisfied by the
   selected version of the name it constrains, else `context_range_conflict`
   naming every requirer of that name and its range or exact form.

No backtracking across names is performed: the manager never revisits one
name's selection to make another name's constraint satisfiable, and a
closure that has a solution only under such a search fails with the
conflict rather than searching. After resolution the core §7 invariant holds
unchanged: one name, one commit. A cycle among context packages fails and
names the cycle (core §7).

**Skills in the closure.** Skill requirements from context packages carry
ranges and resolve by exactly the rule above, jointly with every other
skill requirement of the closure — including a skill manifest's own exact
`dependencies.skills` (core §4.4), which enter as fixed candidates, and the
direct machine declarations of section 9.4. The requirement-edge semantics
of core §7 (activation modes, command narrowing) are unchanged. Project
`Skillfile.json` and the skill manifest keep core §4.4 unchanged: no range
enters a surface that has no lock.

## 2. Context package shape

A **context package** is a git snapshot, or a directory within one named by
`directory`, or a `path` directory, whose root contains `agent-context.json`,
a strict schema-1 object:

```json
{
  "schema_version": 1,
  "name": "companyA-root-context-ios-developer-umbrella",
  "version": "2.3.0",
  "weight": 100,
  "context": {
    "modules": [
      { "path": "00-ios-umbrella.md" },
      { "path": "90-ios-system.md", "class": "system", "environments": ["claude_code"] }
    ]
  },
  "requires": {
    "contexts": {
      "companyA-root-context-core":             { "git": "…", "range": "^3.0" },
      "companyA-root-context-developers-core":  { "git": "…", "range": "^1.4" },
      "companyA-root-context-developers-ios":   { "git": "…", "range": ">=2.1 <3", "weight": 60 },
      "companyA-root-context-developers-figma": { "git": "…", "directory": "contexts/figma", "range": "^1.0", "weight": 40 }
    },
    "skills": {
      "swiftui": { "git": "…", "range": "^4" },
      "pdf":     { "git": "…", "range": "~1.2" }
    },
    "mcp": {
      "figma-devmode": { "git": "…", "range": "^1" }
    }
  },
  "weights": {
    "companyA-root-context-organizational-structure": 10
  }
}
```

Validation is strict under core §1: readers MUST reject duplicate keys,
unknown fields at every level, invalid UTF-8, and a `schema_version` other
than `1`.

- **`name`** (REQUIRED) is a portable identifier (core §2) and MUST equal the
  name every requirer uses for it.
- **`version`** (REQUIRED) is a strict semantic version without the `v`
  prefix (section 1.4). For a package resolved from a version tag — by range
  or by an exact version-shaped `tag` — `version` MUST equal that tag's
  version, else `context_version_mismatch`. For a package pinned by
  `revision` or by a tag that is not a version, the manifest `version` at
  that commit is the package's version. For a `path` package the manifest
  `version` is authoritative and no tag check applies.
- **`weight`** (OPTIONAL) is a non-negative integer at most 2147483647,
  default `0`: the package's own default precedence weight (section 6).
  **`weights`** (OPTIONAL) maps package names to weights and is meaningful
  only in the root package (section 6).
- **`context`** (OPTIONAL) carries the module manifest of section 3. `context`
  MAY be absent: a package with no modules of its own is a pure umbrella and
  declares no root-context surface — materialization writes no root-context
  file for a profile whose root has no `context` (this is distinct from a
  `context` with zero applicable modules, section 5.4). When `context` is
  present the package root MUST contain the `context/` directory the
  modules live in.
- **`requires`** (OPTIONAL) names other context packages (`contexts`),
  skills (`skills`), and MCP declaration packages (`mcp`); each is an
  OPTIONAL object keyed by package name. Every entry carries a canonical
  `git` source (core §6.1) and exactly one of `range` (section 1.4), `tag`,
  or `revision` (the core §4.4 exact forms). A context or MCP requirement
  MAY carry `directory`, a portable relative path naming the package's
  directory within the snapshot — spelled `directory` so that it is never
  confused with the `path` source kind of section 1, which is an
  operator-local directory. A skill requirement carries no `directory`: a
  skill package is addressed exactly as core §4.4 addresses it, and `mode`
  and `commands` keep their core §4.4 meaning. A context requirement MAY
  carry `weight` to override the required package's own default (section 6).
- **`CONTEXT.md`** at the package root is informative and never
  materialized. Files not named by the manifest are inert: they participate
  in snapshot identity and audit and are never materialized.

There is no umbrella kind. Any context package with `requires.contexts` is
an umbrella; any context package — umbrella or not — installs as a root. A
role umbrella whose modules are empty is a valid, common shape. Discovery by
directory layout does not exist: a directory without `agent-context.json` at
the addressed root is not a context package.

### 2.1 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| `agent-context.json` absent at the addressed root, malformed, unknown field, wrong `schema_version`, invalid `name`, `version`, `weight`, `weights`, or `requires` entry; `context` present without `context/` | `context_manifest_invalid` |
| `agent-mcp.json` absent at the addressed root, malformed, unknown field, wrong `schema_version`, or a `server` rule of section 2.2 violated | `mcp_declaration_invalid` |
| an MCP declaration package's canonical source identity is outside the machine's MCP package allowlist | `mcp_package_not_allowed` |

`profile_index_invalid`, `profile_root_invalid`, and
`profile_context_manifest_invalid` are withdrawn with the `Profilefile.json`
shape they described; no implementation ever emitted them.

### 2.2 MCP declaration packages

An **MCP declaration package** is a third package kind on the same
machinery: a git snapshot, or a directory within one, whose root contains
`agent-mcp.json`, a strict schema-1 object:

```json
{
  "schema_version": 1,
  "name": "figma-devmode",
  "version": "1.2.0",
  "server": {
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "figma-developer-mcp", "--stdio"],
    "env_names": ["FIGMA_API_KEY"],
    "environments": ["claude_code", "codex_cli", "opencode"]
  }
}
```

`name` and `version` follow section 2. `transport` is exactly `stdio` or
`http`. `stdio` carries `command` and `args`: `command` MUST be a bare
executable name — no path separator, no absolute or relative path — that
the tool resolves on `PATH` at launch; anything else is
`mcp_declaration_invalid`. `http` carries `url`, which MUST use the `https`
scheme with an ASCII host and MUST carry no userinfo, query, or fragment.
`args` and `url` are inside the `context-secret-material` detector scope
(section 9.1): a token in an argument or a URL is a blocking finding like a
token in a module. `env_names` lists environment-variable **names** the
server expects at run time; each MUST match the core §2 identifier grammar
and MUST NOT name a manager-reserved variable — the union of every manager
§3.1 reserved set across platforms and interpreter identifiers (`PATH`,
`HOME`, the `LD_`, `DYLD_`, `NODE_`, `NPM_CONFIG_`, and `PYTHON` families,
and the rest) — and machine configuration MAY bound the passable names
further by the lockable `passable_env_names` allowlist (section 12.1).
Values never appear in any package, lock, marker, fragment, or materialized
file; the operator's environment supplies them. `environments` is the
section 3 selector: the adapters whose materialized set includes this
server; absent means every adapter.

The manager never executes, installs, updates, or launches a server. It
verifies, read-only, that a `stdio` command resolves on the operator's
`PATH` and warns `mcp_command_unresolved` when it does not — the manager §6
discipline — and it audits the package like any other. Policy is the
machine's MCP package allowlist: canonical source identities under core
§6.1 segment-aware matching, lockable by system configuration, bounding
which declaration packages a profile may resolve; a package outside it is
`mcp_package_not_allowed` at resolution. The allowlist is over packages, not
launcher binaries, because a binary allowlist bounds nothing: `npx`, `uvx`,
`node`, or `sh` admit any program through `args`. An empty allowlist permits
every network identity, as core §6.1.

## 3. Context modules

The `context` member of `agent-context.json` carries the module manifest:

```json
{
  "modules": [
    { "path": "00-base.md" },
    { "path": "10-style.md" },
    { "path": "20-claude.md", "environments": ["claude_code"] },
    { "path": "90-system.md", "class": "system" }
  ]
}
```

Readers MUST reject duplicate keys and unknown fields at either level.
`modules` is REQUIRED and MAY be empty. Each entry carries:

- **`path`** (REQUIRED) — a portable relative path (core §2) naming a
  regular file below `context/`. Paths are unique across the manifest; a
  duplicate is rejected.
- **`environments`** (OPTIONAL) — a non-empty set-like array of unique
  environment identifiers under the core §2 grammar. An absent selector
  means every environment. An identifier that is not in the machine's
  adapter registry is permitted, produces the warning
  `profile_selector_unknown_environment` at snapshot validation, and selects
  nothing — the manager §5 unknown-identifier discipline.
- **`class`** (OPTIONAL) — exactly `root` or `system`; the default is
  `root`. `system` marks the module as system-prompt content under sections
  5.5 and 7.3.

A module is UTF-8 markdown. Snapshot validation MUST reject a module that is
not valid UTF-8, contains any line ending other than LF, or does not end
with exactly one trailing LF, with `profile_module_bytes_invalid`. There is
no normalization path: a violating module fails the snapshot, it is never
rewritten. A module that validates is thereafter opaque bytes;
materialization MUST reproduce it exactly and MUST NOT apply templating,
variable substitution, inclusion, transcoding, or any other transformation.

A module **applies** to an environment when its selector is absent or
contains that environment's identifier. The **applicable root modules** of a
package for an environment are its `class: root` modules that apply, in
manifest order; the **applicable system modules** are its `class: system`
modules that apply, in manifest order.

### 3.1 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| module manifest malformed, unknown field, duplicate or invalid entry | `context_manifest_invalid` |
| declared module file absent or not a regular file | `profile_module_missing` |
| module not UTF-8, non-LF line ending, or trailing-LF violation | `profile_module_bytes_invalid` |
| selector names an unregistered environment (warning) | `profile_selector_unknown_environment` |

## 4. Profile store

Every closure member has exactly one store entry below the manager home,
keyed by its pin: the resolved commit for a `git` package, the state hash
for a `path` package or the synthesized `local` root. Store entries are
immutable regular-file trees. Two profiles whose locks name the same member
at the same pin share its entry — the runtime-store pattern. A profile's
store identity is the set of entries its lock names. Every materialization
mode of section 8 — `managed-home`, `linked`, and `copied` — materializes
from the same lock's store entries, so the modes cannot diverge for one lock
hash. Physical store paths are implementation-specific (manager §1); the
store joins garbage collection under section 12.

## 5. Deterministic materialization

Materialized root context is a pure function of (lock, precedence policy,
environment identifier, form). Identical inputs MUST yield byte-identical
output on every platform and in every mode. The rules below define the
exact bytes; they are a determinism conformance-vector surface.

**Platform-path collisions.** Protocol paths compare case-sensitively (core
§2); platform paths may not. Any materialization or provisioning step that
would write two protocol paths mapping to one platform path — module files
of closure members whose names or manifest paths fold together on a
case-insensitive filesystem, managed homes for two such profile names
(section 8.1), backup paths (section 8.3) — MUST detect the collision and
fail with `environment_path_collision` before writing anything: the core §2
extraction rule, extended to every materialization and provisioning write
path.

**Parts and joining.** Output is assembled from ordered **parts**. Every
part is a byte string ending with exactly one LF. The document is the parts
joined with exactly one additional LF between adjacent parts — one empty
line — and nothing else. Because every part ends with exactly one LF, the
output is LF-encoded and ends with exactly one trailing LF by construction.

**Emitted order.** The lock's `context` members are sorted by effective
weight under the precedence policy of section 6: ascending weight under
`winner=higher-weight` and descending under `winner=lower-weight` when
`placement=winner-last`; the reverse when `placement=winner-first`, so the
prevailing end of the order is emitted last or first as declared. Members
of equal weight keep their relative core §7 topological order in every
case; the root participates in that order as an ordinary node, and
`placement` never inverts a tie. This is the **emitted order**, and it is
the order of the header's `member:` lines and of the chapters.

The part sequence for a root-context document is:

1. the generation header (section 5.1);
2. for each `context` member in emitted order that has at least one
   applicable root module — a chapter part, then that member's applicable
   root modules in manifest order. A member with no applicable root module
   contributes no chapter and no part; a pure umbrella therefore appears in
   the header and nowhere else.

A **chapter part** is exactly the bytes
`---` LF LF `## Context: ` `<name>` ` ` `<version>` LF — a thematic-break
line, one empty line, and a heading naming the member and its resolved
version:

```text
---

## Context: <name> <version>
```

No pin, path, weight, or other data appears in a chapter part.

**Size advisory.** Each adapter records a `root_context_size_advisory_bytes`
value (section 7.9). When the assembled root-context document exceeds it,
materialization and `env status` warn `environment_context_size_exceeded`
naming the adapter, the byte count, and the advisory; the bytes are still
written exactly, and the warning changes nothing about them. The advisory
exists because a tool that truncates its instructions file truncates the
precedence-winning chapters first under `placement=winner-last`, and no
byte rule can detect that from the outside.

### 5.1 Generation header

Every materialized root-context file begins with the generation header, an
HTML comment that markdown renderers do not display. Its grammar is closed;
a writer MUST emit exactly these lines in exactly this order, each
terminated by one LF:

```text
<!--
curator-root-context-v2
root: <name> <version> <pin>
member: <name> <version> <pin> weight <n>
member: <name> <version> <pin> weight <n> overlay
precedence: winner=<winner> placement=<placement>
lock: sha256:<64 lowercase hex>
generated: Curator Protocol environments revision 1 (https://github.com/relux-works/curator-spec)
notice: generated file; direct edits are unsupported and are detected as drift; update the source profile repository or its composed profiles instead
-->
```

- `<pin>` is `commit <full-hex>` — the full lowercase commit — for a `git`
  package, or `state sha256:<64 lowercase hex>` for a `path` package or the
  synthesized `local` root. The pin grammar is closed at these two
  spellings, and no source-kind information enters the header.
- The `root:` line names the root package, its resolved version, and its
  pin, and appears exactly once.
- One `member:` line per `context` member of the lock — with or without
  applicable modules, the root included — in emitted order (section 5),
  each carrying the member's resolved version, pin, and effective weight
  `weight <n>` in shortest base-10 form, with ` overlay` appended exactly
  when the member is a machine overlay. Skill and MCP members appear in the
  lock, not the header.
- The `precedence:` line states both primitives of section 6 exactly as
  `winner=<higher-weight|lower-weight> placement=<winner-last|winner-first>`
  and appears exactly once.
- The `lock:` line carries the lock hash of section 1.3 and appears exactly
  once.
- The `generated:` and `notice:` lines are the fixed byte strings above.

The header contains no timestamp, machine path, operator identity, hostname,
or locale. Nothing else may be added: an unknown header line is a
conformance failure, not an extension point.

### 5.2 Monolithic form

In the `monolithic` form each applicable root module contributes one part:
its exact validated bytes. The output is one file at the adapter's declared
root-context target (section 7.1). Every adapter supports `monolithic`.

### 5.3 Referenced form

In the `referenced` form the applicable root modules materialize as
individual files that the root file references through the tool's native
mechanism. The layout is fixed:

- Module files land below the managed directory `.agent-context/modules/`
  beside the root-context file, grouped per source package:

  ```text
  <home>/.agent-context/modules/<package-name>/<module-path>
  ```

  `<module-path>` is the module's manifest `path` verbatim. Grouping by
  package name makes two closure members carrying the same module filename
  collision-free in protocol-path space; within one package, manifest paths
  are unique by section 3. Where a platform filesystem folds two of these
  protocol paths to one platform path, the section 5 collision rule fails
  the materialization before writing. The literal path segment `modules`
  is fixed and is not a package name, so no package-name value can collide
  with the sibling `system-prompt.md` of section 5.5 or the sibling `mcp/`
  directory of section 5.8.

- Each materialized module file is the module's exact bytes. No header,
  chapter, or reference line is added to a module file.

- The root file is assembled by the section 5 part rules, with each module
  part replaced by that module's **reference part** — for `claude_code`, the
  single line:

  ```text
  @.agent-context/modules/<package-name>/<module-path>
  ```

  Chapter parts and the generation header are unchanged. The tool's
  approval rule (**verified** from the 2.1.261 bundle): an `@path` target
  that resolves **inside** the launch directory needs no approval; a
  target that resolves **outside** it is loaded only when the managed
  `.claude.json` project entry for that launch directory sets
  `hasClaudeMdExternalIncludesApproved: true`, otherwise it is dropped
  silently — the interactive dialog is what sets the key, and `-p` never
  asks. The managed home is never the launch directory, so every reference
  above is an external include: the `referenced` form for `claude_code`
  therefore requires the project entry of section 7.4 carrying that key
  for the launch directory, and a home lacking it for the launch directory
  is stale (section 10.1). That the referenced content then reaches the
  model is not observable without a logged-in run and **requires an
  operator** before the referenced-form vectors freeze.

- For `opencode`, the tool's reference mechanism is the `instructions` array
  of `<home>/opencode.json`, not root-file syntax. The root file is the
  generation header part alone. The managed `opencode.json` is fully
  manager-authored and its bytes are exact: the CCJ-1 bytes
  ([`registry.md`](registry.md) §1) of the object whose single member,
  `instructions`, is the ordered list of
  `.agent-context/modules/<package-name>/<module-path>` values in exactly
  the order the modules would appear monolithically — no other member —
  followed by exactly one trailing LF. The `opencode.json` surface is then
  a managed surface recorded in the environment marker. When
  `<home>/opencode.json` exists and is not recorded by the preceding
  marker, the referenced form is unavailable: the adapter
  MUST warn `environment_form_unavailable` and materialize `monolithic`
  instead — it MUST NOT edit the unmanaged file.

  Consequence, stated so that it is chosen and not discovered: a
  referenced-form managed `opencode` home carries no other `opencode.json`
  configuration — no provider, theme, or keybind member — because the file
  is manager-authored and an edit is drift that `repair` reverts. The
  profile's MCP set does not need that file: it reaches the tool through
  the section 7.8 `OPENCODE_CONFIG` channel, whose file is separate. Where
  the operator needs other tool configuration in a managed `opencode` home,
  the `monolithic` form is the supported shape. A manager-authored
  `instructions` member inside an otherwise operator-owned file is not
  possible under the section 8.3 ledger discipline and is not offered.

The effective form per environment is chosen by machine configuration with
the adapter's default (section 7.2), never by profile data. When the
configured form is unavailable — the tool gates it, or an unmanaged file
blocks it — the adapter falls back to `monolithic` with
`environment_form_unavailable`; it never fails the operation for form
availability alone.

### 5.4 Zero applicable modules

A root-context materialization whose applicable module set is empty produces
the header part alone. Empty output (zero bytes) never occurs, the file is
always written, and a zero-module materialization is valid, not an error.
Chapters exist only for members with applicable modules, so a lock whose
members all lack applicable modules for an environment yields the header
and nothing else. In the referenced form no module files are materialized
and, for `opencode`, the managed `instructions` array is empty. This is
distinct from a profile whose root declares no `context` (section 2), for
which no root-context surface exists and no file is written.

### 5.5 System-prompt output

The applicable system modules — of every `context` member in emitted order
— materialize as one file assembled by the part-joining rule with **no
generation header and no chapter parts**: system-prompt bytes reach the
model verbatim, so no generated text is injected. Provenance and drift
detection for this surface come from the environment marker's recorded
content hash, not from an in-file header.

The system output materializes only into managed homes (section 8.1), at:

```text
<home>/.agent-context/system-prompt.md
```

This file is inert: no revision-1 tool reads that path natively. It exists
so the launch fragment (section 10.2) can name it. When the lock carries no
applicable system modules, the file is absent and the fragment carries no
system-prompt section. The `.agent-context/` directory also carries the
`mcp/` sibling of section 5.8.

For `pi` only, machine configuration MAY additionally set, per
profile × environment, `system_prompt_files` to exactly `off` (default),
`append`, or `replace`. `append` materializes the system output additionally
at `<home>/APPEND_SYSTEM.md`; `replace` materializes it at
`<home>/SYSTEM.md`. Both are live channels the tool applies unconditionally
when present (section 7.3), so under `off` neither file is written and a
plain launch of a managed home carries no active system prompt. System
modules MUST NOT materialize into a native in-place home in any mode, and
secondary fixed-home targets (section 7.6) never receive system modules in
revision 1.

### 5.6 Content-hash binding

Every materialized surface binds a content hash recorded in the environment
marker (section 8.2). The surface hash is the core §8 content hash over the
surface's materialized file set, where each file's protocol path is its
home-relative portable path. For a single-file surface this degenerates to
one record; for the referenced form the set contains the root file, every
materialized module file, and — for `opencode` — the managed
`opencode.json`; for a managed home the section 5.8 MCP file is its own
surface. Identical (lock, precedence policy, environment, form) MUST yield
an identical surface hash on every platform; this equality is a
conformance-vector surface.

### 5.7 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| configured form unavailable; monolithic emitted (warning) | `environment_form_unavailable` |
| materialization would overwrite a file the marker does not record | `environment_surface_unmanaged_conflict` |
| two protocol paths to be written map to one platform path | `environment_path_collision` |
| assembled root-context document exceeds the adapter's size advisory (warning) | `environment_context_size_exceeded` |
| a `stdio` MCP server's `command` does not resolve on the operator's `PATH` (warning; reported at resolution and audit, section 9.1, not at materialization) | `mcp_command_unresolved` |

### 5.8 MCP launch-channel output

The resolved MCP set of a profile for an adapter — the lock's `mcp` members
whose `environments` selector applies to that adapter — materializes as one
inert, hashed, marker-recorded file per adapter, in a managed home only.
It never materializes into a native in-place home, whose MCP configuration
lives in tool-owned mutable state, and never into a secondary fixed-home
target. The file location is below `<home>/.agent-context/mcp/` except
where the tool fixes the location:

| Environment | File | Bytes |
|---|---|---|
| `claude_code` | `<home>/.agent-context/mcp/claude_code.json` | CCJ-1 bytes of the object whose single member `mcpServers` maps each server name to `{"args": [...], "command": "<command>", "type": "stdio"}` for `stdio`, or `{"type": "http", "url": "<url>"}` for `http`; followed by exactly one LF |
| `codex_cli` | `<home>/curator-mcp.config.toml` | the TOML document whose only table is `mcp_servers`, one `[mcp_servers.<name>]` table per server in sorted name order — `<name>` emitted as a TOML bare key, which the core §2 identifier grammar guarantees needs no quoting — each carrying `command = "<command>"` and `args = ["a", "b"]` for `stdio` (elements as TOML basic strings separated by exactly `", "`, the empty list as `[]`), or `url = "<url>"` for `http`, keys in that order, one key per line, LF line endings, exactly one trailing LF, and no other bytes |
| `opencode` | `<home>/.agent-context/mcp/opencode.json` | CCJ-1 bytes of the object whose single member `mcp` maps each server name to `{"command": ["<command>", ...args], "type": "local"}` for `stdio`, or `{"type": "remote", "url": "<url>"}` for `http`; followed by exactly one LF |
| `pi` | none — no file and no fragment `mcp` section | — |

No `env` member, no value, and no operator-supplied byte ever enters a
materialized MCP file: the fragment carries the `env_names` union (section
10.2) and the operator's environment supplies values at launch. Where the
resolved set for an adapter is empty, no file is written and the fragment
carries no `mcp` section. The trailing-LF rule is the same rule section 5.3
applies to the managed `opencode.json`. The per-adapter server-object
shapes for `claude_code` and `opencode` are recorded from vendor
documentation and are **docs-confidence**; the `codex_cli` layer file is
**verified** on 0.153.2 — a file whose only table is `mcp_servers` is
applied through `-p` and its servers appear in `codex mcp list` (section
7.8). Each docs-confidence shape verifies against the pinned release
before the MCP byte vectors freeze. `codex_cli`'s fixed location makes `curator-mcp.config.toml`
a reserved name inside every managed `codex_cli` home, recorded in the
marker like every other managed surface.

## 6. Composition

A machine MAY declare, per installed profile, an ordered list of
**overlays**. An overlay is an ordinary context package named by a `git`
source with a range or exact form, or by a `path` source under the section
1 rules — a personal repository or a local directory on the machine. The
declaration lives in machine configuration only; package data MUST NOT
declare, request, or alter composition. An overlay is not a distinct
package shape.

Each overlay declaration carries a machine-assigned weight, default the
machine's `overlay_default_weight` (section 12.1), initially `1000` — above
the weights roots use in practice, so that personal refinements prevail
under the default policy. Overlays **join the closure**: resolution (section
1.4) seeds them beside the root, their own requirements resolve jointly with
the root's, and an overlay that needs a skill version the root forbids is a
reported `context_range_conflict`, never a silent second copy. The lock
records overlays as members flagged `overlay`. An overlay declaration naming
an uninstallable or unreadable source fails resolution with the section 1.1
diagnostic of that source; a declaration that repeats a name already in the
closure by another declaration is `environment_composition_invalid`.

**Effective weight.** Every closure member has one effective weight,
computed by exactly these rules in order, each overriding the previous:

1. the member's manifest `weight`;
2. the `weight` declared on the requirement edge by its direct requirers.
   When several direct requirers declare an edge weight for one member they
   MUST agree, else `context_weight_conflict` naming every requirer and its
   value — unless rule 3 names the member, in which case the root has the
   final word and the disagreement is reported as a warning under the same
   diagnostic;
3. the root package's `weights` map. The root's own edge weights are
   treated as entries of this map; a package named both on a root edge and
   in the map is `context_weights_duplicate` (section 1.1). A `weights`
   entry naming a package outside the closure is `context_weight_unknown`
   (section 1.1);
4. for a machine overlay, the weight the overlay declaration assigns —
   machine configuration outranks repository content, so a package that is
   both an overlay and a requirement takes the overlay's weight.

`weights` is meaningful only in the root. A non-root member whose manifest
carries a non-empty `weights` map is `context_weights_not_root` at
resolution time — snapshot validation stays position-independent — so a
package authored as a root MAY be reused as a dependency exactly when its
map is empty or absent.

**Precedence policy.** Weights order chapters and nothing else in this
revision. They never merge instruction text and they never resolve a
version constraint: an empty range intersection fails regardless of
weights. Machine configuration declares the precedence policy as two
independent, closed primitives:

- `winner`: `higher-weight` (default) or `lower-weight` — which side of a
  weight comparison prevails;
- `placement`: `winner-last` (default) or `winner-first` — whether the
  prevailing material is emitted last or first in the materialized root
  context.

The default pair reproduces the earlier `later-overrides-earlier` reading;
either primitive may be changed without the other. Section 5 fixes the
emitted order. Instruction text cannot be merged mechanically: precedence
is declared to the reader and the agent — in the generation header (section
5.1) and the chapter structure — never resolved silently by the manager.

**Skills and MCP under composition.** Skill and MCP composition is joint
resolution, not a union: every chain member's requirements enter one
constraint set (section 1.4), so two members requiring one skill either
unify on one commit or fail with `context_range_conflict` naming both. There
is no "precedence favors one declaration" rule for skills and no divergence
warning — a divergence is now a conflict or a unification. The lockable
composition policy of section 12.1 (`overlays_allowed`) lets a machine
forbid overlays entirely.

**What composition does not cover.** Composition orders context members and
resolves skills and MCP declarations. It does not compose agent lists or
locale: a context package declares no `agents` and no `locale`, and the
manager §1 machine preferences (`agents`, `preferred_locale`) apply to a
profile's skill closure exactly as they apply to the global scope today —
one machine preference, never a per-member value. Hybrid manifests (manager
§4.3) are project-side declarations and never compose with a profile; the
scope precedence is fixed in section 9.4. A later revision that admits a
per-package `agents` or `locale` member does so under its own review.

The lock, and through it the generation header, the environment marker, and
the launch fragment, record every member with its weight and the precedence
primitives, so status, drift detection, and session resume always see
exactly what was assembled.

### 6.1 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| overlay declaration repeats a closure name already declared, or is otherwise not a valid overlay declaration | `environment_composition_invalid` |
| direct requirers disagree on a member's edge weight (error; warning when the root's `weights` map names the member) | `context_weight_conflict` |
| non-root member carries a non-empty `weights` map | `context_weights_not_root` |

`environment_composition_skill_divergence` is withdrawn: under joint
resolution the condition it described is `context_range_conflict` or a
unification.

## 7. Environment adapter registry

The manager §5 agent-adapter table generalizes to a closed **environment
adapter registry**. Adapters are manager code, never package code. Admitting
a new adapter is a specification revision with its own review — the core
§12.3 closed-set discipline. An environment identifier not in the registry
keeps the manager §5 behavior: a warning and no output, except where a
section below requires an error for an explicit operand.

### 7.1 Revision-1 adapters

The closed revision-1 adapter set is exactly:

| Environment | Home mechanism | Home shape | Root-context target | Skills target |
|---|---|---|---|---|
| `claude_code` | `CLAUDE_CONFIG_DIR=<home>` | variable names the home | `<home>/CLAUDE.md` | `<home>/skills/` |
| `codex_cli` | `CODEX_HOME=<home>` | variable names the home | `<home>/AGENTS.md` | `<home>/skills/` |
| `opencode` | `XDG_CONFIG_HOME=<parent>` | tool reads `<parent>/opencode/` as the home | `<home>/AGENTS.md` | the manager §5 native surface (`~/.agents/skills`), unchanged in revision 1 |
| `pi` | `PI_CODING_AGENT_DIR=<home>` | variable names the home | `<home>/AGENTS.md` | `<home>/skills/` |

`gemini`, `cursor`, and `windsurf` remain skills-only adapters under the
unchanged manager §5 table in revision 1. Tools with no home-isolation
mechanism are out of scope.

`XDG_CONFIG_HOME` is a generic XDG variable: every XDG-conforming child of a
launched `opencode` session resolves configuration under the managed parent.
Revision 1 accepts and narrows this: when a managed `opencode` parent is
provisioned, the manager seeds it with symlinks to the entries of the
operator's effective XDG config home that the machine's `xdg_seed_allowlist`
(section 12.1) names and that exist — never `opencode/`, and never an entry
the allowlist does not name. The default allowlist is `git`, `gh`, and
`ssh`; an organization widens or narrows it per machine. Seed links are
recorded in the environment marker. **Reconciliation** runs on `profile
sync`, `profile use`, and `env resolve --repair` against the operator's
current XDG config home: an allowlisted entry newly present is seeded and
recorded; a recorded seed whose target no longer exists is removed; an
entry in the managed parent that the marker does not record is never
touched — where such an entry shadows an allowlisted operator entry, the
condition is reported as `environment_seed_shadowed` and left as it is.
`XDG_DATA_HOME` and `XDG_STATE_HOME` are **ambient**: the manager never
sets, seeds, or manages them, so opencode's authentication state and every
XDG data or state file stay the operator's own on every launch. A dedicated
opencode home variable, should the vendor ship one, supersedes the XDG
mechanism in a later revision.

Because the `opencode` skills target is the machine-global native surface, a
managed `opencode` home is **split-brain by construction**: a session
launched into profile A's managed home reads profile A's root context and
the machine-current profile's skills. This is not a scoped switch and no
switch-visibility rule surfaces it, so `env status` carries a standing
per-adapter note for `opencode` stating exactly that, until the skills
surface moves into `<home>/skills/` under a later revision.

### 7.2 Root-context forms

| Environment | Forms supported | Default form |
|---|---|---|
| `claude_code` | `monolithic`, `referenced` | `monolithic` |
| `codex_cli` | `monolithic` | `monolithic` |
| `opencode` | `monolithic`, `referenced` | `monolithic` |
| `pi` | `monolithic` | `monolithic` |

The effective form is machine configuration with these defaults; profile
data cannot select a form. Requesting `referenced` for an adapter that does
not support it is a configuration error, `environment_form_unsupported`,
not a fallback case.

### 7.3 System-prompt channels

Each adapter declares its closed channel-descriptor list. A descriptor's
`kind` is exactly `flag`, `config-key`, `variable`, or `file`; a
system-prompt descriptor's `semantics` is exactly `append` or `replace`
(`semantics` is a system-prompt member and is absent on an MCP descriptor,
section 7.8, which readers MUST accept). A `flag` descriptor carries
`argument`, exactly `path`, `contents`, or `name`: what the launcher passes
after the flag — the materialized file's absolute path, the file's bytes, or
a fixed reserved name. A `flag` descriptor with `argument: name`
additionally carries `name`, the fixed reserved name the launcher passes;
`name` is absent for `path` and `contents`. A `flag` descriptor MAY carry
`with`, an ordered list of companion flags the launcher passes verbatim
beside it.

| Environment | Channels |
|---|---|
| `claude_code` | `flag`/`append`: `--append-system-prompt-file` (`argument: path`); `flag`/`replace`: `--system-prompt-file` (`argument: path`) |
| `codex_cli` | `config-key`/`replace`: `model_instructions_file` |
| `opencode` | none in revision 1 |
| `pi` | `flag`/`append`: `--append-system-prompt` (`argument: path`, polymorphic — see below); `file`/`append`: `APPEND_SYSTEM.md`; `file`/`replace`: `SYSTEM.md` |

The `claude_code` flags are **verified** on Claude Code 2.1.261 (section
7.9). The `pi` row is written from evidence: pi 0.84.2 has no
`--system-prompt-file` and no `--append-system-prompt-file` — both are
rejected as unknown options — and its `--system-prompt <text>` takes text
only, so pi exposes **no file-taking replace flag** and its only replace
path is the agent-dir `SYSTEM.md` file. Its `--append-system-prompt <text>`
is **polymorphic**: it takes text or file contents, and a path that does not
resolve is sent as literal prompt text. The descriptor therefore records
`argument: path` with the polymorphism, and the launcher MUST verify that
the path is a readable regular file immediately before exec and fail rather
than let the tool interpret a dead path as prompt text — the read-failure-
as-absence class section 8.4 bans, applied at launch. The `codex_cli`
config key is **verified** present in the codex configuration surface
(0.153.2); that a per-invocation `-c model_instructions_file=<path>`
override applies it is docs-confidence.

**Admission rule.** A `flag` descriptor with `argument: path` is admitted to
the registry only when the pinned release is verified to accept a file path
in that position; a flag that accepts only text is recorded with
`argument: contents` or not at all. `pi`'s two `file` channels are applied
by the tool unconditionally when the file exists in the agent home
(**verified** in the 0.84.2 loader source); section 5.5 therefore keeps both
absent unless machine configuration explicitly materializes one. Channel
descriptors are data about a channel: nothing in this document applies one.
Application is the launcher's surface, behind its explicit opt-in and
warnings, under Decision 0013 Decision 6.3 and the launcher specification.

### 7.4 Credential passthrough, provisioning seeds, and isolation

Credentials are never profile content and never managed surfaces. Each
adapter declares the closed **passthrough** set a managed home shares with
the native home, together with its **passthrough strategy** — how the
sharing survives the tool's own writes — and the **write behavior** of the
pinned release that the strategy answers to:

| Environment | Passthrough entries | Strategy | Write behavior |
|---|---|---|---|
| `claude_code` | macOS: none — Claude Code stores OAuth credentials in the login Keychain as service `Claude Code-credentials`, account `$USER`; with `CLAUDE_CONFIG_DIR` set the service name is suffixed with `-` plus the first 8 hex characters of the SHA-256 of the config-dir path, so each managed home owns a separate Keychain item that the native item never serves (**verified** from the 2.1.261 bundle strings and the Keychain items present); Linux: `.credentials.json`; Windows: none in revision 1 (reserved pending platform verification) | macOS: `per-home-keychain` — nothing is linked, and every managed home logs in on its own; Linux: `file-link` — the managed home's `.credentials.json` is a symlink to the native file, re-checked by the liveness row | Linux write behavior **unverified** (docs-confidence: rename-over assumed until verified, so the Linux `file-link` is the expected-to-detach case below) |
| `codex_cli` | `auth.json` | `keyring-preferred`: where the operator's `config.toml` sets `cli_auth_credentials_store` to `keyring` the credential is ambient and no entry is linked; under `file` (the default) or `auto` the managed `auth.json` is a `file-link` — a symlink to the native file, re-checked by the liveness row | **verified** in-place: codex 0.153.2 rewrites `auth.json` by truncate-and-write on the same inode, mode 0600, never temp-and-rename (upstream `login/src/auth/storage.rs` for the path the binary names); `cli_auth_credentials_store = file|keyring|auto` **verified** in the embedded configuration docs |
| `opencode` | none — auth lives in `XDG_DATA_HOME`, which the config swap never touches (section 7.1) | ambient | — |
| `pi` | `auth.json` | `file-link` — the managed `auth.json` is a symlink to the native file, re-checked by the liveness row | **verified** in-place: pi 0.84.2 rewrites `auth.json` with a single in-place write, mode 0600, under its own lockfile, never temp-and-rename (installed `core/auth-storage.js`) |

A per-file symlink is severed by any write-temp-then-rename refresh: the
tool replaces the link itself with a regular file, and from that moment the
managed and native homes hold diverging credentials with no drift signal,
because passthrough entries are outside every surface hash. The strategy
column exists for that hazard: a keyring-backed mode has no file to sever;
a `directory` strategy keeps the link one level above the rewritten file;
a `file-link` is safe under a verified in-place writer — `codex_cli` and
`pi` — because an in-place rewrite keeps the inode and the link with it,
while a `file-link` under a rename-over tool, or one whose write behavior
is unverified (`claude_code` on Linux), is **expected to detach** and is
caught by the liveness row and re-linked by `--repair`; and every
file-shaped strategy is watched by the **liveness row** —
`env status` MUST report `environment_passthrough_detached` (non-current)
when a recorded passthrough entry is no longer a symlink or no longer
targets the native entry, and `env resolve --repair` MUST re-link it,
leaving both files' bytes untouched. Where the pinned release's write
behavior is verified in-place, a manager MAY record the entry as
`in-place` and skip nothing: the liveness row runs regardless. An
in-place rewrite has its own hazard, recorded here although nothing in this
document copies a credential file: a reader that snapshots `auth.json`
mid-write can observe a truncated file, so any such copy is taken under the
tool's own lock or while the tool is idle.

The default per profile × environment is `shared`: every managed home reuses
the operator's existing authentication through exactly these entries.
`isolated` — no passthrough, the tool authenticates fresh inside the managed
home — is **unsupported in revision 1** for `opencode`, where it is a no-op
because auth lives outside the swapped config home, and for `claude_code`
on macOS **below the pinned release 2.1.261**, for which no evidence covers
how a managed home's login interacts with the native Keychain item.
Configuring `isolated` for either is the configuration error
`environment_isolated_unsupported`, never a silently shared home. For
`claude_code` on macOS **at or above 2.1.261** the evidence is positive and
the restriction is lifted: the tool selects the Keychain item by
`CLAUDE_CONFIG_DIR` (the passthrough table above), so a managed home is
credential-isolated **by construction** — it never sees the native item
and a fresh `CLAUDE_CONFIG_DIR` reports "Not logged in" (**verified**). The
same fact removes `shared`: there is no Keychain item a manager could link
without handling credential material, which section 7.4 forbids. The
adapter therefore declares `isolated` as the platform default for
`claude_code` on macOS at the pinned release, and a configured `shared` is
the configuration error `environment_shared_unsupported`. One residual is
recorded: that a fresh login inside a managed home writes the suffixed
item and nothing else is inferred from the bundle's service-name builder
and **requires an operator** to confirm with a real login; the verified
selection scheme stands regardless. `isolated` remains available for
`codex_cli`, for `pi`, and for `claude_code` on Linux.

Passthrough entries are excluded from surface content hashes and drift
detection, are never copied into the profile store, and are never audited
as profile content. Materialization, refresh, switch, and garbage collection
MUST NOT create, rewrite, or delete a credential file beyond maintaining the
declared passthrough links themselves.

**Provisioning seeds.** A fresh managed home is not the operator's home: the
tool starts it as a first run — login prompt, onboarding wizard, per-project
trust, MCP approvals — because the state that makes a home "the operator's"
lives in tool-owned files the passthrough never carries. Each adapter
therefore declares a closed **provisioning seed** class: non-credential
files or members copied from the native home exactly once, at provisioning,
never refreshed, never hashed, never drift-checked, never audited as profile
content, and thereafter owned by the tool. Seeds are recorded in the marker
by path so that `env unmanage` (section 9.2) can tell them from tool state,
and are excluded from every surface hash. The enumerated seeds:

| Environment | Provisioning seeds | Evidence |
|---|---|---|
| `claude_code` | `.claude.json` — **written**, not copied: exactly the object `{"hasCompletedOnboarding":true,"projects":{}}` at provisioning, to which repair adds one project entry per launch directory (below); `oauthAccount` is never seeded — login is per home (passthrough table); a `settings.json` seed is not declared in revision 1 | the minimal seed shape is **verified** on 2.1.261: a file holding only these members survives the first run, which merges its own first-run members around them; the fresh-home "Not logged in" behavior is **verified** |
| `codex_cli` | `config.toml` — copied whole (project trust, model, and MCP tables included; the launch channel of section 7.8 layers the profile's MCP set over it) | that the copied file is parsed in the fresh home is **verified** (0.153.2, its `mcp_servers` entries are listed); that a `projects.<path>.trust_level` entry does **not** lift the `exec` git wall is **verified** (section 7.9 `exec_flags`); the remaining member shapes are **docs-confidence** |
| `opencode` | none — the XDG seeds of section 7.1 are the analogous class | — |
| `pi` | `settings.json`, `models.json` | that a fresh dir loses them and re-downloads its tool trees is **verified**; their shapes are docs-confidence |

A seed is one-time by definition: a native-home change after provisioning
does not propagate, and the tool's later writes in the managed home are
its own state. The one per-launch-directory exception is the `claude_code`
**project entry**: `projects.<path>` in the managed `.claude.json`, keyed by
the literal launch directory as used (not its realpath — **verified**, a
`/tmp` seed matches a `/tmp` cwd), holding `"hasTrustDialogAccepted":true`
and, when the home's form is `referenced`, `"hasClaudeMdExternalIncludesApproved":true`
(section 5.3). The marker records the seeded project paths; under the
`referenced` form a launch directory without its entry makes the home
**stale for that directory** (section 10.1), so `env resolve --repair`
adds the entry under the repair lock and a bare `env resolve` reports it.
Under the `monolithic` form the entry is added on the same occasion but
its absence is not staleness: `-p` never asks for trust, and the
interactive trust dialog is tool state. First-run walls, recorded so that
nobody seeds against them: in non-interactive mode each tool's first wall
is authentication (**verified** on all three installed tools) — `claude`
reaches it before any trust or onboarding prompt, `codex`'s only other
wall is its git check (`--skip-git-repo-check` is required outside a git
repository for `exec`, and no configuration seed lifts it), and `pi` has
no trust wall. A seed that is absent in the native home is simply not
seeded; a seed that exists but cannot be read is
`environment_seed_unreadable` and provisioning stops before the first
write (section 8.4 discipline).

**Isolation matrix.** What a managed home isolates per adapter, in revision
1, normatively:

| Environment | Root context, system prompt, MCP set | Skills | Session state and caches | Authentication | Tool configuration |
|---|---|---|---|---|---|
| `claude_code` | per profile (managed home) | per profile (`<home>/skills/`) | per profile | macOS: isolated, always, at the pinned release (per-`CLAUDE_CONFIG_DIR` Keychain item); Linux: shared by default, `isolated` available | seeded `.claude.json` (minimal object plus per-launch-directory project entries), then per home |
| `codex_cli` | per profile | per profile | per profile | shared by default, `isolated` available | seeded once from the native `config.toml`, then per home |
| `opencode` | per profile | **machine-current profile** (split-brain, section 7.1) | per profile for config-home state; `XDG_DATA_HOME`/`XDG_STATE_HOME` state is shared and ambient | shared, always | XDG-seeded allowlist links, reconciled |
| `pi` | per profile | per profile | per profile | shared by default, `isolated` available | seeded once (`settings.json`, `models.json`), then per home |

### 7.5 Shadowing paths

An adapter declares its known **shadowing paths**: higher-precedence
unmanaged files whose presence makes a managed surface inert. The closed
revision-1 declarations are:

| Environment | Shadowing path | Shadowed surface |
|---|---|---|
| `pi` | `AGENTS.override.md` beside the root-context target | root context |

`claude_code`, `codex_cli`, and `opencode` declare none in revision 1. The
adapter ledger and environment marker protect only managed paths, so
materialization and `env status` MUST report `environment_shadowing_path_present`
when a declared shadowing path exists; the file itself is never touched.
The surface is genuinely inert, so the row is **non-current** by default
(section 12). Machine configuration MAY record a per-path
`shadow_acknowledged` entry (section 12.1) — "this override is deliberate" —
which downgrades exactly that row to a reported, current warning; the
default stays fail-closed and the acknowledgment is a record the operator
made.

### 7.6 Secondary fixed-home targets

Some hosts embed an agent environment at a fixed home no environment
variable can retarget, with the primary home's internal layout. An adapter
MAY declare a closed list of such targets: a target identifier (core §2
grammar), a probe path, a home path, and the subset of surfaces the embedded
host honors. Revision 1 declares exactly two, for Xcode's embedded coding
agents. Xcode 26.5 launches the installed `claude` and `codex` binaries
with `CLAUDE_CONFIG_DIR`, respectively `CODEX_HOME`, pointed at an
**Xcode-internal agentic home directory** and passes its system prompt
through `--append-system-prompt`; the operator can move that directory
with the `IDEChatOverrideAgenticHomeDirectory` user default (all
**verified** from the Xcode 26.5 `IDEIntelligenceAgents` bundle strings).
The directory is created on the first agent launch, so its default path
**requires an operator** to record; the table names it by role:

| Adapter | Target id | Probe path | Home | Surfaces honored |
|---|---|---|---|---|
| `claude_code` | `xcode-coding-assistant` | the resolved Xcode-internal agentic home directory (the `IDEChatOverrideAgenticHomeDirectory` value when set, otherwise Xcode's default) | that directory as `CLAUDE_CONFIG_DIR` | root context, skills |
| `codex_cli` | `xcode-coding-assistant` | the same directory | that directory as `CODEX_HOME` | root context, skills |

A secondary target is an in-place surface set: it carries the environment
marker and ledger discipline of section 8, defaults to `copied` mode, and
always reflects the current profile for its scope — an embedded host
launches its agent itself, so managed homes can never reach it. The embedded
hosts' own files (`.claude.json`, `commands/`, `config.toml`, caches) are
unmanaged in revision 1 and MUST NOT be written. That the embedded agents
read the materialized root-context and skills files at these homes is
**docs-confidence** and **requires an operator** — the verification sprint
of 2026-09-05 found the internal directory absent on a machine that had
never launched an Xcode agent, so the claim is tested only by launching
one; Xcode's Keychain hashing (the same first-8-hex SHA-256 scheme as
section 7.4) is verified from the bundle, so the embedded home's login is
its own.

Target participation is machine configuration, never profile data: `auto`
(default), `off`, or an explicit per-target enable. Under `auto` the target
participates exactly when its probe path exists: a machine without the probe
path materializes nothing there and reports nothing missing; a machine with
it re-materializes the target on every install, `use`, and `sync`. The
**first write** into a target's home under `auto` is a write into another
application's directory and requires one-time consent: the manager stops
with `environment_target_consent_required`, naming the target and the home,
until the operator records consent in machine configuration
(`targets.<id>.consented`, section 12.1) or passes the explicit per-target
enable; an explicitly enabled target is consented by that act. Probe results
appear in `env status`, which MUST also state, for every participating
target, that the embedded host's MCP configuration and `commands/` are
**ungoverned** — present, unaudited, and outside this capability. A target
identifier not declared by the registry is `environment_target_unknown`.

### 7.7 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| explicit operand names an unregistered environment | `environment_unknown` |
| explicit operand names an undeclared target | `environment_target_unknown` |
| configured form not supported by the adapter | `environment_form_unsupported` |
| declared shadowing path exists (non-current; current warning under `shadow_acknowledged`) | `environment_shadowing_path_present` |
| `isolated` configured for `opencode`, or for `claude_code` on macOS below the pinned release | `environment_isolated_unsupported` |
| `shared` configured for `claude_code` on macOS at or above the pinned release | `environment_shared_unsupported` |
| recorded passthrough entry is no longer a symlink to the native entry (non-current) | `environment_passthrough_detached` |
| provisioning seed exists in the native home but cannot be read | `environment_seed_unreadable` |
| unrecorded entry in a managed `opencode` parent shadows an allowlisted operator entry (warning) | `environment_seed_shadowed` |
| first `auto` write into a secondary target's home without recorded consent | `environment_target_consent_required` |
| detected tool version differs from the adapter's recorded verified version (warning) | `environment_tool_version_unverified` |

### 7.8 MCP launch channels

Each adapter declares at most one MCP channel descriptor, in the section 7.3
descriptor grammar with `argument` and `with` and without `semantics`. The
fragment's `mcp` section (section 10.2) reproduces it; the launcher applies
it under Decision 0013 Decision 6.3. Resolving a fragment applies nothing,
and a managed home launched without the channel carries no MCP
configuration.

| Environment | Channel | Evidence |
|---|---|---|
| `claude_code` | `flag` `--mcp-config` with `argument: path`, `with: ["--strict-mcp-config"]`. Under `--strict-mcp-config` the tool ignores every other MCP configuration, including servers recorded in the managed home's own `.claude.json`; this is intended — a managed home's MCP set is exactly the profile's | both flags **verified** on Claude Code 2.1.261 (section 7.9) |
| `codex_cli` | `flag` `-p` with `argument: name`, `name: "curator-mcp"`: `-p <name>` layers `$CODEX_HOME/<name>.config.toml` on the base configuration, so the manager's `<home>/curator-mcp.config.toml` (section 5.8) carries the set. The layer name is fixed and reserved. `-p` accepts **exactly one** value — a second occurrence is the tool's argument error, not last-wins — so an operator `-p` after `--` fails the launch and operator profile layering is unavailable in a managed launch (recorded consequence; this closes Decision 0012 Open question 3). `-p` is accepted before and after `exec`. A **missing layer file is silently ignored** (exit 0), so the launcher MUST stat the layer file immediately before exec and fail rather than launch without the set; `env resolve` covers the same file as a marker-recorded surface | all four facts **verified** on codex 0.153.2 by direct invocation; a layer file whose only table is `mcp_servers` composes over the base and its servers are listed (**verified**) |
| `opencode` | `variable` `OPENCODE_CONFIG` naming the section 5.8 file. opencode merges configuration in a documented order — remote, global, `OPENCODE_CONFIG`, project `opencode.json`, `.opencode/`, `OPENCODE_CONFIG_CONTENT`, managed — so a project-level entry with the same server name overrides the managed one; recorded, not prevented | merge order **docs-confidence** (opencode is not installed on the recording machine) |
| `pi` | none — pi 0.84.2 has no MCP channel; no file and no `mcp` section | **verified** absent from the 0.84.2 help |

Whether a given tool passes its own environment through to a `stdio` server
is a per-adapter fact verified with the channel. Under Decision 0013 the
launcher adds the fragment's `env_names` to the launch plan's
environment-name allowlist so that an `ax`-tracked child receives the
operator's values exactly as a direct exec inherits them.

### 7.9 Recorded tool versions and size advisories

Each adapter records the tool release its facts were verified on, and a
size advisory for its root-context target:

| Environment | Verified release | `root_context_size_advisory_bytes` | Advisory evidence |
|---|---|---|---|
| `claude_code` | 2.1.261 (this text; 2.1.257–2.1.259 for the review's facts) | `32768` | none published; the codex figure is adopted as a conservative default |
| `codex_cli` | 0.153.2 (this text; 0.151.0 for the review's facts) | `32768` | `project_doc_max_bytes = 32768` applies to the project-document chain only; the global `$CODEX_HOME/AGENTS.md` is **not truncated** (**verified** on 0.153.2 with a 41 KB file via `codex debug prompt-input`, also with the cap narrowed to 1000), so the advisory is not tied to any tool cap and keeps the common default as a prompt-budget advisory |
| `opencode` | not installed on the recording machine — every opencode fact is docs-confidence | `32768` | none published; default adopted |
| `pi` | 0.84.2 | `32768` | none published; default adopted |

Each adapter additionally records the following members, whose values were
fixed by the verification sprint of 2026-09-05 (claude 2.1.261, codex
0.153.2, pi 0.84.2; opencode not installed):

| Member | `claude_code` | `codex_cli` | `pi` | `opencode` |
|---|---|---|---|---|
| `credential_scope` | `per CLAUDE_CONFIG_DIR (keychain service suffix sha256[0:8])` on macOS (**verified**); `home` on Linux | `home` | `home` | `xdg-data` |
| `auth_write` | — (Keychain on macOS; Linux **unverified**) | `in-place` (**verified**) | `in-place (lockfile)` (**verified**) | docs-confidence |
| `global_context_cap` | `none` recorded | `none` (**verified**) | `none` recorded | docs-confidence |
| `exec_flags` | — | `--skip-git-repo-check required outside git` (**verified**) | — | — |
| `profile_flag` | — | `-p (single, silent-if-missing)` (**verified**) | — | — |

`env status` reports, per adapter, the recorded verified release and the
best-effort detected release of the installed tool (`<tool> --version` or
the adapter's documented equivalent, read-only); a detected release that
differs from the recorded one is the warning
`environment_tool_version_unverified` — the facts may still hold, and
nothing in this document is gated on the warning, but the operator is told
the registry's evidence does not cover the binary in front of them. A tool
that cannot be located or whose version cannot be read reports the detected
release as unknown, never as matching.

**Erratum fast path.** A recorded fact that fails to reproduce on a release
this table names is corrected by an erratum on the decision that introduced
it and a rewrite of the affected row here, within revision 1 — the Decision
0010 erratum of 2026-09-05 is the pattern — never by an implementation
working around the recorded fact silently.

## 8. Materialization modes and the environment marker

### 8.1 Modes

A profile materializes into an environment in exactly one of three modes:

- **`managed-home`** — the manager provisions a complete home directory per
  profile × environment below a manager-owned **environments root** in the
  manager home. The only profile-derived path component below that root is
  the profile name, bounded by the core §2 grammar; two profile names that
  map to one platform path below that root are a section 5 platform-path
  collision, and provisioning fails with `environment_path_collision`
  before writing. Managed surfaces inside
  the home are symlinks into the profile store, with copies where a surface
  or platform requires bytes. The environment's own mutable state — session
  logs, history, caches, trust records — lives beside them, owned by the
  tool, giving each profile naturally isolated session state. A managed
  home is activated only by consuming a resolved fragment (section 10);
  nothing in this document applies one to a running process.
- **`linked`** — in-place materialization into the environment's native
  default home as symlinks into the profile store: the manager §5
  symlink-with-copy-fallback discipline extended from skills to root
  context. Only the current profile for the applicable scope (section 9.2)
  is materialized in place.
- **`copied`** — in-place materialization as plain files with recorded
  content hashes, for surfaces or targets where symlinks are unreliable:
  secondary fixed-home targets, link-hostile tools, network filesystems.

Mode defaults: the four adapters default to `linked` for their in-place
surfaces; secondary fixed-home targets default to `copied`; managed homes
always link from the store. An adapter MAY declare a different in-place
default in the registry; profile data cannot.

All three modes materialize from the same lock's store entries (section 4),
so they cannot diverge for one lock hash.

**Fresh homes.** A managed home is provisioned on the first `env resolve
--repair` or `profile sync` that names its profile × environment: the
manager creates the home, materializes the managed surfaces, links the
section 7.4 passthrough entries, writes or copies the section 7.4
provisioning seeds, and — for `opencode` — seeds the section 7.1 XDG
links, in that order, as
one journaled transaction. The **first-resolve notice** accompanies that
provisioning and every first resolve of a home: the manager prints the
managed-home path, states that the tool will treat the home as its own
state root — sessions, trust records, and approvals accrue there and not in
the native home — and names any first-run step the seeds do not cover for
that adapter. The notice is informative and never suppressed by
configuration.

**Two doors.** A native launch of a tool and a `curator run` launch of the
same profile use different homes — the native home under `linked` or
`copied` mode, and the managed home under `managed-home` — and keep separate
session histories, trust records, and approvals. This revision keeps the
split and makes it loud rather than routing the machine-current profile's
managed launches into the native home: the section 10.3 boundary requires
every fragment value to stay below the environments root, and the system-
prompt and MCP surfaces of sections 5.5 and 5.8 exist only in managed
homes. The first-resolve notice names the split; `env status` reports, for
the current profile of each scope, both homes and whether each has been
provisioned. An operator picks one door per environment for daily work; a
`--isolated-home` flag that would change the answer is not in revision 1.

### 8.2 Environment marker, schema 1

Every in-place surface set and every managed home carries a per-home
**environment marker**, `.agent-environment.json`, a strict schema-1 object
beside the managed surfaces. The marker records:

- `version` — exactly `1`;
- `profile` — the profile `name`, the `root` package name, its source
  `kind` (exactly `git`, `local`, or `path`), and `lock_sha256`, the lock
  hash of section 1.3. A `git` root additionally records its canonical
  source identity and declared requirement (`range`, `tag`, or
  `revision` as written, and `directory` when declared); a `path` root
  additionally records `source_path` — the operand exactly as the operator
  supplied it at install, an informative provenance record whose bytes
  never enter any identity — and, exactly when the profile was created by
  the section 9.6 import, `imported_from_native: true`;
- `members` — the lock's `context` members in emitted order (section 5),
  each with its `name`, `version`, pin (`commit` or `state_sha256`),
  `weight`, and `overlay` flag; a `path` member additionally records its
  `source_path` as above;
- `precedence` — an object carrying both primitives, `winner` and
  `placement` (section 6), always present;
- `mode` — exactly `managed-home`, `linked`, or `copied`;
- `surfaces` — one entry per managed surface: its home-relative file
  paths, its form where the surface has one, its content hash under section
  5.6, and — for a `linked` home — whether any entry fell back from symlink
  to copy under the manager §5 discipline. For a managed home the section
  5.8 MCP file is the surface keyed `mcp`. Surface keys are sorted;
  required arrays are present even when empty;
- for a managed home, the recorded `passthrough` entries with their section
  7.4 strategy, and the recorded provisioning `seeds` by home-relative path;
- for a managed `claude_code` home, `seeded_projects`: the sorted list of
  literal launch-directory paths whose project entry section 7.4 has
  written into the managed `.claude.json`, so that resolve can tell a
  missing entry from one the tool later rewrote;
- for a managed `opencode` parent, the recorded XDG seed links of section
  7.1;
- for a home whose backups directory is non-empty, nothing: backups are
  discovered from the section 8.3 directory, never recorded in the marker.

Readers MUST reject an unsupported marker version and MUST NOT infer newer
semantics from unknown fields. An unreadable or invalid marker fails closed:
the home's surfaces are treated as unmanaged — nothing is removed or
replaced — and status reports `environment_marker_invalid`. The marker joins
the `agent-*` identifier family deliberately; the frozen core §1.1
identifiers keep their exact spellings.

The marker is a record, not a signature: it MUST NOT be used as an
authorization token or provenance proof (core §10 discipline).

### 8.3 Ledger discipline and backups

The marker is the ledger of record for environment surfaces, extending the
core §11 rule unchanged: a manager MUST remove or replace only files its
preceding marker records and MUST fail with
`environment_surface_unmanaged_conflict` rather than overwrite an unmanaged
file. Skill entries keep the core §11 adapter ledger; the two records never
merge.

Takeover and onboarding backups (section 9.5) land in **versioned**
backup sets `.agent-environment-backup/<n>/` beside the marker, where `<n>`
is a decimal generation counter starting at `1` and incremented per
operation that backs anything up; each set preserves each file's
home-relative path. A backup set, once written, is never modified, and a
new operation always opens the next generation: `environment_backup_exists`
fires only when the next generation's directory already exists — a
half-finished predecessor — and never wedges a second takeover of the same
path. Backups are outside every surface hash and are never materialized,
served, or read by any rule in this document. Machine configuration sets
`backup_retention` (section 12.1), the number of generations kept, default
`5`; when a new generation exceeds it, the oldest generations beyond the
count are removed by that same operation, and `0` means keep every
generation. `env unmanage --restore-backups` (section 9.2) restores the
newest generation. `env backups scrub [--older-than <days>]` removes
generations on the operator's explicit request; nothing else removes a
backup, and garbage collection never does. `env status` reports, per home,
the number of backup generations and the age of the oldest and newest — a
backup of a hand-maintained context file may hold secrets, and the
operator is told it is there.

### 8.4 Drift

For `linked` surfaces, drift is a link that no longer targets the expected
store path or a target whose bytes fail the recorded hash. For `copied` and
`managed-home` surfaces, drift is a recorded content hash that no longer
matches. Drift detection MUST state both halves explicitly: the surface was
modified outside the manager, and the file was left untouched; the
installation is non-current, and `repair` restores the managed bytes. A
drifted file is never silently overwritten outside `repair`.

An absent surface file and a failed read are different facts: a failed
marker read is `environment_marker_invalid`; a failed read of a recorded
surface file is `environment_surface_unreadable`, the row is non-current
with its currency reported as unknown, and no absence-shaped outcome —
`environment_surface_missing` included — may fire on either.

### 8.5 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| marker unreadable, malformed, or unsupported version | `environment_marker_invalid` |
| managed surface bytes or link differ from the record (non-current) | `environment_surface_drift` |
| recorded surface file absent (non-current) | `environment_surface_missing` |
| recorded surface file exists but cannot be read (non-current) | `environment_surface_unreadable` |
| write would touch a file the marker does not record | `environment_surface_unmanaged_conflict` |
| next backup generation directory already exists | `environment_backup_exists` |

## 9. Profile lifecycle

### 9.1 Installation, resolution, and audit

```text
profile install <source> [--directory <dir>] [--range <range> | --tag <tag> | --revision <commit>] [--as <name>] [--use]
```

`<source>` is either a git URL or a `path` operand. The distinction is
syntactic, never probed from the filesystem: an operand beginning with `/`,
`./`, or `../` (or a platform absolute-path spelling) is a `path`
declaration; every other operand resolves as `git` under section 1. One
install names **one root**: the context package at the addressed root —
`--directory <dir>` selects a directory within a `git` snapshot — becomes
the profile's root, and the profile name is the root package's `name`
unless `--as <name>` is given; a name already installed is
`profile_name_taken`.

For a `git` source the operator expresses the declared requirement with at
most one of `--range <range>`, `--tag <tag>`, or `--revision <commit>`,
mapping one-to-one onto the section 1 declaration forms; when none is
supplied, `--range latest` applies. A repository with no version tags
installs only by `--revision` or by a non-version `--tag`, and the manager
says so when `latest` finds no candidate. Supplying more than one
requirement flag, or a requirement flag or `--directory` with a `path`
operand, is `profile_install_ref_conflict`. There is no `--branch`.

Installation **resolves** the closure under section 1.4 — the root, the
machine overlays declared for the profile name, and every requirement they
carry transitively — **audits** every member, **writes the lock** (section
1.3), and installs every member's store entry (section 4). Every closure
member passes the same gates: canonical source identity and the core §6.1
allowlist for `git` sources, the MCP package allowlist for `mcp` members,
snapshot validation under sections 2 and 3 (and core §3–§4 for skills), and
the audit below. Profiles installed from any number of repositories coexist
as one machine profile set, and two profiles whose locks share a member
share its store entry.

Profile installation always runs the manager §7 source audit in strict
mode over every member; an advisory profile install does not exist. A
`path` snapshot audits identically to a `git` snapshot. A `path` package has
no network identity: its identity for local revocation is its state hash,
the core §6.1 network allowlist does not apply (local sources bypass it),
and a `path` snapshot never produces a shared `audit-record-v1` object,
whose shape requires a network identity and a commit. The audit pipeline is
unchanged — raw-tree hashing, the static canary whose failure always blocks,
deterministic detectors, revocation — and gains two REQUIRED classes for
context and MCP snapshots:

- **`context-secret-material`** — a deterministic detector over context
  modules, `agent-context.json`, `agent-mcp.json` (its `args` and `url`
  included), and `CONTEXT.md` that reports credential-like material (keys,
  tokens, passwords, and equivalent secret classes) as a verifiable finding
  at blocking severity, each finding naming the file and the byte span.
  Because profile installation is always strict, a member carrying such a
  finding fails installation. The detector is **unpinnable**: a manager §7
  content-hash pin on the snapshot does not clear it, and no configuration,
  flag, or policy downgrades it. The only escape is a **scoped waiver**
  recorded in machine configuration (`secret_material_waivers`, section
  12.1): the member's pin, the file's protocol path, the exact byte span,
  and a free-text reason; a waiver clears exactly the finding whose file
  and span it names, at that pin, and is reported as a warning naming the
  waiver every time the member is audited. A waiver whose pin, file, or
  span matches no finding is `context_secret_waiver_unmatched` (warning).
  The detector's pattern classes are closed and vectored — the next batch
  delivers `vectors/context-detectors.json` with, per class, positive cases
  (`secret-aws-access-key`, `secret-private-key-block`,
  `secret-bearer-token`, `secret-in-mcp-args`, `secret-in-mcp-url`) and
  negative cases (`placeholder-example-key`, `content-hash-not-secret`,
  `waived-span-clears-only-itself`, `pin-does-not-clear-finding`).
- **`context-system-module-present`** — an always-warn, never-blocking
  surfacing class that reports every `class: system` module of every
  context member with its package, path, and selector at install and
  update. System-prompt bytes are the sharpest surface a profile carries;
  this class guarantees they never enter a machine without a provenance
  line at install. `fail_on` never applies to it.

Root-context modules are prompt material: audit tooling SHOULD surface them
for human prompt-injection review; the pipeline guarantees provenance and
immutability, not intent.

A `path` install from a working-tree checkout whose modules carry CRLF
endings fails `profile_module_bytes_invalid` like any other; the diagnostic
for a `path` source MUST carry the hint that a `core.autocrlf` or
`text=auto` checkout is the usual cause and that a fresh checkout with
`core.autocrlf=false`, or the `git` source kind, produces LF bytes. There is
no normalizing install flag: section 3 has no normalization path.

Activation on install follows operator intent without magic: `install` sets
the machine current profile only when the machine has none — first install,
and the activation is reported, never silent — or when the operator passes
`--use`. `--use` takes no name: an install names one root, so there is
nothing to choose. In every other case the manager prints the installed
profile and how to activate it. Re-installing an already installed source
with the same requirement re-resolves exactly as `profile update` does
(section 9.2) and is reported as an update.

### 9.2 Current profile, switching, update, and removal

Machine configuration records at most one machine **current profile**, plus
per-scope current profiles under section 9.3.

**`profile use <name>`:**

1. re-materializes every in-place surface of every registered adapter —
   native default homes and every participating secondary fixed-home
   target — from the store entries its lock names, atomically per entry,
   under the manager-home mutation lock, journaled like any other
   manager-home transaction (manager §2.5), and re-points the machine
   command shims (section 9.4) to the selected profile when the switch is
   machine-scope — a section 9.3 scoped switch leaves the shims alone;
2. updates the recorded current profile for the affected scope;
3. warns that already-running agent sessions keep the previous context in
   memory and may write state derived from it, and recommends launching
   through managed homes for concurrent multi-profile work.

The switch attempts **every** entry of the scope and reports per-adapter and
per-target results. The new current profile is recorded only when the whole
scope materialized; when any entry failed, the recorded current is
unchanged, the successfully switched entries are reported as
`profile_use_partial` (non-current, because they no longer match the
recorded current), and `profile use` of either profile — the recorded one
or the attempted one — completes the scope from the journal. The switch
never touches environment-owned mutable state, credential files beyond
section 7.4 links, unmanaged files, or backups.

**`profile update [<name> | --all]`** re-resolves the root and the overlays
from their declared requirements, fetching new candidates, and proceeds in
this order:

1. resolution under section 1.4 produces a candidate lock;
2. every member new to the lock — a name or pin not in the old lock — is
   audited in strict mode under section 9.1; a blocking finding on any new
   member leaves the **old lock in place**, reports `profile_update_blocked`
   with the finding, and changes nothing;
3. the new store entries are installed and the new lock is published as one
   manager-home transaction;
4. in-place scopes whose current profile is this one re-materialize from
   the new lock;
5. managed homes of this profile are marked **stale** (`environment_home_stale`
   at their next bare `env resolve`, section 10.1; `curator run` always
   passes `--repair` and repairs the home instead of surfacing it) for
   explicit repair, never repaired in the background — a running session
   may be reading them;
6. store entries the new lock no longer names become GC-eligible under
   section 12; the old lock is retained beside the new one until the next
   garbage collection so that a stale managed home can still be identified.

A root pinned by exact `tag` or `revision` is reported as pinned and does
not move; a moved tag is a warning, or an error under strict-tag policy. An
update that resolves to the identical lock changes nothing and says so. The
skill-scope `update` and `upgrade` commands of the manager (manager §2)
never move a profile's lock. Under this capability
`curator global update|upgrade [--profile <name>|--all-profiles]` **fetch
only**: they refresh the candidates of the named profiles' skill sources,
report which pins `profile update` would move and to what, and change no
lock, store entry, or surface; a profile's skill set changes only through
`profile update` or the direct declarations of section 9.4. The `default` profile's `local` root is
re-keyed only when its migrated skill set changes, as one transaction per
operation, so a `global add` churns exactly one lock hash and the `ax`
drift check sees one change, not several.

**`profile remove <name> [--purge]`** refuses with `profile_in_use` while the
profile is the current profile of any scope — machine or section 9.3 scope —
or is named as an overlay of any other installed profile; the operator
switches or clears first. Removal deletes the profile's lock and its
configuration records; its managed homes, which hold the operator's session
data, are **retained** unless `--purge` is given, in which case they are
removed with their markers and backups after the notice. Store entries no
other lock names become GC-eligible. Retained homes without a profile are
**orphans**: `env status` reports each orphan by path, and `env unmanage`
or a later `--purge` removes it.

**`env unmanage [--restore-backups] [--env <env-id>] [--target <target-id>]`**
takes every in-place surface set of the named scope (default: every scope)
back to native ownership: managed surfaces recorded by the marker are
removed — symlinks unlinked, copied files deleted — and, under
`--restore-backups`, the newest backup generation of section 8.3 is copied
back to each file's home-relative path before the marker is deleted;
without the flag the backups stay in place and the operator is told where.
Unmanage never touches files the marker does not record, never touches
managed homes (those are `profile remove --purge`), and never touches
credential files. The recorded current profile of an unmanaged scope is
cleared.

### 9.3 Scoped switching

`profile use` accepts `--env <env-id>` and `--target <target-id>` to narrow
the switch to a subset of registered adapters or to one secondary fixed-home
target. A scoped switch records a per-scope current profile. `env status`
and `profile list` MUST surface every scope whose current profile differs
from the machine default: a split-brain configuration is always visible,
never implicit. An unknown `--env` operand is `environment_unknown`; an
unknown `--target` operand is `environment_target_unknown`.

A scoped current is cleared in either of two ways, with the same effect: a
scoped `profile use --clear`, or a scoped `profile use` naming the profile
that is the machine default. Both remove the scope record, re-materialize
the scope from the machine default, and make the scope follow the machine
default thereafter; a scope record equal to the machine default is never
kept.

### 9.4 Profile-scoped skills and migration

The existing machine-global skill scope becomes profile-scoped. A profile's
skill set is the `skill` members of its lock: the resolved `requires.skills`
of its closure plus any **direct declarations** the machine adds through the
existing global skill commands (`global add`, `global remove`, and their
kin), which now write into the profile's lock through the same resolution —
a direct declaration is a constraint attributed to the machine, in the exact
`tag` or `revision` forms of core §4.4, and enters the closure of section
1.4 beside the root's requirements. Each profile's skills resolve through
the unchanged closure, audit, build, and runtime machinery; the resolved
skills materialize into that profile's managed homes and — for the current
profile of each scope — the in-place adapter surfaces under the manager §5
discipline. Global skill operations act on the current profile and accept
`--profile <name>` and `--all-profiles`. `profile sync` re-materializes
every installed profile across every registered adapter and participating
target from the locks it finds; it is the actualization path when a new
adapter or target is registered on the machine.

**Commands.** Skill commands reach a shell through the manager's forwarding
shims in one user-bin directory (manager §12.1; core §12.1). That directory
is a machine singleton: in revision 1 it carries the rendered command set of
the **machine-current profile**, and `profile use` (section 9.2) re-points
the shims on every machine-scope switch. Revision 1 declares profile skill
**commands unavailable inside managed-home launches**: a `curator run`
session inherits the machine shims, so a launch of a profile other than the
machine-current one sees the current profile's commands or none — a stated
limitation, not a discovered one. The fragment reserves `path_prepend`
(section 10.2) for the revision that gives each profile a command root below
the environments root; it is never emitted in revision 1. Independently of
that revision, managed skill bin directories and any directory a skill
publishes onto `PATH` MUST NOT carry an executable whose name begins with
`curator-`, and materialization MUST refuse such an entry with
`environment_reserved_command_name` — the umbrella discovery of section 11
trusts `PATH`, and profile-materialized files must not be able to poison it.

**Hybrid scope.** Hybrid manifests (manager §4.3) are orthogonal to
profiles: they never participate in profile switching, composition, or a
lock, and they never target a managed home's project. Within a project
closure the precedence is project, hybrid, then the **current profile of
the applicable scope** as section 9.3 resolves it — "global" in manager §4.3
now names that profile's skill set. Hybrid-only closure nodes render once in
the machine store with the machine locale, unchanged, and are not
re-rendered on a profile switch.

**Migration.** On first use of the profile surface, the existing
machine-local global scope is renamed into a builtin profile `default` with
a synthesized `local` root — no `context`, version `0.0.0` — whose lock
carries only the migrated global skills as direct declarations. `default`
carries source kind `local`: no git identity, no requirement, no commit;
its root's store key and pin are its state hash, recomputed when its state
changes, and its lock hash follows. A root with no `context` declares no
root-context surface (section 2), so no root-context file is written for
`default`; it materializes skills alone. Switching, `profile sync`, and
`env status` treat a `local` profile exactly like an installed one. A
machine that never installs another profile observes no behavior change:
`default` simply is the current profile and existing global installations
keep their behavior byte-for-byte.

### 9.5 Onboarding

A machine with hand-maintained global context must reach managed state
without loss. Onboarding ships complete in revision 1: detection, the
foreign-manager stop, the replace notice, backup, takeover, and the
section 9.6 import.

Onboarding is triggered only by a **mutating** profile operation that meets
unmanaged state — `profile install`, `profile use`, `profile sync`, `profile
update`, `env resolve --repair`, and an explicit takeover. Read-only
commands — `profile list`, `env status`, `env resolve` without `--repair` —
report unmanaged state and never begin onboarding, never write a backup,
and never prompt. On such a trigger the manager:

1. **Inventories**, per registered adapter and participating target:
   existing unmanaged root-context files; existing global skills; and
   managed-surface paths that are already symlinks pointing outside the
   manager's store. The last is evidence of another manager and stops the
   operation with `environment_foreign_manager_detected` and an explicit
   choice — abort, or take over with backup — never a silent absorption.
   The inventory additionally applies a best-effort **heuristic**: the
   presence of a well-known dotfile-manager state location (a closed,
   documented list per manager — `~/.local/share/chezmoi`,
   `~/.config/home-manager`, and the like) elevates the notice for plain
   unmanaged files to `environment_foreign_manager_suspected` (warning): a
   dotfile manager appears to manage this machine and will overwrite
   managed surfaces on its next apply. The heuristic never blocks.
2. **Notifies**: before any write, the operator is told that native global
   context files are being replaced by managed ones and where the backup
   lands.
3. **Backs up, always**: every file the operation will replace is copied
   into the next section 8.3 backup generation before the first write,
   whether or not any import was requested, subject to
   `environment_backup_exists`.
4. **Classifies and offers the import**: the detected state is classified
   under section 9.6 and the classification is reported before any write;
   the import itself runs only on the operator's request and under the
   section 9.6 consent rules. Onboarding without an import ends after
   step 3 and the takeover writes the operator chose.

Takeover of a specific unmanaged file outside onboarding requires the
explicit takeover flag and performs the same notice and backup; without the
flag, section 8.3 applies and the operation fails rather than overwrite.
Authentication is never part of onboarding, takeover, or import: credential
files stay where the section 7.4 passthrough expects them, untouched.

After onboarding, repeated drift on one surface is the same evidence seen
late: a manager SHOULD report a surface repaired more than an
implementation-defined number of times within an implementation-defined
window as a **suspected external writer** under
`environment_foreign_manager_suspected`, naming the surface, so that a
copy-mode dotfile manager fighting the ledger is read as what it is and not
as manager flakiness.

### 9.6 Onboarding import

The import turns the detected native context into an installed profile
through the ordinary `path` pipeline of section 9.1. Its input is the
section 9.5 inventory; its output is one installed, audited, locked
profile whose environment markers record `imported_from_native`.

**Detected surfaces.** The revision-1 detected-surface list is closed.
For each registered adapter, over its native default home:

- the **root-context file** at the adapter's section 7.1 root-context
  target; and
- each **skills entry** of the adapter's manager §5 global skills surface
  that the manager's adapter ledger does not record. A ledgered entry
  belongs to the machine-global scope and reaches managed state through
  the section 9.4 migration, never through import.

A surface that is absent is simply not detected. A participating
secondary fixed-home target (section 7.6) joins the section 9.5 inventory
and backup but contributes no detected surface of its own: its unmanaged
root-context file is a lossy finding exactly when its bytes differ from
the same adapter's detected native root-context file, because those
distinct bytes would not carry over — the backup still preserves them.

**Classification.** An import is **lossless** iff every detected surface
maps onto a supported surface of the detecting adapter's revision:

- a root-context file maps when it can be read and is valid UTF-8 —
  reassembly normalization (below) is content-preserving and does not
  make an import lossy;
- a skills entry maps when the manager can recover a complete exact
  declaration from the entry's own records: a valid install marker
  (core §10) recording the source identity, declared ref, and resolved
  commit, or a git checkout whose `origin` remote canonicalizes under
  core §6.1 and whose committed `HEAD` carries no staged, dirty, or
  untracked bytes.

Every other detected surface is a **loss**: an unreadable file, a
root-context file that is not valid UTF-8, a skills entry with no
recoverable exact declaration, or a divergent secondary-target
root-context file. The **loss list** names each loss — adapter, platform
path, and reason — and an absence and a failed read stay different facts
(section 8.4): an absent surface never appears in the loss list, and a
failed read is always a loss, never treated as absence.

**Consent gate.** A lossless import proceeds without stopping. A lossy
import stops with `environment_import_lossy` and the loss list; it
proceeds only under an explicit per-operation consent flag, which
re-reports the loss list as warnings under the same diagnostic. Machine
configuration MUST NOT pre-record consent.

**Reassembly.** The manager assembles a context-package-shaped directory
inside the machine home (physical location implementation-specific,
manager §1):

- `agent-context.json`, `schema_version` 1, `name` `imported` unless the
  operator supplies a name under the core §2 grammar, `version` `1.0.0`,
  `weight` `0`, and no `weights`. A chosen name that is already installed
  stops the import with `profile_import_name_taken` before any write.
- One module `context/<env-id>.md` per adapter with a detected
  root-context file, carrying that file's normalized bytes with the
  selector `environments: ["<env-id>"]` and class `root`, listed in
  `context.modules` in ascending environment-identifier order.
  **Normalization** is exactly: every CRLF and bare-CR line ending becomes
  LF, and the content ends with exactly one trailing LF. It applies only at
  reassembly — the section 3 no-normalization rule for snapshot modules
  is untouched — and the original bytes are already in the section 9.5
  backup. An import with no detected root-context file emits no `context`
  member.
- One `requires.skills` entry per mapping skills entry, reproducing the
  recovered declaration pinned by `revision` to its resolved commit — the
  install marker's resolved commit when a valid install marker exists,
  otherwise the git checkout's committed `HEAD` — with the checkout's or
  marker's canonical identity as `git`. Each such entry is reported with
  the warning `environment_import_skill_foreign`: the skill was managed by
  other means, and the operator SHOULD re-declare it from its upstream
  source — a range or tag — to receive updates.

The assembled directory then installs through section 9.1 exactly as an
operator-supplied `path` source — snapshot copy, state-hash pin,
resolution of the pinned skills, always-strict audit; a blocking finding,
`context-secret-material` included, fails the import like any install.
Activation follows the section 9.1 rules without magic. The import writes
nothing into any native home by itself: replacing native files remains the
section 9.5 takeover path with its notice and backup.

### 9.7 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| foreign-manager symlink detected during onboarding | `environment_foreign_manager_detected` |
| dotfile-manager state detected, or repeated drift on one surface (warning) | `environment_foreign_manager_suspected` |
| audit finding from the secret-material detector class (blocking, unpinnable) | finding class `context-secret-material` |
| `class: system` module present in a context member (always warning) | finding class `context-system-module-present` |
| recorded secret-material waiver matches no finding (warning) | `context_secret_waiver_unmatched` |
| `--as <name>` or the root package name is already an installed profile name | `profile_name_taken` |
| more than one requirement flag, or a requirement flag or `--directory` with a `path` operand | `profile_install_ref_conflict` |
| `profile update` candidate lock carries a blocking finding on a new member; old lock stands | `profile_update_blocked` |
| `profile use` left a scope partially switched; recorded current unchanged (non-current) | `profile_use_partial` |
| `profile remove` names a profile that is current in any scope or an overlay of another profile | `profile_in_use` |
| skill or managed bin entry named `curator-*` | `environment_reserved_command_name` |
| lossy classification without the consent flag (stops with the loss list) | `environment_import_lossy` |
| lossy import proceeding under explicit consent (warning, loss list) | `environment_import_lossy` |
| imported skill declaration recovered from foreign records (warning) | `environment_import_skill_foreign` |
| chosen import profile name already installed | `profile_import_name_taken` |

`profile_index_ambiguous` is withdrawn with the multi-profile repository
shape; `--use` takes no name.

## 10. Resolution and the launch fragment

### 10.1 `env resolve`

The manager's only execution-facing primitive is:

```text
env resolve <env-id> [--profile <name>] [--repair] [--format json|env|shell]
```

It resolves a profile — the named one, otherwise the current profile for the
applicable scope — and an environment to a **launch environment fragment**.
Resolution is a pure function from (lock, precedence policy, environment,
machine configuration) to the fragment; it launches nothing and applies no
channel.

**Read-only by default.** Resolution verifies that the profile's managed
home for the environment is materialized and current, and the verification
is **lock-free**: it reads the marker and covers exactly the surfaces the
marker records — no more — and for a symlinked surface whose link targets an
entry of the immutable profile store, link-target identity is sufficient
currency (the store entry's integrity is the store's own invariant, section
4), so a launch does not re-hash a large skills tree. A home that is
unprovisioned, stale after `profile update`, drifted, or whose passthrough
is detached is **stale**: without `--repair`, resolve reports
`environment_home_stale` with the reasons and emits **no fragment** —
fail-closed, so that a launcher never runs an agent in a home the manager
knows is wrong without saying so. For a `claude_code` home in the
`referenced` form, the launch directory's missing project entry (section
7.4) is a staleness reason like any other. Under `--repair` the same
lock-free verification runs **first**, and a current home emits its
fragment without touching any lock; only when that verification finds the
home stale does resolve take the **repair lock** — the manager-home
mutation lock of manager §2.5, the same lock `profile use` holds — with a
bounded wait (implementation-documented, at least one second and at most
sixty), provisions or repairs the home from
the store entries the lock names as one journaled transaction —
re-materializing managed surfaces, re-linking passthrough entries,
reconciling XDG seeds, adding the launch directory's project entry,
never touching environment-owned mutable state,
unmanaged files, seeds, or backups — and then emits the fragment. Repair
restores managed bytes from the store; it MUST NOT adopt candidate bytes
found in the home. Lock acquisition that times out is
`environment_lock_unavailable`, distinct from `environment_repair_failed`,
which keeps meaning that the store cannot restore this home — an entry is
missing or fails validation. Neither emits a fragment.

The two lock classes this document names are the **mutation lock** (manager
§2.5: every write below the manager home, `profile use`, `profile update`,
`profile sync`, repair, garbage collection) and the **status read**, which
holds no lock. There is no per-home lock in revision 1. The window between
a completed repair and the child process's first read of the home is a
**recorded residual**: another same-user process can write into the home in
that window, and the marker is a record, not a signature (section 8.2). The
launcher MAY re-verify the recorded surface hashes immediately before exec
under its own specification; nothing here requires it.

`--format json` prints the `launch-env-fragment-v1` object as its CCJ-1
bytes ([`registry.md`](registry.md) §1) followed by exactly one LF — the
canonical form, so that the `works.relux.curator.fragment-digest` extension
key (Decision 0013 Decision 6.4) is `sha256:` over exactly these bytes
without the LF and is comparable across managers and releases. `--format
env` prints one `NAME=value` line per fragment variable, LF-terminated, in
the adapter's declared variable order. `--format shell` prints one POSIX
`export NAME='value'` line per variable with single-quote escaping; it is
POSIX-only by design, and automation on Windows or in PowerShell MUST
consume `--format json` — there is no `pwsh` format in revision 1. An
unregistered `<env-id>` is `environment_unknown`; an uninstalled `--profile`
operand is `profile_unknown`.

**`curator run`.** The launcher, `curator-run`, is the single composer of a
launch under Decision 0013 (Option A): it resolves the fragment first with
`--repair`, builds the interactive plan against the fragment's managed-home
path, composes argv as plan ++ system-prompt channel flags (under its
opt-in) ++ MCP channel flags ++ native arguments after `--`, composes the
environment as inherited ⊕ plan ⊕ fragment `env` ⊕ the engaged
`variable`-kind channel, bounds `env_names` under section 10.3, and either
delegates to `ax start --launch-plan -` or execs directly (Decision 0013
Decisions 6.3 and 6.4). Its provider mapping covers `claude_code`,
`codex_cli`, and `pi`; **`opencode` is `env_unsupported` for `curator run`**
in revision 1 — no agents-management system plugin exists for it — while
`env resolve opencode` and its managed homes are fully specified here and
an operator applies the fragment by hand. `env_unsupported` is the
launcher's diagnostic, not this document's.

### 10.2 `launch-env-fragment-v1`

The fragment is a closed object; readers MUST reject unknown fields,
unknown kinds, and unknown semantics or argument values:

```json
{
  "fragment": "launch-env-fragment-v1",
  "environment": "claude_code",
  "profile": { "name": "companyA-root-context-ios-developer-umbrella", "lock_sha256": "<64 lowercase hex>" },
  "precedence": { "winner": "higher-weight", "placement": "winner-last" },
  "env": { "CLAUDE_CONFIG_DIR": "<absolute managed-home path>" },
  "system_prompt": {
    "path": "<absolute path to .agent-context/system-prompt.md>",
    "channels": [
      { "kind": "flag", "semantics": "append", "flag": "--append-system-prompt-file", "argument": "path" },
      { "kind": "flag", "semantics": "replace", "flag": "--system-prompt-file", "argument": "path" }
    ]
  },
  "mcp": {
    "path": "<absolute path to .agent-context/mcp/claude_code.json>",
    "env_names": ["FIGMA_API_KEY"],
    "channels": [
      { "kind": "flag", "flag": "--mcp-config", "argument": "path", "with": ["--strict-mcp-config"] }
    ]
  }
}
```

- `profile` carries `name` and `lock_sha256` — the lock hash of section 1.3
  without the `sha256:` prefix — and nothing else. The fragment carries no
  source-kind, source-path, or member list: a consumer needs the pin, not
  the provenance; the marker and the lock hold the rest.
- `precedence` is an object carrying both primitives and is always present.
  There is no `composition` member: overlays are lock members, and the lock
  hash covers them.
- `env` maps each registry-declared variable name for the environment to a
  managed-home path.
- `system_prompt` is present exactly when the lock carries at least one
  applicable system module for the environment. It is data about a
  channel, never an applied override: `path` names the inert section 5.5
  file and `channels` reproduces the adapter's section 7.3 descriptors
  (`flag` with `flag`, `argument`, `name` when `argument` is `name`, and
  OPTIONAL `with`; `config-key` with `key`; `variable` with `variable`; or
  `file` with `filename`). Resolving a fragment activates nothing.
- `mcp` is present exactly when the adapter's resolved MCP set is non-empty
  and the adapter declares a channel (section 7.8): `path` names the
  section 5.8 file, `env_names` is the sorted union of the `env_names` of
  the servers in that adapter's set, and `channels` reproduces the
  adapter's section 7.8 descriptor without `semantics`. The example above
  is the `claude_code` shape; a `codex_cli` fragment's `mcp.path` names
  `<home>/curator-mcp.config.toml` and its single `mcp.channels` entry is
  `{ "kind": "flag", "flag": "-p", "argument": "name", "name": "curator-mcp" }`.
- `path_prepend` is a **reserved** OPTIONAL member: when present, exactly
  one absolute path below the manager-owned environments root that a
  launcher prepends to the child's `PATH`. Revision 1 never emits it
  (section 9.4); a reader MUST accept its absence and MUST reject any value
  outside the environments root.

### 10.3 The profile-influence boundary

Fragment variable names come only from the closed adapter registry.
Fragment values are absolute paths below the manager-owned environments
root. Profile bytes MUST NOT select, add, rename, or retarget an
environment variable and MUST NOT move a value outside that root; the only
profile-derived component of a value is the profile-name path segment,
bounded by the core §2 grammar — no separators, no traversal. A profile
chooses what the context says, never how a process is launched. This is the
package-influence boundary of the core execution policies, applied to
environment injection.

`env_names` are the one place package bytes name something about a launch,
and they name only which operator variables the launcher may pass through —
never a value. They never enter the fragment's `env`; they reach a launch
plan only through the launcher's environment-name allowlist, bounded twice
before the composer sees them: by the section 2.2 reserved-name exclusion
and by the lockable `passable_env_names` list of section 12.1. A name that
also appears in the composed environment literals is dropped from the
allowlist by the launcher with a warning (Decision 0013 Decision 6.3), so
the composed document is disjoint by construction.

### 10.4 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| operand names an unregistered environment | `environment_unknown` |
| named or current profile not installed | `profile_unknown` |
| managed home unprovisioned, stale, drifted, or passthrough detached; no fragment without `--repair` | `environment_home_stale` |
| repair could not acquire the mutation lock within the bounded wait | `environment_lock_unavailable` |
| managed home cannot be repaired from the store | `environment_repair_failed` |

## 11. Umbrella subcommand discovery

A CLI subcommand the manager does not implement resolves to an executable
named `curator-<name>` on `PATH` and is executed with the remaining
arguments verbatim — the established git/kubectl/docker external-subcommand
convention. The rules are closed:

- `<name>` is the operator's typed subcommand and MUST match the core §2
  identifier grammar; anything else is a usage error, not a lookup.
- An implemented subcommand always wins; discovery runs only for unknown
  names.
- The manager carries no knowledge of any provider: no provider registry,
  no provider-specific flags, no version coupling.
- A missing provider fails with the exact executable name and installation
  guidance; nothing is downloaded or installed implicitly.
- Profile data, marker data, and fragment data MUST NOT influence the
  dispatched name, the resolved path, or the argument vector. Dispatch input
  is operator argv and `PATH` alone.
- The resolved executable MUST NOT reside in a directory the manager itself
  publishes onto `PATH` — the user-bin shim directory, a managed skill bin
  directory, or any directory below the environments root — and a provider
  found there is refused with `subcommand_provider_untrusted`, naming the
  path. Together with the section 9.4 `curator-*` name reservation, this
  keeps profile-materialized files from poisoning the `PATH` the dispatch
  trusts; profile bytes were already excluded.

This is the one place the manager executes an executable it does not ship;
the trust model is exactly the host plugin convention named above. The
first providers, informative here, are `curator-run` (the launcher, its own
specification, Decision 0013) and `curator-session` (a shim to the agent
session manager).

### 11.1 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| unknown subcommand with no `curator-<name>` on `PATH` | `subcommand_provider_missing` |
| `curator-<name>` resolved inside a manager-published or managed directory | `subcommand_provider_untrusted` |

## 12. Status, machine configuration, and garbage collection

`profile list` reports every installed profile: name, root package name,
source identity, declared requirement (`range`, `tag`, or `revision` as
written), root version, lock hash, and current markers — the machine
default and every section 9.3 scope that differs. A `local` profile
reports `local` as its source, `-` for requirement, `0.0.0` as version, and
its lock hash. A `path` root reports `path` as its source, its recorded
source path as the identity, `-` for requirement, and whether it is
imported-from-native.

`env status [--check] [--json]` reports the
profile × environment × surface matrix: mode, form, materialized lock hash,
content-hash currency, drift, missing surfaces, marker validity,
unregistered adapters found in machine configuration, every declared
shadowing path that exists with its acknowledgment state, the lock's
context members with weights and the precedence primitives per activation,
every scope whose current profile differs from the machine default,
secondary-target probe and consent results with the standing note that each
participating target's embedded MCP configuration and `commands/` are
ungoverned, the passthrough liveness row per managed home, the recorded
seeds per managed home, the XDG seed state per managed `opencode` parent
with any `environment_seed_shadowed` entry, the standing `opencode`
split-brain note of section 7.1, the recorded and detected tool release per
adapter (section 7.9), both homes of the current profile per scope and
their provisioning state (section 8.1), backup generation counts and ages
per home (section 8.3), orphaned managed homes (section 9.2), and
`environment_context_size_exceeded` where it applies. Both commands follow
the manager §10 discipline exactly: recompute and report, never mutate — no
fetch, no repair, no adoption, no channel application, no onboarding.
`--check` returns non-zero when any row is non-current.

An installation row is current only when its marker is valid and supported;
profile identity, lock hash, member list, precedence, mode, and form match
the effective machine state; every recorded surface hash verifies; and
every recorded passthrough entry is live. A drifted, missing, shadow-inert
(unless acknowledged under `shadow_acknowledged`), detached, partially
switched, stale, or unreadable state is non-current; unreadable evidence is
reported as unreadable, never as absence (section 8.4). Warnings —
`environment_context_size_exceeded`, `environment_tool_version_unverified`,
`environment_seed_shadowed`, `environment_foreign_manager_suspected`, an
acknowledged shadowing path — never make a row non-current.

Garbage collection extends the manager §10 and core §9.4 rules: it runs
under the manager-home mutation lock, and its live roots additionally
include every store entry named by any installed profile's lock — and by
a retained previous lock until it is dropped (section 9.2) — every managed
home and in-place surface set referenced by a valid environment marker, and
every entry referenced by an in-flight transaction journal. An unreadable
marker or unprovable reference fails safe: the uncertain entries are
retained and the uncertainty reported. Environment-owned mutable state
inside managed homes is never collected, and backups are never collected.

### 12.1 Machine configuration knobs

Every machine-configuration surface this document names is one of the
following closed list, carried by `manager-config` schema 2 (the next
batch) under one `environments` object, so that no knob lives in an
implementation-private file. Names are given here so that the schema, the
CLI rows, and manager §12 spell them identically. Defaults apply when a
knob is absent.

| Knob | Values | Default | Section |
|---|---|---|---|
| `current_profile` | profile name or `null` | `null` | 9.2 |
| `scoped_current` | map env-id or target-id → profile name | empty | 9.3 |
| `overlays.<profile>` | ordered list of `{ source, range \| tag \| revision, directory?, weight? }` | empty | 6 |
| `overlay_default_weight` | non-negative integer | `1000` | 6 |
| `overlays_allowed` | boolean | `true` | 6, 12.2 |
| `precedence.winner` | `higher-weight`, `lower-weight` | `higher-weight` | 6 |
| `precedence.placement` | `winner-last`, `winner-first` | `winner-last` | 6 |
| `forms.<env-id>` | `monolithic`, `referenced` | adapter default | 7.2 |
| `system_prompt_files.<profile>.pi` | `off`, `append`, `replace` | `off` | 5.5 |
| `targets.<target-id>.participation` | `auto`, `off`, `enabled` | `auto` | 7.6 |
| `targets.<target-id>.consented` | boolean | `false` | 7.6 |
| `isolation.<profile>.<env-id>` | `shared`, `isolated` | `shared`; `isolated` for `claude_code` on macOS at the pinned release | 7.4 |
| `xdg_seed_allowlist` | list of XDG config entry names | `["git", "gh", "ssh"]` | 7.1 |
| `passable_env_names` | list of identifiers, or `null` for unbounded | `null` | 2.2, 10.3 |
| `mcp_package_allowlist` | list of canonical source identities | empty (permits all) | 2.2 |
| `shadow_acknowledged` | list of `{ env, path }` | empty | 7.5, 12 |
| `secret_material_waivers` | list of `{ pin, file, span: [start, end], reason }` | empty | 9.1 |
| `backup_retention` | non-negative integer, `0` = unlimited | `5` | 8.3 |
| `require_current_profile` | profile name or `null` | `null` | 12.2 |
| `in_place_mode.<env-id>` | `linked`, `copied` | adapter default | 8.1 |

Team distribution stays **per-machine** in revision 1: an organization
ships a bootstrap shape — a system-configuration file (manager §1) carrying
the locked knobs of section 12.2 and a documented `profile install` command
line — and each machine applies it; there is no fleet-push surface and no
knob is read from a package. Informative CLI rows (`profile compose`, `env
config`) that edit these knobs are the next batch's `cli/curator.md` work.

### 12.2 Lockable knobs

The manager §1 `locked` set is extended, for managers implementing this
capability, by exactly these keys under `environments`:
`overlays_allowed`, `precedence`, `mcp_package_allowlist`,
`passable_env_names`, `require_current_profile`, and `isolation`. A system
file that locks `require_current_profile` to a profile name makes `profile
use` of any other profile in the machine scope a configuration error under
the manager §1 locked-key rules, and `env status` reports the requirement;
a locked `overlays_allowed: false` empties every overlay list with the
manager §1 warning. The manager §1 credential rule stands: no key that
selects or constrains credential material is lockable, and `isolation` is
lockable only in the direction of `shared`.

A **non-overridable skill class** — a skill the root requires that no
overlay may re-require at another version — is not needed under joint
resolution, where an overlay that disagrees fails with
`context_range_conflict` and an overlay that agrees changes nothing; a
declared class is therefore out of revision 1, and per-skill fleet policy
beyond `overlays_allowed` returns with the registry protocol's package
index under its own review. This is the phasing statement the review asked
for.

## 13. Conformance surfaces

The following surfaces of this document are conformance-vector surfaces,
with schemas and vectors delivered separately (`schemas/v1/`, positive and
negative vectors, and byte-exact determinism vectors). Schemas:
`agent-context-v1` (section 2), `agent-mcp-v1` (section 2.2),
`context-lock-v1` (section 1.3), the rewritten `agent-environment-marker-v1`
(section 8.2), and the rewritten `launch-env-fragment-v1` (section 10.2)
— which requires `argument` on every `flag` descriptor and `name` exactly
when `argument` is `name`; the Decision 0012 §9 worked example, which omits
`argument` on its system-prompt descriptors, is read as pre-revision —
each with positive and negative schema cases; `profilefile-v1` and
`context-manifest-v1` with their cases are withdrawn. Vector families:
version and range parsing (section 1.4, including the coercion table and
the excluded forms); resolution (conflict, downward re-selection,
prerelease admission, exact-constraint unification); lock canonicalization
and hashing (CCJ-1 bytes and `lock_sha256`); the section 5 materialization
bytes — the `curator-root-context-v2` header, part joining, `## Context:`
chapter parts, the no-chapter case for a member without applicable modules
(replacing the retired empty-chapter vector), zero-module output,
referenced-form layout, and system-prompt output — under both `winner` and
both `placement` primitives; the section 5.6 hash binding; MCP
materialization bytes per adapter (section 5.8); the detector classes of
section 9.1 (`vectors/context-detectors.json`, positive and negative, the
waiver and unpinnable cases included); and the section 1.2 snapshot
byte-exactness vector (`vectors/snapshot-acquisition.json`). The nine
retired `expected/environments/*` sets are regenerated under the v2 type
line. A manager claiming this capability MUST pass the complete vector set;
there is no partial claim.
