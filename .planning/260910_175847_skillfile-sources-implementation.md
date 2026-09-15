# Approved Skillfile sources: implementation plan

Epic: `EPIC-260910-ohqchs`. Seven stories, fifteen implementation tasks. Planning only; implementation agents have not been dispatched. On 2026-09-15, publication of the accepted specification and this plan through a PR was authorized. Implementation remains paused by the user.

Specification input: `/Users/iv/Developer/ReluxWorks/curator-spec/.temp/STORY-260910-8fv3s5/worktree`; accepted CR2 task `TASK-260910-1xph2y`, candidate tree `4087f02f5459a96d1a03d78ddb343d82608df0e6`. Future implementation belongs in `/Users/iv/Developer/ReluxWorks/curator`, not the specification repository.

The shared authoritative board is `/Users/iv/Developer/ReluxWorks/curator/.task-board`. Always pass that absolute `--board-dir` when operating from this nested worktree; its relative configuration would otherwise resolve incorrectly.

## Canonical execution model: dependencies restored

On 2026-09-15, all 20 intended task-level dependency edges were persisted using the Curator-managed task-board from project-management main `b64f1237b90a14b3739c13b737a606c0b4eec90f`. Historical unrelated links were preserved. The canonical query now returns six story phases and no projection cycles for this epic. The initial one-wave snapshot is historical and superseded by [the recovered snapshot](260915_191704_epic-260910-ohqchs.md). Fibonacci points are relative scope estimates, not elapsed time. Graph readiness does not authorize execution or replace complete spawn admission checks.

```text
active:false
criticalPath:STORY-260910-197y84 > STORY-260910-1bhj0g > STORY-260910-3vxe3y > STORY-260910-20sx61 > STORY-260910-1s75e1 > STORY-260910-1cnwwp
elements:7
mode:children
scope:EPIC-260910-ohqchs
statuses:{"STORY-260910-197y84":"to-dev","STORY-260910-1bhj0g":"to-dev","STORY-260910-1cnwwp":"to-dev","STORY-260910-1s75e1":"to-dev","STORY-260910-20sx61":"to-dev","STORY-260910-24nyb1":"to-dev","STORY-260910-3vxe3y":"to-dev"}
waves:[["STORY-260910-197y84"],["STORY-260910-1bhj0g","STORY-260910-24nyb1"],["STORY-260910-3vxe3y"],["STORY-260910-20sx61"],["STORY-260910-1s75e1"],["STORY-260910-1cnwwp"]]
```

## Scope and task handoffs

### STORY-260910-197y84: skillfile-v2-model-and-selection

- **TASK-260910-24cuys — parse-opt-in-skillfile-v2-sources** (5 points). internal/manifest, skillspec, identity, protocoljson; capability admission and source union.
  Acceptance: Accept relative/absolute path, git URL and explicit repository sources with valid refs; preserve every v1 field including legacy source meaning; reject mixed arms, unsupported versions and malformed directories before I/O. Add schema-backed positive/negative and v1 regressions.
  Persisted dependency: none.

- **TASK-260910-3kvq02 — expand-deterministic-skill-collections** (5 points). internal/manifest, closure, identifiers; individual selectors and immediate-child collection expansion.
  Acceptance: Validate aliases and SKILL.md names; support literals or * and excludes without recursive globbing; fail missing named and invalid discovered members, traversal and name/version collisions; retain skill-level dependency units and deterministic ordering.
  Persisted dependency: TASK-260910-24cuys.

### STORY-260910-24nyb1: safe-immutable-local-acquisition

- **TASK-260910-14hsti — enforce-local-source-and-output-boundaries** (8 points). internal/snapshot, staging, privatedir and adapter destination planning.
  Acceptance: Canonicalize physical paths, symlinks and case semantics; distinguish authored agents from managed outputs; validate operator root_inputs; reject unsafe overlap before traversal and recheck at publication; protect unmanaged files. Path source . with a safe selected subdirectory remains valid.
  Persisted dependency: TASK-260910-24cuys.

- **TASK-260910-16k7xy — capture-and-store-local-package-snapshots** (8 points). internal/snapshot, hashing, contextstore or appropriate existing protected store.
  Acceptance: Capture admitted dirty/untracked filesystem bytes even inside Git; hash exact byte inventory and executable flags using all three normative vectors; freeze runtime/build/dependency inputs; fail capture races and missing snapshots; never synthesize a Git commit or use a live directory after capture.
  Persisted dependency: TASK-260910-14hsti.

### STORY-260910-1bhj0g: machine-repository-policy-and-acquisition

