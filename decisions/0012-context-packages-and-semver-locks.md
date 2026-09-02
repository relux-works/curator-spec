# Decision 0012: context packages, semver-locked closures, and launch-channel MCP

## Status

Proposed 2026-09-02. Draft for review; nothing here is normative yet.
Acceptance authorizes rewriting the affected sections of
`protocol/environments.md` in place — the document stays at revision 1,
which was claimed by no implementation and carried by no tag; only the
generation-header type line bumps to `curator-root-context-v2` — together
with the new schemas and vectors, the manager-profile and CLI text, and the
withdrawal of the two schemas this decision retires, as separately tracked
work. It changes nothing in the frozen `protocol/core.md`. It supersedes
the profile-repository shape of Decision 0010 (Decisions 2, 5-composition,
and 8) and leaves every other Decision 0010 rule in force. Section
references without a document name refer to `protocol/core.md`;
"environments §N" names `protocol/environments.md` revision 1 as landed at
`4d55698`.

## Context

Decision 0010 shaped a profile as a directory inside one repository: an
index (`Profilefile.json`), a module manifest, an optional skill declaration
file, and machine-declared overlays. That shape served the first question —
one operator, a company context beside a personal one — and it shipped with
byte-exact materialization, an adapter registry, managed homes, and a launch
fragment that the pre-implementation review (STORY-260901-zddtn8) left
standing.

It does not serve the organizational question. An organization wants
context as a **graph of reusable units**: a company core, a developers core,
domain contexts (iOS, Figma), an organizational-structure context — each
owned by a different team, versioned on its own cadence, installable on its
own as a root — and role umbrellas that assemble them for a person:
`companyA-root-context-ios-developer-umbrella` depends on the core, the
developers core, the iOS and Figma contexts, and is what an iOS developer
installs. Each unit must be able to say which global skills and which MCP
servers its instructions assume. Versions must resolve like a package
ecosystem resolves them — by semantic version ranges with collisions
detected — because units evolve independently. And when two units disagree,
the person who assembled the umbrella, not the manager, must decide whose
instructions carry more weight.

Curator already has the machinery this needs — for skills. Skill packages
are git snapshots or directories within one, with a canonical source
identity, exact references, a manifest, transitive `dependencies.skills`, a
provider-first closure with the invariant "one name resolves to exactly one
commit", read-only MCP requirements, a commit-keyed store, and an audit
pipeline. What skills lack is version *ranges*: the protocol admits only
exact tags and revisions, and the closure fails when two declarations name
different commits. That exactness is a feature — installations are
reproducible — and it is preserved here by the standard package-ecosystem
move: declarations carry ranges, installations carry a **lock** of exact
commits, and the lock is the identity. The operator's "semver for skills"
is honored wherever a lock exists: a context package requires skills by
range and the profile lock pins them. A project `Skillfile.json` has no
lock today, so its declarations keep the exact forms of §4.4 until a
project lock is decided (Open question 6).

The review also settled two adjacent facts this decision relies on. The
first is its M1 resolution, Option A: `curator-run` composes a
caller-supplied launch plan into `ax start --launch-plan`, and `SpawnPlan`
gains `stdin` — to be recorded as its own decision under the next free
number after reconciliation with the swift-driver draft's 0011. The second
is that materialization into managed homes plus an inert file plus a
launcher-applied channel is the pattern that lets Curator carry a surface
without executing anything or writing into a tool's mutable state. MCP
configuration rides that pattern.

## Decision

### 1. Context packages

A **context package** is a second package kind on the existing package
machinery: a git snapshot or a directory within one, carrying a root
`agent-context.json` (strict schema 1) and a `context/` directory of
modules. The manifest declares:

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
      "companyA-root-context-developers-figma": { "git": "…", "path": "contexts/figma", "range": "^1.0", "weight": 40 }
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

- `name` is a portable identifier (§2) and MUST equal the name every
  requirer uses for it. `version` is a strict semantic version (Decision
  2). For a package resolved from a version tag — by range or by an exact
  version-shaped `tag` — `version` MUST equal that tag's version, else
  `context_version_mismatch`. For a package pinned by `revision` or by a
  tag that is not a version, the manifest `version` at that commit is the
  package's version. For a `path` package the manifest `version` is
  authoritative and no tag check applies.
- `weight` is a non-negative integer at most 2147483647, default `0`: the
  package's own default precedence weight (Decision 4). `weights` is
  OPTIONAL and meaningful only in the root package (Decision 4).
- `context` carries the module manifest of environments §3 unchanged
  (`path`, `environments` selector, `class` root|system), moved inline;
  `context/` and its byte rules are unchanged. `context` MAY be absent: a
  package with no modules of its own is a pure umbrella.
- `requires` names other context packages, skills, and MCP declaration
  packages. Every entry carries a canonical git source (§6.1) and exactly
  one of `range` (Decision 2), `tag`, or `revision` (the §4.4 exact forms).
  A context or MCP requirement MAY carry `path`, a portable relative path
  naming the package's directory within the snapshot — new wire for those
  two kinds. A skill requirement carries no `path`: a skill package is
  addressed exactly as §4.4 addresses it, and `mode` and `commands` keep
  their §4.4 meaning. A context requirement MAY carry `weight` to override
  the required package's own default (Decision 4).
