# Managed-home provisioning origin, revision 1

This additive, unreleased amendment defines the private `provisioning-origin/1`
record. It supplements [environments](environments.md) sections 7.4, 8 and 10.1;
it changes no published marker, lock, fragment or profile schema. In particular,
[marker 7](codex-seed-c.md#3-marker-and-status) remains byte-identical.
[Decision 0029](../decisions/0029-provisioning-origin.md) adopts this contract.

## 1. Record and capture

Every newly provisioned managed home MUST have a manager-owned, owner-private
regular file named `.agent-provisioning-origin.json` beside
`.agent-environment.json`. The complete record MUST satisfy the separate
[closed schema](../schemas/provisioning-origin-v1/provisioning-origin-v1.schema.json)
and these semantic constraints. A record is private machine state: it MUST NOT
enter portable packages, locks, fragments, public logs or managed-home snapshots.
It contains paths and provenance, never credential bytes or tokens.

| Member | Meaning |
| --- | --- |
| `record` | Exactly `provisioning-origin/1` |
| `adapter` | Exact adapter identity |
| `operator_home` | Actual operator home anchor captured before provisioning mutation |
| `selector` | Adapter selector name, original state and original value |
| `native_root` | Resolved absolute native root selected before mutation |
| `capture` | `provisioning` / `native-selection`, or `adoption` / `explicit-operator-input`, and RFC 3339 UTC time |
| `binding` | Exact profile name, current `sha256:` lock identity and managed-home target |

`selector.state` is exactly `absent`, `present-empty` or `present-value`.
Absent forbids `value`; present-empty requires `value: ""`; present-value
requires the original nonempty value. The name is `CLAUDE_CONFIG_DIR` for
Claude, `CODEX_HOME` for Codex, `PI_CODING_AGENT_DIR` for Pi, and
`XDG_CONFIG_HOME` for OpenCode and Muse. Empty and absent may select the same
native default but MUST remain distinct capture facts. A managed caller
selector is still recorded as the original input; it is not a native origin.

The operator anchor, native root and managed target MUST be absolute, clean
paths without dot components, redundant separators or control characters.
Native selection MUST establish physical containment through existing ancestor
identities, including case aliases and symlinks, without creating missing
tails. A native root inside the managed environments root MUST refuse. Where
absent tails leave case identity ambiguous, refusal is required rather than
case-folded admission. A physically distinct outside native directory remains
valid on a case-sensitive filesystem. Resolving a nonexistent native tail is
permitted; following broken or looping links, failed inspection, or using an
unreadable path as evidence of absence is forbidden.

Capture all fields before the first provisioning mutation, including before
changing any selector or materializing the home. The record describes capture
facts, not a reconstruction from a credential link or today's process state.

## 2. Authority and refusal

Resolve, verify, repair and credential-policy derivation MUST use only the
valid record's `native_root` for the existing home's native credential origin.
Today's selector, HOME default or current credential symlink target MUST NOT
replace that authority. Native-store inspection and expected credential links
are evaluated against that origin under the existing credential policy.

Readers MUST validate the complete record and exact adapter/profile/lock/target
binding before any mutation or launch-fragment emission. Missing records refuse
with `environment_provisioning_origin_required`; malformed, unreadable,
unsupported, orphaned or mismatched records refuse with
`environment_provisioning_origin_invalid`. No fragment, origin rewrite,
credential replacement or unrelated repair is permitted on either refusal.
A correctly bound old record matching the existing marker may be rebound to a
new lock only as part of an otherwise authorized profile update, in the same
transaction as the corresponding home and marker update; its captured origin,
selector, anchor and provenance remain unchanged. Ordinary repair cannot bless
an unexplained lock mismatch or renew an origin from ambient process state.

A credential entry targeting native B conflicts when the recorded origin is A,
even if B is today's default. Repair MUST refuse that conflict without writes.
If a recorded credential link is absent, authorized repair may restore only the
link to A; it MUST NOT copy credentials or point at B. Existing regular files,
including hardlinked credentials, retain the existing conflict protections.

A policy cache MUST bind the validated record identity/digest, adapter, profile,
managed target, lock and credential-policy inputs, including release/backend
observations. Re-read authority at a fresh operation and after lock acquisition,
recovery or authority publication; do not reuse a pre-lock or failed observation
to admit changed authority. Native-skill routing has its own contract; recording
credential origin does not authorize retargeting unrelated native surfaces.

## 3. Atomic lifecycle and recovery

Publication of the home, its marker and origin record MUST be one recoverable
transaction under the manager-home mutation lock. Record-file atomic rename
alone is insufficient when home files or credential links have already changed.
Before commit, validate every planned credential replacement and authority
binding. Failed provisioning or adoption MUST leave no partial origin, marker,
home fragment or credential mutation. Failed repair MUST restore the affected
home preimage. Unrelated tool-owned state and native credentials are preserved.

The durable transaction MUST cover changed home files, entry-owned symlinks,
marker and record, with preimages and input identities. Crash recovery must
restore the preimage or complete the same admitted unit before the home can
emit a fragment. Recovery is not permission to infer a new native origin.
Recheck path boundaries and lock authority before resumed publication.

Removing a managed home MUST remove its origin record in the same lifecycle.
Retained homes retain their records. Snapshot/export/import MUST NOT transfer
this record as destination authority; destination provisioning or explicit
trusted adoption establishes destination-local authority. Old binaries that do
not implement this amendment are not qualified to maintain adopted homes;
this sidecar supplies no claim that such binaries enforce the new contract.

## 4. Legacy adoption

A legacy home without a record MUST refuse normal resolve and repair. The
manager MUST expose an explicit `adopt` operation requiring trusted operator
input for operator-home anchor, original selector state/value and native root,
plus exact adapter/profile/managed target and lock selection. CLI spelling is
implementation-owned but the command MUST be named and documented; no hidden
configuration or implicit automatic migration qualifies.

Adoption validates the existing home marker and all supplied authority against
its exact current lock, requires a non-managed native root, and validates every
credential entry against the explicitly supplied origin before any write. It
MUST NOT derive trusted input from today's HOME, default path or credential
symlink. Wrong-target credentials, unknown binding, unsupported schema or any
failed read refuse without writes. Adoption writes provenance
`adoption` / `explicit-operator-input` and commits atomically with the validated
home state. Repeated identical adoption is read-only/idempotent; a different
origin cannot replace an existing record through `adopt`.

## 5. Conformance and limits

The [separate corpus](../conformance/provisioning-origin-v1/README.md) executes
closed-schema and pure authority cases, with planted wrong-verdict and schema
controls through the publication entry. It qualifies no manager filesystem,
cache, CLI, concurrency or crash-recovery behavior.

Adopting implementations MUST independently exercise the real provisioning,
resolve, repair, explicit adoption and removal paths with valid neighbors:
custom A remains authoritative under today's B; retargeted B refuses in read
and repair without mutation; missing link restores only A; missing/malformed/
stale/orphan records refuse; selector absent/empty/value remain distinct; cache
invalidation survives lock/recovery/record changes; injected commit failures
and restart recovery preserve the admitted home/origin unit. Preserve independent
review probes, and test symlink, hardlink, absent-root/case-alias and physically
distinct outside-native controls on the relevant platform matrix.
