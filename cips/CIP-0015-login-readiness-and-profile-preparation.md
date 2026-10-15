# CIP-0015: Login readiness and profile preparation

- **Status:** Accepted
- **Decision:** owner decision 2026-10-15; implementation remains separately tracked
- **Normative text:** [Login readiness revision 1](../protocol/login-readiness.md) §§1–7; [environments](../protocol/environments.md) §§7.4, 9.8, 10.2, 10.3, 12 and 12.1; [Decision 0024](../decisions/0024-login-readiness-and-profile-preparation.md)
- **Owner:** orchestrator; decision: operator
- **Created:** 2026-10-15
- **Related:** [CIP-0003](CIP-0003-claude-managed-home-credential-modes.md) (credential modes); [CIP-0010](CIP-0010-credentials-setup-token-and-inherited-auth.md) (setup-token and inherited authentication); [CIP-0011](CIP-0011-credential-broker-and-agent-users.md) (broker); owner decisions 2026-10-15 (D1, D7–D11, D13)
- **Affects:** environments §§7.4, 9, 10, 12 and 12.1; manager configuration, status output and launch-fragment contracts; curator; curator-agent-launcher; skill-agents-management; skill-project-management

## Summary

Curator reports `login: present | absent | unknown` for each profile ×
environment and provides one command to prepare a profile for later launches.
`curator env login` invokes the tool's own interactive login in its managed
home, while `curator profile prepare` installs if necessary, resolves the
participating environments and offers missing home logins without changing
the current profile. A user-owned credential-store selector lets Curator
choose supported native, file or Keychain storage and convey that choice
to the launcher. Readiness is metadata about the selected source in the
calling session, never proof of a valid subscription or a successful turn.

## Motivation and user stories

- An operator prepares a profile once before spawning agents and sees which
  environments still need attention, instead of discovering login prompts
  independently inside each spawn.
- A desktop login must not be reported as usable by an ssh-launched worker
  merely because both processes run under the same OS user.
- An operator selects file storage for an unattended Codex or Muse home
  without Curator rewriting the tool's configuration or handling tokens.
- A CI caller asks what is missing without opening a browser, provisioning
  a home, changing the current profile, or starting a login ceremony.
- A broker-backed profile reports its configured lease source rather than
  suggesting that each agent account should acquire its own vendor login.

These requirements implement owner decision 2026-10-15 (D7),
owner decision 2026-10-15 (D8) and owner decision 2026-10-15 (D9).
Curator owns home verification and readiness; the launcher applies the
fragment and the plan, without independently inspecting home contents
(owner decision 2026-10-15 (D1)).

## Current state

### Specification and implementation pins

Specification claims below refer to curator-spec `d34d8a6`, release candidate
1.0.0-rc.14. Implementation claims refer to curator `00fec196`, the brief's
main-branch pin; a newer local branch tip is not substituted for that pin.
Section references are to `curator-spec/protocol/environments.md` unless
another document is named. This section describes the pre-adoption baseline;
Design records the accepted direction. The Normative text pointer identifies the frozen leaf-1 contract;
acceptance does not claim implementation shipment.

- §7.4 separates credential passthrough from non-credential provisioning
  seeds and defines `shared` and `isolated` as native-store sharing choices,
  not account, process or filesystem isolation. Its per-adapter table covers
  Claude, Codex, Pi, OpenCode and Muse, including credential-link liveness,
  unreadability, detach and explicit-migration rules.
- The §7.4 Claude row describes macOS per-home Keychain items and Linux
  `.credentials.json` links. Its historical fallback observation does not
  establish a universally Keychain-backed login. The Codex row derives
  storage from native `config.toml`: absent `cli_auth_credentials_store`
  means `file`; `keyring` and `auto` refuse isolated admission pending
  qualification. The recorded write-through observation is Codex 0.153.2.
- The §7.4 Muse row describes a file link and unmeasured refresh writes.
  This is insufficient to describe the default Keychain behavior measured
  in Muse 1.4.8 below. Existing admission and the newer file-backend decision
  need a separate Muse credential-store admission CIP; this draft does not
  silently replace that adapter's admission contract.
- §10.1 defines read-only resolve and explicit `--repair`; neither launches
  a tool. §10.2 defines closed fragment revisions 1–3 and §10.3 restricts
  environment transport. Specifically, §10.2 restricts `env` to registry-declared
  managed-home paths (Muse v3 has exactly four XDG variables); §10.3 requires
  absolute values below the environments root and forbids profile-selected
  variables. A Muse backend literal needs an explicit successor amendment,
  never an extra variable in v1–v3. §12 defines the status matrix and makes `--check`
  non-zero for non-current rows. There is no login-readiness row there.
- §12.1 includes `isolation.<profile>.<env-id>` and other machine knobs,
  but no `credential_store` knob. §12.2 permits isolation locks; it does not
  give packages authority to select credential material.
- `curator/internal/envprofile/status.go:47–75` defines `HomeState` without
  a login member; `:214–226` defines the homes matrix and notes.
  `:342–343` adds standing Muse and OpenCode caveats, not login evidence.
  `:1137–1150` already detects tool versions, reporting unknown on failure.