- `CONTEXT.md` at the package root is informative and never materialized.
  Files not named by the manifest are inert and participate only in
  snapshot identity and audit.

There is no umbrella kind. Any context package with `requires.contexts` is
an umbrella; any context package — umbrella or not — installs as a root. A
role umbrella whose modules are empty is a valid, common shape.

### 2. Versions, ranges, and resolution

**Versions.** Version tags are strict Semantic Versioning 2.0 with a
mandatory `v` prefix: `v<major>.<minor>.<patch>[-<prerelease>]`, under the
§6.3 tag grammar. Build metadata is not admitted: a tag carrying `+<build>`
is not a version candidate. A tag that does not parse is not a version
candidate and is silently outside every range; it remains addressable by
the exact `tag` form. Versions are totally ordered by the SemVer 2.0
precedence rule (`1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-beta < 1.0.0`).
Because build metadata is excluded and tag names are unique within a
repository, no two candidates of one source share a version, so "the
highest satisfying candidate" is always unique.

**Ranges.** The range grammar is closed. Its semantics are those of
node-semver (the npm implementation; README sections "Caret Ranges",
"Tilde Ranges", "X-Ranges", "Prerelease Tags", verified against 7.7.4),
restricted as stated. A range is one or more **comparator sets** joined by
`||`; a candidate satisfies the range when it satisfies any set. A
comparator set is one or more primitives joined by whitespace; a candidate
satisfies the set when it satisfies every primitive. Primitives:

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
spelling equivalent to `*` (in npm, `latest` is a distribution tag, not
range grammar). `*`, `x`, and `latest` select the highest **stable**
version.

**Prereleases.** A version with a prerelease satisfies a range only when
some primitive of a satisfied comparator set names a prerelease on the same
`major.minor.patch` — the npm rule: `2.0.0-rc.1` satisfies `^2.0.0-rc.0`
and `>=2.0.0-rc.0`; `2.1.0-rc.1` satisfies neither; `2.0.0-rc.1` satisfies
none of `*`, `>=1.0.0`, `<3`. An operator who wants a prerelease names one.

**Resolution.** Resolution is the §7 closure with its admission rule
generalized from exact refs to constraints. Every requirement on one
package name MUST agree on the canonical source identity (unchanged). A
requirement contributes a **constraint**: a `range` as written; an exact
`tag` or `revision` as a fixed candidate. The **effective constraint** of a
name is the intersection of every current constraint on it; an exact
constraint fixes the name's only candidate — that commit, carrying the
version defined in Decision 1 (the manifest `version` for contexts and MCP
packages; for a skill, the version of the highest version tag of its source
that peels to that commit, or no version) — and every range on the name
MUST admit that version. Two exact constraints on one name MUST peel to
one commit (§7, unchanged; different refs resolving to one commit unify).
The candidates of a name are the source's version tags, peeled under §6.3.

The algorithm is fixed so that two managers lock identically:

1. **Seed.** The constraint set holds the root's install declaration
   (Decision 7) and every overlay declaration (Decision 5), each attributed
   to the machine; the root and each overlay are pending names.
2. **Select and expand.** While a pending name exists, take the
   lexicographically smallest (Unicode scalar value order, as §7). Compute
   its effective constraint; if empty, fail `context_range_conflict`. Select
   the highest candidate satisfying it — for a `||` disjunction, the
   highest candidate satisfying any member — and expand the manifest at
   that commit: every requirement it declares is added to the constraint
   set, attributed to this name at this version, and every name whose
   constraint set changed becomes pending.
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
conflict rather than searching. After resolution the §7 invariant holds
unchanged: one name, one commit. A cycle among context packages fails and
names the cycle (§7).

**Skills in the closure.** Skill requirements from context packages carry
ranges and resolve by exactly the rule above, jointly with every other
skill requirement of the closure — including a skill manifest's own exact
`dependencies.skills` (§4.4), which enter as fixed candidates. The
requirement-edge semantics of §7 (activation modes, command narrowing) are
unchanged. Project `Skillfile.json` and the skill manifest keep §4.4
unchanged: no range enters a surface that has no lock (Open question 6).

### 3. The lock is the identity

