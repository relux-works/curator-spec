# CIP-0011: Credential broker leases and agent OS users

- **Status:** Draft (revision 3)
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-09
- **Related:** [CIP-0010](CIP-0010-credentials-setup-token-and-inherited-auth.md) (credential sources, protected credential binding C3.4, executor capability, CIP-0003 disposition); [CIP-0008](CIP-0008-remote-worker-launch-mode.md), [CIP-0009](CIP-0009-donor-side-deployment-and-bridge.md); [Decision 0013](../decisions/0013-execution-ownership-and-launch-plans.md) (launch plans); [Decision 0017](../decisions/0017-environment-credential-modes.md) (credential modes); environments §7.4, §10.3, §12.1–§12.2; relux-works/curator-credential-broker `spec/broker.md` (draft v0.3); relux-works/curator-host-helper `spec/helper.md` (draft v0.3, with the launcher and `exec.stop`); relux-works/curator-dispatcher `spec/dispatcher.md` (draft v0.2); relux-works/curator-network-profiles (binding records)
- **Affects:** environments §7.4 and §12.1 (a credential source value), Decision 0013 (the credential extension), the launcher SPEC, the manager command set (`broker`, `agent-user` as a dispatcher client), the final executors (task-board spawn runner first, then the session host and the remote-worker supervisor)

## Revision 2

An architecture review on 2026-10-09 kept the direction and found gaps that this revision closes: an unprivileged dispatcher had no way to run anything as a created account (the helper repository now has a narrow launcher); the broker path did not restate CIP-0010's protected binding (now explicit); the per-turn token-only Codex home contradicted CIP-0010's no-copy decision (removed); network checks claimed more than a caller's record proves (now cooperative and labelled so); and the first slice was too wide (now one protected Claude launch first).

## Revision 3

The owner decided (2026-10-09) to build the dispatcher as its own platform module, relux-works/curator-dispatcher, instead of folding its work into Curator. `curator agent-user` becomes a client of the dispatcher: the dispatcher, running under its own service account, owns the run records, the grant checks, the capacity gates, provisioning through the helper and the broker, the start through the launcher, and reconciliation. Its v0 is a command run under that account; its v1 is a daemon with a socket for orchestrators and the session host, on the same core.

## Summary

CIP-0010 lets a managed home use a credential enrolled once instead of a login per home, but its authentication node lives in one OS user's store and cannot serve agents that run as other OS users. This CIP connects Curator to two platform components:

- **curator-credential-broker** holds each account once, under its own service user, and leases it to launches that a signed grant authorises, identifying the launching process by its kernel-reported UID and the account's never-reused generation. It also runs the single Codex auth owner per account.
- **curator-host-helper** creates and retires per-agent OS accounts through a closed, journaled operation schema run with `sudo`, and its **launcher** starts one approved executor under one active agent account. (Its v1 adds per-account firewall rules.)

Curator gains a credential source `broker:<account>`, the broker mode of the credential extension, a broker client in the final executor, `curator broker …` commands, and `curator agent-user …` commands that play the dispatcher's role until a dispatcher exists. The result is the owners' first MVP shape: one subscription, one machine, a chain of OS accounts, each agent running under its own account and receiving the subscription's credential from the broker.

## Motivation

- **Owner (2026-10-09):** a launch of an environment with a profile should run from its own OS account and get its token from the broker; the mechanism must work when orchestrators and helpers create agents, including ephemeral agents with an account created for one task; a subscription's traffic should be bound to a network profile.
- CIP-0010 slice 0 named the missing piece: a peer-authenticated interface across OS users. Designing it as the platform's credential broker from the start avoids a second rewrite.

## Design

### 1. Credential source `broker:<account>`

CIP-0010's `credential_source.<profile>.<harness>` (user-owned layer, never lockable) gains the value `broker:<account>`, naming a broker account id. The value enters the closed configuration schema together with its CLI and marker changes; a Curator profile's bytes still never select accounts, endpoints, executables or injected values (environments §10.3), and no system lock selects credential material (§12.2).

