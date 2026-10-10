// C4 (Structurizr DSL) fragment for CIP-0009 (revision 2): the donor machine and the bridge to our host.
// Style follows relux-works/swarm-platform-architecture diagrams/c4 (hierarchical identifiers, one container per process).
// Revision 2: two OS identities on the donor (untrusted harness, trusted bridge); the relay holds no keys and no network;
// the bridge signs outbound envelopes with the worker's key; the harness reaches only the relay socket and the provider proxy.
workspace "Remote worker on a donor machine" "CIP-0008/0009: lockdown harness, trusted bridge identity, minimal remote-tools relay, one SSH connection towards the project host" {
  !identifiers hierarchical

  model {
    donorOwner = person "Donor (the machine's owner)" "Owns the donor machine; runs init, status, stop, leave, purge"
    operator = person "Project operator" "Confirms fingerprints, issues grants and packages"

    donor = softwareSystem "Donor machine" "A machine we do not own, lending a harness subscription" {
      curator = container "curator (donor install)" "Go CLI" "init/status/stop/run/leave/purge; consumes the composed lockdown plan; writes the locked machine config (bridge-owned)"
      helper = container "swarma-helper" "privileged helper (sudoers, absolute path)" "closed schema: create-worker, remove-worker, set-egress, apply-sandbox, rollback; allocated identifiers; journal"
      harnessUser = container "Harness identity swarma-rw-<project>" "OS user, home 0700, quotas, Seatbelt/Landlock read boundary" "the UNTRUSTED side: managed home and scratch dir only"
      bridgeUser = container "Bridge identity swarma-rb-<project>" "OS user, system service (launchd daemon / systemd)" "the TRUSTED side: keys, locked config, audit, lifecycle state"
      supervisor = container "Bridge service: supervisor" "curator remote-worker run (bridge identity)" "launches the harness as the harness identity; admitted mailbox items become turns via the session-input adapter; budgets, rate, lifetime (trusted-side counters)"
      bridgeCore = container "Bridge service: SSH client + signer + admission" "swarma-bridge (bridge identity)" "one SSH connection to our host (K_ssh, host key pinned, rechecked on every reconnect); signs outbound envelopes with K_sig; admits inbound items; durable cursors; audit"
      keys = container "Key store" "0600 files owned by the bridge identity (keyring-backed later)" "K_sig (Ed25519), K_enc (X25519), K_ssh (Ed25519); unreadable by the harness identity"
      harness = container "Harness" "Claude Code / Codex / Muse (harness identity, lockdown plan)" "no local tool offered to the model; only the relay; provider credential injected per launch"
      relay = container "swarma-remote-tools" "local stdio MCP relay (harness identity)" "no keys, no network; forwards tools/call to the bridge socket; effective tool set = policy intersection"
      socket = container "Relay socket" "Unix socket, peer credentials checked" "only the harness identity of this project may connect"
      proxy = container "Provider proxy" "bridge identity or system service" "the harness identity's only network exit: provider API hosts of the qualified tuple"
      egress = container "Kernel egress + sandbox" "pf/nftables by UID, Seatbelt/systemd+Landlock" "harness UID -> proxy only; bridge UID -> SSH host and join point only; reads confined"
    }

    project = softwareSystem "Project host" "Our host" {
      joinPoint = container "Join point" "HTTPS, three verbs: challenge, cert, collect" "atomic invitation consumption, tombstones, rate limits; never commands"
      sshd = container "sshd + swarma-rb-exec" "Match block for workplace users; root-owned AuthorizedKeysFile; forced command by absolute path" "speaks swarma-rb/1; executes under swarma-workplace-exec/1"
      workplace = container "Remote workplace (OS-user backend)" "one OS user per worker; policy: tools, write scope, network, limits, env_allow" "where every tool call runs; audit; cleanup"
      bridge = container "Bridge (M3)" "broker, mailbox, trust gate" "admits messages; verifies the worker's signature; carries bytes unchanged under a distinct carrier account"
      registry = container "Trust registry + key keeper" "pins K_sig, K_enc, K_ssh; grants; root-signed admission and revocations" "operator certificates chained to the root"
      dns = container "DNS zone (DNSSEC, mandatory)" "TXT _swarma, SSHFP, TLSA" "published fingerprints of the environment, validated inside the client"
    }

    provider = softwareSystem "Model provider API" "Anthropic / OpenAI / Meta" "External"

    donorOwner -> donor.curator "init <invitation>, status, stop, leave, purge"
    donor.curator -> donor.helper "create/remove identities, egress, sandbox (sudo; closed schema)"
    donor.curator -> donor.keys "generate K_sig, K_enc, K_ssh (bridge identity); decrypt the package"
    donor.curator -> project.dns "validate the fingerprints (DNSSEC in the client; DNS-over-HTTPS fallback)"
    donor.curator -> project.joinPoint "challenge; cert (signed swarma-join/1 transcript + code); collect (HTTPS: Web PKI, pinned by TLSA)"
    donor.supervisor -> donor.harness "launch as the harness identity under the lockdown plan; next admitted turn"
    donor.harness -> donor.relay "MCP stdio: tools/call"
    donor.relay -> donor.socket "forward (peer credentials checked)"
    donor.socket -> donor.bridgeCore "authenticated local RPC"
    donor.harness -> donor.proxy "model API over the proxy only"
    donor.proxy -> provider "HTTPS"
    donor.bridgeCore -> donor.keys "sign envelopes with K_sig; SSH with K_ssh"
    donor.bridgeCore -> project.sshd "one SSH connection; swarma-rb/1 frames (bounded CBOR, op_key idempotency)"
    project.sshd -> project.workplace "exec / file ops as the workplace user; process-group lease"
    project.sshd -> project.bridge "mailbox.read / mailbox.post (worker-signed bytes) / mailbox.notify (advisory)"
    operator -> project.joinPoint "check the enrolment against the signed card or the invitation; release package"
    operator -> project.registry "pin keys; root-signed admission; grants"
    project.bridge -> project.registry "verify signatures, grants, revocation, freshness"
  }

  views {
    container donor "DonorContainers" "Donor machine: the untrusted harness identity (harness, relay), the trusted bridge identity (supervisor, SSH client, signer, keys, audit), the proxy and the kernel boundary" {
      include *
      autolayout lr
    }
    container project "ProjectSideContainers" "Our host: join point, sshd with the forced executor, the OS-user workplace, the bridge, the registry and DNS" {
      include *
      autolayout lr
    }
  }
}