The result of resolution is the profile **lock**: a strict schema-1 object
(`context-lock-v1`) naming the root and listing every closure member —
contexts, skills, and MCP declarations, the root and the overlays among
them — with its `kind` (`context`, `mcp`, or `skill`), `name`, canonical
source identity (absent for a `path` package) and, when declared, its
`path` within the snapshot, resolved `version` (absent for a skill pinned
exactly with no version tag), its pin — `commit`, or `state_sha256` for a
`path` package: the revision-1 pin shape — its effective weight (Decision
4), its `required_by` list (the sorted names of its direct requirers; empty
for the root), and whether it is an `overlay`.
Members are sorted by (`kind`, `name`), bytewise. A `path` member's source
path stays in machine configuration and the environment marker; it never
enters the lock, so the lock hash is the same on every machine that locks
the same bytes. The lock is machine state below the manager home, never
repository content. Its CCJ-1 hash (`registry.md` §1) is the **lock
hash**, and the lock hash is the profile's effective pin everywhere
Decision 0010 used a commit: the generation header, the environment
marker, the launch fragment, `profile list`, and the `ax` extension key
that records the profile pin (ax PR #1, `works.relux.curator.profile-pin`).

Store entries stay commit-keyed per package (state-hash-keyed for a
`path` package) — the runtime-store pattern — so two profiles sharing a
package share its entry. A profile's store identity is the set of entries
its lock names.

`profile install` resolves and writes the lock; `profile update`
re-resolves (Decision 8) and writes a new lock only when the new closure
passes the always-strict audit of environments §9.1 in full — a blocking
finding on any new member leaves the old lock in place and is reported.
Nothing re-resolves implicitly: `profile use`, `profile sync`, `env
resolve`, and status read the lock they find.

### 4. Weights and precedence

Every closure member has one **effective weight**, computed by exactly
these rules in order, each overriding the previous:

1. the member's manifest `weight`;
2. the `weight` declared on the requirement edge by its direct requirers.
   When several direct requirers declare an edge weight for one member they
   MUST agree, else `context_weight_conflict` naming every requirer and its
   value — unless rule 3 names the member, in which case the root has the
   final word and the disagreement is reported as a warning;
3. the root package's `weights` map. The root's own edge weights are
   treated as entries of this map; a package named both on a root edge and
   in the map is `context_weights_duplicate`. A `weights` entry naming a
   package outside the closure is `context_weight_unknown`;
4. for a member declared as a machine overlay (Decision 5), the weight the
   overlay declaration assigns — machine configuration outranks repository
   content, so a package that is both an overlay and a requirement takes
   the overlay's weight.

`weights` is meaningful only in the root. A non-root member whose manifest
carries a non-empty `weights` map is `context_weights_not_root` at
resolution time — snapshot validation stays position-independent — so a
package authored as a root MAY be reused as a dependency exactly when its
map is empty or absent.

Weights order chapters and nothing else in this revision. They never merge
instruction text and they never resolve a version constraint: an empty
range intersection fails regardless of weights. Machine configuration
declares the **precedence policy** as two independent primitives, each
closed:

- `winner`: `higher-weight` (default) or `lower-weight` — which side of a
  weight comparison prevails;
- `placement`: `winner-last` (default) or `winner-first` — whether the
  prevailing material is emitted last or first in the materialized root
  context.

The default pair reproduces Decision 0010's `later-overrides-earlier`
reading; either primitive may be changed without the other. Materialization
sorts the closure's context members by effective weight and places the
winning end of that order — the heaviest under `higher-weight`, the
lightest under `lower-weight` — last under `winner-last` and first under
`winner-first`. Members of equal weight keep their relative §7 topological
order in every case; the root participates in that order as an ordinary
node, and `placement` never inverts a tie. One chapter is emitted per
context member that has applicable modules; a member's own modules stay
contiguous in manifest order. The generation header states both primitives
and lists every context member with its weight in emitted order, so a
reader and the agent see the hierarchy the assembler intended.

### 5. Machine overlays

Machine configuration MAY declare, per installed profile, an ordered list
of overlays. An overlay is an ordinary context package named by a `git`
source with a range or exact form, or by a `path` source (an operator-local
directory under the environments §1 `path` rules) — a personal repository
or a local directory on the machine. Each overlay declaration carries a
machine-assigned weight (default: the configurable machine default,
initially above any root weight so that personal refinements prevail under
the default policy) and joins the closure: its own requirements resolve
jointly with the root's, so an overlay that needs a skill version the root
forbids is a reported `context_range_conflict`, never a silent second copy.
Overlay declarations are the only composition surface; a package MUST NOT
declare overlays. The lock records overlays as members flagged `overlay`.

### 6. MCP declaration packages and launch-channel materialization

An **MCP declaration package** is a third package kind: a git snapshot or
directory with a root `agent-mcp.json` (strict schema 1):

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

`transport` is exactly `stdio` or `http`. `stdio` carries `command` and
`args`: `command` MUST be a bare executable name — no path separator, no
absolute or relative path — that the tool resolves on `PATH` at launch;
anything else is `mcp_declaration_invalid`. `http` carries `url`, which
MUST use the `https` scheme with an ASCII host and MUST carry no userinfo,
query, or fragment. `args` and `url` are inside the `context-secret-material`
detector scope: a token in an argument or a URL is a blocking finding like
a token in a module. `env_names` lists environment-variable **names** the
server expects at run time; each MUST match the §2 identifier grammar and
MUST NOT name a manager-reserved variable (the manager §3.1 reserved set —
`PATH`, `HOME`, the `LD_`/`DYLD_`/`NODE_` families, and the rest), and
machine configuration MAY bound the passable names further by a lockable
allowlist. Values never appear in any package, lock, marker, fragment, or
materialized file; the operator's environment supplies them. `environments`
is the environments §3 selector: the adapters whose materialized set
includes this server; absent means every adapter. The manager never
executes, installs, updates, or launches a server. It verifies, read-only,
that a `stdio` command resolves on the operator's `PATH` and warns when it
does not — the manager §6 discipline — and it audits the package like any
other.

Materialization is a **launch channel**, the environments §5.5 pattern.
The resolved MCP set of a profile materializes as one inert, hashed,
marker-recorded file per adapter format below `<home>/.agent-context/mcp/`
in a managed home only — never into a native in-place home, whose MCP
configuration lives in tool-owned mutable state — and the launch fragment
gains an `mcp` section naming the file, the sorted union of the `env_names`
of the servers in that adapter's set, and the adapter's channel descriptor.
The descriptor reuses the environments §7.3 descriptor grammar with an
`argument` member (`path`, `contents`, or `name`) and, for `flag`, an
OPTIONAL `with` list of companion flags. Revision-1 channels:

- `claude_code` — `flag` `--mcp-config` with `argument: path`, `with:
  ["--strict-mcp-config"]` (both verified in 2.1.258 help). Under
  `--strict-mcp-config` the tool ignores every other MCP configuration,
  including servers recorded in the managed home's own `.claude.json`;
  this is intended — a managed home's MCP set is exactly the profile's.
- `codex_cli` — `flag` `-p` with `argument: name`, `name: "curator-mcp"`:
  the manager writes `<home>/curator-mcp.config.toml` whose only member is
  `mcp_servers`, and `-p <name>` layers `$CODEX_HOME/<name>.config.toml` on
  the base configuration (verified in 0.151.0 help). The layer name is
  fixed and reserved: `-p` is also the operator's profile flag, an
  operator `-p` after `--` names a second layer, and which of two `-p`
  occurrences wins is unverified (Open question 3).
- `opencode` — `variable` `OPENCODE_CONFIG` naming a manager-written
  configuration whose only member is `mcp`. opencode merges configuration
  in a documented order — remote, global, `OPENCODE_CONFIG`, project
  `opencode.json`, `.opencode/`, `OPENCODE_CONFIG_CONTENT`, managed — so a
  project-level entry with the same server name overrides the managed one;
  recorded, not prevented.
- `pi` — none (0.84.2 has no MCP channel); no file and no `mcp` section.

The launcher applies the channel under its own specification; resolving a
fragment applies nothing, and a managed home launched without the channel
carries no MCP configuration. Under Option A the launcher, `curator-run`,
is the single composer: it adds the fragment's `env_names` to the launch
plan's environment-name allowlist so that an `ax`-tracked child receives
the operator's values, exactly as a direct exec inherits them. Whether a
given tool passes its own environment through to a `stdio` server is a
per-adapter fact verified with the channel.

This is deliberately not a plugin runtime: MCP is the plugin standard, and
the missing pieces were declaration, materialization, and policy. Policy is
the manager §1 system configuration: an allowlist of MCP package canonical
source identities (§6.1 matching), lockable, bounding which declaration
packages a profile may resolve — `mcp_package_not_allowed` otherwise. The
allowlist is over packages, not launcher binaries, because a binary
allowlist bounds nothing: `npx`, `uvx`, `node`, or `sh` admit any program
through `args`. An organization allowlists the declaration packages it has
reviewed; an empty allowlist permits every network identity, as §6.1.

### 7. Profiles, installation, and the default profile

A profile is a root context package plus its lock plus the machine
overlays declared for it. `profile install <source> [--path <dir>]
[--range <range> | --tag <tag> | --revision <commit>]` names the root;
`--range` defaults to `latest`. Branch tracking is withdrawn for profile
roots: ranges replace it, and a repository with no `v*` tags installs only
by `--revision` (or by a non-version `--tag`). The profile name is the root
package name unless `--as <name>` is given; two installed profiles MUST NOT
share a name. `Profilefile.json`, per-profile directories, and the
profile-scoped `Skillfile.json` of Decision 0010 are withdrawn before any
implementation shipped them; a profile's skill set is the resolved
`requires.skills` of its closure plus any direct declarations the machine
adds through the existing global skill commands, which now write into the
profile's lock through the same resolution.

The builtin `default` profile of Decision 0010 Decision 8 remains: a
synthesized `local` root with no modules whose lock carries only the
migrated global skills.

### 8. Update, materialization, marker, and fragment

`profile update [<name> | --all]` re-resolves the root and overlays from
their declared ranges, fetches new candidates, audits every member that is
new to the lock in strict mode, and publishes the new lock and store
entries as one manager-home transaction; in-place scopes on that profile
re-materialize; managed homes are marked stale for explicit repair
(review M10). Exact `tag` and `revision` roots are reported as pinned and
do not move; a moved tag is a warning, or an error under strict-tag policy.

The generation header becomes `curator-root-context-v2`. Its lines, in
order: the type line; a `root:` line — `root: <name> <version> <pin>`; one
`member:` line per context member of the closure, with or without
applicable modules, in emitted order — `member: <name> <version> <pin>
weight <n>`, with ` overlay` appended for an overlay; a `precedence:` line
— `precedence: winner=<winner> placement=<placement>`; a `lock:` line —
`lock: sha256:<64 lowercase hex>`; and the fixed `generated:` and `notice:`
lines. `<pin>` keeps the revision-1 grammar: `commit <full-hex>` or `state
sha256:<hex>`. Skill and MCP members appear in the lock, not the header.
The chapter part becomes `## Context: <name> <version>` and is emitted for
context members with applicable modules only, so a pure umbrella
contributes a `member:` line and no chapter; the v2 replacement of the
`monolithic-composed-empty-chapter` vector exercises exactly that. The
environment marker records the root, the lock hash, the precedence
primitives, and the member list in place of the single profile pin and the
`composition` object; the launch fragment's `profile` object carries `name`
and `lock_sha256`, its `composition` member is withdrawn, its `precedence`
member carries both primitives, and it gains the `mcp` section of Decision
6 with the file path, the `env_names` union, and the channel descriptor.
The system-prompt output, the referenced form (grouped per package name in
place of profile name), the platform-collision rule, and every other byte
rule of environments §5 are unchanged apart from these lines.

### 9. Worked example: the companyA iOS umbrella

The umbrella manifest of Decision 1 is the root. `companyA-root-context-core`
is required twice — by the umbrella (`^3.0`) and by
`companyA-root-context-developers-core` (`^3.1`); the effective constraint
is `>=3.1.0 <4.0.0-0` and neither requirer declares an edge weight, so
the core keeps its manifest weight `0`. The core requires
`companyA-root-context-organizational-structure` (`^1.0`), which the root's
`weights` map sets to `10`. `companyA-root-context-developers-ios` also
requires `swiftui` `^4.2`; jointly with the umbrella's `^4` that is
`>=4.2.0 <5.0.0-0`. The machine declares one overlay, `personal`, from a
local directory at the default overlay weight `1000`. Under the default
policy the lock is (indented for reading; the lock hash is over the CCJ-1
bytes):

```json
{
  "schema_version": 1,
  "root": "companyA-root-context-ios-developer-umbrella",
  "members": [
    { "kind": "context", "name": "companyA-root-context-core", "source": "github.com/companyA/root-context-core", "version": "3.2.1", "commit": "1111111111111111111111111111111111111111", "weight": 0, "required_by": ["companyA-root-context-developers-core", "companyA-root-context-ios-developer-umbrella"], "overlay": false },
    { "kind": "context", "name": "companyA-root-context-developers-core", "source": "github.com/companyA/root-context-developers-core", "version": "1.6.0", "commit": "3333333333333333333333333333333333333333", "weight": 20, "required_by": ["companyA-root-context-ios-developer-umbrella"], "overlay": false },
    { "kind": "context", "name": "companyA-root-context-developers-figma", "source": "github.com/companyA/root-contexts", "path": "contexts/figma", "version": "1.1.0", "commit": "4444444444444444444444444444444444444444", "weight": 40, "required_by": ["companyA-root-context-ios-developer-umbrella"], "overlay": false },
    { "kind": "context", "name": "companyA-root-context-developers-ios", "source": "github.com/companyA/root-context-developers-ios", "version": "2.4.2", "commit": "5555555555555555555555555555555555555555", "weight": 60, "required_by": ["companyA-root-context-ios-developer-umbrella"], "overlay": false },
    { "kind": "context", "name": "companyA-root-context-ios-developer-umbrella", "source": "github.com/companyA/root-context-ios-developer-umbrella", "version": "2.3.0", "commit": "6666666666666666666666666666666666666666", "weight": 100, "required_by": [], "overlay": false },
    { "kind": "context", "name": "companyA-root-context-organizational-structure", "source": "github.com/companyA/root-context-organizational-structure", "version": "1.0.4", "commit": "2222222222222222222222222222222222222222", "weight": 10, "required_by": ["companyA-root-context-core"], "overlay": false },
    { "kind": "context", "name": "personal", "version": "0.3.0", "state_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "weight": 1000, "required_by": [], "overlay": true },
    { "kind": "mcp", "name": "figma-devmode", "source": "github.com/companyA/mcp-figma-devmode", "version": "1.2.0", "commit": "7777777777777777777777777777777777777777", "weight": 0, "required_by": ["companyA-root-context-ios-developer-umbrella"], "overlay": false },
    { "kind": "skill", "name": "pdf", "source": "github.com/relux-works/skill-pdf", "version": "1.2.5", "commit": "8888888888888888888888888888888888888888", "weight": 0, "required_by": ["companyA-root-context-ios-developer-umbrella"], "overlay": false },
    { "kind": "skill", "name": "swiftui", "source": "github.com/relux-works/skill-swiftui", "version": "4.3.0", "commit": "9999999999999999999999999999999999999999", "weight": 0, "required_by": ["companyA-root-context-developers-ios", "companyA-root-context-ios-developer-umbrella"], "overlay": false }
  ]
}
```

`profile use` or `env resolve` for `claude_code` materializes
`<home>/CLAUDE.md` with this header (default policy: ascending weight, the
heaviest last; every member has applicable modules, so each is followed by
its `## Context:` chapter):

```text
<!--
curator-root-context-v2
root: companyA-root-context-ios-developer-umbrella 2.3.0 commit 6666666666666666666666666666666666666666
member: companyA-root-context-core 3.2.1 commit 1111111111111111111111111111111111111111 weight 0
member: companyA-root-context-organizational-structure 1.0.4 commit 2222222222222222222222222222222222222222 weight 10
member: companyA-root-context-developers-core 1.6.0 commit 3333333333333333333333333333333333333333 weight 20
member: companyA-root-context-developers-figma 1.1.0 commit 4444444444444444444444444444444444444444 weight 40
member: companyA-root-context-developers-ios 2.4.2 commit 5555555555555555555555555555555555555555 weight 60
member: companyA-root-context-ios-developer-umbrella 2.3.0 commit 6666666666666666666666666666666666666666 weight 100
member: personal 0.3.0 state sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa weight 1000 overlay
precedence: winner=higher-weight placement=winner-last
lock: sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
generated: Curator Protocol environments revision 1 (https://github.com/relux-works/curator-spec)
notice: generated file; direct edits are unsupported and are detected as drift; update the source profile repository or its composed profiles instead
-->
```

`env resolve claude_code --format json` prints:

```json
{
  "fragment": "launch-env-fragment-v1",
  "environment": "claude_code",
  "profile": { "name": "companyA-root-context-ios-developer-umbrella", "lock_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb" },
  "precedence": { "winner": "higher-weight", "placement": "winner-last" },
  "env": { "CLAUDE_CONFIG_DIR": "<absolute managed-home path>" },
  "system_prompt": {
    "path": "<absolute path to .agent-context/system-prompt.md>",
    "channels": [
      { "kind": "flag", "semantics": "append", "flag": "--append-system-prompt-file" },
      { "kind": "flag", "semantics": "replace", "flag": "--system-prompt-file" }
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

The materialized `<home>/.agent-context/mcp/claude_code.json` is the CCJ-1
bytes of the tool's `mcpServers` object followed by exactly one LF — no
`env` member, because values never enter a materialized file:

```text
{"mcpServers":{"figma-devmode":{"args":["-y","figma-developer-mcp","--stdio"],"command":"npx","type":"stdio"}}}
```

`curator-run` then execs `claude --mcp-config <that path>
--strict-mcp-config` in the managed home, with `FIGMA_API_KEY` on the plan's
environment-name allowlist.

## Rejected alternatives

- **Reusing `SKILL.md` packages as context packages.** A skill is loaded on
  demand by the agent through its skills discovery; root context is always
  on. Overloading one package kind would make every skill a candidate root
  and every root a candidate skill. Separate kinds on one engine keep the
  loading semantics distinct and the machinery shared.
- **Range resolution without a lock.** Re-resolving at every operation would
  make materialization non-reproducible and drift undetectable; the lock is
  what keeps §7's one-name-one-commit invariant true after ranges are
  admitted.
- **Ranges in project `Skillfile.json` now.** Widening §4.4 to
  `ref.kind: "semver"` without a project lock is the alternative above by
  another door: a project declaration with `^4` would re-resolve on every
  operation. Ranges enter the project surface together with a project lock
  (Open question 6), not before.
- **Weights resolving version conflicts.** Letting a heavier package win an
  incompatible range hides a real constraint violation behind precedence;
  constraints stay hard, weights order only what has no mechanical
  resolution.
- **Transitive weight overrides.** Letting any ancestor rewrite any
  descendant's weight makes effective weights depend on the whole graph
  shape and impossible to reason about locally; direct requirer plus root
  final word is the smallest rule that still lets the assembler decide.
- **A hardcoded precedence direction.** Decision 0010 fixed
  `later-overrides-earlier`; organizations differ on whether the base or
  the refinement should prevail and on where models weigh material most.
  Two closed primitives cost nothing and remove the argument.
- **Independent overlay resolution.** Resolving overlays separately and
  reconciling duplicates by weight reintroduces two commits for one name.
- **Branch-tracking profile roots.** Decision 0010 let a directly installed
  profile track a branch. A branch is a moving pointer with no version,
  which is what ranges express better: `latest` tracks releases, a range
  bounds them, and a lock records what was taken. A repository that tags
  no versions is installed by `--revision`, and its author is told why.
- **A backtracking resolver.** Searching assignments across names finds
  solutions a greedy pass misses, at the cost of results that depend on
  search order and are hard to explain in a diagnostic. Highest-satisfying
  with downward re-selection is what a reader can predict from the
  manifests alone; a closure that needs the search is reported as the
  conflict it is.
- **A Curator plugin runtime for MCP servers.** The manager's no-execution
  boundary is the property everything else rests on; MCP already defines
  the runtime contract. Declaration, launch-channel materialization, and
  allowlist policy deliver installation without execution.
- **An MCP allowlist over launcher binaries.** `npx`, `uvx`, `node`, and
  `sh` are the commands real servers use, and each admits any program
  through `args`; allowlisting them bounds nothing. Package identities are
  what an organization actually reviews.
- **Writing MCP configuration into native homes in revision 1.** Those
  files are tool-owned mutable state (`.claude.json`) or operator-owned
  configuration; the launch channel avoids both and the in-place write
  returns with its own review, as Decision 0010 phased it.

## Compatibility impact

No change to the frozen core: §4.4 `dependencies.skills` and
`Skillfile.json` keep their exact forms, and version ranges appear only in
context-package `requires` and in the profile lock. Everything below is
inside the separately versioned agent-environments capability.

`protocol/environments.md` stays at revision 1 and is rewritten in place;
the generation-header type line bumps to `curator-root-context-v2` so the
retired and the replacement vector sets are unambiguous. Section by section
against the landed text — *rewritten* means the section's rules change,
*bytes change* means the rules stand and named sentences or identifiers
change, *unchanged* means not a byte:

| Section | Disposition | Why |
|---|---|---|
| §1 profiles and sources | rewritten | a profile is a root package plus lock plus overlays; the surface list gains MCP declarations; `git` carries `range`, `tag`, or `revision` (no `branch`); a `path` operand names a directory whose root is `agent-context.json`; `local` unchanged |
| §1.1 | bytes change | ref-form row reworded; `context_range_conflict`, `context_version_mismatch`, and the Decision 4 weight diagnostics join the table |
| §2 repository shape | rewritten | becomes the context-package shape: `agent-context.json`, `context/`, `CONTEXT.md`; `Profilefile.json` and per-profile directories withdrawn |
| §2.1 | rewritten | `profile_index_invalid` and `profile_root_invalid` withdrawn; `context_manifest_invalid` replaces `profile_context_manifest_invalid` |
| §3 manifest and modules | rewritten | the entry shape (`path`, `environments`, `class`), module byte rules, and applicability rule stand verbatim, but the object moves inline into `agent-context.json`, the `version: 1` member goes, and the section title and diagnostics rename |
| §3.1 | bytes change | diagnostic names follow §3 |
| §4 profile store | rewritten | per-package commit- or state-keyed entries; a profile's identity is the set its lock names |
| §5 materialization (body) | rewritten | pure function of (lock, precedence policy, environment, form); part sequence is one chapter per context member with applicable modules in weight order; chapter part bytes `## Context: <name> <version>`; platform-collision and part-joining rules unchanged |
| §5.1 header | rewritten | the `curator-root-context-v2` grammar of Decision 8 |
| §5.2 monolithic | unchanged | — |
| §5.3 referenced | bytes change | `<profile-name>` becomes the package name in the layout and reference line; the opencode `instructions` rule stands |
| §5.4 zero modules | bytes change | "the header followed by the empty chapters" becomes the header alone — chapters exist only for members with applicable modules |
| §5.5 system prompt | bytes change | "of every profile in chain order" becomes "of every context member in emitted order"; the `.agent-context/mcp/` sibling is introduced by the new §5.8 |
| §5.6 hash binding | bytes change | the tuple follows §5; the MCP file joins the managed-home surface set |
| §5.7 | unchanged | — |
| §5.8 MCP launch-channel output (new) | new | the per-adapter file, its bytes, and its managed-home-only rule (Decision 6) |
| §6 composition | rewritten | overlays are closure members with weights; the precedence direction becomes the two primitives; the skill-union paragraph is replaced by joint resolution, so `environment_composition_skill_divergence` is withdrawn (a divergence is now a conflict or a unification) |
| §6.1 | rewritten | follows §6 |
| §7 registry (body), §7.1, §7.2 | unchanged | — |
| §7.3 system-prompt channels | bytes change | the descriptor grammar gains `argument` (`path`, `contents`, `name`) and `with`; the system-prompt rows stand |
| §7.4, §7.5, §7.6, §7.7 | unchanged | — |
| §7.8 MCP launch channels (new) | new | the four adapter rows of Decision 6 |
| §8.1 modes | bytes change | "the same store entry" becomes "the same lock's store entries" |
| §8.2 marker | rewritten | `profile` records root, kind, and lock hash; `composition` withdrawn in favor of `members` and `precedence` (both primitives); the `mcp` surface entry |
| §8.3, §8.4, §8.5 | unchanged | — |
| §9.1 installation | rewritten | one root per install; `--range`/`--tag`/`--revision`; resolution, lock, and audit of every member; the detector scope becomes context modules, `agent-context.json`, `agent-mcp.json` (`args` and `url` included), and `CONTEXT.md`; `--use` takes no name |
| §9.2, §9.3 | unchanged | — |
| §9.4 skills and migration | rewritten | the profile skill set is the lock's skills; direct machine declarations write into the lock; `default` keeps its `local` kind with a lock of migrated skills |
| §9.5 onboarding | unchanged | — |
| §9.6 import | rewritten | reassembly emits `agent-context.json` (version `1.0.0`, one module per adapter as before) with `requires.skills` pinned by `revision`; detection, classification, consent, and normalization stand |
| §9.7 | bytes change | `profile_index_ambiguous` withdrawn; the ref-flag row reworded |
| §10.1 `env resolve` | bytes change | the pure-function tuple follows §5; repair semantics unchanged here (review M10 is separate) |
| §10.2 fragment | rewritten | `profile` carries `lock_sha256`; `composition` withdrawn; `precedence` becomes an object; the `mcp` section; the identifier `launch-env-fragment-v1` is kept, its schema rewritten in place |
| §10.3 boundary | bytes change | one paragraph: `env_names` never enter the fragment `env` and reach a plan only through the launcher's allowlist, bounded by the reserved set and the lockable passable-names list |
| §10.4 | unchanged | — |
| §11, §11.1 | unchanged | — |
| §12 status and GC | bytes change | declared ref becomes the declared requirement; effective pin becomes the lock hash; GC live roots become every store entry a lock names |
| §13 conformance | rewritten | the surface list of the new schemas and vectors |
| manager §12.1 registry | bytes change | the MCP channel rows and the reserved codex layer name |
| manager §12.2 modes and marker | bytes change | marker contents follow environments §8.2 |
| manager §12.3 lifecycle | rewritten | install grammar and the single-root rule; `profile update`; skill scope writes into the lock |
| manager §12.4 | unchanged | — |
| manager §12.5 `env resolve` | bytes change | the tuple and the `mcp` section |
| manager §12.6 audit | bytes change | the detector scope of §9.1 |
| manager §12.7 status and GC | bytes change | follows environments §12 |
| `cli/curator.md` profile rows | bytes change | `profile install` grammar, `profile list` columns, the `profile update` row |
| `schemas/v1/profilefile-v1.schema.json`, `context-manifest-v1.schema.json` and `schema-cases/profilefile-v1`, `schema-cases/context-manifest-v1` | withdrawn | replaced by `agent-context-v1`, `agent-mcp-v1`, `context-lock-v1` and their cases |
| `schemas/v1/agent-environment-marker-v1.schema.json`, `launch-env-fragment-v1.schema.json` | rewritten in place | same identifiers; no implementation claims them |
| the nine `conformance/v1/expected/environments/*` sets (`monolithic-claude-code`, `monolithic-codex-selector-excluded`, `monolithic-composed-empty-chapter`, `monolithic-zero-modules`, `monolithic-zero-modules-composed`, `referenced-claude-code-composed`, `referenced-opencode`, `referenced-opencode-zero-modules`, `system-prompt-composed`) with their `vectors/environments.json` cases and `manifest.json` entries | withdrawn | regenerated under the v2 type line, with the empty-chapter case re-cut as the no-chapter case and new sets for weight ordering under both primitives and for MCP bytes per adapter |

New conformance surfaces: version and range parsing, resolution (including
conflict, downward re-selection, and prerelease cases), lock
canonicalization and hashing, weight ordering under both precedence
primitives, and MCP materialization bytes per adapter. `Profilefile.json`
and `context.json` never entered the §1.1 identifier list or
`COMPATIBILITY.md`; what leaves is exactly the two schemas, their
schema-cases, and the nine vector sets above.

## Security impact

- Every package kind passes the same gates: canonical source identity,
  allowlist, snapshot validation, always-strict audit, `context-secret-
  material` (and its Decision 0010 review resolutions) — now over MCP
  `args` and `url` as well — and the `context-system-module-present`
  surfacing class.
- Range resolution reads tags; a tag can move. The lock pins commits, so
  movement is detected at `profile update` under the unchanged strict-tag
  policy, never at use time.
- Weights, precedence primitives, and overlay declarations widen nothing:
  they order bytes the audit already admitted. A root's `weights` map is
  the one place assembly intent overrides a dependency's self-declaration,
  and it is repository content under audit.
- MCP declarations never carry values, never execute, and never reach a
  native home in revision 1. `command` is a bare name on `PATH`, `url` is
  `https` without userinfo, and the package allowlist is lockable by
  system configuration. `env_names` are the one place package bytes name
  something about a launch: they select which operator variables the
  launcher may pass through, never their values, never a reserved name,
  and only within the lockable passable-names bound. The launcher's
  application of the channel is the launcher specification's surface.
- The lock is a record, not a signature (§10 discipline).

## Consequences

- Organizations model context as a versioned package graph with the same
  tooling discipline as skills; individuals keep overlays in a personal
  repository or a local directory.
- The Decision 0010 profile-repository shape is withdrawn before
  implementation. The pre-implementation review's sixteen MUST items apply,
  with M9's detector scope re-targeted to `agent-context.json`,
  `agent-mcp.json`, and `CONTEXT.md`, and M12's knob list grown by the
  overlay default weight, the precedence primitives, per-overlay weights,
  the MCP package allowlist, and the passable-names allowlist.
- The reference implementation gains version parsing and range resolution
  in the closure package, a lock object, two manifest kinds, and the MCP
  materializer; the launcher specification gains the `mcp` channel and the
  `env_names` pass-through.
- Package discovery — an organization index of its context, skill, and MCP
  packages — is not addressed here; the registry protocol is the natural
  home and is left to its own decision.

## Open questions

1. **Machine default overlay weight.** A fixed large constant (recommended:
   `1000`) or "one above the heaviest root member"? Recommendation: the
   constant — predictable, and `weights` on the root can still climb above
   it deliberately.
2. **Prerelease admission policy.** Whether an organization can allow
   `latest` to select prereleases machine-wide (a `prerelease: allow`
   switch) or whether prereleases stay range-explicit only. Recommendation:
   range-explicit only in revision 1; a machine switch is a later, lockable
   addition.
3. **Codex profile-layer channel.** `-p <name>` layering
   `$CODEX_HOME/<name>.config.toml` is documented in codex 0.151.0 help;
   that a layer file with only `mcp_servers` composes cleanly over the base
   configuration, and which occurrence wins when the operator passes a
   second `-p`, need the pinned-release verification the environments
   §7.3 discipline already requires.
4. **Lockability surface.** Which of root allowlist, overlay maximum
   weight, precedence primitives, MCP package allowlist, and passable
   `env_names` become manager §1 `locked` keys in revision 1 — the
   review's M15.
5. **Package discovery.** Whether the registry protocol grows a package
   index in the same revision or after.
6. **Project lock.** Before a project `Skillfile.json` may carry ranges, a
   separate decision must fix the lock's identifier (joining §1.1), its
   location, its relationship to the install marker, and its interaction
   with `Skillfile.dev.json`. Until then §4.4 stands and ranges live only
   in context packages and the profile lock.
