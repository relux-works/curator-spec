# Login readiness and profile preparation, revision 1

This normative amendment adopts [CIP-0015](../cips/CIP-0015-login-readiness-and-profile-preparation.md)
implementation-plan leaf 1, by owner decision 2026-10-15 (D1, D7–D9, D11,
D13). It supplements [environments](environments.md) §§7.4, 9, 10, 12 and
12.1. The bounded changes below take precedence for implementations adopting
this capability. Acceptance specifies a contract, not implementation shipment
or platform qualification. No released schema or fragment revision is changed.

## 1. Presence and status grammar

For every participating profile × environment, status MUST report `login`
as exactly `present`, `absent`, or `unknown`, independently of content
`current`. A standalone versioned row follows
[`login-row-v1`](../schemas/login-readiness-v1/login-row-v1.schema.json).
It is not a replacement schema for the entire existing status matrix.
Implementations MUST NOT add these fields silently to a closed older wire
contract. The complete `env-status-v1` carrier is allocated in
[containing carriers](rc7-carriers.md); the standalone row remains frozen.

- `present`: metadata establishes an accessible candidate for the selected
  source in the calling session under qualified adapter rules.
- `absent`: inspection succeeded and established no candidate. A missing
  home establishes absence only for an exclusively home-local source with
  a readable, protected parent.
- `unknown`: evidence is inaccessible, ambiguous, conflicting, untrusted,
  unqualified or incomplete. Read failure MUST NOT be treated as absence.

Presence does not establish valid JSON, token validity, expiry, scope,
subscription, refresh safety or successful inference. Rows MUST NOT carry
credential bytes, token digests or account identities. No readiness fact is
cached in a marker, installed profile or plan as launch authority.

`login_detail` has REQUIRED `source`, `store`, `backend`, `session` and
`reason`; OPTIONAL `keychain_access` is admitted only for Claude. All are
closed enums in the row schema. `source` is `per-home`, `native` (shared native
source), `environment`, `node`, `helper`, `broker`, or `ambient`. `store` is
the effective Curator selector `native | file | keychain`. `backend` is
`file | keychain | environment | external | unknown`, describing the effective
backend rather than an account. `session` MUST be `caller`.
`keychain_access` is `available | unavailable | unknown`.

The stable reasons are `candidate-present` for present, `candidate-absent`
for absent, and, for unknown, `metadata-unavailable`, `empty-file`,
`source-conflict`, `untrusted-home`, `unqualified-backend`, or `ambient`.
An unestablished backend is `unknown`; it cannot support present or absent.
Implementations MUST choose the reason matching the observed uncertainty;
these labels are row metadata, not command refusal codes.

### 1.1 Metadata readers

Status MUST NOT invoke an agent executable, open a credential file for its
content, request Keychain secret data, invoke a secret-producing helper,
attempt network access, acquire a broker lease, prompt or unlock a store.
A Keychain metadata query MUST disable data return and be qualified as
bounded, nonprompting and non-unlocking. An unqualified probe reports unknown.
Denial, locked stores, timeouts and unavailable APIs are unknown, not not-found.

For a file, verify protected parent, entry type, ownership, private
permissions, accessibility and any expected passthrough link identity using
metadata. A nonempty regular candidate at the approved destination is
present; a zero-length candidate is unknown (`empty-file`). A successful
lookup with no entry is absent. Unexpected links, directories, unsafe
ownership and permission/read failures are unknown. Only a verified shared
link may lead to the native candidate. Status MUST NOT repair it. Detached
passthrough remains independently non-current under environments §7.4.

