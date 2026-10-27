# Proposed profile skill-plan conformance

This separate unreleased family accompanies the
[carrier/reconciliation proposal](../../protocol/profile-skill-plan-proposal.md)
and [closed schemas](../../schemas/profile-skill-plan-v1/README.md).
It changes no released schema, `conformance/v1` vector, manifest or release pin.

`baseline.json` is a neutral, complete version-5 lock with a narrowed Memory
command, a transitive context-only helper, and an unrelated drifting machine
declaration. Names and hashes are synthetic fixture identities. `packages`
contains normalized facts from hypothetical pinned manifests (requirements,
commands and admitted ref evidence), not real checked-out packages or a
runtime audit claim. `direct` includes the declaration object and separate
read-only installed observation. `runtime_lock_sha256` is the generation's
external binding; the two baseline digests are literal expected identities.
The optional `retained_members` fixture input models protected old-lock
preimages. Unrelated old members can remain in the new lock without entering
the selected plan; invented or rewritten retained members are rejected.
Context package facts come from the admitted immutable snapshot. Network
source/commit/directory and manifest version agree with the lock; state-backed
contexts instead match the core-v2 state hash and exclude network identity.
Recomputing lock hashes after a substituted context identity does not admit it.

`requested_outcome: slice-a-model` exercises the bounded Slice A model only.
The actual `profile-command-admission` and `managed-session-skill-cli` companions remain unallocated.
Adoption/completion vectors model authoritative companion records as
`unallocated`, `accepted`, or `qualified`; accepted-only and missing records
refuse, while a hypothetical fully qualified record is the positive control.
These inputs do not qualify either companion and are not caller bypass flags.

`cases.json` applies explicit edits to disposable copies of that fixture.
Each edit has a `path` of JSON member names/array indexes and either `value`
or `delete: true`. `rebind: true` recomputes plan and external lock bindings
after the edits, allowing graph errors to reach semantic validation. Binding
tamper cases use `rebind: false`. Expected outcomes are independently authored
contract data; the oracle does not generate them. The `negative` flag marks a
forbidden inference control that remains a successful selective operation,
such as unreadable unrelated state staying unknown rather than converged.

Expected `effects` are ordered abstract operations; `state` names the old,
new, or explicitly documented per-entry generation after successful recovery.
They prescribe what a future manager harness observes. They are not execution
logs. `unrelated_calls: []`, preserved preimages and selected-only convergence
apply even when unrelated installed bytes drift from their declarations.
`recover-*` cases inject a durable journal phase as input, not a real crash.
The compiler-failure input in those recovery cases establishes that recovery
does not attempt compilation. Real adapters need byte/kind/mode/link-target,
receipt, executable and daemon-identity inventories, not these abstract labels.

## Obligation inventory

Every numbered normative obligation has vectors in `cases.json` or
`schema-cases.json`; the publication tests enumerate all uppercase normative
occurrences and reject unknown or missing mappings. Representative paired
controls follow; the JSON `obligations` arrays are the full mapping.

| Obligation | Admitted control | Negative / forbidden outcome control |
| --- | --- | --- |
| PSP01 carrier / compatibility | `context-lock-v5-valid`, `legacy-1-valid`, `legacy-2-valid`, `legacy-4-valid` | Missing/unknown members, `legacy-*-reject-skill_plan`, `reader-not-opted-in` |
| PSP02 complete pinned graph | `runtime-narrow-transitive`, `overlap-alias-ref`, `context-{explicit-root,directory,state}-matches` | `context-member-mismatch-*`, `context-package-mismatch-*`, `context-state-mismatch`, mixed state/network identity, duplicate package, missing/cyclic/unreachable graph and member/provenance cases |
| PSP03 modes, refs, selections | `mode-full`, `mode-context`, `mode-runtime`, `default-mode-full` | `selected-missing`, `selected-git`, empty/duplicate/unsorted narrowing and invalid ref/mode shapes |
| PSP04 edge union and exact surfaces | `overlap-full-union`, `context-plus-narrow-runtime`, `runtime-selection-union` | `selected-git`, `inactive-command-does-not-collide`; the narrowing control plant detects widening |
| PSP05 plan and lock binding | Literal `baseline.json` digests and digest-sensitivity test | `bad-plan-digest`, `bad-runtime-binding`, `tampered-selection-digest`, `prepare-receipt`, forbidden runtime fields |
| PSP06 pinned lifecycle | `admitted-tag-pinned-reuse`, `exclusive-use`, `exclusive-sync`, `exclusive-repair`, `status-read-only` | `moved-tag-refuses`, `legacy-runtime-*`, `changed-direct-provenance` |
| PSR01 selected ownership | `runtime-narrow-transitive`, `retained-lock-member`, `stale-owned-only`, `stale-shared-retained` | `unproven-extra-member`, `rewritten-retained-member`, `stale-ownership-unknown`; global-reconciliation plant detects unrelated effects |
| PSR02 drift reporting | `unrelated-in-sync`, `runtime-narrow-transitive` | `unrelated-unknown`, `unrelated-drift-absent` preserve unknown/absent distinctions |
| PSR03 exact overlap constraints | `overlap-full-union`, `overlap-alias-ref` | `overlap-conflict-source`, `overlap-conflict-commit`, `overlap-conflict-directory` |
| PSR04 command preflight and companion gate | `case-sensitive-neighbor`, `inactive-command-does-not-collide`, `reserved-case-sensitive-*`, hypothetical `protected-command-adoption-qualified-model` | Selected/retained/case-alias conflicts, unmanaged destination, `reserved-name`, `reserved-alias-*`, unallocated/accepted-only protected-command and combined adoption requests |
| PSR05 preparation / transaction | `runtime-narrow-transitive`, all `recover-*` phase controls, `handled-adapter-conflict`, `partial-adapter` | `prepare-*`, `recover-corrupt`, `status-pending-recovery`; compilation and publication order is explicit in expected effects |
| PSR06 exclusive live routing and companion gate | `exclusive-*`, `inactive-routing-unchanged`, `scoped-use-routing-unchanged`, hypothetical `managed-session-adoption-qualified-model` | `routing-{missing,mismatched,unknown,other-profile}-{first-activate,install,update,use,sync,repair,recover}`, unallocated/accepted-only managed-session and combined adoption requests |

## Tools

Install the repository's `requirements-dev.txt`, then run from its root:

```sh
python3 tools/profile_skill_plan.py
python3 -B -m unittest discover -s tools -p 'test_profile_skill_plan.py' -v
make validate
```

The standalone entry validates the complete schema and semantic corpus.
The tests add bounded plants that drop digest verification, widen command
selection, admit context narrowing, introduce a global-install effect, ignore
context pin agreement, and check reserved prefixes with the wrong case rules.
Each plant fails at its intended published case through the same corpus entry;
unrelated setup failures do not satisfy the control.
Existing `make validate` / hosted unittest discovery executes these checks;
no shared validator dispatch or generator registration is changed in this lane.
Inputs stay in this namespace. Transient logs belong in `.temp/`.

These are specification consistency checks. No manager, compiler, service,
enrollment, live routing supervisor, adapter, crash recovery or platform runtime
is qualified. Real install witnesses and the accepted implementation coverage
gate remain prerequisites after specification-owner acceptance.
