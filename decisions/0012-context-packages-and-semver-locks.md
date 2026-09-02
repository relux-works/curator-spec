# Decision 0012: context packages, semver-locked closures, and launch-channel MCP

## Status

Proposed 2026-09-02. Draft for review; nothing here is normative yet.
Acceptance authorizes rewriting the affected sections of
`protocol/environments.md` (revision 1 → revision 2), the additive core
changes named in Compatibility impact, the new schemas and vectors, and the
manager-profile and CLI text, as separately tracked work. It supersedes the
profile-repository shape of Decision 0010 (Decisions 2, 5-composition, and
8) and leaves every other Decision 0010 rule in force. Section references
without a document name refer to `protocol/core.md`; "environments §N" names
`protocol/environments.md` revision 1.

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
commits, and the lock is the identity.

The review also settled two adjacent facts this decision relies on: the
execution plane composes a launch through a caller-supplied plan into `ax`
(Decision 0011, Option A), and materialization into managed homes plus an
inert file plus a launcher-applied channel is the pattern that lets Curator
carry a surface without executing anything or writing into a tool's mutable
state. MCP configuration rides that pattern.

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
  requirer uses for it. `version` is a strict semantic version (Decision 2)
  and MUST equal the version of the tag the package was resolved from.
- `weight` is an integer, default `0`, the package's own default precedence
  weight (Decision 4). `weights` is OPTIONAL and admitted only in a root
  package (Decision 4).
- `context` carries the module manifest of environments §3 unchanged
  (`path`, `environments` selector, `class` root|system), moved inline;
  `context/` and its byte rules are unchanged. `context` MAY be absent: a
  package with no modules of its own is a pure umbrella.
- `requires` names other context packages, skills, and MCP declaration
  packages. Every entry carries a canonical git source (§6.1), an OPTIONAL
  `path` naming a directory within the snapshot (the skill `source`
  convention), and exactly one of `range` (Decision 2), `tag`, or
  `revision` (§4.4 exact forms). A requirement MAY carry `weight` to
  override the required package's own default (Decision 4).
- `CONTEXT.md` at the package root is informative and never materialized.
  Files not named by the manifest are inert and participate only in
  snapshot identity and audit.

There is no umbrella kind. Any context package with `requires.contexts` is
an umbrella; any context package — umbrella or not — installs as a root. A
role umbrella whose modules are empty is a valid, common shape.

### 2. Versions, ranges, and resolution

Version tags are strict Semantic Versioning 2.0 with a mandatory `v`
prefix: `v<major>.<minor>.<patch>[-<prerelease>][+<build>]`, under the §6.3
tag grammar. Build metadata is ignored for ordering and equality. A tag that
does not parse is not a version candidate and is silently outside every
range; it remains addressable by the exact `tag` form.

The range grammar is closed and npm-shaped: an exact version (`1.2.3`,
meaning `=1.2.3`); caret `^1.2.3`; tilde `~1.2.3`; comparator sets of
`>=`, `>`, `<=`, `<`, `=` joined by whitespace (conjunction); alternatives
joined by `||` (disjunction); the wildcards `*` and `x` in a component; and
the spelling `latest`, equivalent to `*`. `*`, `x`, and `latest` select
the highest **stable** version — a prerelease version satisfies a range
only when the range names a prerelease on the same `major.minor.patch`,
the npm rule that keeps `latest` from landing on `v2.0.0-rc.1`.

Resolution is the §7 closure with one change to its admission rule. For
each package name across the whole closure — root, transitive
requirements, and machine overlays (Decision 5) — every requirement MUST
agree on the canonical source identity (unchanged), and the effective
constraint is the intersection of every declared range with every exact
`tag`/`revision` form treated as a single-version range. The manager lists
the source's version tags, selects the **highest version satisfying the
effective constraint**, and peels it to a commit under §6.3. An empty
intersection is `context_range_conflict`, naming every requirer and its
range. Ties are impossible (versions are a total order after discarding
build metadata). After resolution the §7 invariant holds unchanged: one
name, one commit.

Skills gain the same form: core §4.4 `dependencies.skills` and the
`Skillfile.json` direct declaration admit `ref.kind: "semver"` with a
`range`, resolved by exactly the rule above — the branch-and-range
prohibition of §4.4 is narrowed to branches. Skill requirements from
context packages and from a profile's own declarations resolve jointly with
every other skill requirement in the closure.

### 3. The lock is the identity