| Adapter/source | Required derivation | Bound |
|---|---|---|
| Claude, macOS native | Establish caller-session Keychain capability non-interactively. A qualified capable session queries metadata of the §7.4 suffixed service/account; a qualified fallback session inspects managed `.credentials.json` metadata. | Never use an item visible only in another session or try both stores to obtain present. Unknown capability, precedence or identity yields unknown. |
| Claude, Linux native | Inspect managed `.credentials.json`, or its verified native link under shared. | Bad links/read failures remain unknown; no refresh guarantee. Windows remains unqualified. |
| Codex, effective file | Resolve source/store first; inspect managed `auth.json`, or the compatible verified native shared link. | No parsing or validity claim. |
| Codex, keyring/auto | Report unknown pending a qualified metadata-only identity and precedence probe. | Existing isolated refusal remains. No guessed per-home keyring scope. |
| Muse, explicit file | Inspect `$XDG_CONFIG_HOME/muse/auth.json` in the managed projection. | Admission and shared-link compatibility belong to the separate Muse follow-up. Refresh writes remain unqualified. |
| Muse, configured absent/native | Managed Muse resolves to effective file; inspect the managed file under the same metadata-only rules as explicit file. | Native global Keychain presence does not establish managed readiness. Do not rewrite the configured selector or guess fallback. |
| Pi | Inspect adapter-declared `auth.json` and any verified native link under §7.4. | Unknown source/backend stays unknown. No Pi login wrapper is added. |
| OpenCode | Report unknown, source/reason `ambient`, backend `unknown`. | Authentication is outside the swapped config home. No home-local candidate is invented. |
| Node/helper | Use protected registration/accessibility metadata under the separately adopted source policy. | Registration is not token validity. No helper secret output is requested. |
| Broker | Use configured lease-source metadata under its authority contract. | Unreachable/unauthorized observation is unknown; never a local-login fallback or lease request. |

For Claude, the service is `Claude Code-credentials-` followed by the first
eight lowercase hexadecimal characters of SHA-256 of the **exact**
`CLAUDE_CONFIG_DIR` string exported by the launcher, without an additional
realpath, symlink or path normalization. Use the service/account convention
of environments §7.4, including account `$USER`. If
that identity or vendor path interpretation cannot be established, report
unknown rather than false absence. The supplied Claude Code 2.1.299 macOS
measurement establishes session dependence, not qualification of every reader.
A daemon inherits its starting session's capabilities; transport name alone
is not a capability test. Guidance MUST say to log in from the same kind of
session as the launcher and recompute readiness in a different session.

An explicitly admitted inherited environment source can be present from
nonempty-variable existence alone; values MUST NOT be printed or copied.
Under node/broker policy a competing inherited source instead reports unknown
(`source-conflict`) and retains the executor's source-conflict refusal.
Source-policy and broker requirements do not become adopted merely by this
amendment referring to them; their pending revisions retain their own gates.

### 1.2 Aggregate behavior and migration

Plain status exits 0 after rendering a matrix, even with absent/unknown login;
operational failure to produce the matrix is nonzero. `env status --check`
MUST exit 0 only when all existing currency checks pass and **every**
participating login row is present. Otherwise it exits 1, still emitting all
available rows. Unknown is never satisfied evidence.

This deliberately adopts the CIP's strict aggregate: a participating OpenCode
row currently makes `--check` and prepare incapable of returning 0. Such a
profile can still render ordinary status and use explicit install/resolve;
no new login gate is added to launch. This cost is accepted to avoid claiming
unobserved readiness, rather than silently excluding an adapter. A future
ambient-source qualification or an explicit participation change is separate
work. Rollout documentation MUST announce this impact.

For example, current + present passes; current + absent fails; current +
unknown fails, including ambient OpenCode; non-current + present fails.
Previously currency-only scripts MUST account for the stricter check. Existing
profiles retain native selection and their current-profile markers.

## 2. User-owned credential-store policy

The OPTIONAL machine knob is `credential_store.<profile>.<env-id>` in the
`environments` configuration object; its default is `native`. The selector
map follows
[`credential-store-config-v1`](../schemas/login-readiness-v1/credential-store-config-v1.schema.json).
It is a subtree schema, not a new complete manager-config revision.
The machine CLI spelling is
`curator env config set credential_store.<profile>.<env-id> native|file|keychain`. Every
other configuration member retains its previous meaning. Closed older
manager-config versions MUST reject this new member. The complete
`manager-config-v5` carrier imports this subtree under
`environments.credential_store`; [containing carriers](rc7-carriers.md)
allocates it without changing manager-config versions 1–3.

