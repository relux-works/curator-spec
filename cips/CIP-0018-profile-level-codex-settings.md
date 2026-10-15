# CIP-0018: Profile-level Codex settings as launch overrides

- **Status:** Accepted
- **Owner:** Curator maintainers; decision: operator
- **Created:** 2026-10-15
- **Related:** owner decision 2026-10-15 (D9, D13); owner decision 2026-10-16 (D14); CIP-0015 machine credential-store selection
- **Affects:** environments §§2, 6, 7.3, 7.4, 10.2, 10.3, 12.1; curator; curator-agent-launcher; skill-agents-management; skill-project-management; swarma-dispatcher

- **Decision:** owner decision 2026-10-15 (D9, D13), corrected by owner decision 2026-10-16 (D14); profile inheritance and typed launch overrides retained; credential-store selection is machine-owned.
- **Normative text:** [Profile Codex settings §§1–7](../protocol/profile-codex-settings.md), [environments §§2, 6, 7.4, 8.2, 10.2–10.3, 12.1](../protocol/environments.md), [member schemas](../schemas/profile-codex-settings-v1/README.md), [cases and vectors](../conformance/profile-codex-settings-v1/README.md), [Decision 0025](../decisions/0025-profile-codex-settings.md).

## Summary

A profile can declare a bounded set of Codex settings in its context-package
manifest, inherited through the same closure and weights as its overlays.
Curator resolves the values and emits typed launch data; the launcher applies
that data as stable `-c key=value` argv pairs on every managed Codex launch.
Neither resolution nor launch rewrites the native or managed `config.toml`:
that file remains a one-time seed followed by tool-owned state.
Owner decision 2026-10-16 (D14) removes `cli_auth_credentials_store` from the
package vocabulary, which admits no key in this revision. Curator fills that
launch override only from CIP-0015's user-owned machine selector
`credential_store.<profile>.<env-id>` (default `native`).

## Motivation and user stories

An operator needs a machine-owned credential-store choice even when a seeded
home has an older configuration. Owner decision 2026-10-16 (D14) assigns that
choice exclusively to the machine selector: packages must not decide that
tokens go to disk. A hosted session needs the same machine-selected override
as an interactive launch, while retaining its own sandbox, approvals and tool
isolation. Profile inheritance remains available for future reviewed keys.

Owner decision 2026-10-15 (D13) requires profile-level inheritance and launch
overrides. Owner decision 2026-10-15 (D9) assigns the per-profile × environment
credential-store decision to Curator and its application to the launcher.
Owner decision 2026-10-15 (D1) leaves home preparation and verification with
Curator; a launcher must not rediscover settings by reading package files.

This proposal defines a small initial vocabulary rather than arbitrary Codex
configuration access. New settings require a reviewed vocabulary extension.
Login preparation, snapshot production and remote transport remain the work
of their companion proposals; this CIP specifies the settings those paths
must preserve and consume.

## Current state

### Sources and confidence

The following references are to inspected, immutable source baselines:

- **S:** curator-spec `d34d8a6`, [environments](../protocol/environments.md).
- **C:** curator `00fec196`, paths and line numbers below.
- **P:** skill-project-management `b057ef468`, paths and line numbers below.
- **A:** skill-agents-management **v0.5.62**, the dependency source vendored
  in P's `tools/board-cli/vendor/` tree. P `tools/board-cli/go.mod` and
  `tools/board-cli/vendor/modules.txt` pin that exact dependency version.
- **L:** curator-agent-launcher `9ad2f016`, `SPEC.md` **0.5.1-draft**.

A-prefixed paths below are relative to that vendored repository root, not a
claim that an older standalone checkout has the same implementation.
Code inspection establishes existing code paths, not new live probe results.
The measured Codex facts cited from S retain its **Codex 0.153.2** version.
No independent credential-storage or upstream merge probe was run for this CIP.

S §10.3 says a profile chooses context, never how a process is launched,
and forbids profile-selected environment variables. Adoption deliberately
narrows the first boundary only for reviewed package keys, admitting none in
this revision under D14; the variable boundary remains unchanged. The machine
credential-store selector uses a separate closed launch vocabulary.

### Profile composition and closed channels

S §2 defines strict schema-1 `agent-context.json` with `context`, requirements
and weight metadata; it defines no profile Codex settings member. S §6 lets
machine-declared overlays join the root's jointly resolved closure. Effective
weights derive from manifest defaults, requirement edges, the root's weights
map and finally the machine overlay assignment, in that order.

