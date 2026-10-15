# Required operation vectors (not executed by the metadata checker)

These normative cases freeze the observable leaf-1 contract for later
production-entry tests. Inputs refer to admitted synthetic profiles and private
destinations, never a particular machine. Each rejection emits no success
manifest, preserves source and prior target, and cleans only own staging.
Repository metadata checks execute **0** of these operation cases.

| Named production test | Positive control | Required counterexamples and outcome |
|---|---|---|
| `MaterializeCLI_ContentClosure` | Exact admitted root/support/skill/system/MCP closure | Nested credentials, seeds, foreign XDG links, marker internals and state never exported; secret-bearing selected content refuses under existing admission code, never silently redacted |
| `MaterializeCLI_DestinationBoundary` | Absent or empty owned destination outside protected ancestry | Linked ancestor/target, reparse point, uncertain ownership, other-principal writes, protected ancestry and unrelated nonempty target: `environment_materialize_destination_invalid`; no escaped writes |
| `MaterializeCLI_NoTornGeneration` | One verified generation under the mutation lock | Repair/switch/global-sync races, same-fragment ABA or changed store bytes: one verified generation or `environment_materialize_capture_drift`, never mixed accepted bytes |
| `MaterializeCLI_SourceRefusals` | Current readable source | Stale/unprovisioned: `environment_home_stale`; contention: `environment_lock_unavailable`; pending recovery: `environment_materialize_recovery_required`; unreadable marker/store/surface/passthrough retains its existing diagnostic, never absence or repair |
| `MaterializeCLI_PortableIdentity` | Manifest-only equals export for the same source; another source binding has the same portable projection | Bare manifest-only: `usage` before selection/locks/writes; unsupported absolute-reference relocation: `environment_materialize_relocation_unsupported`; changed output bytes/modes/descriptor/producer identity never compare equal |
| `MaterializeCLI_Idempotence` | Byte-verified identical target is unchanged | Forged metadata, altered content, extras, missing/unreadable entries or a different generation: `environment_materialize_snapshot_mismatch`; prior target unchanged |
| `MaterializeCLI_AdapterBoundary` | Qualified supported adapter supplies its complete closure | Opencode before profile-local skills qualification: `environment_materialize_adapter_unsupported`; cannot report a partial snapshot as success |

The schemas may describe a reserved opencode descriptor without authorizing
materialization. Structural acceptance is not an operation's success verdict.

Future hosted attach/resume must verify the actual complete content and
covered overlays against the original baseline; missing evidence or failed
reads never establish absence, never update the baseline and never fall back
to live homes. The executor must establish independent plan authority, exact
archive/manifest/descriptor correspondence and protected runtime content before
child code. Their exact transport bytes/caps and runtime mechanism remain
later leaves; this document does not invent refusal-code aliases for them.