- `curator/internal/envprofile/managed.go:2486–2504`,
  `firstResolveNotice`, tells Claude homes to log in on first use and Codex
  homes to log in unless native credentials are shared. It also records
  remaining first-run steps and Muse uncertainty; it does not perform login.
- `curator/docs/environment-config.md:81–138`, “Logging in to managed
  homes”, documents manual resolve followed by `claude auth login` and the
  current isolation table. The same section explains session-dependent Keychain
  access and the environment-token alternative. It does not implement
  `curator env login` or `curator profile prepare`.

### Measured authentication surfaces

The following store facts are supplied measurements dated 2026-10-14 in
the owner-decision record, not new authentication probes by this proposal.

| Tool and measured platform | Established fact | Bound |
|---|---|---|
| Claude Code 2.1.299, macOS 15 | A Keychain-capable session saves to `Claude Code-credentials-<hash>`, where the suffix is the first eight hexadecimal characters of SHA-256 of the config-dir path. Without that access, an ssh-origin session saves `<home>/.credentials.json` at 0600. | The stores do not see each other. A user without a login Keychain cannot save this login. A daemon inherits its starting session's access. |
| Claude Code 2.1.299, macOS 15 | `claude auth status --json` reports `loggedIn` and `authMethod` without a model call. `CLAUDE_CODE_OAUTH_TOKEN` wins over home login, writes nothing and reports `authMethod=oauth_token`. | A status command can consult authentication internally. The token is inference-only; Remote Control refuses it. |
| Muse 1.4.8, macOS 27 | Default login uses global Keychain service `ai.meta.dev.credentials`; `auth.json` is fallback. Missing Keychain access can prevent saving. | Default storage is not per managed home. A surviving file link alone does not establish effective authentication. |
| Muse 1.4.8, macOS 27 | `TBH_CREDENTIAL_BACKEND=file` saves `$XDG_CONFIG_HOME/muse/auth.json` at 0600 and later runs use file storage with zero Keychain access; a link to another home's file works. | Refresh write behavior is unmeasured. `META_API_KEY` leaves the store untouched; minted keys through `exec --api-key-stdin` bill the subscription. |
| Codex, §7.4 evidence | `cli_auth_credentials_store` selects storage; absent means `file`. | No new keyring-scope or refresh measurement is asserted here. |

Help-only inspection on 2026-10-15 found the following interfaces. No login,
logout, credential read or actual authentication-status command was run.

| Installed CLI | Help inspected | What it establishes |
|---|---|---|
| Codex CLI 0.162.1 | `codex login --help`; `codex login status --help` | `login status` exists. Neither inspected help advertises a JSON output flag. Login accepts `-c key=value` overrides and separate stdin credential modes; this CIP does not invoke those stdin modes. |
| Muse Code 1.4.8 (1.4.8-R6256.1) | `muse --help`; `muse auth --help`; `muse login --help` | Top-level `login`, `logout` and `auth` exist; `auth` documents `set --api-key-stdin`. Login requests browser approval and documents `META_API_KEY` priority. No login-status command is advertised in these help surfaces; an undocumented one remains unconfirmed. |
| Claude Code 2.1.300 | `claude auth status --help` | JSON is the default status output; text output is also offered. The store measurements above remain explicitly pinned to 2.1.299. |

### Relationship to previous proposals

CIP-0003's operative disposition and CIP-0010 C1–C3/C6 retain per-home,
node/token and helper sources, protected binding, no silent fallback and
explicit migration. CIP-0010 Revision 2.2 distinguishes source-policy v1's
per-home default from v2's required explicit entries. Its inherited Claude
authentication means an intentionally enrolled setup-token, not extraction
of the native login. Its first node backend is a protected file, separate
from the vendor's per-home credential-store backend proposed here.

CIP-0011 §§1–3 and §5 retain broker-owned enrolment, grants, lease delivery
and the Codex auth owner. Readiness here cannot replace those authority
checks or imply that a local file supplies a broker credential.

This CIP adds orchestration, metadata reporting and the vendor-store knob.
On adoption, it supersedes only §7.4's rule that Codex storage selection
always comes from native configuration when an explicit Curator override is
selected, and expands §12's check semantics as stated below. It does not
supersede CIP-0003/CIP-0010 source policy, CIP-0011 custody, credential-link
ownership, or their no-copy and no-fallback requirements. The Claude session
facts refine the old backend description; they do not authorize exporting
Keychain bytes. Muse admission is a named follow-up, not an implicit change.

## Design

### Options considered

Each question has a recommendation below. “Security” includes the bound the
option can honestly promise, rather than treating presence as authorization.