A profile with this source holds no credential of its own. At every launch the final executor, running under the agent's account, requests a lease and delivers the material through the harness's channel (environment variable at exec, stdin, or the Codex app-server's external tokens), never into argv, files or logs.

`node:<label>` (CIP-0010, the same-user file store) remains for single-user machines without a broker. A machine that runs agents as separate OS accounts uses `broker:`.

### 2. Launch-plan extension and the protected binding

- The credential travels in the plan only as metadata, in `extensions["works.relux.curator.credential/1"]` with `mode: "broker"`, `account` and `channel`; no new top-level plan member. The extension is marked as required-understanding: an executor that does not implement it refuses the plan instead of ignoring it.
- Intake refuses a broker-mode plan unless the executor declares `credential-injection/1` and can reach the broker socket (`credential_broker_unavailable`).
- Broker mode implements CIP-0010 C3.4 explicitly. Immediately before exec, the executor resolves `credential_binding/1` destination-locally (peer identity, profile, harness, account, channel, vendor endpoint, approved executable digest, policy generation), sends it in the lease request, and re-checks it before exec; the broker checks it against its own records and approved lists (broker §8.2).
- The executor refuses to exec when any other source supplies a credential for the harness (inherited environment, settings `apiKeyHelper`, configuration keys, native store selectors) (`credential_source_conflict`), and never replaces such a source silently.
- An executor may declare `credential-injection/1` only for a harness release that has been qualified to keep the credential out of children it does not control (MCP servers, hooks, tool subprocesses) and to use the leased source as the effective one. A clean environment at exec is not enough on its own.
- The plan digest is passed as `launch_id` for correlation; receipts bind the consumed plan, the qualified executor and the policy generation without material. A digest is not proof of what ran.

### 3. Codex auth owner

CIP-0010's single auth owner for Codex personal plans is implemented inside the broker (`codex-chatgpt` accounts):

- enrolment is a ceremony run by the broker under its own user (the vendor's device login into a fresh broker-owned home); no existing login is imported and no keyring item is exported;
- launches use **only** `codex app-server` with external tokens: the lease carries the access token and the ChatGPT account id; a 401 is answered through `lease.renew` within the app-server's response deadline, or the turn fails without any fallback login;
- launches never hold `auth.json`. `codex exec` is not served in broker mode; serving it would need an explicit amendment of CIP-0010's no-copy decision with operator consent, contents, lifetime and cleanup rules;
- each supported Codex release is qualified before the broker leases for it (`lease_harness_unqualified` otherwise). The mechanism is proven live on Codex 0.155.1; the supported release must be re-qualified first.

### 4. Agent OS accounts: the dispatcher and `curator agent-user`

relux-works/curator-dispatcher does the dispatcher's work from the platform design (architecture §7.1): it accepts a launch request, authenticates the caller by its OS account, checks the caller's grant and the machine's capacity, provisions the agent (helper `user.create`, a leaf grant for `agent:<generation>` narrowed to the request and the caller's grant, broker `bind`), starts the executor under the agent account through the helper's launcher, tracks the run in a durable record keyed by the caller's request id, cleans up (unbind, retire), and reconciles after crashes. It runs under its own unprivileged service account, which is the only account configured as a dispatcher in the helper and the broker.

Curator's commands are its clients:

```
curator agent-user create --label dev-7f3 --profile dev --account ivan/claude/personal \
    [--until <time>] [--network egress-a]            # dispatcher: provision
curator agent-user run    --label dev-7f3 [--plan <launch plan> | --profile dev]   # dispatcher: start
curator agent-user run    --dispatch --profile dev …  # dispatcher: dispatch (provision, start, clean up)
curator agent-user retire --label dev-7f3            # dispatcher: retire
curator agent-user list
```

- Curator composes the plan (compose-only) and passes it to the dispatcher as opaque bytes with its digest; the dispatcher never reads fragments or credentials.
- In the dispatcher's v0, the client runs the dispatcher command under the dispatcher's account through one sudoers rule; in v1 it talks to the dispatcher's socket. The commands and their results do not change between the two.
- A caller administers only the agents it provisioned, and can never obtain for an agent more than its own grant allows. Its requests are signed with a key associated with its OS account, and the broker keeps the caller's authorization as a dependency of every binding: revoking the caller's grant cuts its agents' new leases and renewals at once (owner decision 2026-10-10). Arbitrary `sudo -u` is never used instead of the launcher.
- Platform paths and accounts follow the root `/opt/swarma` (agent accounts `worker-<label>` with homes in `/opt/swarma/workers/`, services in `/opt/swarma/services/`); retired homes are archived under the helper's retention policy.

### 5. `curator broker`

`curator broker enrol|accounts|grant|revoke|bindings|status` are provider commands for the broker's command line (broker spec §14), in the same way that `curator network` fronts curator-network-profiles. `env status` reports, per managed home with a broker source: the account id, its kind and expiry state (stated, computed or unknown), whether the broker is reachable, and the last refusal; never material.

### 6. Network profiles

A broker account may require a network profile. Curator's launch already resolves the network profile for a Curator profile (`[bindings.profiles]` in the operator's destination-local `~/.curator/network.toml`); the executor passes the resulting record (`profile_ref`, `profile_digest`, assurance) in the lease request.

