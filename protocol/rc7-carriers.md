# Login/store and Codex containing carriers, revision 1

This normative publication implements CIP-0015 L15-0 and CIP-0018 C0 together,
under D7, D8 and D14. The **rc.7 implementation wave** name is not a release
version: this extension is unreleased and does not change historical
`1.0.0-rc.7` or the frozen rc.14 corpus. It takes precedence over the earlier
open-allocation statements in the two amendments. Snapshot descriptors keep
their separate closed namespace and MUST NOT acquire credential policy.
Grammar publication does not qualify a runtime or enable an emission.

## 1. Allocation and complete validation

The [whole-object schemas](../schemas/rc7-carriers-v1/README.md) allocate:

| Carrier | Exact discriminator | Required addition / retained baseline |
|---|---|---|
| Manager configuration | `schema_version: 5` | Configuration 3, plus optional `environments.credential_store` importing frozen `credential-store-config-v1` |
| Readiness status | `status: "env-status-v1"` | First explicitly versioned full readiness matrix; required `rows`, `codex_settings`, `observations` |
| Context manifest | `schema_version: 2` | Manifest 1, plus optional empty-only `codex_settings` |
| Context lock | `schema_version: 4`, `hash_version: 2` | Lock 2, plus REQUIRED `precedence`, `codex_settings: {}`, `codex_settings_contributions: []` |
| Environment marker | `version: 5`, `hash_version: 2` | Marker 3, plus REQUIRED `codex_settings: {}` |
| Launch fragment | `fragment: "launch-env-fragment-v5"` | Fragment 4, replacing only Codex payload ownership as section 3 specifies |

Draft CIP-0013 reserves proposed config 4, lock 3 and environment marker 4
for separate base-context semantics. This publication skips those numbers;
it neither adopts nor repurposes that draft. Readers lacking those separately
published contracts MUST reject those identities.

Every whole object and its nested objects are closed. Retained fields,
required members, type constraints and non-schema semantics retain their
previous meaning. Readers MUST reject unknown members, revisions, duplicate
JSON keys and invalid UTF-8 before using a document. A standalone member or
row validator MUST NOT substitute for its containing schema. An invalid
carrier emits no usable output and replaces no installed state. Discriminants
are not inferred from a filename, module suffix or optional field.

Configuration versions 1–3, context manifest 1, lock 1–2, marker 1–3 and
fragment 1–4 remain unchanged. In particular v4 has its original
`credential_store.config_overrides`; it MUST NOT accept `codex_settings`.
New readers MAY also implement explicit old readers; they MUST dispatch on
the exact discriminator and MUST NOT relabel old data as a successor.
Old readers reject successors and new fields under old tokens. Required
policy MUST NOT be dropped to satisfy an old reader. Existing status formats
retain their closed shapes; readiness adoption requires explicit selection
of `env-status-v1`, never insertion of login fields into a legacy format.
There was no previously allocated whole readiness-status token in this spec;
this publication does not invent a retrospective legacy status schema.

Machine configuration alone selects stores. Package, overlay, repository and
system-lock documents MUST NOT carry credential-store/source/account policy.
The system-config locked-key vocabulary is unchanged; the existing lockable
`isolation` knob is not a store selector. Config schema admission is not
adapter/platform eligibility. Unsupported explicit maps retain section 4's
refusal, never silent fallback. No package contribution participates in
machine selection or becomes machine policy provenance.

## 2. Identity and status

Only absent or `{}` package `codex_settings` is admitted, including dependencies
that lose precedence and overlays. Validate every package before selection.
A lock always records effective `{}`, empty contributions `[]`, and the actual
precedence primitives. Empty declarations do not create contribution records.
An entry with even empty `settings` is therefore invalid in this vocabulary.
The marker records `{}` and its existing profile pin binds the successor lock.
Neither lock nor marker records the machine selector or its projected value.
Store changes do not mutate package identity or upgrade an existing carrier.

All six objects use registry CCJ-1 canonical JSON: UTF-8, sorted keys, no extra
whitespace and no trailing newline in the canonical byte stream. The lock's
existing content-hash framing version 2 covers the entire successor lock,
including its version, precedence, empty settings and contributions. The
marker profile pin MUST bind that computed lock identity. Fragment/plan
coverage includes both agreement and typed payload. A digest change requires
normal identity/currentness handling, never silent seed or pin rewriting.
[Canonical fixtures](../conformance/rc7-carriers-v1/canonical.json) specify exact
bytes and SHA-256 of those bytes; their SHA-256 is a fixture checksum, not an
alternative lock framing algorithm. Marker/fragment hash fields in isolated
schema examples are synthetic pins, not an assertion that all examples form
a single installed profile.