| Question | Option and mechanism | Pros | Cons and security |
|---|---|---|---|
| How status derives login | A. Metadata-only source inspection | No agent auth process, network or secret payload; fits D7. | Existence cannot validate tokens; failures must remain unknown. **Recommended.** |
| How status derives login | B. Run each vendor's status command | Better effective-source diagnostics, especially Claude. | Vendor code may read secrets, prompt, write caches or change output; no advertised uniform machine format for all tools. Not recommended for ordinary status. |
| How status derives login | C. Attempt an authenticated turn | Demonstrates one request at one instant. | Cost, network, refresh and side effects; contradicts metadata-only D7 and is unsuitable for status. |
| Scope of readiness | A. Calling-session observation | Honest about Keychain access; no privilege crossing. **Recommended.** | Cannot promise a launch from another session succeeds; callers must compare session kind. |
| Scope of readiness | B. Cache a machine-wide last successful login | Fast and convenient. | Stale, crosses desktop/ssh visibility and can claim another session's capability. No secret bytes, but misleading authority. |
| Shared-mode login | A. Refuse before starting a vendor process | Prevents accidental mutation through a native link. **Recommended.** | Operator must log in natively or explicitly migrate to isolated. |
| Shared-mode login | B. Return success with a no-op message | Convenient repeated preparation. | A direct login request looks successful despite no login attempt; risks treating absence as satisfied. |
| Prepare activation | A. Prepare without making current | Safe for automation and multiple profiles. **Recommended.** | Operator uses explicit `profile use` if activation is wanted. |
| Prepare activation | B. Install and make current | One onboarding command. | Changes unrelated default launches and scoped selection; increases mutation and recovery scope. |
| Non-interactive prepare | A. Report only, including installation/resolve needs | Predictable CI; no hidden acquisition or login. **Recommended.** | Cannot provision a missing profile until an explicit interactive preparation or install/resolve step. |
| Non-interactive prepare | B. Install/repair but skip login | Useful headless provisioning. | “Check” would mutate and fetch; harder consent and failure semantics. Use existing explicit install/resolve commands instead. |
| Credential-store default | A. `native`, preserving vendor selection | Existing logins retain selection; no implicit migration. **Recommended.** | Operators must select `file` explicitly for predictable supported automation. |
| Credential-store default | B. `file` for every supported managed home | Consistent unattended behavior. | Silently changes existing Keychain selection; Claude has no such switch; risks misleading migration. |
| Credential-store transport | A. Closed typed policy in fragment; Muse backend in fragment env | Curator owns selection; consumers apply data. **Recommended.** | Needs coordinated schema and consumer publication, with refusal by old readers. |
| Credential-store transport | B. Rewrite vendor config or let launcher inspect it | Fewer fragment changes. | Violates ownership, risks clobbering tool state and contradicts D1/D9/D13. |

### Recommendation

#### 1. Readiness is presence evidence in the calling session

Add a `login` value for every participating profile × environment row:

- `present`: metadata establishes a candidate for the selected source that
  this calling session can access under the adapter's qualified rules.
- `absent`: inspection of the selected source completed and established
  that no candidate exists. A missing home may establish this only when the
  source is known to be exclusively home-local and its parent is readable.
- `unknown`: inaccessible or ambiguous store, unsupported metadata probe,
  conflicting sources, untrusted home, unqualified backend, or failed read.

`present` never means unexpired, correctly scoped, refreshable, subscribed,
or inference-tested. No credential bytes, account identities or token
digests enter the row. Display the evidence source, session scope and
reason beside it; never collapse `unknown` to `absent`.

The login reader MUST NOT invoke an agent binary, request secret data from
Keychain, open a credential file for content, or attempt network access.
Use a non-interactive Keychain metadata query by the adapter's service
identity with data return disabled. A denied query, locked store, timeout
or unavailable API is `unknown`, not item-not-found. Implementations must
qualify that metadata lookup itself does not prompt or unlock a store.
If they cannot do so, that backend remains `unknown`.

For a file, verify the protected parent, entry type, expected link identity
where shared, ownership and private permissions using metadata. A nonempty
regular candidate at the approved destination is `present`; a zero-length
file is `unknown`, since it can be an interrupted write. A successful lookup
with no entry is `absent`. Permission denial, unexpected links, directories,
unsafe ownership or inability to establish accessibility are `unknown`.
Do not parse JSON or claim that nonempty bytes have valid vendor structure.

Only an expected, verified shared link may lead to the native credential
candidate, and only its metadata is inspected. Passthrough currency remains
an independent gate: a detached link is not repaired by status, and a file
elsewhere cannot make that home current. No metadata result is cached as
an authentication fact in a marker or installed profile.

