# CIP-0010: Credentials for managed launches: `setup-token` adoption, homes with inherited authentication, and the disposition of CIP-0003

- **Status:** Draft (revision 2, after the architecture review of 2026-10-08)
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-08
- **Related:** owner brief 2026-10-08 §8; [CIP-0003](CIP-0003-claude-managed-home-credential-modes.md) (Draft); [Decision 0017](../decisions/0017-environment-credential-modes.md) (`shared|isolated`, Q4, Q7 no-copy); environments [§7.4](../protocol/environments.md#74-credential-passthrough-provisioning-seeds-and-isolation), §10.3, §12.1–§12.2; wiki `research/harness-auth/RESEARCH.md` (2026-10-07) and `PLAN-expiry-check.ru.md`; wiki `session-host/architecture.ru.md` §7.3 (credential broker); VISION v1.3 LCH §7; [CIP-0008](CIP-0008-remote-worker-launch-mode.md), [CIP-0009](CIP-0009-donor-side-deployment-and-bridge.md); relux-works/remote-worker-harness `docs/session-mode.md` ("Login: the single auth owner")
- **Affects:** environments §7.4 and §12.1 (new user-owned knob), Decision 0013 (a required plan extension), Decision 0017 (Q4 evidence label; Q7 unchanged), the marker schema, curator (`env credential` commands, the Codex auth owner), curator-run/launcher, the final executors (session host, task-board spawn runner, the remote-worker supervisor)

## Revision 2: what the architecture review changed

- **F20:** "one `auth.json` = one live refresher" was wrong: `rwh` measured the refresh race between app-servers sharing one file (eight callers, one refresh with its lock, eight without). The Codex personal-plan node is now a **single auth owner** (one process holds the account lease and refreshes) that hands **external access tokens** to launches; launches carry no `auth.json` (C2).
- **F21:** no `isolation: bare`. `isolation` keeps its Decision 0017 meaning (native-store sharing); the credential **source** is a separate axis, `credential_source`, with its own per-harness storage and channel table; absent versus unreadable versus native-keyring cases are specified without silent export or fallback (C2).
- **F7:** the credential source is never selectable by a system lock (environments §12.2 is unchanged); it lives in the **user-owned** machine configuration; a package may state a non-authoritative requirement, never select a node (C3).
- **F22:** the executor capability `credential-injection/1` is a necessary gate, not an authorization: the final executor re-resolves a **protected binding** (`credential_binding/1`: executor peer identity, profile, harness, account label, channel, endpoint, approved executable digest, policy generation) at exec; injected names are reserved, conflicting sources refuse, the harness environment and the MCP children's environment are separated, and the effective-source check of the expiry plan is a qualification step; the text states honestly that an environment-delivered token is readable by the harness (C3, §Security).
- **F23:** CIP-0003 is not silently superseded: a clause-by-clause disposition table keeps its gates, precedence, protected-store reads, migration and no-fallback rules; the overstated "Claude cannot share a file on macOS at all" is corrected; the Codex keyring-per-`CODEX_HOME` fact is labelled as source inspection pending the live probe (Decision 0017 Q4); the stripped copy stays prohibited by Decision 0017 Q7 and is no longer offered as an option; setup-token enrolment is never permission to extract a native login (C6, §Options).
- **F24:** enrolment time is not mint time: a node records `issued_at` only when supplied and reports `expires_at: unknown` otherwise; error classification is typed and keeps its uncertainty; recovery is defined per persistence mode; `/login` is handled by shipping modes where it does not exist, not by a launch-flag table (C3).
- **F6:** the plan member is a required Decision 0013 §6.4 extension, coordinated with CIP-0008's schema table (C3).
- **F25:** the sequencing names slice 0, the minimal peer-authenticated broker interface across OS users, as the prerequisite of the owner's MVP; a per-user node alone does not deliver it (C7, §Implementation plan).

## Summary

Three related changes. (1) **Adopt `claude setup-token`** (`CLAUDE_CODE_OAUTH_TOKEN`) for tracked and headless launches behind explicit gates: the token is enrolled once into a per-user protected store under an *authentication node*, referenced by an opaque `source_ref`, re-resolved through a protected binding and injected into the harness process environment by the **final executor** only; the plan and the fragment never carry it. (2) **Homes with inherited authentication**: a managed home may start with no credential of its own and use the authentication of a node higher up (the operator's root login or a named account node) instead of a per-home Keychain login on macOS or a per-home `auth.json`; for Claude this is the enrolled token; for Codex it is an access token handed out by a single auth owner per account; each with stated limits. (3) **CIP-0003 disposition**: its `token` mode is the core of this CIP and should be accepted in a narrowed revision; its `shared-file` mode is replaced by the node; `per-home` stays the interactive default; `helper` stays for API keys; its gates, precedence, protected-store reads and migration rules are retained clause by clause. Priority: high, right after v0.15.0-rc.5, with slice 0 (the cross-user broker interface) first, because the owner's MVP, tracked spawns and remote workers depend on it.

## Motivation and user stories

- **Owner (2026-10-08):** "research and propose how to adopt `claude setup-token`, possibly behind special flags, for tracked and headless launches"; "a mode where a managed home starts bare but reuses the authentication of a root authentication session, or of a node higher up if the machine has several accounts, instead of a per-home Keychain login; for Codex likewise"; "state whether CIP-0003 is needed now, what is superseded, and its priority".
- **Tracked spawns** (task-board workers) today need a logged-in managed home per profile; on macOS each one is a separate `/login`, which is the pain the owner named on 2026-10-05.
- **Remote workers** (CIP-0008/0009) run under the donor's subscription: the donor enrols one token on their machine under the bridge identity; every launch of the lockdown harness receives it from the supervisor, and the harness never sees a store.
- **The MVP** (owners' call C15: one subscription, one machine, a chain of OS users) needs one place that holds a login and a per-launch injection path **across OS users**, which is the credential broker of architecture §7.3; this CIP specifies the node, the binding and the executor contract the broker speaks, and names the minimal cross-user interface as slice 0.

## Current state

Facts are measured, vendor-documented or source-inspected, with the label stated (RESEARCH §A–§E, 2026-10-07; curator v0.15.0-rc.4; environments §7.4; `rwh` session-mode):

- **Claude Code.** `claude setup-token` opens the browser flow and prints a one-year OAuth access-only token; it saves nothing. `CLAUDE_CODE_OAUTH_TOKEN` takes precedence over Keychain credentials for the whole session; it cannot be shortened, scoped or renewed in place ("generate a new one and restart"); revocation only in the claude.ai UI; `apiKeyHelper` accepts API keys or JWTs only; `--bare` never reads OAuth. On macOS a native login is a Keychain item keyed by `CLAUDE_CONFIG_DIR` (service suffix sha256[0:8]), so every managed home is its own login and `shared` is refused (`environment_shared_unsupported`); sharing the OS Keychain does not make two homes share an item. A plaintext `.credentials.json` path exists as the fallback (and the Linux form); CIP-0003 records synthetic linked-file reads for it and correctly withholds any refresh-safety qualification. Subscription logins are refresh-token families with single-use rotation: a copy that refreshes invalidates its siblings. Terms: no account sharing; `CLAUDE_CODE_OAUTH_TOKEN` in CI is documented practice. Whether the native Keychain lookup is suppressed when the environment token is present is the **effective-source check** of PLAN step 2: proposed, not yet measured.
- **Codex.** `auth.json` is rewritten in place (0600) and rotated at every refresh (5 minutes before `exp`, or after 8 days); OpenAI: one `auth.json` per runner, never shared across concurrent jobs or machines; stores `file|keyring|auto|ephemeral`; the keyring entry is keyed by `CODEX_HOME` (**source inspection**, RESEARCH §B; the live probe of Decision 0017 Q4 is pending); Business/Enterprise access tokens (`CODEX_ACCESS_TOKEN`, 1–90 days, admin-revocable) are a clean per-launch path; `CODEX_API_KEY` wins over everything. **Measured by `rwh`:** several app-servers sharing one `auth.json` race on refresh; with its `auth.json.rwh-lock` and one refresh owner an eight-caller test produced one refresh, without the lock eight; its tenants receive external access tokens and hold no `auth.json`. Curator links the managed `auth.json` to the native one (`keyring-preferred` strategy; in-place writer verified), never copies; the in-place writer preserves link identity and says nothing about concurrent refresh ownership.
- **Muse.** `META_API_KEY` always wins; account login is Keychain-first with an `auth.json` fallback; `muse exec --api-key-stdin`; no helper. The spawn allowlist does not pass `META_API_KEY` yet (TASK-261007-hjwgiz).
- **CIP-0003 (Draft)** proposes four Claude modes — `per-home`, `token` (opaque `source_ref`, e.g. a Keychain item), `helper`, gated `shared-file` — with configuration precedence and defaults, protected-store reads in a defined order, a legacy Linux path, migration rules, no fallback, and item 5: refuse `token` and `helper` for tracked runs until the final executor does the protected lookup itself. Nothing of it is implemented. VISION v1.3 (CUR-R3) already assumes M1 does the lookup with `source_ref` in the plan.
- **Owner decisions 2026-10-07:** subscriptions now, tokens architecturally; Team/Enterprise (Claude) and Business (Codex) not for the first release; the personal-plan Codex workaround (one serialized copy per account) is admitted; "one person = one subscription; the broker substitutes it only into that person's launches, in the volume of one person"; no traffic interception in the first implementation.

## Design

### Options considered

**For Claude inherited authentication**
1. *Copy the Keychain item under the new home's service name.* Copies a refresh-capable OAuth family; rotation revokes siblings; violates Decision 0017 Q7. Rejected.
2. *One enrolled `setup-token` at an authentication node, injected per launch.* Documented practice, no refresh state, one revocation point. **Recommended.** Limits: one year, restart on expiry, revocation only in the vendor UI, readable by the harness process (trusted-process posture).
3. *`apiKeyHelper` to a node service.* API keys only (Console billing), not the subscription. Kept as the `helper` mode for API-key setups.
4. *A proxy that injects the credential into provider traffic.* Research only (owner decision 2026-10-07).

**For Codex inherited authentication**
1. *File-link every home's `auth.json` to one file* (revision 1). The file is not a lock: `rwh` measured the race. Rejected.
2. *A single auth owner per account* (the `rwh` pattern): one Curator-owned process holds the account lease with an explicit lock, is the only refresher of the native `auth.json`, and hands the current access token to each launch as an external token; launches hold no `auth.json`. Admitted by the owner's decision (one serialized copy per account) and measured by `rwh`. **Recommended for personal plans.** Limit: a native `codex` client of the same account on the same machine must go through the owner's file (it is the native file) and must not run concurrently with the owner's refresh; that rule is the human's, stated in `status`.
3. *Business/Enterprise access token in `CODEX_ACCESS_TOKEN` at the node, injected per launch.* Clean, revocable, 1–90 days. **Recommended where the plan exists**; not for the first release per the owner.
4. *Keyring store shared across homes.* Keyed by `CODEX_HOME` per source inspection; not inherited. Rejected pending Decision 0017 Q4.
5. *Stripped copy without `refresh_token`.* Prohibited by Decision 0017 Q7; a future amendment would need operator-owned profile and environment, source and destination roles, purpose, reason and expiry. Not an option of this CIP.

**For who injects**
1. *The launcher writes the token into the plan or fragment.* Secrets in a hashed, logged document. Rejected (Decision 0013: the plan carries no secret values).
2. *The final executor re-resolves a protected binding and injects into the process environment at exec.* The only process that must see the value is the one that execs the harness. **Recommended**; it is what VISION M1 does and what the donor supervisor (CIP-0009) does.

### Recommendation

**C1. Authentication nodes.** A new managed object, the **authentication node**: a per-OS-user, per-harness, per-account-label record under the manager's environments root, `auth/<label>/`, holding *references and metadata* only: `{harness, account_label, kind: claude-oauth-token | codex-auth-owner | codex-access-token | meta-api-key | gemini-api-key, source_ref, enrolled_at, issued_at?, expires_at | unknown, last_refusal?}`. Material lives in the per-user protected store (macOS login keychain for interactive users; a 0600 file owned by the service identity for headless service identities such as the donor bridge; Linux secret service or a 0600 file), never in the node record. The **root node** is the label `root` of a user; several accounts are several labels. A node belongs to the OS user that enrolled it; another OS user cannot read it by construction. Crossing OS users is the credential broker of architecture §7.3, whose minimal interface is slice 0 of this CIP (C7).

**C2. Homes with inherited authentication.** `isolation` keeps the Decision 0017 meaning (`shared|isolated`: whether the native store is shared). A separate axis, the **credential source**, is set per profile and harness in the user-owned machine configuration: `credential_source.<profile>.<harness>` = `per-home` (default) | `node:<label>` | `helper`. A home whose source is a node holds no credential of its own: no seed, no link (for Claude), and the executor injects by the harness's channel table at every launch:

| Harness | Channel at exec | Store state inside the home | Absent / unreadable / native-keyring cases |
|---|---|---|---|
| `claude_code` | `CLAUDE_CODE_OAUTH_TOKEN=<value>` in the harness process environment; `--bare` is never combined with it | no Keychain item is created or read (qualified by the effective-source check, not assumed); `.credentials.json` absent | node absent → `credential_node_missing`; store unreadable → `credential_store_unreadable`; a native login present in the home → `credential_source_conflict`; never a fallback to the native login |
| `codex_cli` personal | an external access token from the **auth owner** of the account (`curator env credential owner`, one per account label, the only refresher, holding the lease lock on the native `auth.json`); the launch receives it through the app-server's external-token path (the `rwh` adapter) | no `auth.json` in the managed home; `cli_auth_credentials_store = ephemeral` pinned | owner not running → `credential_owner_unavailable`; native file detached or forked → `environment_credential_conflict`; keyring store selected natively → the owner refuses to enrol until the human switches the store to `file` (`--from-native` never exports a keyring item) |
| `codex_cli` Business | `CODEX_ACCESS_TOKEN=<value>` in the process environment | no `auth.json` | as for Claude |
| `muse` | `META_API_KEY=<value>` in the process environment, or `exec --api-key-stdin` | no account login in the home | as for Claude |
| `gemini`/`agy`/`qwen` | API-key environment variables | — | as for Claude |

So "inherited authentication" for Claude is one token from `setup-token`, enrolled in the root node and injected into every home that names it (the documented path); the native per-home login stays for long-lived interactive sessions. For Codex it is the auth owner's external token (or a Business access token). Existing homes are untouched: adoption goes through `inspect → plan → apply` with a coordinated marker revision (CIP-0003's migration rule, retained).

**C3. Gates for tracked and headless launches** (the "special flags" of the brief).
1. The knob `credential_source.<profile>.<harness>` lives in the **user-owned** layer of the machine configuration and is never lockable by system configuration (environments §12.2 unchanged: locks do not select or constrain credential material). A package's environment entry may carry `credential_requirement: {kind}` as a non-authoritative statement ("this profile needs an enrolled Claude token"); it never names a node (F7).
2. Per launch, `curator run --credential node:<label>` is admitted only when the knob allows that node for the profile; otherwise `usage`.
3. **Plan extension and executor capability.** The plan carries the required extension `works.relux.curator.credential/1` = `{mode: node, source_ref, harness_channel}` (no value), coordinated in CIP-0008's schema table. Intake refuses a node-mode plan unless the executor declares the versioned capability `credential-injection/1` (the session host M1, the task-board spawn runner, the remote-worker supervisor); until then it refuses `credential_injection_unavailable`, which is CIP-0003 item 5 with the executors named.
4. **Protected binding (F22).** The capability is necessary, not sufficient. At exec the executor re-resolves `credential_binding/1` from its trusted store: `{executor peer identity, profile, harness, account label, channel, provider endpoint, approved executable digest, policy generation}`; a caller-supplied `source_ref` or a self-declared capability never substitutes for it. The injected variable names are **reserved**: if the inherited environment, a settings file (`apiKeyHelper`), a configuration key or a helper already supplies a credential for the harness, the launch refuses `credential_source_conflict` rather than letting a higher-precedence source win or send authorization elsewhere. The harness process environment and the MCP children's environment are **separate**: `passable_env_names` bounds what the declaration asks for, and the injected names are never passed to a child. Behavioural qualification behind the capability (per tuple, lab): the token is present in the harness process only, no Keychain read occurs (effective-source check), no child receives it, a conflicting source refuses, and an unknown `source_ref` refuses without fallback.
5. **Status and events.** `env status` shows `credential: node root (claude-oauth-token, enrolled 2026-10-08, issued 2026-10-08 (stated), expires 2027-10-08 (computed) | unknown, last refusal none)`; never a hash of the material. A node enrolled without `--issued-at` reports `expires_at: unknown` and emits no expiry warning (F24). Events `credential_expiring` (T−5 min before a JWT `exp`; T−3 days before a stated Claude expiry), `credential_expired`, `credential_error {class: auth | permission | quota | unknown}` (the executor classifies the harness's typed error where it can and keeps `unknown` where a 401/403 cannot be separated from a permission or quota cause; opaque TLS traffic gives it no HTTP status), `reauth_required`. Reaction: park the session, notify the operator, no indefinite retry; after re-enrolment, recovery per persistence mode: Claude resumes its transcript with `--resume`; Codex under `ephemeral` has no native resume and restarts from the task snapshot; Muse resumes from its session log; each path is a lab measurement (PLAN steps 3–4), not a promise.
6. **`/login` inside a home that inherits authentication.** For tracked and headless launches Curator ships only modes where the interactive command path does not exist (`--print`, the app-server, `exec`); for interactive homes the launcher prints a warning and `status` shows the conflict afterwards (`credential_source_conflict`), because a command typed inside a running harness cannot be intercepted by a launch-flag table.

**C4. Enrolment commands** (human-only steps stay with the human; the vendor flow is never bypassed; enrolment of a deliberately supplied token is never permission to extract an existing native login): `curator env credential enrol claude_code --node root --token-stdin [--issued-at <date>]` (the human runs `claude setup-token` themselves and pipes the output; Curator stores it in the protected store and records the node); `curator env credential enrol codex_cli --node root --from-native` (starts the auth owner on the native `auth.json` of this user after the liveness checks of §7.4; refuses a keyring-backed native store); `enrol codex_cli --access-token-stdin`; `enrol muse --api-key-stdin`; `curator env credential owner start|stop|status` (the Codex auth owner); `curator env credential revoke --node <label>` (deletes the stored item, marks the node, stops the owner; the vendor-side revocation is the human's step, named in the output); `status`.

**C5. Remote workers.** On the donor machine the node is enrolled by the donor (the machine's owner) during `curator remote-worker init` (CIP-0009) under the **bridge identity**; the supervisor is the executor with `credential-injection/1` and resolves the binding from the bridge's store; the harness is launched in lockdown with the token in its environment only. The project side never holds a donor credential (architecture §7.9).

**C6. CIP-0003 disposition, clause by clause (F23).** Recommended: adopt CIP-0003 (narrowed) and this CIP together in one decision record.

| CIP-0003 clause | Disposition |
|---|---|
| Mode `per-home` and its defaults | retained; the interactive default |
| Mode `token` with opaque `source_ref` | retained as the node mode of this CIP, with the gates of C3 |
| Mode `helper` | retained for API-key setups |
| Mode `shared-file` and its gate | replaced by the node; the Linux legacy linked-file path stays described as the legacy lane with its unqualified refresh safety, never as a sharing strategy |
| Configuration precedence and defaults | retained; `credential_source` takes the place of `credential_sources` with the same precedence rules |
| Protected-store read order and the no-fallback rule | retained verbatim |
| Legacy Linux handling | retained |
| Migration (`inspect → plan → apply`, marker revision) | retained; this CIP's marker members ride the same revision |
| Item 5 (refuse `token`/`helper` for tracked runs until the executor does the lookup) | retained in substance as `credential_injection_unavailable`; lifted per executor only when that executor implements `credential_binding/1` and passes the qualification of C3.4 |
| Facts: macOS Keychain per `CLAUDE_CONFIG_DIR` | retained; the revision-1 wording "cannot share a file on macOS at all" is withdrawn: the native store is the Keychain, and the plaintext fallback exists with unqualified refresh safety |
| Decision 0017 Q4 (Codex keyring keyed by `CODEX_HOME`) | recorded as source inspection; the live probe stays pending; the decision text gets an evidence label, not a new claim |
| Decision 0017 Q7 (no copy) | unchanged; the stripped copy is not offered |

*Priority:* P1 after v0.15.0-rc.5, in the order of C7.

**C7. Sequencing and what is not here (F25).** Slice 0 is the **minimal peer-authenticated broker interface**: `credential_binding/1` served over a Unix socket with peer credentials from the operator's user to a final executor running as another OS user, proving one authorized chain end to end (wrong peer, wrong account, expired binding refused) before nodes are generalised or any donor is deployed. Not in this CIP: the full broker (leases, concurrency bounded to one person's volume), proxy injection (research), Team/Enterprise plans (owner: not for the first release), `CLAUDE_CODE_OAUTH_REFRESH_TOKEN` provisioning (UNVERIFIED semantics).

## Security considerations

- **One person, one subscription.** The node is per OS user and per account label; Curator never multiplies an account across users; the Codex auth owner serialises one account to one refresher; the broker, later, bounds concurrency to one person's volume (owner decision). Vendor terms are quoted in RESEARCH §F; the posture here is the documented one (a setup-token in automation).
- **Material at rest:** the per-user protected store only; the node record is references and timestamps. **In flight:** the executor's memory and the harness process environment at exec; never argv, never the plan, never a fragment, never a log, never an MCP child.
- **What the harness can do with it (F22):** a token in the process environment is readable by the harness and can be copied by a compromised one within its sandbox; removing store copies limits the blast radius to one token with one revocation point, it does not make the token non-extractable. This is the owner-approved initial trusted-process posture; stronger non-extraction (proxy-side injection or a lease the process cannot read) is a separate design.
- **Rotation hazards:** Claude token: none (no refresh); Codex: exactly one refresher per account (the owner), a forked or detached native file is refused (`environment_credential_conflict`), never merged (Decision 0017 Q7).
- **Revocation:** Claude in the vendor UI; Codex `codex logout` at the owner's file; Curator's `revoke` removes the local item, stops the owner and marks the node so every launch refuses until re-enrolment.

## Compatibility and migration

- `isolation: shared|isolated` keep their meaning; `credential_source` is a new user-owned knob defaulting to `per-home`; nothing changes for existing homes until `apply`.
- Marker schema: additive members `credential_source`, `auth_node`, `credential_kind`, `enrolled_at`, `issued_at`, `expires_at` (no digests of material), in the coordinated marker revision of CIP-0003.
- CIP-0003's `credential_sources` config is renamed to `credential_source` with the same precedence before it ships.

## Specification changes

- environments §7.4: the authentication node, the credential-source axis, the channel and case table of C2, the Codex auth owner; §12.1: `credential_source.<profile>.<harness>` in the user-owned layer; §12.2 unchanged (explicitly: not lockable).
- Decision 0013: the required extension `works.relux.curator.credential/1`; intake capability `credential-injection/1`; `credential_binding/1` at the final executor; refusals `credential_injection_unavailable`, `credential_source_conflict`, `credential_node_missing`, `credential_store_unreadable`, `credential_owner_unavailable`.
- Decision 0017: an evidence label on Q4; Q7 unchanged.
- Launcher SPEC: `--credential node:<label>`, receipt line, status line, the warning for interactive homes.
- Manager: `env credential enrol|revoke|status|owner`.
- A decision record adopting CIP-0003 (narrowed, per the table of C6) and CIP-0010 together.

## Implementation plan

0. **Slice 0:** `credential_binding/1` over a peer-authenticated Unix socket across two OS users on one host; one chain proven with refusals (wrong peer, wrong account, expired). Size M.
1. Spec text and the decision record. Size S–M.
2. curator: nodes, `credential_source`, the Codex auth owner (from `rwh`), `env credential` commands, status and events, marker members. Size M.
3. Executors: `credential-injection/1` with the binding and the qualification suite in the task-board spawn runner (the first consumer), then the session host, then the donor supervisor. Size M each.
4. Lab (the owner's laptop, per PLAN): step 2 (effective source: no Keychain read with the environment token), steps 3–4 for Claude (revocation signal, `--resume` with a new token), the Codex owner race test (eight callers, one refresh) at 0.159.0. Size S of operator time.
5. Muse: `META_API_KEY` pass-through (TASK-261007-hjwgiz) then node kind `meta-api-key`. Size S.

## Test plan

- Production-entry: a Claude home with source `node:root` launched through `curator run` has the token in the harness process environment only, no Keychain item, no `.credentials.json`, and no token in any MCP child's environment; a Codex home has no `auth.json`, `ephemeral` pinned, and an external token from the owner.
- Negatives: `--credential node:x` with a knob that does not admit it refuses `usage`; a node plan on an executor without `credential-injection/1` refuses `credential_injection_unavailable`; a caller-supplied `source_ref` that differs from the binding refuses; a home with a native login and a node source refuses `credential_source_conflict`; an inherited `CLAUDE_CODE_OAUTH_TOKEN`, an `apiKeyHelper` or a `CODEX_API_KEY` beside a node source refuses `credential_source_conflict`; a stopped owner refuses `credential_owner_unavailable`; a forked native `auth.json` refuses `environment_credential_conflict`; the token never appears in the plan, the fragment, the receipt, logs or `env status` (grep over all artifacts in the test); `--bare` combined with a node refuses; a system lock naming a node refuses `usage`.
- Concurrency: eight Codex launches through one owner produce exactly one refresh (the `rwh` vector at 0.159.0).
- Lifecycle: an expired or revoked token produces a typed `credential_error` and a parked session; re-enrolment and relaunch recover per persistence mode (lab evidence from PLAN steps 3–4); a node without `--issued-at` shows `expires_at: unknown` and emits no expiry event.
- Slice 0: a binding request from a wrong peer UID, for a wrong account label, or past its expiry is refused by the broker; a right one is served exactly once per launch.

## Open questions for the operator

1. **Default for tracked launches once an executor passes the qualification:** keep `per-home` as default and require the knob (recommended), or make `node:root` the default when a root node exists?
2. **Codex personal plan:** adopt the single auth owner with external tokens (recommended, measured by `rwh`), with the race test at 0.159.0 as the precondition?
3. **Accept CIP-0003 narrowed together with this CIP** in one decision record (recommended), or keep them separate?
4. **Muse:** node kind `meta-api-key` only (recommended), or also an account-login node once refresh semantics are measured?
5. **Slice 0 before rc.6?** The broker interface is the prerequisite of the owner's MVP; recommended: yes, as the first item after rc.5.
