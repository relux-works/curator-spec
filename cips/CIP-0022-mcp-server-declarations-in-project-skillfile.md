# CIP-0022: MCP server declarations in the project Skillfile

- **Status:** Accepted; decision: operator, 2026-10-22
- **Owner:** orchestrator; decision: operator
- **Created:** 2026-10-21
- **Related:** TASK-261021-yiyrus — cip-mcp-in-project-skillfile;
  [CIP-0002](CIP-0002-project-context-in-managed-launches.md) — project
  context, item approval and fleet/manager ceilings;
  [Decision 0022](../decisions/0022-accept-skillfile-sources-v1.md) — sources
- **Affects:** Project Skillfile grammar, source resolution and future MCP
  contribution admission; environments §2.2; manager §§6 and 12;
  future schema, lock, approval and conformance artifacts

## Operative summary

| Field | Contract |
|---|---|
| Phase | Accepted; publication of the normative grammar and native qualification remain gates. |

## Owner decisions (2026-10-22)

The operator accepted this CIP and the recommended answers to all five questions:

1. **Staged boundary (Q1):** Adopt package resolution and native writers first.
   Block every inline arm until the relevant CIP-0002 admission contracts exist.
   Each advertised adapter still requires its normative contract and qualification.
2. **Install options (Q2):** Leave the nested `install` vocabulary undefined,
   report ignored options explicitly and initially ignore all options. Typed
   headers/auth require a later contract and separate effective-configuration
   approval; server approval confers no such authority.
3. **Runtime pins and lexical guards (Q3):** Adopt the listed URL character
   guards. The normative leaf must define a shared closed `npx`/`uvx` pin grammar,
   including exact flags, package forms and bypass negatives before enforcement
   claims. External documents or implementation validators are not authority.
4. **Inline audit waivers (Q4):** Permit none initially. Existing package waiver
   semantics remain unchanged. Any later inline waiver needs protected
   project/name/digest/field identity, exact finding scope and visible evidence.
5. **Carriers and writers (Q5):** Use a separate versioned namespace, distinct
   server/declaration/manifest identities and per-entry ownership, preserving
   released bytes. Freeze exact native paths, transaction scope, drift/removal
   controls and stage capability advertisement in the adoption leaf before
   claiming a supported writer.

These decisions accept the design; normative grammar publication and native
qualification remain gates. No schema, writer or managed capability is published.

## Summary

Propose project-only Skillfile schema 3: schema 2 plus an optional
`mcp_servers` map. Deliver Git declaration packages first under existing
source allowlist and audit gates, then inline declarations as individually
approved CIP-0002 project contributions. Reuse the closed `agent-mcp.json`
`server` object, one environment-id vocabulary and normalized declaration
digests. An optional neutral `install` member contains writer-local options
whose handling is explicit in the plan. The operator accepted this design on
2026-10-22; no released grammar, native writer or managed-launch capability
is changed or claimed here.

## Motivation and user stories

- A project author declares skills and MCP requirements/configuration inputs
  together, without copying native configuration for each environment.
- An operator selects an audited Git declaration package using the same
  source policy and immutable snapshot discipline as existing MCP packages.
- An operator reviews each inline declaration and approves its exact server
  digest; a repository edit cannot silently change executable arguments,
  endpoint, environment-variable access or selected environments.
- A manager reports every server/environment pair, including known targets
  it cannot write, and explains which writer-local options it ignores.

## Current state

The specification baseline examined is curator-spec `e41f96387287f5e76604627f9e63662f7d6d86d4`,
whose released specification identifies itself as 1.0.0-rc.14. This is a
protocol proposal, not an implementation investigation; no runtime probe
or fresh Curator implementation conformance is asserted.

