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
  immutable snapshot and never adopts bytes from the source directory
  again: later edits to the source directory change nothing until the
  operator reinstalls, and nothing about a `path` source is ever fetched
  from a network. The section 4 boundary verification re-inspects the
  directory (`lstat`-class, metadata only) at every resolve but adopts no
  bytes. The snapshot contains only directories and regular files under
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
| installed profile's lock file is present but cannot be read or parsed | `environment_store_untrusted` (entry-class; never `profile_unknown`) |
| no candidate satisfies a name's effective constraint, or a final constraint is unsatisfied (names every requirer, its range or exact form, and the candidates considered) | `context_range_conflict` |
| `git` source with a signer allowlist whose selected candidate carries neither a tag signature nor a commit signature (names the source and the tag or commit) | `context_source_unsigned` |
| `git` source with a signer allowlist whose candidate signature verifies against no allowed signer, or fails verification (names the source, the tag or commit, and the signer seen) | `context_source_signer_rejected` |
| `git` source with no signer allowlist under `require_source_signers` (names the source) | `context_source_signers_missing` |
| manifest `version` differs from the version of the tag the package was resolved from | `context_version_mismatch` |
| root `weights` map names a package also named on a root requirement edge with a weight | `context_weights_duplicate` |
| root `weights` map names a package outside the closure | `context_weight_unknown` |

A missing `path` operand and an unreadable one are different facts (the
section 8.4.1 discipline): `profile_source_path_missing` never fires on a
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
authorization token or provenance proof (core §10 discipline). The
signature check lives in resolution (section 1.4): for a `git` source with
a signer allowlist (section 12.1) the selected candidate's tag or commit
signature MUST verify before the candidate enters the lock. Verification
results are `env status` posture (section 12), not lock content.

The lock file itself is verified under the section 4 protected-boundary
contract: on every `env resolve`, and again under the manager-home
mutation lock for every mutating profile operation, the manager MUST verify
the lock file's ownership, private mutation permissions or DACL, regular
file type, and link safety before trusting the lock it names. A lock file
that fails the contract makes the profile `environment_store_untrusted`
(section 10.1). Lock reads follow the section 8.4.1
absence-versus-read-failure rule (lock row): an absent lock file is the
not-installed condition (`profile_unknown`), while a lock file that is
present but cannot be read or parsed — permission, I/O, or path errors,
undecodable bytes, content that fails parsing or schema validation — is
entry-class `environment_store_untrusted` (section 4), never
`profile_unknown`, and is never rebuilt from (section 8.4.1, lock row).

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
**stable** version. `latest` stays `*` under signer verification: with an
allowlist it follows every signed in-range tag of that source, without one
it follows any tag — the named residual of finding E1. The strict-tag
policy covers a *moved* tag, not a *new* one (section 9.2). A range that
does not parse is `profile_source_invalid`.

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

**Signer verification.** For a `git` source that carries a signer allowlist
(section 12.1), resolution verifies the selected candidate's signature
before the candidate enters the lock. The check applies to every selection
from the source — by range or by exact `tag` or `revision`, for every
closure member kind. The selected candidate's annotated tag signature OR
the signature of the commit it peels to MUST verify against an allowed
signer; either suffices. A `revision` selection carries no tag, so only
the commit signature can satisfy the check. Verification failure is a
resolution error and the operation fails closed: `profile install` MUST
fail, and `profile update` MUST leave the old lock in place. The three
failures are mutually exclusive:

- neither the tag nor the commit carries a signature:
  `context_source_unsigned`, naming the source and the tag or commit and
  stating that no signature was found;
- a signature is present but verifies against no allowed signer, or the
  verification itself fails: `context_source_signer_rejected`, naming the
  source, the tag or commit, and the signer the signature claims;
- under `require_source_signers` (section 12.1), a `git` source with no
  allowlist: `context_source_signers_missing`, naming the source.

A verification failure is not a constraint: the manager MUST NOT silently
select a lower candidate — step 3 re-selection never fires on it. A `path`
source and the synthesized `local` root carry no signature material and
are never verified. A source mapped to an empty allowlist has an allowlist
that admits no signer: every candidate of that source fails — unsigned as
`context_source_unsigned`, signed as `context_source_signer_rejected`.

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
| MCP declaration carried by a `path`-kind package — a root, an overlay, or an onboarding import — at resolution (names the package and the declaration) | `mcp_declaration_path_source_refused` |
| the MCP package allowlist is empty at install, update, or status under the `permissive` posture (warning: every declaration package in the closure is admitted) | `mcp_package_allowlist_empty` |
| the MCP package allowlist is empty under the `hardened` posture while the resolved closure carries an MCP declaration package (resolution error at install/update; non-current at status) | `mcp_package_allowlist_empty` |
| S4 profile `s4-warn`: a launch passes an operator variable not listed in an explicitly configured `passable_env_names`, or any passed operator variable when the knob is absent (warning, names the variables and the knob) | `mcp_env_passthrough_unlisted` |
| S4 profile `s4-enforce`: a requested name outside the effective `passable_env_names` is dropped from the launch allowlist (warning, names the variables) | `mcp_env_passthrough_dropped` |

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
and the rest) — and machine configuration bounds the passable names by the
lockable `passable_env_names` allowlist (section 12.1): only a listed
name's operator value may reach a launch. Under the revision-1 rule (S4
profile `s4-enforce`, section 10.3) an absent knob is the empty list, so
nothing passes unless the operator opts a name in; an explicit `null`
keeps meaning unbounded — every requested name passes — as an explicit,
lockable-away operator choice. Under the `hardened` machine posture
(manager §7.1) an explicit `null` is refused instead (section 10.3).
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
every network identity, as core §6.1 — and that state always warns:
`profile install`, `profile update`, and `env status` MUST emit
`mcp_package_allowlist_empty`, stating that every declaration package in
the closure is admitted. Under the `hardened` machine posture (manager
§7.1) the warning becomes a resolution error — the same code — for any
profile whose resolved closure carries an MCP declaration package:
install and update MUST fail without writing or changing the lock, and
`env status --check` MUST report the row non-current. Under `hardened`
with no MCP declaration in the closure the empty allowlist keeps warning
and the operation proceeds. The refusal fires however the empty value
arrived — absent, explicit, or locked — since it is the profile's meaning,
not a default the operator can keep by writing it down (manager §7.1).

**Source kind: `git` only.** An MCP declaration package MUST resolve from
a `git` source. A `path`-kind package — a root, an overlay, or an
onboarding import (sections 6, 9.1, 9.6) — MUST NOT carry an MCP
declaration: resolution MUST refuse a closure whose `mcp` member carries
no canonical source (a `state_sha256` pin) with
`mcp_declaration_path_source_refused` (error), naming the package and the
declaration — never admitted, never warned-through. A `path` source has
no canonical identity for the allowlist above and is never verified
(section 1.4), which is why it may not carry declarations; the allowlist
is total over canonical identities.

### 2.3 MCP declaration surfacing

A `stdio` declaration names a program the agent tool executes at launch
(section 10.3), so the operator sees every declaration before it can run.
At `profile install` (section 9.1) and `profile update` (section 9.2) the
manager MUST print, after the audit gate passes and before the lock is
published or any surface is (re-)materialized, one surfacing row per MCP
declaration package in the resolved closure, in ascending package-name
byte order. `env status` (section 12) repeats the same rows for the
current profile of each scope it reports. The row columns are closed, in
this order:

| Column | Content |
|---|---|
| `package` | the declaration package's name |
| `version` | the declaration package's resolved version |
| `transport` | exactly `stdio` or `http` |
| `command` | the `stdio` `command`; exactly `-` when `transport` is `http` |
| `args` | the `stdio` `args` as a JSON array with no spaces; `[]` when `transport` is `http` |
| `env_names` | the declaration's requested `env_names` in declared order, as a JSON array with no spaces |

Each row is one line of the form

```text
mcp-declaration <package> <version> <transport> command=<command> args=<args> env_names=<env_names>
```

terminated by exactly one LF. Strings inside `args` and `env_names` are
JSON double-quoted strings. When the resolved MCP set is empty the manager
prints no surfacing row. Surfacing is informative: it emits no diagnostic
and never fails the operation.

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

**System-module admission.** A package is **direct** when it is the root
itself, when it is an active overlay (section 6), or when it is named by
the root's or an active overlay's `requires.contexts` entry; every other
`context` member — reached only through another package's `requires` — is
**transitive**. Only the system modules of direct packages, and of
transitive packages admitted by a `system_module_waivers` entry (section
12.1) naming the package, are **admitted**. The section 5.5 system-prompt
output and the section 10.2 fragment `system_prompt` section MUST contain
only admitted system modules. The machine policy `transitive_system_modules`
(section 12.1) is exactly `drop` (default) or `error`:

- Under `drop`, a non-admitted applicable system module MUST be skipped at
  materialization, and the manager MUST emit the warning
  `context_system_module_dropped` naming the package and the module path;
  the materialized bytes MUST be exactly the admitted modules' bytes.
  Resolution, installation, and update MUST NOT fail for admission.
- Under `error`, resolution of the same module MUST fail with the resolution
  error `context_system_module_transitive` naming the package and the module
  path — the first such module in emitted order, manifest order within a
  package — and the manager MUST NOT write or change the lock: `profile
  install` MUST fail, and `profile update` MUST leave the old lock in place.

**`path` sources.** The direct-naming rule above applies as is to `path`
members: a `path` root or overlay is direct, and a `path` package reached
only through another package's `requires` is transitive — a lock
resolution cannot produce, because `requires` entries are `git`-only
(section 2) — with its system modules non-admitted exactly like any
transitive package's. A `path` source is never verified (section 1.4),
which is why
its system modules are admitted only under this rule AND only after its
directory passes the section 4 protected-boundary contract at every
resolve and before any materialization, exactly like a store entry: a
`path` source that fails it is `environment_store_untrusted` (section 4),
not an admission verdict — no fragment, non-current, posture row naming
the path and the failing check — with no rebuild. The boundary check is
on the directory, not on the content class: a `path` source without
system modules passes the same contract (sections 6, 9.6).

The `context-system-module-present` finding class (section 9.1) is
unaffected by admission: it MUST report every `class: system` module of every
member at install and update, admitted or not, so system-prompt provenance
never depends on the machine policy.

### 3.1 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| module manifest malformed, unknown field, duplicate or invalid entry | `context_manifest_invalid` |
| declared module file absent or not a regular file | `profile_module_missing` |
| module not UTF-8, non-LF line ending, or trailing-LF violation | `profile_module_bytes_invalid` |
| selector names an unregistered environment (warning) | `profile_selector_unknown_environment` |
| transitive system module under the `error` policy | `context_system_module_transitive` |

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

The environments root and every store entry are **protected state** in the
core §9.3 sense: manager-created, manager-protected, and resolved
independently of package input. Resolution and materialization MUST reuse a
store entry only below that protected state. On every `env resolve`, and
again under the manager-home mutation lock for every mutating profile
operation — install, update, use, sync, repair, garbage collection — the
manager MUST verify ownership, private mutation permissions or DACL,
containment, regular file types, and link safety for the environments root,
the profile store root, the profile lock file (section 1.3), the
environment marker of every home the operation reads or writes (section
8.2), and every store entry the lock names:

- **ownership** — every verified path is owned by the operator;
- **permissions** — private mutation permissions, or the platform DACL
  equivalent: no identity other than the operator may mutate a verified
  path;
- **containment** — every store entry path resolves below the environments
  root without leaving it; an entry path that escapes the root is
  untrusted wherever it points;
- **regular file types** — every store component is a directory or a
  regular file; a special file below the store is untrusted;
- **link safety** — verified by `lstat`, never by following links: no
  symlink at the environments root, at a store entry root, or at any
  component below the store root the manager did not create. The manager
  creates no symlink below the store root — entries are immutable
  regular-file trees — so any symlink there is untrusted.

Store integrity is verified against the pin, not the marker. For every
store entry the lock names, the manager MUST recompute the entry's tree
hash from its bytes and require it to equal the pin: for a `git` member
the git tree object identity of the pinned commit (or the recorded
snapshot tree hash the lock carries), for a `path` or `local` member the
`state_sha256` (core §8 content hash, section 1). This check needs no home
marker and runs at every `env resolve` and before provisioning or repair
of any home. Missing hashes never count as passed: an entry whose tree
hash cannot be recomputed, or whose expected pin hash is absent, fails.

Two failure classes, in order. (a) An enclosing boundary that cannot be
proven — the environments root or the profile store root (wrong owner,
world/group-writable permissions, symlinked, not a directory, not
contained) — refuses every mutating operation before its first write and
every resolve (no fragment); nothing is rebuilt, because there is no
protected place to rebuild into; `env status` reports the row non-current
naming the boundary (section 12); the operator repairs the boundary out of
band. (b) An individual entry — a store entry, the lock file, or a marker
file — that fails its own boundary checks or its pin hash — or, for the
lock file, cannot be read or parsed (section 8.4.1, lock row) — inside a
proven enclosing boundary is `environment_store_untrusted`; a real operation
rebuilds it from the revalidated snapshot into newly established protected
state (operation-private staging, atomic publication under the mutation
lock), except a lock file that cannot be read or parsed, which is never
rebuilt from (section 8.4.1, lock row): no mutating operation rebuilds,
re-materializes, or replaces anything from the unreadable evidence.
Dry-run evaluation of a boundary-or-hash entry-class failure reports
`would-rebuild-untrusted-store` and mutates nothing; dry-run evaluation
of an unreadable or malformed lock reports `environment_store_untrusted`
with no rebuild planned and mutates nothing. Resolve fails closed (no
fragment, non-current) until rebuilt — or, for the unreadable lock, until
the operator recovers out of band. Verification order is enclosing
boundary → entries → pin hashes →
home currency (section 10.1). An implementation that cannot prove the
enclosing boundary MUST fail closed as in (a); an implementation that
cannot prove an entry boundary or pin hash MUST fail closed as in (b).
Self-consistent lock, marker, and hash bytes do not repair or authenticate
an untrusted boundary.

**`path` source directories.** The contract extends to the declared
directory of every `path` source the lock names — a root, an overlay, or
an onboarding import (sections 6, 9.1, 9.6). On every `env resolve`, and
again under the manager-home mutation lock for every mutating profile
operation — install, update, use, sync, repair, garbage collection — the
manager MUST verify the five boundary checks for the directory, with the
declared directory as the root the checks are relative to:

- **ownership** — the directory and every component below it are owned by
  the operator;
- **permissions** — private mutation permissions, or the platform DACL
  equivalent: no identity other than the operator may mutate the
  directory or any component below it;
- **containment** — every component resolves below the declared directory
  without leaving it; a component that escapes it is untrusted wherever
  it points;
- **regular file types** — every component below the declared directory
  is a directory or a regular file; a special file is untrusted;
- **link safety** — verified by `lstat`, never by following links: no
  symlink at the declared directory or at any component below it. The
  manager creates no symlink below the declared directory, so any symlink
  there is untrusted.

