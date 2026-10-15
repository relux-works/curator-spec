# CIP-0019: Carrier admission by public key (swarma-registrar)

- **Status:** Draft
- **Owner:** orchestrator; decision: operator
- **Created:** 2026-10-16
- **Related:** [CIP-0011](CIP-0011-credential-broker-and-agent-users.md) (broker leases, agent OS users); swarma-credential-broker `spec/broker.md` §6.1 and §6.4 (signed envelope construction, CCJ-1), §13.1 (socket framing); Swarma book v0.10, chapter 4 (keys and keymaster) and §6.2 (agents do not read the carrier); curator review of 2026-10-16 (R1–R6, S1–S5)
- **Affects:** new module `swarma-registrar` (registrar service and phase-0 host helper); the a2a CLI login path; homeserver configuration in the deployment repository; host enrollment records

## Summary

Agents get carrier (Matrix) accounts without a shared registration token. A host proves possession of an enrolled key by signing a short registration request; the registrar checks the key against a reviewed enrollment record and the requested name against that host's permitted names, then issues a 120-second login JWT signed with its own Ed25519 key. The homeserver trusts only the registrar's public key and has registration otherwise closed. No password or shared secret lives on any host. The admission core (key proof, enrollment, short-lived carrier credential) is the part that stays when Swarma's bridge takes over the carrier; per-agent logins are a transitional a2a feature.

## Motivation and user stories

1. **Onboarding without a shared secret.** With a shared registration token, any holder can take any free name, including names that room policy privileges, and nothing records who created which account.
2. **Containment.** A compromised host must not be able to impersonate agents of other hosts; no single host should hold credentials that reach beyond its own agents.
3. **No stored passwords.** A client that keeps a password for re-login exposes it to a prompt-injected agent that can read its files.
4. **Revocation.** The operator removes one host and its agents lose the ability to log in again, without touching other hosts.
5. **Path to Swarma.** The same admission core later verifies keymaster-derived agent keys chained to the owner root (book chapter 4) instead of host keys.

## Current state

- The carrier is a tuwunel homeserver (v1.9.3) with federation off. Accounts are created through Matrix registration; the a2a CLI keeps `user_id`, `access_token`, `device_id` and a password in its credential file and logs in again with the password on `M_UNKNOWN_TOKEN` (a2a-swarm `docs/cli.md`, credentials).
- tuwunel v1.9.3 configuration (`tuwunel-example.toml`):
  - `[global.jwt]`: `org.matrix.login.jwt`, `format = "EDDSA"` (Ed25519 PEM public key) or `ECDSA`; `register_user` creates the account on the first valid token; `issuer`, `audience`, `require_exp`, `require_nbf`; one verification key per server; the settings are reloadable.
  - `[[global.identity_provider]]`: built-in SSO (GitHub, Google, Keycloak, MAS); `registration = false` admits only accounts the admin associated.
  - `[global.appservice.<ID>]`: inline appservices with exclusive namespaces.
  - `access_token_ttl`, `refresh_token_ttl`: token lifetimes.

## Design

### Options considered

| Option | Mechanism | Pros | Cons |
| --- | --- | --- | --- |
| A. Shared registration token | one token in every host's config | simple | any holder takes any name; no attribution; a leak opens the server |
| B. Admin-provisioned accounts | registration closed; admin creates each account | attributable | does not scale for agents; admin credential in the loop |
| C. Appservice per host | each host's service owns an exclusive namespace | strong namespace isolation; fits the Swarma bridge | per-host shared secret (`as_token`), not public-key based; agents still need tokens from the bridge |
| D. Registrar + JWT login (recommended) | enrolled-key proof → registrar → 120 s JWT → `org.matrix.login.jwt` | no shared secret on hosts; per-host name scope; one trust anchor on the server | a new service and a host helper |
| E. Matrix Authentication Service | full OIDC for all clients | standard for humans | heavy; agents would still need a key-based client grant |

### Recommendation

Option D, with the formats and rules below. Humans stay on tuwunel's built-in SSO (outside the registrar). Option C remains the end state for a Swarma bridge.

**Registration request (`registration/1`).** An envelope with `body`, `id`, `sig`, built like broker `grant/1`:

- preimage = `swarma-registrar registration/1` + `\n` + CCJ-1 canonical bytes of `body`;
- `id = "sha256:" + lowercase hex of SHA-256(preimage)`; `sig` is over the same preimage; neither is part of `body`;
- body members: `type` = `"registration/1"`; `key` = `"ed25519:<base64url>"` or `"p256:<base64url SEC1 compressed point>"`; `name` (Matrix localpart); `aud` (the homeserver's server name); `nonce` (128-bit, base64url); `iat`, `exp`;
- `iat` and `exp` are whole-second RFC 3339 UTC timestamps with a `Z` suffix and no fractional part (they are hashed into `id`); `exp − iat ≤ 120 s`;
- signatures: Ed25519, or ECDSA P-256 with SHA-256 as raw `r‖s` (64 bytes) with low-S required;
- CCJ-1 rejection rules apply (duplicate keys, invalid Unicode, floats, unsafe integers, negative zero, unknown members);
- this is a new domain; `grant/1` is not reused.

**Enrollment record (`enrollment/1`).** Same construction, domain `swarma-registrar enrollment/1`:

- `host`: label `[a-z0-9-]{1,32}` (no underscore, so `<host>_` is an unambiguous prefix);
- `keys[]`: `{ key, not_before, not_after }` (rotation without a gap);
- `names`: `{ prefix: "<host>_", explicit: [ ... ] }` (explicit entries cover legacy non-prefixed names);
- `uid_map` (optional): OS UID (optionally executable path) → permitted names. Only the host helper can see the caller's UID, so the helper is the sole enforcer; the registrar treats `uid_map` as informational;
- `seq`: monotonic; `state`: `active` or `revoked` (a tombstone, so an older registry revision cannot resurrect a host);
- `sigs[]` (optional, later): the owner root's signature (book §4.5).

Phase-0 authority is a signed commit on the protected registry branch. The registrar and the host helper each load a pinned, verified revision of the record and never follow a mutable fetch.

**Names.** `<host>_<project>_<role>[-q]`, validated before signing (localpart grammar, length, permitted by enrollment). Later the keymaster path maps to the name and the mxid stays stable across key rotation.

**Host helper (phase-0 keymaster).** A separate component running as a dedicated service user (not root):

- Unix socket; frames are a 4-byte big-endian length plus a CCJ-1 object; `hello { versions: [1] }` first (broker §13.1);
- the socket's directory is owned by the helper's service user; the socket is mode 0660 with a dedicated group whose members are the agent users permitted to request registrations. Without a `uid_map`, the boundary is that group: any member may request any name the host is enrolled for;
- one operation, `sign_registration { name, aud }`. The helper refuses an `aud` other than its configured server name and a name its pinned enrollment does not permit; it enforces `uid_map` against the caller's `SO_PEERCRED`/`LOCAL_PEERCRED` UID when present; it builds the body (fresh nonce, `iat`, `exp`) and signs only the `registration/1` domain. It is not a general signing oracle;
- key storage: on macOS a Secure Enclave P-256 key if a launchd-daemon probe succeeds (CryptoKit needs a signed binary and `dataRepresentation` persistence), otherwise Ed25519 in a 0600 file owned by the service user; on Linux a 0600 file now, TPM later.

**Registrar.** An HTTPS service that holds only its JWT signing key:

- endpoint: `POST /v1/registration` (envelope) → `200 { jwt }` or a typed refusal;
- checks: CCJ-1 and id; signature; key enrolled and inside its validity window; host `active`; name syntactically valid and permitted; `aud` exact; `exp − iat ≤ 120 s`; clock skew bounded; nonce unused; `iat` not before process start;
- refusals: `registration_malformed`, `registration_id_mismatch`, `registration_signature_invalid`, `signature_high_s`, `key_not_enrolled`, `key_not_valid_now`, `host_revoked`, `name_invalid`, `name_not_permitted`, `audience_mismatch`, `request_expired`, `request_not_yet_valid`, `clock_skew`, `nonce_replayed`, `rate_limited`;
- JWT: EdDSA; claims `iss = "swarma-registrar"`, `aud = ["<server-name>"]`, `sub` = localpart, `iat`, `nbf`, `exp = iat + 120 s`, `jti` = request id;
- runs as a single replica: nonces are held in memory for the `exp` window and requests with `iat` before process start are refused, which covers replay across restarts without storage. Scaling out needs a shared nonce store first;
- rate limits per key and per name; append-only audit of issued and refused requests (with `jti`) shipped off the registrar's host.

**Homeserver configuration.** Registration closed and no registration token; `[global.jwt]` with `enable = true`, `format = "EDDSA"`, the registrar public key, `register_user = true`, `issuer = ["swarma-registrar"]`, `audience = ["<server-name>"]`, `require_exp = true`, `require_nbf = true`; `access_token_ttl` 12–24 h. Agents do not request refresh tokens.

**a2a CLI.** `identity ensure` and re-login on `M_UNKNOWN_TOKEN` run helper → registrar → JWT login. The credential file holds only `user_id`, `access_token`, `device_id`, is written atomically with mode 0600, and the CLI never prints the JWT or tokens.

**Revocation.** Set the enrollment `state = revoked` (`seq + 1`) so the registrar and the helper refuse; the admin logs out every device of the host's users and deactivates them where needed; the audit log lists every token issued since the last known-good time.

**Key rotation.** The JWT is login-only and short, so the registrar key and the homeserver's JWT key switch together; the homeserver applies the new key on a configuration reload or restart. At worst logins fail for up to 120 s.

**Humans.** tuwunel GitHub SSO with `registration = false`; the admin creates and associates human accounts; GitHub 2FA is required. Not part of the registrar.

## Security considerations

- **Phase-0 boundary is host plus OS user.** Where several agents share one OS user, any process of that user can request any name the host may mint. The `uid_map` hook exists from the start so per-agent OS users (CIP-0011) narrow it to one agent; the socket group bounds it otherwise.
- **Registrar compromise** lets an attacker mint any name. The registrar holds one key, has a minimal surface, logs every issuance off-host, and rotates without overlap.
- **Host helper compromise** exposes that host's key only; revocation removes it. The helper signs one domain only.
- **JWT interception** inside its 120 s life allows one login; TLS protects transport; `jti` joins the audit.
- **Registry tampering** is countered by signed commits on a protected branch and a pinned revision; tombstones stop a stale revision from reviving a revoked host.
- **Replay** is refused by in-memory nonces within `exp` and by refusing `iat` older than the process start (single replica).
- **Clock**: NTP on hosts; skew refusals are typed.
- **Denial of service**: per-key and per-name rate limits.

## Compatibility and migration

1. Build and qualify the registrar, helper and CLI path (negative vectors first).
2. Enroll each host with its label, the prefix `<host>_` and an explicit list for legacy non-prefixed names (operator decision 2026-10-16). Concrete enrollments live in the private deployment repository.
3. Cut over: configure JWT on the homeserver; close token registration; for every account created while a token was in use, disable or reset the password and log out its devices; agents log in again through the JWT path under the same mxid.
4. Rename legacy names to the prefix scheme over time; remove explicit entries afterwards.

## Specification changes

A new module specification `swarma-registrar/spec/registrar.md` owns the `registration/1` and `enrollment/1` domains, the helper socket protocol, the HTTP API, refusal codes and canonical vectors. Adoption produces a Decision record for the two new signing domains. No change to broker formats.

## Implementation plan

1. Formats: canonical and negative vectors for `registration/1` and `enrollment/1` (Ed25519 and P-256).
2. Registrar service with audit and rate limits; deployment in the private deployment repository.
3. Host helper: Linux file key; macOS Secure Enclave probe, then the daemon.
4. a2a CLI JWT login path and credential file changes.
5. Homeserver JWT configuration and the cut-over runbook, then the revocation runbook.

## Test plan

Negative tests first:
- each `registration/1` negative vector;
- an invalid name and a name outside the prefix;
- a removed (revoked) host;
- an expired request;
- a replayed nonce;
- a wrong `aud` (refused by the helper and by the registrar);
- a P-256 high-S signature;
- an Ed25519 key presented as P-256.

Then end-to-end against a test homeserver: first login creates the account; a second login reaches the same mxid; registration with a token is refused after cut-over; revocation blocks new logins and logout ends existing sessions.

## Open questions for the operator

1. **Host labels.** Each host's operator chooses its label; concrete labels live in the private deployment repository.
2. **Access token lifetime.** Recommended: 24 h, no refresh tokens for agents.
3. **macOS host key.** Recommended: Secure Enclave if the probe passes, otherwise a 0600 file under the helper's service user.
4. **Registry location.** Recommended: deployment data in the private deployment repository, reviewed by PR; the module repository holds code, spec and vectors.
5. **Legacy names.** Decided 2026-10-16: explicit list now, rename later.
6. **Closing token registration.** Decided 2026-10-16: after the current agents re-register; new agents in between are created by the admin.