Today S §6 explicitly says weights order chapters and nothing else. Its
`winner` primitive selects higher or lower weight; `placement` orders emitted
chapters. Same-key setting resolution is therefore a proposed extension,
not an already implemented interpretation of composition.

S §7.3 defines closed descriptor kinds `flag`, `config-key`, `variable` and
`file`. `with` is an optional companion-flags list on `flag`, not a fifth
kind. A `config-key` descriptor supplies a key for a materialized prompt
path; it is not a general map of configuration values. C
`internal/envregistry/envregistry.go:101-128` defines those shapes; its
Codex row at `:269-286` selects `CODEX_HOME`, replacement through
`model_instructions_file`, `-p curator-mcp` and the `config.toml` seed.

C `internal/envfragment/envfragment.go:52-70` defines the fragment members
and version selection; `:73-103` renders channel descriptors and `:106-138`
renders the object. None of those members carries arbitrary scalar settings.
Its env/shell rendering at `:157-214` emits only environment variables, so
sourcing that output cannot apply configuration channels.

### Seeds, credentials and MCP

S §7.4 copies the Codex seed once: revision A copies the native `config.toml`
whole, warning about inherited native MCP servers; revision B removes the
`mcp_servers` table and descendants on the initial copy. Subsequent native
changes do not propagate, and repair does not rewrite tool-owned seed bytes.
C `internal/envregistry/envregistry.go:28-37` selects seed revision B.
Existing revision-A homes retain their bytes and warnings (S §7.4).

S §7.8 layers `-p curator-mcp` over the base in both seed revisions. It
records on Codex 0.153.2 that the profile flag is single-valued and a missing
layer file is silently ignored, requiring a pre-exec file check. This layer
merges with the base; it does not remove native servers in an old seed.

S §7.4 defines sharing from the **native home's** effective
`cli_auth_credentials_store`: absent means `file`; `file`, `keyring` and
`auto` are the verified selectors. A divergent managed `config.toml` changes
nothing about that sharing decision. Its existing isolation gate admits
Codex only under native `file`, refusing `keyring`/`auto`. These are current
rules to amend explicitly, not assumptions that a launch override already
changes provisioning or links.

Scalar `-c` precedence over a conflicting seed and the effect of this key on
login, app-server and token refresh remain unverified on Codex 0.153.2.
Native configuration support does not establish those launch behaviors.

### The launcher and the session host

A `pkg/agentic/systems/codex/context.go:137-192` validates the Curator Codex
channels and TOML-encodes the system-prompt path. A
`pkg/agentic/systems/codex/args.go:237-249` appends it as a `-c` pair in the
shared argument builder. `context.go:194-258` separately encodes MCP context
values; that surface is not permission to inject arbitrary profile keys.
L §§4.1, 4.3 and 4.5 describe fragment consumption, plan construction and
channel delivery; its closed fragment contract needs an explicit amendment.

P `tools/board-cli/internal/sessionmanager/codex_host.go:1589-1602` renders
and writes a private session `config.toml`. At `:1619-1643` it explains why
MCP isolation is written into that private document: Codex merges `-c` table
overrides with the loaded tables rather than replacing the whole table.
At `:1644-1687` it mirrors selected source keys, writes project trust and
applies ordinary tool policy or builder isolation last.

Consequently `-c mcp_servers={}` cannot be treated as clearing inherited
servers. This is the merge behavior documented by the inspected host source;
qualification against each supported Codex release remains an implementation
test, rather than a new measurement claimed here. The private policy file
is session-owned; it is distinct from either Curator's managed seed or the
operator's native file. D13 does not transfer profile-settings ownership to
that host.

## Design

### Options considered

Each table is one design question. All fields and diagnostics below are
proposed contracts unless explicitly identified above as current state.

**Where settings live and which keys are admitted**

| Option | Mechanism | Pros | Cons | Security |
| --- | --- | --- | --- | --- |
| A: closed manifest vocabulary | Add typed `codex_settings` to each context-package manifest; allow reviewed exact keys only | Inheritance uses existing package identity; bounded audit | Each added key needs a spec revision | Unknown and policy keys fail closed |
| B: manifest denylist | Accept most Codex keys except reserved prefixes | Broad customization | Every upstream key can change the attack surface | New aliases or tables can bypass the denylist |
| C: separate settings file | Manifest points at a TOML file with unrestricted contents | Familiar native format | Another parser, path and digest surface; ambiguous ownership | Tables, includes and secrets require broad filtering |