Profile packages, overlays, system locks and repositories MUST NOT select a
store, credential source or account. This knob is user-owned and not lockable;
existing isolation locks continue to apply. Resolve source → store → isolation
admission → link strategy, in that order.

| Adapter | native | file | keychain |
|---|---|---|---|
| Codex | Native `config.toml`; absent selector means file; no override. | Typed `cli_auth_credentials_store` override `file` at both login and launch. | Typed override `keyring` only on a qualified macOS backend; otherwise refuse. |
| Muse (managed) | Configured absent/native resolves to effective **file**, without rewriting the configured selector. | Matching literal `TBH_CREDENTIAL_BACKEND=file` at login and launch. | Refuse `environment_credential_store_unsupported`. |
| Claude | Session-qualified native choice. | Refuse: no established force-file interface. | Refuse: no established force-Keychain interface. |
| Pi/OpenCode | Preserve existing behavior. | Refuse pending a qualified mapping. | Refuse pending a qualified mapping. |

A Codex explicit file override supersedes §7.4's native-only selection rule
for home-owned authentication. Isolated file is admitted; native keyring,
native auto and explicit keychain retain isolated refusal pending per-home
scope qualification. Shared file requires a compatible native file source;
an old `auth.json` under native keyring/auto MUST NOT be resurrected as shared
login. Curator MUST NOT rewrite either native or managed `config.toml`.

Changing selector does not migrate ownership, delete credentials or discard
login. Recorded link/backend conflicts require existing inspect → plan → apply
migration before launch; repair cannot silently migrate. Node/helper/broker
sources refuse non-native home-store overrides as inapplicable. Unsupported
mappings never fall back to native. Claude refusal includes the session rule
and the explicitly selected environment-token alternative.

Muse file admission for isolated/shared is owner decision D10, but its
normative admission/default/native-compatibility table belongs to the separate
Muse CIP. This amendment supplies grammar and transport, not a second
admission rule or a refresh-safety claim.

### 2.1 Fragment projection and package boundary

[`store-projection-v1`](../schemas/login-readiness-v1/store-projection-v1.schema.json)
freezes a **projection**, not an executable launch fragment: `environment`,
a closed `credential_store` object with `selection` and, for explicit Codex,
one `config_overrides` member, plus `env` containing only backend literals
(the home-path variables are omitted from this projection).

The frozen standalone projection retains its original native shape. Managed
Muse is the exception: configured absent/native maps to effective file before
projection. Its generic native shape is not a second Muse admission rule. Codex file
and keychain require exactly `cli_auth_credentials_store: "file"` and
`"keyring"`, respectively. Muse file requires exactly
`TBH_CREDENTIAL_BACKEND: "file"` in `env`, with no Codex override. Unknown
keys, missing or contradictory projections MUST be rejected. Structural
admission of Codex keychain does not prove platform qualification or isolated
admission. Those semantic gates still apply.