The full `env-status-v1` schema requires:

- `rows`: every participating profile × environment exactly once, sorted
  bytewise by `(profile, environment)` inside its REQUIRED frozen `readiness`
  row. Each enclosing row also requires mode, lock hash (null if unavailable),
  recorded and detected tool version (null if unknown), configured selector,
  native storage, effective store, surface rows and observations. The
  `readiness.current` value is the complete existing currency verdict, not
  merely the listed surface subset. Surface rows expose name, currentness,
  form, paths and diagnostic codes. `effective_store` MUST equal the frozen
  login detail's store. Configured absent is reported as default `native`;
  configured native is never rewritten to make a managed-Muse mapping.
- `codex_settings`: exactly one sorted row per reported profile, with effective
  `{}`, contributions `[]` and the actual precedence. There are no contribution
  origins/weights or override/tie outcomes in this empty vocabulary; context
  member weights remain ordinary inspection metadata. Machine-selected
  launch storage is reported separately, never as package settings.
- `observations`: the existing non-home and machine matrix reports. Per-home
  observations live in their enclosing row. Each is a closed metadata record
  with kind, name, state and scalar value, optional path and provenance. The
  closed kind set covers posture, store trust, passthrough, seeds, targets,
  shadows, scoped current profiles, backups, providers, orphans, source signer,
  context, dropped system modules and diagnostics. Names identify the existing
  environments §12 report item; values are sanitized display metadata, never
  arbitrary vendor output. These records preserve §12's mandatory inventory,
  posture order/provenance and trust/error distinctions; they are not a way
  to omit currency checks or add policy owners.

Rows carry metadata only: no credential bytes, credential digests or account
identities, in any string, observation, path or extension. A schema cannot
prove that an otherwise well-typed string is sanitized. Native storage and
effective launch storage are separate reports; unknown native inspection
never becomes an absent native key. Status is not launch authorization.

For managed Muse, a `present` or `absent` row whose selected source is
`per-home` or `native` (the verified shared source) MUST report backend
`file`. A global Keychain candidate cannot establish either verdict for the
managed file source. This containing-carrier relation supplements the frozen,
adapter-generic `login-row-v1`; validating that row alone is insufficient.
Unknown metadata or `source-conflict` remains `unknown`, with the observed or
unknown backend; it MUST NOT become file-candidate presence or absence.
Environment, node, helper and broker sources retain their separate source
policies and backend reporting. This rule neither forces their backend to
file nor adopts an otherwise unadopted external-source policy.

Plain status exits 0 after rendering; operational matrix failure is nonzero.
Strict status --check and prepare require every participant current and present.
Absent or unknown makes aggregate exit 1, with all available rows retained.
Participating OpenCode remains unknown/ambient with unknown backend and
ambient reason, so such a profile cannot currently return green check/prepare.
Ordinary status, explicit install/resolve and launch remain available under
their own existing gates. No login authorization gate is added to launch.

## 3. Single payload and producer/consumer transition

In v5, `credential_store` is closed agreement metadata with only REQUIRED
`selection`. `codex_settings` is the sole typed Codex argv payload.
Legacy config_overrides is forbidden in v5, even when identical to the payload.
For Codex:

| Effective selector | Agreement | Typed payload |
|---|---|---|
| native | absent or `{"selection":"native"}` | absent |
| file | `{"selection":"file"}` | REQUIRED `{"cli_auth_credentials_store":"file"}` |
| qualified keychain | `{"selection":"keychain"}` | REQUIRED `{"cli_auth_credentials_store":"keyring"}` |

A payload with absent agreement, mismatch, empty payload or duplicate owner
is invalid. Native MUST omit the payload. Non-Codex adapters MUST omit it.
Other adapters retain v4 admission: Muse requires effective file, five values
and its optional verified root fact; Claude/Pi/OpenCode admit native agreement
only. All v4 path, channel, permissions, root-context and one-parent constraints
remain. No settings field is added to a snapshot descriptor.

CIP-0018 §3's exact two-element `-c`, `key=<canonical TOML scalar>` pairs apply,
in ASCII key order before the positional prompt/`--`; file maps to
`["-c","cli_auth_credentials_store=\"file\""]`. No shell evaluation or native,
managed-seed, snapshot or private-host configuration rewrite applies settings.
Direct structured login consumes typed policy without evaluating shell output.
Competing raw argv/RPC/profile policy owners refuse even if equal.