- In this version the check is **cooperative**: it shows that the requesting process declared the expected profile, and it is recorded as declared. It does not prove that traffic used the profile.
- An account that requires enforcement is refused (`lease_network_enforcement_unavailable`) until helper v1 publishes trusted applied state for the agent's generation; from then on the broker matches that state, not the request.

## Specification changes

- environments §7.4: the `broker:<account>` source, its channel table (shared with CIP-0010 C2), and its refusal codes; §12.1: the value in `credential_source`, never lockable.
- Decision 0013: the broker mode of `extensions["works.relux.curator.credential/1"]`, its required-understanding marking, and the intake refusal `credential_broker_unavailable`.
- Launcher SPEC: the protected binding at the final executor, the lease request, delivery rules, conflict refusal, the qualification conditions for `credential-injection/1`, and the refusal codes.
- Manager: `broker` and `agent-user` command groups.

## Implementation plan

1. **Formats** in curator-credential-broker: grants, revocations and socket frames frozen with canonical and negative vectors; the verifier with its mutant suite.
2. **Slice 0: one protected Claude launch.** Helper v0 with the launcher; broker slice 0 (file store, local grants and revocations, bind, lease, release, the `env` channel, audit); dispatcher v0 (requests, run records, grants, capacity, provisioning, start, cleanup, reconciliation); in Curator the executor with the broker client, the `broker:` source, the plan extension, `curator broker`, `curator agent-user` as the dispatcher's client, `env status` lines. Acceptance on hosted runners through `curator agent-user` and the dispatcher, with exactly the deployed sudoers rules.
3. **Slice 1: Codex** external tokens, the enrolment ceremony and the auth owner, qualified on the supported release.
4. **Slice 2: enforced networking** with helper v1 and applied state.

Keeper migration, a shared registry, roles and wildcards in grants, concurrency bounds, Muse (researched in parallel), parent access to child homes and donor deployment come later and do not block these slices.

## Test plan

Hosted runners only; no account, launcher or firewall test runs on a developer's or a production host.

- Production entry: `curator agent-user create` and `run` through the dispatcher, then a tracked launch under the agent account receives a lease and runs Claude; the token is in the harness process environment only and in no file, argv, log or covered child process.
- Negatives: no binding; a retired generation; a recycled UID or a repeated label; another dispatcher's agent; wrong profile; wrong harness; expired grant; revoked grant; unreadable revocation state; revoked account; broker unreachable; executor without `credential-injection/1`; conflicting inherited credential; unqualified harness release; a broker connection inherited across the launcher (it must not reach the executor); unapproved executor digest.
- Codex (slice 1): eight concurrent launches near expiry cause one refresh; a 401 renews within the deadline and the turn continues; a slow or failed renewal fails the turn without a fallback login.
- No material in plans, fragments, receipts, logs, `env status` or covered child processes (a scan of all artifacts).

## Open questions for the operator

1. Resolved (owner, 2026-10-09): the dispatcher is its own module and `curator agent-user` is its client.
2. Which executor gets the broker client first. Recommended: Curator's own small executor (started by the launcher under the agent account); the board's spawn path and the session host then start agents through the dispatcher instead of embedding the client.
3. Grant registry beyond the broker's local state: open platform question (D-R6).