Recommend **A**, with no admitted package key in this revision under D14.
Credential-store, credential-source and account keys are never admissible.
Other keys need a reviewed typed vocabulary extension. D9's machine selector
uses the typed launch transport without becoming a package contribution.

**How inherited values conflict**

| Option | Mechanism | Pros | Cons | Security |
| --- | --- | --- | --- | --- |
| A: section 6 weights | Select one scalar using effective weights and `winner`; reject unequal ties | Matches operator composition controls | Requires an explicit extension to section 6 | No traversal-order tie breaker or hidden override |
| B: root always wins | Ignore dependency weights for settings | Simple mental model | Machine overlays cannot refine by the same policy | Root publisher can defeat machine refinements |
| C: first/last traversal wins | Use topological emission order | Reuses an existing sequence | Unrelated graph edits change winners | Order manipulation silently changes settings |

Recommend **A**; `placement` has no role in scalar value selection.

**How values reach Codex**

| Option | Mechanism | Pros | Cons | Security |
| --- | --- | --- | --- | --- |
| A: typed fragment member | New version carries resolved `codex_settings`; plugin emits `-c` | Values remain data; existing prompt channel stays unchanged | Requires coordinated strict-reader updates | Independent validation at resolve and plan boundaries |
| B: overload config-key | Add arbitrary `value` to current channel descriptors | Reuses a kind name | Breaks path-based semantics and every closed reader | Blurs trusted adapter keys and publisher-controlled values |
| C: rewrite the seed | Merge values into managed `config.toml` at resolve | Old launchers would see them | Contradicts D13 and tool-owned state | Repair can overwrite user/tool settings |

Recommend **A**. Reuse the plugin's TOML scalar encoder and argv construction
path internally, not the external `system_prompt` descriptor grammar.

**How host policy interacts**

| Option | Mechanism | Pros | Cons | Security |
| --- | --- | --- | --- | --- |
| A: disjoint keys, refuse collisions | Profile vocabulary excludes host policy; validate all launch layers before exec | Host remains authoritative; no reliance on argv ordering | Unsupported collisions stop a launch | Cannot weaken a policy via later overrides |
| B: append host overrides last | Allow arbitrary profile keys, then repeat host scalars | Convenient for ordinary scalars | Tables merge; aliases and resume paths complicate enforcement | Cannot attest exclusive MCP isolation from ordering |
| C: reject every hosted setting | Hosted sessions discard or refuse the whole feature | Minimal host change | Violates D9/D13 hosted delivery intent | Avoids collisions by removing the capability |

Recommend **A**. Host tool policy wins by ownership, not by hoping that a
last `-c` repairs an already unsafe table merge.

### Recommendation

#### Package member and validation

Add OPTIONAL `codex_settings` at the top level of `agent-context.json`.
It is a closed object with no admitted package keys in this revision. For example:

```json
{
  "schema_version": 1,
  "name": "example-profile",
  "version": "1.0.0",
  "codex_settings": {}
}
```

This is a proposed extension to S §2's strict schema, requiring coordinated
reader adoption; it is not valid input to the unamended current schema.
The member may occur in the root, required context packages and ordinary
machine overlay packages. Skill packages and MCP declarations cannot carry
it as an alternative settings source. A package with no context modules may
still contribute settings. A path overlay receives no extra configuration
powers by being machine-selected.

The initial package allowlist is empty under D14. New keys require a reviewed
typed vocabulary extension; credential-store, credential-source and account
keys, including `cli_auth_credentials_store`, are never admissible here.
Declaring that key with either `file` or `keyring`, or declaring any unknown
key, produces `context_manifest_invalid` before resolution and no launch data.

In the launch transport only, `keyring` is the Codex spelling for the OS
credential store, including the Keychain where applicable. CIP-0015's machine
selector maps `file` to `file`, qualified `keychain` to `keyring`, and `native`
to no override. Native `auto` remains a compatibility inspection value;
no new storage selector or Codex default is inferred by this CIP.

Reject null, booleans, numbers, arrays, objects and TOML-source strings in
place of the empty package object. Reject duplicate JSON keys before decoding to a
map, unknown manifest fields, unknown setting names, dotted/quoted aliases,
invalid UTF-8 and control characters in names. There is no interpolation,
include, executable expression, deletion marker or secret value. An absent
or empty object contributes nothing; neither clears a lower-weight value.