| Producer or consumer | Required behavior |
|---|---|
| package installer/resolver | Read manifest 2 only with explicit support; validate all declarations before precedence; publish lock 4/marker 5 together under ordinary transactions |
| status/config reader | Select the exact config/status carrier; unsupported identities refuse, never hide or drop members |
| full JSON producer | Emit v5 for nonempty Codex policy only after runtime qualification and every selected consumer supports v5 and typed settings |
| direct interactive/exec/login consumer | Validate the full v5 envelope and accepted machine policy before constructing argv; never inspect packages or home files for policy |
| hosted app-server/resume consumer | Apply the same payload; bind host reuse and resume to accepted settings/lock identity or require the normal new-session transition |
| plan/dispatcher/receiver | Cover, relay and validate the exact full payload unchanged, with explicit support at each hop; missing support refuses before execution |
| old reader | Reject new identity; never retry an old token with policy removed |
| env/shell renderer | Nonempty Codex settings refuse with `codex_settings_unsupported`, zero output |
| native/empty env/shell renderer | Existing environment-only projection remains available; it is not a complete typed launch contract |
| Muse env/shell renderer | Retain exactly four XDG parent paths in registry order then backend file literal; limited environment projection, not a replacement for full JSON |

All renderer/consumer refusals occur before writing any partial output,
replacing installed state or invoking a vendor. Unsupported full typed delivery
refuses with `codex_settings_unsupported`; no usable launch artifact may omit
required settings. A malformed/competing typed payload is
`codex_settings_delivery_conflict`. These are semantic implementation vectors,
not evidence that any runtime entrypoint has executed them here.

## 4. One Muse decision table

This table is consumed by resolve, login and every direct/hosted launch path.
It supersedes the earlier contradictory explicit-map diagnostic and generic
backend-conflict wording for adopting implementations. Credential-source
conflicts are separate from a backend literal; clearing a source is forbidden.

| Configured / ambient / explicit input | Effective result / diagnostic | Required bound |
|---|---|---|
| Muse configured absent or native | effective file, selector unchanged | Mandatory `TBH_CREDENTIAL_BACKEND=file`; no stored-selector rewrite |
| Muse configured file | effective file | Same policy at login and launch |
| Muse explicit keychain | `environment_credential_store_unsupported` | No fragment, link, login or launch; file-selection guidance |
| Muse ambient backend keychain or another inherited backend value | mandatory file literal wins | Ambient backend is not an explicit operator override; later merges cannot replace the literal |
| Muse explicit plan/backend override incompatible with file | `environment_credential_conflict` | Refuse before exec; equality never authorizes a second owner |
| Competing inherited credential source under the selected source policy | existing source-conflict refusal | No source stripping or backend-literal fallback; readiness unknown/source-conflict |
| Unsupported native storage selector | `environment_credential_unsupported` | Unknown native storage is distinct from an unsupported explicit machine map |

The generic native-preservation table in login-readiness §2 applies to other
adapters; it is not a second managed-Muse admission rule. Muse shared mode still
requires compatible native file login; isolated creates no passthrough link.
This publication does not qualify refresh or concurrent refresh.

## 5. Status boundary, CLI and activation

Adopting readiness status executes no agent binary, including --version or auth status.
Detected version is honestly unknown unless established without agent execution.
A future diagnostic is an explicit command with no implicit status call site;
it cannot become a secret-producing fallback. Existing recorded registry
versions remain reported and known mismatches retain their warning.

The exact CLI grammar remains `env login <env-id> [--profile <name>]` and
`profile prepare <source-or-name> [--non-interactive]`. Preparation uses install's
explicit source grammar and default naming, not implicit update or activation.
Login requires the installed/current/trusted isolated home and interactive
input/output under login-readiness §3; it does not install, repair or activate.
Prepare retains §4's report-only noninteractive behavior and strict aggregate.

This publication closes the containing grammar gate only. Explicit Codex
projection remains unavailable until qualified storage/CLI precedence at login,
app-server and refresh, strict consumers and covered route delivery pass their
applicable gates. Snapshot/hosted/archive enablement remains separately owned.
Muse v4 work is not held behind future package vocabulary or Codex qualification.
No measurement of credential custody, vendor execution, no-partial-output at a
runtime renderer, or metadata reader safety is claimed by schema conformance.

## 6. Subsequent local-source allocation

[Local setup-token revision 1 §5](local-setup-token-source.md#5-closed-carriers)
serializes the next allocation after this joint L15-0/C0 publication:
config/marker/fragment 6 and status 2, in a dedicated schema namespace.
This publication's six carriers remain unchanged. Manifest 2 and lock 4 still
reject source/account policy. Source marker provenance never changes package
identity. Node emission is independently gated and is not a prerequisite for
unrelated existing v4 Muse delivery.
