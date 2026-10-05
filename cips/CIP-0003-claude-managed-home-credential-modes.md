# CIP-0003: Claude managed-home credential modes

- **Status:** Draft
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-04
- **Related:** TASK-261004-34brhn — research-claude-login-transfer-modes; STORY-261004-1pwxri — claude-macos-managed-home-login-modes; Decision 0017 — environment credential modes.
- **Affects:** curator-spec rc.14 environments §§7.4, 7.7, 7.9, 8.2, 8.4.1, 10.1–10.4, 12.1–12.2; manager §§1, 12.4–12.5; configuration, marker and launch-fragment schemas; curator; curator-run/launcher and its tracked execution boundary.

## Summary

Offer an operator-controlled credential source for each profile and environment: `token`, `helper`, or `per-home`, with `shared-file` admitted only by a verified platform capability. A setup token reuses the operator's subscription authorization without extracting the existing native login; a helper supplies an externally managed API credential; a per-home login remains owned and refreshed by Claude Code. Curator resolves references and manages metadata, while the launcher obtains a selected token from a protected store immediately before starting the child. Keep `per-home` as the new macOS default and preserve existing installations until explicit adoption. This proposal does not discharge Decision 0017 Q1's disposable-account gate or authorize native credential copying under Q7.

## Motivation and user stories

The binding operator decision requests all three mechanisms, selected per profile and per environment. An unattended profile should be able to use a separately minted subscription token from a protected store. A profile using a credential service should be able to select `apiKeyHelper` and let that service handle rotation. An interactive profile should be able to retain its own Claude Code login across launches, including the tool's native Keychain/file behavior.

Changing context profiles should not accidentally change billing because an inherited API key won over the intended subscription token. Changing a credential mode must not remove an existing login, silently migrate credential ownership, or reveal a token through launch previews, board resources, fragments, argv, or tracked execution records.

Research bounds: one decision proposal and its evidence companion, at most 96 KiB combined; a 60-minute initial worker budget; no additional research prerequisite before the first implementation slice. Grammar freezing is not applicable to this research artifact: the schema sketch below becomes a reviewed grammar in the spec leaf. The first consuming slice is trusted mode resolution plus protected-store token injection through the real curator-run child-process entry point.

## Current state