| Adapter/source | Derivation and source reported | Unknown cases and limits |
|---|---|---|
| Claude, macOS, per-home/native | Establish the calling session's Keychain capability non-interactively. For a qualified Keychain-capable session, query the suffixed service's metadata using the exact exported `CLAUDE_CONFIG_DIR` string and §7.4 service/account (`$USER`) naming; uncertain derivation is unknown, never absent. For a qualified fallback session, inspect `<home>/.credentials.json` metadata. | A negative capability result must distinguish a qualified no-access session from a failed probe. An item visible to another session cannot satisfy this row. If the effective store or vendor fallback precedence cannot be established, report unknown. Never try the other store merely to obtain present. |
| Claude, Linux, per-home/native | Inspect the managed `.credentials.json`, or its verified native passthrough under shared. | No new refresh safety claim; bad link or unreadable target stays unknown/non-current. Windows remains unknown pending qualification. |
| Codex, effective file | Inspect managed `auth.json`, or the verified native link for shared. | Source selector must first be resolved. File existence does not prove JSON validity or login method. |
| Codex, effective keyring or auto | Report unknown until a metadata-only, nonprompting store identity and precedence probe is qualified. | Do not assume per-home keyring scope, guess from a file, or parse human `login status` output. Existing isolation refusal remains. |
| Muse, explicit file | Inspect `$XDG_CONFIG_HOME/muse/auth.json` in the managed fragment environment, with the shared-link rules if admitted by the Muse follow-up. | File-backend login is measured; refresh writes remain unqualified. |
| Muse, native Keychain selection | Query metadata for `ai.meta.dev.credentials` only when selected backend and nonprompting access are established. | The item is global, not per-home. A failed query cannot trigger file fallback; uncertain fallback precedence yields unknown. |
| Pi | Inspect the adapter-declared `auth.json` and verified native link using §7.4 metadata rules. | Unsupported source selection or unqualified backend yields unknown; this CIP adds no Pi login command. |
| OpenCode | Unknown: authentication is ambient outside the swapped config home in the current contract. | No home-local credential candidate is invented. A future adapter can qualify a source-specific reader. |
| Explicit node/helper source | Use only protected source-registration and accessibility metadata under CIP-0010; source must be unambiguous. | Registration is not token validity. Unavailable helper readiness or unknown metadata yields unknown; never invoke a helper just to obtain secret output. |
| Broker source | Report the configured lease source and metadata-only broker readiness under CIP-0011. | Unreachable or unauthorized observation is unknown, never absent and never permission to acquire a local login. |

The adapter derives this after effective source selection, not by scanning
all possible stores. An explicitly admitted inherited environment credential
may supply `present` from nonempty-variable existence only, with source
`environment`; its value is neither printed nor copied. Under node/broker
policy, a conflicting inherited credential instead yields `unknown` and the
existing source-conflict refusal. A home file must not hide that conflict.

Every observation is for `session: caller`. Claude additionally reports
`keychain_access: available | unavailable | unknown`; these are proposed
metadata labels, not a claim that “ssh” always means unavailable. A daemon
started from a desktop session may differ from one started through ssh.
The operator rule is: **log in from the same kind of session the launcher
runs in**. Readiness in another session must be recomputed, not carried as
a boolean capability in the launch plan.

The standalone row schema freezes the following shape; integration into a
containing status revision remains coordinated publication work:

```json
{
  "schema_version": 1,
  "profile": "example",
  "environment": "claude_code",
  "current": true,
  "login": "unknown",
  "login_detail": {
    "source": "per-home",
    "store": "native",
    "backend": "unknown",
    "session": "caller",
    "keychain_access": "unknown",
    "reason": "metadata-unavailable"
  }
}
```

`store` records the effective Curator selector, while `backend` names the
observed selection (`file`, `keychain`, `environment`, `external`, or
`unknown`). `source` is a source class, never an account or secret. Omit
`keychain_access` for adapters where it is inapplicable. The normative row
schema publishes closed enums and stable reason labels;
these labels are distinct from diagnostic codes.

Keep content `current` separate from login readiness. Extend the aggregate
`--check` condition: it exits 0 only when all existing currency checks pass
and every participating login row is `present`. Either `absent` or `unknown`
makes it exit 1, with all available rows still emitted. Plain status returns
0 after a successfully rendered matrix even if some rows are absent or
unknown; operational failure to produce a matrix is non-zero. `--check`
therefore proves observed presence and currency, never successful inference.
This intentionally means a profile participating in ambient OpenCode cannot
currently pass check or prepare. Ordinary status and explicit install/resolve
remain usable; launch gains no login gate. The strict aggregate avoids treating
unobservable readiness as satisfied, and rollout guidance must name this cost.

#### 2. `curator env login`

Proposed syntax:

```text
curator env login <env-id> [--profile <name>]
```

Resolve the canonical environment and explicit or applicable current profile
using §10.1 lookup rules. Require an installed profile, a trusted current
home and a supported adapter. A stale home is a refusal with the existing
resolve diagnostic and an explicit resolve/repair hint; login itself does
not repair, install, migrate isolation, or change the current profile.

For home-owned authentication require isolated mode, even when readiness is
already present: the direct command is an explicit operator request to run
the vendor ceremony again. Under shared mode refuse before starting the
tool, state that login is owned by the native source, and name the native
login alternative without running it. Never write through a shared link.
Claude macOS shared refusal continues to apply independently.

| Adapter | Child invocation | Applied managed selection |
|---|---|---|
| Claude Code | `claude auth login` | `CLAUDE_CONFIG_DIR` from the fragment; only native storage is supported. |
| Codex | `codex login` | `CODEX_HOME` plus the selected launch-time `-c` storage override, when explicit. |
| Muse | `muse login` | Managed XDG roots plus `TBH_CREDENTIAL_BACKEND=file` for the file selector. Admission remains owned by the Muse follow-up. |

Do not accept arbitrary extra vendor arguments, token arguments, stdin-key
modes or a shell command string in this wrapper. Resolve the executable
through trusted machine tool selection, outside profile-owned binaries;
execute argv directly from a neutral directory so repository hooks, project
MCP and prompt channels are not activated as a side effect of login.
Use only the required home/store projection of the fragment, not agent-turn
permission or system-prompt flags. Curator directly invokes the tool; the
ordinary launcher is not a login implementation.

