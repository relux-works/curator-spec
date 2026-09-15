> Historical correction brief (2026-09-10). Recovery verified on 2026-09-15 using project-management main `b64f1237`: all 20 intended Curator task dependencies were persisted and the canonical plan now succeeds. See [the current implementation plan](260910_175847_skillfile-sources-implementation.md). The original observations and requested acceptance criteria below are retained as history; this notice does not claim every independently listed task-board acceptance test was rerun.

# Task-board: leaf dependency validation and container projection cycles

Status: implementation brief; implementation has not started.

## Objective

Allow valid task dependencies to be added without rejection caused by unrelated historical graph defects or by cycles introduced only by grouping tasks into stories/epics. Continue rejecting actual task dependency cycles. Keep canonical planning truthful when tasks from the same story must execute in different waves.

This change belongs in the task-board source repository. Do not implement a Curator-local workaround, edit board storage directly, remove historical dependencies to make tests pass, or disable cycle validation globally.

## Observed failure and evidence

Observed CLI: `task-board 0.24.3-335-gac9044a5` (commit `ac9044a5`).
Board: `/Users/iv/Developer/ReluxWorks/curator/.task-board`.
Affected new epic: `EPIC-260910-ohqchs`.

During implementation decomposition, this mutation was rejected:

```bash
task-board --board-dir /Users/iv/Developer/ReluxWorks/curator/.task-board m \
  'link(TASK-260910-3kvq02, blocked_by=TASK-260910-24cuys)'
```

The requested link makes collection selection depend on its parser. Neither task belongs to the historical stories named in the error. The diagnostic instead reports cycles involving:

- `STORY-260720-1uv5gi` and `STORY-260720-3plyvy`;
- `STORY-260720-35dck7` and `STORY-260728-10wxx2`.

The read-only `task-board repair-links` command lists unsupported container links, but does not offer a repair that eliminates these reported cycles. Do not apply its unrelated cleanup as a purported fix.

One inspected historical sequence is:

1. `TASK-260720-1nvomm`: v6 core contract, in `STORY-260720-35dck7`.
2. `TASK-260728-1a52au`: v7 core contract, in `STORY-260728-10wxx2`, depends on the v6 task.
3. `TASK-260729-3nx97g`: v6 golden regeneration, in `STORY-260720-35dck7`, depends on v7 task `TASK-260728-2kp3tv`.

These inspected links create opposite edges in the story projection. They do not, by themselves, prove a cycle between individual tasks. The complete historical leaf graph has not been audited. Do not claim that every reported historical cycle is false.

Evidence in the current specification worktree:

- `.temp/source-implementation-plan/mutations.log`: rejected mutation and full diagnostic.
- `.temp/source-implementation-plan/historical-cycle-inspection.log`: task/story projections and statuses.
- `.temp/source-implementation-plan/repair-links-readonly.log`: available repair diagnostics.
- `.temp/source-implementation-plan/board-items.json`: all 15 new tasks and their 20 intended dependencies.
- `.planning/260910_175847_skillfile-sources-implementation.md`: blocked Curator implementation plan.

Code-level cause remains to be confirmed. The producer must locate the mutation validation and canonical planning call paths and distinguish leaf cycles, stored legacy container edges, and derived container cycles before changing behavior.

## Graph semantics

A leaf is a Task or Bug. A Story or Epic groups leaves; group membership does not imply that all work in one group must finish before any work in another group starts.

In the examples below, arrows mean execution order: prerequisite -> dependent. In stored `blocked_by` syntax the reference points in the opposite direction.

Minimal legal case:

```text
Story A: A1, A2
Story B: B1
Leaf dependencies: A1 -> B1 -> A2
```

The leaf graph is acyclic. Its container projection has `A -> B -> A`. The system must preserve all three leaves and both dependencies and permit the sequence. It must not introduce an all-of-story completion barrier from those derived edges.

Minimal illegal case:

```text
A1 -> B1 -> A2 -> A1
```

This is a real dependency cycle and must be rejected regardless of story membership or task status.

## Required mutation behavior

1. Adding a dependency must reject self-dependencies, unknown/invalid endpoints, hierarchy violations and any actual leaf cycle created by the proposed change. Existing validation unrelated to cycle classification remains in force.
2. For `link(A, blocked_by=B)`, validate against the current persisted graph under the existing transaction/concurrency boundary. In dependency-reference direction, a new cycle exists if B already reaches A. Do not rely only on ancestors, direct neighbors, displayed story edges or cached plans.
3. A historical cycle in a disconnected component must not reject a valid link in another component. Report historical defects through board diagnostics; do not silently mark the board globally valid.
4. Within a component containing an existing leaf cycle, reject an added edge when that edge itself participates in a cycle in the resulting graph. An unrelated pre-existing cycle alone is not grounds to reject an edge that introduces no new cycle. This does not make tasks affected by the old cycle schedulable.
5. Re-adding an existing edge retains the documented idempotent behavior and creates no duplicate records. It does not certify or repair an existing cycle.
6. Rejected mutations leave dependency storage, task state and success activity unchanged. Any existing rejection audit behavior remains intact.
7. Batch mutations, if supported, validate their combined final graph: two individually plausible edges cannot jointly commit a cycle. Concurrent reverse-edge mutations cannot both commit.
8. Do not solve the issue by filtering out done/closed leaves. Historical dependencies remain meaningful; active planning filters are a view, not permission to admit invalid graph changes.
9. Audit other graph-changing entry points, including reparenting and imports when present. Reuse the corrected graph semantics where applicable; document exact coverage rather than claiming untested API parity.

