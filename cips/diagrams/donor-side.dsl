// C4 (Structurizr DSL) fragment for CIP-0009: the donor machine and the bridge to our host.
// Style follows relux-works/swarm-platform-architecture diagrams/c4 (hierarchical identifiers, one container per process).
workspace "Remote worker on a donor machine" "CIP-0008/0009: lockdown harness, local remote-tools MCP server, one SSH connection towards the project host" {
  !identifiers hierarchical

  model {
    donorAdmin = person "Donor (the machine's owner)" "Owns the donor machine; runs init, status, stop, revoke"
    operator = person "Project operator" "Confirms fingerprints, issues grants and packages"

    donor = softwareSystem "Donor machine" "A machine we do not own, lending a harness subscription" {
      curator = container "curator (donor install)" "Go CLI" "init/status/stop/revoke; composes the lockdown launch; writes the locked machine config"
      helper = container "swarma-helper" "privileged helper (sudoers)" "creates the harness user, firewall rules, sandbox profile; removes them at revoke"
      harnessUser = container "Harness OS user swarma-rw-<project>" "OS user, home 0700, quotas" "the kernel boundary on the donor"
      supervisor = container "Remote-worker supervisor" "curator remote-worker run" "launches the harness under the lockdown plan; mailbox items become turns; budgets, rate, lifetime"
      harness = container "Harness" "Claude Code / Codex / Muse" "no local tools; only the remote-tools MCP; provider credential injected per launch"
      mcp = container "swarma-remote-tools" "local stdio MCP server" "bash, read_file, write_file, apply_patch, mailbox_read, mailbox_post; holds the SSH client and pinned keys; audit log"
      keyring = container "OS keyring" "login keychain / secret service" "the worker's private key, never exported"
      proxy = container "Egress proxy" "network profile" "the harness user's only network exit: provider API hosts"
      firewall = container "Kernel firewall + sandbox" "pf/nftables by UID, Seatbelt/systemd+Landlock" "harness -> proxy only; mcp -> join point and SSH host only; file reads confined"
    }

    project = softwareSystem "Project host" "Our host" {
      joinPoint = container "Join point" "HTTPS, two verbs" "accepts certificates, releases packages; never commands"
      sshd = container "sshd + swarma-rb-exec" "forced command" "speaks swarma-rb/1; executes in the workplace"
      workplace = container "Remote workplace" "OS user or container backend" "where every tool call runs"
      bridge = container "Bridge (M3)" "broker, mailbox, trust gate" "admits messages; holds the worker's carrier identity; signs outbound"
      registry = container "Trust registry + key keeper" "pins, grants, revocations" "root-signed admission"
      dns = container "DNS zone (DNSSEC)" "TXT _swarma, SSHFP, TLSA" "published fingerprints"
    }

    provider = softwareSystem "Model provider API" "Anthropic / OpenAI / Meta" "External"

    donorAdmin -> donor.curator "init <invitation>, status, stop, revoke"
    donor.curator -> donor.helper "create/remove user, firewall, sandbox (sudo)"
    donor.curator -> donor.keyring "generate key pair; decrypt package"
    donor.curator -> project.dns "resolve with DNSSEC; compare fingerprints"
    donor.curator -> project.joinPoint "POST cert; collect package (TLS pinned by TLSA)"
    donor.supervisor -> donor.harness "launch under the lockdown plan; next turn on doorbell"
    donor.harness -> donor.mcp "MCP stdio: tools/call"
    donor.harness -> donor.proxy "model API over the proxy only"
    donor.proxy -> provider "HTTPS"
    donor.mcp -> project.sshd "one SSH connection, key K, host key pinned; swarma-rb/1 frames"
    project.sshd -> project.workplace "exec / file ops as the workplace user"
    project.sshd -> project.bridge "mailbox.read / mailbox.post / mailbox.notify"
    operator -> project.joinPoint "confirm fingerprint; release package"
    operator -> project.registry "pin K; root-signed admission; grants"
    project.bridge -> project.registry "verify signatures, grants, revocation"
  }

  views {
    container donor "DonorContainers" "Donor machine: the harness user, the lockdown harness, the local remote-tools server, the keyring, the proxy and the kernel boundary" {
      include *
      autolayout lr
    }
    container project "ProjectSideContainers" "Our host: join point, sshd with the forced executor, the workplace, the bridge, the registry and DNS" {
      include *
      autolayout lr
    }
  }
}
