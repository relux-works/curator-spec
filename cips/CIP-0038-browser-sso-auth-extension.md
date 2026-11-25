# CIP-0038 (Draft): Isolated Browser SSO Authentication Extension for Curator Credential Broker

- **Status:** Draft (reserved in `curator-spec` PR #233 / `S0`)
- **Owner:** Ivan Oparin (decision); author: Curator Architect
- **Created:** 2026-11-25
- **Depends on:** CIP-0037 (`curator-credential-broker` MVP: two-process custody + gateway, envelope-encrypted `SecretStore`, `--confirm-auth-delta` origin pinning, `singleflight` + `flock`)
- **Related:** CIP-0036 (`Curator.app` GUI helper), CIP-0011, CIP-0025

---

## 1. Summary

Many internal corporate portals sit behind a shared OIDC/SAML Identity Provider (e.g., Okta, Microsoft Entra ID, or another enterprise IdP) without personal access tokens or dedicated CLI OAuth clients. This CIP extends `CIP-0037` (`curator-credential-broker`) with a declarative `auth_methods[].kind = "browser_sso"` flow executed **exclusively inside `curator-auth-custody` on the host**, using the OS-installed Chrome/Chromium browser over **inherited anonymous pipes (`--remote-debugging-pipe`) -- NEVER a TCP debugging port**.

Placing browser SSO inside `curator-auth-custody` (rather than inside agent-side CLIs) solves two hard security problems simultaneously:
1. **Blast-radius containment:** Web session cookies carry full user UI privileges. Because cookies and CSRF tokens remain strictly on the host broker (`curator-auth-custody` -> short-lived lease to `curator-auth-gateway`), the gateway enforces operator-confirmed `allowed_path_prefixes` and `allowed_methods` (e.g., read-only `GET`) outside the agent's reach.
2. **Headless microVM & OS-user compatibility:** Isolated agents inside `CIP-0011` OS accounts or `CIP-0025` microVMs need no Chrome, display, keychain, or corporate Root CA -- all browser login/silent-refresh happens on the host.

---

## 2. Security-Critical Design Invariants

### 2.1 Strictly `--remote-debugging-pipe` (Zero TCP DevTools Port)

- `curator-auth-custody` MUST launch Chrome/Chromium exclusively with **`--remote-debugging-pipe`** (CDP JSON messages over inherited file descriptors 3 and 4).
- `--remote-debugging-port` (including `=0`) is **FORBIDDEN**: a localhost TCP debugging port grants full browser and IdP cookie access to every UID on the host (including isolated `CIP-0011` agent accounts).

### 2.2 Isolated Ephemeral Profiles + Envelope-Encrypted `storage_state`

- `curator-auth-custody` MUST NEVER read or touch the user's personal Chrome profile.
- Browser session material (`storage_state`: IdP SSO cookies, target domain cookies, CSRF tokens, optional `localStorage`) is stored in `~/.curator/auth-store/<sso_account_id>.enc` using CIP-0037's AEAD envelope encryption (32-byte KEK in OS Keychain / Secret Service / Windows Credential Manager -- bypassing the 2560-byte Windows CredMgr limit).
- During interactive login (`curator auth login` on Control Socket / `Curator.app`) or silent headless refresh, custody creates a fresh `0700` temp directory inside the per-user private runtime dir (`confstr(_CS_DARWIN_USER_TEMP_DIR)` / `$XDG_RUNTIME_DIR`), injects `storage_state`, launches system Chrome, extracts updated `storage_state`, persists encrypted bytes atomically, and wipes the temp directory.
- Optional per-account `persistent_browser_profile: true` stores an isolated `0700` profile under `~/.curator/auth-profiles/<sso_account_id>/` (registered top-level manager-home directory excluded from `contextpkg`, `CIP-0014` snapshots, and unencrypted bulk backups) strictly for IdPs requiring device-bound browser profiles.

### 2.3 Shared IdP SSO Per Profile Group + Operator-Owned Origins

- Following CIP-0037 B4, **all origins (`base_url`, `idp.issuer`, `idp.redirect_hosts[]`, `cookie_domains[]`) MUST resolve exclusively from operator-owned machine config** and require `--confirm-auth-delta` on bind or widening. Package adapters specify only relative `entry_path`, `extract_mode`, and CSRF selector/header names.
- Multiple accounts within one profile (or an explicitly shared profile group) MAY reference one `idp_ref` (e.g., `corp-oidc-work`). Logging into `corp-oidc-work` once interactively enables silent headless cookie acquisition for every portal sharing that `idp_ref` under the same profile, while keeping `work` and `personal` SSO jars strictly separate.

### 2.4 Three Declarative Extraction Modes

1. **`cookie`:** extracts and leases domain-scoped `Cookie` values to `curator-auth-gateway` strictly for operator-pinned target origins.
2. **`cookie_csrf`:** extracts `Cookie` + CSRF token (`csrf_meta_selector` HTML `<meta>` tag or `csrf_cookie_name` -> `csrf_header`) + declared `extra_headers` (e.g., `X-Requested-With: XMLHttpRequest`).
3. **`spa_token_capture`:** listens over `--remote-debugging-pipe` CDP network events during login/refresh to capture `access_token` (and optional `refresh_token`) from the SPA's OIDC token response or first `Authorization: Bearer` request, transitioning thereafter to fast pure-HTTP `bearer`/`refresh_token` mode without launching Chrome.

### 2.5 Two-Stage Silent Refresh (`net/http` Fast Path -> Ephemeral Chrome Fallback), `singleflight` + `flock`, and Non-Interactive Exit `3`

- **Zero resident Chrome processes:** Normal API traffic (99.9% of requests across any number of parallel agents) runs strictly over pure Go `net/http` using cached cookies/CSRF/tokens (0 MiB Chrome overhead). Chrome NEVER runs persistently and is NEVER launched per agent.
- Expired web sessions typically return `302`/`303` redirecting to `idp.redirect_hosts[]` (or `200 text/html` login HTML) rather than `401`.
- When `curator-auth-gateway` observes a `session_expired_match` (`401`, `302`/`303` to operator-configured `idp.redirect_hosts[]`, or unexpected `text/html` on a JSON API), it requests a silent refresh from `curator-auth-custody` under an in-process `singleflight` guard + per-`sso_account_id` `flock` (re-reading the encrypted store first so 20 parallel agent calls trigger at most ONE refresh per account):
  1. **Stage 1 -- Pure-HTTP Redirect Fast Path (~150ms, zero Chrome):** For standard OIDC/SAML redirect flows (e.g., `oauth2-proxy`, standard BFFs) that require no JavaScript, `curator-auth-custody` replays the bounded redirect chain (`portal` -> operator-pinned `idp.redirect_hosts[]` carrying the stored IdP SSO session cookie from `storage_state` -> `portal` callback) strictly with Go `net/http` (still enforcing DNS-pinned SSRF and operator-pinned origin allowlists). If fresh target cookies are obtained, refresh finishes in ~150ms without ever spawning Chrome.
  2. **Stage 2 -- Ephemeral Headless Chrome Fallback (2-3s, immediate exit):** Only when Stage 1 encounters a JavaScript-gated flow (SAML auto-submit form, JavaScript-driven OIDC SPA token capture) does `curator-auth-custody` spawn ONE short-lived headless Chrome strictly over `--remote-debugging-pipe`, extract updated `storage_state`, terminate Chrome immediately, and wipe the temp `0700` profile.
- If the IdP SSO session itself has expired (interactive 2FA/Passkey required), any Data Socket request immediately fails closed with HTTP `401` / CLI exit code `3` (`auth_interactive_login_required`), NEVER popping up a browser window during an agent run.

---

## 3. Explicit Feasibility and Policy Boundaries

1. **Device-Bound Session Credentials (DBSC), Token Binding, and Sender-Constrained Tokens (DPoP):** IdPs enforcing hardware/TPM-bound browser cookies (DBSC) invalidate cookies replayed outside the bound Chrome process, and SPAs issuing sender-constrained tokens (RFC 9449 DPoP) bind refresh/access tokens to a browser-held key so `spa_token_capture` cannot replay them out of process. Adapters for such IdPs/SPAs fail closed with `auth_exchange_failed` rather than downgrading security.
2. **Corporate IdP Terms and Replay Policy:** Automated headless replay of corporate web SSO sessions may be restricted by an employer's security or acceptable-use policy. `browser_sso` is an **explicit operator opt-in** per account; compliance with target IdP policy is solely the operator's responsibility. Wherever a service supports OAuth2 PKCE/Device Flow with narrowed scopes (e.g., `read_api`), operators SHOULD prefer CIP-0037's `oauth2_pkce`/`oauth2_device` over `browser_sso`.

---

## 4. Implementation Slice (`A3b`, ~1.5 LU)

- **Repository:** `relux-works/curator-credential-broker` (depends on `CIP-0037` `A2` + `A3`).
- **Deliverables:** system Chrome discovery (macOS/Linux/Windows), CDP client strictly over `--remote-debugging-pipe` (refusing any TCP flag), ephemeral `0700` profile lifecycle, `cookie`/`cookie_csrf`/`spa_token_capture` extractors, `302`-to-IdP refresh trigger, `singleflight` + `flock` concurrency tests, and adversarial negative tests proving zero TCP sockets, deletion of temp profiles, non-interactive exit `3`, and host-side blocking of `DELETE`/`/admin` over a live web session cookie.
