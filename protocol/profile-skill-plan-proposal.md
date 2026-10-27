# Profile skill-plan carrier and selective reconciliation proposal

Status: **Proposed allocation; not adopted or released.** This document
proposes `context-lock-v5` and `profile-skill-plan-v1`. Acceptance by the
specification owner precedes implementation. It grants no installation,
activation, enrollment, or release authority. Published lock schemas 1 and 2
remain frozen. Retaining the unreleased schema-4 shape is a compatibility
proposal, not a pre-existing freeze.

The proposal narrows the profile bridge in [environments §9.4](environments.md#94-profile-scoped-skills-and-migration)
without changing [core §4.4](core.md#44-dependencies) dependency declarations.
It follows the lock allocation, reconciliation boundary and transaction
decisions in the accepted [profile skill runtime design](https://github.com/relux-works/curator/blob/05102ddb4f4911f25c49fee5ba55221a5dd16a3e/docs/design/profile-skill-runtime.md#owner-decisions).
It does not amend the existing global-operation or adapter exception rules.
There is no new dependency family or build hook. The command-admission and
managed-launch companions in section 5 are explicit prerequisites; this
carrier alone does not satisfy either owner command outcome.

## 1. Complete carrier

**[PSP01]** An opting-in writer MUST emit the closed
[`context-lock-v5`](../schemas/profile-skill-plan-v1/context-lock-v5.schema.json)
carrier. It retains the schema-4 context/MCP member, precedence and empty
Codex-settings meanings, adds required `skill_plan` and `skill_plan_sha256`,
and retains `hash_version: 2`. Skill members additionally require normalized
`directory` (including `.`). A reader lacking version-5/plan-version-1 support
refuses runtime enablement with `profile_skill_plan_required`; it does not
interpret the plan as a schema-4 lock. Schemas 1, 2 and 4 reject these fields.
The historical readers remain available for inspection and context behavior.

The plan contains three canonical arrays:

| Field | Meaning and order |
| --- | --- |
| `nodes` | All and only profile-reachable transitive skills, sorted by name. Each has `kind: skill`, name, canonical network source, full commit, normalized directory, `hash_version: 2`, and unprefixed core-v2 `content_sha256` of the selected package. |
| `edges` | Every incoming requirement, sorted by `(consumer.kind, consumer.name, provider)`. Consumer kind is `context`, `skill` or `machine`; its name identifies that package, or the directly declared skill for a machine edge. Each edge records provider, explicit defaulted mode, exact requested ref, and optional command narrowing. |
| `direct_constraints` | Only machine declarations whose names overlap the profile-reachable closure, sorted by name. Each records name, source, commit, directory, exact ref and `declaration_sha256`. Unrelated declarations remain outside this portable plan. |

An exact ref is `{kind: tag, value: <exact tag>}` or
`{kind: revision, value: <full commit>}`. A revision equals the provider's
commit. A tag's admitted resolution evidence binds that tag to this commit
under the existing source/signer policy; tag signatures and verification
posture remain in protected source-admission records, not portable locks.
`declaration_sha256` is `sha256:` plus SHA-256 of CCJ-1 of the original parsed
direct-declaration object, before source normalization/default insertion.
Its actual manifest bytes and enclosing global file stay unchanged.

**[PSP02]** The planner and every reuse path MUST validate complete graph and
pin agreement against the pinned packages and recorded overlapping direct
declarations: one identity per skill name; no duplicate node, edge or direct
constraint; no missing, extra, unreachable or cyclic skill; and no missing,
invented or changed requirement. Context-origin edges come from lock context
members; before consuming their requirements, the planner compares each
admitted context snapshot's canonical source, full commit and normalized
directory (`.` when omitted) with that member. A state-backed context instead
matches its core-v2 `state_sha256`, carries no source/commit/directory identity,
and uses its immutable admitted snapshot. The manifest version also matches
the member. Rehashing a substituted lock does not establish this agreement.
Skill-origin edges come from pinned skill manifests. Machine edges
are exactly the overlapping constraints, enter as `full`, and do not pull
unrelated machine roots into the closure. Skill lock members and plan nodes
agree on name/source/commit/directory; `required_by` is the sorted unique
package-consumer names, excluding synthetic machine consumers. Unrelated
pre-existing skill lock members are copied from the protected old lock as
opaque entries outside the selected plan, preserving pins and provenance.
During explicit version upgrade alone, an absent legacy root directory becomes
`.`; all other member fields stay identical. Every skill member is
either a selected plan node or such a retained entry; a new unexplained member
is invalid. Retention does not assert that its pin satisfies today's unrelated
direct declaration. Violations
refuse with `profile_skill_plan_invalid`. The root and non-skill closure keep
their existing validity rules. Path-selected packages retain the existing
link-free containment and per-package audit rules; this allocation introduces
no alternative acquisition path.

**[PSP03]** Each edge MUST retain its explicit `full`, `runtime` or `context`
mode and exact ref; `commands` is permitted only for runtime, is nonempty,
sorted and unique, and names only exported script/build commands. Missing or
system-only command names refuse with `profile_skill_command_invalid` before
build/publication. Omitted `commands` means all exported commands, not an
empty selection. Unknown fields and invalid ref/mode/selection shapes refuse
as `profile_skill_plan_invalid`. Array order is bytewise ASCII for identifiers;
the closed schemas admit no non-ASCII identifier extensions here.

**[PSP04]** Activation MUST be the union of incoming edges: `full` activates
context and every exported script/build command; `context` activates context
only; `runtime` activates all or its selected commands with no context from
that edge. A separate full edge dominates narrowing. Dependencies of every
reachable node expand with their own declared modes, including dependencies
of context-only nodes; modes are not inherited from a parent edge. System
commands remain prerequisites and never become exported shims. Only
context-active nodes enter prompt surfaces; only command-active outputs enter
the runtime generation. No synthetic full-mode Skillfile substitutes for edges.

## 2. Digest and lifecycle binding

**[PSP05]** A consumer MUST verify `skill_plan_sha256` equals `sha256:` plus
SHA-256 of the CCJ-1 bytes of the complete `skill_plan`, and bind the runtime
generation to the existing lock hash: `sha256:` plus SHA-256 of CCJ-1 of the
complete lock, including both new fields. There is no embedded lock hash and
no circular digest. Graph, refs, modes, selections, pins, directories and direct
provenance all participate; arrays are verified in canonical order before
hashing. Bad plan digest, supplied lock-binding mismatch, or runtime receipt
binding mismatch refuses with `profile_skill_plan_binding_invalid`. Artifact
paths, platform receipts, executable hashes and enrollment state stay outside
the portable lock in its protected runtime generation. Hash equality supplies
identity, not authority or signer proof.

**[PSP06]** `use`, `sync`, repair and status MUST consume the stored pins and
edges without resolving fresh refs or silently upgrading old locks. Runtime
enablement from a legacy lock reports `profile_skill_plan_required` and asks
for explicit update/reinstall; inspection and existing context-only operations
remain readable. Explicit install/update alone can create the new plan after
resolution and admission. Pinned reuse checks packages and recorded tag
evidence; an observed moved tag refuses `profile_skill_pin_changed` rather
than changing the pin. No network tag refresh is required merely for status.
A changed overlapping direct declaration requires explicit update and refuses
reuse as `profile_skill_plan_invalid`.

## 3. Selective reconciliation boundary

The selected set is the profile-reachable plan closure, including overlapping
machine constraints. Ordinary global reconciliation remains a separate
operator operation; there is no implicit `global install` bridge.

**[PSR01]** Profile installation/reconciliation MUST act only on the selected
closure and profile-owned outputs. It preserves the global Skillfile bytes,
unrelated direct declarations, installed targets, shims, markers, receipts,
service configuration and daemon identity. It performs zero unrelated
fetch/build/delete/service-control operations and never delegates to full
global reconciliation. Retained command inventory is read as opaque ownership
data, not fed to a compiler. The new lock copies unrelated pre-existing members
instead of dropping or re-resolving them; their protected generation/ownership
references remain live. A stale output formerly owned by this profile can
be removed only when no retained direct or other owner references it; unknown
ownership refuses with `profile_skill_ownership_unknown`. Shared ownership
retains the target and removes only the departing profile's reference.

**[PSR02]** Reports MUST distinguish selected-closure outcome from unrelated
drift. A read-only per-declaration inventory reports name, declared exact ref,
observed installed pin (or absence), and `in-sync`, `drift` or `unknown`.
Unreadable observations are unknown, never absent or converged. No source
resolution, build or repair runs to complete this inventory. Known drift is
preserved and reported even when selected installation succeeds; unknown
drift outside the selected set is nonblocking unless command ownership cannot
be established. A selective success makes no whole-machine convergence claim.

**[PSR03]** An overlapping direct constraint MUST unify with its selected
provider's canonical source/commit/directory, with full-mode activation added
to the incoming union. Different exact refs resolving to the same tuple are
compatible. Incompatible source, commit or directory refuses
`profile_skill_pin_conflict` before build/publication, naming both consumers,
their constraints and tuples. Neither declaration wins by priority, and the
global declaration is never rewritten to fit the profile.

**[PSR04]** Preflight MUST reject a selected active command colliding with
another selected or retained provider (`profile_skill_command_conflict`), an
unmanaged destination (`environment_surface_unmanaged_conflict`), or a reserved
`curator-*` name (`environment_reserved_command_name`). The comparison follows
the target platform's path/case-alias rules. An inactive command does not
collide. All preflight refusals preserve every live preimage and publish nothing.
This bounded check is not the complete protected-command policy. Acceptance
of the owner's broader command-safety requirement depends on the accepted
`profile-command-admission` companion below; command-publication adoption
also depends on its runtime qualification. Neither a successful abstract
Slice A vector nor carrier acceptance removes that gate.

## 4. Preparation, publication and isolated routing

**[PSR05]** Publication MUST follow successful source admission, strict audit,
ordinary trusted-driver validation, compilation and receipt verification for
the selected graph, before publishing its new lock. One runtime/record journal
coordinates the generation, lock, owned shims and current pointer. A preparation
failure preserves all live preimages; unreferenced verified cache entries are
not install success. Source, audit and driver failures retain their ordinary
diagnostics (`context_source_signer_rejected`,
`audit.capability.network-undeclared`, `unsupported_build_driver` in the
corpus's bounded examples). This allocation proposes
`profile_skill_compile_failed` for a selected compiler failure, retaining the
underlying compiler diagnostic. It changes no signer policy.

For recovery the journal's durable phase selects the result:

| Phase | Successful recovery result |
| --- | --- |
| absent / preparing | Old complete runtime and records |
| prepared / committing / cleanup | New complete runtime and records |
| rolling_back / rollback_cleanup | Old complete runtime and records |

Unknown/corrupt recovery state reports `profile_skill_recovery_failed` and
keeps the domain closed. No successful result exposes a mixed runtime.
Recovery uses prepared artifacts without compiling or enrolling. Keep old
generations while referenced by an installed profile, rollback slot or journal.
Read-only status reports pending recovery and does not recover it.

The documented adapter exceptions remain exceptions: a handled unmanaged
in-place conflict after lock publication retains the new lock and verified
generation, restores touched in-place surfaces, preserves the unmanaged
surface and every other mutable preimage, and keeps old current routing and
shims. Other documented partial-adapter outcomes retain old machine routing
and report per-entry results. Neither exception permits compile-after-lock.
The corpus models the handled conflict separately from preflight refusal.

**[PSR06]** Every Slice A live publisher and recovery path MUST hold a
supervisor-issued exclusive routing-domain admission lock, revalidate it under
the manager lock, and refuse missing, mismatched, unknown or other-profile
consumer evidence with `profile_skill_routing_unproven` before changing live
state. The witness binds private manager/bin/cache identities, fixed PATH,
current profile and admitted consumers; consumer admission is serialized with
mutation. Machine switching drains old consumers. An ordinary home path,
process scan or empty lease is insufficient. Inactive preparation changes no
current routing; scoped use changes no machine shims. Slice B multi-profile
commands and launcher transport require the `managed-session-skill-cli`
companion below. Readiness and enrollment remain separate gates. Acceptance
of the owner's managed-session CLI requirement depends on the accepted
companion, and native/hosted adoption depends on its runtime qualification;
the fixed domain PATH witness alone proves neither delivery outcome.

## 5. Conformance and adoption

### Required companion allocations

This carrier proposal itself supplies neither companion nor qualification. The
specification owner/integration writer owns the shared amendment to
[environments §9.4](environments.md#94-profile-scoped-skills-and-migration);
the designated delivery owners below own its implementation and qualification.
These are required gates, not work represented as delivered by this proposal.

| Companion | Allocation owner and required amendment | Acceptance and adoption evidence |
| --- | --- | --- |
| `profile-command-admission` | curator-spec specification owner and L1 integration writer, with Curator's command-publication owner; amend §9.4 and PSR04 together | A versioned protected-name inventory with pinned aqua and mise registry inputs, POSIX/coreutils commands, shell builtins and platform tools. Specify completeness, provenance, inventory upgrades, target lookup/case/extension/alias rules and fail-closed handling of unknown platform evidence. Independently check every active export against the admitted base PATH, including actual executable resolution and unreadable/missing admission evidence, before publication. Protect names even if absent from that PATH; a dynamic PATH check alone is insufficient. Paired conformance covers `git`, `ls`, `sh`, `cd`, registry/platform names, target aliases, dynamic-only collisions, unreadable inventories/PATH and nearby ordinary names, with exact diagnostics and preserved preimages. Accepted normative allocation precedes implementation; real platform witnesses precede publication adoption. |
| `managed-session-skill-cli` | Jointly curator-spec, Curator, curator-run and the hosted session manager; amend §9.4's managed-home limitation and [§10.2](environments.md#102-the-launch-environment-fragment), with the Slice B fragment/runtime binding | The [native-first companion](profile-command-path.md) allocates receipt verification, PATH admission and per-launch provenance. No-export profiles get no prepend/refusal; Slice A non-current and hosted-without-carrier launches use explicit empty-root diagnostics without refusing for unavailable commands. Current-profile native delivery requires verified root/lock/plan/generation and final-child witnesses. Hosted active delivery needs a joint curator-run/session-host carrier and qualification; old carriers remain closed. Slice B adds immutable all-profile roots, concurrent command versions, leases and GC. Refuse invalid active bindings and dropped negotiated delivery; never borrow another profile's singleton or recompose ambient PATH. Combined completion/adoption remains gated on accepted companions and applicable real native/hosted/all-profile witnesses, including the D-PATH one-shot rules. |

The owner's combined protected-command and managed-session outcome stays open
until both companions are accepted and their applicable real-runtime witnesses
are qualified. An accepted Slice A carrier is only one dependency. A proposed
completion/adoption request lacking either required companion reports
`profile_skill_companion_required` without effects or publication. Qualification
records are supplied by the responsible acceptance/qualification authorities;
they are not user-supplied bypass flags. The corpus models these records as
abstract states to check the gate, and cannot establish their truth.

The [schema and semantic corpus](../conformance/profile-skill-plan-v1/README.md)
maps every numbered obligation to paired positive and negative vectors.
The specification oracle checks structural validity, graph/activation/hash
relations and abstract transition/effect decisions. It does not run Curator,
compile a fixture, touch a service or prove filesystem transaction recovery.
After allocation acceptance, the implementation gate needs real isolated
install/update/use/sync/repair/recovery witnesses, unchanged preimage inventories
and the accepted design's coverage gate. Passing specification data checks
does not lift that gate.

[Open allocation and adoption decisions](../conformance/profile-skill-plan-v1/UNRESOLVED_QUESTIONS.md)
remain explicit; none is answered by publication alone.