Before a per-home ceremony, refuse competing inherited credential variables
or settings sources under the existing source-conflict policy. Do not let an
environment token satisfy the post-login check for a requested home login,
and do not silently strip or replace an operator-selected source.

Require interactive terminal input and output and no headless marker before
starting a home login. Missing interactivity is a usage refusal; there is no
fallback to device-token collection by Curator. The child owns terminal I/O
and any browser ceremony. Curator MUST NOT capture, parse, log or persist
the child's credential-bearing output, callbacks, stdin or environment
values; disable session transcript capture for this path. The tool may
display its own short-lived approval code directly to the operator.

After the child terminates, recompute metadata readiness and print a
sanitized summary. A child exit of 0 with unknown readiness is not promoted
to verified login. No logout, cleanup of vendor credential files or
cross-store copying is attempted on failure or cancellation.

Proposed exit contract: 0 means the child returned 0 and readiness is now
present; 1 means policy/resolve failure or a successful child followed by
absent/unknown readiness; 2 means invalid usage or non-interactive invocation.
A non-zero child exit is propagated unchanged; a signal uses the platform's
ordinary signal-exit convention. Diagnostics distinguish child failure from
Curator refusal, since a vendor may also return 1 or 2. These are proposed
command semantics, not claims about current refusal-code allocation.

For Claude, repeat the same-session rule before login. If a launcher cannot
use that session's Keychain, the alternative is an explicitly selected
environment-token source: an intentionally minted `claude setup-token`
credential supplied at execution through the CIP-0010 protected source path
as `CLAUDE_CODE_OAUTH_TOKEN`. Curator does not collect it through `env login`
or insert it into a fragment. This is inference-only; Remote Control is not
required for swarm v0 (owner decision 2026-10-15 (D11)). An OS user without
a login Keychain cannot be fixed by forcing Claude file storage.

For a node/helper source, refuse home login with source-specific enrolment
guidance; do not silently replace the source with per-home. Broker handling
is the short specialization in §5 below.

#### 3. `curator profile prepare`

Proposed syntax:

```text
curator profile prepare <source-or-name> [--non-interactive]
```

An installed name selects its existing locked profile. Otherwise accept the
same explicit source forms and default naming rules as `profile install`;
an unresolved bare name is not guessed into a remote URL. Ambiguous naming
refuses with guidance to use an explicit source. Existing install/audit and
source-trust gates apply; prepare grants no waiver or implicit update.

Interactive preparation proceeds in this order:

1. Install only if the requested profile is not installed. Preserve an
   installed lock and snapshot; updating requires `profile update`.
2. Leave both machine-current and scoped-current selections unchanged.
   Preparation is useful for future spawns with `--profile`; activation
   remains the explicit `profile use` operation.
3. Enumerate every participating environment from the installed lock and
   effective machine policy, using Curator's existing adapter resolver.
   Resolve each with repair as needed under §10.1, retaining its existing
   trust, migration and credential-conflict refusals. Do not turn off an
   inconvenient participant to improve the result.
4. Read login metadata for each row. For `absent`, invoke the §2 login path
   only if the session is interactive, the adapter supports it and the
   selected source owns a home login. Shared/native absence yields a native
   login action; node/helper/broker sources yield their own enrolment action.
   Do not invoke a vendor home login for those sources.
5. For `unknown`, report the reason and the next explicit diagnostic or
   enrolment action; do not assume absence and do not start another login.
   For `present`, do not log in again. Failed or cancelled login does not
   erase prior credentials or roll back successful installation/repairs.
6. Recompute and print a table for all participants: environment, home
   currency, login value, source, effective store/backend, caller-session
   scope, and next action. Continue collecting independent resolve/read
   failures; after a cancelled login, start no further ceremonies.

There is no automatic whole-profile rollback: completed install and repair
transactions stand, and tool-owned credential writes remain tool-owned.
Release mutation locks before interactive login, then revalidate home,
source and selector before spawning and before reporting. If inputs change,
stop the affected operation rather than logging into a different home.
Prepare does not hold a global home lock while waiting for browser approval.

`--non-interactive`, or detected non-interactivity, is strictly report-only:
no install/fetch, repair, activation, browser launch or login. It resolves
existing participants read-only. For a missing profile, report installation
required and participation unknown; do not invent an empty successful table.
Explicit install and resolve commands remain available for automated writers.

Prepare exits 0 only when every participating home is current and every
login is present. It exits 1 for missing/unknown readiness, unresolved
participants or any failed operation; invalid arguments exit 2. Child login
exit details remain in the sanitized per-row result; the aggregate exit is
1 rather than whichever child happened to run last. Cancellation is non-zero.

Idempotence means an installed, current, present profile causes no install,
repair, activation or login writes on repetition. It does not freeze token
validity: a later metadata failure changes the report. After partial failure,
rerunning addresses only rows that still need an admitted operation.

#### 4. Per-profile credential-store selection

Add the user-owned machine knob:

```text
curator env config set credential_store.<profile>.<env-id> native|file|keychain
```

The default is `native`: preserve the tool's existing storage selection.
This names the vendor credential backend, not CIP-0010's node store. A profile
package, overlay, system lock or hostile repository cannot select a backend,
credential source or account. Existing `isolation` locks still apply.