This CIP is filed from the research draft in [.research/261004_CIP-0003-claude-managed-home-credential-modes.md](https://github.com/relux-works/curator/blob/fae2ff9cab17a031c26a2b4c776afd8dc5e8b4f6/.research/261004_CIP-0003-claude-managed-home-credential-modes.md) on `relux-works/curator` `main` @ `fae2ff9c`. Evidence identifiers used below resolve in the companion [.research/261004_CIP-0003-claude-managed-home-credential-modes_evidence.md](https://github.com/relux-works/curator/blob/fae2ff9cab17a031c26a2b4c776afd8dc5e8b4f6/.research/261004_CIP-0003-claude-managed-home-credential-modes_evidence.md) at the same commit; they are cited, not copied. The operator has made no acceptance decision on this proposal. Repository citations are pinned to curator main `ca1b776fb580ec0cee0173bf150daf063023aeaa`, curator-spec rc.14 `43bf0a2506d5c354a73bbc3ea4623d4653db10c7`, and launcher main `2517d2753945d0a8b0c40a291e4aef883a7c16ee`.

- Curator exposes `environments.isolation.<profile>.<env>` with `shared|isolated`, rather than credential-source modes (`internal/config/environments.go:20`, `:799`). Its macOS Claude adapter declares no shared passthrough, pins 2.1.261, defaults to isolated, and refuses shared (`internal/envregistry/envregistry.go:240`, `:450`). The production resolve path calls this policy (`internal/envprofile/managed.go:319`). [C1–C3]
- The macOS isolated marker currently records `strategy=per-home-keychain`, `backend=keychain`, and the registry's release without observing a successful Keychain write (`internal/envprofile/managed.go:598`). This is strategy metadata, not evidence of actual authentication or of the selected backend. [C3]
- rc.14 §7.4 and Decision 0017 Q1 retain the shared-store gate. The recorded 2.1.273 login wrote a managed `.credentials.json`; its cause was unknown. Current documentation and shipped fallback logic provide a possible explanation, not a retrospective diagnosis of that host. Q7 refuses credential copies; the manager never exports a native Keychain secret to JSON. [S1–S3]
- rc.14 already contains manager-config-v3, launch-env-fragment-v3, and marker-v3. Its §12.2 now permits isolation locks in either direction even though Decision 0017's original Q6 described that as future work. This draft uses the rc.14 normative text for compatibility. [S4]
- The inspected macOS executable is **Claude Code 2.1.287**, not an assertion about the globally latest release. Safe scratch probes confirmed per-directory service selection, local token/helper/API-key selection, synthetic file fallback, and synthetic Keychain preference. They exercised `auth status`, not successful model authentication. No real login, refresh, logout, credential-store read, or Keychain write was performed. [P1–P15]
- The launcher's direct path already keeps the full environment out of its JSON value, but the tracked path serializes `env_literals`. Credential injection must happen after that serialization boundary, never by adding a token to fragment `env` or composition literals (`internal/composition/composition.go:35`, `:75`; `internal/execution/execution.go:142`). [L1]

### Mechanism and lifecycle findings

| Mechanism | Source, persistence and refresh | Bound of the finding |
| --- | --- | --- |
| `claude setup-token` → `CLAUDE_CODE_OAUTH_TOKEN` | Separate browser authorization issues a long-lived subscription token; the documented default is one year. Setup prints it without saving it. The CLI constructs an access-token-only credential, without a refresh token or known expiry, from the environment. Each new process needs injection again; after expiration or revocation, mint and install a replacement, then restart. | Docs and shipped code; dummy token selects `oauth_token`. No live issuance, expiry, or revocation test. Model-request capability is narrower than full browser login: do not promise Remote Control or fetched claude.ai connectors. `--bare` does not consume this variable. [D1, D2, B3, B4, P4] |
| `apiKeyHelper` | A settings command produces an API credential. Claude caches it in the process, normally for 300,000 ms; the helper owns issuance/renewal. Documented reruns include cache expiry, eligible 401/403 responses and expired cached JWTs. A new process starts with a new cache. | This is an API credential channel, not evidence that a setup token works as an equivalent full subscription login. Native output is used in API-key and bearer headers. The shipped helper can retain an old cached value after a background refresh failure. Status selects the helper without executing it. [D3, B5, P6] |
| Per-home `/login` | With an ordinary `CLAUDE_CONFIG_DIR`, the macOS service is directory-scoped. The store tries Keychain first and has a plaintext `.credentials.json` fallback under the selected storage directory. Stored login state includes refresh information; the CLI renews it and persists the resulting credentials. It can eventually require interactive login again. | Keychain-first selection is measured with a shim; fallback/write and refresh logic are inspected. First login, refresh persistence, and locked-Keychain behavior on a real account remain unmeasured. Console OAuth stored as an Anthropic profile outside the config home is excluded from the proposed per-home qualification. [B1, B2, B6, P7–P9, D1] |
| Native file symlink | A synthetic linked file can be read on this build, including on a second process launch. | **Readability is not refresh safety.** The ordinary plaintext writer calls an atomic staging/rename helper; another storage API has explicit symlink-refusal states. Real refresh, active-path selection, and cross-home refresh locking have not been qualified. [B2, B7, P13–P14] |

For ordinary first-party CLI operation, documented priority is provider selection, then `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY`, `apiKeyHelper`, `CLAUDE_CODE_OAUTH_TOKEN`, qualifying Anthropic profile/federation sources, and stored subscription login. Gateway sessions and some profile choices have additional rules. API-key approval differs between interactive use and `-p`. Treat this as the vendor's source-selection logic, not the Curator configuration precedence defined below. [D1; synthetic confirmation limited to P4–P6]

## Design

### Options considered

The first three options are complementary operator choices, as required by the brief.

| Option | Mechanism and advantages | Tradeoffs and security |
| --- | --- | --- |
| **1. `token`** | Inject an explicitly enrolled setup token from a protected store. Reuse one source across selected profiles; avoid an additional home login for each launch. | Finite lifetime, no CLI self-refresh, subscription feature limits, restart on rotation. The child and its permitted descendants may see the environment. A stolen token grants its scoped access until expiry/revocation. |
| **2. `helper`** | Configure an operator-owned `apiKeyHelper` bridge. Useful for vaults, temporary credentials and centrally managed rotation. | Executes trusted machine code; helper output is a secret channel. API billing/endpoint behavior may differ from subscription login. Caching, retry and retained-value behavior must be accepted and tested. |
| **3. `per-home`** | Let Claude Code create and refresh its own directory-scoped login. No Curator secret read is needed. | Each home needs an initial login. A Keychain failure may leave a plaintext file. Re-login and backend changes belong to Claude; native Console profile behavior is not home-separated. |
| **4. `shared-file`, capability-gated** | Maintain only the native file link when the exact platform/backend/release has passed qualification. | Can detach on atomic replacement, be refused as a symlink, or race refreshes using different home locks. Not admitted on macOS by this CIP's evidence. Preserve existing Linux behavior as legacy, without relabeling it verified. |

An undocumented `CLAUDE_SECURESTORAGE_CONFIG_DIR` can alter both file and Keychain lookup on the inspected build, including unsuffixed lookup when explicitly empty. That expands Decision 0017's earlier string-only evidence, but it is **not** a fifth supported mode or a way around Q1. No operator credential was accessed through it. [B1, P11–P12]

### Recommendation

Adopt options 1–3 as explicit selectors, with option 4 reserved behind the original sharing gate. Use one machine-owned configuration surface. Profile packages, overlays, project repositories and generated fragments cannot define secret sources or helper commands.

Proposed manager-config-v4 example; source records contain references and non-secret execution metadata only:

```json
{
  "schema_version": 4,
  "skills_root": "/srv/curator/skills",
  "projects": {},
  "credential_sources": {
    "subscription-primary": {
      "kind": "claude-oauth-token",
      "backend": "macos-keychain",
      "service": "works.relux.curator.oauth",
      "account": "subscription-primary"
    },
    "api-issuer": {
      "kind": "api-key-helper",
      "executable": "/usr/local/libexec/issue-claude-key",
      "args": [],
      "ttl_ms": 300000
    }
  },
  "environments": {
    "credentials": {
      "defaults": {
        "claude_code": {"mode": "per-home"}
      },
      "profiles": {
        "automation": {
          "claude_code": {"mode": "token", "source_ref": "subscription-primary"}
        },
        "vault": {
          "claude_code": {"mode": "helper", "source_ref": "api-issuer"}
        },
        "interactive": {
          "claude_code": {"mode": "per-home"}
        }
      }
    }
  }
}
```

The closed selector union is `{mode: per-home}`, `{mode: token, source_ref}`, `{mode: helper, source_ref}`, or `{mode: shared-file}`. Extra fields, inline secrets, arbitrary credential paths, unknown modes, wrong source kinds and unsupported environment/platform combinations refuse resolution. Identifiers use the existing portable identifier grammar. Helper `executable` is absolute, `args` is a string array, and `ttl_ms` is an integer from 0 through 86,400,000, default 300,000; zero requests no time-based reuse. Other environments retain their existing protocol until an adapter explicitly supports these selectors. Source configuration is operator-owned, access-restricted machine state, outside profile snapshots and portable exports. For the initial macOS token backend, `service` is the fixed Curator-owned namespace shown above and `account` must equal the source ID; arbitrary Keychain services and native Claude items are rejected. The dedicated item holds the token plus a generation and optional enrollment/expiry metadata as one atomically replaced record. No source may point to a native or managed Claude credential file.

**Configuration precedence and defaults.** For an opted-in environment, the explicit profile/environment selector wins over that environment's default selector; no field-wise merging occurs between selectors. If neither is present in the new credential configuration, macOS Claude defaults to `per-home`. Existing configs with no new credential configuration keep the legacy rules, including their ambient-auth semantics. System policy cannot name a source, replace a helper, or lock credential-source configuration; rc.14's no-credential-selection lock rule remains intact.

`isolation` continues to describe native-store sharing, rather than being renamed or reinterpreted as account isolation. `token`, `helper`, and `per-home` require no native-store links; `shared-file` requires the existing shared-store strategy. An explicit legacy isolation setting or applicable system lock that disagrees with the chosen strategy is a configuration conflict. New selectors override only the implicit legacy default. An isolated store lock does not forbid reusing a deliberately selected external token: as in Q2, it never promised account separation. Report both the source mode and store-sharing policy to make that distinction visible.

**Launch selection.** New explicit modes are authoritative at launch. Before looking up a secret, the launcher rejects competing inherited authentication inputs by name, never value; it does not silently fall back to them. The versioned conflict set covers API/bearer/OAuth variables, OAuth refresh provisioning variables, host/FD token channels, provider switches, Anthropic profile/federation selection, the secure-storage override, and auth/endpoint settings that contradict the selected mode. Nonempty active gateway/profile state outside the managed home, incompatible admin policy, unsupported `--bare` use and native flags that could replace credential settings also require refusal or an explicitly qualified adapter path. A present secure-storage override is a conflict even when its value is empty. An unreadable policy source is an error, not an absent credential.

For `helper`, supply a protected launch settings file whose only generated authentication setting is a command invoking a trusted curator-run credential bridge with an opaque source identifier. The bridge resolves the same machine-owned profile/environment authorization, directly executes the declared executable and args from a fixed trusted working directory, and returns only a bounded credential to Claude's private helper pipe. It suppresses raw helper stderr and emits a generic failure; native Claude otherwise includes helper stderr in errors. No arbitrary project command is adopted. The settings file contains no credential and does not overwrite the operator's native or managed `settings.json`.

Effective Claude settings precedence must be qualified for the pinned release. Managed policy remains authoritative: the bridge is not a bypass. Curator must not claim a selected mode if a higher-priority effective helper, environment block, gateway, profile or provider wins. Production tests must include those sources and live settings reload. This is a guarantee about launch selection and Curator's own handling, not an enduring security boundary against a user or repository code already allowed to execute as that user.

### What curator-run does at launch

1. Resolve the profile, environment and closed selector from trusted machine configuration; check policy, adapter capability, existing-home migration state and native credential conflicts. Produce only non-secret metadata. `env resolve`, status, previews and dry runs never retrieve a secret or invoke a helper.
2. Bind the selected source to that effective profile/environment and a digest of the trusted non-secret configuration. Validate the provider executable and the settings bridge before secret retrieval. Recheck the binding and file identities at the final launch boundary; a changed source, policy or executable refuses rather than using stale authorization.
3. In `token`, read only the specifically enrolled item from the selected protected store using Security.framework on macOS. No Keychain enumeration, native Claude item lookup, shell substitution or `security ... -w` logging pipeline is involved. Put the value into the child's `CLAUDE_CODE_OAUTH_TOKEN` environment immediately before spawn; keep it out of parent-global environment, argv, request JSON, fragments, diagnostics and audit payloads. Distinguish absent, locked/denied, malformed and expired metadata states. None triggers another mode.
4. In `helper`, install the non-secret settings reference and TTL; the bridge owns secret-output handling and Claude owns its helper cache. In `per-home`, inject only the managed config directory and let Claude manage its credential backend. Never infer logged-in status from a file or marker. In `shared-file`, perform the existing no-follow link checks plus the new capability gate; Curator never reads or repairs credential bytes.
5. For tracked or remote launch, the final executor must implement the same protected-source lookup contract on the execution host. Carry an opaque authorized reference, not a secret in `env_literals`, `env_names` fallback or the tracked request. Until that boundary is implemented and verified, explicitly selected token/helper modes refuse tracked execution; direct-mode support must not be advertised as tracked-mode support.

### Expiry, refresh and rotation

| Mode | Curator behavior | Operator recovery and persistence |
| --- | --- | --- |
| `token` | Read the current store generation at each launch. Optional expiry metadata comes from enrollment; an opaque token is not parsed to invent an expiry. Refuse a known-expired source; report unknown expiry without claiming freshness. No automatic login or native-store fallback. | Enroll a fresh setup token through a protected input flow outside logs, atomically replace the dedicated item, and restart affected sessions. Already running children retain their old token. Revoke old authorization through the provider's supported flow; replacing local bytes alone is not revocation. |
| `helper` | The bridge validates output shape, bounds output and execution, and emits no raw stderr. Claude's cache and native retry behavior apply; the bridge never swaps modes. A returned API key has no Curator refresh token. | Rotate at the issuer. New launches call the helper anew; existing sessions see refresh according to cache/retry behavior. For immediate cutover, restart sessions. The issuer must not print a secret into error output or persist it in project files. |
| `per-home` | Preserve both Keychain and file state. Record the strategy as native-selected, with observed backend unknown unless a specific metadata-only observation establishes it. Do not move credentials when backend selection changes. | Claude performs refresh and writes its store; interactive re-login is required when refresh can no longer renew. Use the same config-directory path on relaunch. Renaming or moving a home can select a different Keychain item and needs an explicit plan. |
| `shared-file` | Never rotate, copy back or merge a credential. Recheck link identity, target kind/liveness and the exact capability before launch. | A detached regular file or failed metadata read refuses use and preserves both stores. Refresh qualification is a prerequisite, not a reason to repair by copying. |

Enrollment and rotation are separate operator actions, never side effects of profile install/resolve. A proposed protected-input enrollment command may accept the newly minted token from a no-echo terminal or private input stream; the command line contains only the source ID. Do not automate parsing `setup-token`'s terminal UI as a stable token-export API. This research does not invoke enrollment.

## Security considerations

The threat model includes accidental disclosure through plans/logs, a hostile profile repository selecting another source or executable, symlink and replacement races, stale source references, and credentials being sent to an unexpected endpoint. Trust belongs to the operator-owned source registry, the protected store, the validated launcher/provider binaries and explicitly selected helper. Source identifiers are references, not authorization: a forged fragment must not grant access to any Keychain item. Verify the mapping against the trusted machine state at use time.

Use restrictive ownership and permissions, no-follow reads and identity checks for registry/settings/helper paths. Avoid symlink-following TOCTOU checks followed by an unguarded open. Do not serialize resolved secrets in tracked plans or crash diagnostics; do not emit their hashes as proof. On errors, report the mode, neutral source ID and error category only. Public evidence excludes tokens, account identifiers, personal paths and raw operator settings.

An environment token is protected in transit from Curator's argv/logging paths but is accessible to the Claude process and potentially its child tools, hooks, MCP servers and same-user debugging facilities. These modes are not a sandbox or protection against a malicious executable already authorized to run as the operator. Before first-party token injection, refuse unqualified endpoint overrides; sanitize diagnostic paths and do not print environment snapshots. The launcher cannot promise that arbitrary child code will never print a credential it receives.

A helper is intentional code execution and a credential supplier. Its bridge must capture output privately, never forward raw stderr, bound response size and runtime, and ensure it is invoked only for an authorized source. The output format is a single nonempty printable-ASCII credential, at most 16 KiB after trimming, with no embedded whitespace; reject malformed output without echoing it. Cap bridge execution at 30 seconds for the initial contract. A helper's native five-minute cache is not a promise of immediate revocation.

## Compatibility and migration

Existing manager schemas, fragments and markers stay frozen. Reserve **manager-config-v4**, **launch-env-fragment-v4** and **agent-environment-marker-v4** for enactment; v3 already exists. Old consumers reject v4, and new consumers still accept the existing shapes. Coordinate release/pin promotion between spec, manager and launcher. No system-config bump is proposed because this draft adds no system-selectable source field; revise it only if the operator later chooses a new mode-enforcement policy.

Explicit adoption uses the existing inspect → plan → apply discipline. A plan compares non-secret settings, links and marker metadata, records the new mode/source reference, and preserves credential bytes. A source-only rotation updates the protected store without relinking the home. A mode change of a provisioned home requires a plan even if it creates no filesystem link. Refuse a regular file where a shared link would be needed, unreadable metadata, unexpected targets, and conflicting locks. Do not reset or log out a native/per-home account to make migration pass.

The compatibility path retains legacy macOS isolated-by-default behavior and Linux shared-file behavior, with their current evidence limits. Do not silently classify a legacy ambient API key as `token` or `helper`; mode adoption is explicit. The revised marker separates the declared source mode, source role, strategy, capability release and optional observation from actual authentication state. New per-home records must not assert `backend=keychain` solely from GOOS.

## Specification changes

Adopt CIP-0003 and a follow-on decision record referencing Decision 0017; preserve the historical observations.

1. **Q1 / environments §7.4:** split external injection from native-store sharing. Token/helper capability checks may be qualified independently; neither is a claim to share Claude's native login store. Keep macOS `shared-file` unavailable until the authorized disposable-account experiment proves read precedence, refresh write/link behavior and Keychain write conditions for the pinned release. Record 2.1.287 synthetic/static findings at their actual confidence. Amend the per-home description to allow native Keychain or file fallback.
2. **Q7 / manager credential boundary:** allow only an explicitly enrolled, operator-selected external credential to be read transiently by the launcher/bridge for the selected child. Curator materialization, resolution, repair, migration, backup and GC MUST NOT extract, copy, merge or export native or managed Claude credential material. This includes native Keychain-to-JSON export and refresh-token cloning. Secret waivers remain unrelated to credential-copy consent. Enrolling a fresh setup token is not permission to copy the existing login.
3. **Q2, Q5 and the original option-1 deferral:** retain bounded store separation, add the explicit selector/source-reference model and marker metadata, and replace the deferral of additional mode controls. Reconcile Q6's historical follow-up wording with rc.14's already-enacted isolation locks. Define the conflict rule above rather than silently weakening those locks.
4. **§§7.7, 7.9, 8.2, 8.4.1, 10, 12 and manager §§1, 12.4–12.5:** add the union, defaults, precedence, migration and capability tables; distinguish absent, unreadable, unsupported, source-conflict, store-denied and known-expired states. None may produce an authenticated claim or a fallback fragment. Define launch-reference provenance and final-executor obligations.
5. **Schemas and vectors:** source definitions live only in protected operator machine configuration. Fragment-v4 carries only `{mode, source_ref?}` plus a non-secret trusted-configuration binding; no helper body, store value, token-derived hash or arbitrary auth env assignment. Marker-v4 records metadata without credential bytes. The consumer independently verifies the binding instead of trusting caller-minted metadata. `passable_env_names` remains the MCP name surface and cannot authorize provider credential injection.

## Implementation plan

Sizes are relative: S is a bounded schema/docs leaf, M is a cross-module behavior leaf with production tests. These are consuming leaves, not additional serial research tasks.

| Order | Leaf | Size | Reviewable output |
| --- | --- | --- | --- |
| 1 | Spec and decision enactment | M | Closed unions, mode/store policy table, v4 schemas, negative vectors, Q1/Q7 amendments and exact version capability rules. Resolve the operator choices below here. |
| 2 | Manager resolution and migration | M | Config parser, effective selector, conflict handling, truthful status/marker, fragment-v4 and metadata-only inspect/plan/apply. No secret-store reads. |
| 3 | Direct launcher token slice | M | Real curator-run resolves trusted metadata, validates target/endpoint/policy, reads the dedicated Keychain item in process and spawns Claude with private env. A sentinel child proves the delivery and absence from artifacts. Include protected enrollment/rotation and error classification. |
| 4 | Helper bridge and per-home selection | M | Trusted helper command channel, stderr containment, bounded output/runtime, TTL, native policy/conflict checks and backend-neutral per-home records. |
| 5 | Tracked execution and qualification | M | Execution-host source-reference handling, no serialized token, retry/relaunch semantics and disposable-account verification of token/helper/per-home. Unknown executor capability refuses. |
| Conditional | Shared-file admission | M | Only if Q1's experiment supports it: versioned capability and link/refresh/concurrency conformance. Otherwise keep the mode refused; do not add a copy-back workaround. |

The draft names production call sites to extend: curator `internal/envprofile/managed.go:319` and `internal/envfragment/envfragment.go:54`; launcher `cmd/curator-run/main.go`, `internal/plan/plan.go:219`, `internal/composition/composition.go:75`, and `internal/execution/execution.go:117`. Work remains in the existing Go stack. [C1–C4, L1]

## Test plan

Tests below are **planned implementation/qualification work**, not results from this research. Current measurements and real exit codes are in the companion.

- Drive actual `curator env resolve` and `curator-run` entry points with a scratch HOME and synthetic source registry. Positive rows select all three supported modes, profile override versus environment default, and legacy compatibility. Negative rows cover wrong source kind, inline secrets, missing/denied stores, unreadable config, expired metadata, unknown mode/release, conflicting legacy locks and unsupported platform/executor.
- A real child reports only booleans proving the synthetic sentinel reached the intended environment or helper pipe. Search every produced argv, fragment, preview, tracked request, log and error artifact for that sentinel. Test direct and tracked paths separately; reject a forged source reference and a changed configuration binding before secret retrieval.
- Include ambient API key/bearer, helper, settings `env`, project/local/admin overrides, provider switches, gateway state, active Anthropic profile, `--bare`, injected FD/host channels and the undocumented secure-storage selector. Mutate the production conflict set to omit each class; the corresponding case must fail. Test reload behavior and report the boundary after startup explicitly.
- Helper cases include success, empty/multiline/oversized output, stderr containing the sentinel, exit failure, timeout, shell metacharacters in args, hostile cwd, late executable replacement, cache expiry, eligible 401/403, JWT expiry and background-refresh failure with a cached value. Verify no accidental switch to saved OAuth or inherited API auth.
- An authorized disposable **OS user and account**, outside the operator's login, performs initial login and a real inference turn; then tests the next launch, renewal, expiry/revocation, concurrent renewal, Keychain writable/locked/unavailable, file+Keychain conflicts and each backend transition. Record only neutral source labels, exits and metadata: paths relative to scratch, file kind/mode/inode/timestamps and service suffix. Do not export either Keychain value for comparison. In-process comparisons, if needed, emit booleans only. Distinguish failure to observe from absence.
- For shared-file, exercise the real refresh path and concurrent native/managed sessions. Observe whether the symlink survives and where new state is written; test regular-file replacement, dangling target, unreadable target and a TOCTOU replacement. A narrower capability/version gate mutant must be caught; deleting a gate alone is insufficient.
- Matrix: macOS direct/tracked for each admitted backend/release; Linux protected-store/helper/per-home qualification as separate capability rows; Windows new modes refused until its store/helper/ACL path is qualified. Include native file-refresh tests on Linux before upgrading legacy shared-file to verified. Unsupported rows must refuse without secret reads.

Report coverage as executed rows over the independent spec-derived matrix, not a list of passing helper unit tests. Q1 presently has **0/3 required disposable-account facts established by this run**. No product test suite or previously attached login evidence was replayed or accepted as a current-release pass.

## Open questions for the operator

1. **Default and rollout:** adopt `per-home` for newly opted-in macOS profiles, preserve legacy behavior until inspect → plan → apply, and allow `token`/`helper` overrides? **Recommend yes.** All three mechanisms remain available; no automatic login extraction is involved.
2. **Q7 boundary:** authorize dedicated setup-token enrollment plus transient final-executor injection, while native/per-home credential export and copying stay refused? **Recommend yes.** Without this narrow revision, the new launcher secret-read behavior has no normative authority.
3. **Conflicting ambient auth:** refuse explicit-mode launch when another source or endpoint can win, rather than accepting native precedence silently? **Recommend yes.** Preserve the legacy path for existing ambient setups; do not claim a mode that was not selected.
4. **Helper scope:** define `helper` as an external API credential mechanism, with the protected bridge and native cache behavior, rather than promise subscription-login equivalence? **Recommend yes.** Require fresh-account qualification before claiming any additional token kind.
5. **Shared-file and undocumented selector:** retain the Q1 gate and exclude `CLAUDE_SECURESTORAGE_CONFIG_DIR` from supported modes? **Recommend yes.** Run its approved disposable-account experiment only if shared-store support is still desired; token/helper delivery can proceed independently.
6. **Qualification access:** schedule an authorized disposable-account/OS-user check as part of implementation qualification, with no operator-account access? **Recommend yes.** Keep unmeasured capability rows unavailable rather than treating this research's synthetic status results as successful authentication.
