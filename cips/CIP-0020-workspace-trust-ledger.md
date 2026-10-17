# CIP-0020: Workspace trust ledger for managed homes

- **Status:** Adopted in part (A1)
- **Accepted:** 2026-10-17, operator-approved direction in TASK-261017-2qvl57; implementation and adapter qualification are separate work.
- **A1 adoption:** [Environments §7.10](../protocol/environments.md#710-workspace-trust-ledger) and [Decision 0026](../decisions/0026-workspace-trust-ledger-and-bindings.md) adopt sections 1–3 and ledger/reference revocation from section 6; private record v1 and executable specification vectors are published. A2 (projection/adapters) and A3 (derivatives/task-board hints) remain deferred; no implementation qualification is claimed.
- **Owner:** Curator maintainers; decision: operator
- **Created:** 2026-10-17
- **Related:** TASK-261017-2qvl57 — cip-workspace-trust-ledger; STORY-261017-cgq25o — workspace trust; [CIP-0014](CIP-0014-managed-home-snapshots.md) (snapshot boundary)
- **Affects:** [Environments](../protocol/environments.md) §§7.4, 8.3–8.4.1, 9 and resolve/repair; Curator managed-home adapters; task-board workspace admission

## Summary

Curator owns workspace trust for managed homes through a machine-local ledger
of exact absolute paths, scoped by environment and attributed to an operator
action. Explicit grants, launching Curator in a directory, and binding a
profile or extracting agent context from a repository record distinct events.
Resolve and repair project valid grants into Claude and Codex managed homes,
without taking ownership of unrelated tool state. Trust does not propagate by
path prefix; only directories created and recorded by Curator tooling can
inherit a repository grant. This accepted direction ships no implementation,
new wire schema or runtime qualification in this specification-only task.

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
| `event` | Exactly `explicit-grant`, `implicit-launch` or `implicit-bind` |
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

This task files the accepted CIP, indexes it and adds an adoption reference
beside §7.4's launch-directory exception. It does not amend released schemas,
add normative conformance vectors, or claim an adapter implementation. Later
adoption must publish the ledger/creation/projection record versions, the
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

## Open questions for the operator

None for this accepted direction. Wire publication and supported-release
qualification are follow-up delivery gates, not permission to weaken the
scope, provenance or conservative ownership requirements above.