The allocated [v5 full fragment](rc7-carriers.md#3-single-payload-and-producerconsumer-transition)
MUST retain §10.2's closed
registry/path rules except for this **single** non-path literal: Muse file
selection carries `TBH_CREDENTIAL_BACKEND=file`, derived only from effective
machine policy. Muse still carries all four XDG paths with one protected
parent; `HOME` remains forbidden. The §10.3 package boundary continues to
forbid profile-selected names, literals, retargeting and source selection.
The literal is not a package-controlled passthrough variable.

Revisions v1–v3 remain closed and MUST reject both the new policy member and
the Muse literal. The containing publication allocates v5 for the single
Codex payload;
v4 retains its existing transport unchanged. Old readers MUST reject the new
token, never drop required policy or downgrade. The frozen standalone
`store-projection-v1` is not a v5 full-envelope validator; v5 imports selection
as agreement metadata and carries Codex argv only in `codex_settings`.

Curator projects policy; the launcher applies it without reading home files
or inferring stores. Codex argv uses `-c cli_auth_credentials_store="file"`
or `-c cli_auth_credentials_store="keyring"`; Muse gets the literal environment
variable. Both direct and hosted paths MUST apply identical policy.
Conflicting explicit operator argv/backend overrides MUST refuse, never win
by argv order. For managed Muse, the mandatory file literal overrides ambient
backend variables; inherited credential-source conflicts remain separate and
retain their source-policy refusal. The [one Muse decision table](rc7-carriers.md#4-one-muse-decision-table)
applies at resolve, login and every launch path. No shell command string
is admitted.

## 3. `env login`

`curator env login <env-id> [--profile <name>]` uses §10.1 canonical lookup.
It requires an installed profile, trusted current home and supported adapter.
It MUST NOT install, repair, migrate or activate a profile. Stale homes refuse
with the existing resolve diagnostic and repair guidance.

Home-owned login requires isolated mode, even for an already-present direct
login request. Shared mode MUST refuse before exec, with native-login guidance;
it MUST NOT write through a shared link. Claude macOS shared remains refused.
Resolve a trusted machine executable outside profile-owned bins and execute
argv directly from a neutral directory with only the required home/store
projection: `claude auth login`, `codex login`, or `muse login`. No Pi/OpenCode
wrapper, arbitrary vendor args, stdin-key mode or shell string is admitted.
Existing source conflicts refuse before exec; do not strip a selected source
or count an environment token as post-login home readiness.

Require terminal input **and** output and no headless/CI marker. Missing
interactivity is a usage refusal. The child owns terminal/browser I/O;
Curator MUST NOT capture, parse, log or persist credential-bearing output,
callbacks, stdin or environment values. Transcript capture MUST be disabled
for this path. Project tools, MCP and prompt channels MUST NOT be activated.

Recompute metadata after the child exits and print only a sanitized summary.
Exit 0 requires child exit 0 and present home readiness; exit 1 means policy
or resolve refusal, or child success followed by absent/unknown; invalid usage
or non-interactivity exits 2. Propagate a nonzero child exit unchanged and use
the platform's ordinary signal convention. Diagnostics MUST distinguish child
failure from Curator refusal, including overlapping numeric exits. Do not
logout, remove vendor files or copy between stores on failure/cancellation.

Claude guidance repeats the same-session rule. An intentionally enrolled
`setup-token` source delivered as `CLAUDE_CODE_OAUTH_TOKEN` through the protected
source contract is an alternative for inference, not a forced file backend
or Remote Control credential. This wrapper never collects it. A user without
a login Keychain cannot be repaired by forcing Claude file storage.
Node/helper sources refuse home login and provide source-specific enrolment
guidance. Broker login routes only through the separately authorized operator
enrolment ceremony; unauthorized callers refuse. Status itself never enrols
or acquires a lease. No new broker wire or custody guarantee is added.

## 4. `profile prepare`

`curator profile prepare <source-or-name> [--non-interactive]` selects an
installed name's existing lock, otherwise the same explicit source forms and
default naming as `profile install`. Ambiguous bare names refuse; do not guess
a remote URL. Existing trust/audit/install gates remain required.

Interactive prepare MUST:

1. Install only if absent, preserving existing locks/snapshots; updating needs
   explicit `profile update`.
2. Preserve machine-current and all scoped-current selections. Activation
   remains explicit `profile use`.
3. Enumerate every participant from the lock and effective machine policy;
   resolve/repair through §10.1 without bypassing trust, isolation, migration
   or credential conflicts. Never omit an inconvenient participant.
4. Read metadata. Only absent, supported, isolated, home-owned authentication
   can enter §3's ceremony. Shared/native absence gives native-login guidance;
   external sources give enrolment guidance. Unknown MUST NOT trigger login;
   present MUST NOT trigger repeated login.
5. Collect independent errors and recompute all rows, with environment,
   currency, login, source, store/backend, caller-session scope and next action.
   After cancellation, start no further ceremonies.

Completed transactions and vendor-owned writes stand on partial failure; no
whole-profile rollback is promised. Release mutation locks before browser
interaction. Revalidate home/source/selector before exec and before reporting;
changed inputs stop the affected operation rather than redirecting login.
An installed, current, present profile causes no install, repair, activation
or login writes on repetition. Retry addresses only remaining admitted needs.

Explicit or detected non-interactivity is strictly report-only: no fetch,
install, repair, activation, browser or login. Resolve existing participants
read-only. A missing profile reports installation required and participation
unknown; an empty invented table MUST NOT count as success.

Exit 0 requires every participating home current and every login present;
missing/unknown readiness, unresolved participants, failed operations or
cancellation is nonzero (aggregate failure 1; invalid arguments 2). Child
failure details remain sanitized per row; do not return whichever child exit
happened last. OpenCode's deliberate strict-aggregate limit is §1.2.

## 5. Diagnostics and security

| Condition | Diagnostic |
|---|---|
| Unsupported Curator selector value, adapter/platform mapping, or inapplicable non-native override | `environment_credential_store_unsupported` |
| Unsupported **native** storage selector | Existing `environment_credential_unsupported`, unchanged |
| Existing isolation, native-sharing, source, migration, trust or stale-home refusal | Retain the corresponding existing diagnostic; no success fallback |

No new code is allocated for a vendor child exit or a readiness reason.
Existing numeric command exits are specified in §§3–4. Readiness metadata MUST
NOT be used to authorize another session, remote destination or snapshot.
A presence observation has a TOCTOU bound; real authentication failure belongs
to the subsequent tool invocation. Credentials MUST NOT be copied into snapshot
archives based on a caller-side present row. Existing source-binding,
child-secret filtering and Codex single-refresh-owner gates remain unchanged.

## 6. Conformance

The [separate corpus](../conformance/login-readiness-v1/README.md) contains
structural positives/negatives and required semantic rows. Schema validation
proves closed grammar, not safe Keychain access or real CLI behavior. Consumer
implementations MUST exercise the real status/prepare/login and direct/hosted
composition paths for the semantic rows, and retain reviewer regressions.
Metadata fixtures do not qualify platform probes or Muse refresh safety.

## 7. Containing publication and deferred qualification

[Containing carriers](rc7-carriers.md) publishes manager-config 5,
`env-status-v1` and fragment 5 together with Codex carriers. Released bytes
remain unchanged; unsupported identities or delivery MUST refuse. Optional
vendor diagnostics remain a later explicit command,
never a hidden status fallback. Metadata-reader platform qualification, Windows
backends, Codex keyring identity/precedence, Muse refresh, broker
adoption and destination authentication remain with their owning follow-ups.
This leaf decides no new snapshot, broker, tool custody or credential transport.

## 6. Adopted local node source

[Local setup-token revision 1](local-setup-token-source.md) specializes §§1–4
without widening `login-row-v1`: Claude node uses node/native/file/caller
(or unknown backend when unestablished). Its §4 table distinguishes successful
absence from denied/unsafe/incomplete metadata, empty candidates and conflicts.
The full status v2 successor enforces that relation; status 1 remains frozen.
Registration lifecycle and route capability do not enter readiness: a known
expired candidate can remain present, while exec refuses. Status never reads
material or executes an agent. Node env login refuses
`credential_source_enrollment_required`; prepare neither enrolls nor invokes
native login for node absence/unknown, and retains current+present aggregate
semantics. Config v6 selects only user-owned source policy, and node mode
requires native home-store selection. Package/lock authority remains forbidden.