Validate every contribution before precedence, including values that would
lose. A high-weight valid declaration cannot hide a hostile lower-weight
one. Invalid input emits no usable fragment and makes launch fail closed.
Adoption names the diagnostics in the linked normative text; this does not
claim that existing implementations emit them.

Never admit `sandbox_mode`, `approval_policy`, permission profiles,
`sandbox_*`, `permissions`, `default_permissions`, `mcp_servers`, `model`,
`model_provider`, `model_providers`, API endpoints/keys, project trust, hooks,
`model_instructions_file` or alternate configuration/profile selectors
through this member. This list illustrates the boundary; the exact allowlist,
not this list of examples, is the validator's authority.

Machine permission policy and explicit operator provider choices continue
through their existing separate surfaces. Machine consent to those surfaces
does not turn `codex_settings` into a raw TOML escape hatch or widen the
allowlist. Credential-store, credential-source and account keys remain
forbidden regardless of machine authorization; other future keys require a
reviewed typed vocabulary extension.

#### Inheritance and reporting

Collect contributions from the resolved closure once per package identity.
Compute each member's effective weight exactly as S §6 specifies; do not
introduce a special root or dependency priority. This machinery is retained
for future reviewed keys; with an empty package vocabulary it yields `{}` and
no contributions. It never composes or applies precedence to credential-store
selection. For each admitted key:

1. Select the highest effective weight under `winner=higher-weight`, or the
   lowest under `winner=lower-weight`.
2. If all declarations at that winning weight have the same typed value,
   coalesce them and retain every winning origin.
3. If winning declarations disagree, refuse resolution (`codex_settings_conflict`); no lexical name,
   overlay-list order, graph order or chapter placement breaks the tie.
4. If lower-ranked values differ, succeed with a visible `codex_settings_override` diagnostic
   identifying key, package origins, weights, winning value and winner rule.
   Identical redundant values remain visible in inspection provenance.

An unequal tie at a losing weight is recorded as superseded, not an error:
the selected extremum is unambiguous. Existing requirement-edge weight
conflicts remain S §6 conflicts before settings selection. Changing
`placement` alone never changes the effective settings.

Record contributions and effective values in the lock under a versioned
schema extension. Include them in lock identity, marker currency and status
inspection so a mutable path overlay or machine-weight change invalidates
the old result. The launcher sees only effective values and the existing
lock identity; provenance remains Curator's inspection concern.

#### Fragment and argv delivery

Add OPTIONAL `codex_settings` as a closed typed launch-override object to a
new closed fragment revision. Unlike the empty package vocabulary, this
transport admits `cli_auth_credentials_store` with `file` or `keyring` only,
filled exclusively by Curator from the machine selector. Machine overrides
are absent from package locks and markers, but covered by launch identity. Reserve no concrete version number here:
coordinate it with the parallel root-context and snapshot amendments to
avoid assigning incompatible meanings to one revision. It is admitted only
when `environment=codex_cli`; when empty it is omitted. No `channels`, raw
argv strings or file paths are supplied by the profile for this member.

Curator performs resolution, eligibility validation and canonical fragment
emission. The launcher consumes that exact effective object and passes it
through the typed agents-management request. The Codex plugin validates the
allowlist again and emits each key once, sorted by ascending ASCII key name,
as two argv elements: `-c` and `key=<canonical TOML scalar>`.
For the first use the actual elements are:

```json
["-c", "cli_auth_credentials_store=\"file\""]
```

Use a TOML scalar serializer; do not concatenate unquoted publisher text or
invoke a shell. The quotation marks above are part of the TOML argument,
not shell quoting. Keep configuration pairs before any positional prompt or
`--` boundary. Sort only the profile-settings block, preserving the existing
order and semantics of other provider-owned argv blocks.

Apply the same typed block in interactive, exec and hosted app-server
construction, login preparation, resumed hosts and tracked dispatch.
A reused host may keep the block only when its resolved settings identity
matches; otherwise restart through the normal host path or refuse reuse.
No caller may emulate delivery by sourcing `--format shell`, editing the
seed or reading an overlay directly.

L's fragment digest and the plan-covered launch must include this member.
A remote dispatcher relays the covered settings/fragment unchanged; it does
not resolve weights, synthesize overrides or select a backend. Reject an
unknown revision or a missing required settings payload at the consumer;
never downgrade a nonempty settings profile to an older fragment.

