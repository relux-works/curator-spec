# Profile-level Codex settings, revision 1

This document is normative. It adopts implementation-plan leaf 1 of
[CIP-0018](../cips/CIP-0018-profile-level-codex-settings.md), under owner decision
2026-10-15 (D9, D13), corrected by owner decision 2026-10-16 (D14). It amends the identified sections of
[environments](environments.md); their other rules remain in force.
This is an unreleased extension, separate from the frozen rc.14 corpus.
Acceptance specifies a contract; it does not enable a producer or qualify a
Codex release, launcher, host or dispatcher.

## 1. Closed manifest vocabulary (environments section 2)

A context package MAY declare OPTIONAL `codex_settings`, a closed JSON object.
The [member schemas](../schemas/profile-codex-settings-v1/README.md) define the
exact structural additions. No package key is admitted in this revision;
only an absent member or `{}` is valid. New keys require a reviewed typed
vocabulary extension. Credential-store, credential-source and account keys,
including `cli_auth_credentials_store`, MUST NEVER be admitted here.
The only credential-store selector is the user-owned machine knob
`credential_store.<profile>.<env-id>` (default `native`) in
[login readiness section 2](login-readiness.md#2-user-owned-credential-store-policy).
Packages, overlays, locks and repositories MUST NOT select that store.

The root, required context packages and ordinary machine-selected overlays
MAY contribute, including a package without context modules. Skill packages
and MCP declarations MUST NOT carry this member as another settings source.
A path overlay acquires no extra powers. An absent or empty object contributes
nothing and MUST NOT clear a lower-ranked value.

Readers MUST validate every contribution before precedence, including losing
contributions. They MUST reject duplicate JSON keys before decoding to a map,
invalid UTF-8, unknown fields or setting names, dotted or quoted aliases,
control characters, and any nonempty settings object, including a declaration
of `cli_auth_credentials_store` with either `file` or `keyring`. There is no
interpolation, include, executable expression, deletion marker or secret value.
Invalid input MUST produce `context_manifest_invalid` and no usable fragment;
failed install/update MUST preserve the previous lock and materialized state.
JSON Schema validates decoded structure, not duplicate keys or input encoding.

The allowlist is the authority, rather than a denylist. It excludes sandbox
and approval controls, permission profiles, `sandbox_*`, `permissions`,
`default_permissions`, MCP servers, model/provider selection, endpoints and
API keys, project trust, hooks, instruction paths and alternate config/profile
selectors. Admission of another key requires a reviewed typed vocabulary
revision; credential-store, credential-source and account keys remain forbidden
regardless of machine authorization.

## 2. Inheritance and identity (environments sections 1.3, 6, 8.2, 12)

Collect each resolved context-package identity once, including requirements
and overlays. Compute effective weights by environments section 6 without
changing its four-step calculation or requirement-edge conflict rules.
The following inheritance machinery is retained for reviewed vocabulary
extensions; with no admitted package key, effective package settings are `{}`
and contributions are empty. It MUST NOT compose or apply precedence to the
machine credential-store selector. For each admitted key, the resolver MUST:

1. Select the highest effective weight for `winner=higher-weight`, or the
   lowest for `winner=lower-weight`.
2. Coalesce identical typed values at that weight, retaining all winning
   origins for inspection.
3. Refuse differing values at that weight with `codex_settings_conflict`.
   Package name, traversal, overlay order and chapter placement MUST NOT
   break a tie. Refusal emits no fragment and publishes no replacement lock.
4. Succeed with `codex_settings_override` when superseded values differ,
   reporting the key, origins, weights, winning value and winner rule.
   Identical redundant contributions remain inspectable. Disagreement at a
   losing weight is superseded, not a winning conflict.

`placement` MUST NOT affect settings. Weights now select these admitted
scalars as well as ordering chapters; they still cannot merge instruction
text, resolve incompatible versions or select an MCP/skill by preference.

A successor lock MUST record the effective `codex_settings` (including `{}`),
`codex_settings_contributions` and the existing precedence primitives.
Contributions are sorted bytewise by package name, exactly once per context
member with a nonempty declaration, with `{package, settings}` entries.
`package` MUST name that lock's context member; its existing pin and effective
weight bind the contribution. Settings MUST equal the validated declaration
at that pin. Readers MUST recompute selection and reject a mismatch; the
schema alone cannot establish these relations. The existing lock CCJ-1 hash
MUST cover all these members, including precedence. No source paths or secrets
enter them. An empty selection has an empty contribution list.

A successor marker MUST record effective `codex_settings` (including `{}`)
and bind the successor lock hash through its existing profile pin. Marker
currency MUST compare the recorded settings and pin to that lock. Status MUST
show effective settings, all contribution origins and weights, override/tie
outcomes, and separately native storage versus effective launch storage.
Changed path-package bytes, machine weights or winner policy MUST make an
old identity non-current; resolve MUST NOT silently relabel or re-resolve it.
Protected-boundary checks, explicit update and migration rules still apply.

## 3. Fragment and delivery (environments sections 7.3, 7.8, 10.2)

A new closed fragment revision MUST admit OPTIONAL `codex_settings`, with
a closed typed launch-override object, only for `environment=codex_cli`.
It carries reviewed package settings and Curator's machine-selected override;
the latter is not a package contribution and MUST NOT enter package locks or
markers. In this revision the transport admits only
`cli_auth_credentials_store: "file" | "keyring"`, filled exclusively from
`credential_store.<profile>.<env-id>`: `file` maps to `file`, qualified
`keychain` maps to `keyring`, and `native` emits no store override.
The effective object MUST be present when nonempty and omitted otherwise.
A missing payload required by the accepted launch identity is a refusal,
not silence. Package settings remain `{}` regardless of machine selection.
The launcher MUST consume the resolved object and lock identity; it MUST NOT
read package/overlay files to rediscover values. Provenance remains Curator's
inspection concern. No new channel kind, descriptor field, raw argv string
or publisher-selected file path is admitted.

Curator owns resolution, eligibility and canonical emission. The launcher
passes the exact typed member to its Codex plugin, which MUST revalidate the
allowlist and emit each key once in ascending ASCII key order. Each setting
is two argv elements: `-c`, then `key=<canonical TOML scalar>`. For file mode:

```json
["-c", "cli_auth_credentials_store=\"file\""]
```

For this enum the canonical scalar is the exact value enclosed in TOML basic
string double quotes, with no spaces or newline. Use a TOML scalar serializer,
never a shell or concatenation of unvalidated publisher text. Pairs MUST
precede the positional prompt or `--` boundary. Sorting applies only to this
block; other provider-owned blocks retain their order and semantics.

The same typed block MUST reach interactive, exec, hosted app-server, login
preparation, resumed-host and tracked-dispatch paths. Host reuse MUST match
the accepted settings identity; a mismatch requires a normal restart/new
session transition or refusal. Running sessions keep their accepted snapshot
and settings. Resume MUST use that identity or make an explicit new-session
transition. A later overlay edit cannot relabel a running session's backend.

The fragment digest and plan-covered launch MUST cover settings. A remote
dispatcher MUST relay the covered payload unchanged, without resolving,
rewriting or inspecting Curator homes. Unknown revisions, missing required
payloads or unsupported delivery MUST refuse, never downgrade to an older
fragment. Shell-format output is not a transport for settings.

## 4. Ownership and the bounded exception (environments sections 10.3, 12.1)

The former statement that a profile never shapes launch behavior is narrowed
only for keys admitted by a reviewed package vocabulary extension; this
revision admits none. Credential-store selection comes exclusively from the
machine selector, never profile bytes, and uses section 3's single typed
transport, validated mechanically before resolution and again before launch. The
registry-only environment-variable boundary is unchanged: profile bytes
MUST NOT select, add, rename or retarget variable names or values. The
existing operator-variable allowlist is a separate, unchanged exception.

Host policy and profile settings MUST have disjoint ownership. Before exec,
host and plugin MUST reject collisions with reserved channels and competing
raw `-c`/`--config` sources, dotted/table aliases, native profile selection or
equivalent request/RPC fields that could replace the chosen credential
backend. Equality does not authorize duplicate owners. Hosted start, client
and resume paths MUST enforce this rule. Protected policy, trust, approvals,
permissions and private policy documents remain host-controlled.

Hosts MAY write their own private session policy `config.toml`, but MUST NOT
persist profile settings into it or rewrite native, managed-seed or snapshot
configuration to apply settings. Resolve, repair and global skill sync MUST
NOT backfill this member into a seed. Both seed revisions retain their exact
existing behavior, including revision-A residual warnings. Exclusive hosted
MCP policy MUST use an exclusive base document: `-c mcp_servers={}` is not a
proof that inherited tables are cleared. Unsafe composition MUST refuse.

Equal winning values from dependencies are harmless redundancy; differing
winning values from two third-party requirements can deny resolution. This
is a fail-closed availability risk, not a permission bypass. Weights admit
no capability, and signatures do not authorize policy weakening.

## 5. Credential eligibility amendment (environments section 7.4)

D9's file-mode selection comes only from the machine selector
`credential_store.<profile>.<env-id>` defined by CIP-0015 section 2, as
confirmed by D14. Curator fills section 3's single typed settings transport
from that selector for login preparation and subsequent launches; no package,
overlay, lock or repository value composes with or overrides it. No credential bytes
may enter manifests, locks, fragments, plans, status or diagnostics.
Native storage determines sharing; effective launch storage determines the
managed invocation's backend. An override MUST NOT convert a native keyring
identity into a file credential or treat an unrelated `auth.json` as the
native authenticated store.

When the machine selector explicitly selects storage, preparation MUST apply this matrix
before linking or invoking login/the agent. A successfully read native config
with no key means native `file`. Read/parse failure means unknown and MUST
refuse; it MUST NOT fall back as though the key were absent.

| Mode | Native storage | Effective launch storage | Required result |
|---|---|---|---|
| shared | file, including absent key | file | Existing native-file passthrough and liveness rules |
| shared | keyring | keyring | Existing ambient identity; no assumed per-home keyring scope |
| shared | any other pairing, including auto | explicit file or keyring | Refuse mismatch/ambiguity; offer isolated preparation or explicit native-store migration |
| isolated | any successfully inspected verified selector (`file`, `keyring`, `auto`) | file | Only a separately prepared private file credential; never link the native file |
| isolated | any | keyring | Refuse pending independent per-home scoping evidence |

The isolated/file row explicitly amends section 7.4's native-file-only gate,
coordinated with CIP-0015; it is not a current implementation claim. With no
explicit setting, ALL existing section 7.4 rules apply, including native
`auto` behavior. An unrecognized native selector remains unsupported even
for isolated/file. A backend or isolation change requires the existing
inspect → plan → confirm → apply migration, never repair. Selection MUST NOT
migrate credentials, silently sign in, repair detached links or bypass
readiness. Unsupported runtime capability MUST refuse before a model or
login invocation, with an actionable report.

On the recorded Codex 0.153.2 baseline, scalar CLI precedence over a conflicting
seed and the effect of this override on `codex login`, app-server and token
refresh are **unverified**. These are required semantics to qualify on every
supported release, not measured facts inferred from native config support.
Producer enablement MUST wait for that qualification, CIP-0015 matrix adoption
and strict consumer support. Use disposable homes/accounts and no model call
for credential-storage qualification; never persist secret probe output.

## 6. Diagnostics

These are normative extension diagnostics; their existence does not assert
that current implementations emit them. Existing read-failure diagnostics
retain environments section 8.4.1's absence/failure distinction.

| Condition | Diagnostic and outcome |
|---|---|
| Invalid package contribution, even if losing | `context_manifest_invalid`; refuse, no replacement lock or fragment |
| Differing settings at winning weight | `codex_settings_conflict`; refuse, name key, origins, weights and winner rule |
| Superseded different values | `codex_settings_override`; warning with section 2 provenance; resolution succeeds |
| Invalid typed launch payload or competing owners | `codex_settings_delivery_conflict`; refuse before exec, no settings/config write |
| Unsupported revision, runtime capability, missing required payload or unavailable delivery path | `codex_settings_unsupported`; refuse before login/agent invocation |
| Shared native/effective mismatch or ambiguous native auto with explicit override | `environment_credential_conflict`; no link or launch |
| Explicit isolated/keyring | `environment_isolated_unsupported`; no link or launch |
| Unrecognized native selector | `environment_credential_unsupported`; no link or launch |

Diagnostics MUST contain only nonsecret metadata. New launch consumers adopt
these extension codes consistently; they do not imply new permission to read
homes or to repair state.

## 7. Wire allocation, conformance and rollout

The [schemas](../schemas/profile-codex-settings-v1/README.md) freeze the added
member shapes, not complete manifest/lock/marker/fragment envelopes. Their
schema-module revision `v1` is NOT an enclosing wire version or fragment token.
Existing closed schemas MUST continue rejecting these additions. A producer
MUST NOT insert them into any old envelope, including with an old version
token. Full successor envelopes MUST retain all existing constraints, change
their version discriminants, and include these exact member contracts.

The coordinated allocation of successor manifest, lock, marker and fragment
versions remains OPEN with the parallel base-context, root-context and snapshot
amendments. Recommended resolution: one jointly reviewed allocation if shipped
together, independently versioned strict readers otherwise. No existing or
parallel proposed version is repurposed here. Full carrier schemas and
positive/negative carrier cases MUST be published in that allocation before
producer enablement; this leaf's modules MUST NOT be used as envelope validators.
The later curator-spec qualification leaf records this remaining rollout gate.

The [conformance corpus](../conformance/profile-codex-settings-v1/README.md)
publishes executable structural cases and semantic vectors for cross-repository
consumption before producer activation. Specification tests prove structural
rejection and corpus consistency only. Real resolve, login, launch, host and
relay entrypoints remain unverified here. Their tests MUST observe the required
state/argv and forbidden effects; reproducing expected labels in a helper
is not qualification. Old profiles retain existing behavior until an explicit
supported identity transition. No repair implicitly upgrades their carriers.