- **TASK-260910-1o9x1f — load-machine-owned-repository-endpoint-policy** (5 points). internal/config, identity, gitcred.
  Acceptance: Implement source-policy schema, exact canonical identity, one/two distinct endpoints, provider refs, order and pin. URL without policy attempts declared URL once; logical identity without entry fails; invalid/unreadable policy fails before network. Package inputs cannot introduce providers or commands.
  Persisted dependency: TASK-260910-24cuys.

- **TASK-260910-5nrmtt — apply-bounded-authenticated-transport-resolution** (8 points). internal/gitops, buildrepo, buildsource, gitcred; existing Git acquisition lanes.
  Acceptance: Use existing SSH wrapper/HTTPS credential broker and lane grammar; at most two attempts within total deadline; fallback only on positively classified availability/auth failures. TLS, host-key, ref, identity, integrity, audit, unknown and ambiguous 404 fail closed. Verify locked content and sanitized errors; no ambient unsafe Git config or secret persistence.
  Persisted dependency: TASK-260910-1o9x1f.

### STORY-260910-3vxe3y: package-lock-and-frozen-resolution

- **TASK-260910-1a75qd — implement-source-lock-model-and-validation** (5 points). internal/managerlock or dedicated package lock module, protocoljson.
  Acceptance: Persist Skillfile.lock.json with exact package identities and frozen selection; separate machine path binding from portable content identity; validate stale/malformed lock and package membership; distinguish all three source identity arms. Never confuse environment context lock with package lock.
  Persisted dependency: TASK-260910-24cuys.

- **TASK-260910-19w2aj — resolve-source-closure-and-explicit-refresh** (8 points). internal/closure, closuregraph, closureexec, install, snapshot and Git acquisition integration.
  Acceptance: Resolve selected local/Git packages and transitive dependencies into a deterministic locked plan. Install/launch use pinned membership and immutable bytes; only explicit resolve/refresh reselects. Missing locked snapshot fails; refresh catches runtime-only and build-only changes. Retain existing dependency conflict and root-only branch rules.
  Persisted dependency: TASK-260910-3kvq02, TASK-260910-16k7xy, TASK-260910-5nrmtt, TASK-260910-1a75qd.

### STORY-260910-20sx61: source-audit-runtime-and-build-integration

- **TASK-260910-hwxr26 — bind-source-audit-to-existing-assurance-gates** (8 points). internal/audit, registry, artifactpolicy, scriptpolicy.
  Acceptance: Validate source-audit-v1 identity/context/policy/evidence/time/decision bindings; keep it distinct from registry attestation. Required network attestation for local packages fails; preserve authorized pins, revocation and assurance checks before cache/compiler. Validate absent, malformed, stale and wrong evidence without weakening currentness.
  Persisted dependency: TASK-260910-19w2aj.

- **TASK-260910-17ps6u — materialize-local-runtime-and-command-dependencies** (5 points). internal/runtimestore, globalbins, capabilities, install, adapters.
  Acceptance: Install scripts/assets and dependency runtimes from immutable local snapshots with existing command, capability, protected runtime-store and shim semantics. Exercise an actual local skill with runnable script and dependency; refresh uses frozen replacement, never live links or arbitrary new hooks.
  Persisted dependency: TASK-260910-hwxr26.

- **TASK-260910-dufdai — implement-source-aware-build-receipts-and-cache** (8 points). internal/buildcache, buildsource, buildrepo, godriver and current supported build driver integration.
  Acceptance: Implement receipt v3 package identity wrapper/cache key for both local and external build arms. Preserve all existing declared/effective identities, locked commits, targets, substitutions and assurance. Preserve toolchain readiness/failure behavior; runtime/build input mutations invalidate required state; no prebuilt download or compiler bootstrap added. Test all external-evidence field mismatches and both arms.
  Persisted dependency: TASK-260910-hwxr26.

### STORY-260910-1s75e1: marker-migration-and-atomic-installation

- **TASK-260910-1xs0pj — migrate-install-markers-with-full-currentness** (8 points). internal/marker, audit, install status/currentness readers.
  Acceptance: Implement marker v5 and complete 25-field v4 migration. Preserve Git attestation and legacy substituted semantics where applicable; reject those fields for invalid local arms. New selectors cannot enable legacy substitution. Verify package/lock binding and all marker mismatch/evidence cases; summaries never authorize execution.
  Persisted dependency: TASK-260910-dufdai.