## Legacy container links

Retain existing compatibility and write-admission rules for stored Story/Epic links. This fix does not authorize new container dependency declarations or a silent migration of old ones.

Distinguish stored links from derived links in validation and diagnostics. A derived projection cycle must not be reported as a leaf cycle. If legacy links carry separate executable semantics, document those semantics and validate them separately; do not erase or reinterpret them implicitly. Scope any migration required by the discovered contract as a separate reviewed change.

## Canonical planning requirements

- Compute executable leaf ordering from the actual task dependency graph.
- The minimal legal example must produce ordering equivalent to A1, then B1, then A2. Independent leaves may share a wave; every prerequisite must precede its dependent.
- Story/epic summaries must disclose that a container can span multiple execution waves. A flat story projection that is cyclic cannot be presented as an ordinary topological story schedule.
- Preserve the canonical API as the source for CLI compact output and saved plans. No special Curator scheduler or hand-maintained replacement waves.
- If the existing plan schema cannot represent interleaved containers, provide an explicit machine-readable non-executable container-summary result with a usable canonical leaf plan. Specify and test any additive or versioned API change; do not silently change existing field meanings or break consumers.
- A real cycle inside the requested planning scope must return actionable cycle diagnostics, not an empty critical path or a misleading all-independent wave. Unaffected scoped plans must remain usable. A whole-board plan must not claim that cyclic portions can execute.
- Retain the existing critical-path weighting contract, but calculate task execution constraints from the leaf graph. Do not sum cyclic container projections or invent a story-level critical path where no such ordering exists.
- Planner output must be deterministic under different storage/read iteration orders.

## Diagnostics

For a rejected cycle-creating link, identify the requested dependent and prerequisite and return at least one concrete leaf cycle witness, including the proposed edge. Distinguish it from historical errors elsewhere. Preserve existing error-code compatibility where possible; document any necessary new classification.

Global validation must distinguish actual leaf cycles, unsupported stored container links and projection-only cycles. Projection-only cycles are informational or planning-representation diagnostics, not invalid leaf dependencies. Do not claim that `repair-links` can repair a condition it does not handle.

## Acceptance tests

Use minimal fixtures through production validation/planning code and at least one CLI integration path. Expected-result fixture labels alone are not execution evidence.

| Case | Required result |
| --- | --- |
| A1 -> B1 -> A2 across stories A/B/A | Both links accepted; leaf ordering valid; story interleaving visible |
| Add A2 -> A1 to that sequence | Rejected with leaf cycle witness; no partial write |
| Disconnected historical leaf cycle plus valid new edge | New edge accepted; historical cycle remains diagnosable |
| Historical projection-only cycle plus valid new edge | Accepted; no false leaf-cycle error |
| Existing leaf cycle in same weak component, new edge not participating in any cycle | Accepted without certifying cyclic tasks as executable |
| New edge joining paths so it participates in a cycle | Rejected, including when the return path crosses epic boundaries |
| Self-edge, missing endpoint, duplicate edge | Existing invalid-input/idempotency contracts preserved |
| Cycle involving done/closed tasks | Detected; status filtering does not weaken mutation integrity |
| Two-edge batch or simultaneous reverse edges | No cyclic final state; failed transaction leaves no partial success |
| Real cycle in selected planning scope | Explicit diagnostics; no fake successful schedule |
| Unaffected scoped plan with historical cycle elsewhere | Valid deterministic plan available |
| Stored legacy container edge | Existing admission/compatibility policy retained and separately diagnosed |
| Compact JSON/saved-plan views | Same canonical ordering and truthful representation limitations |

## Delivery and Curator recovery

1. Confirm the exact task-board source repository, current instructions and implementation paths. Record the root-cause finding and affected consumers.
2. Add reproducing regression tests, implement the smallest coherent graph/plan correction, and run relevant existing mutation, planning, transaction and compatibility tests.
3. Obtain independent review of leaf semantics, legacy behavior, concurrency and API compatibility. Preserve the current no-commit/no-publication boundary unless separately authorized.
4. Validate the corrected executable against a disposable copy of the affected board first. Do not mutate historical source-board links during reproduction.
5. Through the supported installation/session lifecycle, make the reviewed fix available. Do not replace a running manager's daemon or bypass its update rules.
6. Replay the 20 intended Curator dependencies using task-board mutations. Inspect current state first: already-present edges are not duplicated, and changed task ownership/scope is not overwritten.
7. Re-query `plan(EPIC-260910-ohqchs, mode=children)` and the necessary leaf-level canonical plans. Save the corrected plan in the existing specification worktree and replace the incomplete-schedule warning only after successful verification.
8. Verify all 20 intended edges are persisted, no historical edge was removed, and the accepted 126 specification paths and unrelated board state were preserved. Curator implementation remains unstarted.

Completion means the regression is fixed and the real blocked planning workflow is recovered. Merely hiding historical diagnostics, accepting every link, or producing a schema-only planning snapshot is insufficient.
