// Revision 2026-10-13: R-TRANSFER, zero egress, qualified host admission and separate public entry host; no runtime evidence.
// C4 (Structurizr DSL) fragment for CIP-0009 (revision 7, R-WORKPLACE cycle-2 findings 2026-10-12: B boundary shown; A/C differences in source notes; B disabled until separate provisioner contract exists): the donor machine and the bridge to our host.
// Defining sections: ../CIP-0009-donor-side-deployment-and-bridge.md#recommendation (D0-D12); ../../protocol/remote-worker.md#publication-status.
// Phase: Draft donor target after one-host slice 0 + project helper v1/workplace qualification; no current deployment/qualification claim.
// Refusal/recovery: unknown tuple/posture/generation or failed trust refuses; failed B provisioning reverses journal; channel loss pauses/catches up without repeating effects.
// State owners: donor bridge role owns keys/config/audit/cursors/budgets; harness role owns managed home/scratch; join point owns queue/challenges/tombstones/packages; project registry owns public pins/grants/revocations, project bridge owns mailbox/carrier, service-principal swarma-rb-exec outside workplace UID owns policy/caps/execution leases, durable binding-generation identity/digest claims and admission floors; ten-minute output cache is separate. Claims are discarded only after identities are permanently inadmissible; recovery reconciles before admission.
// Separate explicit operator home retention states confidentiality is not guaranteed; git/accepted outputs retain their own policy.
// Exact service UIDs, state files/retention and recovery record schemas unspecified in CIP-0009 D4/D5/D7/D9.
// Style follows relux-works/swarm-platform-architecture diagrams/c4 (hierarchical identifiers, one container per process).
// Variant B: two OS identities on the donor (untrusted harness, trusted bridge); the relay holds no keys and no network;
// A/C: donor UID user service; A qualified lockdown only, no OS boundary or proxy; C sandbox without UID split.
// A/C keys: qualified Secure Enclave P-256 signing/SSH on supported Macs, files elsewhere; B Ed25519 0600, no Keychain.
// Invitation/transcript/package, join API/error, channel/backend and donor provisioner formats: pending protocol/remote-worker.md.
// the bridge signs outbound envelopes with the worker's key; the harness reaches only the relay socket and the provider proxy.
workspace "Remote worker on a donor machine" "Draft donor target after slice 0 + project helper v1/workplace qualification: CIP-0009 Recommendation D0-D12; B disabled pending separate provisioner; A/C substitutions in source notes and PlantUML variant view" {
  !identifiers hierarchical

  model {
    donorOwner = person "Donor (the machine's owner)" "Owns the donor machine; runs init, status, stop, leave, purge"
    operator = person "Project operator" "Reviews enrolment, issues admission, grants and packages; no voice comparison"

    donor = softwareSystem "Donor machine" "A machine we do not own, lending a harness subscription" {
      curator = container "curator (donor install)" "Go CLI" "human donor UID for init/leave/purge; bridge role for run/status/stop; consumes the composed lockdown plan; writes the locked machine config (bridge-owned)"
      helper = container "Separate donor provisioner (B only; pending)" "Separate binary and privileges; not swarma-user-manager" "Short spec, closed schema, rules and removal pending; B disabled; allocated identifiers, journal/rollback required"
      harnessUser = container "Harness identity worker-<project>" "OS user, home 0700, quotas, Seatbelt/Landlock read boundary" "the UNTRUSTED side: managed home and scratch dir only"
      bridgeUser = container "Bridge identity swarma-bridge-<project>" "OS user, system service (launchd daemon / systemd)" "the TRUSTED side: keys, locked config, audit, lifecycle state"
      supervisor = container "Bridge service: supervisor" "curator remote-worker run (bridge identity)" "launches the harness as the harness identity; admitted mailbox items become turns via the session-input adapter; budgets, rate, lifetime (trusted-side counters)"
      bridgeCore = container "Bridge service: SSH client + signer + admission" "swarma-bridge (bridge identity)" "one SSH connection to our host (K_ssh + short user certificate; host CA/name/validity/KRL checked every reconnect); signs outbound envelopes with K_sig; admits inbound items; durable cursors; audit"
      keys = container "Key store" "0600 files owned by the bridge identity (no Keychain; non-exportable later only without Keychain)" "K_sig (Ed25519), K_enc (X25519), K_ssh (Ed25519); unreadable by the harness identity"
      web = container "Optional donor swarma-web" "Own B identity / C sandbox; never harness/bridge" "Trusted-circle per-identity opt-in, donor key stays donor-side; search-provider API endpoints only; pending qualification"
      harness = container "Harness" "Claude Code / Codex / Muse (harness identity, lockdown plan)" "no local tool offered to the model; only the relay; provider credential injected per launch"
      relay = container "swarma-remote-tools" "local stdio MCP relay (harness identity)" "no keys, no network; forwards tools/call to the bridge socket; effective tool set = policy intersection"
      socket = container "Relay socket" "Unix socket, peer credentials checked" "only the harness identity of this project may connect"
      proxy = container "Provider proxy" "bridge identity or system service" "the harness identity's only network exit: provider API hosts of the qualified tuple"
      egress = container "Kernel egress + sandbox" "pf/nftables by UID, Seatbelt/systemd+Landlock" "harness UID -> proxy only; bridge UID -> SSH host and join point only; reads confined"
    }

    entry = softwareSystem "Separate public entry host" "R-SHARED: no untrusted placements beside shared ingress" {
      joinPoint = container "Join point (service UID unspecified in D9)" "HTTPS, three verbs: challenge, cert, collect" "atomic invitation consumption, tombstones, rate limits; never commands"
    }
    project = softwareSystem "Project host" "R-SHARED: platform services only beside untrusted work" {
      sshd = container "sshd + relay-only fixed login shell" "Root-controlled Match, TrustedUserCAKeys + KRL + workplace principal; protected absolute relay stub" "Root-owned stub accepts only sshd forced-command invocation; no user startup files; relays to service socket, no policy or tool authority"
      executor = container "swarma-rb-exec" "Service principal outside workplace UID" "Kernel peer UID and active generation authentication; service-owned policy/caps/leases/claims/floors/audit; swarma-rb/1 and swarma-workplace-exec/1 unpublished, owner/formats unresolved"
      dispatcher = container "Dispatcher + root launcher/user manager" "Existing journaled start/receipt/exec.stop path" "Workplace class activates only with helper v1 fw.apply + published applied state, including loopback; v0 refuses all variants including read-only; physical starts dispatcher-owned"
      workplace = container "Remote workplace jobs or runner" "Untrusted workplace UID; private home; standalone Git across isolated accounts" "OS write boundary is UID writable set; task write scope plan/import bound; qualified zero egress, denied loopback, no proxy destination; R-EXEC profile; per-job/runner concurrency and stop blast radius unpublished; process groups alone prove no absence; controls/claims/audit stay service-owned"
      bridge = container "Bridge (M3; service UID unspecified in D5)" "broker, mailbox, trust gate" "admits messages; verifies the worker's signature; carries bytes unchanged under a distinct carrier account"
      registry = container "Trust registry + key keeper (service UID unspecified in D4/D12)" "pins K_sig, K_enc, K_ssh; grants; root-signed admission and revocations" "operator certificates chained to the root; user CA private key in project keeper/hardware token, renewal only for authenticated active workplace principal"
      dns = container "DNS zone (DNSSEC default)" "TXT _swarma, TXT _swarma-ssh-ca, TLSA" "Per-environment root/host-CA/TLS trust; validated in client; declared no-DNSSEC invitation uses pins, never fallback on failure"
    }

    board = softwareSystem "Board change-request machinery" "R-TRANSFER import on B to signed exact C; independent trusted review, signed rework letters from C, signed fast-forward K1/K3"
    runners = softwareSystem "R-VERIFY runners on another machine" "Secret-free isolated ephemeral runners; controlled dependency egress; results as board data"
    search = softwareSystem "Search-provider API only" "Opt-in donor-side search; no arbitrary fetch; no project access to donor key"
    provider = softwareSystem "Model provider API" "Anthropic / OpenAI / Meta" "External"

    donorOwner -> donor.curator "init <invitation-file> (no secret in argv), status, stop, leave, purge"
    donor.curator -> donor.helper "B future provisioning/removal boundary (separate spec pending; not user-manager operations)"
    donor.curator -> donor.keys "generate K_sig, K_enc, K_ssh (bridge identity); decrypt the package"
    donor.curator -> project.dns "DNSSEC branch only: local validation, DoH transport; failed reads/mismatch refuse; pins must agree"
    donor.curator -> entry.joinPoint "challenge; cert (signed swarma-bridge join/1 transcript + code when invited); collect (HTTPS: Web PKI + DNSSEC/TLSA or declared invitation pins; schemas pending)"
    donor.supervisor -> donor.harness "validate tuple/current generation/binding; refuse unknown or changed input; launch as harness identity under composed plan; next admitted turn"
    donor.harness -> donor.relay "MCP stdio: tools/call"
    donor.relay -> donor.socket "forward (peer credentials checked)"
    donor.socket -> donor.bridgeCore "authenticated local RPC"
    donor.harness -> donor.proxy "model API over the proxy only"
    donor.proxy -> provider "HTTPS"
    donor.web -> search "Optional search-provider API only; donor key stays here, no channel/package"
    donor.web -> donor.harness "Opt-in tool results to donor model only; separate identity/profile"
    donor.bridgeCore -> donor.keys "sign envelopes with K_sig; SSH with K_ssh"
    donor.bridgeCore -> project.sshd "one SSH connection; trust failure refuses; channel loss pauses new turns; reconnect reconciles same durable claim and original admission window; retained result or pending/unknown_result, never automatic re-execution"
    project.sshd -> project.executor "relay only; service authenticates kernel peer UID and active generation"
    project.executor -> project.dispatcher "authorized execution start/stop; service claims identity/digest before effects; unknown claims never replay"
    project.dispatcher -> project.workplace "root launcher/start receipt and journaled exec.stop; R-TRANSFER materialize/export under child UID; account-wide absence/fence before export, export recorded or operator waiver before deletion"
    project.dispatcher -> board "Bounded workspace result as resource to original caller; no worker push/MR; worker Git history unused"
    board -> runners "All heavy work and candidate execution; tester orchestrates/reads results only"
    project.executor -> project.bridge "mailbox.read / mailbox.post (worker-signed bytes) / mailbox.notify (advisory)"
    operator -> entry.joinPoint "check the enrolment against signed card, invitation binding or open application; release package"
    operator -> project.registry "pin keys; root-signed admission; grants"
    project.bridge -> project.registry "verify signatures, grants, revocation, freshness"
  }

  // Default no web/search/fetch: donor loop provider endpoints + our host, plan alone disables provider search inside API.
  // Read-only task resources beside workspace, digests in plan; worker requests more by letter, never fetches.
  // R-UNTRUSTED: recorded admission class, no subscription binding/lease; circle enables donor opt-ins only.
  // R-CEILINGS host matrix + R-EXEC + R-RANGE-DENY precedence + R-SOCKETS qualify every placement; no OS-name ban.
  // R-STANDING workplace loop donor-side only; trusted standing plan surfaces digest-checked before launch/restart/resume.
  // R-WATCH one-account freeze/journaled stop and phone alerts; R-ALLSTOP manual hold/range deny/all stops/broker freeze/host snapshots.
  // Existing donor channel-down/project suspended; unknown keeps admission closed; explicit recovery; delivered tokens keep vendor lifetime.
  views {
    container donor "DonorContainers" "Draft target, variant B (disabled until provisioner spec/qualification): the untrusted harness identity (harness, relay), the trusted bridge identity (supervisor, SSH client, signer, keys, audit), the proxy and the kernel boundary" {
      include *
      autolayout lr
    }
    container project "ProjectSideContainers" "Draft project target: join point, root sshd/relay shell, service-principal executor, dispatcher/root execution path, the workplace jobs, the bridge, the registry and DNS" {
      include *
      autolayout lr
    }
  }
}