The result of resolution is the profile **lock**: a strict schema-1 object
listing every closure member — contexts, skills, and MCP declarations —
with its name, kind, canonical source identity, resolved version, full
commit, effective weight (Decision 4), and requirer chain, in a sorted
canonical order. The lock is machine state below the manager home, never
repository content. Its CCJ-1 hash (`registry.md` §1) is the **lock hash**,
and the lock hash is the profile's effective pin everywhere Decision 0010
used a commit: the generation header, the environment marker, the launch
fragment, `profile list`, and the `ax` extension keys.

Store entries stay commit-keyed per package — the runtime-store pattern —
so two profiles sharing a package share its entry. A profile's store
identity is the set of entries its lock names.

`profile install` resolves and writes the lock; `profile update`
re-resolves (Decision 8) and writes a new lock only when the new closure
passes the always-strict audit of environments §9.1 in full — a blocking
finding on any new member leaves the old lock in place and is reported.
Nothing re-resolves implicitly: `profile use`, `profile sync`, `env
resolve`, and status read the lock they find.

### 4. Weights and precedence

Every closure member has an **effective weight**: its manifest `weight`,
overridden by the `weight` its **direct requirer** declares on the
requirement edge, overridden by the root package's `weights` map — the
root has the final word. A `weights` entry naming a package outside the
closure is `context_weight_unknown`; a non-root manifest carrying `weights`
is rejected at snapshot validation. Machine overlays (Decision 5) carry the
weight machine configuration assigns them.

Weights order material and decide mechanical collisions; they never merge
instruction text. Machine configuration declares the **precedence policy**
as two independent primitives, each closed:

- `winner`: `higher-weight` (default) or `lower-weight` — which side of a
  weight comparison prevails;
- `placement`: `winner-last` (default) or `winner-first` — whether the
  prevailing material is emitted last or first in the materialized root
  context.

The default pair reproduces Decision 0010's `later-overrides-earlier`
reading; either primitive may be changed without the other. Materialization
emits one chapter per closure member with modules, ordered by effective
weight under `placement`, ties broken by the §7 topological order and then
by name; a member's own modules stay contiguous in manifest order. The
generation header states both primitives in words and lists every member
with its weight, so a reader and the agent see the hierarchy the assembler
intended. Mechanical collisions — two members declaring the same MCP server
name with differing declarations — are resolved for the member that
`winner` favors and reported. Version constraints are never a weight
question: an empty range intersection fails regardless of weights.

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
    "required_in": ["claude_code", "codex_cli", "opencode"]
  }
}
```

`transport` is exactly `stdio` or `http`; `stdio` carries `command` (a bare
executable name or an absolute path) and `args`; `http` carries `url`.
`env_names` lists environment-variable **names** the server expects at run
time — values never appear in any package, lock, marker, fragment, or
materialized file; the operator's session environment supplies them. The
manager never executes, installs, updates, or launches a server. It
verifies, read-only, that a `stdio` command resolves on the operator's
`PATH` and warns when it does not — the manager §6 discipline — and it
audits the package like any other.

Materialization is a **launch channel**, the environments §5.5 pattern.
The resolved MCP set of a profile materializes as one inert, hashed,
marker-recorded file per adapter format below `<home>/.agent-context/mcp/`
in a managed home only — never into a native in-place home, whose MCP
configuration lives in tool-owned mutable state — and the launch fragment
gains an `mcp` section naming the file and the adapter's channel
descriptor. Revision-1 channels: `claude_code` — `flag`: `--mcp-config
<path>` together with `--strict-mcp-config`; `codex_cli` — `flag`: `-p
<name>` selecting a manager-written `<home>/<name>.config.toml` layer whose
only member is `mcp_servers`; `opencode` — `variable`: `OPENCODE_CONFIG`
naming a manager-written configuration whose only member is `mcp`; `pi` —
none. The launcher applies the channel under its own specification;
resolving a fragment applies nothing, and a managed home launched without
the channel carries no MCP configuration.

This is deliberately not a plugin runtime: MCP is the plugin standard, and
the missing pieces were declaration, materialization, and policy. Policy is
the manager §1 system configuration: an allowlist of `stdio` commands and
`http` hosts, lockable, so an organization can bound what its profiles may
declare.

### 7. Profiles, installation, and the default profile

A profile is a root context package plus its lock plus the machine
overlays declared for it. `profile install <source> [--path <dir>]
[--range <range> | --tag <tag> | --revision <commit>]` names the root;
`--range` defaults to `latest`. The profile name is the root package name
unless `--as <name>` is given; two installed profiles MUST NOT share a
name. `Profilefile.json`, per-profile directories, and the profile-scoped
`Skillfile.json` of Decision 0010 are withdrawn before any implementation
shipped them; a profile's skill set is the resolved `requires.skills` of
its closure plus any direct declarations the machine adds through the
existing global skill commands, which now write into the profile's lock
through the same resolution.

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

The generation header becomes `curator-root-context-v2`: a `root:` line
(name, version, commit), one `member:` line per closure member with modules
in emitted order (name, version, commit, effective weight, `overlay` where
applicable), a `precedence:` line stating both primitives, a `lock:` line
with the lock hash, and the fixed `generated:` and `notice:` lines; the
chapter part becomes `## Context: <name> <version>`. The environment marker
records the root, the lock hash, and the member list in place of the single
profile pin; the launch fragment's `profile` object carries `name` and
`lock_sha256`; the `ax` extension key `works.relux.curator.profile-pin`
carries the lock hash. The system-prompt output, the referenced form, the
platform-collision rule, and every other byte rule of environments §5 are
unchanged apart from these lines.

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
- **A Curator plugin runtime for MCP servers.** The manager's no-execution
  boundary is the property everything else rests on; MCP already defines
  the runtime contract. Declaration, launch-channel materialization, and
  allowlist policy deliver installation without execution.
