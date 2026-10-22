# Project Skillfile MCP declarations, stage A, revision 1

This normative, separately versioned extension adopts CIP-0022's package-first
stage A. It changes no released carrier or core-suite pin. Its capability token
is `skillfile-mcp-stage-a-v1`. Implementations MAY omit this capability; a
supporting implementation MUST implement this complete stage, together with
Skillfile sources revision 1 and repository transport revisions 1–2. Acceptance
is not evidence that a particular manager or native adapter implements it.

## 1. Scope, inheritance and dispatch

Project Skillfile schema 3 is schema 2 with `schema_version: 3` and optional
`mcp_servers`. All schema-2 fields, source aliases, skills, selection rules and
strict unknown-member behavior retain their meaning. Skill manifest versions
remain independent. Writers MUST NOT implicitly upgrade a Skillfile. Schemas
1/2 reject `mcp_servers`. A schema-2-only reader, or a machine-global schema-3
input, fails with the existing upgrade error, before acquisition or writes.
Machine-global profile locks retain their existing role.

Parse strict UTF-8 JSON: duplicate keys, non-scalar strings, non-JSON constants,
non-integral numbers, negative zero (`-0`) and integers outside CCJ-1's safe
range refuse. Reject negative zero before integer conversion, including inside
ignored `install` data. Unknown members, mixed declaration arms and null refuse as `mcp_declaration_invalid`.
An absent/empty map has no declarations; it does not enroll or remove foreign
native entries. NAME is case-sensitive and matches
`^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$`.

## 2. Closed declaration grammar

`mcp_servers` maps NAME to exactly one of:

- URL string: expands to `{"server":{"transport":"http","url":URL}}`.
- Inline object: exactly `{"server":SERVER,"install"?:OPTIONS}`.
- Package object: exactly `{"package":PACKAGE,"install"?:OPTIONS}`.

SERVER has the closed environments §2.2 server member vocabulary:
`stdio` requires `transport`, bare `command` and `args`; `http` requires
`transport` and `url`. Both optionally contain `env_names` and `environments`.
No headers, auth, inline environment values, shell recipe or unknown SERVER
member is admitted. Inline command length is 1–255 Unicode scalars; each
inline argument is at most 8192 Unicode scalars. Inline URL length is defined
in §3. Retain reserved-name exclusions and machine passability ceilings.

Resolved `agent-mcp.json` packages MUST first pass their unchanged legacy
UTF-8 **byte** ceilings: URL 4096 bytes, command 255 bytes, each argument 8192
bytes. The package path is stricter than inline syntax for multibyte values;
a value within the inline scalar ceiling can still be invalid in a package.
Both planning and locked replay enforce these byte ceilings in addition to
schema scalar limits. Released package schemas remain unchanged; JSON Schema
`maxLength` alone cannot establish a UTF-8 byte ceiling. The stage-A lane
additionally applies [the closed runtime-pin sheet](mcp-runtime-pins.md) and §3 below to
resolved packages; it does not alter legacy package acceptance outside this
new lane.

PACKAGE reuses environments §2's MCP requirement: `git`, exactly one of
`range`, `tag`, `revision`, optional `directory`. Retain the Git URL grammar,
semver range grammar, tag grammar and full lowercase 40/64-character commit
OID. No branch, path, source alias or local-snapshot arm exists. Directory is
a portable relative path, never `.`, traversal or a symlink component; absent
selects the repository root. The selected root MUST contain valid schema-1
`agent-mcp.json` whose `name` equals NAME. No renaming or last-writer-wins.

A stage-A reader recognizes inline arms but MUST refuse them, including plain
URLs, as `mcp_inline_approval_unsupported`. A record supplied by the project,
an ordinary pin, an empty package allowlist or a purported external approval
cannot enable stage B. Structurally malformed declarations still receive
`mcp_declaration_invalid`; recognizing the arm does not waive parsing.

## 3. URLs, audit and ignored options