- **TASK-260910-3eu4cy — publish-source-installs-and-locks-atomically** (8 points). internal/transaction, install, adapters, runtimestore and repair/refresh integration.
  Acceptance: Publish lock, marker, runtime and adapters as one recoverable transaction; faults roll back consistently. Recheck physical output boundaries at write time. Status, repair and refresh enforce exact currentness and frozen inputs; protect unmanaged files and prove retarget/copy mutation failure paths.
  Persisted dependency: TASK-260910-1xs0pj, TASK-260910-17ps6u, TASK-260910-14hsti.

### STORY-260910-1cnwwp: source-cli-and-executable-conformance

- **TASK-260910-stbg4d — expose-source-workflow-and-actionable-diagnostics** (5 points). Existing cmd entry points, help and curator README; source opt-in, resolve/install/status/refresh/repair.
  Acceptance: Provide coherent existing-command UX with local/absolute/Git/collection examples and documented machine policy setup. Stable source/transport errors include sanitized remediation; launch never rescans live inputs. Label opt-in draft support accurately and retain released v1 behavior.
  Persisted dependency: TASK-260910-3eu4cy.

- **TASK-260910-1xya7x — execute-draft-source-conformance-and-end-to-end-scenarios** (8 points). internal/crossconformance and integration fixtures; consumer schema pinning and platform test lanes.
  Acceptance: Run all 102 draft schema cases, 3 snapshot vectors and 73 semantic cases against real production entry points, plus v1 regressions. Test local skill+script+compiled CLI+dependencies and broker-backed transport fixtures, transactions and OS path semantics. Record actual platform coverage, unsupported lanes and exact tested revision; do not claim release qualification from schema-only tests or alter frozen spec releases.
  Persisted dependency: TASK-260910-stbg4d, TASK-260910-5nrmtt.

## Conformance traceability

Every semantic case has a primary implementation owner below. The final conformance task executes all cases through production entry points; a case fixture carrying an expected result is not evidence that the manager implements it. Shared schema coverage: parser, lock, policy, snapshot, audit, marker and receipt owners each cover their wire models; final task runs all 102 schema cases and the three byte snapshot vectors.