The verification inspects the directory but adopts no bytes from it:
later edits to the source directory change nothing until the operator
reinstalls (section 1), and no pin is recomputed against the live
directory — the member's `state_sha256` pin remains the integrity
baseline for its store entry as above. A `path` source that fails the
contract is entry-class `environment_store_untrusted` for that profile:
resolve emits no fragment, status is non-current, and `env status`
reports the row naming the path and the failing check (section 12).
There is no rebuild: the source is the operator's directory, and the
operator fixes it out of band; a real operation MUST NOT re-copy the
directory into the store to clear the verdict. For dry-run purposes the
failure is not in the entry-rebuild branch of (b) above: dry-run
evaluation of a `path` source directory failure reports
`environment_store_untrusted` with no rebuild planned and mutates
nothing — never `would-rebuild-untrusted-store`, which names only a
store entry or marker file failure, or a lock boundary-check failure,
that a real operation would rebuild (section 10.1).

The contract is not configurable: no knob narrows, widens, or disables it.
Rollout is direct (impact row "S5"). Rollout of the `path`-directory
extension is direct (impact row "E6": under the hood).

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
path. Every write below follows the section 8.3.1 write discipline: the
manager replaces directory entries and never writes through a symbolic
link.

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
  asks. The same guard skips a user-level `$CLAUDE_CONFIG_DIR/CLAUDE.md`
  that is itself a symbolic link or a hard link (`nlink > 1`) while the
  key is unset (**verified** from the 2.1.261 bundle; the guard keys on the
  memory type `User`, not on which directory `CLAUDE_CONFIG_DIR` names), so
  the `claude_code` root-context surface is materialized as a regular file
  (a copied surface in the sense of section 8.1) in every mode and every
  home — managed, `linked` in-place, and `copied` — never as a link,
  whatever the form. The managed home is never the launch directory, so every reference
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

The admitted applicable system modules (section 3) — of every `context`
member in emitted order — materialize as one file assembled by the
part-joining rule with **no generation header and no chapter parts**:
system-prompt bytes reach the model verbatim, so no generated text is
injected. Provenance and drift detection for this surface come from the
environment marker's recorded content hash, not from an in-file header.

The system output materializes only into managed homes (section 8.1), at:

```text
<home>/.agent-context/system-prompt.md
```

This file is inert: no revision-1 tool reads that path natively. It exists
so the launch fragment (section 10.2) can name it. When the lock carries no
admitted applicable system modules, the file is absent and the fragment
carries no system-prompt section. The `.agent-context/` directory also
carries the `mcp/` sibling of section 5.8.

Under the default `drop` policy (section 3), a non-admitted applicable
system module is skipped: the file holds exactly the admitted modules'
bytes, and materialization warns `context_system_module_dropped` naming
the package and the module path. The fragment's `system_prompt` presence
(section 10.2) follows the same admitted set, and it continues to drive
the Decision 0013 `works.relux.curator.system-modules` extension key, so
`ax` resume still refuses on drift.

Rollout (E2): the default `drop` policy is non-breaking — resolution,
installation, and update never fail for admission; only the materialized
system-prompt bytes omit non-admitted modules — so no warn-first split
applies; `error` is opt-in strictness selected in machine configuration
or locked to `error` by system configuration (section 12.2).

For `pi` only, machine configuration MAY additionally set, per
profile × environment, `system_prompt_files` to exactly `off` (default),
`append`, or `replace`. `append` materializes the system output additionally
at `<home>/APPEND_SYSTEM.md`; `replace` materializes it at
`<home>/SYSTEM.md`. These are native discovery channels subject to the
flag and trusted-project precedence in section 7.3. Under `off` neither
file is written: Curator materializes no active system-prompt file, but
native flags or trusted project-local files can still supply a prompt. System
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
| transitive system module skipped under the `drop` policy (warning; section 5.5) | `context_system_module_dropped` |
| transitive system module under the `error` policy (section 3) | `context_system_module_transitive` |

### 5.8 MCP launch-channel output

The resolved MCP set of a profile for an adapter — the lock's `mcp` members
whose `environments` selector applies to that adapter — materializes as one
inert, hashed, marker-recorded file per adapter, in a managed home only.
Its write is a section 8.3.1 write.
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

A `path` overlay passes the section 4 protected-boundary contract at
every resolve and before any materialization, exactly like a store
entry — the check is on the directory, not on the content class — and a
`path` overlay that fails it is `environment_store_untrusted` with no
rebuild (section 4). A `path` overlay MUST NOT carry an MCP declaration
(section 2.2).

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
Reconciliation presence checks follow the section 8.4.1
absence-versus-read-failure rule (seed row): an allowlisted entry whose
state cannot be established is never treated as absent — a recorded seed
whose target cannot be statted for any reason other than absence is kept,
nothing is seeded from an entry that cannot be read, and the operation
reports `environment_seed_unreadable`.
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
rejected as unknown options. Its native `--system-prompt` value suppresses
`SYSTEM.md` discovery.
The registry above exposes replacement through its `SYSTEM.md` file
descriptor; it does not add a native replace-flag descriptor. Its
`--append-system-prompt <text>` is **polymorphic**: it takes text or file contents, and a path that does not
resolve is sent as literal prompt text. The descriptor therefore records
`argument: path` with the polymorphism, and the launcher MUST verify that
the path is a readable regular file immediately before exec and fail rather
than let the tool interpret a dead path as prompt text — the read-failure-
as-absence class section 8.4.1 bans, applied at launch. The `codex_cli`
config key is **verified** present in the codex configuration surface
(0.153.2); that a per-invocation `-c model_instructions_file=<path>`
override applies it is docs-confidence.

**Admission rule.** A `flag` descriptor with `argument: path` is admitted to
the registry only when the pinned release is verified to accept a file path
in that position; a flag that accepts only text is recorded with
`argument: contents` or not at all. In pi 0.84.2, a native
`--system-prompt` value suppresses `SYSTEM.md` discovery, and native
`--append-system-prompt` values suppress `APPEND_SYSTEM.md` discovery:
a flag and a discovered file of the same semantics are alternatives, not
additive. When discovery applies, an existing trusted project's
`<cwd>/.pi/SYSTEM.md` or `<cwd>/.pi/APPEND_SYSTEM.md` takes precedence
over the corresponding agent-home file. This is **verified** in
`dist/core/resource-loader.js` (0.84.2, source selection at lines 380/386,
discovery at lines 808–829). Section 5.5 keeps the managed-home files absent
unless machine configuration explicitly materializes one.

**Recorded residual.** The launcher's managed-home probe does not probe
trusted project-local `.pi` files or establish the tool's trust decision.
Managed-home absence therefore does not prove that Pi will discover no
system prompt; materialization remains managed-home-only and default off.

Channel descriptors are data about a channel: nothing in this document applies one.
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
| `codex_cli` | `auth.json` | `keyring-preferred`: where the operator's `config.toml` sets `cli_auth_credentials_store` to `keyring` the credential is ambient and no entry is linked; under `file` (the default) or `auto` the managed `auth.json` is a `file-link` — a symlink to the native file, re-checked by the liveness row. The manager assumes the keyring identity is operator-global (independent of `CODEX_HOME`) until a disposable-account scratch-`CODEX_HOME` probe proves per-home scoping, so under `keyring` or `auto` storage `isolated` is `environment_isolated_unsupported`. An absent `cli_auth_credentials_store` key means effective `file` storage, so `isolated` is admitted; a storage selector outside the verified `file`/`keyring`/`auto` set fails closed with `environment_credential_unsupported` | **verified** in-place: codex 0.153.2 rewrites `auth.json` by truncate-and-write on the same inode, mode 0600, never temp-and-rename (upstream `login/src/auth/storage.rs` for the path the binary names); `cli_auth_credentials_store = file|keyring|auto` **verified** in the embedded configuration docs |
| `opencode` | none — auth lives in `XDG_DATA_HOME`, which the config swap never touches (section 7.1) | ambient | — |
| `pi` | `auth.json` | `file-link` — the managed `auth.json` is a symlink to the native `~/.pi/agent/auth.json` (native root `~/.pi/agent`, not `~/.pi`), re-checked by the liveness row | **verified** in-place: pi 0.84.2 rewrites its agent-root `auth.json` with a single in-place write, mode 0600, under its own lockfile, never temp-and-rename (installed `core/auth-storage.js`) |

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
caught by the liveness row — reported detached, re-linked when the link
path is absent, refused with `environment_credential_conflict` when the
detach left a regular file; and every
file-shaped strategy is watched by the **liveness row** —
`env status` MUST report `environment_passthrough_detached` (non-current)
when a recorded passthrough entry is no longer a symlink or no longer
targets the native entry. A link path that is absent is re-linked by
`env resolve --repair`, leaving the native bytes untouched; a link
path that instead holds a regular file or a symlink to an unexpected
target is the refusal `environment_credential_conflict` — repair MUST
NOT remove, replace, or re-point it, and emits no fragment. A recorded
entry whose link state
cannot be established — `lstat` or `readlink` fails with permission, I/O,
or path errors — is not detached (section 8.4.1, passthrough row): `env
status` MUST report `environment_passthrough_unreadable` (non-current,
currency unknown), `env resolve` MUST report it the same way and emit no
fragment, and `--repair` MUST NOT re-link the entry: repair leaves it
untouched for the operator to make readable. A directory at the entry path
is "no longer a symlink" and stays detached-side: it is
`environment_passthrough_detached`, re-linked by `--repair`, which
removes only an empty directory — a non-empty one fails the repair
with `environment_credential_conflict` instead of destroying its
contents. Where the pinned release's write
behavior is verified in-place, a manager MAY record the entry as
`in-place` and skip nothing: the liveness row runs regardless. An
in-place rewrite has its own hazard, recorded here although nothing in this
document copies a credential file: a reader that snapshots `auth.json`
mid-write can observe a truncated file, so any such copy is taken under the
tool's own lock or while the tool is idle.

The default per profile × environment is `shared`: every managed home reuses
the operator's existing authentication through exactly these entries. The
`isolation` knob selects credential-store sharing, not a security
sandbox: `isolated` is bounded store separation — the managed home does
not share the declared credential stores with the native home — never
account separation (ambient auth such as helpers, cloud credentials,
auth variables, and native selectors is unchanged) and never
filesystem isolation. `isolated` — no passthrough, the tool
authenticates fresh inside the managed home — is **unsupported in
revision 1** for `opencode`, where it is a no-op because auth lives
outside the swapped config home, for `claude_code` on macOS **below
the pinned release 2.1.261**, for which no evidence covers how a
managed home's login interacts with the native Keychain item, and for
`codex_cli` under native `keyring` or `auto` storage, whose identity
is assumed operator-global (passthrough table above): under `auto`
the tool uses the keyring when one is available and the file-link is
inert there, so an `isolated` home on a keyring host would
authenticate through the operator-global keyring. Configuring
`isolated` for any of these is the configuration error
`environment_isolated_unsupported`, never a silently shared home. A
future revision may admit `auto` only where the manager proves the
effective store is `file`, probe-gated.
For `claude_code` on macOS **at or above 2.1.261** the evidence is positive and
the restriction is lifted: the tool selects the Keychain item by
`CLAUDE_CONFIG_DIR` (the passthrough table above), so a managed home is
credential-isolated **by construction** — it never sees the native item
and a fresh `CLAUDE_CONFIG_DIR` reports "Not logged in" (**verified**). The
same fact removes `shared`: there is no Keychain item a manager could link
without handling credential material, which section 7.4 forbids. The
adapter therefore declares `isolated` as the platform default for
`claude_code` on macOS at the pinned release, and a configured `shared` is
the configuration error `environment_shared_unsupported`. The recorded
residual is answered negatively: a 2.1.273 managed-home login wrote a
`.credentials.json` file under `CLAUDE_CONFIG_DIR` and no suffixed
Keychain item appeared — the native item untouched, cause unknown — so
no verified `shared` store exists and `shared` stays refused until an
authorized disposable-account experiment proves which store Claude
reads first, whether the file is rewritten in place on refresh, and
under which conditions, if any, a suffixed item is written; the
verified selection scheme stands regardless. `isolated` remains
available for `codex_cli` under `file` storage only — including an
absent `cli_auth_credentials_store` key, which resolves to effective
`file` — for `pi`,
and for `claude_code` on Linux. Sharing is defined by the native
home's effective storage alone: a managed `config.toml` that diverges
from the native selection changes nothing, and the manager never
rewrites either file to realign them. The operator's machines have no cli_auth_credentials_store key in config.toml, so the platform default file applies and isolated is admitted; the operator's profile design relies on that platform default and on nothing more from 0017.

**Migration.** A mode change is never applied by repair: changing the
effective mode of a provisioned home runs an explicit inspect → plan
→ apply migration under the manager lock. The migration inventories
the old marker, every link target, and both Pi roots (`~/.pi/auth.json`
and `~/.pi/agent/auth.json`); preserves the effective mode on upgrade;
unlinks only a recorded link still targeting the declared native
store; and never copies secret material at any step. On an isolated →
shared conflict — the managed home holds credential bytes a link
would displace — the migration reports both sides and stops: the
operator resolves the conflict out of band and re-runs. The recorded
2 B `~/.pi/auth.json` is unlinked as a recorded link of the wrong
target, never deleted as a native file. Operator evidence
2026-09-21: on the operator Mac the managed Pi home links to
`~/.pi/auth.json`, which does not exist — the real credential is
`~/.pi/agent/auth.json` — so the link is dangling, and `env status`
is silent about it. A dangling or mis-targeted credential link is
reported, never silent: `env status` (and `resolve`) report it with
`environment_credential_conflict`-class wording (curator follow-up
F-C1). On the operator Mac, ~/.curator/environments/default/pi/auth.json points to ~/.pi/auth.json; that target does not exist, the real credential is ~/.pi/agent/auth.json, and env status does not show the dangling passthrough as detached. env status and resolve report dangling or mis-targeted credential links as detached, with environment_credential_conflict-class wording instead of silence.

**Credential record.** Decision 0017 choice 5 defines the schema-2
credential record in `agent-environment-marker-v2.schema.json`
(`schemas/v1/agent-environment-marker-v2.schema.json`). Every schema-2
passthrough record MUST carry `isolation` (the effective `shared` or
`isolated` mode), `strategy`, `source_role` (`native` when the
bytes are owned by the native home, `managed` when they are owned by
the managed home), `backend` (`file`, `keychain`, or `ambient`),
`backend_version` (the non-empty verified tool release), and
`provenance` (`provisioned`, `repaired`, or `migrated`). A
linkless record MUST omit `path`: this applies to the `ambient`
strategy or backend and to `per-home-keychain` when `isolation` is
`isolated`. Every other passthrough record MUST carry its home-relative
`path`. Schema 2 encodes these requirements and rejects additional
record members.

