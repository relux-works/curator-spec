# CIP-0011: Credential broker leases and agent OS users

- **Status:** Draft
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-09
- **Related:** [CIP-0010](CIP-0010-credentials-setup-token-and-inherited-auth.md) (credential sources, executor capability, CIP-0003 disposition); [CIP-0008](CIP-0008-remote-worker-launch-mode.md), [CIP-0009](CIP-0009-donor-side-deployment-and-bridge.md); [Decision 0013](../decisions/0013-execution-ownership-and-launch-plans.md) (launch plans); environments §7.4, §10.3, §12.1–§12.2; relux-works/curator-credential-broker `spec/broker.md` (draft v0.1); relux-works/curator-host-helper `spec/helper.md` (draft v0.1); relux-works/curator-network-profiles (binding records)
- **Affects:** environments §7.4 and §12.1 (a credential source value), Decision 0013 (the credential plan extension), the launcher SPEC, the manager command set (`broker`, `agent-user`), the final executors (session host, task-board spawn runner, the remote-worker supervisor)

## Summary

CIP-0010 lets a managed home use a credential enrolled once instead of a login per home, but its authentication node lives in one OS user's store and cannot serve agents that run as other OS users. This CIP connects Curator to two new platform components:

- **curator-credential-broker** holds each account once, under its own service user, and leases it to launches that a signed grant authorises, identifying the launching process by its kernel-reported UID. It also runs the single Codex auth owner per account.
- **curator-host-helper** creates and removes per-agent OS users (and, in its v1, per-user firewall rules) through a closed, journaled operation schema run with `sudo`.

Curator gains a credential source `broker:<account>`, a broker client in the final executor, the plan member `credential` mode `broker`, `curator broker …` commands, and `curator agent-user …` commands that play the dispatcher's role until a dispatcher exists. The result is the owners' first MVP shape: one subscription, one machine, a chain of OS users, each agent launching from its own account and receiving the subscription's credential from the broker.

## Motivation

- **Owner (2026-10-09):** a launch of an environment with a profile should run from its own OS account and get its token from the broker; the mechanism must work when orchestrators and helpers create agents, including ephemeral agents with a user created for one task; a subscription's traffic should be bound to a network profile.
- CIP-0010 slice 0 named the missing piece: a peer-authenticated interface across OS users. Designing it as the platform's credential broker from the start avoids a second rewrite.

## Design

### 1. Credential source `broker:<account>`

CIP-0010's `credential_source.<profile>.<harness>` (user-owned layer, never lockable) gains the value `broker:<account>`, naming a broker account id. A profile with this source:

- holds no credential of its own;
- at every launch, the final executor asks the broker for a lease for (harness, profile, account), passing the launch's network binding record when curator-network-profiles resolved one;
- delivers the material through the harness's channel (environment variable at exec, stdin, Codex app-server external token, or a per-turn token-only Codex home) and never into argv, files, logs or MCP children.

`node:<label>` (CIP-0010, the same-user file store) remains for single-user, interactive machines without a broker. A machine that runs agents as separate OS users uses `broker:`.

### 2. Plan member and gates

The CIP-0010 extension `works.relux.curator.credential/1` gains `mode: "broker"` with `{ account, harness_channel }` and no value. Intake refuses a broker-mode plan unless the executor declares `credential-injection/1` and can reach the broker socket (`credential_broker_unavailable`). The executor's lease request carries the plan digest as `launch_id`, so the broker's audit names the exact launch.

The executor refuses to exec when any other source supplies a credential for the harness (inherited environment, settings `apiKeyHelper`, configuration keys) (`credential_source_conflict`), as in CIP-0010.

### 3. Codex auth owner

CIP-0010's "single auth owner" for Codex personal plans is implemented inside the broker (`codex-chatgpt` accounts). Launches never hold `auth.json`; app-server launches renew a rejected access token through the broker without a restart; `codex exec` launches receive a per-turn token-only home. The external-token path is qualified per Codex release before the broker leases it (`lease_harness_unqualified` otherwise); it is proven live on Codex 0.155.1 and must be re-qualified on the supported release first.

### 4. Agent OS users: `curator agent-user`

Until a dispatcher exists, Curator plays its role:

```
curator agent-user create --label dev-7f3 --profile dev \
    --grant <grant file or id> [--until <time>] [--network egress-a]
curator agent-user remove --label dev-7f3
curator agent-user list
```

`create` runs curator-host-helper (`user.create`, and in helper v1 `fw.apply` with the network profile's proxy), then `bind`s the new UID in the broker with the grant chain and the account generation from the helper ledger. `remove` unbinds first, then removes the user. The calling OS user must be a configured helper caller and a configured broker dispatcher; nothing else changes when a dispatcher later takes over the same two calls.

### 5. `curator broker`

`curator broker enrol|accounts|grant|revoke|bindings|status` are provider commands for the broker's command line (broker spec §14), in the same way that `curator network` fronts curator-network-profiles. `env status` reports, per managed home with a broker source: the account id, its kind and expiry state (stated, computed or unknown), whether the broker is reachable, and the last refusal; never material.

### 6. Network profiles

A broker account may require a network profile. Curator's launch already resolves the network profile for a Curator profile (`[bindings.profiles]` in the operator's `~/.curator/network.toml`); the executor passes the resulting binding record in the lease request and the broker refuses a mismatch. With helper v1 rules the agent's UID can reach the network only through that profile's proxy.

## Specification changes

- environments §7.4: the `broker:<account>` source, its channel table (shared with CIP-0010 C2), and its refusal codes; §12.1: the value in `credential_source`.
- Decision 0013: `credential` mode `broker`; intake refusal `credential_broker_unavailable`.
- Launcher SPEC: the lease request at the final executor, delivery rules, the refusal codes.
- Manager: `broker` and `agent-user` command groups.

## Implementation plan

1. **curator-host-helper v0** (users, ledger, journal, audit; hosted-runner qualification).
2. **curator-credential-broker slice 0** (broker spec §16), including the Codex external-token re-qualification on the supported release.
3. **Curator:** the broker client in the final executor (task-board spawn runner first, then the session host), the `broker:` source, the plan mode, `curator broker`, `curator agent-user`, `env status` lines.
4. **Lab chain on hosted runners:** enrol, create an agent user, bind, launch Claude and Codex under it, and the refusal set (other UID, other account, expired or revoked grant, network mismatch, conflicting source).
5. **helper v1** firewall rules, making network requirements enforced.

## Test plan

- Production entry: a tracked launch under an agent user created by `curator agent-user create` receives a lease and runs; the token is in the harness process environment only.
- Negatives: no binding, recycled UID, wrong profile, wrong harness, expired grant, revoked grant, revoked account, network mismatch, broker unreachable, executor without `credential-injection/1`, conflicting inherited credential.
- Codex: eight concurrent launches near expiry cause one refresh; an app-server 401 renews and the turn continues.
- No material in plans, fragments, receipts, logs, `env status` or MCP children (scan of all artifacts).

## Open questions for the operator

1. Should `curator agent-user` stay after a dispatcher exists (for manual setups), or be removed?
2. Should the session host or the task-board runner be the first executor with the broker client? Recommended: the task-board runner (tracked spawns are the main consumer today).
3. Grant registry beyond the broker's local file: open platform question (D-R6).
