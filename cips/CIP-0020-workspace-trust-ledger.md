# CIP-0020: Workspace trust ledger for managed homes

- **Status:** Adopted in part (A1)
- **Accepted:** 2026-10-17, operator-approved direction in TASK-261017-2qvl57; implementation and adapter qualification are separate work.
- **A1 adoption:** [Environments §7.10](../protocol/environments.md#710-workspace-trust-ledger) and [Decision 0026](../decisions/0026-workspace-trust-ledger-and-bindings.md) adopt sections 1–3 and ledger/reference revocation from section 6; private record v1 and executable specification vectors are published. A2 (projection/adapters) and A3 (derivatives/task-board hints) remain deferred; no implementation qualification is claimed.
- **Policy-grant amendment (2026-10-27):** Section 2.1 and [Decision 0031](../decisions/0031-policy-derived-workspace-trust.md) publish the Q1 policy-derived consent contract, a separate private event schema and paired specification vectors. Environments integration and production implementation/qualification remain separate; this amendment does not activate an adapter.
- **Owner:** Curator maintainers; decision: operator
- **Created:** 2026-10-17
- **Related:** TASK-261017-2qvl57 — cip-workspace-trust-ledger; STORY-261017-cgq25o — workspace trust; [CIP-0014](CIP-0014-managed-home-snapshots.md) (snapshot boundary)
- **Affects:** [Environments](../protocol/environments.md) §§7.4, 8.3–8.4.1, 9 and resolve/repair; Curator managed-home adapters; task-board workspace admission

## Summary

Curator owns workspace trust for managed homes through a machine-local ledger
of exact absolute paths, scoped by environment and attributed to an operator
action. Explicit grants, launching Curator in a directory, and binding a
profile or extracting agent context from a repository record distinct events.
An operator-approved policy can supply a separate `policy-grant` for an exact
registered checkout; it never impersonates an operator's `explicit-grant`.
Resolve and repair project valid grants into Claude and Codex managed homes,
without taking ownership of unrelated tool state. Trust does not propagate by
path prefix; only directories created and recorded by Curator tooling can
inherit a repository grant. The private records below are not portable wire
extensions and establish no implementation or runtime qualification.

## Motivation and user stories

An operator who binds a repository-local profile or extracts its agent context
has already chosen that repository as agent input. Requiring a second trust
prompt for the same repository loses that intent. Recording implicit consent
at bind time makes the decision inspectable and revocable instead of relying
on whichever native tool last wrote its configuration.

An operator needs the same workspace selection to reach Claude and Codex,
without trusting unrelated repositories or silently transferring consent to a
replacement repository at the same path. A task-board story worktree created
by Curator tooling inside that repository should be usable without trusting
all directories with a similar name. Removing a profile binding should remove
only the trust that binding supplied, while another active binding keeps its
grant and native tool decisions remain intact.

## Current state

The baseline is curator-spec `9dfc557`, [environments](../protocol/environments.md)
§7.4: Claude's managed `.claude.json` starts with a minimal onboarding seed;
repair adds a project entry per literal launch directory and records seeded
paths. Codex's `config.toml` is a one-time native seed, with separately versioned
MCP filtering. Neither seed is a portable profile trust ledger.

Sections 8.3–8.4.1 require recorded ownership, no writes through links and
failure to read distinguished from absence. Section 9 installs and removes
profiles but does not define repository-binding trust. Those disciplines are
inputs to this design, not evidence that the proposed commands already exist.
The vendor facts below are inherited from §7.4; no implementation-source
inspection or new vendor execution probe was performed for this proposal.

## Design

### Options considered

| Option | Mechanism | Benefits | Costs and security limits |
| --- | --- | --- | --- |
| Native tool state only | Continue trusting copied seeds and interactive prompts | No new ledger | No environment-scoped provenance or binding revocation |
| Prefix grants | Trust a common ancestor or directories by worktree name | Fewer entries | Grants unrelated repositories and attacker-created directories |
| Machine-local exact-path ledger (selected) | Record grants, binding references and per-key projection ownership | Inspectable scope, identity lapse and bounded revocation | Requires reconciliation and version-qualified adapters |

### Recommendation

Adopt the exact-path ledger and the following contract. The requirements here
are the accepted target; the released environments rules remain the baseline
until a separately tracked adoption publishes its carriers and conformance
cases.

### 1. Ledger and provenance

The ledger MUST live in private machine-local Curator state, outside portable
profiles, package snapshots, locks and exported managed-home snapshots. A
portable profile MUST NOT supply, import or reactivate a grant. This is a
separate ledger from the environment-surface marker in §8.3; a seeded path
alone is not evidence of operator consent.

Every grant records:

| Field | Required meaning |
| --- | --- |
| `grant_id` | Stable machine-local event identifier for reference and revocation |
| `environment` | One adapter identity, such as `claude_code` or `codex_cli`; no wildcard |
| `path` | Exact absolute existing directory path, validated without following links; never a prefix expression |
| `repository` | For a repository path: checked root path, primary remote URL and root commit identity, as defined below; absent only for an explicitly admitted non-repository directory |
| `event` | In the original private record v1, exactly `explicit-grant`, `implicit-launch` or `implicit-bind`; `policy-grant` uses the separate §2.1 carrier |
| `operator` | OS user identity (stable local user ID and user name); additionally the operator public-key identity when a signed action is used, never a private key |
| `time` | Grant time as an RFC 3339 UTC timestamp |
| `reason` | Nonempty operator-supplied reason for explicit grants; a generated description of the launch or binding action for implicit grants |
| `binding` | For `implicit-bind`, stable binding ID, profile identity and trigger (`profile-add` or `context-extract`) with the repository-local source path |
| `state` | Active, revoked or lapsed, with transition time and reason retained for provenance |

Repository identity is the tuple (checked absolute root path, primary remote
URL, root commit). Inspect the path and every component with no-follow
semantics before repository discovery; discovering a realpath through a link
and trusting that realpath is forbidden. Obtain repository metadata without
executing repository hooks or configuration-defined commands. The primary
remote is `origin` when present, otherwise the sole configured remote; an
ambiguous remote selection refuses. Record an explicit no-remote value for a
repository with no remote. URLs MUST be credential-free; reject embedded
credentials rather than persisting them. The root commit is the full object
ID of the unique root ancestor of HEAD, not the moving HEAD commit; no commit,
multiple roots or an incomplete history that cannot establish it refuses.
Normal commits and branch switches with the same tuple do not lapse a grant.

Before each use, recheck the tuple. A different repository root, primary
remote or root commit at the same path lapses the grant and every derivative;
repair MUST NOT silently rebind it. An unreadable or indeterminate identity
is unknown and refuses use, never evidence of equality or absence. A fresh
operator grant or a new successful binding action is needed after a lapse.
These identity fields do not detect a byte-identical clone or malicious code
within an otherwise identical repository; this is consent provenance, not
content attestation.

### 2. Commands and consent events

```text
curator env trust add <env> <path> --reason <text>
curator env trust remove <env> <path>
curator env trust list <env>
```

`add` records an `explicit-grant` after validating the environment, exact path
and applicable repository identity. A concrete non-repository directory can
be explicitly granted (or granted by an actual launch there), but cannot be
a bind source or an inheritance parent. Reject filesystem roots, the user's
home as a blanket workspace grant, wildcards, prefix/range expressions,
relative paths, missing paths, non-directories and any symlink component;
never expand a broad operand into many grants. An exact ordinary directory
does not authorize its existing or future descendants.

A successful Curator launch selection records `implicit-launch` for its exact
validated working directory and selected environment. Failed selection or
failed path admission creates no grant. For repository directories, capture
the containing repository identity; a launch from a repository subdirectory
does not itself grant the repository root. This replaces an unrecorded
launch-directory seed only when this CIP is adopted.

`list` reports grant IDs, exact paths, environments, events, operator/time,
reason, repository tuple, binding references, derived paths, validity and
projection/revocation conflicts. It is read-only. An unreadable ledger is an
error, never an empty list. Diagnostics and stored provenance MUST exclude
credentials and secret URL components.

### 2.1 Policy-derived grants (Q1 first slice)

#### Authority and boundary

The operator role owns project trust, permissions and sandbox policy, hooks,
credentials and memory-off. A keeper MAY exercise that role through Curator
commands only under the owner's authenticated approval. The command records
both the approving operator principal and the operator/keeper actor of that
approval command. Neither a role string in a request nor a package's
signature proves authority.
A package, profile, dependency, project file, peer message or ordinary launch
MUST NOT create, widen, import or renew this authority. No human config edit,
vendor TUI response or automated prompt keystrokes are part of this path.

This slice grants only exact project trust and digest-listed hook consent.
It grants no project-item approval, permission, sandbox bypass, credential
access or memory setting. The owner-selected default of unattended lanes
without the vendor sandbox is a separate runtime-policy decision, not a
consequence of `project_trust: true`. Its launcher mapping is outside this
amendment. The launcher MUST apply the current authorized result at every
start, resume or restart, before starting the provider.

The policy is private operator state, outside packages, profiles, locks,
snapshots and exports. Changes MUST go through an operator-authorized Curator
command with an authenticated approval reference and audit trail. Same-UID
file ownership cannot prevent a sandbox-bypassed process from tampering with
this state. Until the CIP-0024 protected trust boundary is deployed, this is
an explicit residual integrity limitation, not an isolation guarantee. A
record's issuer fields are provenance; validation MUST establish authority
against protected operator state, not accept those fields as a capability.

#### Policy binding and event schema

Each approved entry has a stable `entry_id`; repository root commit and one
canonical destination; accepted credential-free remote spellings; exact
environments and lane identities/classes; `project_trust`; allowed hooks;
operator approval, time and reason; and `review_by`. Empty hooks allow no
hook consent. The entry digest is lowercase SHA-256 of CCJ-1 bytes of the
complete approved entry, including all these scope, approval and expiry
fields, excluding only a top-level `sig` as CCJ-1 specifies. It is not a hash
of a policy ID, path, selected fields or the whole unrelated policy store.
Duplicate IDs, ambiguous entries, unverifiable authority and incomplete reads
MUST refuse; they MUST NOT select a convenient match.

The closed [policy-grant event schema](../schemas/workspace-trust-policy-grant-v1/README.md)
defines `workspace-trust-policy-grant-v1`. It is additive private state, not
an extension to `workspace-trust-record-v1` or any released portable carrier.
An implementation MUST retain the distinction when reading, listing and
revoking a mixed ledger. An unsupported event fails closed; it MUST NOT be
downgraded to `explicit-grant` or silently ignored as absent consent.

| Event field | Required meaning |
| --- | --- |
| `record`, `event`, `grant_id` | Carrier `workspace-trust-policy-grant-v1`, event exactly `policy-grant`, stable private event ID |
| `policy` | Exact `entry_id` and `sha256` of the complete approved entry |
| `subject` | Registered `checkout_id`, registration digest, exact no-follow checkout `path`, §1 `repository` tuple, and `canonical_destination` |
| `identity` | Registration `root_identity`, one exact `environment`, and concrete `lane_id`; no wildcard |
| `surfaces` | `project_trust` boolean and a unique-by-`hook_id` list of `{hook_id, sha256}`; each digest binds the full effective hook definition, including executable, arguments, trigger and execution-affecting settings |
| `issuer` | Role exactly `operator`, approving `principal_ref`, immutable `approval_ref`, and approval-command `actor` (`operator` or `keeper`, with principal reference) |
| `time`, `review_by`, `reason` | UTC grant time, policy review deadline and nonempty reason; grant time cannot predate approval and deadline MUST equal the approved entry's deadline |
| `state`, `state_history` | Current status, time, reason and transition actor, retaining prior transitions; revocation always carries an operator issuer and approval reference |

`sha256` members are 64 lowercase hex characters. Times use UTC RFC 3339.
State begins `active` at `time`; transitions are `active -> revoked`,
`active -> lapsed`, optionally `lapsed -> revoked`, never reactivation.
Times are nondecreasing. Automatic lapse has `by: null`; operator revocation
has `by: issuer`. The initial state attributes the approving issuer. A new
operator approval creates new provenance, never rewrites an old event.

The registration digest and `root_identity` bind the protected registration
and retained filesystem identity from project-context §2. `path` equals the
registered checkout root, not a normalized alias, descendant or reused path.
Recheck its no-follow identity and the full §1 repository tuple at each use.
An absent/changed/unreadable registration is not a policy match. Policy
consent proves which approval applies, not repository ownership or code
authenticity; ordinary commits with unchanged identity do not lapse it.

Canonical destination is the closed tuple `transport` (`https` or `ssh`),
lowercase `host`, explicit integer `port`, and absolute `repository_path`;
SSH additionally requires `user` and a nonempty set of SHA-256 host-key
fingerprints. Paths have no dot components, repeated separators, percent
escapes, query or fragment. The first slice admits only direct canonical-host
URL spellings: `https://host[:port]/path` or `ssh://user@host[:port]/path`,
omitting default port 443/22. It refuses aliases, SCP shorthand and equivalent
but differently spelled operands rather than normalizing them into consent.
Wider spelling support requires a separately qualified evaluator. Neither
Git `insteadOf` nor SSH configuration may redirect even a directly named
host. Establish the effective destination and pinned SSH host key without
executing hooks/config commands or making a discovery network connection;
refuse `Match exec`, `ProxyCommand`, `ProxyJump`, `KnownHostsCommand`,
unverifiable routing or an unqualified evaluator. The host pin is checked
again by the eventual transport. Merely parsing a URL establishes none of
these runtime facts.

#### Admission, recording and audit

Curator derives the event automatically from an already approved protected
entry; it does not require another owner confirmation on each launch. The
`issuer` refers to the authenticated policy approval, not the launching agent
or a fabricated contemporaneous operator action. The approval's actor and
digest-bound scope MUST remain verifiable from private command audit state.

Before preparation and every start/resume/restart, Curator MUST re-read the
policy, registration, ledger and ownership journal under the mutation lock;
validate operator approval, digest, deadline, exact checkout, repository and
canonical destination; and match the environment and lane. Granted surfaces
MUST be a subset of the approved entry. Every effective hook definition AND
every existing native hook approval in the selected home MUST be accounted
for by an exact listed hook ID/digest, including when the list is empty.
Package-provided requests cannot authorize either trust or hooks.

Hook discovery, native approval state, merge, lookup, reload and revocation
MUST be qualified for the actual supported vendor release before unattended
trust is usable. Unknown, unreadable, foreign or mismatched hook state refuses
before provider start without deleting foreign bytes. This applies even to
an apparently hook-free checkout: no interim seed or hook-trust bypass flag
is allowed while the adapter cannot establish absence. A startup check does
not freeze later in-session hook discovery; qualification must record that
residual risk, especially for lanes without the vendor sandbox.

Each successful seeding leaves (1) the private `policy-grant`, (2) a per-home,
per-key journal entry binding its grant ID, policy ID/digest, exact inserted
value and preimage/ownership evidence, and (3) a sanitized launch output line
naming the policy/grant, checkout, environment and granted surfaces. The
ledger and journal are authoritative; output is informational. Persist grant
and ownership intent before projection using §6's recoverable transaction;
partial/interrupted preparation MUST NOT produce usable trust or start a
provider. Retries are idempotent for the same current authorization. An
unreadable policy, ledger or journal is an error, never empty state.

An unknown checkout with no matching policy entry MUST refuse an unattended
launch with `workspace_untrusted` before provider start. No existing native
seed, old grant or implicit launch/bind fallback can satisfy this required
policy admission. Recovery points to operator/keeper authorization through
Curator, not a vendor prompt. Refusals report a sanitized reason without
issuing a grant or writing projection state. Reasons include
`workspace_trust_policy_authority`, `workspace_trust_policy_digest`,
`workspace_trust_grant_revoked`, `workspace_trust_hook_digest`, and
`workspace_trust_destination_mismatch`; unreadable state and unqualified
adapters retain §7 diagnostics.

#### Revocation and inspection

Removing OR editing an entry revokes every grant derived from its entry ID,
even if the edit only narrows scope or changes a reason. Persist revocation
before cleanup; a partial failure cannot restore authority. Retain the old
policy digest, issuer, timestamps, surfaces and transition history. Expiry at
`now >= review_by`, registration/filesystem identity change, or repository
tuple change lapses grants. Resolve, repair, restart and profile update MUST
NOT renew revoked or lapsed events; new approval is required.

Reconcile all touched homes under §6: remove only keys Curator inserted and
still owns, preserving unrelated/pre-existing/tool-written state. A changed
key, ambiguous attribution or unreadable home preserves bytes, records
cleanup pending and denies subsequent authorization. A key supported by
another independent current grant is retained, but that other grant cannot
bypass required policy admission. Retrying cleanup never regrants consent.
Revocation does not terminate an already running process.

Read-only inspection MUST show policy entries and their current digest/status,
derived grants including revoked/lapsed history, approving operator and actor,
exact registered subject, surfaces, all touched homes and pending cleanup.
Missing and unreadable state remain distinct; listing never repairs or grants.
Credentials, authenticated URLs and secret hook payloads MUST NOT appear in
diagnostics or exported audit summaries; show sanitized IDs/digests instead.

### 3. Implicit bind grants

When adding a profile from a repository-local profile path or Skillfile, or
extracting agent context from inside a repository, Curator MUST record trust
for that repository automatically as implicit consent at bind time. The
binding action identifies the selected environment(s); write a separate
environment-scoped `implicit-bind` grant for each selected adapter. An action
with no selected environment MUST require environment selection, never grant
all adapters. A downloaded dependency, transitive profile member, portable
profile import or unrelated process reading files is not a binding action.

Validate the source and enclosing repository without following links and
record all §1 provenance, including the event, OS operator, optional signing
key identity, time, source path, binding ID and repository tuple. Commit the
binding and its grant references together under the machine mutation lock;
failed or interrupted binding must not leave active trust without a binding.
Report the automatic grant and the exact environments and repository root.
No second trust confirmation is required for a valid binding action.

The grant covers the repository root and only §4 derivatives. It does not
cover arbitrary subdirectories, sibling repositories, every source of the
profile closure, or another environment. Each binding has its own reference;
repeating the same binding is idempotent, while independently added profiles
produce separate references. Resolve, repair and profile update do not mint
new bind consent or renew a lapsed or explicitly revoked grant.

### 4. Narrow tooling inheritance

An already trusted repository root may supply trust to an exact directory
that Curator's own tooling creates strictly inside that root. Curator MUST
record the creation operation, exact child path, parent grant and repository
identity, creating tool identity, time and directory identity in its private
machine state. A task-board story worktree qualifies only through this
Curator-owned creation record, not because its name resembles a story path,
its `.git` file names a trusted repository, or another caller asserts it was
created by tooling. An integration must record creation through Curator's
trusted local tooling boundary; repository-supplied files cannot mint it.

At use, recheck the parent's active environment-scoped grant and repository
identity, the no-link path containment and the child's recorded directory and
repository/worktree identity. Replacement, relocation, untrusted parent or
unverifiable creation evidence refuses inheritance. Pre-existing directories
and manually created lookalikes do not qualify. A valid child gets an exact
projection entry linked to the parent grant in the same environment, never
a prefix grant or an independent perpetual grant. Removing or lapsing the
last applicable parent grant invalidates its derivatives. Independently
recorded explicit child grants remain subject to their own validity.

### 5. Resolve, repair and version-qualified application

Both `env resolve` and `env resolve --repair` MUST evaluate ledger validity
and projection ownership for the selected profile/home and environment.
Bare resolve reports a missing or stale projection and emits no usable
fragment; repair applies valid grants under the repair lock. Existing valid
projections need no rewrite. Neither path can treat ledger read failure as
absence, reuse an identity-mismatched grant, or bypass an admission refusal.

| Adapter | Managed-home projection | Version and evidence bound |
| --- | --- | --- |
| `claude_code` | Merge only `projects[<exact path>].hasTrustDialogAccepted = true` in the managed `.claude.json` | §7.4 records minimal seed and literal launch-path behavior verified on Claude Code 2.1.261; ledger-driven reconciliation and revocation require qualification |
| `codex_cli` | Set only `trust_level = "trusted"` under `[projects."<exact path>"]` in the managed `config.toml`, using proper TOML key escaping | §7.4 records seed parsing on Codex 0.153.2; other member shapes are docs-confidence, including this trust projection; a trust entry does not lift the verified `exec` Git check |

Preserve all other keys, project entries and tool-written state. Claude's
`hasClaudeMdExternalIncludesApproved` remains a separate referenced-context
rule under §§5.3/7.4; trust consent does not grant that capability. Codex's
model, MCP, credentials, sandbox and Git admission policies are unaffected.
Seeded native trust entries remain tool-owned unless independent insertion
provenance proves otherwise; copying a seed is not an explicit ledger grant.

Adapters MUST name supported vendor versions and the confidence of each fact.
An unqualified version/shape refuses automatic projection with a qualification
hint; documentation confidence is not a passing runtime probe. Before adapter
activation, qualify merge, lookup and revocation on the supported release;
this proposal does not expand the verified version range. Use safe structured
edits and §8.3.1 no-follow atomic writes, never replace a whole seed from its
original bytes to insert or delete a trust key. Malformed, unreadable or linked
destinations stop before writes. Apply the same discipline to the private
trust ledger, creation records and projection journal.

Exactness here defines Curator authorization. It does not assert that a
vendor ignores ancestor trust or implements Curator's repository identity
checks. task-board must enforce the ledger decision before launching; native
vendor state alone is not an attestation of Curator trust. A snapshot or an
already running session is not refreshed by ledger reconciliation; the
snapshot/launcher contract remains separately owned by CIP-0014.

### 6. Revocation and shared bindings

Removing a binding removes its grant reference and reconciles only the
Curator-added projections supported solely by that reference. If several
profiles bind the same repository in the same environment, trust remains
until the last active binding reference goes. An independent explicit or
launch grant also remains until revoked or lapsed; a binding removal cannot
revoke another operator event. Other environments are unchanged.

`trust remove <env> <path>` explicitly revokes all grant events for that exact
path in that environment, including active binding references, and invalidates
its dependent derived grants. Existing bindings remain installed but revoked;
resolve, repair and update MUST NOT recreate their consent. A new explicit
grant or a new binding action can establish consent again. The command is
idempotent for an absent grant and does not require the former directory to
still exist; it uses the recorded exact path without traversing or trusting
it. Broad or symlink-alias operands still refuse.

The projection journal records, per managed home and exact key, whether the
key was absent before insertion, the inserted value, supporting grant IDs and
subsequent ownership conflicts. Curator MUST remove only a key it added and
still owns. Never remove a pre-existing/tool-written trust value, a whole
project table carrying other members, or unrelated bytes. A matching native
seed or tool value can satisfy vendor configuration but confers no Curator
ownership. A changed value or uncertain ownership is a conflict: preserve it,
revoke ledger authorization and report vendor cleanup pending, without
claiming the vendor trust was removed. Equal bytes alone cannot establish
that a tool has not independently rewritten a value; ambiguous attribution
must fail conservatively. No revocation promises to erase independently
written tool consent or terminate a running session.

Use a journaled transaction for grant/reference changes and owned-key
reconciliation across affected managed homes. If a home is unreadable,
revoke authorization durably, retain pending cleanup and report the failure;
subsequent repair retries only the recorded owned-key cleanup. Never report
successful projection cleanup after a failed read/write or let a partial
revocation restore an active grant. Directory creation and bind failures have
no unauthorized partial grant; retries must not duplicate references.

### 7. Refusals and task-board diagnostics

The following target diagnostics carry the environment, exact sanitized path,
failed check and recovery action; no refusal emits an authorized fragment.

| Condition | Diagnostic and expected action |
| --- | --- |
| Unknown or unsupported adapter | `workspace_trust_environment_unsupported`; select a supported environment |
| Relative, broad, wildcard, filesystem-root or blanket-home grant | `workspace_trust_path_invalid`; name one exact workspace directory |
| Symlink at the path or any component | `workspace_trust_symlink`; use the actual no-link path and grant separately |
| Add/launch/bind path missing or not a directory | `workspace_trust_path_missing` / `workspace_trust_path_kind`; no grant |
| Bind/inheritance requires a repository but none exists | `workspace_trust_repository_required`; no implicit grant |
| Root/remote/commit identity unavailable, ambiguous or unreadable | `workspace_trust_repository_unverifiable`; no grant or inherited authorization |
| Repository identity differs from recorded identity | `workspace_trust_repository_changed`; lapse and request fresh consent |
| Creation provenance absent or invalid | `workspace_trust_inheritance_refused`; explicitly grant the exact child if intended |
| No valid grant for the selected environment and exact path | `workspace_untrusted`; explicit-grant command hint |
| Ledger, creation record or projection journal unreadable/malformed | `workspace_trust_ledger_unreadable`; currency unknown, no empty-ledger fallback or writes |
| Vendor file unreadable/malformed, linked or ownership conflict | `workspace_trust_projection_conflict`; preserve tool state, report pending cleanup where applicable |
| Projection missing/stale on bare resolve | `workspace_trust_projection_stale`; run resolve with repair after consent is validated |
| Unsupported vendor release or projection shape | `workspace_trust_adapter_unqualified`; qualify the adapter before projection |

Task-board MUST continue refusing untrusted workspaces; it MUST NOT suppress
its check, self-mint trust or infer it from a trusted-looking name or vendor
file. Its refusal MUST point to this Curator command, with the actual selected
environment and exact path safely quoted:

```text
Workspace is not trusted for <env>. Grant it with:
curator env trust add <env> <path> --reason <text>
```

An unreadable trust decision is reported as unknown/error, never as trusted
or as a successful empty-ledger read. A path rejected for links, identity or
kind also reports that specific cause: the hint is not an instruction to
bypass the refusal. Curator owns grants; task-board consumes their validity.

## Security considerations

Treat repository contents and caller-supplied creation claims as untrusted.
Environment scoping and reference counting prevent consent crossing adapters
or disappearing while another binding still needs it. No-follow checks and
identity revalidation must be held through the operation with safe filesystem
handles or equivalent race-resistant primitives; a preflight `lstat` followed
by an unchecked open is insufficient. Keep machine records private to the
operator; do not export keys, credentials or authenticated remote URLs.

The ledger is an operator-consent record, not a sandbox, code signature or
replacement for package audit. A repository sharing the recorded remote and
root history can still change maliciously. Vendor-native ancestor semantics,
independent tool consent, active sessions and undetectable identical rewrites
are explicit bounds; task-board authorization does not rely on those proxies.

## Compatibility and migration

Retain released seed revisions, marker schemas and fragment bytes. Adoption
must publish its own versioned records and conformance cases; do not add
unknown members to released markers. Existing `seeded_projects` and native
Codex trust tables are not retroactively labelled implicit consent. Report
legacy tool-owned trust separately and establish ledger provenance through a
new valid launch, binding action or explicit grant. In particular, the old
literal-path Claude observation is not permission to follow symlinks under
this ledger contract.

Only the bounded per-key exception changes recurring seed behavior. Repair
cannot refresh unrelated seed bytes, take over tool state, automatically
migrate all native trust, or import grants from portable profiles/snapshots.
An unsupported consumer remains untrusted rather than falling back to broad
vendor trust. Installation and profile removal must coordinate reference
updates with the §9 lifecycle without changing package source identity.

## Specification changes

The original leaf filed the accepted CIP and its §7.4 adoption reference;
A1 subsequently published its private record and executable corpus. The
policy-grant amendment adds §2.1, its separate closed schema and
[paired corpus](../conformance/workspace-trust-policy-grant-v1/README.md),
without changing A1 record bytes, released carriers or environments text.
It claims no adapter implementation. Later adoption must integrate the
ledger/creation/projection record versions, the
§§8.3–8.4.1 ownership/read-failure integration, §9 bind/removal integration and
resolve/repair diagnostics with a Decision record under
[GOVERNANCE.md](../GOVERNANCE.md).

## Implementation plan

1. Publish this specification proposal and its §7.4 reference (this leaf).
2. Implement machine-local records and `env trust` commands with journaled
   bind/unbind provenance, exact environment scoping and identity checks.
3. Qualify Claude and Codex managed-home per-key reconcile/revoke adapters
   against pinned releases; retain their distinct evidence bounds.
4. Integrate recorded tooling creation and task-board refusal hints; add
   production-entry conformance and interruption tests before activation.

These are follow-up implementation leaves, not implementation delivered here.

## Test plan

The following are paired acceptance examples for future production-entry
tests. They are specification counterexamples, not results of runtime tests.
Each row names the required positive control and the forbidden outcome.

| Entry point / claim | Positive control | Negative case and expected result |
| --- | --- | --- |
| `env trust add/list` scope | Exact directory and explicit reason recorded for one environment | Broad, relative, missing, non-directory or symlinked path refuses without a new grant; another environment remains untrusted |
| Profile add/context extraction | Local repository source records root grant with binding, OS identity, time and full repository tuple | Non-repository, linked source or unverifiable identity refuses; failed binding leaves no active grant |
| Resolve identity check | New ordinary commit on same root history/remote remains valid | Different repository, changed remote/root commit at same path lapses; unreadable metadata refuses as unknown |
| Tooling-created directory | Recorded child of a currently trusted repository is admitted in the same environment | Manual lookalike, replaced child, symlink, external directory or untrusted parent gets no inheritance |
| Claude/Codex repair | Qualified adapter adds only the named trust key, preserving neighboring state | Malformed/linked destination or unqualified release refuses; bare resolve never claims an absent projection current |
| Binding removal | Two profile bindings keep trust after first removal, revoke after last | Removing one must not revoke the other environment or an independent grant; remove never deletes pre-existing/tool-written keys |
| `env trust remove` | Revokes root consent and derived grants; repeat is idempotent | Existing binding cannot silently regrant on repair; ownership/read failure preserves vendor bytes and reports pending cleanup |
| task-board workspace admission | Exact valid environment grant admits the workspace | Missing, lapsed, other-environment or unreadable consent refuses with Curator hint; vendor trust alone cannot bypass |
| Transaction retry | Successful bind and reconcile have one effective reference per binding | Interrupted bind never leaks a grant; interrupted revoke never restores authority or loses pending cleanup |

Future narrowing mutants should, for example, limit scoping to profile name
instead of environment, check only the final path component for links, compare
only remote while ignoring root commit, recognize children by name instead of
creation record, and delete an entire project table instead of the owned key.
The named production-entry tests must kill those mutants; removing a check
alone does not prove its bound. No such runtime mutants were executed here.

For this documentation-only leaf run the repository's schema/vector/link
validator, existing Python and Go tooling tests, deterministic regeneration
and whitespace checks. Existing reviewer tests must remain unchanged. These
checks establish repository consistency, not the proposed runtime behavior.

The §2.1 corpus pairs valid operator/keeper policy grants with package
self-grants, stale policy digest, revoked grant, hook digest mismatch,
unknown checkout and noncanonical destination. Additional cases cover expiry,
identity/scope drift, unqualified adapters, unreadable state and conservative
policy edit/removal cleanup. Its publication checker and bounded invalid-
verdict control establish executable specification consistency only; real
filesystem, authenticated approval, transaction recovery, SSH evaluation and
vendor execution remain implementation qualification obligations.

## Open questions for the operator

None for this accepted direction. Wire publication and supported-release
qualification are follow-up delivery gates, not permission to weaken the
scope, provenance or conservative ownership requirements above.
