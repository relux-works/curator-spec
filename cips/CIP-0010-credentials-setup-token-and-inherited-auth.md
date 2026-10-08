# CIP-0010: Credentials for managed launches: `setup-token` adoption, bare homes with inherited authentication, and the disposition of CIP-0003

- **Status:** Draft
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-08
- **Related:** owner brief 2026-10-08 §8; [CIP-0003](CIP-0003-claude-managed-home-credential-modes.md) (Draft); [Decision 0017](../decisions/0017-environment-credential-modes.md) (`shared|isolated`, Q7 no-copy); environments [§7.4](../protocol/environments.md#74-credential-passthrough-provisioning-seeds-and-isolation); wiki `research/harness-auth/RESEARCH.md` (2026-10-07) and `PLAN-expiry-check.ru.md`; wiki `session-host/architecture.ru.md` §7.3 (credential broker); [CIP-0008](CIP-0008-remote-worker-launch-mode.md), [CIP-0009](CIP-0009-donor-side-deployment-and-bridge.md)
- **Affects:** environments §7.4 and §12.1 (new knobs), Decision 0013 (plan members), the marker schema (credential mode fields), curator (`env credential` commands), curator-run/launcher, the final executors (session host, task-board spawn runner, the remote-worker supervisor)

## Summary

Three related changes. (1) **Adopt `claude setup-token`** (`CLAUDE_CODE_OAUTH_TOKEN`) for tracked and headless launches behind explicit gates: the token is enrolled once into the OS keyring under an *authentication node*, referenced by an opaque `source_ref`, and injected into the harness process environment by the **final executor** only; the plan and the fragment never carry it. (2) **Bare homes with inherited authentication**: a managed home may start empty and reuse the authentication of an authentication node higher up (the operator's root login or a named account node) instead of a per-home Keychain login on macOS or a per-home `auth.json` link; for Claude this is the enrolled token, for Codex it is one serialized `auth.json` per account (or a Business access token), each with stated limits. (3) **CIP-0003 disposition**: its `token` mode is the core of this CIP and should be accepted in a narrowed revision; its `shared-file` mode is superseded by the authentication node; `per-home` stays the interactive default; `helper` stays for API keys. Priority: high, right after v0.15.0-rc.5, because remote workers (the donor's subscription), tracked spawns and the MVP's one-subscription chain all depend on it.

## Motivation and user stories

- **Owner (2026-10-08):** "research and propose how to adopt `claude setup-token`, possibly behind special flags, for tracked and headless launches"; "a mode where a managed home starts bare but reuses the authentication of a root authentication session, or of a node higher up if the machine has several accounts, instead of a per-home Keychain login; for Codex likewise"; "state whether CIP-0003 is needed now, what is superseded, and its priority".
- **Tracked spawns** (task-board workers) today need a logged-in managed home per profile; on macOS each one is a separate `/login`, which is the pain the owner named on 2026-10-05.
- **Remote workers** (CIP-0008/0009) run under the donor's subscription: the donor enrols one token on their machine; every launch of the lockdown harness receives it from the supervisor, and the harness never sees a store.
- **The MVP** (owners' call C15: one subscription, one machine, a chain of OS users) needs one place that holds a login and a per-launch injection path, which is the credential broker of architecture §7.3; this CIP is the single-user, single-node form of it and the shape the broker will speak.

## Current state

Facts are measured or vendor-documented (RESEARCH §A–§C, 2026-10-07; curator v0.15.0-rc.4; environments §7.4):

- **Claude Code.** `claude setup-token` opens the browser flow and prints a one-year OAuth access-only token; it saves nothing. `CLAUDE_CODE_OAUTH_TOKEN` takes precedence over Keychain credentials for the whole session; it cannot be shortened, scoped or renewed in place ("generate a new one and restart"); revocation only in the claude.ai UI; `apiKeyHelper` accepts API keys or JWTs only; `--bare` never reads OAuth. On macOS a native login is a Keychain item keyed by `CLAUDE_CONFIG_DIR` (service suffix sha256[0:8]), so every managed home is its own login and `shared` is refused (`environment_shared_unsupported`); on Linux `.credentials.json` is file-linked. Subscription logins are refresh-token families with single-use rotation: a copy that refreshes invalidates its siblings. Terms: no account sharing; `CLAUDE_CODE_OAUTH_TOKEN` in CI is documented practice.
- **Codex.** `auth.json` is rewritten in place (0600) and rotated at every refresh (5 minutes before `exp`, or after 8 days); OpenAI: one `auth.json` per runner, never shared across concurrent jobs or machines; stores `file|keyring|auto|ephemeral`; the keyring entry is keyed by `CODEX_HOME` (open probe Q18); Business/Enterprise access tokens (`CODEX_ACCESS_TOKEN`, 1–90 days, admin-revocable) are a clean per-launch path; `CODEX_API_KEY` wins over everything. Curator links the managed `auth.json` to the native one (`keyring-preferred` strategy; in-place writer verified), never copies.
- **Muse.** `META_API_KEY` always wins; account login is Keychain-first with an `auth.json` fallback; `muse exec --api-key-stdin`; no helper. The spawn allowlist does not pass `META_API_KEY` yet (TASK-261007-hjwgiz).
- **CIP-0003 (Draft)** proposes four Claude modes — `per-home`, `token` (opaque `source_ref`, e.g. a Keychain item), `helper`, gated `shared-file` — and refuses `token` and `helper` for tracked runs until the final executor does the protected lookup itself (item 5). Nothing of it is implemented. VISION v1.3 (CUR-R3) already assumes M1 does the lookup with `source_ref` in the plan.
- **Owner decisions 2026-10-07:** subscriptions now, tokens architecturally; Team/Enterprise (Claude) and Business (Codex) not for the first release; the personal-plan Codex workaround (one serialized copy per account) is admitted; "one person = one subscription; the broker substitutes it only into that person's launches, in the volume of one person"; no traffic interception in the first implementation.

## Design

### Options considered

**For Claude inherited authentication**
1. *Copy the Keychain item under the new home's service name.* Copies a refresh-capable OAuth family; rotation revokes siblings; violates Decision 0017 Q7. Rejected.
2. *One enrolled `setup-token` at an authentication node, injected per launch.* Documented practice, no refresh state, one revocation point. **Recommended.** Limit: one year, restart on expiry, revocation only in the vendor UI.
3. *`apiKeyHelper` to a node service.* API keys only (Console billing), not the subscription. Kept as the `helper` mode for API-key setups.
4. *A proxy that injects the credential into provider traffic.* Research only (owner decision 2026-10-07): vendors may detect it and close accounts.

**For Codex inherited authentication**
1. *File-link every bare home's `auth.json` to the node's file* (today's `shared`, in-place writer). One live refresher per account because there is one file; a serialized copy per account is admitted by the owner. **Recommended for personal plans.** Limit: concurrent refresh coordination between homes is unverified (§7.4); the node's `.auth.json.lock` and Codex's own refresh window are the only serialization; probe before relying on it (PLAN step 6).
2. *Business/Enterprise access token in `CODEX_ACCESS_TOKEN` at the node, injected per launch.* Clean, revocable, 1–90 days. **Recommended where the plan exists**; not for the first release per the owner.
3. *Keyring store shared across homes.* Keyed by `CODEX_HOME`; not inherited. Rejected pending Q18.
4. *Stripped copy without `refresh_token`, relaunched at `exp`.* Works until expiry, no rotation hazard; a fallback when the file-link cannot be used (different OS users). Kept as an option of the broker.

**For who injects**
1. *The launcher writes the token into the plan or fragment.* Secrets in a hashed, logged document. Rejected (Decision 0013: the plan carries no secret values).
2. *The final executor resolves `source_ref` and injects into the process environment at exec.* The only process that must see the value is the one that execs the harness. **Recommended**; it is what VISION M1 does and what the donor supervisor (CIP-0009) does.

### Recommendation

**C1. Authentication nodes.** A new managed object, the **authentication node** (`auth node`): a per-OS-user, per-harness, per-account-label record under the manager's environments root, `auth/<label>/`, holding *references* only: `{harness, account_label, kind: claude-oauth-token | codex-auth-file | codex-access-token | meta-api-key | gemini-api-key, source_ref, enrolled_at, expires_at?, last_refusal?}`. Material lives in the OS keyring (macOS login keychain, Linux secret service; a 0600 file under the node only where no keyring exists), never in the node record. The **root node** is the label `root` of a user; several accounts are several labels. A node belongs to the OS user that enrolled it; another OS user cannot read it by design (per-user keyrings), which is where the credential broker of architecture §7.3 takes over, speaking the same `source_ref`.

**C2. Bare homes.** A managed home with `isolation: bare` (a third value beside `shared|isolated` of Decision 0017) starts with no credential seed and no link; the profile's environment entry names `auth_node: <label>`; at every launch the final executor resolves the node and injects by the harness's channel table:

| Harness | Channel at exec | Store state inside the bare home |
|---|---|---|
| `claude_code` | `CLAUDE_CODE_OAUTH_TOKEN=<value>` in the process environment; `--bare` is never combined with it | no Keychain item is created or read; `.credentials.json` absent; a `/login` inside the home is refused by policy (it would create a competing family) |
| `codex_cli` personal | `auth.json` **file-linked** to the node's file (the node holds the one live family); `cli_auth_credentials_store = file` pinned in the managed `config.toml` | one writer per account; the node's lock serializes refresh; detachment is checked at every resolve (§7.4 liveness rules) |
| `codex_cli` Business | `CODEX_ACCESS_TOKEN=<value>` in the process environment | no `auth.json` |
| `muse` | `META_API_KEY=<value>` in the process environment, or `exec --api-key-stdin` | no account login in the home |
| `gemini`/`agy`/`qwen` | API-key environment variables | — |

**C3. Gates for tracked and headless launches** (the "special flags" of the brief).
1. The machine knob `credential_mode.<profile>.<env-id>` with values `per-home` (default), `node:<label>`, `helper` — lockable by system configuration; a profile's environment entry may only *name* a node, never a value.
2. Per launch, `curator run --credential node:<label>` is admitted only when the knob allows that node for the profile; otherwise `usage`.
3. **Executor capability.** The plan carries `credential: {mode: node, source_ref, harness_channel}` (no value). Intake refuses a node-mode plan unless the executor declares the versioned capability `credential-injection/1` (the session host M1, the task-board spawn runner, the remote-worker supervisor). Until an executor declares it, node mode for tracked launches refuses with `credential_injection_unavailable`, exactly CIP-0003 item 5; this CIP names the executors and the capability instead of leaving the refusal open-ended.
4. **Audit and status.** `env status` shows `credential: node root (claude-oauth-token, enrolled 2026-10-08, expires 2027-10-08, last refusal none)`; never a hash of the material. Events `credential_expiring` (T−5 min for JWT `exp`; T−3 days for the Claude token's mint date), `credential_expired`, `credential_revoked` (401/403 seen by the executor), `reauth_required`; the executor's reaction is to park the session and ask the operator to enrol a new token, then relaunch (PLAN steps 3–4). A relaunch with a new token resumes the conversation by native `--resume` (to be confirmed by PLAN step 4).

**C4. Enrolment commands** (human-only steps stay with the human; the vendor flow is never bypassed): `curator env credential enrol claude_code --node root --token-stdin` (the human runs `claude setup-token` themselves and pipes the output; Curator stores it in the keyring and records the node); `curator env credential enrol codex_cli --node root --from-native` (links the node to the native `auth.json` of this user, after the liveness checks of §7.4); `enrol codex_cli --access-token-stdin`; `enrol muse --api-key-stdin`; `curator env credential revoke --node <label>` (deletes the keyring item and marks the node; the vendor-side revocation is the human's step, named in the output); `status`.

**C5. Remote workers.** On the donor machine the node is enrolled by the donor (the machine's owner) during `curator remote-worker init` (CIP-0009) under the harness user; the supervisor is the executor with `credential-injection/1`; the harness is launched in lockdown with the token in its environment only. The project side never holds a donor credential (architecture §7.9: "remote agents use their own provider credentials").

**C6. CIP-0003 disposition.**
- *Needed now:* yes, as the Claude mode table and the Keychain facts, but narrowed: `token` mode is this CIP's node mode (accepted here with the gates of C3), `helper` stays as is, `per-home` stays the interactive default, `shared-file` is **superseded** by the authentication node (Claude cannot share a file on macOS at all; Codex's file-link is the node).
- *Superseded by this CIP:* CIP-0003 items on `shared-file` gating; its item 5 refusal (replaced by the executor capability); its `credential_sources` machine config v4 (replaced by nodes).
- *Priority:* P1 after v0.15.0-rc.5: it unblocks tracked spawns without per-home logins, remote workers, and the MVP. Recommended procedure: accept CIP-0003 as "superseded in part by CIP-0010" and adopt one decision record for both.

**C7. Not in this CIP:** cross-OS-user leases (the broker), proxy injection (research), Team/Enterprise plans (owner: not for the first release), `CLAUDE_CODE_OAUTH_REFRESH_TOKEN` provisioning (UNVERIFIED semantics).

## Security considerations

- **One person, one subscription.** The node is per OS user and per account label; Curator never multiplies an account across users; the broker, later, bounds concurrency to one person's volume (owner decision). Vendor terms are quoted in RESEARCH §F; the posture here is the documented one (a setup-token in automation).
- **Material at rest:** OS keyring only; the node record is references and timestamps. **In flight:** the executor's memory and the harness process environment at exec; never argv, never the plan, never a fragment, never a log. The composed environment literal list of Decision 0013 is disjoint from injected names by construction (the name is reserved for the executor).
- **Rotation hazards:** Claude token: none (no refresh); Codex file-link: exactly one live family per account, serialized by one file; a forked regular file is refused (`environment_credential_conflict`), never merged (Decision 0017 Q7).
- **Revocation:** Claude in the vendor UI; Codex `codex logout` at the node; Curator's `revoke` removes the local item and marks the node so every launch refuses until re-enrolment.
- **A `/login` inside a bare home** is refused by the launcher's refusal table (CIP-0008 R4 shape) for tracked launches and warned for interactive ones, because it would create a competing credential family.

## Compatibility and migration

- `isolation: shared|isolated` keep their meaning; `bare` is additive. `per-home` stays the default; nothing changes for existing homes.
- Marker schema: additive members `credential_mode`, `auth_node`, `credential_kind`, `enrolled_at`, `expires_at` (no digests of material), in the next marker revision.
- CIP-0003's `credential_sources` config is dropped before it ships; nodes replace it.

## Specification changes

- environments §7.4: the authentication node, `isolation: bare`, the channel table of C2, the `/login` refusal; §12.1: `credential_mode.<profile>.<env-id>`.
- Decision 0013: plan member `credential {mode, source_ref, harness_channel}`; intake capability `credential-injection/1`; the refusal `credential_injection_unavailable`.
- Launcher SPEC: `--credential node:<label>`, receipt line, status line.
- Manager: `env credential enrol|revoke|status`.
- A decision record adopting CIP-0003 (narrowed) and CIP-0010 together.

## Implementation plan

1. Spec text and the decision record. Size S–M.
2. curator: nodes, `isolation: bare`, `env credential` commands, status and events, marker members. Size M.
3. Executors: `credential-injection/1` in the task-board spawn runner (the first consumer), then the session host, then the donor supervisor. Size M each.
4. Lab (the owner's laptop, per PLAN): steps 1–4 for Claude (token in env, no Keychain write, revocation signal, `--resume` with a new token) and step 6 for Codex (one copy per account, stripped copy). Size S of operator time.
5. Muse: `META_API_KEY` pass-through (TASK-261007-hjwgiz) then node kind `meta-api-key`. Size S.

## Test plan

- Production-entry: a bare Claude home launched with node `root` has the token in the process environment and no Keychain item or `.credentials.json` afterwards; a bare Codex home has `auth.json` as a link to the node file and `cli_auth_credentials_store = file` pinned.
- Negatives: `--credential node:x` with a knob that does not admit it refuses `usage`; a node plan on an executor without `credential-injection/1` refuses `credential_injection_unavailable`; a forked Codex `auth.json` refuses `environment_credential_conflict`; the token never appears in the plan, the fragment, the receipt, logs or `env status` (grep over all artifacts in the test); `--bare` combined with a node refuses.
- Lifecycle: an expired or revoked token produces `credential_revoked` and a parked session; re-enrolment and relaunch resume (lab evidence from PLAN steps 3–4).

## Open questions for the operator

1. **Default for tracked launches once an executor declares the capability:** keep `per-home` as default and require the knob (recommended), or make `node:root` the default when a root node exists?
2. **Codex personal plan:** admit the file-link to the root node for bare homes (recommended, per the 2026-10-07 decision), with the concurrency probe as a precondition?
3. **Accept CIP-0003 narrowed together with this CIP** in one decision record (recommended), or keep them separate?
4. **Muse:** node kind `meta-api-key` only (recommended), or also an account-login node once refresh semantics are measured?