| Adapter | `native` | `file` | `keychain` |
|---|---|---|---|
| Codex | Native `config.toml` selector; absent means file; no override. | Carry `cli_auth_credentials_store="file"` through the fragment policy and apply as `-c cli_auth_credentials_store="file"` at login and launch. | Map to `cli_auth_credentials_store="keyring"` on a qualified macOS backend; other platforms refuse this value pending mapping qualification. |
| Muse | No override; measured default is global Keychain with fallback. | Set `TBH_CREDENTIAL_BACKEND=file` in the fragment `env`, consistently for login and every launch. | Refuse until an explicit force-Keychain interface is qualified; default Keychain with fallback is not equivalent to forcing it. |
| Claude | Tool chooses Keychain or file according to session capability. | Refuse: no supported force-file switch is established. | Refuse: no supported force-Keychain switch is established. |
| Pi, OpenCode and other adapters | Preserve existing behavior. | Refuse until that adapter declares and qualifies a mapping. | Refuse until that adapter declares and qualifies a mapping. |

Unsupported Curator selector values or mappings use the new
`environment_credential_store_unsupported` code, never silent native fallback.
The existing `environment_credential_unsupported` retains its native-selector
meaning; the two conditions must not be conflated.
The Claude refusal explains the session rule and token alternative. Native
does not guarantee a specific backend and does not invent an environment
variable to steer Claude.

Resolve source → store → isolation admission → link strategy, in that order.
For home-owned Codex credentials, an explicit file override supersedes the
native-only selector rule. Isolated file mode is admitted; native keyring,
native auto, and explicit keychain retain the existing isolated refusal
until per-home keyring scoping is qualified. Under shared file mode the
native source must itself be the compatible file store; selecting file must
not resurrect a stale `auth.json` from a native keyring/auto configuration.
Incompatible native sharing is refused, not exported or copied.

Changing a selector cannot implicitly migrate credential ownership or
discard a login. Detect conflicts with recorded link/backend policy and
require the existing inspect → plan → apply migration before a changed
strategy launches. Curator does not read credential payloads during that
migration and never removes a vendor-owned file to make the new mode fit.

Muse `isolated` and `shared` admission through explicit file backend is
decided optimistically without awaiting refresh probes (owner decision
2026-10-15 (D10)). The separate Muse credential-store admission CIP owns
that table change, defaults, native sharing compatibility and its refresh
bound. This CIP supplies the selector and transport, not a second admission
implementation. Native remains the compatibility default here; prepare
reports the need for explicit file selection where the admitted Muse policy
requires it, and never changes the selector silently.

Proposed fragment policy is a closed `credential_store` object carrying
`selection` and, for Codex, one typed `config_overrides` entry for
`cli_auth_credentials_store`. Muse file selection also requires the matching
literal `TBH_CREDENTIAL_BACKEND=file` in `env`. The launcher validates their
agreement and refuses unsupported selection, missing override, contradictory
values or unknown keys. This proposal allocates neither a fragment revision
token nor an executable command-string field; coordinate the next revision
with the existing pending credential and Codex-settings work.

Curator resolves policy and emits only metadata. The launcher and
agents-management pass the typed override into Codex argv for interactive
and hosted launches, or apply the Muse literal env unchanged. They do not
read home files, infer stores, rewrite `config.toml`, or discover Curator
layout. Conflicting native arguments or inherited backend variables refuse
rather than winning by argv order. This follows owner decision 2026-10-15
(D9), and launch-time Codex settings follow (D13). Older fragment readers
must reject the new revision; no required policy may be silently dropped.

For node/helper/broker sources, non-native home-store overrides are refused
as inapplicable rather than selecting a competing login. Source injection
retains CIP-0010/CIP-0011 conflict checks at the executor.

#### 5. Swarm specialization

Under a broker source, `env login` means operator enrolment at the broker,
not vendor login in an agent home. Route through CIP-0011's authorized
operator ceremony; an agent or unauthorized caller receives enrolment
guidance and refusal, never widened authority. Readiness reports the lease
source and its observable metadata readiness; it neither acquires a lease
as a status side effect nor attests the next lease will be granted. Unknown
broker state stays unknown. The broker remains the owner of long-lived
credentials; no new broker wire fields or lease guarantees are defined here.

## Security considerations

The primary threats are secret disclosure by diagnostics, false readiness
from failed reads, credential-store confusion, and repository-selected login
execution. Status uses only bounded nonprompting metadata operations; no
secret bytes or digests enter JSON, markers, plans, board resources or logs.
Vendor status output is not a safe substitute for those operations merely
because its documented fields look harmless.

Curator validates protected home and selector inputs before invoking a
trusted executable. It never evaluates shell exports from profile content,
searches profile-owned bins for login, or enables project tools during the
ceremony. Direct terminal attachment excludes transcript collection; login
output and environment values must not be attached as evidence.

Presence is an observation with a TOCTOU bound. Another process may revoke,
replace or refresh a credential after status; the subsequent tool launch
owns real authentication failure. Metadata cannot prove JSON validity or
effective access on an unqualified platform. Keychain denial and read
failure never trigger an absent-source fallback or automatic login.