Host-owned policy keys and profile settings are disjoint. Before exec, the
host and plugin reject profile collisions with reserved channels and reject
conflicting raw `-c`/`--config`, dotted-table forms, native profile selection
or equivalent request/RPC fields that could replace a selected credential
backend. Equality does not authorize duplicate sources: require one owner.
The host separately validates its tool-policy surfaces, including resume.
Policy overrides, private policy documents and protected session parameters
remain host-controlled; profile data cannot choose their contents.

The host may still write its **own private** session policy `config.toml`.
It must not persist profile settings into that file, or rewrite a Curator
snapshot/seed as a side effect of applying this CIP. Hosted gateway isolation
must continue to construct an exclusive base document: `-c` table merging
cannot clear an inherited MCP inventory. If the host cannot compose a safe
launch with the requested setting, it refuses instead of dropping it.

#### Credential-store selection and CIP-0015

CIP-0015 section 2's machine selector `credential_store.<profile>.<env-id>`
(default `native`) is the only source of the Codex store choice under D14.
Curator fills this member as its single launch transport; packages, overlays,
locks and repositories cannot select, refine or override that choice.
D9's machine-selected file mode becomes `cli_auth_credentials_store="file"`
for login preparation and every subsequent launch. No credential bytes enter the manifest, lock,
fragment, plan, status row or diagnostics.

Separate two facts in status: **native storage**, which determines what can
be shared, and **effective launch storage**, which selects the managed
session backend. Preserve S §7.4's native-storage rule for sharing. A launch
file override does not turn a native keyring identity into a shared file
credential or make an existing `auth.json` the authenticated native store.

For an explicit machine selection, preparation checks this matrix before linking or
launching; read/parse failure is unknown and refuses, never native `file`:

| Mode | Native storage | Effective launch storage | Proposed result |
| --- | --- | --- | --- |
| shared | file, including absent native key | file | Use existing native-file passthrough and liveness checks |
| shared | keyring | keyring | Use current ambient identity semantics; no invented per-home keyring scope |
| shared | any other pairing, including auto | explicit file or keyring | Refuse; explain the backend mismatch/ambiguity and offer isolated preparation or explicit native-store migration |
| isolated | any successfully inspected native selector | file | Admit only a separately prepared private file credential; never link the native file |
| isolated | any | keyring | Refuse until independent per-home scoping is established |

The isolated/file row is an explicit amendment to S §7.4's native-file-only
eligibility gate, coordinated with CIP-0015; it is not a claim about current
code. Without an explicit machine selection, retain today's native-derived
rules, including current `auto` behavior. Backend or isolation changes to an
existing home require the existing inspect → plan → confirm → apply migration,
not repair. The setting cannot migrate credentials, silently sign in, repair
a detached link or bypass readiness. Unsupported backend capability refuses
with an actionable report before a model or login invocation.

## Security considerations

The adoption deliberately amends S §10.3's no-launch-influence statement only
for reviewed package keys, admitting none in this revision under D14.
The closed typed credential-store override is machine-owned; package bytes
admit no paths, names, raw TOML or policy keys. Profile-selected environment variables remain forbidden.
Two third-party requirements with differing winning values can deny resolution;
this is a fail-closed availability risk, not a permission bypass.

Treat every package contribution as hostile configuration, even from a signed
source: signature trust is not permission to weaken sandboxing. Exact-key
validation happens before inheritance and again at the launch boundary.
Closed values exclude TOML tables, command injection, provider redirection,
credential payloads, alternate instruction paths and MCP declarations.
Machine weights choose among admitted values; they grant no capabilities.

A hostile profile cannot add an MCP server through settings. MCP continues
through its existing declaration, allowlist, seed-revision and channel path.
This CIP does not erase the known residual of revision-A or pre-rule seeds,
or attest every future project-local configuration source as safe. Hosted
exclusive tool policy must account for those sources before accepting a
launch; ordinary settings validation is not an MCP isolation proof.

Bind settings to the resolved lock, fragment digest and session/plan identity.
Revalidate protected path-package boundaries at resolve/materialization as
S §§4 and 6 require; reject stale identities at launch handoff. Do not read a
mutable overlay a second time after accepting the resolved fragment. Resumed
and remote sessions must verify that the accepted selection is the selection
they actually use. Unknown versions and read failures never mean absence.