[Core §5](../protocol/core.md#5-project-manifests) defines schema 1.
[Skillfile sources revision 1 §1](../protocol/skillfile-sources.md#1-acquisition-and-selection)
adds optional project schema 2 without implicit migration. Unsupported
versions fail with the upgrade error. Its §3 binds the parsed declaring
Skillfile to `manifest_sha256`; this raw manifest identity must not be
silently replaced by a normalized MCP digest.

[Environments §2.2](../protocol/environments.md#22-mcp-declaration-packages)
defines Git-only `agent-mcp.json`, closed transport arms, URL restrictions,
reserved environment names, MCP package allowlisting and secret-material
audit. Its §2.3 requires surfacing before publication.
[Manager §12](../profiles/manager.md#12-agent-environments-manager-profile)
retains protected stores, ledgers, audit-before-publication and read-only
resolve/status. [Manager §6](../profiles/manager.md#6-mcp-requirements)
checks requirements read-only; it does not authorize installing a server.
The environments introduction explicitly leaves native MCP write management
for separate review. These contracts must be extended through adoption,
not inferred from design acceptance.

[CIP-0002](CIP-0002-project-context-in-managed-launches.md#operator-input-2026-10-10)
requires individual protected project contributions, attributed approvals,
fleet/manager ceilings and suppression of unadmitted native discovery. It
was accepted on 2026-10-22; normative publication and native qualification
remain gates. Schema-3 parsing alone cannot satisfy those launch gates.
The operator decisions of 2026-10-21 fix the neutral `install` name, the
environment rule, package-first sequencing and digest-bound inline approval;
the remaining choices were resolved by the 2026-10-22 owner decisions above.

## Design

### Options considered

| Option | Mechanism | Tradeoff |
|---|---|---|
| Native configuration only | Keep one native MCP file per tool outside the Skillfile. | No new grammar, but repeated declarations, separate ownership and no common review identity. |
| Inline declarations first | Add URL/object declarations directly to install. | Convenient, but bypasses the existing Git package allowlist unless a new approval authority is implemented first. |
| Package first, approved inline second | Add schema 3 with explicit declaration arms and staged capability support. | Reuses package trust now; inline waits for CIP-0002 admission rather than treating repository bytes as authority. Recommended. |

### Recommendation

The operator accepted the third option; normative publication remains a gate.
The following capitalized requirements describe the proposed contract only.

#### Schema and scope

Schema 3 is exactly schema 2 with `schema_version: 3` and the optional
top-level member `mcp_servers`. All other schema-2 fields, source aliases,
selectors, skill semantics and strict unknown-field rules retain their
meaning. Skill manifest versions remain independent. Schema 1 or 2 MUST
NOT accept `mcp_servers`; writers MUST NOT upgrade a file to 3 implicitly.
A machine-global Skillfile MUST continue to reject schema 3 with the
upgrade error; profile locks remain the machine-global mechanism.

`mcp_servers` is an object mapping case-sensitive NAME to exactly one DECL
arm below. NAME matches `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$`. Duplicate JSON
keys, invalid UTF-8, unknown members, mixed arms and JSON null MUST be
rejected before acquisition or publication. An absent or empty map means
no project MCP declarations; it does not remove unrelated native entries.

#### Declaration grammar

1. **URL shorthand:** a string expands exactly to
   `{"server":{"transport":"http","url":"<string>"}}`.
2. **Inline object:** exactly `{"server": SERVER, "install"?: OPTIONS}`.
3. **Package object:** exactly `{"package": PACKAGE, "install"?: OPTIONS}`.
   It MUST NOT also contain `server`.

```json
{
  "schema_version": 3,
  "skills": [],
  "mcp_servers": {
    "docs": "https://docs.example.invalid/mcp",
    "tools": {
      "server": {
        "transport": "stdio",
        "command": "uvx",
        "args": ["example-mcp==1.2.3"],
        "env_names": ["TOOLS_TOKEN"],
        "environments": ["claude_code", "codex_cli"]
      }
    },
    "catalog": {
      "package": {
        "git": "https://code.example.invalid/tools/catalog.git",
        "tag": "v1.2.3",
        "directory": "mcp/catalog"
      }
    }
  }
}
```

The examples are inert declarations, not fetch or execution instructions.
SERVER is **exactly** the closed server object of environments §2.2 and
[`agent-mcp-v1.schema.json`](../schemas/v1/agent-mcp-v1.schema.json):

| Transport | Required members | Optional members | Forbidden members |
|---|---|---|---|
| `stdio` | `transport`, `command`, `args` | `env_names`, `environments` | `url` and any other member |
| `http` | `transport`, `url` | `env_names`, `environments` | `command`, `args` and any other member |

`command` is a bare executable name (1–255 characters), never a path.
Arguments are strings bounded at 8192 characters each under that schema.
`env_names` is a unique list of names, with the existing reserved-name
exclusions and machine passability ceilings. It contains no values.
No headers, auth data, shell recipe, runtime bootstrap or executable code
is admitted as an extra SERVER member. Additional runtime pin rules for
`npx`/`uvx` need a closed, reviewed grammar before adoption; the example's
version pin does not establish such a validator (operator question 3).

#### URLs and secrets

Both URL forms MUST meet environments §2.2: HTTPS, ASCII host, no userinfo,
query or fragment, and the existing 9–4096 character schema bounds. The
schema-3 lane additionally proposes rejecting whitespace, control/format
characters, `$`, braces and backslashes; it performs no interpolation,
URL decoding into commands, environment expansion or shell evaluation.
These extra lexical guards need dedicated vectors and do not retroactively
change existing package schema bytes.

The `context-secret-material` detector MUST inspect `url` and `args`,
including the expanded shorthand and resolved package. A token in a URL
path is a blocking finding even when URL syntax is valid. Audit also
covers `install` input so a writer-local extension cannot hide credentials.
No approval or ordinary content pin clears a secret finding. Existing
package audit/waiver policy is retained; extending waiver identity to inline
inputs is a separate owner decision, with no inline waiver by default.
Diagnostics identify the field and finding class without echoing secret
bytes. No credentials are read or authentication attempted at install.

#### One environment vocabulary

`server.environments`, when present, is a nonempty unique list of canonical
Curator adapter ids. Use the registered ids in
[environments §7](../protocol/environments.md#7-environment-adapter-registry):
currently `claude_code`, `codex_cli`, `opencode`, `pi` and `muse`. Command-line
aliases are not persisted ids; skill-only adapters do not become environment
ids through this proposal. An unknown id is `mcp_declaration_invalid`.

Absence means every environment the manager can write, independently of
the Skillfile's skill `agents` selection. A listed, known environment the
manager cannot write gets exactly `skipped: unsupported` for that pair;
it MUST NOT refuse the operation or be silently dropped. That skip never
claims native write support, project isolation or managed-launch delivery.
CIP-0002 still refuses a launch whose required admitted capability cannot
be enforced. A reporting skip during installation cannot waive that gate.

#### Stage A: declaration packages

PACKAGE reuses environments §2's Git MCP requirement grammar: `git`,
exactly one of `range`, `tag`, `revision`, and optional `directory`.
`range` uses environments §1.4; a revision is a full lowercase commit OID;
`tag` uses the existing tag grammar. No `branch`, `path`, source-alias or
local-snapshot arm is added. `directory` uses the environments package
path discipline: absent selects root, `.` is invalid, traversal and symlink
components refuse. The selected root MUST contain valid `agent-mcp.json`.
Its `name` MUST equal NAME; no renaming or last-writer-wins is introduced.

Resolve and freeze exact committed bytes through existing source safety,
source allowlist, MCP package allowlist (including hardened empty-list
refusal), signer/revocation and strict audit gates. Record package identity,
selected directory, resolved version/commit and server digest in a future
versioned lock; no moving ref is resolved at launch or status. Updating a
package re-audits the candidate and preserves the previous installation on
failure. A package declaration does not bypass CIP-0002 when later composed
as project control context in a managed launch.

The stage-A reader recognizes inline arms but refuses them with
`mcp_inline_approval_unsupported`, including a plain URL. It MUST NOT silently
ignore them or weaken the package-only allowlist to accept local content.

#### Stage B: inline project contributions

Inline URL/object declarations are CIP-0002 `mcp` items. The allowlist key
is **(manager-registered project identity, NAME)**, never a repository label,
Skillfile alias, endpoint host or executable name. No inline declaration
acquires a fabricated Git source, registry attestation or package identity.
The package-source allowlist continues to govern package declarations;
it cannot authorize inline entries through an empty-list default.

Before any native write or launch admission, each inline item needs operator
approval bound to that key and SHA-256 of its normalized SERVER object.
Even a plain HTTPS endpoint declaration requires approval. Approval records live in
protected manager state, record the approver and effective ceiling/policy,
and are never accepted from the repository. An agent may exercise approval
only under a previously granted, recorded ceiling. Operator and agent
approval cannot exceed immutable fleet/manager denies or widen passable
secret names. Enabling a category does not approve its items.

Changes to endpoint, transport, command, argument order/content, environment
names or selected environments require a new approval. A syntax-only edit
whose normalized server is identical does not change this approval binding.
Changing NAME or project identity cannot replay it. Revoke/disable prevents
future admission; changed candidates are never automatically adopted.
At publication and launch, revalidate protected approval, current policy
and exact snapshot/digest; refusal leaves prior native and manager state
unchanged. CIP-0002's protected composition, source-exclusion, lifetime
and lease requirements remain prerequisites for managed activation.

#### Normalization and distinct digests

Normalize only after strict parsing and complete semantic validation:
expand shorthand; represent absent `env_names` as `[]`; sort unique
`env_names` and explicit `environments` by UTF-8 bytes; preserve argument
order and all string scalar values exactly. Do not lowercase URLs, trim
arguments, normalize Unicode or resolve executable paths. Leave absent
`environments` absent, meaning all writable environments at planning time;
an explicit list remains distinct. CCJ-1 canonicalizes object key order.

The **server digest** is `sha256:` plus SHA-256 of CCJ-1 of this normalized
SERVER, without an enclosing object or trailing LF. Shorthand and its
expanded object have the same digest. This digest binds inline approval;
NAME/project are bound separately by its allowlist key.

The **normalized declaration model** is the expanded declaration with its
normalized server (or package selector), with absent `install` represented
as `{}`. Its CCJ-1 SHA-256 is the declaration digest; shorthand and expansion
also match here. A resolved package additionally binds its exact acquired
identity and resolved server digest in the effective plan. `install` changes
alter the declaration/plan identity even when the server digest is stable.
Neither digest replaces schema-2 `manifest_sha256` or existing lock hashes:
textually different parsed manifests may retain different manifest hashes.
The adoption leaf must version affected lock/approval/plan carriers, rather
than extending a closed released carrier in place.

#### Writer-local `install`

OPTIONS is an object for writer-local install options that a manager may
honour or ignore and names in its plan. This CIP reserves no member for a
particular implementation. Potential uses include `headers`, `auth`, `scope`
and `git_policy`; their nested grammar and defaults are deliberately
**undefined here**, not four newly standardized native options.

The plan MUST name each supplied option and whether it is honoured or
ignored, without exposing values that may be sensitive. A writer claiming
support MUST identify its documented contract and validate the option before
mutation; an ignored option has no native effect. Unknown DECL members
outside `install` always refuse. `install` MUST NOT override SERVER,
select machine-global scope, authorize network/secret access, bypass audit
or ceilings, or start a process. Any supported option affecting effective
control configuration requires its own CIP-0002 approval/ceiling binding;
server-digest approval alone cannot authorize an auth/header change.
Curator's initial writer should ignore all OPTIONS with explicit plan rows
until a separate typed contract is accepted (operator question 2).

#### Planning, ownership and total reporting

Validate the complete declaration set, source/audit/approval gates and
planned native preimages before any publication. Reuse marker/ledger
ownership and no-follow transaction rules; a foreign same-name native entry
is a conflict, never permission to overwrite it. Profile/project same-ID
servers deduplicate only under CIP-0002's matching identity rule; a differing
server needs explicit replacement approval. Failure MUST leave prior native
files, skills, lock and ownership/approval records unchanged.

For each valid NAME, enumerate explicit `environments`, or all writable
environments when absent, in stable NAME/environment byte order. Emit
exactly one outcome per pair, naming the canonical environment and actual
project-relative output path. When there is no writable target/path, report
`path: unavailable`; never invent a path for an unsupported adapter.

Outcomes are `added`, `updated`, `unchanged`, `restored`, `removed`,
`released`, `skipped: drift`, `skipped: unsupported`,
`conflict: foreign entry`, or `refused: <code>`. Restoration/release/removal
require an explicit ownership/drift policy and approval of affected items;
this proposal does not automatically enroll foreign configuration. Include
previously owned removed pairs in a cleanup plan. A refused operation still
reports all determinable affected pairs and its refusal summary, with no
successful mutation outcome. Syntax errors that prevent pair enumeration
get a declaration-level diagnostic; report every independently determinable
pair without fabricating a target from malformed data.

`--dry-run` prefixes each planned pair with `would:` and performs no writes,
fetches, auth checks or server starts; missing locked input is a reported
precondition failure, not permission to acquire it. After successful writes,
state `MCP configuration installed. Authentication not checked.` Any per-tool
setup/login hints are printed and never executed. Native path/adapter
qualification is part of later writer adoption, not established here.

#### Proposed typed refusal codes

| Code | Condition |
|---|---|
| Existing upgrade error | Unsupported schema 3, or schema 3 in machine-global scope; no fallback parse. |
| `mcp_declaration_invalid` | Invalid NAME, mixed/unknown declaration arm/member, malformed server/URL, invalid or unknown environment id. |
| `mcp_package_not_allowed` | Package outside the existing MCP source allowlist. |
| `mcp_package_allowlist_empty` | Existing warning under permissive policy; existing blocking empty-list case under hardened policy. |
| `mcp_inline_approval_unsupported` | Inline arm requested before the stage-B admission capability exists. |
| `mcp_inline_approval_required` | No current protected approval for this project/NAME/server digest, including changed/revoked approval. |
| `mcp_contribution_policy_refused` | Approval would exceed fleet/manager ceilings or an install option lacks required effective-config approval. |
| `mcp_native_entry_conflict` | Planned native name is foreign or conflicting; no overwrite. |
| `mcp_install_option_invalid` | Writer claims an install-option contract but its supplied value fails that contract. |

Secret detection retains finding class `context-secret-material` with a
blocking audit result. Existing snapshot, source, signer, store, read-failure,
transaction and launch capability codes retain their distinct conditions;
these failures MUST NOT all become `mcp_declaration_invalid`.
`skipped: unsupported` is a pair outcome, **not** a refusal code. The exact
new code spellings remain subject to operator adoption.

## Security considerations

A hostile checkout controls declarations, native config, symlinks and later
edits. It may try token-bearing URLs, environment-name widening, executable
arguments hidden behind `npx`/`uvx`, cross-project approval replay, foreign
entry takeover or a changed snapshot after approval. Package allowlisting
bounds source identities, not executable intent; a bare command allowlist
alone cannot constrain programs selected by its arguments.

Always audit expanded shorthand and complete resolved packages before
publication; secret material blocks even in syntactically valid URL paths.
Approval binds exact normalized bytes plus project/name and is checked
again against protected state and current ceilings. Never accept an
on-repository approval, source native config implicitly, follow unowned
links or treat unreadability as absence. Snapshot/digest checks alone do
not isolate same-user hostile processes; CIP-0002 adapter qualification
must establish the claimed boundary. Do not claim managed delivery merely
because a native project file was written.

No MCP server, package manager, runtime installer or server command is ever
started at install, preview, audit, status or requirement checking. No
server connection or login is attempted. Operator credentials stay outside
repository inputs, locks, markers, reports and materialized configuration;
only policy-admitted names/references may reach a later authorized launch.
This proposal does not grant a launcher a new execution capability.

## Compatibility and migration

Keep Skillfile schemas 1/2, released `agent-mcp.json`, existing source and
profile locks, release metadata and conformance pins byte-identical. A
schema-3 reader implements all schema-2 semantics; schema-2-only readers,
including Curator releases through rc.7, reject schema 3 with the upgrade
error and MUST NOT ignore its MCP member or downgrade the file. That rc.7
compatibility requirement is the operator's supplied baseline, not a new
binary probe result. Existing writers never upgrade files automatically.

Publish package support before inline approval support, and advertise each
capability honestly. Stage A refuses every inline arm; stage B is not
enabled until CIP-0002's relevant admission contracts are adopted. Native
project configuration support and strict managed-launch support are separate
claims. No automatic import, takeover, credential migration or machine-global
Skillfile schema upgrade occurs.

## Specification changes

Following design acceptance, separately publish a Decision record for schema 3,
package-first trust and project/name/server-digest approval. Amend core §5 and the source extension
for inheritance and version dispatch; environments §2.2 for reuse and §2.3
for surfacing; manager §§6/12 for explicit write-management capability,
ownership and the separation from read-only requirement checks. Coordinate
CIP-0002 contribution, approval, composition and launch transport changes.

Publish separate schema-3, lock/approval/plan schemas and conformance artifacts
only after their complete grammar is reviewed. Do not rewrite closed released
carriers or core-suite pins. This acceptance record publishes no schemas or
vectors. Proposed vectors remain listed below for the normative adoption leaf.

## Implementation plan

| Order | Leaf | Size | Exit evidence |
|---|---|---|---|
| 1 | Record operator acceptance and answers | S | Completed by the 2026-10-22 owner decisions; subsequent publication and qualification gates remain. |
| 2 | Normative stage-A grammar, versioned carriers and vector namespace | M | Schemas, prose, positive/negative corpus and Decision agree; frozen release bytes unchanged. |
| 3 | Package resolver and qualified native writer | M per adapter | Real install/preview/status paths preserve allowlist/audit/ownership gates, report all pairs and start no server. |
| 4 | CIP-0002 inline authority and protected carriers | M | Project/name/digest approvals, ceilings, revocation and replay tests pass before inline activation. |
| 5 | Stage-B writer and separately qualified managed delivery | M per adapter | Exact approved snapshot delivered; unadmitted native discovery excluded, or launch refuses with evidence. |

No implementation task, native binary installation or runtime qualification
is authorized by this acceptance record. Split cross-component leaves before
implementation and record exact tool/platform versions at qualification.

## Test plan

The following are **vectors to add at adoption**, not tests claimed to pass
by this acceptance record. Each gate needs nearby valid controls and a
narrowing mutant
that fails for the intended invariant, not unrelated setup errors.

| Family / claim | Positive controls and forbidden outcomes | Narrowing mutant |
|---|---|---|
| Scope and inheritance | Project schema 3 retains every schema-2 source/skill form; schemas 1/2 reject MCP, global 3 and older readers fail with upgrade, no writes. | Drop version/scope dispatch or ignore `mcp_servers`. |
| Declaration arms | Shorthand/object/package valid; invalid NAME bounds, duplicate keys, unknown fields, null, mixed arms and wrong transport members reject before fetch. | Permit one extra server member or mixed arm. |
| URL and secrets | Valid HTTPS succeeds; HTTP, Unicode host, userinfo/query/fragment, lexical violations and a token in URL path/args block without echo or writes. Include maximum-length boundary controls. | Scan only queries, or scan objects but omit shorthand. |
| Environments | Missing selector covers writable adapters; known unwritable id skips without refusal; unknown id rejects; no fallback to skill `agents`. | Reject known unsupported ids or accept any syntactically valid id. |
| Packages | Allowlisted audited exact snapshot installs; nonallowlisted source, hardened empty list, moved lock input, directory escape/link, wrong package name and absent manifest refuse without partial writes. | Apply general source allowlist but omit MCP allowlist. |
| Inline authority | Exact approved digest succeeds; missing/revoked/changed approval, another project/name, self-minted record and ceiling violation refuse. Stage A refuses URL/object even if an external record claims approval. | Reuse approval by NAME only, or approve plain URLs implicitly. |
| Digests | Shorthand equals expansion; key/set order is immaterial; argument order, endpoint, selector and env names change server digest; install changes plan digest; raw manifest hash remains distinct. | Hash raw shorthand bytes, omit args/selector, or use normalized MCP hash as manifest hash. |
| Install options | Ignored options are named with no effects; supported validated options preserve ceilings; malformed supported option and unapproved effective header/auth change refuse. | Allow install option to overwrite server or widen secret access. |
| Ownership and reporting | Owned updates/removals and mixed supported/unsupported pairs report once each; foreign entries, unreadable preimages, drift and publication failure preserve complete prior state. Dry-run is read-only. | Treat failed reads as absence, omit refusal rows or publish first pair before all gates pass. |
| No execution and launch boundary | Install/preview/status with instrumented fake runtimes start no server and contact no endpoint; qualified managed launch uses approved snapshot, otherwise refuses. | Run command as a readiness probe, or treat native write success as strict launch admission. |

Runtime pin conformance vectors remain pending normative publication of the
accepted closed-grammar direction; they must cover both valid pinned invocations
and bypass variants. Native
writer qualification runs on each advertised adapter/platform/version using
disposable homes with no real credentials. Schema tests establish structural
validity only; they cannot prove native loading or isolation.

For this documentation-only change, validate template sections,
Accepted status/date/index agreement, local links and unchanged normative paths. Exercise the link checker
with a bounded broken-link control. No product behavior changes, so executable
runtime regression tests and runtime mutants are inapplicable to this delta.

## Open questions for the operator

All entries below are resolved; original questions and recommendations
are retained as historical text.

1. **Accept this Draft's staged boundary?** Recommend package resolution/native
   writer adoption first, with every inline arm blocked until the relevant
   CIP-0002 admission contracts exist. Does the owner want a narrower first
   native-adapter set before the stage-A normative leaf?
   **Resolved:** [2026-10-22 owner decision 1](#owner-decisions-2026-10-22)
   adopts the recommendation above.
2. **Standardize `install` now?** Recommend leaving its nested vocabulary
   undefined, explicitly reporting ignored options, and initially ignoring
   all of them. Typed headers/auth need a later contract and separate effective
   configuration approval; they cannot inherit authority from server approval.
   **Resolved:** [2026-10-22 owner decision 2](#owner-decisions-2026-10-22)
   adopts the recommendation above.
3. **Runtime pin and lexical guards?** Recommend adopting the listed URL
   character guards and defining a shared closed `npx`/`uvx` pin grammar in
   the normative leaf. Exact allowed flags, package forms and bypass negatives
   must be specified before a reader claims enforcement; no external document
   or implementation-specific validator becomes authority by reference.
   **Resolved:** [2026-10-22 owner decision 3](#owner-decisions-2026-10-22)
   adopts the recommendation above.
4. **Inline audit waivers?** Recommend none initially. Existing package waiver
   semantics remain unchanged; any later inline waiver needs protected
   project/name/digest/field identity, exact finding scope and visible evidence.
   **Resolved:** [2026-10-22 owner decision 4](#owner-decisions-2026-10-22)
   adopts the recommendation above.
5. **Carrier and writer contracts?** Recommend a separate versioned namespace,
   distinct server/declaration/manifest identities and per-entry ownership,
   preserving released bytes. Freeze exact native paths, transaction scope,
   drift/removal controls and stage capability advertisement in the adoption
   leaf before claiming a supported writer.
   **Resolved:** [2026-10-22 owner decision 5](#owner-decisions-2026-10-22)
   adopts the recommendation above.