Shared mode remains a sharing choice, not account separation. The wrapper
refuses login through shared links, protects their identity, and never
converts a global Keychain item into a per-home credential. Credential-store
selection does not weaken executor binding, child-secret filtering or the
single Codex refresh-owner requirements of CIP-0010/CIP-0011.

## Compatibility and migration

Existing profiles keep native storage selection and existing current-profile
markers. No new selector entry, credential source, install or login is
inferred from reading status. A change of store or sharing policy requires
explicit migration when existing credential ownership would conflict.

Status JSON gains versioned, closed readiness metadata; consumers must use
the published status contract rather than parsing text notes. Existing
`current` retains content currency. `--check` becomes stricter on rollout:
automation that previously checked only materialization must account for
unknown or absent login. Announce this behavior change with examples.

Fragment publication is coordinated across spec, Curator and consumers.
Do not add unknown members to v1–v3 or assume an old launcher applies an
override. Login and launch use the same effective backend policy. The
manual resolve-plus-vendor-login path remains valid for native selection.
First-resolve guidance gains the prepare/login commands and session caveat.

Managed-home readiness is not snapshot or destination readiness. Owner
decisions 2026-10-15 (D4–D6) require per-session materialization; snapshot
transfer, destination paths and credential access remain that work's
contract. A caller-side present row cannot authorize a remote launch or
justify copying credential bytes into a snapshot archive.

## Specification changes

On adoption, in lockstep with implementation:

1. Amend environments §7.4 with store/source/isolation ordering, metadata
   readers and Claude's session-qualified backend facts; retain no-copy,
   passthrough liveness and explicit ownership migration.
2. Add `env login` and `profile prepare` to the manager/CLI lifecycle with
   interactivity, no-activation, report-only and exit semantics above.
3. Amend environments §12 with `login`, metadata scope, uncertainty, and
   aggregate check behavior; §12.1 gains the user-owned `credential_store`
   knob. §12.2 does not gain a credential-store or source-selection lock.
4. Amend §10.2 in the coordinated successor revision with the one closed
   Muse `TBH_CREDENTIAL_BACKEND=file` literal exception to path-only `env`;
   §10.3 continues to forbid profile-selected literals or variable names.
   Publish coordinated configuration/status/fragment schemas and conformance
   vectors, keeping v1–v3 unchanged. Use the new
   `environment_credential_store_unsupported` code for Curator selectors,
   retaining the native-selector code's existing meaning. Freeze the typed
   store policy with the existing pending fragment work before choosing its
   revision token; reject unknown semantics.
5. Mirror consumer obligations in curator-agent-launcher SPEC and
   skill-agents-management; task-board and the session host consume Curator
   outcomes without keeping their own home-content or login checklist.
6. Record D7–D9 adoption and the bounded supersession stated in Current
   state. Refer Muse admission to its separate CIP, and broker enrolment
   authority to CIP-0011 without changing either silently.

## Implementation plan

Ordered leaves use Fibonacci sizes; each leaf names its owning repository.
Leaf 1 is frozen by the Normative text above. Later leaves remain with their
owning repositories; no implementation shipment is asserted.

1. **curator-spec, size 3:** freeze status and store-policy grammar, CLI
   semantics and migration examples with pending fragment revisions. Add
   conformance rows for absence versus failure and old-reader rejection.
2. **curator, size 5:** add the user-owned selector, adapter mappings and
   metadata-only readiness behind the production status/resolve entry
   points. Qualify platform metadata probes; unsupported probes stay unknown.
3. **curator-agent-launcher + skill-agents-management, size 5:** consume the
   new typed fragment policy, apply Codex argv/Muse env for direct and hosted
   modes, reject conflicts and remove any duplicate home inspection.
4. **curator, size 3:** implement `env login` through the shared policy
   projection with trusted executable selection, direct terminal I/O,
   no transcript capture and post-login metadata reporting.
5. **curator, size 5:** implement profile preparation over existing install
   and resolve entry points; no activation, explicit partial results,
   report-only headless behavior and repeat-run idempotence.
6. **curator-spec + curator, size 3:** land the separately reviewed Muse
   admission follow-up using D10's file backend and explicit refresh bound;
   update first-resolve guidance and environment-config documentation.
7. **skill-project-management, size 2:** integrate preparation guidance and
   present/absent/unknown display without inspecting credentials or homes;
   preserve source/session scope in sanitized outcomes.
8. **curator + swarma-dispatcher, size 3:** wire broker-source enrolment
   routing and lease-source readiness via the existing authority boundary;
   dispatcher transports no new credentials and does not inspect homes.

## Test plan

The following tests and mutants are required implementation work, not
runtime evidence supplied by this documentation draft. Drive CLI entry
points and the actual launcher composition path, not uncalled helpers.
Retain every existing reviewer regression under its original name.