Inline URLs have 9–4096 Unicode scalar values (packages additionally obey §2’s
4096-byte ceiling), the HTTPS scheme and ASCII host, with
no userinfo, query or fragment, as environments §2.2. Additionally reject
Unicode whitespace, control and format characters, `$`, `{`, `}`, and `\`.
Check the lexical string before parsing it. Perform no interpolation,
percent-decoding into commands, environment expansion or shell evaluation.

Run the existing `context-secret-material` detector over expanded inline
inputs, resolved package `url`/`args`, and **all** `install` keys and values.
A token in a syntactically valid URL path remains blocking. Diagnostics name
the field/finding class, never matching secret bytes. No ordinary content pin
or approval clears a secret finding. Retain existing protected package audit
and waiver policy; this extension adds no Skillfile waiver and no inline
waiver. No credentials are read and no authentication is attempted.

OPTIONS is an arbitrary JSON object, with no standardized nested vocabulary.
For stage A every supplied top-level option is **ignored** and named, in UTF-8
byte order, in the plan, without its value. No option can override SERVER,
change project scope, authorize network/secret access, bypass audit/ceilings
or start a process. `headers`, `auth`, `scope` and `git_policy` are examples of
ignored names, not standardized options or accepted authority. A writer-local
supported option contract, and its `mcp_install_option_invalid` check, require
a separately accepted revision; stage A MUST NOT claim such support.

## 4. Trust, resolution and exact replay

Before publication, apply existing source safety, general source allowlist,
MCP package allowlist, signer/revocation and strict audit gates. MCP allowlist
matching is core §6.1's segment-aware canonical identity matching. A package
outside it refuses with `mcp_package_not_allowed`. An empty MCP allowlist
warns `mcp_package_allowlist_empty` under permissive policy; hardened policy
refuses with that code when the declaration set contains a package. This
warning is not a blocking error under permissive policy.

Resolve and freeze the exact committed package bytes, selected directory,
version/commit, content identity and normalized server digest. Validate package
schema/name and all additional stage-A gates on the resolved candidate. No
moving ref is resolved by status or launch. Replay a missing snapshot under
the existing source replay rules; changed content is `source_snapshot_changed`,
unavailable input is `source_snapshot_unavailable`, and changed full-document
CCJ-1 manifest identity is `source_lock_stale`. Update re-audits the candidate.
Failure retains previous native files, skills, lock, approvals and ownership state.

Schema-3 parsing or package allowlisting does not authorize managed project
control context. CIP-0002 admission, protected composition, ceilings, exact
snapshot delivery and native-source exclusion remain separate prerequisites.
No stage-A native write establishes managed-launch delivery.

## 5. Environment selection and reporting

Persist only canonical registry ids: `claude_code`, `codex_cli`, `opencode`,
`pi`, `muse`. Unknown ids and aliases are `mcp_declaration_invalid`. An explicit
selector is nonempty and unique. Absence selects every writable environment,
independently of skill `agents`. The first writer-adoption wave is Claude,
Codex and Muse; each still needs real adapter/platform qualification. Do not
infer an available output path or writer from registry membership.

For each valid NAME enumerate explicit environments, or writable environments
when absent, in NAME/environment UTF-8 byte order. Include previously owned
removed pairs in cleanup plans. Emit exactly one outcome per pair with the
actual project-relative path. A known unsupported environment gets
`skipped: unsupported`, `path: unavailable`, without refusing the operation.
Unknown or malformed targets never become invented paths. Declaration errors
that prevent enumeration get declaration-level diagnostics; retain all other
independently determinable pairs.

Outcomes are `added`, `updated`, `unchanged`, `restored`, `removed`, `released`,
`skipped: drift`, `skipped: unsupported`, `conflict: foreign entry`, or
`refused: CODE`. A refused transaction reports all determinable affected pairs
and a summary, with no successful mutation outcome. Dry-run prefixes each row
`would:` and performs no writes, fetches, auth checks or server starts. Missing
locked input is a reported precondition failure. After successful publication
print `MCP configuration installed. Authentication not checked.` Per-tool
setup/login hints are printed and never executed.

## 6. Versioned carriers and ownership

The complete closed schemas live in
[schemas/skillfile-mcp-v1](../schemas/skillfile-mcp-v1/README.md). They are new
carriers, not added members of released locks. `mcp-lock-v1` encloses an
unchanged source `skills_lock`, full-document CCJ-1 `manifest_sha256`,
manager-registered `project_id`, and sorted unique NAME entries with normalized declaration and
exact resolved package/server identities. A source lock's manifest identity
MUST equal the outer manifest identity. Bind the current project and parsed
manifest identity on every replay; a well-formed repository-supplied lock is
not trust.
`resolved.directory` is null for the root, otherwise exactly the declared
portable directory. Resolved source identity is the canonical identity of the
declared Git source; transport policy never enters it. An explicit revision
MUST equal `resolved.commit` (including OID width); a declared range MUST
contain `resolved.version` under the existing source SemVer range semantics,
including prerelease rules. Rehashing cannot legitimize a contradictory
selection. Tag-to-commit and snapshot attestations remain external requirements.
Require normalized server/declaration bytes, recompute their digests and the enclosed source-lock
digest, and reject duplicate or unsorted names. Compare each plan’s complete
pair set against its exact lock and current capabilities; a standalone plan
schema cannot establish completeness or protected authority.

`mcp-approval-v1` is a **protected package ownership-action authorization**,
not an inline contribution approval. It binds project/NAME/server/content
identity, operation (`replace`, `restore`, `remove`, `release`), approver,
effective policy digest and active/revoked state. Require a matching current
protected record for those explicit actions; ordinary package install still
uses existing package source/audit authority. Refuse effective policy/operation
violations as `mcp_contribution_policy_refused`; never consume repository
records as authority. Stage B's inline approval carrier namespace is reserved,
with no accepted stage-A instance or inline admission path.

`mcp-plan-v1` binds project, manifest and lock identities, dry-run state,
sorted unique pair rows and ignored-option names. A missing target path is
JSON null (`unavailable` when rendered). The plan lock digest MAY be null
when input is unavailable and the plan refuses, or when there are no pairs;
a successful nonempty plan MUST bind a real lock digest. Only `refused` rows have a refusal
code; unsupported rows have null path/code. Plans containing a refusal/conflict
have no successful mutation outcomes. Plans are observations, not approval.
Hash the complete carrier using CCJ-1 after omitting only its own digest field:
`lock_sha256` or `plan_sha256`. Neither hash replaces the full-document
CCJ-1 manifest identity.

Maintain per-record protected ownership keyed by project/NAME/environment/path,
binding native entry preimage and last installed digest; owning a file does
not own foreign entries in it. Validate every planned preimage, source and gate
before a single transaction publishes native edits, skills, lock and ownership
state. A foreign same-name entry refuses `mcp_native_entry_conflict`; an
unreadable preimage is not absence. Use lossless entry edits, no-follow parent
and leaf handling, race revalidation, complete rollback and existing store/
ledger protections. Drift defaults to `skipped: drift`; explicit restore,
release, removal or replacement needs the protected action record above.
Qualification must freeze actual native paths and entry encodings for each
writer; this specification does not invent a Muse path or authorize a server
process. Requirement checks remain read-only even when a writer is supported.

## 7. Normalization and distinct identities

After strict parsing and complete semantic validation, expand shorthand;
represent absent `env_names` as `[]`; sort unique `env_names` and explicit
`environments` by UTF-8 bytes. Preserve argument order and every scalar
exactly: no URL lowercasing, argument trimming, Unicode normalization or
executable-path resolution. Leave absent `environments` absent, distinct from
an explicit list. CCJ-1 canonicalizes object keys; strings must be scalars.

`server_sha256` is SHA-256 (prefixed `sha256:`) of the normalized SERVER's
CCJ-1 bytes, without enclosing object or trailing LF. The normalized declaration
expands shorthand, normalizes SERVER or preserves the package selector, and
represents absent `install` as `{}`. Its CCJ-1 SHA-256 is
`declaration_sha256`. Shorthand and expansion have equal server/declaration
digests. `install` changes declaration/plan identity, not server identity.
Resolved packages bind selected exact bytes and server digest in addition.
All option keys, including a key spelled `sig`, remain declaration data.
Neither normalized digest replaces schema-2 `manifest_sha256`, the CCJ-1
SHA-256 of the entire parsed declaring Skillfile, with no MCP expansion or
default insertion. Switching shorthand to its expanded object can change that
manifest identity while preserving normalized MCP identities; whitespace and
object-key ordering alone do not change the parsed-manifest hash.

## 8. Refusals and reserved later-stage conditions

| Code | Stage-A condition |
| --- | --- |
| Existing upgrade error | Unsupported schema 3 or machine-global schema 3; never downgrade. |
| `mcp_declaration_invalid` | Malformed JSON, NAME/arm/server/URL/selector/pin or resolved package declaration. |
| `mcp_package_not_allowed` | Outside the MCP package allowlist. |
| `mcp_package_allowlist_empty` | Warning permissively; refusal when hardened with package declarations. |
| `mcp_inline_approval_unsupported` | Any valid inline arm at stage A, regardless of purported approval. |
| `mcp_contribution_policy_refused` | Protected ownership action violates current policy/authority. |
| `mcp_native_entry_conflict` | Foreign/conflicting native record; no takeover. |
| `context_source_unsigned` | Required package signature is absent. |
| `context_source_signers_missing` | Required trusted signer configuration is absent. |
| `context_version_mismatch` | Selected package version contradicts the required selection. |
| `source_allowlist_empty` | Hardened general-source policy requires a nonempty source allowlist. |

The four existing source diagnostics above are admitted verbatim in the closed
plan-row code enum: preserving the gate’s exact refusal avoids recoding it as
an unsupported pair. When enumeration is impossible, emit the declaration-level
diagnostic; retain refusals on independently determinable supported pairs and
null-code skips on known unsupported pairs.

`mcp_inline_approval_required` and `mcp_install_option_invalid` are reserved
for later inline admission and supported install-option contracts respectively;
stage A cannot emit them in place of its inline refusal or ignored-option rows.
`context-secret-material` remains a blocking audit class, not a malformed URL
catch-all. Existing source, signer, snapshot, store, read, transaction and
launch refusal conditions retain their distinct codes.

## 9. Conformance boundary

The [separate corpus](../conformance/skillfile-mcp-v1/README.md) checks strict
parsing, schemas, lexical/pin rules, normalized digests and a bounded semantic
model over explicitly supplied package/policy/native observations. Every
negative has a valid control and each new check has a narrowing control.
It does not fetch packages, observe filesystem ownership, execute a native
writer, contact endpoints or qualify launch isolation. Implementations must
prove those effects at their real entrypoints in disposable homes, with
tripwire runtimes and endpoints, before advertising support.
