# CIP-0009: Donor-side deployment and the worker-to-project bridge

- **Status:** Draft
- **Owner:** ivan-curator (orchestrator); decision: operator (both owners for the bridge contract)
- **Created:** 2026-10-08
- **Related:** owner brief 2026-10-08; [CIP-0008](CIP-0008-remote-worker-launch-mode.md) (the lockdown launch mode); [CIP-0010](CIP-0010-credentials-setup-token-and-inherited-auth.md); [CIP-0007](CIP-0007-manager-provisioned-cli-tools.md) (provisioned binaries); [Decision 0009](../decisions/0009-first-party-module-roots.md); environments [§2.2](../protocol/environments.md#22-mcp-declaration-packages); VISION v1.3 (relux-works/swarm-platform-architecture) §0, LCH §8, the sequences `external-agent-onboarding`, `remote-workplace-attach`, `remote-worker-start`, `mailbox-delivery`; wiki `session-host/architecture.ru.md` §7.2, §7.4, §7.5, §7.9, §7.10; relux-works/remote-workplace protocol v2.1; relux-works/remote-worker-harness (`rwh`)
- **Affects:** a new Curator command group `remote-worker`; a first-party module `swarma-remote-tools` (local MCP server); manager §12 (locked donor configuration); the remote executor (`rwh` successor) on our host; diagrams in `cips/diagrams/`

## Summary

This CIP specifies the **donor side** of a remote worker and the **bridge** between the donor's machine and the project's host: what Curator installs on the donor machine at first deployment (an OS user, a kernel sandbox, a per-user firewall, a locked machine configuration, a local MCP server for the remote tools), how the initial exchange works (invitation, key pair, self-signed certificate, join point, out-of-band fingerprint check, root-signed admission, encrypted credential package), how the harness talks to our host (one SSH connection from the donor towards our host, carrying the framed Remote Bash protocol and the mailbox), how MITM is defended (DNS-published fingerprints under DNSSEC, pinned keys both ways, signed envelopes), and how a worker is retired on both sides. It decides that the remote tools are an **MCP server** while the initial exchange is a **Curator CLI step**, never a tool the model can call. Diagrams: `diagrams/donor-first-deployment.puml`, `diagrams/join-handshake.puml`, `diagrams/remote-worker-turn.puml`, `diagrams/remote-worker-retire.puml`, `diagrams/donor-side.dsl` (C4 containers).

## Motivation and user stories

- **Owner (2026-10-08):** "Curator on the donor machine manages the MCP setup, including a local MCP server for the remote tools, at first deployment of the environment"; "what the donor sees, how they stop it, what is logged on their side"; "the full set: handshake, join point, DNS fingerprints, MITM, Remote Bash, mailbox, retire, with diagrams".
- **A person who downloaded our toolchain** and wants to run their agent on our task: one invitation, one command, a visible result ("registered, waiting for tasks"), and a way out.
- **Our orchestrator** wants the remote worker to be an ordinary worker: pin-checked launch, mailbox tasks, results as outcome proposals, no commands ever sent towards the donor's machine (architecture §7.9: connection towards the host only, C19).
- **Both owners** want one strong boundary and few moving parts (remote-workplace design rule).

## Current state

- `rwh` (relux-works/remote-worker-harness) runs Claude, Codex and Muse on the dedicated Mac mini with the built-ins locked (CIP-0008 §Current state) and the tools served from the project machine over `ssh -R` (a reverse-forwarded Unix socket) or through a relay; its `rwh worker` mode turns addressed a2a messages into turns under allow-from, budget and rate guards. The tunnel is opened **by the project side into the remote machine** and the remote machine is *ours*; nothing exists for a foreign donor, and the host side keeps no per-worker OS user (that is the remote workplace of architecture §7.9, designed in VISION v1.3 and not yet implemented).
- relux-works/remote-workplace v2.1 gives the **host side** of tool execution: a fresh hardened container per call inside a dedicated VM, a per-worker policy (tools, write scope, network mode, limits), change extraction as a reviewed patch, an egress service. This CIP does not change it; the remote workplace of VISION v1.3 (an OS user on our host) and the container workplace are two backends of the same executor.
- Curator today: no `remote-worker` commands; MCP declaration packages are `git`-sourced `agent-mcp.json` with `stdio` (bare command on `PATH`) or `http` (`https` only) transports, bounded by `mcp_package_allowlist` (§2.2); the manager never installs or launches a server (§2.2); first-party modules have roots (Decision 0009); CIP-0007 proposes operator-trusted provisioning of binaries.
- Keys: the key keeper of architecture §7.2 is design; `curator-trust` is a v0.4 draft; today's a2a uses per-agent Matrix accounts with tokens in `~/.config/a2a-swarm/` (0600).

## Design

### Options considered

**A. Where the remote tools live**
1. *MCP server on our host, reached by the harness over `http`* (environments §2.2 `http`). The harness would need a network path and an authentication secret it holds itself; the donor's firewall would have to allow the harness user out to our host; the secret would be in the harness's reach. Rejected.
2. *Local MCP server on the donor machine (`stdio`), Curator-managed, holding the SSH client and the pinned keys.* The harness sees only a local process; the keys and the connection belong to the server process (same OS user, but the model has no tool that reads files); the firewall allows the harness user out only to the provider API, and allows the server process out only to our join point and SSH host. **Recommended.**
3. *Curator skill with scripts.* Scripts need a local shell, which the lockdown removes. Rejected for tools; kept for prompts.

**B. How the donor receives tasks and messages**
1. *A carrier client (Matrix) on the donor machine.* Mirrors our bridge, but puts carrier credentials on a foreign machine and adds a second network path. Later option.
2. *Mailbox over the tool channel.* The same SSH connection carries `mailbox.read`, `mailbox.post` and server-pushed `mailbox.notify` frames; the carrier identity of the worker lives in **our** bridge, as for local agents (C2 of the owners' call: the agent never reads the carrier). The donor holds no carrier credential at all. **Recommended for the first release.**

**C. The initial exchange**
1. *An MCP tool `enrol`.* The model would see the key material or at least drive the exchange. Rejected.
2. *A Curator CLI step run by a human on the donor machine* (`curator remote-worker init <invitation>`), with the private key generated inside the OS keyring of the harness user and never exported. **Recommended.**

### Recommendation

**D1. Components on the donor machine** (C4: `diagrams/donor-side.dsl`).

| Component | Runs as | Job |
|---|---|---|
| `curator` (donor install) | the donor (the machine's owner) for `init`; the harness user for everything else | first deployment, status, stop, revoke; composes the lockdown launch (CIP-0008) |
| privileged helper (`swarma-helper`) | root for one command (sudoers rule limited to this executable) | creates the harness OS user, the home, the firewall rules, the sandbox profile; removes them at revoke (architecture §7.5) |
| harness OS user `swarma-rw-<project>` | — | the kernel boundary: home 0700, no password, no interactive login, process and disk quotas |
| remote-tools MCP server (`swarma-remote-tools`) | the harness user | a `stdio` MCP server: tools `bash`, `read_file`, `write_file`, `apply_patch`, `mailbox_read`, `mailbox_post`; holds the SSH client, the pinned keys and the audit log; no model-facing enrolment |
| remote-worker supervisor (`curator remote-worker run`) | the harness user | launches the harness under the lockdown plan, turns mailbox items into turns, posts results, enforces budgets and lifetimes (the `rwh worker` guards: allow-from, daily tokens, rate, ping-pong, turn timeout, lifetime) |
| per-user egress proxy (network profile) | the harness user or a system service | the only network exit of the harness user: provider API hosts for the pinned harness, nothing else; the server process has a separate rule to our join point and SSH host |
| locked machine configuration | files owned by the donor's account, read by Curator | `tool_posture.remote-worker: lockdown`, `permissions.remote-worker: remote-auto`, `mcp_package_allowlist: [swarma-remote-tools]`, `passable_env_names: []`, the pinned harness release, the project binding (host, SSH host key fingerprint, root fingerprint) |

**D2. OS sandbox per platform.**
- *macOS:* a hidden standard user created by the helper (`sysadminctl`/`dscl`, no secure token, no login), `pf` anchor with `user` rules: the harness UID may connect only to `127.0.0.1` ports of the egress proxy and nothing else; the server process UID (same user; distinguished by the proxy's socket ownership and by a second anchor keyed on the destination: our join point and SSH host only); Seatbelt (`sandbox-exec`) profiles written by Curator for the harness process (deny file reads and writes outside the managed home and the scratch dir; deny AppleEvents, pasteboard, LaunchServices `open`, securityd beyond the keychain item it needs; the Muse profile is the one `rwh` measured); `launchd` user agents for the supervisor so it survives logout; quotas through `launchd` limits.
- *Linux:* a system user with `nologin`, home 0700; `nftables` rules with `meta skuid` for the harness UID (loopback to the proxy only) and the server UID (join point and SSH host only); the harness started under `systemd-run --uid … -p ProtectSystem=strict -p ProtectHome=tmpfs -p PrivateTmp=yes -p NoNewPrivileges=yes -p RestrictAddressFamilies=AF_UNIX,AF_INET,AF_INET6 -p BindReadOnlyPaths=<managed home>` with Landlock or bubblewrap where available for the read boundary Muse needs; quotas through cgroups.
- *Windows:* later (owners' call C18).
- Curator records the sandbox profile digest in the plan (CIP-0008 R5) so a changed profile is a changed plan.

**D3. The remote-tools MCP server as a declared package.** `swarma-remote-tools` is a first-party module (Decision 0009) shipped with the toolchain, declared to profiles as an MCP declaration package (`agent-mcp.json`, `transport: stdio`, `command: swarma-remote-tools`, no `env_names`), pinned in the profile lock like any package, and the only entry of the donor's locked `mcp_package_allowlist`. The command resolves on the managed PATH (CIP-0004 append rule) to the pinned binary. It exposes:

| Tool | What it does | Executes where |
|---|---|---|
| `bash {cmd, cwd?, timeout?}` | Remote Bash request on the channel | our host, inside the workplace (OS user or container backend) |
| `read_file`, `write_file`, `apply_patch` | file operations inside the workplace | our host |
| `mailbox_read {id?}` | fetch an admitted message with its verification record | our bridge |
| `mailbox_post {binding, text}` | post an outbound message under the worker's bound identity | our bridge (signs with the worker's identity, audience projection) |

Nothing else. No `enrol`, no `key`, no `config`. The server refuses any `tools/call` outside this list with an error result that never reaches the channel (the `rwh` policy gate), and logs the name.

**D4. First deployment** (`diagrams/donor-first-deployment.puml`, `diagrams/join-handshake.puml`).
1. We issue an **invitation**: `{join_point_url, root_fingerprint, invitation_code, project, role, expires_at}`; the code is one-time, 20+ characters, shown to the human over a second channel (chat, voice).
2. The donor (the machine's owner) runs `curator remote-worker init <invitation-file>` (equivalently `swarma join <invitation>`). Curator: resolves the join point's DNS name and **requires DNSSEC-validated** `TXT _swarma.<domain>` carrying the root fingerprint and `SSHFP` records for our SSH host; refuses if the TXT fingerprint differs from the invitation's; calls the helper to create the harness user, home, firewall and sandbox; **generates the key pair inside the harness user's OS keyring** (macOS login keychain item of that user; Linux `secret-service` or a 0600 file under the home when no keyring exists) and a self-signed certificate `{public key, name, role, contact, expires}` signed over the invitation code; shows the fingerprint to the donor.
3. Curator POSTs the certificate to the join point over HTTPS (TLS pinned to the certificate published in DNS `TLSA` or to the root-signed join-point certificate from the invitation; the join point accepts only `cert` and `collect`; no commands).
4. Our side: the operator (or an orchestrator with the `onboard` grant plus operator confirmation) **compares the fingerprint over the second channel** (the invitation code binds the certificate to the invitation; the human reads back the fingerprint), pins the key in the registry, has the root sign the admission record, issues the grants (post to the project room's worker thread, read own mailbox, no delegation, expiry), and builds the **credential package**: `{our root public key, host, SSH host key fingerprint, workplace user name, carrier identity (held by our bridge, not sent), project binding digest, pinned harness release, expiry}`, encrypted to the worker's key (X25519 + AEAD) and signed by the operator.
5. Curator on the donor collects the package (`collect` with the certificate's signature), decrypts it through the keyring (the private key never leaves the keyring process boundary), verifies the operator's signature against the root fingerprint that DNS and the invitation both named, writes the locked machine configuration and the project binding, installs the `swarma-remote-tools` declaration into the `remote-worker` profile, and prints "registered; waiting for tasks".
6. Our dispatcher provisions the workplace (an OS user on our host, `authorized_keys` with `restrict,command="swarma-rb-exec"` and the worker's SSH public key, firewall per UID), as in `remote-workplace-attach`.

**D5. The bridge** (`diagrams/remote-worker-turn.puml`).
- *Connection:* the server process opens **one SSH connection from the donor machine to our host**, as the workplace user, with the worker's key; the host key is checked against the pinned fingerprint from the package **and** the DNSSEC `SSHFP` record; `restrict` plus a forced command on our side means the connection can only run the Remote Bash executor. Our host never connects to the donor and never sends commands into the donor's machine; the server reconnects with backoff after a drop.
- *Framing:* one multiplexed channel over the SSH session, length-prefixed JSON frames (`swarma-rb/1`): requests `{id, kind: exec|cancel|stdin, cmd, cwd, env_allow[], timeout_s, max_output_bytes}` and `{id, kind: file.read|file.write|patch.apply, path, …}`; replies `{id, kind: stdout|stderr|exit|error, seq, bytes|code}`; mailbox frames `{id, kind: mailbox.read|mailbox.post}` and the server-pushed `{kind: mailbox.notify, message_id}`; every request has a deadline and an output cap; a dropped channel ends the child processes on our side (architecture §7.9 "Remote Bash").
- *Audit, both sides:* our executor logs who, what, when and the exit; the donor's MCP server logs tool name, argument hash and sizes (never arguments or environment), so the donor can see what left their machine.
- *Tasks and turns:* the orchestrator posts a signed task message to the worker's mailbox (a snapshot of one element; no board access); our bridge admits it (signature, grant, decision guard) and pushes `mailbox.notify` down the channel; the supervisor on the donor turns it into the harness's next turn; the result is posted through `mailbox_post`, signed by our bridge with the worker's bound identity (the worker holds no carrier credential), and becomes an outcome proposal.
- *What the worker sees:* its managed home, the task snapshot, its own mailbox with verification records. *What it never sees:* our board, the carrier, carrier credentials, other homes, the network beyond the proxy.

**D6. MITM and identity.** First contact is protected by two independent anchors — the DNSSEC-validated `TXT`/`SSHFP`/`TLSA` records and the out-of-band fingerprint check bound to the one-time invitation code — and by the self-signature proving key possession. After that everything is pinned: the worker's key in our registry and `authorized_keys`, our root and SSH host key on the donor, operator-signed packages, signed envelopes over exact bytes with freshness and replay rules (VISION ADM). Compromise of the worker's key: the operator revokes (root-signed record), removes `authorized_keys`, and the bridge refuses the next frame; compromise of our host key: a new key, new `SSHFP`, and every donor re-runs `init --rotate-host`.

**D7. Retire** (`diagrams/remote-worker-retire.puml`). Our side: revoke grants and, if needed, the key; drop the workplace (stop processes, archive the home, delete the user, remove firewall rules). Donor side: `curator remote-worker stop` (kill the harness user's processes, mark stopped) and `curator remote-worker revoke` (delete the keyring item, the locked configuration and the managed home; call the helper to remove the user, firewall and sandbox). The identity stays pinned unless revoked, so the same worker can return to a new workplace.

**D8. Donor control surface.** `curator remote-worker status` (posture, project, connection state, last tool call, budget used, audit path), `stop`, `revoke`, `audit tail`, and the locked configuration the owner of the donor machine owns. The harness user cannot change any of it; the operator on our side cannot either.

## Security considerations

- **Boundary on the donor:** the OS user plus the kernel sandbox and the per-UID firewall (D2). The MCP server runs in the same user as the harness, so the private key is protected from the *model* by the lockdown (no file tool) and from a compromised *process* only by the keyring's access control; a stronger split (server under a second user, the harness reaching it over a Unix socket) is the next step once a stdio server over a socket relay is measured, as `rwh` did for Muse.
- **Boundary on our host:** the workplace user and the remote-workplace policy; the worker can only run what the policy allows, where it allows it.
- **Network:** the harness user reaches the provider API only through the proxy; the server reaches only our hosts; nothing listens on the donor machine.
- **Secrets:** the worker's private key never leaves the keyring; the provider credential enters the harness per launch (CIP-0010); the carrier credential stays in our bridge; no secret is in argv, the plan or the invitation.
- **Supply chain:** the binaries on the donor machine come from the toolchain release with checksums and attestations (R55 discipline); CIP-0007 governs anything else the donor installs.
- **Replay and freshness:** invitation codes are one-time; the join point rate-limits; envelopes carry `issued_at`, `expires_at` and a nonce.

## Compatibility and migration

- Nothing changes for local launches. The donor-side commands are new. `rwh` becomes the executor on our host behind the same framed protocol; its `worker` guards move into the supervisor.
- The remote workplace backend on our host may be the VISION OS-user workplace or the remote-workplace container; the protocol is the same.

## Specification changes

- A new Curator command group `remote-worker` (`init`, `status`, `stop`, `revoke`, `run`, `audit`), and the `swarma-helper` privileged helper with its sudoers rule, in manager §12 (donor profile) and a new manager section "remote worker on a donor machine".
- `swarma-remote-tools` as a first-party module root (Decision 0009) and as an MCP declaration package; the six tools above as its closed tool list.
- The `swarma-rb/1` framed protocol as a protocol document (requests, replies, mailbox frames, deadlines, caps, audit fields).
- The invitation and credential package as schemas (`swarma-invitation/1`, `swarma-credential-package/1`), the join point's two verbs, the DNS record conventions (`TXT _swarma.<domain>`, `SSHFP`, `TLSA`, DNSSEC required).
- The donor's locked machine configuration as a named manager profile.

## Implementation plan

1. Protocol documents and schemas (this CIP's §Specification changes); the C4 and sequence diagrams folded into the platform repository's `diagrams/`. Size M.
2. `swarma-remote-tools`: the MCP server with the six tools, the SSH client with pinned host keys, the framed client, the audit log. Size L.
3. Our-side executor: the forced command `swarma-rb-exec` speaking `swarma-rb/1` over the SSH session, backed by the workplace; the mailbox frames bridged to M3. Size L (reuses `rwh` and remote-workplace).
4. `curator remote-worker init|status|stop|revoke|run` and the helper, macOS first, then Linux. Size L.
5. Join point service: two verbs, DNS publishing, operator confirmation flow with the companion app or chat. Size M.
6. Lab: one donor machine (a hosted runner) joining a lab host; the measurements of D2 per OS. Size M.

## Test plan

- Handshake negatives: wrong invitation code, expired invitation, DNS without DNSSEC, TXT fingerprint mismatch, package signed by a wrong key, package encrypted to a wrong key, replayed `collect`.
- Connection negatives: host key mismatch (pinned vs offered), unknown worker key, a second connection while one is up, frames above the cap, deadline overrun, channel drop (children die).
- Sandbox positives/negatives per OS: file reads outside the home refused, egress outside the proxy refused, the proxy refuses a non-provider host, the helper refuses a second user with the same name.
- Tool list: `tools/list` is exactly the six; a `tools/call` of another name is an error result and an audit line.
- Retire: after `revoke`, no process, no keyring item, no user, no firewall rule remains; the registry still lists the identity unless revoked.

## Open questions for the operator

1. **Two OS users on the donor (harness and server) from the start, or one?** Recommended: one for the first release, with the split as the next step once measured.
2. **Join point hosting.** A minimal HTTPS service on our host, or a function behind our domain? Recommended: on our host, two verbs only, rate-limited.
3. **DNSSEC availability** on our domain. Required by this design; confirm the registrar supports it.
4. **Carrier identity of a remote worker:** held by our bridge only (recommended), or also as a device credential on the donor for offline doorbells (later option B)?
5. **Who may run `init` on a donor:** only a human owner of the donor machine (recommended), or also an orchestrator of the donor's organisation with a grant?