| Semantic case | Primary task |
| --- | --- |
| `broad-root` | `TASK-260910-14hsti` |
| `managed-source` | `TASK-260910-14hsti` |
| `symlink-managed` | `TASK-260910-14hsti` |
| `case-alias` | `TASK-260910-14hsti` |
| `write-boundary-retarget` | `TASK-260910-3eu4cy` |
| `root-no-inputs` | `TASK-260910-14hsti` |
| `selector-escape` | `TASK-260910-3kvq02` |
| `unknown-alias` | `TASK-260910-3kvq02` |
| `missing-excluded-literal` | `TASK-260910-3kvq02` |
| `bad-wildcard-member` | `TASK-260910-3kvq02` |
| `duplicate-name` | `TASK-260910-3kvq02` |
| `frozen-membership` | `TASK-260910-19w2aj` |
| `capture-mutation` | `TASK-260910-16k7xy` |
| `frozen-copy-mutation` | `TASK-260910-16k7xy` |
| `local-git-dirty` | `TASK-260910-16k7xy` |
| `missing-audit-report` | `TASK-260910-hwxr26` |
| `strict-network-attestation-local` | `TASK-260910-hwxr26` |
| `missing-snapshot` | `TASK-260910-19w2aj` |
| `runtime-only-refresh` | `TASK-260910-19w2aj` |
| `build-only-refresh` | `TASK-260910-19w2aj` |
| `fallback-dns` | `TASK-260910-5nrmtt` |
| `fallback-auth-rejected` | `TASK-260910-5nrmtt` |
| `fallback-tls` | `TASK-260910-5nrmtt` |
| `fallback-host-key` | `TASK-260910-5nrmtt` |
| `fallback-integrity` | `TASK-260910-5nrmtt` |
| `fallback-identity` | `TASK-260910-5nrmtt` |
| `fallback-ref-moved` | `TASK-260910-5nrmtt` |
| `fallback-audit` | `TASK-260910-5nrmtt` |
| `fallback-unknown` | `TASK-260910-5nrmtt` |
| `fallback-policy-unreadable` | `TASK-260910-5nrmtt` |
| `fallback-http-404` | `TASK-260910-5nrmtt` |
| `pinned-auth` | `TASK-260910-5nrmtt` |
| `endpoint-identity-mismatch` | `TASK-260910-1o9x1f` |
| `attested-network-current` | `TASK-260910-1xs0pj` |
| `legacy-substitution-current` | `TASK-260910-1xs0pj` |
| `legacy-substitution-strict` | `TASK-260910-1xs0pj` |
| `selector-substitution-forbidden` | `TASK-260910-1xs0pj` |
| `local-required-registry` | `TASK-260910-hwxr26` |
| `external-substitution-strict` | `TASK-260910-1xs0pj` |
| `external-only-current` | `TASK-260910-1xs0pj` |
| `attestation-evidence-absent` | `TASK-260910-hwxr26` |
| `attestation-evidence-unreadable` | `TASK-260910-hwxr26` |
| `attestation-evidence-malformed` | `TASK-260910-hwxr26` |
| `attestation-evidence-stale` | `TASK-260910-hwxr26` |
| `attestation-evidence-revoked` | `TASK-260910-hwxr26` |
| `attestation-evidence-wrong-name` | `TASK-260910-hwxr26` |
| `attestation-evidence-wrong-repository` | `TASK-260910-hwxr26` |
| `attestation-evidence-wrong-commit` | `TASK-260910-hwxr26` |
| `attestation-evidence-wrong-context` | `TASK-260910-hwxr26` |
| `attestation-evidence-wrong-key` | `TASK-260910-hwxr26` |
| `marker-plan-mismatch-registry` | `TASK-260910-1xs0pj` |
| `marker-plan-mismatch-status` | `TASK-260910-1xs0pj` |
| `marker-plan-mismatch-key_id` | `TASK-260910-1xs0pj` |
| `marker-plan-mismatch-substituted` | `TASK-260910-1xs0pj` |
| `marker-plan-mismatch-package` | `TASK-260910-1xs0pj` |
| `marker-plan-mismatch-lock_sha256` | `TASK-260910-1xs0pj` |
| `external-evidence-mismatch-repository` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-declared_identity` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-declared_locked_commit` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-declared_tag` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-effective_identity` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-object_format` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-commit` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-substituted` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-substitution` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-build_source` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-descriptor_target` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-execution_policy` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-cache_key` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-receipt_sha256` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-artifact_sha256` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-artifact_path` | `TASK-260910-dufdai` |
| `external-evidence-mismatch-input.package` | `TASK-260910-dufdai` |

## Board blocker recovery

The historical rejection is retained in `.temp/source-implementation-plan/mutations.log` and the linked correction brief. The installed task-board scopes new-edge cycle validation to the task graph; all 20 intended edges now exist and canonical planning succeeds. No historical links were removed and cycle validation was not disabled. The old unmanaged executable at `~/.local/bin/task-board` may still be selected by PATH; use the Curator-managed executable resolved for the current machine. On this machine it is `/Users/iv/.curator/global/bin/task-board`.

## Execution and review boundaries

- Stories are detailed and set to `to-dev`; leaf tasks remain unstarted. No agent allocation has been launched. Producers and independent reviewers should be selected explicitly at implementation preflight; the earlier Astra medium producer/reviewer requirement was fulfilled for the specification, and is not silently changed by this plan.
- Inspect current Curator implementation and accepted outcomes before creating task worktrees. Existing context-management, credential-broker and build behavior is a baseline to extend, not a backlog to redo. Preserve unrelated dirty work.
- Publication of the accepted specification and plan through a PR is authorized. Preserve its accepted candidate provenance; this remains an opt-in draft, not a published protocol release. Frozen v1 schemas remain unchanged. Consumer fixtures must record their draft source digest.
- Production coverage is currently absent for the 73 draft semantic cases. Cross-platform path/case/executable-bit and rollback behavior require actual platform evidence; report any unavailable platform as unverified.
- Existing compiler/toolchain readiness remains the baseline. This plan does not add prebuilt CLI downloads, compiler installation, registries, signatures or new OS distribution policies.
- Rules/knowledge, private/generated instruction files, MCP wiring/plugins and advanced repository aliases/mirrors/ports remain deferred in `UNRESOLVED_QUESTIONS.md`. They are not hidden acceptance criteria for this epic.

## Reproduce the plan

```bash
/Users/iv/.curator/global/bin/task-board --board-dir /Users/iv/Developer/ReluxWorks/curator/.task-board q 'plan(EPIC-260910-ohqchs, mode=children)'
/Users/iv/.curator/global/bin/task-board --board-dir /Users/iv/Developer/ReluxWorks/curator/.task-board plan EPIC-260910-ohqchs --save
```

## Task-board correction brief

See [Task-board dependency validation fix](260910_task-board-dependency-validation-fix.md) for the observed failure, graph semantics, acceptance tests and recovery procedure. This brief does not authorize implementation.
