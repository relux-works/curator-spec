# CIP-0037 (Draft r3): Curator Credential Broker -- Unified Tool and MCP Credential Mediation (MVP)

- **Status:** Draft (r3; reserved in `curator-spec` PR #233 / `S0`)
- **Owner:** Ivan Oparin (decision); author: Curator Architect
- **Created:** 2026-11-25
- **Depends on:**
  - `curator-spec` PR #233 (`S0`: coordinated CIP-0034..0038 index and `platform-contract-disposition.md` reservation)
  - CIP-0011 (agent OS user isolation; required for strong cross-UID isolation tier)
  - CIP-0025 (execution isolation contract, boundary receipts; required for microVM tier)
- **Related:**
  - CIP-0006 (`profile_settings`, operator-only authority threat model)
  - CIP-0035 (session surface projection)
  - CIP-0036 (managed GUI hosts and signed `Curator.app` helper)
  - CIP-0038 (separate companion draft: isolated Browser SSO authentication over `--remote-debugging-pipe`)
  - Environments sections 2.2, 5.8, 10.3 (`passable_env_names` / S4), 11 (umbrella subcommand discovery)
  - `swarma-credential-broker` `spec/secret-free-mode.md` and `spec/secret-free-gateway.md`
  - `swarma-keyvault` (`pkg/kekclient`, optional macOS Secure Enclave KEK backing)
  - SealLink `v1.0.0` `SPEC-06` and `SPEC-07` (post-`rc1` follow-up Plane 1 integration)
- **Affects:**
  - `curator-spec`: new protocol document `protocol/tool-auth-mediation.md`, `auth-adapter-v1` schema, `curator-auth-adapter/1` plugin protocol, `environments` sections 2.2 and 10.3, machine configuration (`auth`), manager-home top-level directory registry (`~/.curator/auth-store/`), CLI (`curator auth ...` via section 11 umbrella discovery)
  - `curator`: profile closure auth-requirement discovery (`requires.auth` / `auth_service`), operator-owned `auth` origins/accounts/bindings with `--confirm-auth-delta`, `env status` auth readiness rows
  - `curator-credential-broker` (new Curator plugin repository): two-process host architecture (`curator-auth-custody` + `curator-auth-gateway`), `curator-auth` CLI, `curator-mcp-bridge` (stdio-to-HTTP over Unix socket), `curator-mcp-exec` (Mode C shim), envelope-encrypted OS `SecretStore`, Go client SDK (`pkg/authclient`)
  - `curator-agent-launcher`: launcher-scoped session open/close for `curator-run` and `curator-app`, and `Curator.app` GUI integration

---

## 1. Summary

Agents rely on dozens of CLI utilities (issue trackers, Git forges, wikis, error trackers, test/deploy/observability tools, WebDAV drives) and MCP servers (`stdio` and remote `http`). Storing tokens in shell environments or ad-hoc per-CLI files causes four systemic failures: secret leakage into agent context/files/argv, inability to run two concurrent profiles against the same service with different accounts, incompatibility with GUI Dock launches (`CIP-0036`) and isolated OS users/microVMs (`CIP-0011`/`CIP-0025`), and fragmented login/status management.

This CIP specifies **`curator-credential-broker`** -- a dedicated **Curator plugin** (`environments` section 11 umbrella discovery -> `curator auth ...`) implementing a **host-side, zero-TCP, two-process credential mediation architecture** for tools and MCP servers:

1. **Custody & Lifecycle Process (`curator-auth-custody`):** Reachable ONLY on a host-only control Unix socket (`0600`). Holds the envelope-encryption KEK in the OS native store (macOS Keychain / Linux Secret Service / Windows Credential Manager), owns `0600` AEAD-encrypted credential blobs under `~/.curator/auth-store/`, executes enrollment (`curator auth login`), refresh rotation, and token exchange, and mints short-lived session material to the gateway. Never handles untrusted agent HTTP requests.
2. **Request-Adapter Gateway Process (`curator-auth-gateway`):** Reachable ONLY on a local data Unix socket (or microVM `vsock` -- **zero TCP listeners**). Holds ONLY active session mappings and short-lived operational credentials leased from `curator-auth-custody`. Enforces operator-pinned origins, path prefixes, HTTP/WebDAV methods, DNS-pinned IPv4/IPv6 SSRF guards, and process-ancestry checks before injecting credentials on outbound HTTPS.
3. **Agent Sandbox (Plane 3):** CLIs and MCPs receive ONLY `CURATOR_AUTH_SOCKET` and an opaque short-lived `CURATOR_AUTH_SESSION`. Unmodified remote HTTP MCP clients connect through a local stdio-to-HTTP bridge (`curator-mcp-bridge`) speaking over the Unix socket -- eliminating loopback TCP entirely.

### 1.1 Architectural Separation and Linux Station Coexistence

This design mirrors the custody-versus-gateway separation established in `swarma-credential-broker`'s `spec/secret-free-mode.md` and `spec/secret-free-gateway.md`, while keeping tool/MCP mediation in a separate Curator plugin (`relux-works/curator-credential-broker`):

- **Why a separate repository:** `swarma-credential-broker` ("Merovingian") is a Linux-only daemon narrowly scoped to model-provider subscription credentials (`CIP-0011`). Its specification explicitly excludes request adapters and HTTP forwarding. `curator-credential-broker` serves macOS, Linux, and Windows desktops immediately and follows Curator's section 11 plugin model.
- **Explicit coexistence on Linux stations (`CIP-0011`/`CIP-0025`):**
  - `swarma-credential-broker` exclusively holds **model-provider subscription credentials** (Claude/Codex harness accounts).
  - `curator-credential-broker` exclusively holds **tool and MCP service credentials** (CLIs and MCP servers).
  - **Neither broker proxies for, reads from, or delegates to the other.** Both independently verify `CIP-0025` protected boundary receipts on isolated executions.

### 1.2 Scope Split (Focused MVP)

To keep delivery incremental and reviewable:
- **In scope for CIP-0037 (MVP):** two-process custody + gateway (`curator-auth-custody` + `curator-auth-gateway`), envelope-encrypted OS `SecretStore`, Mode A (`bearer`, `header`, `basic`, `token_exchange`, `refresh_token`, `oauth2_pkce`, `oauth2_device`, `mtls`, WebDAV methods), Mode B (narrowed ephemeral mint), Mode C (`curator-mcp-exec`), `curator-mcp-bridge` (stdio-to-HTTP over Unix socket), `curator auth` CLI, `curator` closure auto-discovery and `--confirm-auth-delta` origin pinning, launcher session wiring, and one Go client SDK (`pkg/authclient`).
- **Split to CIP-0038:** `browser_sso` (isolated Chrome over `--remote-debugging-pipe`, shared IdP SSO, cookie/CSRF/SPA capture, DBSC and IdP policy boundaries).
- **Deferred to post-`SealLink v1.0.0-rc1` follow-up:** SealLink Plane 1 (`seallink-grant/1` / `seallink-invocation/1` / `seallink-session-open/1` / `seallink-receipt/1`) and Mode D depth-2 re-delegation. v1 retains a clean authorization-gate seam so SealLink plugs in without rewriting CLIs, adapters, or sockets.

---

## 2. Honest Security Model and Isolation Tiers

This CIP explicitly distinguishes two security tiers and makes **no false isolation claims** on a same-UID desktop:

| Tier | Environment | What Is Guaranteed | What Is NOT Guaranteed |
|---|---|---|---|
| **Tier 1: Same-User Workstation** (single OS user: laptop CLI & `CIP-0036` GUI) | Operator, harness, CLIs, and broker run under one OS UID | Zero long-lived secrets on disk in plaintext, in configs, in `argv`, in launch fragments, or in LLM context/transcripts. Mode A prevents accidental leakage, enforces operator-pinned origins/paths/methods, and enables concurrent multi-profile workflows (`work` vs `oss`). Process-ancestry checks reject casual cross-profile session replay, and `curator-auth-custody` restricts secret-returning Control Socket operations (gateway credential leases, `login`) by peer code identity (macOS `audit_token_t` + designated requirement; Linux `/proc/<pid>/exe` identity) to further narrow casual same-UID access. | **Does NOT defend against a hostile same-UID process.** On one OS user, `ps -E` / `KERN_PROCARGS2` (macOS) and `/proc/<pid>/environ` (Linux) allow any same-UID process to read `CURATOR_AUTH_SESSION` or Mode C child environments of an admitted tree. Additionally, an unlocked Linux Secret Service (`org.freedesktop.secrets`) collection is readable by any same-UID D-Bus client without a prompt, so on Linux Tier 1 the 32B KEK is NOT protected against a hostile same-UID process (unlike macOS Keychain ACL). Mode C on same-user is strictly **operational convenience** (zero-disk Dock/CLI launch), not isolation. |
| **Tier 2: Isolated Execution** (`CIP-0011` dedicated agent OS user OR `CIP-0025` microVM) | Custody and gateway run outside the agent UID / outside the guest VM; peer identity is kernel-authenticated (`SO_PEERCRED` / `LOCAL_PEERCRED` or host-mapped `vsock` CID) | **True OS/VM boundary isolation:** compromised agents, `Bash`, and sibling profiles cannot read custody secrets, OS Keychain, refresh tokens, or another profile's `CURATOR_AUTH_SESSION`. Mode C is **refused by default** under `hardened` without an explicit per-server operator waiver. | Compromise of the host root or of the gateway process itself (gateway compromise is bounded to currently leased short-lived material, never refresh tokens or `SecretStore` KEK). |

---

## 3. Architecture: Two Processes, Zero TCP, and Delivery Modes

### 3.1 Two-Process Host Split

```text
+-----------------------------------------------------------------------------+
| HOST CONTROL PLANE (operator UID / dedicated custody UID)                   |
|                                                                             |
|  curator auth CLI / Curator.app (interactive login, bind, status, revoke)   |
|  curator-run / curator-app      (session open/close only)                   |
|         |                                                                   |
|         v  Control Unix Socket (0600, per-user runtime dir, lstat-verified) |
|  +-----------------------------------------------------------------------+  |
|  | PROCESS 1: curator-auth-custody (Custody & Lifecycle)                 |  |
|  | - Owns 32B KEK in OS SecretStore (Developer ID signed binary!)        |  |
|  | - Owns 0600 AEAD blobs in ~/.curator/auth-store/<account_id>.enc      |  |
|  | - Owns OAuth2 PKCE/Device enrollment, refresh_token, token_exchange   |  |
|  | - Single-flight + per-account flock on all refreshes                  |  |
|  | - Never accepts agent HTTP proxy traffic                              |  |
|  +-----------------------------------+-----------------------------------+  |
|                                      | Internal Custody Unix Socket (0600)  |
|                                      | (leases short-lived access material) |
|                                      v                                      |
|  +-----------------------------------------------------------------------+  |
|  | PROCESS 2: curator-auth-gateway (Request-Adapter Gateway)             |  |
|  | - Holds ONLY active session table + short-lived leased headers/tokens |  |
|  | - Enforces peer UID + process-ancestry (Tier 1) or SO_PEERCRED /      |  |
|  |   vsock CID + CIP-0025 boundary receipt (Tier 2)                      |  |
|  | - Enforces operator-pinned origins, path prefixes, HTTP/WebDAV verbs  |  |
|  | - DNS-pinned IPv4/IPv6 SSRF guard, redirect block, host CA/proxy      |  |
|  | - Append-only hash-chained audit log (zero secrets / query tokens)    |  |
|  +-----------------------------------+-----------------------------------+  |
+--------------------------------------|--------------------------------------+
                                       | Data Unix Socket (0600) or vsock
                                       | (ZERO TCP listening sockets!)
                                       v
+-----------------------------------------------------------------------------+
| AGENT SANDBOX (Tier 1 same-user OR Tier 2 OS-user / microVM)                |
| - Harness (`claude`, `codex`, `agy`, `Claude Desktop`)                      |
| - CLIs using Go SDK `pkg/authclient` -> CURATOR_AUTH_SOCKET                 |
| - Remote HTTP MCPs via `curator-mcp-bridge` (stdio <-> HTTP over Unix sock) |
| - Legacy stdio MCPs via `curator-mcp-exec` (Mode C; refused in Tier 2       |
|   hardened unless explicitly waived)                                        |
+-----------------------------------------------------------------------------+
```

### 3.2 Transport Rules (Zero TCP Normative Contract)

- **Unix domain sockets and `vsock` are the ONLY normative transports.** No TCP listener (`127.0.0.1:<port>` or otherwise) is opened by `curator-auth-custody` or `curator-auth-gateway`.
- **Unmodified remote HTTP MCP clients:** Because Claude Code and Claude Desktop do not dial Unix sockets directly for `transport: "http"` MCP servers, `curator-credential-broker` ships **`curator-mcp-bridge`** -- a lightweight `stdio` MCP adapter launched as the MCP server command (`command: "curator-mcp-bridge"`, `args: ["--service", "<service_id>"]`). It speaks standard MCP JSON-RPC on stdin/stdout to the harness and forwards Streamable HTTP/SSE requests to `curator-auth-gateway` strictly over the Unix socket / `vsock`! Zero TCP ports, zero CORS or DNS-rebinding exposure, and full kernel peer authentication!
- **Per-user runtime socket directory (no `/tmp` squatting, `<= 104B` macOS `sun_path`):**
  - macOS: `confstr(_CS_DARWIN_USER_TEMP_DIR)` + `/ca/` (e.g., `/var/folders/.../T/ca/d.sock`, owned by UID, `0700`, verified `< 104` bytes).
  - Linux: `$XDG_RUNTIME_DIR/curator-auth/` (fail closed if `XDG_RUNTIME_DIR` is unset/untrusted; never fall back to world-writable `/tmp`).
  - Windows: Named Pipe (`\\.\pipe\curator-auth-<sid>-data` with explicit owner-only DACL).
  - Before `bind`, the daemon MUST `lstat` every created directory component, verify `uid == geteuid()`, `mode & 0777 == 0700`, and non-symlink, refusing with `auth_socket_dir_untrusted` on any mismatch.

### 3.3 Delivery Modes

| Mode | Tier 1 (Same-User) | Tier 2 (OS-User / microVM) | Semantics |
|---|---|---|---|
| **Mode A: `http-gateway`** (Default) | Zero secrets on disk/context; origin/path/method policy; process-ancestry bound | Full OS/VM secret isolation; zero outbound internet or CA needed in guest | Gateway proxies `/v1/proxy/<service>/<path>` over Unix socket / `vsock`, injecting short-lived auth headers or host mTLS certs. |
| **Mode B: `ephemeral-token`** | Convenience / short TTL only (not defense against hostile same-UID) | Short-lived narrowed token only (refresh token/master key never enters VM) | `/v1/mint/<service>` MUST require declared audience and scope narrowing (`mint_scopes[]`, max TTL `<= 3600s`); token can still be exfiltrated within its TTL if sandbox is compromised. |
| **Mode C: `scoped-env`** (`curator-mcp-exec`) | Operational convenience for legacy `stdio` MCPs (including Dock launches) without disk secrets; NOT isolation against same-UID env reads | **Refused by default** (`auth_scoped_env_refused`) under `hardened` unless explicitly waived per server in machine config | `curator-mcp-exec --service <S> -- <cmd>` fetches ONLY declared `scoped_env_names` immediately before `execve` of that child. |
| **Mode D: `seallink-direct`** *(post-rc1 follow-up)* | Reserved seam | Reserved seam | Depth-2 child `seallink-grant/1` (`recipient.mode = "key"`) minted to an ephemeral sandbox keypair. |

---

## 4. Authority Boundary: Operator-Owned Origins vs Package Adapters

**Threat model invariant (aligned with CIP-0006):** A git package MUST NEVER acquire authority to redirect the operator's credentials to an arbitrary host.

### 4.1 Strict Separation of Origin Authority

1. **Operator machine config (`~/.curator/config.json`) is the SOLE authority for origins:**
   - Every account record declares exact operator-owned `base_url` (`https://<host>[:<port>]`, no userinfo/query/fragment) and, for OIDC/OAuth, exact `idp.issuer` and `idp.token_origin`.
2. **Package `auth-adapter.json` (schema v1) MAY contain ONLY relative paths and closed template variables:**
   - Every path (`allowed_path_prefixes[]`, `exchange_path`, `refresh_path`, `auth_path`, `token_path`, `status_probe.path`) MUST begin with `/` and MUST NOT contain a scheme (`https://`), host, `//`, or `..`.
   - Closed template variable set (strictly account-derived):
     - `${BASE_URL}` (resolved from operator account `base_url`; permitted only at URL prefix position in display/probe construction, never overridden by package);
     - `${IDP_ISSUER}` (resolved from operator IdP `issuer`);
     - `${META.<field>}` (non-secret account metadata field; strictly URL path-segment escaped; FORBIDDEN in scheme/host/port positions).
   - Any absolute foreign URL or unknown template variable in a package `auth-adapter.json` refuses immediately at validation with `auth_adapter_origin_forbidden`.
3. **Explicit Operator Confirmation on Bind and Widening (`--confirm-auth-delta`):**
   - Binding an adapter to an account (`curator auth bind`) prints the exact pinned origin (`base_url`), `allowed_path_prefixes[]`, `allowed_methods[]`, and `delivery` modes and requires explicit confirmation (`--confirm-auth-delta`, analogous to `--confirm-system-delta` in `profile install/update`).
   - Any subsequent `profile update` where a package's `auth-adapter.json` widens `allowed_path_prefixes`, `allowed_methods`, `scoped_env_names`, or `delivery` refuses until the operator re-confirms with `--confirm-auth-delta`!

### 4.2 Closed `auth-adapter.json` Schema (v1 MVP)

```json
{
  "schema_version": 1,
  "service": "issue-tracker",
  "display_name": "Issue Tracker API",
  "allowed_path_prefixes": ["/api/issues/", "/api/users/"],
  "allowed_methods": ["GET", "HEAD", "POST"],
  "delivery": ["http-gateway"],
  "non_secret_meta_fields": ["org", "project", "namespace", "user_id"],
  "auth_methods": [
    {
      "id": "bearer",
      "kind": "bearer",
      "jwt_exp_check": false,
      "token_regex": "^[A-Za-z0-9._:-]{16,512}$"
    },
    {
      "id": "basic",
      "kind": "basic"
    },
    {
      "id": "uaa-exchange",
      "kind": "token_exchange",
      "exchange_path": "/api/uaa/oauth/token",
      "body_encoding": "form",
      "exchange_fields": {
        "grant_type": "apitoken",
        "scope": "openid",
        "token": "${SECRET_TOKEN}"
      },
      "token_json_field": "access_token",
      "expires_in_json_field": "expires_in"
    }
  ],
  "status_probe": {
    "method": "GET",
    "path": "/api/users/me",
    "identity_json_path": "login",
    "expiry_json_path": null
  }
}
```

**Built-in `auth_methods[].kind` values in CIP-0037 MVP:**
1. `bearer` (`Authorization: Bearer <secret>`, optional offline `jwt_exp_check`)
2. `header` (`<header>: <prefix><secret>`, e.g., `PRIVATE-TOKEN`, `X-API-Key`, `Authorization: OAuth ...`)
3. `basic` (`Authorization: Basic base64(user:secret)` + `non_secret_meta_fields`)
4. `token_exchange` (master API token exchanged on `curator-auth-custody` for cached short-lived JWT; transparent single retry on `401`)
5. `refresh_token` (lazy refresh `< 60s` before expiry or on `401` under single-flight + `flock`; atomic rotated refresh persistence in `curator-auth-custody`)
6. `oauth2_pkce` / `oauth2_device` (Authorization Code + PKCE S256 via ephemeral loopback callback during interactive `curator auth login` on host, or RFC 8628 Device Flow for headless stations; relative `auth_path`/`token_path` resolved against operator-pinned `base_url` or `idp.issuer`)
7. `mtls` (host-side TLS client cert + key managed by `curator-auth-custody`)

*(Note: `browser_sso` is specified separately in companion draft `CIP-0038` using `--remote-debugging-pipe`.)*

### 4.3 Gateway Security Invariants

1. **Path & Method Enforcement:** Clean path (`path.Clean`, rejecting raw `%2e`, `%2f`, `\`), match `allowed_path_prefixes[]` and `allowed_methods[]` (supporting WebDAV `PROPFIND`, `MKCOL`, `MOVE`, `COPY`, `SEARCH` only when explicitly declared and confirmed).
2. **Header Stripping:** Strip client-supplied `Authorization`, `Cookie`, `PRIVATE-TOKEN`, `X-API-Key`, `Host`, and `X-Curator-Session` before injecting gateway credentials.
3. **DNS-Pinned IPv4/IPv6 SSRF Protection:** Resolve target host once inside a custom `DialContext`, reject ALL IPv4 AND IPv6 loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`, `fe80::/10`), multicast, unspecified (`0.0.0.0`, `::`), and RFC1918/ULA (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`) addresses unless the operator explicitly opted into `allow_private_network: true` on that exact account in machine config, and **dial the pinned IP directly** (preventing DNS rebinding).
4. **No Automatic Redirects:** `CheckRedirect` always returns `http.ErrUseLastResponse`; any `3xx` `Location` outside the pinned origin refuses with `403 cross_origin_redirect_blocked` (and any future same-origin redirect re-checks SSRF and path prefixes).
5. **Single-Flight + Cross-Process Refresh Lock (`flock`):** All refreshes run in `curator-auth-custody` under an in-process single-flight gate AND a per-`account_id` `flock`, re-reading the encrypted store before hitting `/token` so concurrent calls never race rotating refresh tokens.
6. **Session-Origin Interactivity Rule (NEVER TTY-Based):** Because some harnesses run tool commands inside a PTY (e.g., unified exec), interactivity MUST NOT be inferred from `isatty()`. **Every request arriving on the Data Socket (carrying an agent session) is strictly non-interactive**: if re-authentication is needed, the gateway immediately returns HTTP `401` / CLI exit code `3` (`auth_interactive_login_required`) naming the exact `curator auth login` command. ONLY explicit operator commands on the host-only Control Socket (or `Curator.app`) may initiate interactive login.
7. **Redacted Types & Append-Only Hash-Chained Audit Log:** All secret structs override `String()`, `GoString()`, `MarshalJSON()`, and `Format()` to `"<redacted>"`. The gateway writes an append-only, hash-chained JSONL audit log (`prev_sha256` per record) containing `(ts, session_id, profile, service, method, matched_prefix, status, decision, reason)` -- never secret values, never query strings or full URLs containing tokens -- with bounded size/day rotation.

### 4.4 Executable Adapter Plugin Protocol (`curator-auth-adapter/1`)

For services requiring custom auth (HMAC, Kerberos/SPNEGO), a host-only executable plugin invoked solely by `curator-auth-custody` (with explicit `--confirm-auth-delta` admission) speaks newline-delimited canonical JSON over stdin/stdout with four closed verbs: `describe`, `status`, `login`, `authorize_request`.

---

## 5. Envelope-Encrypted `SecretStore`, Signing, Auto-Discovery, and Session Lifetimes

### 5.1 Envelope Encryption (Solving Windows 2560B and Keychain Limits)

Windows Credential Manager enforces `CRED_MAX_CREDENTIAL_BLOB_SIZE = 2560` bytes, and macOS Keychain has practical item size ceilings (previously encountered by multi-token OAuth payloads). Therefore `curator-auth-custody` uses **envelope encryption** across all platforms:

- **OS Store holds ONLY a 32-byte KEK** (`works.relux.curator.auth.kek` / `v1`):
  - macOS: Security.framework Keychain (`kSecAttrAccessibleWhenUnlockedThisDeviceOnly`; optional `swarma-keyvault` `pkg/kekclient` Secure Enclave KEK on managed stations).
  - Linux: D-Bus Secret Service (`org.freedesktop.secrets`) or operator-unlocked encrypted keyfile on headless stations.
  - Windows: Windows Credential Manager (`CredReadW`/`CredWriteW`, 32 bytes -- always well under 2560 bytes).
- **Encrypted payload files live in `~/.curator/auth-store/<account_id>.enc`** (`0600` regular files, AEAD AES-256-GCM with AAD binding `(schema_version, account_id, service)`):
  - Bounded maximum plaintext size (`<= 256 KiB` checked before write; oversized payloads refuse with `auth_secret_too_large`).
  - Registered as a new top-level manager-home directory explicitly excluded from `contextpkg`, `CIP-0014` snapshots, and unencrypted bulk backups (and `tmutil addexclusion` on macOS).
- **Pre-login availability check:** Before prompting or opening OAuth browser login, `curator auth login` calls `SecretStore.ProbeWritable()` and refuses early with `auth_store_unavailable` if locked/inaccessible.
- **Code signing for macOS Keychain ACL stability (mandatory in A2):** `curator-auth-custody` MUST ship with a stable **Developer ID designated requirement** (same Relux Works release signing pipeline as `Curator.app`) so binary updates do not trigger macOS Keychain ACL prompt storms.
- **Optional external providers (`1Password`, `Vault`):** Deferred to `A2b`, **off by default**, enabled strictly by explicit operator machine-config opt-in (honoring host policies where agent lanes must never access an operator's 1Password).

### 5.2 Auto-Discovery and Multi-Profile Account Bindings

- Packages declare `requires.auth: [{ "service": "<id>", "adapter": "<relpath-or-pkg>", "optional": false }]` (and `agent-mcp.json` v2 adds optional `auth_service: "<id>"`).
- Curator deterministically computes `RequiredAuthServices(profile)` from the profile lock closure so `curator auth status`, `curator env status`, and `Curator.app` automatically discover every service across every profile.
- Machine config `~/.curator/config.json` stores non-secret `auth.idps`, `auth.accounts` (with operator-owned `base_url` and `meta`), and `auth.profile_bindings.<profile>.<service> = <account_id>` -- enabling the same service to use distinct accounts across concurrent managed homes (`work` vs `oss`) or intentionally share one account.

### 5.3 Session Lifetimes, Process-Ancestry Binding, and GUI Granularity

- **Independent of unlanded `home-leases` (`curator #208`):**
  - **CLI `curator run`** (native unhosted launches take no home lease per `home-leases.md` L6): `curator-run` opens a session bound to `(profile, env_id, root_pid, root_start_time, boot_id, allowed_services[], max_ttl <= 4h)` and closes it on child exit.
  - **GUI `curator app` (`CIP-0036`):** `curator-app` opens a session bound to the GUI host main process incarnation (`CIP-0036` observer) + `max_ttl` (renewable by the host-side launcher while the instance lives, independently expiring on TTL). **Explicit granularity:** in GUI hosts, `CURATOR_AUTH_SESSION` is scoped **per `(profile, host_instance)`** and shared across all sessions and MCP processes spawned by that instance (not per `execution_id`).
- **Process-ancestry binding (Tier 1 narrowing):** On every Data Socket request, `curator-auth-gateway` reads `LOCAL_PEERPID` / `SO_PEERCRED` PID and walks kernel parent PIDs up to the session's registered `(root_pid, root_start_time, boot_id)`. Requests from outside that process tree refuse with `auth_peer_ancestry_mismatch`.
- **Tier 2 (`CIP-0011` / `CIP-0025`):** Replaces same-UID ancestry with kernel peer UID / host-mapped microVM `vsock` CID verified against the current `CIP-0025` protected boundary receipt (`EIC-5-03`, `EIC-8-04`).

### 5.4 `Curator.app` GUI Integration (Shared With `CIP-0036`)

The Developer-ID-signed `Curator.app` helper (URL router in `CIP-0036`) connects to `curator-auth-custody` over the Control Socket to provide a menu bar / status window showing auto-discovered services per profile and managed home, one-click OAuth/PAT login into `SecretStore`, non-blocking notifications on `auth_interactive_login_required`, and one-click session revocation.

---

## 6. CLI, Wire Surface, and Diagnostics

### 6.1 Operator CLI (`curator auth` -> `curator-auth` via `environments` section 11)

```text
curator auth status [--profile <P>] [--service <S>] [--live] [--format json]
curator auth login  <service> --account <id> [--method <m>] [--profile <P>]
curator auth bind   <service> --profile <P> --account <id> --confirm-auth-delta
curator auth unbind <service> --profile <P>
curator auth logout --account <id>
curator auth test   <service> --profile <P>
curator auth daemon [start|stop|status]
```

### 6.2 Data Socket Wire API (Unix Socket / `vsock`, Zero TCP)

- `GET /v1/meta/<service>`: returns non-secret account metadata (`org`, `project`, `namespace`, `user_id`).
- `GET /v1/status/<service>`: executes adapter status probe, returns `{authenticated, identity, expires_at}`.
- `ANY /v1/proxy/<service>/<path>`: Mode A HTTP/WebDAV Auth-Injecting Gateway.
- `POST /v1/mint/<service>`: Mode B narrowed ephemeral token mint.

### 6.3 Diagnostics

| Code | Exit | Meaning |
|---|---:|---|
| `auth_broker_unavailable` | 1 | Control/data socket or `vsock` unreachable |
| `auth_socket_dir_untrusted` | 1 | Runtime socket directory failed `lstat` owner/`0700`/non-symlink check |
| `auth_store_unavailable` | 1 | OS KEK store locked or inaccessible (checked before interactive login) |
| `auth_secret_too_large` | 1 | Encrypted credential payload exceeds `256 KiB` ceiling |
| `auth_adapter_origin_forbidden` | 1 | Package adapter contained an absolute URL or unapproved template variable |
| `auth_delta_confirmation_required` | 1 | Binding or package update widens origins, paths, methods, or delivery without `--confirm-auth-delta` |
| `auth_account_unbound` | 1 | Profile requires `<service>` with no binding in machine config |
| `auth_secret_missing` | 1 | Bound `account_id` has no encrypted blob in `~/.curator/auth-store/` |
| `auth_interactive_login_required` | 3 | Data-socket request needs interactive operator login; names exact `curator auth login` command |
| `auth_peer_ancestry_mismatch` | 1 | Data-socket caller PID is outside the session's admitted process tree |
| `auth_session_closed` | 1 | Session expired, closed, or revoked |
| `auth_service_not_admitted` | 1 | Session not authorized for `<service>` |
| `auth_endpoint_forbidden` | 1 | Path, method, SSRF target IP, or cross-origin redirect violates policy |
| `auth_exchange_failed` | 1 | `token_exchange` or `refresh_token` failed in custody process |
| `auth_scoped_env_refused` | 1 | Mode C requested under `hardened` isolated posture without explicit waiver |

---

## 7. Implementation Plan (Focused MVP: ~7.5 LU + Follow-Ups)

| Unit | Repo | Deliverable | Size (LU) | Depends On |
|---|---|---|---:|---|
| **S0** | `curator-spec` | Coordinated index + `platform-contract-disposition.md` PR reserving CIP numbers `0034-0038` and next `launch-env-fragment` revisions | 0.5 | -- |
| **S3** | `curator-spec` | Accept CIP-0037 MVP, `protocol/tool-auth-mediation.md`, `auth-adapter-v1` schema, `agent-mcp.json` v2 (`auth_service`), conformance vectors | 1.0 | S0 |
| **A1** | `curator` | Closure auto-discovery (`requires.auth`), operator-owned `auth` machine config, `--confirm-auth-delta` widening check, `~/.curator/auth-store/` exclusions, `env status` rows | 1.0 | S3 |
| **A2** | `curator-credential-broker` | `curator-auth-custody` (Control Socket, 32B KEK OS store + `0600` AEAD `~/.curator/auth-store/`, Developer ID signing for Keychain ACL, `ProbeWritable`, `<redacted>` types, `singleflight` + `flock`) + `curator-auth` CLI | 2.0 | S3 |
| **A3** | `curator-credential-broker` | `curator-auth-gateway` (Data Socket in `confstr`/`XDG_RUNTIME_DIR` with `lstat` guard, process-ancestry check, declarative adapter engine for `bearer`/`header`/`basic`/`token_exchange`/`refresh_token`/`oauth2_pkce`/`device`/`mtls`/WebDAV, DNS-pinned IPv4/IPv6 SSRF guard, hash-chained audit log) + Go SDK `pkg/authclient` + pilot adapters (YouTrack-style, Sentry-style, WebDAV) | 2.0 | A2 |
| **A4** | `curator-credential-broker` + `curator-agent-launcher` | `curator-mcp-bridge` (stdio-to-HTTP over Unix socket, zero TCP) + `curator-mcp-exec` (Mode C) + `curator-run`/`curator-app` session lifecycle wiring (TTL + launcher/instance lifetime) | 1.0 | A2, I4 |
| **A5** | `curator-credential-broker` | Tier 2: `CIP-0011` OS-user (`SO_PEERCRED`), `CIP-0025` microVM (`vsock`), boundary receipt verification, `curator-auth-adapter/1` host plugin runner, optional `swarma-keyvault` KEK | 1.5 | A3, CIP-0011/0025 |
| **A6** | `curator-agent-launcher` (`Curator.app`) | Menu bar / auth status GUI (per-profile and multi-managed-home), one-click login, re-auth notifications, session revocation | 1.5 | A2, I6 |

**Separate follow-up CIPs (explicitly outside CIP-0037 MVP):**
- **CIP-0038:** `browser_sso` (system Chrome CDP strictly over `--remote-debugging-pipe`, shared IdP SSO, `cookie` / `cookie_csrf` / `spa_token_capture`, DBSC and IdP policy boundaries).
- **Post-`SealLink v1.0.0-rc1` CIP:** SealLink Plane 1 executor admission (`seallink-grant/1`, `seallink-invocation/1`, `seallink-session-open/1`, `seallink-receipt/1`) and Mode D depth-2 re-delegation.

---

## 8. Decisions Recorded and Remaining Open Questions

**Confirmed (2026-11-25):**
- Repository name: **`relux-works/curator-credential-broker`** (accepted by Curator Core with B5 two-process split).
- Zero TCP transport: Unix sockets / `vsock` only + `curator-mcp-bridge` stdio-to-HTTP bridge for unmodified remote HTTP MCPs.
- Mode C policy: allowed on Tier 1 same-user desktop (explicitly convenience, not isolation); refused under Tier 2 `hardened` without per-server waiver.
- Pilot SDK targets (`A3`): Go SDK first (`pkg/authclient`), piloted on generic YouTrack-style issue tracker, Sentry-style error tracker, and WebDAV (zero private/third-party org references).
- External providers (`1Password`, `Vault`): deferred to `A2b`, strictly off by default and opt-in only.

**Remaining operator sign-offs:**
1. Confirm the coordinated reservation PR (`S0`) allocating CIP numbers `0034` (qualification), `0035` (surface), `0036` (GUI hosts), `0037` (credential broker MVP), `0038` (browser SSO), and the next `launch-env-fragment` versions.
2. Confirm default CLI session `max_ttl` (`4h`) and GUI session `max_ttl` (`12h` with host-side renewal while instance lives).