A schema-1 marker retains passthrough entries with `path` and
`strategy` only; the manager MUST NOT rewrite it solely to add the
schema-2 credential record. If a successful manager-home mutation
already requires publishing a replacement marker for another state
change, that publication MUST use schema 2 and include the complete
credential records. There is no standalone marker-upgrade write. If the
mutation rolls back, journal recovery MUST restore the exact preceding
marker bytes, including its schema version.

Marker publication MUST occur under the manager-home mutation lock in
the same journal-protected transaction as the mutation. The manager
MUST write the complete marker to a temporary file in the marker's
directory and atomically rename it into place; rollback MUST restore the
preceding marker. Backup discovery MUST inspect auth paths with
`lstat` and MUST NOT follow auth symlinks. Backups MUST NOT archive
credential bytes or traverse a symlink to credential bytes.

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
| `codex_cli` | `config.toml` — copied under the seed rule below: revision A copies it whole (project trust, model, and MCP tables included); revision B copies every top-level member except `mcp_servers` (the `mcp_servers` table and every `mcp_servers.*` sub-table removed); the launch channel of section 7.8 layers the profile's MCP set over the seeded base in both revisions | that the copied file is parsed in the fresh home is **verified** (0.153.2); that a `projects.<path>.trust_level` entry does **not** lift the `exec` git wall is **verified** (section 7.9 `exec_flags`); that a whole-copy home lists the native `mcp_servers` entries is **verified** (0.153.2 — the revision-A and pre-rule behavior; revision B strips them); the remaining member shapes are **docs-confidence** |
| `opencode` | none — the XDG seeds of section 7.1 are the analogous class | — |
| `pi` | `settings.json`, `models.json` | that a fresh dir loses them and re-downloads its tool trees is **verified**; their shapes are docs-confidence |

**Codex seed MCP rule.** A whole-copy `codex_cli` seed inherits every
native `mcp_servers` entry into the managed home, outside the profile's
lock and outside the section 2.2 allowlist, while the section 7.8 channel
layers the profile's set over that base — the asymmetry the section 7.8
residual table records. The seed rule therefore ships in two explicitly
labelled revisions; a manager MUST ship revision A before revision B:

- **Revision A (warning release).** The seed is still copied whole, but
  provisioning MUST emit `mcp_native_servers_ungoverned` (warning) naming
  every native `mcp_servers` entry the home inherited, stating that the
  next revision stops inheriting them, and carrying the migration hint:
  declare the server in the profile's MCP set, or accept the loss. `env
  status` MUST list those entries per managed `codex_cli` home as
  ungoverned — outside the lock and the section 2.2 allowlist.
- **Revision B (flip release).** The seed copies `config.toml` with the
  `mcp_servers` table and every `mcp_servers.*` sub-table removed — the
  seeded file carries the trust, model, and TUI configuration, every
  top-level member of the native file except `mcp_servers`, and MUST parse
  as TOML — and provisioning MUST report the stripped names once with
  `mcp_native_servers_not_inherited` (warning). A managed `codex_cli`
  home provisioned under revision B runs only the profile's MCP set
  through the section 7.8 channel. `env status` MUST list the stripped
  entries per managed `codex_cli` home as not inherited.

Both revisions write the `codex_seed_record` marker record of section 8.2
at provisioning: the `revision` (`A` or `B`) and the snapshot of the
native `mcp_servers` entry names taken from the native file at
provisioning time — names only, never server commands or env values. The
provisioning warning under either revision fires exactly when the snapshot
is non-empty: a native file with no `mcp_servers` entries warns nothing,
and the record is still written with an empty snapshot. The rule applies
at provisioning only: seeds are thereafter owned by the tool, and an
existing home keeps its bytes. The manager-shipped seed-rule revision and
the home's recorded seed revision are distinct: a managed `codex_cli`
home provisioned under revision A and now served by a revision-B manager
keeps its inherited servers, `env status` MUST list their recorded names
as ungoverned, and the home reports `mcp_seed_unstripped` (warning) with
the repair hint (re-provision) — unless the recorded snapshot is empty,
in which case there is no inherited server and the mismatch warns
nothing. A managed `codex_cli` home whose marker predates the rule — the
record is absent — reports the same warning with the same hint.

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
write (section 8.4.1, seed row). A seed path that is not a regular file —
a symlink, directory, or special file — is unreadable-side: provisioning
stops with `environment_seed_unreadable`, never by copying through the
link nor by skipping the seed as absent. Under revision B, native
`config.toml` bytes that do not parse as TOML are likewise
`environment_seed_unreadable`: the strip cannot be computed, so
provisioning stops rather than seeding whole or skipping.

**Isolation matrix.** What a managed home isolates per adapter, in revision
1, normatively:

| Environment | Root context, system prompt, MCP set | Skills | Session state and caches | Authentication | Tool configuration |
|---|---|---|---|---|---|
| `claude_code` | per profile (managed home) | per profile (`<home>/skills/`) | per profile | macOS: isolated, always, at the pinned release (per-`CLAUDE_CONFIG_DIR` Keychain item; `shared` refused until the Decision 0017 experiment passes); Linux: shared by default, `isolated` available | seeded `.claude.json` (minimal object plus per-launch-directory project entries), then per home |
| `codex_cli` | per profile | per profile | per profile | shared by default, `isolated` available under `file` storage only (`isolated` refused under `keyring` or `auto` storage) | seeded once from the native `config.toml`, then per home |
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
The existence check uses `lstat`-class semantics (section 8.3.1): a
symlink at a declared shadowing path counts as present and is never
dereferenced. An `lstat` that fails for any reason other than ENOENT-class
absence is not absence (section 8.4.1): the path is reported as
`environment_shadowing_path_present` naming the path as unverifiable,
never as absent.
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
it re-materializes the target on every install, `use`, and `sync`. A probe
path that cannot be statted for any reason other than ENOENT-class absence
counts as present — the target participates and the first-write consent
gate below applies unchanged — and `env status` reports the probe as
unverifiable, never as absent (section 8.4.1). The
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
| configured form unavailable at materialization; monolithic emitted (warning; section 5.7) | `environment_form_unavailable` |
| declared shadowing path exists (non-current; current warning under `shadow_acknowledged`) | `environment_shadowing_path_present` |
| `isolated` configured for `opencode`, or for `claude_code` on macOS below the pinned release | `environment_isolated_unsupported` |
| `shared` configured for `claude_code` on macOS at or above the pinned release | `environment_shared_unsupported` |
| recorded passthrough entry is no longer a symlink to the native entry (non-current) | `environment_passthrough_detached` |
| recorded passthrough entry whose link state cannot be established — `lstat` or `readlink` fails with permission, I/O, or path errors (non-current, currency unknown; never "detached") | `environment_passthrough_unreadable` |
| recorded passthrough link path holds a regular file or a symlink to an unexpected target at repair (refusal, no fragment; never removed or re-pointed) | `environment_credential_conflict` |
| credential strategy cannot be established — native storage selector outside the verified set (refusal, no fragment) | `environment_credential_unsupported` |
| provisioning seed exists but cannot be read — a native-home file or a named XDG entry | `environment_seed_unreadable` |
| unrecorded entry in a managed `opencode` parent shadows an allowlisted operator entry (warning) | `environment_seed_shadowed` |
| first `auto` write into a secondary target's home without recorded consent | `environment_target_consent_required` |
| detected tool version differs from the adapter's recorded verified version (warning) | `environment_tool_version_unverified` |
| native `mcp_servers` entries inherited into a managed `codex_cli` home under seed-rule revision A (warning; section 7.4) | `mcp_native_servers_ungoverned` |
| native `mcp_servers` entries stripped from a managed `codex_cli` seed under seed-rule revision B (warning; section 7.4) | `mcp_native_servers_not_inherited` |
| managed `codex_cli` home with an unstripped seed — marker lacks the seed record (pre-rule provisioning), or the recorded seed revision is `A` with a non-empty snapshot while the manager ships revision `B` (warning, re-provision hint; section 7.4) | `mcp_seed_unstripped` |

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
| `codex_cli` | `flag` `-p` with `argument: name`, `name: "curator-mcp"`: `-p <name>` layers `$CODEX_HOME/<name>.config.toml` on the base configuration, so the manager's `<home>/curator-mcp.config.toml` (section 5.8) carries the set. The layer name is fixed and reserved. `-p` accepts **exactly one** value — a second occurrence is the tool's argument error, not last-wins — so an operator `-p` after `--` fails the launch and operator profile layering is unavailable in a managed launch (recorded consequence; this closes Decision 0012 Open question 3). `-p` is accepted before and after `exec`. A **missing layer file is silently ignored** (exit 0) — under `--strict-config` too (0.153.2, sprint evidence) — so the launcher MUST stat the layer file immediately before exec and fail rather than launch without the set; `env resolve` covers the same file as a marker-recorded surface | all four facts **verified** on codex 0.153.2 by direct invocation; a layer file whose only table is `mcp_servers` composes over the base and its servers are listed (**verified**) |
| `opencode` | `variable` `OPENCODE_CONFIG` naming the section 5.8 file. opencode merges configuration in a documented order — remote, global, `OPENCODE_CONFIG`, project `opencode.json`, `.opencode/`, `OPENCODE_CONFIG_CONTENT`, managed — so a project-level entry with the same server name overrides the managed one; recorded, not prevented | merge order **docs-confidence** (opencode is not installed on the recording machine) |
| `pi` | none — pi 0.84.2 has no MCP channel; no file and no `mcp` section | **verified** absent from the 0.84.2 help |

What each channel does to the home's own MCP configuration — the
per-adapter residual — is closed in this table:

| Environment | Home MCP configuration under the channel |
|---|---|
| `claude_code` | `--strict-mcp-config` disables every other MCP configuration, including servers recorded in the managed home's own `.claude.json`: the launch set is exactly the profile's |
| `codex_cli` | `-p curator-mcp` layers the profile set over the seeded base: under seed-rule revision A the base still carries the native servers, reported as ungoverned (section 7.4); a home provisioned under revision B carries none in its base: the launch set is exactly the profile's (a revision-A home keeps its inherited base under a revision-B manager and reports `mcp_seed_unstripped`; section 7.4) |
| `opencode` | the documented merge order applies — remote, global, `OPENCODE_CONFIG`, project `opencode.json`, `.opencode/`, `OPENCODE_CONFIG_CONTENT`, managed — so project-level servers remain and a same-named project entry overrides the managed one: recorded residual, not prevented |
| `pi` | none: no channel, no MCP configuration in a managed launch |

The launch set is what the tool offers the agent at launch under a managed
launch through the channel above.

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
| `global_context_cap` | `none` recorded (docs-confidence) | `none` (**verified**) | `none` recorded (docs-confidence) | docs-confidence |
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
  default home as symlinks into the profile store (except the
  `claude_code` root-context surface, below): the manager §5
  symlink-with-copy-fallback discipline extended from skills to root
  context. Only the current profile for the applicable scope (section 9.2)
  is materialized in place.
- **`copied`** — in-place materialization as plain files with recorded
  content hashes, for surfaces or targets where symlinks are unreliable:
  secondary fixed-home targets, link-hostile tools, network filesystems.

Mode defaults: the four adapters default to `linked` for their in-place
surfaces; secondary fixed-home targets default to `copied`; managed homes
link from the store. One per-surface exception holds in every mode and
every home and is not overridable by the registry or by machine
configuration: the `claude_code` root-context surface is always a copied
regular file, because the tool skips a linked `CLAUDE.md` while the
external-includes key is unset (section 5.3); the `claude_code` skills tree
follows the home's mode as usual, and the marker's `surfaces` entry records
the copy (section 8.2). An adapter MAY declare a different in-place default
in the registry; profile data cannot.

All three modes materialize from the same lock's store entries (section 4),
so they cannot diverge for one lock hash.

**Fresh homes.** A managed home is provisioned on the first `env resolve
--repair` or `profile sync` that names its profile × environment: the
manager creates the home, materializes the managed surfaces, links the
section 7.4 passthrough entries, writes or copies the section 7.4
provisioning seeds, and — for `opencode` — seeds the section 7.1 XDG
links, in that order, as
one journaled transaction. Every write in that transaction is a section
8.3.1 write. The **first-resolve notice** accompanies that
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

### 8.2 Environment marker, schemas 1 and 2

Every in-place surface set and every managed home carries a per-home
**environment marker**, `.agent-environment.json`, beside the managed
surfaces. Its supported wire formats are the strict schema-1 object
(`agent-environment-marker-v1.schema.json`) and the strict schema-2
object (`agent-environment-marker-v2.schema.json`). Newly created
markers MUST use schema 2. Existing schema-1 markers remain supported;
the only upgrade rule is the otherwise-required marker publication
stated in section 7.4. The marker records:

- `version` — exactly `1` for schema 1 or `2` for schema 2;
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
  5.6, and — for a `linked` or managed home — whether any entry is a copy
  rather than a link: the manager §5 fallback, or the always-copied
  `claude_code` root-context surface of section 8.1, each recorded with its
  reason so that section 8.4 hash drift applies to the copy; every copy's
  path is one of the entry's paths. The surface keys are exactly
  `root-context`, `skills`, `system-prompt`, and, for a managed home, the
  section 5.8 MCP file keyed `mcp`; only `root-context` carries a `form`.
  Surface keys are sorted;
  required arrays are present even when empty;
- for a managed home, the recorded `passthrough` entries and
  provisioning `seeds` by home-relative path: schema 1 entries carry
  `path` and `strategy`, while schema 2 entries carry the complete
  section 7.4 credential record and carry `path` only when linkable;
- for a managed `claude_code` home, `seeded_projects`: the sorted list of
  literal launch-directory paths whose project entry section 7.4 has
  written into the managed `.claude.json`, so that resolve can tell a
  missing entry from one the tool later rewrote;
- for a managed `codex_cli` home provisioned under the section 7.4 seed
  rule, `codex_seed_record`: the closed object `{ revision,
  native_mcp_servers }` — `revision` exactly `A` (warning release: the
  native servers were inherited) or `B` (flip release: the native servers
  were stripped), `native_mcp_servers` the ascending-byte-order snapshot
  of the native `mcp_servers` entry names taken at provisioning, names
  only, empty when the native file carried none. The record is absent on
  every other home; its absence on a managed `codex_cli` home means
  pre-rule provisioning, reported as `mcp_seed_unstripped` (section 7.7).
  The recorded `revision` never changes after provisioning: an `A` record
  under a revision-B manager keeps reporting its inherited names as
  ungoverned and adds `mcp_seed_unstripped` (section 12);
- for a managed `opencode` parent, the recorded XDG seed links of section
  7.1;
- for a home whose backups directory is non-empty, nothing: backups are
  discovered from the section 8.3 directory, never recorded in the marker.

Readers MUST reject an unsupported marker version with
`environment_marker_invalid` and MUST NOT infer newer semantics from
unknown fields. Marker reads follow the section 8.4.1
absence-versus-read-failure rule (marker row): an absent marker is the
unprovisioned-home condition (`environment_home_stale`, section 10.1),
while an unreadable or malformed marker fails closed with
`environment_marker_unreadable` — non-current with currency unknown, never
"absent" — the home's surfaces are treated as unmanaged, nothing is
removed or replaced. The marker joins
the `agent-*` identifier family deliberately; the frozen core §1.1
identifiers keep their exact spellings.

The marker is a record, not a signature: it MUST NOT be used as an
authorization token or provenance proof (core §10 discipline).

The marker file itself is verified under the section 4
protected-boundary contract alongside the home it records: ownership,
private mutation permissions or DACL, regular file type, and link safety,
verified on every `env resolve` and again under the manager-home mutation
lock for every mutating profile operation. A marker file that fails the
contract makes the profile `environment_store_untrusted` (section 10.1),
distinct from `environment_marker_unreadable`, which means the marker
cannot be read or parsed, and from `environment_marker_invalid`, which
keeps meaning unsupported marker version.

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

Ledger and backup reads follow the section 8.4.1 absence-versus-read-failure
rule (ledger and backup-record rows). The ledger of record unreadable is
`environment_marker_unreadable`: nothing is recorded, so nothing is removed
or replaced, and any attempted write meets
`environment_surface_unmanaged_conflict`. A backup inventory that cannot be
established — the generations directory or a generation needed by restore,
scrub, retention, or status cannot be listed or read — is unknown, never
empty, and reports `environment_backup_record_unreadable`: `env status`
reports the backup row non-current with currency unknown; restore, scrub,
and retention pruning stop before mutating with the same diagnostic; and
the next-generation existence check never proceeds as if the generation
were absent.

### 8.3.1 Write discipline

Every materialization, takeover, repair, or backup write this document
directs at a managed surface in any mode (`copied`, `linked`,
`managed-home`), a section 8.3 backup, the section 8.2 marker, or the
adapter ledger — a closed list of write classes over a closed list of
destinations — replaces the directory entry and never follows a symbolic
link. The manager creates the new regular file or link under an
operation-private name in the same directory, then renames over the
target (atomic replace). The manager MUST NOT follow a symbolic link at
the target path or at any path component below the managed root that the
manager itself did not create in this operation: `O_NOFOLLOW`-class
semantics on open, `lstat`-class semantics on inspection. Components at
or above the managed root — the environments root for a managed home,
the native home directory for in-place surfaces — resolve normally; only
components strictly below the managed root are policed.

A pre-existing symlink at a managed-surface target path is disposed by a
closed rule:

- a manager-owned link — a link the manager created in this operation,
  or a marker-recorded surface entry — is replaced as an entry; drift
  and repair semantics (sections 8.4, 10.1) apply unchanged;
- the section 9.5 foreign-manager stop applies exactly as section 9.5
  states: the operation stops, and an authorized takeover backs up the
  link itself — the backup preserves the symlink with the same link
  text, never dereferenced — then replaces the entry;
- any other link the manager does not own follows the ledger rule: the
  write fails with `environment_surface_unmanaged_conflict` unless a
  takeover authorization covers that path, in which case the takeover
  backs up the link itself, as above, and replaces the entry.

A symlink at a path component below the managed root that the manager
did not create in this operation refuses the write with
`environment_write_would_follow_link`, naming the path, however the
target itself is owned: no takeover flag authorizes traversal, because
the flag covers replacing the target entry, never following a link. The
same refusal fires when a backup, marker, or ledger destination path —
manager-private paths with no ledger or takeover machinery of their own —
traverses or names a link the manager did not create in this operation.
Backup reads MUST NOT dereference a replaced link either. In no case is
the target of a pre-existing link opened for writing.

`env status` reports every managed-surface, backup, and marker path
blocked by a link the manager does not own with
`environment_write_would_follow_link`, naming the path; the row is
non-current (section 12).

### 8.4 Drift

For `linked` surfaces, drift is a link that no longer targets the expected
store path or a target whose bytes fail the recorded hash. For `copied` and
`managed-home` surfaces, drift is a recorded content hash that no longer
matches. Drift detection MUST state both halves explicitly: the surface was
modified outside the manager, and the file was left untouched; the
installation is non-current, and `repair` restores the managed bytes. A
drifted file is never silently overwritten outside `repair`. Drift
inspection uses `lstat`-class semantics (section 8.3.1): a surface path
that is a symlink is identified with `readlink`, never opened through
the link.

Absence and read failure are distinct facts for every state and surface
file (section 8.4.1): drift compares the home against the record, so a
surface that cannot be read is not drifted — it is
`environment_surface_unreadable` (non-current, currency unknown), and no
absence-shaped outcome — `environment_surface_missing` included — may fire
on it.

Store failure is not drift: drift compares the home against the record,
while `environment_store_untrusted` compares the store against its pin
and the section 4 boundary. A linked surface whose link targets the
expected store path but whose store entry fails the contract is not
`environment_surface_drift`; the profile is `environment_store_untrusted`
(section 10.1) and no fragment is emitted. Home currency is a separate
check (section 10.1): a marker that belongs to another lock is
`environment_home_stale`, never `environment_store_untrusted`.

### 8.4.1 Absence versus read failure

For every file the manager reads as state or surface — marker, lock,
ledger, backup record, provisioning seed, passthrough entry, recorded
surface, inventory candidate, a closed list — the outcomes "absent" and
"present but unreadable or malformed" are distinct facts. "Absent" means
ENOENT-class on `lstat` or `open` of the exact path: no entry exists there.
"Present but unreadable or malformed" means the path resolves to an entry
the manager cannot use: permission or I/O errors on stat, open, or read; a
path component that is not a directory; a symlink where a regular file is
required, or a directory where a file is expected; undecodable bytes; or
content that fails parsing or schema validation. A failed read, stat, or
parse of any such file MUST NOT be reported, persisted, or acted upon as
absence, and MUST NOT trigger any absence-shaped action — provisioning,
re-seeding, takeover, re-materialization, or an "unprovisioned" verdict. An
unreadable file makes the affected row non-current with currency unknown
(section 12), and the operation that needs the file fails closed.

The unreadable outcome per file class is closed in this table; every
section that reads one of these files references this rule and names its
row's diagnostic, never a local restatement:

| File class | Absence legitimately means | Present but unreadable or malformed means | Owning section |
| --- | --- | --- | --- |
| marker | no marker file: the home is unprovisioned (`environment_home_stale` at resolve) | `environment_marker_unreadable` — non-current, currency unknown; surfaces treated as unmanaged, nothing removed or replaced | 8.2 |
| lock | no lock file: the profile is not installed (`profile_unknown`) | `environment_store_untrusted` (entry-class) — never `profile_unknown`; resolve emits no fragment, status is non-current with currency unknown, and no mutating operation (install, update, use, sync, repair, garbage collection) rebuilds, re-materializes, or replaces anything from the unreadable evidence — recovery is an explicit operator action (reinstall from the profile source, or the section 9.2 retained previous lock) that never reads the unreadable file as input | 1.3 |
| ledger | the ledger is absent with its home (unprovisioned) | the marker as ledger of record unreadable is `environment_marker_unreadable`; no remove or replace (attempted writes meet `environment_surface_unmanaged_conflict`) | 8.3 |
| backup record | no generations: nothing to restore; the next generation proceeds; status reports zero | `environment_backup_record_unreadable` — the backup inventory is unknown: status reports the backup row non-current with currency unknown; restore, scrub, and retention pruning stop before mutating; the next-generation check never proceeds as if the generation were absent | 8.3 |
| provisioning seed | the seed is not seeded | `environment_seed_unreadable` — provisioning stops before the first write | 7.4 |
| passthrough entry | the recorded link is missing, replaced, or retargeted: `environment_passthrough_detached` — a missing link, or a directory at the entry path, is re-linked by `--repair`; a regular file or an unexpected retarget is `environment_credential_conflict` at repair, never removed or re-pointed | `environment_passthrough_unreadable` — non-current, currency unknown, never "detached"; repair leaves the entry untouched | 7.4 |
| recorded surface | `environment_surface_missing` | `environment_surface_unreadable` — non-current, currency unknown | 8.4 |
| inventory candidate | not detected — never in the loss list | a loss with reason; a lossy import stops with `environment_import_lossy` unless consented; onboarding stops before its first write while the inventory is incomplete | 9.5, 9.6 |

Auth-path discovery is no-follow: backup discovery MUST use
`lstat` on each auth path and MUST NOT follow an auth symlink. If a link
target must be identified for the section 7.4 liveness check, the manager
MAY read the link text but MUST NOT open or traverse the target for
discovery or backup. Credential paths and bytes MUST NOT be archived.
An `lstat` or required `readlink` failure is unreadable, never absence.

Boundary verification precedes readability classification: on the section
10.1 verification order (enclosing boundary, then entries, then pin hashes,
then home currency), a failure that violates the section 4 contract — a
symlink at the marker or lock path, a non-regular entry component — or that
prevents proving the boundary at all is `environment_store_untrusted` for a
lock, marker, or store file, never an unreadable code (sections 1.3, 4,
8.2).

### 8.5 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| marker unreadable or malformed (non-current, currency unknown; never "absent") | `environment_marker_unreadable` |
| marker unsupported version | `environment_marker_invalid` |
| store entry, lock, or marker file fails the §4 protected-boundary contract or its pin hash, or a `path` source directory fails its §4 boundary checks (non-current) | `environment_store_untrusted` |
| managed surface bytes or link differ from the record (non-current) | `environment_surface_drift` |
| recorded surface file absent (non-current) | `environment_surface_missing` |
| recorded surface file exists but cannot be read (non-current) | `environment_surface_unreadable` |
| write would touch a file the marker does not record | `environment_surface_unmanaged_conflict` |
| next backup generation directory already exists | `environment_backup_exists` |
| backup inventory (generations directory or a needed generation) cannot be listed or read (non-current, currency unknown; restore, scrub, and retention pruning stop before mutating) | `environment_backup_record_unreadable` |
| a write that would traverse a symlink below the managed root, or open through a symlink at a backup, marker, or ledger destination, that the manager did not create | `environment_write_would_follow_link` |

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

After the audit gate passes and before the lock is published, `profile
install` MUST print the section 2.3 surfacing rows for the resolved MCP
set, and MUST emit `mcp_package_allowlist_empty` when the MCP package
allowlist is empty; neither fails the install.

Activation on install follows operator intent without magic: `install` sets
the machine current profile only when the machine has none — first install,
and the activation is reported, never silent — or when the operator passes
`--use`. `--use` takes no name: an install names one root, so there is
nothing to choose. In every other case the manager prints the installed
profile and how to activate it. Re-installing an already installed source
with the same requirement re-resolves exactly as `profile update` does
(section 9.2) and is reported as an update; `profile install` accepts
`--confirm-system-delta` for that path with the same per-invocation
semantics as `profile update`.

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

**`profile update [<name> | --all] [--confirm-system-delta]`** re-resolves
the root and the overlays from their declared requirements, fetching new
candidates, and proceeds in this order:

1. resolution under section 1.4 produces a candidate lock;
2. every member new to the lock — a name or pin not in the old lock — is
   audited in strict mode under section 9.1; a blocking finding on any new
   member leaves the **old lock in place**, reports `profile_update_blocked`
   with the finding, and changes nothing;
3. after the audit gate passes and before the lock is published or any
   surface is re-materialized, `profile update` MUST print the
   resolved-version delta of the candidate lock against the old lock, then
   the section 2.3 surfacing rows for the candidate lock's MCP set, and
   MUST emit `mcp_package_allowlist_empty` when the MCP package allowlist
   is empty; printing never fails the update, and the confirmation gate
   below runs after all three;
4. the new store entries are installed and the new lock is published as one
   manager-home transaction;
5. in-place scopes whose current profile is this one re-materialize from
   the new lock;
6. managed homes of this profile are marked **stale** (`environment_home_stale`
   at their next bare `env resolve`, section 10.1; `curator run` always
   passes `--repair` and repairs the home instead of surfacing it) for
   explicit repair, never repaired in the background — a running session
   may be reading them;
7. store entries the new lock no longer names become GC-eligible under
   section 12; the old lock is retained beside the new one until the next
   garbage collection so that a stale managed home can still be identified.

**Resolved-version delta.** The delta compares the candidate lock against
the old lock per member, keyed by (`kind`, `name`): **added** (in the
candidate lock only), **removed** (in the old lock only), **moved** (in
both with a different version or pin). The manager prints one delta line
per added, removed, or moved member, in ascending (`kind`, `name`)
bytewise order; with an empty delta it prints no delta line. The line
grammar is closed:

```text
lock-delta added <kind> <name> <version> <pin>
lock-delta removed <kind> <name> <version> <pin>
lock-delta moved <kind> <name> <from-version> → <to-version> <from-pin> → <to-pin>
```

`<kind>` is exactly `context`, `mcp`, or `skill`. `<version>` is the
member's resolved version, or `-` when the lock carries none (a skill
pinned exactly whose source carries no version tag peeling to that
commit). `<pin>` is `commit:<full lowercase hex>` or `state:<64 lowercase
hex>`, following the lock's pin shape. Each line is terminated by exactly
one LF.

**System-delta confirmation.** When the delta introduces or changes a
`class: system` module or an MCP declaration, the update needs an explicit
per-run confirmation. The trigger is exactly:

- a member new to the lock that carries a `class: system` module, or a
  moved member whose system-module inventory differs — the sorted list of
  (`path`, `environments` selector, bytes) over its `class: system`
  manifest entries, compared between the old and the new snapshot;
  admission under section 3 does not narrow the trigger; or
- an `mcp` member new to the lock, or a moved one whose MCP declaration
  differs — the CCJ-1 bytes ([`registry.md`](registry.md) §1) of the
  declaration object as the lock and the materialization read it:
  `transport`, `command`, `args`, `env_names`, the `url` of an `http`
  declaration, and the `environments` selector. Any byte difference
  triggers — a changed `url`, a changed selector, or a reordered array
  (CCJ-1 preserves array order) — and no field is narrowed out; absent
  (an `http` declaration carries no `command` or `args`) differs from
  present.

The confirmation ships warn-first (impact row "E1 update confirmation") in
two explicitly labelled revisions:

- **Revision A (warning release).** The manager warns
  `profile_update_system_delta`, naming every member the trigger names
  and carrying the migration hint `revision B refuses with
  profile_update_confirmation_required unless --confirm-system-delta is
  given`, and proceeds. Old behavior is otherwise kept.
- **Revision B (flip release).** The manager refuses with
  `profile_update_confirmation_required`, naming every member the trigger
  names, unless the invocation carries `--confirm-system-delta`. A refusal
  leaves the old lock in place and changes nothing: no publish, no
  re-materialization, no stale-marking.

No release both warns-and-proceeds and refuses at once: revision A adds
the warning and proceeds; revision B refuses without the flag. A manager
MUST ship revision A before revision B. `--confirm-system-delta` is per
invocation only: no configuration knob may pre-confirm it. Under `--all`
the flag is given once and confirms every profile of the run; without it
each profile updates in turn and the first refusal stops the run with the
refusing profile unchanged and later profiles untouched. With an empty
trigger the flag is accepted and ignored. A reinstall that re-resolves as
an update (section 9.1) prints the delta and runs the same gate, and
`profile install` accepts `--confirm-system-delta` with identical
per-invocation semantics: a triggered reinstall under revision B refuses
without the flag and proceeds with it. No configuration knob
pre-confirms a reinstall either.

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
adapter or target is registered on the machine. A lock it cannot read is
not "not found" (section 8.4.1, lock row): the profile is reported as
`environment_store_untrusted` and left unmaterialized.

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
keep their behavior byte-for-byte. Migration reads each global skill's
install record to synthesize the lock; a record it cannot read is a loss
with reason under the section 8.4.1 inventory-candidate row — never "not
installed" — and migration stops before any write with
`environment_import_lossy` naming the skill. Unlike import, the migration
path admits no consent flag: the operator makes the record readable — or
removes the skill through the normal global-remove path — and retries;
the skill is never dropped silently.

### 9.5 Onboarding

A machine with hand-maintained global context must reach managed state
without loss. Onboarding ships complete in revision 1: detection, the
foreign-manager stop, the replace notice, backup, takeover, and the
section 9.6 import.

Onboarding is triggered only by a **mutating** profile operation that meets
unmanaged state — `profile install`, `profile use`, `profile sync`,
`profile update`, `env resolve --repair`. Read-only commands — `profile
list`, `env status`, `env resolve` without `--repair` — report unmanaged
state and never begin onboarding, never write a backup, and never prompt. On
such a trigger the manager:


1. **Inventories**, per registered adapter and participating target:
   existing unmanaged root-context files; existing global skills; and
   managed-surface paths that are already symlinks pointing outside the
   manager's store. The last is evidence of another manager and stops the
   operation with `environment_foreign_manager_detected` and an explicit
   choice — abort, or take over with backup — never a silent absorption.
   The inventory additionally applies a best-effort **heuristic**: when
   plain unmanaged files are met and the well-known state location of a
   dotfile manager from the closed table below is present, the notice is
   elevated to `environment_foreign_manager_suspected` (warning), naming
   the manager: a dotfile manager appears to manage this machine and
   will overwrite managed surfaces on its next apply. The heuristic
   never blocks.
   Inventory reads follow the section 8.4.1 absence-versus-read-failure
   rule (inventory-candidate row): a candidate that cannot be read is never
   treated as absent — a detected-surface candidate that cannot be read
   joins the section 9.6 loss list with its reason, and a symlink at a
   managed-surface path whose target cannot be read stops the operation
   with `environment_foreign_manager_detected`, naming the path as
   unverifiable, with the same explicit choice. The dotfile-manager
   heuristic stays best-effort and warning-only: a probe it cannot
   complete yields no signal and never gates.
2. **Notifies**: before any write, the operator is told that native global
   context files are being replaced by managed ones and where the backup
   lands.
3. **Backs up, always**: every file the operation will replace is copied
   into the next section 8.3 backup generation before the first write,
   whether or not any import was requested, subject to
   `environment_backup_exists`. A symlink the operation will replace is
   backed up as a symlink with the same link text, never dereferenced
   (section 8.3.1).
4. **Classifies and offers the import**: the detected state is classified
   under section 9.6 and the classification is reported before any write;
   the import itself runs only on the operator's request and under the
   section 9.6 consent rules. Onboarding without an import ends after
   step 3 and the takeover writes the operator chose.

**Dotfile-manager state table (closed).** The heuristic checks exactly
the following per-manager, per-platform locations, in row order. A
conforming manager's heuristic list is exactly this table, in this
order; a table change is a spec revision, never an
implementation-private list. Each cell carries its confidence:
`verified` means checked against the manager's own documentation or
source (cited in the revision evidence with URL and version/date);
`docs-confidence` means documented but not verified end to end. A
`verified` label scopes to the default location the cited source
establishes — the base variable, the leaf name, and the default
base — not to how the manager treats an unset, empty, or relative
variable; that fallback is the heuristic's own resolution rule
below.

| # | Manager | macOS | Linux | Windows | Source |
|---|---|---|---|---|---|
| 1 | `chezmoi` | `$XDG_DATA_HOME/chezmoi` (default `~/.local/share/chezmoi`) — verified | `$XDG_DATA_HOME/chezmoi` (default `~/.local/share/chezmoi`) — verified | `%XDG_DATA_HOME%\chezmoi` (default `%USERPROFILE%\.local\share\chezmoi`) — verified | `defaultSourceDir` over `go-xdg`: the XDG data home on every platform, no platform switch |
| 2 | `home-manager` | `$XDG_CONFIG_HOME/home-manager` (default `~/.config/home-manager`) — verified | `$XDG_CONFIG_HOME/home-manager` (default `~/.config/home-manager`) — verified | `none` — verified: Nix-only, no native Windows location | launcher `setConfigFile`/`setFlakeAttribute`; install docs name only Nix platforms |
| 3 | `yadm` | `$XDG_DATA_HOME/yadm` (default `~/.local/share/yadm`) — verified | `$XDG_DATA_HOME/yadm` (default `~/.local/share/yadm`) — verified | `none` — verified: a bash script with no native Windows home to anchor to | `set_yadm_dirs` plus FILES section; every path `$HOME`-relative |
| 4 | `stow` | `none` — verified: keeps no state of its own | `none` — verified: keeps no state of its own | `none` — verified: keeps no state of its own | manual: "stores no extra state between runs" |
| 5 | `dotbot` | `none` — verified: its config lives in the operator's own repo at any path | `none` — verified: its config lives in the operator's own repo at any path | `none` — verified: its config lives in the operator's own repo at any path | README: the dotfiles path is the operator's ("replace with the path to your dotfiles") |

**Resolution.** `~` is the operator home directory as the OS reports
it (`$HOME` on macOS and Linux, `%USERPROFILE%` on Windows). An XDG
cell names its base variable: when `$XDG_DATA_HOME` (resp.
`$XDG_CONFIG_HOME`) is set to a non-empty absolute path it replaces
the default base (`~/.local/share`, resp. `~/.config`); when it is
unset, empty, or not an absolute path the default applies. This
fallback is the heuristic's resolution rule, following the XDG Base
Directory Specification (relative paths are invalid and ignored);
upstream managers differ: yadm rejects a non-absolute value the
same way (`set_yadm_dirs`), while home-manager's launcher
(`setConfigFile`) and chezmoi's `go-xdg` take the first non-empty
value without an absolute-path check, so a relative value resolves
under the heuristic to the default even where the manager itself
would follow the relative path. (`%XDG_DATA_HOME%` and
`%XDG_CONFIG_HOME%` spell the same variables on Windows;
`%LOCALAPPDATA%` and `%APPDATA%` name the Windows application-data
roots for future rows — no current row uses them.)

A location is **present** when the resolved path itself is an existing
directory, inspected with `lstat`-class semantics (sections 4, 8.4):
a symlink at the resolved path is not present even when its target is
a directory, a regular file is not present, and an unreadable path or
a failed inspection is not present — and is never reported as absent
(section 8.4). The check reads exactly the resolved table path:
system `$XDG_DATA_DIRS` entries, manager-private relocations (a
chezmoi `sourceDir`, `$YADM_DIR`/`$YADM_DATA`,
`$HOME_MANAGER_CONFIG`), and sibling paths (chezmoi's config
directory, yadm's `YADM_DIR` config directory, home-manager's
generation links) are not heuristic inputs.

**Outcome.** The manager scans the table in row order and reports the
first row whose location is present; the notice names that manager. A
row whose cell is `none` on the running platform is inert — there is
no path to check. When no row is present there is no notice. The
heuristic never blocks: it only elevates the step-1 notice.

Takeover is not an operation of its own: the explicit takeover flag is
carried by a mutating operation and covers only the specific unmanaged
files that carrying operation would write — it never selects a scope of
its own. The flag is accepted on exactly the mutating operations named
above as onboarding triggers — `profile install`, `profile use`, `profile
sync`, `profile update`, and `env resolve --repair` — and on no other
operation. A carrying operation that meets unmanaged files outside
onboarding performs the same notice and backup as onboarding when the flag
is given; without the flag, section 8.3 applies and the operation fails
with `environment_surface_unmanaged_conflict` rather than overwrite.
Every takeover write is a section 8.3.1 write: the operator's
authorization covers replacing the directory entry after backup, never
opening the link's target for writing.
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
  the section 9.4 migration, never through import. An entry whose ledger
  membership cannot be established — the ledger cannot be read — is not
  "not recorded" (section 8.4.1, inventory-candidate row): it is a loss
  with reason below.

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
(section 8.4.1, inventory-candidate row): an absent surface never appears
in the loss list, and a failed read is always a loss, never treated as
absence.

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
section 9.5 takeover path with its notice and backup. The import is a
`path` root for the section 4 boundary contract: its directory passes the
same verification at every resolve, and an import MUST NOT carry an MCP
declaration (section 2.2) — reassembly emits no `requires.mcp` entry.

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
| update delta introduces or changes a `class: system` module or MCP declaration (revision A warning, names the members, carries the migration hint) | `profile_update_system_delta` |
| same trigger under revision B without `--confirm-system-delta` (refusal, names the members; old lock stands) | `profile_update_confirmation_required` |
| `profile use` left a scope partially switched; recorded current unchanged (non-current) | `profile_use_partial` |
| `profile remove` names a profile that is current in any scope or an overlay of another profile | `profile_in_use` |
| skill or managed bin entry named `curator-*` | `environment_reserved_command_name` |
| lossy classification without the consent flag (stops with the loss list) | `environment_import_lossy` |
| lossy import proceeding under explicit consent (warning, loss list) | `environment_import_lossy` |
| imported skill declaration recovered from foreign records (warning) | `environment_import_skill_foreign` |
| chosen import profile name already installed | `profile_import_name_taken` |
| MCP package allowlist empty at install or update under the `permissive` posture (warning: every declaration package in the closure is admitted) | `mcp_package_allowlist_empty` |
| MCP package allowlist empty at install or update under the `hardened` posture while the resolved closure carries an MCP declaration package (resolution error; old lock stands) | `mcp_package_allowlist_empty` |
| recorded passthrough entry whose link state cannot be established (non-current, currency unknown; never "detached"; policy owned by §7.7) | `environment_passthrough_unreadable` |
| backup inventory (generations directory or a needed generation) that cannot be listed or read (non-current, currency unknown; restore, scrub, and retention pruning stop before mutating; policy owned by §8.5) | `environment_backup_record_unreadable` |

`profile_index_ambiguous` is withdrawn with the multi-profile repository
shape; `--use` takes no name. Section 2.3 surfacing emits no diagnostic
and never fails an operation.

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
entry of the immutable profile store, link-target identity is necessary but
no longer sufficient currency: the store entry's integrity is verified, not
assumed (section 4); the link target is read with `lstat`-class semantics
(section 8.3.1). A copied surface —
the `claude_code` root-context file in every mode, or a manager §5
fallback copy — has no link target and is verified by the content hash
the marker records for it (section 8.2), the same hash section 8.4 drift
compares. A home that is
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
re-materializing managed surfaces, re-linking absent passthrough links,
reconciling XDG seeds, adding the launch directory's project entry,
never touching environment-owned mutable state,
unmanaged files, seeds, or backups — and then emits the fragment. A link
path that holds a regular file or a symlink to an unexpected target is
`environment_credential_conflict`: the repair stops with the diagnostic
and emits no fragment; completed surface repairs stand. Repair never
migrates credential ownership: a mode change that leaves a recorded
link behind it is the explicit migration of section 7.4, never silent
inside `--repair`. Repair
restores managed bytes from the store; it MUST NOT adopt candidate bytes
found in the home. Repair writes are section 8.3.1 writes: repair
replaces directory entries and refuses with
`environment_write_would_follow_link` rather than writing through a link
the manager does not own.
A store entry is re-applied only after that entry passed
the section 4 contract and its pin hash: a non-trusted entry is never
re-applied, so `env resolve --repair` is not persistence for a tampered
store (audit note E7). Failure classes split (section 4): an enclosing
boundary that cannot be proven refuses every mutating operation before its
first write — nothing is rebuilt, because there is no protected place to
rebuild into, and the operator repairs the boundary out of band; an
individual entry (store entry, lock file, marker file) that fails inside a
proven enclosing boundary is rebuilt by a real operation from the
revalidated snapshot into newly established protected state
(operation-private staging, atomic publication under the mutation lock);
an unreadable or malformed lock file is never rebuilt from (section
8.4.1, lock row) — install, update, use, sync, repair, and garbage
collection refuse with `environment_store_untrusted` without rebuilding,
re-materializing, or replacing anything, and recovery is the lock row's
explicit operator action. For a `git` member the manager re-acquires the
pinned commit's exact snapshot bytes (section 1.2) and republishes the
entry with a fresh boundary; for a `path` or `local` member there is no
second copy of the snapshot — bytes are never adopted from the source
directory again (section 1) — so the entry cannot be rebuilt and repair
fails with `environment_repair_failed` while the operator reinstalls.
Dry-run evaluation of an entry-class failure of a store entry or a marker
file, or of a lock file that fails its boundary checks, reports
`would-rebuild-untrusted-store` and mutates nothing; dry-run evaluation
of an enclosing-boundary failure, of a `path` source directory failure,
or of an unreadable or malformed lock file reports
`environment_store_untrusted` with no rebuild planned and mutates nothing
(section 4).
Lock acquisition that times out is
`environment_lock_unavailable`, distinct from `environment_repair_failed`,
which keeps meaning that the store cannot restore this home — an entry is
missing or fails validation, including the section 4 contract. Neither emits a fragment.

**Store-trust verification.** On every resolve, as part of the lock-free
verification, the manager MUST verify in order: enclosing boundary →
entries → pin hashes → home currency (section 4). It verifies the section
4 protected-boundary contract for the environments root, the profile store
root, the profile lock file, the home's marker file when the home has one,
every store entry the lock names, and — for a `path` root or overlay —
the source directory (section 4); then it recomputes every named store
entry's tree hash from its bytes and requires equality with the pin
(section 4) — for a `git` member the tree object identity of the pinned
commit, for a `path` or `local` member the `state_sha256` — with no home
marker required, and before provisioning or repair of any home; missing
hashes never count as passed. A boundary that cannot be proven, or a pin
hash that does not match, makes the profile
`environment_store_untrusted`: resolve reports the diagnostic and emits
**no fragment**, the profile is non-current, and `env status` reports the
row (section 12); an unprovisioned home is verified the same way, so a
swapped entry is untrusted even with no marker. Pin hashes are verified,
not trusted. Home currency is separate: the marker's recorded surface
hashes are compared with the surfaces the CURRENT lock would generate
(sections 5.1, 5.6); a mismatch because the marker belongs to another lock
— stale after `profile update` (section 9.2) — is the ordinary stale-home
condition (`environment_home_stale`) repaired from the verified store,
never `environment_store_untrusted`. An intact updated store with an old
marker is stale and repair succeeds; a swapped updated store with an old
marker is untrusted and its bytes are never adopted. Resolve's reads follow
the section 8.4.1 absence-versus-read-failure rule: an absent marker is
unprovisioned (`environment_home_stale`); an unreadable or malformed marker
is `environment_marker_unreadable` (marker row), never "absent"; an
unreadable recorded surface is `environment_surface_unreadable` (surface
row), never "missing" and never a stale-home reason; an unreadable lock is
entry-class `environment_store_untrusted` (lock row), never
`profile_unknown` and never rebuilt from; and an unreadable passthrough
entry is `environment_passthrough_unreadable` (passthrough row), never
"detached" and never a stale-home reason — while a detached entry stays
a stale-home reason repaired by `--repair`. `--repair` neither
re-materializes an unreadable surface nor re-links an unreadable entry:
it reports the unreadable diagnostic and emits no fragment.
Provisioning-time seed reads fail with `environment_seed_unreadable`
(seed row) and stop provisioning before the first write.
The pin recomputation costs O(store entry bytes named by the lock) per
resolve: every named entry is re-hashed, so a same-user byte swap of a
system-prompt or root-context file — or any file in the entry — is
detected without a marker. A per-surface rule would need the marker and
would misclassify a stale home as untrusted; the pin baseline verifies
unprovisioned homes and separates currency from integrity.

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
untracked environment as `Plan.Env` ⊕ fragment `env` ⊕ the engaged
`variable`-kind channel. In both modes the plan request takes the launcher's
process environment as `LaunchRequest.Env`; `Plan.Env` is the complete
filtered child environment, preserving plugin strips and sanitized `PATH`,
not an overlay on the inherited environment. Tracked `env_literals` start
only from the plugin's own names and values (`System.ChildEnv(nil, req)`
over an empty parent with the same request), then fragment `env` and the
engaged variable channel; inherited `HOME`, `PATH`, and secrets MUST NOT
be serialized from `Plan.Env`. The SHOULD-warn for displaced plugin values
applies only to those own names. The launcher bounds `env_names` under
section 10.3 and subtracts only names in the composed `env_literals`,
warning on each collision. It either
delegates to `ax start --launch-plan -` or execs directly (Decision 0013
Decisions 6.3 and 6.4). Its provider mapping covers `claude_code`,
`codex_cli`, and `pi`; **`opencode` is `env_unsupported` for `curator run`**
in revision 1 — no agents-management system plugin exists for it — while
`env resolve opencode` and its managed homes are fully specified here and
an operator applies the fragment by hand. `env_unsupported` is the
launcher's diagnostic, not this document's.

**Permission mode.** Under Decision 0018 (adopted) every `curator run`
launch resolves one permission mode, `native` or `yolo`, per launch,
first naming level wins: the CLI `--permissions` flag (or `--yolo`)
over the per-profile `permissions` knob of section 12.1, over the
launcher-global `defaults.json` default, over the built-in default —
`yolo` for interactive untracked launches, `native` for headless, CI,
and tracked silence. `native` means no launcher override (argv
forwarded verbatim), not a guaranteed prompting posture; `yolo`
requests the agents-management-declared native bypass, never an
outside-policy bypass. A launch is headless when stdin or stdout is
not a TTY, when the native arguments select a non-interactive form,
when a non-interactive marker is present, or when the launch is
tracked. The non-interactive marker set is exactly {`CI`,
`GITHUB_ACTIONS`}: this paragraph is the set's single normative
statement in this specification — the set is closed, additions come by
specification revision only, never ad-hoc — and the launcher SPEC §4.6
headless detector mirrors it (Decision 0018, choice 7); the two
spellings change only together, in the same revision. The
force-`native` lock of section 12.2 sits above the whole precedence:
under an engaged lock any launcher-visible `yolo` is a `usage` error
naming the locked knob, and total silence resolves `native`. Curator
resolves the profile level and the lock engagement and delivers them
through the fragment's `permissions` member (section 10.2);
`launch-env-fragment-v2` is the minimum transport version token —
transport support is established iff the fragment revision is v2 or
later — and verified transport support is a precondition for admitting
`yolo`: a fragment that predates the token cannot carry the policy or
the lock and is never silence, so any launch that would otherwise
resolve `yolo` is refused (`permission_policy_unsupported`), while a
launch that resolves `native` — explicit `native`, or
headless/CI/tracked silence — proceeds as `native`. The launcher SPEC
§4.1 mirror of this precondition lands with follow-up F-L1. The
provider flag spelling,
the per-tool-release mapping with its goldens, and the argv grammar
are owned by agents-management as a `LaunchRequest` permission-mode
member for `LaunchModeInteractive` (Decision 0018, choices 3 and 6),
not this document and not the launcher SPEC: the launcher never
spells a provider flag (Decision 0013 D5) — it resolves and passes
the mode only. The launcher owns mode resolution (flag over profile
over global over built-in default, including conflict refusal), the
headless detector, transport of the resolved mode, the stderr
provenance line, and the launch-record extension key.

**Tracked residual.** Decision 0013's document has no destination
environment-unset or `PATH`-transform member. Its own-literals-only
composition cannot transport the plugin's inherited-name removals or
`PATH` sanitization to ax's destination environment. Destination filtering
by ax is unknown here; no ax field or implementation change is specified.

### 10.2 The launch environment fragment

Two fragment revisions exist, `launch-env-fragment-v1` and
`launch-env-fragment-v2`, named by the REQUIRED `fragment` member,
which is the fragment's revision token. `launch-env-fragment-v2` is
the minimum transport version token for the section 12.1 `permissions`
profile level and the section 12.2 lock engagement (Decision 0018,
choice 7): a launcher establishes transport support iff the fragment
revision is v2 or later. A v1 reader MUST reject a v2 fragment
(unknown revision token), and MUST reject a v1 fragment carrying the
v2 `permissions` member (unknown field — a v1 fragment with the member
is invalid); the revision token is the only transport signal. A v2
fragment MUST carry the `permissions` member: absence is invalid. A
fragment that cannot carry the policy or the lock is never silence:
when the launcher cannot establish transport support, any launch that
would otherwise resolve `yolo` — from the flag, the profile setting,
the global default, or the built-in default — is refused
(`permission_policy_unsupported`); a launch that resolves `native` —
explicit `native`, or headless/CI/tracked silence — proceeds as
`native` (section 10.1). The launcher SPEC §4.1 mirror of this
precondition lands with follow-up F-L1. Managers emit v1 fragments
until they adopt the v2 emission; the emission cutover is the curator
follow-up named in the changelog, not this revision.

The fragment is a closed object; readers MUST reject unknown fields,
unknown kinds, and unknown semantics or argument values.

**`launch-env-fragment-v1`.** The revision-1 shape:

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
  managed-home path. Every path in the fragment — `env` values,
  `system_prompt.path`, `mcp.path`, `path_prepend` — is absolute and
  carries no `..` segment.
- `system_prompt` is present exactly when the lock carries at least one
  admitted (section 3) applicable system module for the environment. It is data about a
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

**`launch-env-fragment-v2`.** Revision v2 is revision v1 plus one
REQUIRED member, `permissions`, a closed object carrying the resolved
profile level and the lock engagement for the resolved profile. Every
other member keeps its revision-1 meaning; the value has exactly this
shape:

```json
{ "mode": "native", "locked": false, "source": "profile" }
```

- `mode` is REQUIRED, exactly `native` or `yolo`: the
  `permissions.<profile>` knob value for the resolved profile when the
  knob names one, `native` otherwise — under an engaged lock the knob
  was already overridden to `native` with a warning, and when the
  knob is absent `native` is the silence placeholder (see below).
- `locked` is REQUIRED, a boolean: true iff the section 12.2
  force-`native` lock is engaged for the resolved profile.
- `source` is REQUIRED, exactly `profile`, `global`, or `default`:
  which Curator-side input fixed `mode` — `profile` when the machine
  knob named it, `global` when the fleet-global system-file lock
  fixed it, `default` when the knob was absent and no lock is
  engaged. `global` never means the launcher-global `defaults.json`
  default: the launcher reads its own file, and that default never
  appears in the fragment.
- Consistency is schema-enforced: `locked` is true iff `source` is
  `global`, and `mode` is `native` whenever `source` is `global` or
  `default` — a lock forces native, and silence carries the `native`
  placeholder — so `mode` is `yolo` only with `locked: false` and
  `source: "profile"`, and a fragment carrying `yolo` with
  `locked: true` is contradictory and invalid.
- Silence: with `source: "default"` the launcher MUST treat the
  profile level as silent — falling through to the launcher-global
  default — never as an explicit `native` naming. With
  `source: "profile"` the profile level names `mode`.

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

**S4 rollout: warn-first passthrough profiles.** The `passable_env_names`
default change is user-visible — the impact row is "S4 passthrough
default" — so it ships in two explicitly labelled steps. The effective
allowlist is the explicitly configured list when the knob carries one, and
unbounded when the knob is explicitly `null`; when the knob is absent the
profile decides:

- Profile `s4-warn` (the warning release): an absent knob behaves as
  unbounded — the pre-S4 behavior is kept — but every launch that passes
  an operator variable warns `mcp_env_passthrough_unlisted`: when the knob
  carries a list, for each passed variable outside it; when the knob is
  absent, for each passed variable. The warning MUST name the variables
  and the `passable_env_names` knob, and MUST carry the migration hint:
  list the named variables to keep passing them after the flip. An
  explicit `null` passes unbounded with no warning.
- Profile `s4-enforce` (the flip release, the revision-1 rule): an absent
  knob is the empty list. A requested name outside the effective list —
  every requested name when the knob is absent — is dropped from the
  launch allowlist with `mcp_env_passthrough_dropped`, naming the dropped
  variables. An explicit `null` stays unbounded with no diagnostic, and a
  system file MAY lock `passable_env_names` to a list so that `null` is
  unavailable (section 12.2).

A manager MUST ship `s4-warn` before `s4-enforce`: one release MUST NOT
flip the default and start dropping in a single step. `env status` reports
the active profile with the effective allowlist (section 12).

Under the `hardened` machine posture (manager §7.1) an explicit
`passable_env_names: null` is refused with
`passable_env_names_unbounded_refused`, naming the knob, at profile
install, profile update, and launch composition alike: no launch allowlist
is composed from it, the install or update fails without writing or
changing the lock, and `env status --check` reports the machine
non-current. The refusal fires however the `null` arrived — explicit or
locked — since it is the profile's meaning (manager §7.1). An absent knob
keeps following the shipped S4 profile above: the hardened posture
refuses only the explicit unbounded choice, and changes neither S4
profile's own absent-knob rule.

The closed interpreter contract for MCP launch (audit item 4, analogous to
`script-worker-v1`) is a later revision, not this one; it is noted here so
that no reader mistakes the surfacing rows for an execution sandbox.

### 10.4 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| operand names an unregistered environment | `environment_unknown` |
| named or current profile not installed | `profile_unknown` |
| managed home unprovisioned, stale, drifted, or passthrough detached; no fragment without `--repair` | `environment_home_stale` |
| marker unreadable or malformed at resolve (no fragment; non-current, currency unknown; never "absent") | `environment_marker_unreadable` |
| recorded surface file unreadable at resolve (no fragment; non-current, currency unknown; never "missing", never a stale-home reason; `--repair` does not re-materialize it) | `environment_surface_unreadable` |
| lock file unreadable or malformed at resolve (no fragment; non-current, currency unknown; never `profile_unknown`; never rebuilt from — section 8.4.1, lock row) | `environment_store_untrusted` |
| recorded passthrough entry unreadable at resolve (no fragment; non-current, currency unknown; never "detached", never a stale-home reason; `--repair` does not re-link it) | `environment_passthrough_unreadable` |
| recorded passthrough link path holds a regular file or an unexpected symlink target under `--repair` (no fragment; without `--repair` the same state is the stale-home reason above) | `environment_credential_conflict` |
| native credential storage selector outside the verified set at provisioning or repair (no fragment) | `environment_credential_unsupported` |
| store entry, lock, or marker file fails the §4 protected-boundary contract or its pin hash, or a `path` source directory fails its §4 boundary checks, at resolve (no fragment; non-current) | `environment_store_untrusted` |
| enclosing boundary (environments root or store root) cannot be proven at resolve (no fragment; non-current; nothing rebuilt) | `environment_store_untrusted` |
| dry-run evaluation of an entry-class failure of a store entry or a marker file, or of a lock file that fails its boundary checks (no mutation; a real operation would rebuild it) | `would-rebuild-untrusted-store` |
| dry-run evaluation of an enclosing-boundary failure, of a `path` source directory failure, or of an unreadable or malformed lock file (no mutation; no rebuild planned) | `environment_store_untrusted` |
| repair could not acquire the mutation lock within the bounded wait | `environment_lock_unavailable` |
| managed home cannot be repaired from the store | `environment_repair_failed` |
| S4 profile `s4-warn`: launch composition passes an operator variable outside the configured `passable_env_names` (warning, names the variables and the knob) | `mcp_env_passthrough_unlisted` |
| S4 profile `s4-enforce`: launch composition drops a requested name outside the effective `passable_env_names` (warning, names the variables) | `mcp_env_passthrough_dropped` |
| explicit `passable_env_names: null` under the `hardened` posture at profile install, profile update, or launch composition (refusal, names the knob; old lock stands) | `passable_env_names_unbounded_refused` |

## 11. Umbrella subcommand discovery

A CLI subcommand the manager does not implement resolves to an executable
named `curator-<name>` searched as the rollout profiles below state and is
executed with the remaining arguments verbatim — the established
git/kubectl/docker external-subcommand convention, closed to the search
each profile names. The rules are closed:

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
  is operator argv, the trust roots, and machine configuration alone.
- The provider trust roots, in search order, are exactly:
  1. the **install directory** — the directory holding the running manager
     executable, resolved after symlinks; then
  2. the machine-configuration `provider_directories` list (section 12.1),
     in listed order.
  The first executable regular file named `curator-<name>` directly inside
  a root wins; a non-executable file of that name is skipped, and search
  never descends into subdirectories. Every
  `provider_directories` entry MUST be an absolute path — POSIX-absolute
  or Windows drive-absolute, the two spellings the schema admits — and
  SHOULD name a directory only the operator administers: listing a
  directory a project can write re-opens the attack this section closes.
- A trust root the manager cannot read — the install directory or a
  `provider_directories` entry — is a read failure, never absence: lookup
  MUST fail with `subcommand_provider_root_unreadable`, naming the first
  unreadable root in search order, and MUST NOT fall through to a later
  root, to `PATH`, or to `subcommand_provider_missing`. An unreadable root
  is reported as unreadable, never as absence (section 8.4.1).
- The ambient `PATH` is not a trust root. Under revision A the ambient
  `PATH` still selects the provider (the pre-change behavior) and a
  selection outside the trust roots warns; under revision B the ambient
  `PATH` never selects — a `curator-<name>` found only by searching `PATH`
  is refused — and a `PATH` search under revision B is a diagnostic-only
  probe that names the refused path, never a dispatch. A `PATH`-only
  provider is never resolved silently under either profile.
- The resolved executable MUST NOT reside in a directory the manager itself
  publishes onto `PATH` — the user-bin shim directory, a managed skill bin
  directory, or any directory below the environments root — and a provider
  found there is refused with `subcommand_provider_untrusted`, naming the
  refused path and the trust roots consulted, wherever else the path was
  found: under revision A the refusal applies to the `PATH`-selected
  candidate, and under revision B it applies to a trust-root match and to
  a `PATH`-probe match alike, outranking dispatch in both. Together with
  the section 9.4 `curator-*` name reservation, this keeps
  profile-materialized files from poisoning dispatch; profile bytes were
  already excluded.
- Every dispatch reports the resolved absolute provider path: a warning
  names the resolved path, the trust roots consulted, and the migration
  hint; a `subcommand_provider_untrusted` refusal names the refused path
  and the trust roots consulted; `subcommand_provider_missing` names the
  trust roots consulted; `subcommand_provider_root_unreadable` names the
  unreadable directory; and `env status` names the same per provider
  under section 12.

The attack this rule closes is the S6-injected `PATH` (finding E4): a
project-controlled shell hook (finding S6 — a project `.agents/env.sh`
sourced on directory change) prepends a project directory to `PATH`,
planting a `curator-run` there, so that `curator run <env-id>` executes
the project's binary as the launcher with the operator's environment.
Under the trust-root rule that binary is outside the trust roots: under
revision A the planted binary still runs (the `PATH` selection is
unchanged) but warns, and under revision B it is refused.

This is the one place the manager executes an executable it does not ship;
under revision B the trust model is the two configured roots above, not
the ambient host plugin convention, while under revision A the roots are
the trust verdict and the ambient `PATH` still selects. The first providers, informative here, are `curator-run` (the launcher, its own
specification, Decision 0013) and `curator-session` (a shim to the agent
session manager).

**Rollout.** The change of trust is warn-first, in two explicitly labelled
conformance profiles:

- **Revision A (warning release).** Resolution is exactly the pre-change
  behavior: the manager searches the ambient `PATH` in order for the first
  executable regular file named `curator-<name>` directly inside a `PATH`
  entry, skipping non-executables and never descending. A `PATH` match
  inside a manager-published or managed directory is refused with
  `subcommand_provider_untrusted`, naming the refused path and the trust
  roots consulted. A trust root that cannot be read fails with
  `subcommand_provider_root_unreadable` instead of resolving. Otherwise,
  when the `PATH`-selected executable lies directly inside a trust root it
  resolves silently; when it lies outside the trust roots it still
  resolves but warns `subcommand_provider_outside_trust_roots`, naming the
  resolved path, the trust roots consulted, and the migration hint — list
  the provider's directory in `provider_directories` (for example, a
  `curator-run` in `/usr/local/bin`). When no `PATH` entry holds the
  provider the outcome is `subcommand_provider_missing`, naming the trust
  roots consulted, even when a trust root holds it: revision A never
  consults the trust roots for selection. Old behavior is otherwise kept.
- **Revision B (flip release).** The ambient `PATH` never selects. The
  manager searches the trust roots in order — the install directory
  first, then `provider_directories` in listed order — for the first
  executable regular file named `curator-<name>` directly inside a root,
  skipping non-executables and never descending. The five outcomes are
  mutually exclusive: (1) a trusted match — a candidate directly inside a
  trust root and outside every manager-published and managed directory —
  resolves silently; (2) a match inside a manager-published or managed
  directory is refused with `subcommand_provider_untrusted`, naming the
  refused path and the trust roots consulted; (3) when no trust root
  holds the provider, the manager performs a diagnostic-only `PATH` probe
  — the same ordered search revision A uses for selection, but its match
  is never dispatched — and a probe match is refused with
  `subcommand_provider_untrusted`, naming the probed path and the trust
  roots consulted; (4) when neither the trust roots nor the probe hold
  the provider, the outcome is `subcommand_provider_missing`, naming the
  trust roots consulted — a `PATH`-only match never reports missing;
  (5) a trust root that cannot be read fails with
  `subcommand_provider_root_unreadable`, naming the first unreadable root
  in search order, and no later root, probe, or absence outcome fires.
  No release both warns and refuses at once: revision A adds the warning
  and keeps `PATH` selection; revision B removes `PATH` selection and
  refuses.

### 11.1 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| unknown subcommand with no `curator-<name>` executable in the consulted search domain — revision A: no `PATH` match; revision B: no trust-root match and no `PATH`-probe match — and every trust root readable; names the trust roots consulted | `subcommand_provider_missing` |
| `curator-<name>` candidate inside a manager-published or managed directory (revision A: the `PATH`-selected candidate; revision B: a trust-root match or a `PATH`-probe match); or, under revision B only, a `PATH`-probe match outside the trust roots; names the refused path and the trust roots consulted | `subcommand_provider_untrusted` |
| revision A only (warning): `curator-<name>` `PATH`-selected outside the trust roots; names the resolved path, the trust roots consulted, and the `provider_directories` migration hint | `subcommand_provider_outside_trust_roots` |
| a trust root that cannot be read — the install directory or a `provider_directories` entry — under either revision; names the first unreadable root in search order; never absence, never a fallback | `subcommand_provider_root_unreadable` |

## 12. Status, machine configuration, and garbage collection

`profile list` reports every installed profile: name, root package name,
source identity, declared requirement (`range`, `tag`, or `revision` as
written), root version, lock hash, and current markers — the machine
default and every section 9.3 scope that differs. A `local` profile
reports `local` as its source, `-` for requirement, `0.0.0` as version, and
its lock hash. A `path` root reports `path` as its source, its recorded
source path as the identity, `-` for requirement, and whether it is
imported-from-native. A profile whose lock cannot be read is listed with
`environment_store_untrusted`, never omitted as not installed (section
8.4.1, lock row).

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
per home (section 8.3; `environment_backup_record_unreadable`,
non-current with currency unknown, when the inventory cannot be
established), managed-surface, backup, and marker paths blocked
by a link the manager does not own (section 8.3.1), orphaned managed
homes (section 9.2),
`environment_context_size_exceeded` where it applies, the effective
`transitive_system_modules` value with every dropped system module by
package and path where the `drop` policy skipped any (section 3), the resolved
absolute provider path and trust verdict for every `curator-<name>`
executable discovered by the active revision's search — revision A: the
`PATH`-selected executable with its trust verdict; revision B: the
trust-root match or the diagnostic-only `PATH`-probe match — and always
for `curator-run` and `curator-session`, reported missing when absent and
reported unreadable with the directory when a trust root cannot be read
(section 11), the `mcp_package_allowlist_empty` warning row when the MCP
package allowlist is empty under the `permissive` posture — under
`hardened` the row is an error row, non-current, when the current
profile's resolved closure carries an MCP declaration package (section
2.2) — the active S4 profile (`s4-warn` or
`s4-enforce`) with the effective `passable_env_names`, the section 2.3
surfacing rows for the current profile of each scope reported, the
signer-verification posture per lock member's source — `enforced` when an
allowlist is present, naming the verified signer, `unconfigured` when none
is, `required-missing` when `require_source_signers` is true and none is —,
the active update-confirmation revision (`A-warning` or `B-flip`, section
9.2) with its behaviour, the machine-level `require_source_signers`
value, the store-trust row per installed profile — the section 4
boundary and pin-hash verdict for the profile's lock, marker, named store
entries, and — for a `path` root or overlay — the source directory,
naming the failing check and the path or, for an enclosing failure, the
boundary (environments root or store root) when the profile is
`environment_store_untrusted`, the active codex-seed revision (`A` or `B`, section 7.4) with its
behaviour, per managed `codex_cli` home the `codex_seed_record`
revision with its native-server rows (`mcp_native_servers_ungoverned`
for the native names an `A`-record home carries,
`mcp_native_servers_not_inherited` for a `B`-record home's stripped
names, `mcp_seed_unstripped` with the re-provision hint when the marker
predates the rule or when an `A`-record home with a non-empty snapshot
is served by a revision-`B` manager), and the `security_posture` header row —
the profile in force (`permissive` or `hardened`) with its provenance —
followed by the thirteen posture rows of the manager §10 table, identical
in gate name, order, value, and provenance on `env status` and `curator
status`: `hook-trust`, `registry-policy`, `audit-mode`,
`source-allowlist`, `env-passthrough`, `transitive-system-modules`,
`provider-trust-roots`, `source-signers` (the per-source
enforced/unconfigured/required-missing rows above are unchanged),
`update-confirmation`, `codex-seed` (the per-home `codex_seed_record`
native-server rows above are not posture rows and stay unchanged),
`store-boundary` (the per-profile trust verdicts
stay in the store-trust row above), `write-discipline`, and
`mcp-package-allowlist`. No other `env status` posture row exists.
Revision and always-on gates report `shipped` provenance; knob gates
report `profile`, `explicit`, or `lock`. Both commands follow
the manager §10 discipline exactly: recompute and report, never mutate — no
fetch, no repair, no adoption, no channel application, no onboarding.
`--check` returns non-zero when any row is non-current.

An installation row is current only when its marker is valid and supported;
profile identity, lock hash, member list, precedence, mode, and form match
the effective machine state; every recorded surface hash verifies; and
every recorded passthrough entry is live. A drifted, missing, shadow-inert
(unless acknowledged under `shadow_acknowledged`), detached, partially
switched, stale, store-untrusted (`environment_store_untrusted`),
refused-provider (section 11), link-blocked (section 8.3.1), or
unreadable state is non-current; unreadable evidence is
reported as unreadable, never as absence (section 8.4.1). A section 11
provider row is non-current when the active revision refuses or fails
that provider — a manager-published or managed directory match under
either revision, an outside-trust-roots `PATH` match refused under
revision B, or an unreadable trust root failed under either revision with
currency unknown; a `PATH`-absent row under revision A is missing
(non-current) even when a trust root holds the provider. Under revision A
the `subcommand_provider_outside_trust_roots` warning row stays current.
A `hardened` machine whose effective values contradict the profile
(manager §10: empty `allowed_sources`, explicit `null`
`passable_env_names`, or an empty `mcp_package_allowlist` while an
installed profile's resolved closure carries an MCP declaration package)
is non-current, and `--check` returns non-zero. Warnings —
`environment_context_size_exceeded`, `environment_tool_version_unverified`,
`environment_seed_shadowed`, `environment_foreign_manager_suspected`,
`context_system_module_dropped`, `mcp_package_allowlist_empty` under the
`permissive` posture (under `hardened` with an MCP declaration in the
closure it is the non-current error row above),
`mcp_env_passthrough_unlisted`, `mcp_env_passthrough_dropped`,
`mcp_native_servers_ungoverned`, `mcp_native_servers_not_inherited`,
`mcp_seed_unstripped`, an acknowledged shadowing path — never make a row
non-current.

The signer-verification rows re-verify the locked pins against the
effective allowlists from the manager's local source state, without
fetching: an `enforced` row names the verified signer when the local state
reproduces the verification and `unknown` when it cannot. An `enforced`
row whose locked pin fails against the effective allowlist is non-current;
`unconfigured` and `required-missing` rows are informative and never make
a row non-current.

The update-confirmation row reports `A-warning` when the manager ships
revision A of section 9.2 — a triggered delta warns
`profile_update_system_delta` and proceeds — and `B-flip` when it ships
revision B — a triggered delta refuses with
`profile_update_confirmation_required` unless the invocation carries
`--confirm-system-delta`. The row is informative and never makes a row
non-current; no configuration knob pre-confirms.

The codex-seed row reports `A` when the manager ships revision A of
section 7.4 — the `codex_cli` seed is copied whole and provisioning warns
`mcp_native_servers_ungoverned` with the migration hint — and `B` when it
ships revision B — the seed strips `mcp_servers` and provisioning reports
`mcp_native_servers_not_inherited`. A home whose recorded seed revision
is older than the shipped one — revision `A` under a revision-`B`
manager — additionally reports `mcp_seed_unstripped` with the
re-provision hint while its recorded names stay listed as ungoverned
(section 7.4). The row is informative and never makes a row non-current;
no configuration knob selects the revision.

Garbage collection extends the manager §10 and core §9.4 rules: it runs
under the manager-home mutation lock, and its live roots additionally
include every store entry named by any installed profile's lock — and by
a retained previous lock until it is dropped (section 9.2) — every managed
home and in-place surface set referenced by a valid environment marker, and
every entry referenced by an in-flight transaction journal. An unreadable
marker (`environment_marker_unreadable`, section 8.4.1), an unreadable lock
(entry-class `environment_store_untrusted`, section 8.4.1), or another
unprovable reference fails safe: the uncertain entries are retained and the
uncertainty reported. An
enclosing boundary that cannot be proven refuses collection before its
first write — nothing is collected and nothing is rebuilt, and the
uncertainty is reported; the operator repairs the boundary out of band.
Garbage collection revalidates the section 4 boundary for every entry it
considers inside a proven enclosing boundary: an entry that fails the
contract is retained, never collected, and reported; collection never
rebuilds an entry — rebuild is repair's work (section 10.1).
Environment-owned mutable state
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
| `overlays.<profile>` | ordered list of `{ source, range \| tag \| revision, directory?, weight? }` for a `git` source, `{ source, weight? }` for a `path` source | empty | 6 |
| `overlay_default_weight` | non-negative integer | `1000` | 6 |
| `overlays_allowed` | boolean | `true` | 6, 12.2 |
| `precedence.winner` | `higher-weight`, `lower-weight` | `higher-weight` | 6 |
| `precedence.placement` | `winner-last`, `winner-first` | `winner-last` | 6 |
| `forms.<env-id>` | `monolithic`, `referenced` | adapter default | 7.2 |
| `system_prompt_files.<profile>.pi` | `off`, `append`, `replace` | `off` | 5.5 |
| `targets.<target-id>.participation` | `auto`, `off`, `enabled` | `auto` | 7.6 |
| `targets.<target-id>.consented` | boolean | `false` | 7.6 |
| `isolation.<profile>.<env-id>` | `shared`, `isolated` | `shared`; `isolated` for `claude_code` on macOS at the pinned release | 7.4 |
| `permissions.<profile>` | `native`, `yolo` | absent (a silent level) | 10.1 |
| `xdg_seed_allowlist` | list of XDG config entry names | `["git", "gh", "ssh"]` | 7.1 |
| `passable_env_names` | list of identifiers, or `null` for explicit unbounded | `[]` | 2.2, 10.3 |
| `mcp_package_allowlist` | list of canonical source identities | empty (permits all, warned) | 2.2 |
| `shadow_acknowledged` | list of `{ env, path }` | empty | 7.5, 12 |
| `secret_material_waivers` | list of `{ pin, file, span: [start, end], reason }` | empty | 9.1 |
| `transitive_system_modules` | `drop`, `error` | `drop` | 3, 5.5 |
| `system_module_waivers` | list of `{ package, reason }` | empty | 3, 5.5 |
| `backup_retention` | non-negative integer, `0` = unlimited | `5` | 8.3 |
| `require_current_profile` | profile name or `null` | `null` | 12.2 |
| `in_place_mode.<env-id>` | `linked`, `copied` | adapter default | 8.1 — the `claude_code` root-context surface is always copied whatever this value says |
| `provider_directories` | list of absolute paths | `[]` | 11 |
| `source_signers.<source>` | map from canonical source identity to the source's signer allowlist: a list of `{ type, key }` ssh entries and `{ type, fingerprint }` gpg entries | `{}` | 1.4, 12.2 |
| `require_source_signers` | boolean | `false` | 1.4, 12.2 |

Four knobs take part in the machine security posture of manager §7.1:
under the `hardened` posture an absent `transitive_system_modules`
resolves to `error` instead of `drop`, an absent `require_source_signers`
resolves to `true` instead of `false`, an empty `mcp_package_allowlist`
is a resolution error instead of a warning when the closure carries an
MCP declaration package (section 2.2), and an explicit
`passable_env_names: null` is refused (section 10.3). The table above
still states each knob's own default; the posture selects which default
an absent knob takes, and the two refusals are the profile's meaning,
not defaults.

A `secret_material_waivers.pin` is spelled as the member's pin exactly as
the lock (section 1.3) and the marker (section 8.2) record it: bare
lowercase hex, 40 characters for a `commit` pin or 64 for a
`state_sha256` pin, with no `sha256:` prefix — the grammar
`manager-config-v2` enforces.

A `system_module_waivers` entry carries `package`, a portable identifier
(core §2) naming a `context` member of the lock, and `reason`, free text
recording why the operator admits that package's system modules. An entry
naming no member of the lock has no effect.

A `source_signers` key is a canonical source identity exactly as the lock
(section 1.3) spells it. Each entry carries `type` exactly `ssh` or `gpg`:
an `ssh` entry carries `key`, an OpenSSH public key line — `<key-type>
<base64> [<comment>]` where `<key-type>` is exactly one of `ssh-ed25519`,
`ssh-rsa`, `ecdsa-sha2-nistp256`, `ecdsa-sha2-nistp384`,
`ecdsa-sha2-nistp521`, `sk-ssh-ed25519@openssh.com`, or
`sk-ecdsa-sha2-nistp256@openssh.com`; a `gpg` entry carries `fingerprint`, exactly 40 uppercase hex
characters. An `ssh` entry MUST NOT carry `fingerprint`, and a `gpg`
entry MUST NOT carry `key`. An `ssh` entry's identity is its key type
plus its base64 key material; the trailing comment is not part of the
identity — the same key under another comment still matches, and
different material never does. A source absent from the map has no
allowlist and is never verified; a source mapped to an empty list has an
allowlist that admits no signer.

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
`passable_env_names`, `require_current_profile`, `transitive_system_modules`,
`isolation`, `provider_directories`, `source_signers`,
`require_source_signers`, and `permissions` — a locked provider list is fleet
policy for which provider directories every machine trusts. A system
file that locks `require_current_profile` to a profile name makes `profile
use` of any other profile in the machine scope a configuration error under
the manager §1 locked-key rules, and `env status` reports the requirement;
a locked `overlays_allowed: false` empties every overlay list with the
manager §1 warning. The manager §1 credential rule stands: no key that
selects or constrains credential material is lockable, and `isolation` is
lockable only in the direction of `shared`. `transitive_system_modules`
is lockable only in the direction of `error`: a system file MUST lock
`transitive_system_modules` only to `error`, and `system_module_waivers`
MUST NOT be lockable — a lock MUST NOT admit a transitive package's system
modules. `require_source_signers` is lockable only in the direction of
`true`: a system file MUST lock `require_source_signers` only to `true`.
`permissions` is lockable only in the direction of `native`: a system
file MUST lock `permissions` only to `native`. A locked `permissions`
map replaces the machine knob whole with the manager §1 warning when
the machine file set it; total silence under an engaged lock resolves
`native` — the lock redefines the effective default on that machine
(section 10.1).
A locked `source_signers` map is fleet policy per source: for a source the
system file names, the effective allowlist is the system file's list and
the machine file's list for that source is ignored — with the manager §1
override warning naming the system file when the machine file names that
source — while a source the system file does not name takes the machine
file's list. An unlocked system `source_signers` is a default the machine
knob replaces whole (manager §1 rule 3).

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
`context-lock-v1` (section 1.3), `agent-environment-marker-v1` and
`agent-environment-marker-v2` (section 8.2), the rewritten
`launch-env-fragment-v1` (section 10.2)
— which requires `argument` on every `flag` descriptor and `name` exactly
when `argument` is `name`; the Decision 0012 §9 worked example, which omits
`argument` on its system-prompt descriptors, is read as pre-revision —
and `launch-env-fragment-v2` (section 10.2) — revision v1 plus the
REQUIRED closed `permissions` member —
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
materialization bytes per adapter (section 5.8); the section 3
system-module admission cases — a direct package materializes, a
transitive module under `drop` is skipped with its warning and the
materialized bytes are exactly the admitted modules' bytes, the same
module under `error` refuses with `context_system_module_transitive`, a
waiver admits it, and a package named by an active overlay's `requires`
is direct — with the `transitive_system_modules` and
`system_module_waivers` machine-config schema cases and the system-config
error-direction case; the detector classes of
section 9.1 (`vectors/context-detectors.json`, positive and negative, the
waiver and unpinnable cases included); the section 2.3 surfacing bytes
and install/update surfacing order, the section 10.3 S4 rollout profiles'
default resolution, and the `mcp_package_allowlist_empty` warning
(`vectors/environments-env-passthrough.json`); the `passable_env_names`
schema default (`vectors/manager-config-v2.json`); the section 1.2 snapshot
byte-exactness vector (`vectors/snapshot-acquisition.json`); and the
section 11 umbrella provider trust-root vectors
(`vectors/umbrella-provider-resolution.json`): the install-directory and
listed-directory positives, the listed-order first-match-wins case, the
revision-A `PATH`-selection cases (trusted-on-`PATH` silent,
`PATH`-selects-different warning, install-only missing), the revision-A
warning and revision-B refusal of a `PATH`-only provider including the
S6-planted `curator-run`, the manager-published and managed directory
refusals under both revisions, the unreadable-root failures under both
revisions, and the missing case — with the
`provider_directories` grammar pinned by the `manager-config-v2` and
`system-config-v2` schema cases; the section 12.1 `permissions`
per-profile mode grammar with the `native`-alone system direction case
(`vectors/manager-config-v2.json` and the `manager-config-v2` /
`system-config-v2` schema cases); the section 1.4 signer-verification cases
(`vectors/environments-source-signers.json`) — an allowlisted ssh tag
signature accepted, an allowlisted gpg commit signature accepted, an
unsigned candidate refused, a wrong-signer candidate refused, a same-key
ssh signature under another comment accepted, a different-material ssh
signature refused, no allowlist accepted with the `unconfigured` posture,
`require_source_signers` with no allowlist refused, the locked-list
against machine-addition merge, and the update-confirmation revision row —
with the `source_signers` and `require_source_signers` machine-config
schema cases, the exact-length fingerprint cases, and the system-config
direction case; and the section 9.2 update-delta cases (same file) — the
added, removed, and moved lines, no system or MCP change needing no
confirmation, a new system module, a changed MCP `args`, `url`, or
selector, and a reordered `env_names` warning under revision A and
refusing under revision B, `--confirm-system-delta` proceeding, a
reinstall refusing under revision B and proceeding with the flag, and
`--all` confirming every profile of the run; the section 8.3.1
write-discipline vectors
(`vectors/environments-write-nofollow.json`) — the symlinked-target
takeover (replaced with backup under authorization, stopped with
`environment_foreign_manager_detected` without), the symlinked-parent
refusal with `environment_write_would_follow_link` under both
authorization states, the post-provisioning planted-link repair, the
manager-owned-link replace, the symlinked-backup-destination refusals (a traversed parent link and a directly symlinked target),
the inside-pointing-link ledger refusal, and the clean-path and
recorded-file positives — every foreign-link case asserting the link's
former target is byte-identical afterwards;
the section 4
protected-boundary cases
(`vectors/environments-store-boundary.json`) — the intact resolve that
emits a fragment; the swapped system-prompt bytes, swapped root-context
bytes, symlinked entry root, wrong ownership, wrong permissions,
containment escape, non-regular component, and pin-hash mismatch cases
that refuse with `environment_store_untrusted` and emit no fragment; the
environments-root and store-root enclosing-boundary cases that refuse with
no rebuild; the intact-updated-store with old marker case that reports
`environment_home_stale` and repairs, and the swapped-updated-store with
old marker case that refuses with `environment_store_untrusted` and is
never adopted; the unprovisioned-home intact and swapped cases; the
unreadable-marker case that reports
`environment_marker_unreadable`; the dry-run `would-rebuild-untrusted-store`
entry-class case and the enclosing no-rebuild case; the repair rebuild,
entry-rebuild, enclosing-refusal, stale-repair, and unprovisioned cases;
the `env status` non-current posture rows naming the failing check and the
boundary; and the negative cases whose fragment-emitting,
current-reporting, or re-applying observation is non-conforming;
the section 7.4 codex-seed
cases (`vectors/environments-codex-seed.json`) — a native `config.toml`
with `mcp_servers` tables under revision A (copied whole,
`mcp_native_servers_ungoverned` names the entries, posture lists them
ungoverned) and under revision B (the seeded file lacks them,
`mcp_native_servers_not_inherited` names them), a native file without
`mcp_servers` entries (no warning under either revision, the record still
written), the pre-rule-home `mcp_seed_unstripped` posture, and the
revision-A home under a revision-B manager (`mcp_seed_unstripped` with
the re-provision hint, the recorded names still ungoverned) — with the
`codex_seed_record` marker shape;
and the section 2.2 and section 4 path-kind admission cases
(`vectors/environments-path-kind-admission.json`) — the `git` MCP
declaration admitted, the `path` root, overlay, and onboarding-import MCP
declarations refused with `mcp_declaration_path_source_refused` naming the
package and the declaration, the directly named `path` overlay with a
system module admitted when its directory passes the contract, the `path`
root, the `path` overlay, and the onboarding import without system
modules admitted, the world-writable, symlinked-component,
wrong-ownership, containment-escape, and non-regular-component
directories refused with `environment_store_untrusted`, no fragment, and
a posture row naming the path and the failing check, the world-writable
no-system overlay and the untrusted no-system onboarding import refused
the same way regardless of content class, the transitive `path` system
module refused with `context_system_module_transitive`, the dry-run
evaluation of a `path` directory failure reporting
`environment_store_untrusted` with no rebuild planned and mutating
nothing, and the negatives whose admitted, current-reporting,
rebuilding, or would-rebuild-reporting observation is non-conforming; and the
section 2.2/10.3/12 hardened-posture cases
(`vectors/security-posture.json`) — the revision-A permissive default
with its warning, the revision-B hardened flip, the effective defaults
under each posture, explicit-value and lock precedence, the three
profile refusals, the unreachable-registry warning versus error, and the
posture rows with their provenance; and the section 9.5 dotfile-manager
state-table cases (`vectors/environments-dotfile-managers.json`) — the
closed per-manager, per-platform table pinned cell by cell in the
vectors, one `environment_foreign_manager_suspected` case per located
cell, one quiet case per platform, the `none`-cell inert rule, the XDG
override, empty, relative, and Windows cases, the symlink,
regular-file, and unreadable quiet cases, and the two multi-present
table-order cases — recomputed by
`validate_environments_dotfile_managers_vectors`, which refuses a
name-preserving replacement. The nine
retired `expected/environments/*` sets are regenerated under the v2 type
line. A manager claiming this capability MUST pass the complete vector set;
there is no partial claim. A manager conforms to revision A by warning
where the vectors warn and failing where they fail, and to revision B by
refusing or failing where the vectors refuse or fail; it MUST NOT claim
revision B while still resolving on `PATH`. A manager conforms to the
update-delta revision A by warning with `profile_update_system_delta`
where the vectors warn, carrying the migration hint, and proceeding, and
to revision B by refusing with `profile_update_confirmation_required`
where the vectors refuse unless `--confirm-system-delta` is given. A
manager conforms to the codex-seed revision A by copying the native
`config.toml` whole, warning with `mcp_native_servers_ungoverned` where
the vectors warn and carrying the migration hint, and to revision B by
seeding without `mcp_servers` and reporting with
`mcp_native_servers_not_inherited` where the vectors report; it MUST NOT
claim revision B while still inheriting native servers.

The section 8.4.1 absence-versus-read-failure cases
(`vectors/environments-read-failure.json`) pin unreadable-but-present to its
typed discriminating inputs for five file classes: markers at the
open/read/parse stages (permission-denied, I/O, unparseable, and
schema-invalid cases report `environment_marker_unreadable`, never
`environment_home_stale`; a marker failure that violates the section 4
contract, or that prevents proving the boundary, stays
`environment_store_untrusted` under the section 8.4.1 precedence rule);
locks (all seven failure classes — permission-denied, I/O, unparseable,
schema-invalid, symlink-where-regular-required,
directory-where-file-expected, parent-not-directory — report entry-class
`environment_store_untrusted`, never `profile_unknown`; repair and update
against an unreadable lock refuse with nothing rebuilt and nothing
written); provisioning seeds (the six applicable classes report
`environment_seed_unreadable` and provisioning stops, including a
non-regular seed path and unparseable revision-B `config.toml` bytes);
passthrough entries (lstat/readlink permission-denied, I/O, and
parent-not-directory report `environment_passthrough_unreadable` at status
and at resolve with no fragment, and `--repair` leaves the entry
untouched; a directory at the entry path stays detached-side); and backup
records (an unreadable generations inventory reports
`environment_backup_record_unreadable` at status with currency unknown
and stops restore before mutating). Each class carries absence-side
positives pinning the contrast — an absent marker is
`environment_home_stale`, an absent lock is `profile_unknown`, an absent
seed provisions through, a missing link is
`environment_passthrough_detached` (a stale-home reason at resolve), an
absent backup inventory reports zero at status and nothing to restore —
and negatives whose absence-shaped observation (stale, unknown,
provisioned-through, detached, reported-empty) — or, for the lock,
rebuild-shaped observation — is non-conforming, checked by
`validate_environments_read_failure_vectors`.