The credential store selector is nonsecret metadata. File mode still requires
private file ownership, permissions and the existing passthrough/liveness
rules; keyring mode still requires actual runtime access. No access probe may
print credentials or copy tokens into an outcome resource. Keep package
provenance in local inspection without exposing machine-specific details in
public fixtures or specifications.

## Compatibility and migration

Profiles without the new member keep their current behavior. The seed rule
and existing seed-revision records do not change. No repair or global sync
backfills profile settings into `config.toml`; user/tool edits remain intact.
Deploy strict readers before enabling producers, or atomically update both.
Old schema/fragment readers must reject an unsupported nonempty declaration,
not ignore it; empty declarations may only be omitted by a new reader after
validating the package extension.

Settings changes create a new resolved identity. New launches use it;
running sessions retain their accepted snapshot and settings. Resume either
uses that accepted identity or performs an explicit new-session transition.
Do not relabel a live keyring session as file-backed because an overlay moved.
Credential migration remains explicit, and CIP-0015 must adopt the shared
eligibility matrix before the new isolated/file row is enabled.

## Specification changes

The linked normative text adopts the following leaf-1 requirements; consumer
implementation, shared wire allocation and runtime qualification remain gated:

1. Environments §2 and the context schema MUST admit the optional closed
   `codex_settings` object and reject invalid contributions before merging.
2. Section 6 MUST extend effective weights to per-key settings selection,
   preserving all existing weight calculations and defining unequal winning
   ties as refusal. `placement` MUST NOT affect settings.
3. The lock, marker and status contracts MUST cover resolved settings and
   inspection provenance; their schema changes MUST be versioned together.
4. Sections 7.3 and 7.8 MUST retain their current descriptor grammars; §10.2
   MUST add the typed member in a newly assigned fragment revision.
5. Section 10.3 MUST narrow its no-launch-influence statement only for
   reviewed package keys, admitting none under D14, and retain the
   registry-only variable boundary. The credential-store override MUST come
   exclusively from CIP-0015's machine selector. L §§4.1–4.5
   MUST require closed validation, stable TOML
   argv delivery, digest coverage and refusal of unsupported delivery.
6. Section 7.4 and CIP-0015 MUST distinguish native sharing from effective
   launch storage and adopt the explicit-setting matrix above. Section 12.1
   MUST keep machine permission consent separate from profile settings.
7. Record D13's profile/inheritance/argv ownership and D9's concrete selector
   as owner decision 2026-10-15 (D13) and owner decision 2026-10-15 (D9),
   corrected by owner decision 2026-10-16 (D14): the selector is machine-owned,
   never a package contribution.

The adoption publishes new normative member schemas and diagnostics in a
separate unreleased namespace. Full successor carrier allocation remains open
with parallel amendments; existing closed wire schemas remain unchanged.
The leaf does not enable producers or claim an implementation has shipped.

## Implementation plan

Ordered leaves; sizes use relative Fibonacci points and denote future work:

1. **curator-spec, 3:** adopt manifest, lock and fragment schemas, credential
   matrix, closed allowlist and conflict diagnostics; publish cross-repository
   positive/negative vectors before enabling producers.
2. **curator, 5:** parse all contributions, resolve weights, record provenance,
   validate backend eligibility and emit the new canonical fragment; integrate
   with login/preparation and snapshot identity. Preserve seed bytes.
3. **skill-agents-management, 3:** extend the typed Curator context reader and
   Codex BuildPlan/Args path; serialize sorted scalar overrides; reject raw,
   reserved and unsupported-mode conflicts from every public plan entry.
4. **curator-agent-launcher, 3:** update SPEC and strict readers, carry settings
   through interactive/exec/tracked plans and digest coverage; qualify native
   argv delivery without inspecting profile layout or editing homes.
5. **skill-project-management, 5:** carry settings into hosted app-server and
   client/resume paths; retain private tool-policy ownership and exclusive
   builder isolation; reject backend changes on incompatible host reuse.
6. **swarma-dispatcher, 3:** preserve the plan-covered settings and snapshot
   identity across relay; verify tamper/missing-payload refusal without adding
   another resolver or home inspection layer.
7. **curator-spec, 2:** record jointly passing production-entry qualification,
   then enable the producer revision with all consumers available. Keep
   unsupported consumers fail-closed throughout staged rollout.