- **Writing MCP configuration into native homes in revision 1.** Those
  files are tool-owned mutable state (`.claude.json`) or operator-owned
  configuration; the launch channel avoids both and the in-place write
  returns with its own review, as Decision 0010 phased it.

## Compatibility impact

Additive to the frozen core except for one widening: core §4.4
`dependencies.skills` and `Skillfile.json` admit `ref.kind: "semver"` with
`range`, delivered as skill-manifest schema 9 and Skillfile schema 2 so that
readers of earlier schemas reject the form explicitly (the downward gate of
§4). New schemas under `schemas/v1/`: `agent-context-v1`, `agent-mcp-v1`,
`context-lock-v1`; the environments schemas for the marker and the fragment
revise for the lock hash and the `mcp` section. `protocol/environments.md`
moves to revision 2: §2 (repository shape), §6 (composition), §9.1
(installation), and §9.4 (skills) are rewritten to this decision; §5.1 and
the chapter part change bytes under the `curator-root-context-v2` type
line; every other section stands. Revision 1 was claimed by no
implementation and carried by no tag, so the rewrite is in place, and the
type-line bump keeps the two vector sets unambiguous. New conformance
surfaces: version and range parsing, resolution (including conflict and
prerelease cases), lock canonicalization and hashing, weight ordering under
both precedence primitives, and MCP materialization bytes per adapter.
`Profilefile.json` and `context.json` leave the identifier list before they
enter any wire.

## Security impact

- Every package kind passes the same gates: canonical source identity,
  allowlist, snapshot validation, always-strict audit, `context-secret-
  material` (and its Decision 0010 review resolutions), and the
  `context-system-module-present` surfacing class.
- Range resolution reads tags; a tag can move. The lock pins commits, so
  movement is detected at `profile update` under the unchanged strict-tag
  policy, never at use time.
- Weights, precedence primitives, and overlay declarations widen nothing:
  they order bytes the audit already admitted. A root's `weights` map is
  the one place assembly intent overrides a dependency's self-declaration,
  and it is repository content under audit.
- MCP declarations never carry values, never execute, and never reach a
  native home in revision 1; the command/host allowlist is lockable by
  system configuration. The launcher's application of the channel is the
  launcher specification's surface.
- The lock is a record, not a signature (core §10 discipline).

## Consequences

- Organizations model context as a versioned package graph with the same
  tooling discipline as skills; individuals keep overlays in a personal
  repository or a local directory.
- The Decision 0010 profile-repository shape is withdrawn before
  implementation; the pre-implementation review's sixteen MUST items apply
  unchanged, since they concern the edges of the process, not the package
  shape.
- The reference implementation gains version parsing and range resolution
  in the closure package, a lock object, two manifest kinds, and the MCP
  materializer; the launcher specification gains the `mcp` channel.
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
   range-explicit only in revision 2; a machine switch is a later, lockable
   addition.
3. **Codex profile-layer channel.** `-p <name>` layering
   `$CODEX_HOME/<name>.config.toml` is documented in codex 0.151.0 help; that
   a layer file with only `mcp_servers` composes cleanly over the base
   configuration needs the pinned-release verification the environments
   §7.3 discipline already requires.
4. **Lockability surface.** Which of root allowlist, overlay maximum
   weight, precedence primitives, and MCP allowlist become manager §1
   `locked` keys in revision 2 — the review's M15.
5. **Package discovery.** Whether the registry protocol grows a package
   index in the same revision or after.
