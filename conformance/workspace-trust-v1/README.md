# Workspace trust A1 conformance, revision 1

This unreleased corpus adopts [environments section 7.10](../../protocol/environments.md#710-workspace-trust-ledger)
and [Decision 0026](../../decisions/0026-workspace-trust-ledger-and-bindings.md).
It is independent of frozen rc.14 schemas, manifests and candidate pins.

[`schema-cases.json`](schema-cases.json) contains positive and negative private
record instances; [`vectors.json`](vectors.json) contains independently stated
step-by-step verdicts over synthetic facts. The executable specification oracle
is `tools/workspace_trust.py`. The real repository publication entry is
`tools/validate.py:validate_workspace_trust`, dispatched by `make validate`.
Every step compares diagnostics, active grants, binding references, installed
bindings, authorization, pending cleanup and list output, then validates all
resulting private records. Named tests are `test_vector_<name_with_underscores>`
in `tools/test_workspace_trust.py`.

| CIP test-plan row | Positive controls | Negative controls |
|---|---|---|
| `env trust add/list` scope | explicit-scope-and-list; nonrepository-explicit; verified-absent-ledger | reject-*; ledger-*; unknown-environment; blank-reason |
| Profile add/context extraction | context-extract; multi-environment-bind; bind-grant-root-valid-controls; bind-identity-no-remote/sole-remote/origin-preferred | review-bind-home-root; bind-home-source-root; bind-filesystem-root; bind-grant-root-link-final/link-ancestor/kind/missing; profile-not-environment-scope; bind-nonrepository/linked-source/missing-source/source-outside/no-environments/one-bad-environment; bind-identity-* failure cases |
| Resolve identity check | ordinary-commit; subdirectory-launch | root-changed; remote-changed; same-remote-new-root-commit; identity-unknown; exact-path-only; failed-launch-selection |
| Binding removal | last-binding-removal; independent-events-survive | removed last reference cannot resolve; other binding/environment/explicit/launch remain |
| `env trust remove` | remove-missing-directory; new-event-after-revoke | trust-remove-retains-bindings; remove-alias-refused; remove-broad-refused; no renewal by repair/update/replay |
| Transaction retry | bind-retry-idempotent | multi-bind-failure; transaction-read-failure; revoke-retry-never-restores |

Install the existing repository dependency set, then run standalone processes:

```bash
python3 -m pip install -r requirements-dev.txt
python3 tools/workspace_trust.py
python3 -B -m unittest discover -s tools -p 'test_workspace_trust.py' -v
python3 tools/check_workspace_trust_controls.py
python3 tools/check_workspace_trust_controls.py --mutant profile-scope
python3 tools/check_workspace_trust_controls.py --mutant final-component-only
python3 tools/check_workspace_trust_controls.py --mutant remote-only
python3 tools/check_workspace_trust_controls.py --mutant source-path-only-bind
make validate
make regenerate-check
```

The three required individual mutant commands are **expected red, exit 1** for a named
assertion failure. The summary also checks `profile-add-only-removal` and `active-only-replay`,
covering context-extract reference removal and revoked-transaction replay. Those
individual `--mutant` commands likewise expect exit 1. Its two extra positive
controls and the home-root regression/ordinary-root controls must pass before mutation.
The `source-path-only-bind` control retains source admission but omits admission
of the resulting repository-root grant. `test_vector_review_bind_home_root`
must fail: a valid source below home cannot grant the home root. This control
also expects exit 1 individually. The summary returns 0 only when all six assertions
fail without setup errors or skips. It prints mutant, narrowing, named failing
test and survivor bound. The link control retains final-link rejection but
admits a linked ancestor; the identity control retains remote equality but
admits replacement history. They are not delete-only mutants. The publication
plant test changes one cross-environment expected list through the real
publication entry, which must reject that exact vector.

The facts are deliberately synthetic: `components` records observed component
kinds, `repository` records readable root/remote/root-history observations,
`ledger` and `transaction_read` distinguish successful/absent reads from failed
ones, and `commit` describes a bind transaction outcome. `head`/`branch` in the
ordinary-commit control are non-identity observations. `repository: null` means
known non-repository, not failed discovery. All names, users, URLs and paths are
fictional. A cleanup failure models durable revoked authority plus a pending
obligation only; no vendor file is read, edited or claimed clean.

The bind root-admission vectors cover both triggers and single/multiple
environments, first with empty state and then with an unrelated installed
binding and its two grants. Refusal preserves the full private state, including
transaction IDs. Home-root and filesystem-root grants report
`workspace_trust_path_invalid`; separate root link, kind and missing-path
observations exercise the other root admission rules. Ordinary repository
roots with file sources remain valid. Optional `repository.components`,
`repository.kind` and `repository.path_read` describe root-specific synthetic
observations; when omitted, no-link observations follow the checked source
chain, with the root modeled as a present directory. They are not ledger fields
or filesystem probes. Repository identity is still checked independently.
`bind-grant-root-unavailable` retains the repository-unverifiable diagnostic for
missing/null root observations, with unchanged empty and populated state.

This suite measures specification consistency and record admission. **Runtime
cases: unrun.** It cannot prove no-follow OS traversal, race safety, Git discovery
without hook execution, permission enforcement, durable fsync/journal recovery,
concurrency, native projection or actual launcher refusal. Consumers must drive
the six rows through their production entries before claiming those behaviors.
A2 owns qualified projection/owned-key cleanup; A3 owns derivatives and task-board
hints. The private record is never included in any portable carrier; frozen
manifest/lock/marker/fragment positive controls reject its injection. Export and
snapshot implementation enforcement still needs production-entry qualification.

Local logs belong in `.temp/`. Worker handoff records exact commands, real exit
codes, source identity, coverage and open qualification gates.