## Test plan

These are required future implementation tests, not tests claimed to run by
this specification change. Leaf 1 adds executable member-schema cases and
specification-data checks; no runtime gate ships in this leaf.

| Named test | Production entry and observation | Negative or narrowing mutant worth killing |
| --- | --- | --- |
| `SettingsResolveClosureWeights` (future reviewed vocabulary extension) | `curator env resolve --format json` with root, requirement and machine overlay; both winner directions; unchanged result under placement flip | Resolve only root/overlay and omit a required-package setting |
| `SettingsWinningTieRefuses` (future reviewed vocabulary extension) | Resolve equal winning weights with different admitted values; require refusal, no fragment | Permit equal-weight disagreement only for requirements |
| `SettingsValidateAllContributions` | Install/resolve package-selected stores and hostile lower-weight declarations; exact unknown keys, dotted aliases, duplicate keys and wrong types refuse | Validate only winning declarations or only deny `sandbox_mode` |
| `SettingsLaunchAllModes` | Real `curator-run` interactive/exec and hosted app-server construction; capture exact child argv and parse its TOML values | Apply settings only to interactive launches |
| `SettingsHostPolicySurvivesResume` | Hosted start, attach and cold resume under ordinary and builder tool policies; observe effective policy, not merely argv | Reject policy collisions on start but omit resume/RPC checks |
| `SettingsCredentialNativeMatrix` | Prepare/login/launch with disposable file/keyring fixtures across every matrix row; inspect metadata and link identity | Admit shared native-keyring/effective-file mismatch |
| `SettingsSeedUntouched` | Resolve, repair and launch over revision A/B seeds; byte-compare tool-owned config before/after | Avoid seed writes on resolve but write during launch |
| `SettingsMCPTableMergeResidual` | Supported Codex loader with a base server and `-c mcp_servers={}`; prove residual, then hosted builder excludes it by base construction | Treat an empty override table as replacement |
| `SettingsStrictRelayIdentity` | Resolve → materialize/covered plan → dispatcher → exec; altered, missing and unsupported member refuses | Verify digest except when settings is absent at the receiver |
| `SettingsRawOverrideConflict` | BuildPlan/direct plugin and hosted client requests with `-c`, `--config` and profile aliases; conflicting backend fails before exec | Scan split `-c` only and admit `--config=...` |

Preserve existing reviewer tests under their original names. Execute the
landing gate property suites on each implementation candidate. Qualify each
supported Codex release on macOS with and without credential-store access,
and Linux/Windows where those entry points are supported; file mode requires
no Keychain access. Use disposable accounts/homes and no inference call for
storage checks. Record exact versions and unknown capabilities rather than
extrapolating from the S baseline or the host source comment.

A future coverage map must bind each implementation surface to a real entry,
a named negative and a killed narrowing mutant. Report every mutant's actual
failing test; survivors state the bound they leave unproven. The table above
is a planned test matrix, not measured mutant coverage.

## Open questions for the operator

1. **Initial vocabulary:** D14 decides no package key in this revision.
   Credential-store, credential-source and account keys are never admissible;
   other keys need a reviewed typed vocabulary extension.
2. **Backend ambiguity:** D14 retains CIP-0015's machine selector unchanged.
   Its explicit `file`/qualified `keychain` choices map to `file`/`keyring` in
   the transport; `native` emits no override and retains native `auto` behavior.
3. **Cross-backend sharing:** refuse it or introduce a separate credential
   conversion/migration feature? Recommend refusal in this CIP and the explicit
   matrix coordinated with CIP-0015; isolated file preparation is the clean
   alternative when the native identity is in a keyring.
4. **Wire allocation:** one coordinated fragment revision with the parallel
   amendments, or sequential revisions? Recommend one jointly reviewed schema
   allocation if they ship together, otherwise independently versioned strict
   readers. Never reuse an existing revision or silently drop the member.

5. **Override qualification:** does the scalar override beat a conflicting seed
   and select the same backend for login, app-server and token refresh on each
   supported release? Recommend qualifying every path before enabling producers;
   unmeasured behavior remains unknown and unsupported, never assumed.

Questions 1–3 are answered by this adoption and D14: the package vocabulary
is empty, credential storage is selected only by the machine knob, and
cross-backend sharing is refused. Question 4
(shared carrier allocation) and question 5 (release qualification) remain open
rollout gates; no later repository leaf is implemented here.