| Proposed named production-entry test | Negative or property exercised | Narrowing mutant it must kill |
|---|---|---|
| `TestEnvStatusLoginMetadataOnly` | Run status against fake secret-bearing stores and a tripwire agent executable; forbid content opens, secret API results, network and agent-auth invocation. | Permit only Claude auth status execution while leaving other adapters metadata-only. |
| `TestEnvStatusLoginReadFailureUnknown` | Permission denial, locked/denied Keychain, timeout, wrong entry type and incomplete metadata each report unknown; check exits 1. | Treat only file permission denial as absent while retaining other failures. |
| `TestEnvStatusClaudeCallerSession` | Desktop-origin and ssh-origin capability fixtures choose only the qualified effective store; unknown capability cannot select either. | Accept a Keychain item from another session when fallback metadata is absent. |
| `TestEnvStatusPresenceIsNotValidity` | Nonempty candidate is present with stated bound; empty file is unknown; no parsing or validity assertion. | Mark only zero-length regular files present. |
| `TestEnvStatusCheckIncludesLogin` | Current homes with absent and unknown rows fail check; all-present/current passes; plain status still emits the full matrix. | Fail check only for absent, letting unknown pass. |
| `TestEnvLoginSharedRefusesBeforeExec` | Direct login into a shared linked home starts no process and changes no native state. | Refuse Claude shared but allow Codex shared login. |
| `TestEnvLoginRequiresInteractiveTrustedChild` | Missing TTY, CI marker, profile-owned executable, stale home and unsupported mapping refuse before ceremony; output is not captured. | Enforce TTY only for stdin while permitting redirected stdout. |
| `TestEnvLoginChildResultAndPostRead` | Preserve child non-zero/signal status; child success plus unknown post-read returns 1 without fabricated present. | Treat only post-login unknown as success. |
| `TestPrepareAllParticipantsNoActivation` | Prepare a source and an installed name through real install/resolve paths; all participants appear, no current marker changes. | Enumerate only the machine-current adapter, dropping another participant. |
| `TestPrepareHeadlessReportOnly` | Non-interactive missing profile and stale homes report needs without fetch, write or child exec. | Allow repair of only stale Codex homes in report-only mode. |
| `TestPrepareUnknownNeverLogsIn` | Unknown source metadata and conflicting credentials do not start a login; shared absence only supplies guidance. | Auto-login only unknown Claude rows. |
| `TestPrepareIdempotentAndPartial` | Repeat after all-present success writes nothing; one failure retains successful repairs, reports every row and returns 1. | Re-login only already-present Muse rows. |
| `TestStorePolicyAppliedAtLoginAndLaunch` | Codex typed override and Muse env match at both paths and in direct/hosted composition; native config is unchanged. | Apply file override only at login, omitting it from hosted launch. |
| `TestStorePolicyRejectsUnsupportedAndConflicts` | Claude file/keychain, Muse forced keychain, isolated Codex keyring/auto, mismatched native sharing and user override conflicts refuse. | Refuse explicit keyring isolation but admit native auto, or accept only trailing conflicting Codex argv. |
| `TestBrokerReadinessDoesNotEnrolOrLease` | Unavailable observation stays unknown; unauthorized login/enrolment refuses and acquires no lease. | Treat only broker timeout as absent and trigger local login. |

Run the existing spec validator and property suites, adapter tests through
Curator's real CLI, and launcher direct/hosted tests. Platform qualification
covers macOS Keychain-capable and no-access sessions, Linux file stores,
denied metadata, symlink replacement races, cancellation and concurrent
policy changes. Windows backends remain unknown/refused until qualified.
Use disposable synthetic credentials; never attach real vendor output.

For each executed mutant, report mutant, narrowed bound, named failing test
and real exit code. A mutant without a named failing test survives; state
the uncovered bound rather than declaring it killed. Report coverage as
covered rows / declared rows, with native keyring scope, JSON validity,
token expiry, Muse refresh writes and future destination authentication
explicitly outside this presence-only contract. Metadata fixtures do not
prove a live Keychain or vendor-refresh capability.

## Open questions for the operator

1. **Adopt metadata-only presence with stricter `--check`?** Adopted by owner
   decision 2026-10-15: §1 and its rollout notice. Alternative: keep currency-only check
   and add a separate readiness check flag; that preserves old scripts but
   weakens the single preparation/readiness gate. Neither option validates
   tokens. D7 fixes the metadata-only bound, not an inference guarantee.
2. **Keep `native` as the selector default?** Adopted: preserve existing
   native selection and require explicit `file` for supported automation.
   Alternative: default new Codex/Muse homes to file with a versioned opt-in
   migration; never change existing homes silently. Claude stays native.
3. **Require all participating rows for prepare success?** Adopted: yes,
   including unknown ambient adapters; report why they are unknown. This
   deliberately prevents a participating OpenCode profile from passing today,
   as explained in the normative aggregate and rollout guidance.
   Alternative: define a separate explicit profile participation change
   before preparing. Do not silently omit unsupported rows or add a success
   exception for one adapter.
4. **When should optional vendor diagnostics be added?** Recommended:
   keep them outside ordinary status and this first implementation. A later
   explicit diagnostic command can qualify output filtering, side effects
   and supported releases. No hidden `claude auth status` fallback is added.

The coordinated full fragment token and containing manager-config/status
revision numbers remain open with the pending fragment work. Standalone
selector, store projection and readiness-row grammar are frozen without
allocating those containing revisions or permitting v1–v3 extensions. Platform
metadata probes, Codex keyring scope, Muse admission/refresh and destination
readiness remain later-leaf qualification work.
