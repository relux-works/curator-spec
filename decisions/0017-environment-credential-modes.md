# Decision 0017: environment credential modes

## Status

Status: proposed — not adopted

Proposed 2026-09-16. DRAFT for review under TASK-260916-vht714,
STORY-260916-1on1d2. No option is selected.
Filing this proposal authorizes no implementation, workaround, normative
amendment, or landing of the draft.

Numbering: the existing decision series ends at 0016; 0011 remains
reserved as recorded in Decision 0013. This filing uses the next two
unused numbers, 0017–0018.

## Context

[Environments 1.1](../protocol/environments.md) §7.4 declares, per
environment, the closed credential-passthrough set a managed home shares
with the native home, its passthrough strategy, and the pinned write
behavior the strategy answers to. The default per profile × environment
is `shared`; `isolated` is a configuration error (`environment_isolated_unsupported`)
for `opencode` and for `claude_code` on macOS below 2.1.261, while for
`claude_code` on macOS at or above 2.1.261 the restriction is inverted:
`isolated` is the platform default by construction (the tool selects the
login-Keychain item by `CLAUDE_CONFIG_DIR`) and a configured `shared` is
the configuration error `environment_shared_unsupported`. Section 7.4
records one residual: that a fresh login inside a managed home writes the
suffixed Keychain item and nothing else "requires an operator to confirm
with a real login". [Manager](../profiles/manager.md) §12.4 states the
manager-side credential obligations, including that general repair leaves
credential bytes untouched.

The design input is the Fable-reviewed research on board task
TASK-260916-2timlf: the outcome resource
`TASK-260916-2timlf_report.md` (Astra research report, 2026-09-16),
the outcome resource `TASK-260916-2timlf_review-verdict.md`
(independent review, VERDICT ACCEPT with corrections, whose §3/§4 are
authoritative where they differ from the report), and the outcome
resource `TASK-260916-2timlf_native-help.txt` (pinned `--help`
captures). Citation checkouts are curator `18f05497`, curator-spec
`a68854d`, curator-agent-launcher `b34e1e2`, skill-agents-management
`7f0b6bc`, and relux-agents-infra-main `459742ea`; host evidence is
Darwin 24.6.0 with installed Claude 2.1.273, Codex 0.153.4, Pi 0.84.2.
The onboarding evidence is the outcome resource
`TASK-260908-yl5x3k_onboarding-evidence-rev2.md` on TASK-260908-yl5x3k
(B5). The verdict's FINAL recommended design (§3) is recorded below as
a proposal, not an adoption.

Host observations carried into this draft. B5: Claude prompt exit 1
("Not logged in", empty passthrough); Codex prompt exit 0 with an
`auth.json` link; Pi prompt exit 1 (no Anthropic key; recorded
two-byte store, contents not dumped). A metadata-only re-check (exit 0,
no auth contents read): Claude passthrough `[]` with seed
`.claude.json`; Codex `auth.json` file-link with seed `config.toml`;
Pi `auth.json` file-link; native sizes 509 B (Claude JSON), 3864 B
(Codex JSON), 2 B (`~/.pi/auth.json`), 127 B (`~/.pi/agent/auth.json`).
The managed Claude home on the host holds a `.credentials.json` file
(mode 0600, 819 B, mtime 2026-09-16 04:30, the operator's `/login`
inside `curator run claude_code`); the login Keychain holds exactly one
`Claude Code-credentials` item (account `administrator`, created
2026-07-08, last modified 2026-08-17 — untouched by the 04:30 login);
no `Claude Code-credentials-<8hex>` item exists; the native
`~/.claude/.credentials.json` (509 B, mtime 02:17) also exists. The
§7.4 residual is therefore answered NEGATIVELY on this host at 2.1.273:
the managed-home login produced a file under `CLAUDE_CONFIG_DIR`, not a
suffixed Keychain item. The cause is unknown. The string
`CLAUDE_SECURESTORAGE_CONFIG_DIR` in the installed Claude binary proves
string presence only, not semantics or support.

## Gap statement

The knob exists but the design around it is incomplete: the macOS
`claude_code` shared strategy has no verified store now that the
suffixed-Keychain residual is answered negatively; the `pi` native root
is wrong (Curator links `~/.pi/auth.json` while Pi 0.84.2 stores tokens
in `~/.pi/agent/auth.json`); two credential-migration hazards in the
manager are unverified by any production-entry test; the marker records
no mode or strategy (`isolation: None` on the host marker); and the
no-copy boundary has no explicit consent shape for any future copy.

## Options and trade-offs

1. **Keep `environments.isolation.<profile>.<env-id> = shared|isolated`
   (manager-config schema 2) as the canonical v1 knob.** The review
   recommends this: the knob is already parsed, resolved, and locked
   (system map lockable only toward `shared`, whole-map replacement;
   environments §12.2, manager §1). It must be described as
   credential-store sharing, not a security sandbox. A new
   `environments.credential_mode.<env-id>` default, a rename to
   `environments.credentials.<env-id>.mode`, and a per-run credential
   flag are all deferred: the first two need compatibility, precedence,
   and lock migration for no present gain; a per-run flag risks silent
   credential-ownership migration of an existing home.
2. **Registry-owned strategies per environment × GOOS.** The review
   recommends: `codex_cli` keyring-preferred → `auth.json` file-link
   (unchanged); `pi` file-link `auth.json` with the native root
   corrected to `~/.pi/agent` (the link path `auth.json` is right, only
   the native target is wrong); `claude_code` on Linux file-link
   (unchanged, expected-to-detach until refresh behavior is verified);
   `claude_code` on macOS keeps isolated-by-default with shared refused
   exactly as coded until the experiment below passes; `opencode`
   ambient only. Rejected: `keychain-shared` (no manager-linkable item
   exists; the same Keychain is not the same item) and copy-at-provision
   (contradicts the manager §12.4 no-copy boundary; see below).
3. **Fix-first manager repairs, then an explicit migration step.** The
   two inspection-derived hazards (curator `18f05497`,
   `internal/envprofile/managed.go`): (1) shared → isolated does not
   remove the old credential link — `effectivePassthrough` returns empty
   (:500-502), `finalizeMarker` loops over new links only (:934-942),
   the removal set comes from marker surfaces only (:1670-1677), and
   `checkPassthrough` compares recorded vs effective sets only
   (:1342-1345) — so sharing can survive behind an isolated
   configuration; (2) `finalizeMarker` unlinks the wanted-link path
   before symlinking (`_ = os.Remove(full)` at :936) without
   credential-specific preservation, contrary to the
   leave-bytes-untouched promise (manager §12.4). The review recommends:
   unlink only a recorded symlink still targeting the declared native
   store (preserve native bytes; refuse on a detached or regular file),
   refuse with a credential-conflict diagnostic instead of removing a
   regular file at a link path, record `isolation` and strategy per
   marker entry, and run migration as an explicit inspect → plan → apply
   step under the manager lock — never silent inside `resolve --repair`
   — that inventories the old marker, link targets, and both Pi roots,
   preserves the effective mode on upgrade, and lets the operator choose
   the account on isolated → shared conflicts. No secret copies at any
   step. Neither hazard was reproduced live; each needs a
   production-entry test against a temporary store.

## Open questions

1. What is the supported macOS `claude_code` shared store, if any? Gate:
   an authorized disposable-account experiment proving (a) which store
   Claude reads first when both file and Keychain exist, (b) whether the
   file is rewritten in place on refresh, (c) under which conditions, if
   any, a suffixed Keychain item is written. Only then may
   `environment_shared_unsupported` be reconsidered. Secrets are never
   exported from Keychain to JSON by the manager.
2. Is `isolated` bounded store separation or strict account separation
   including ambient auth (helpers, cloud credentials, auth variables,
   native selectors)? The review recommends the bounded store meaning
   pending a full auth-source contract; never filesystem isolation.
3. Which Pi root wins when both `~/.pi/auth.json` and
   `~/.pi/agent/auth.json` exist? Inventory, operator choice, and
   preservation — the existing 2 B `~/.pi/auth.json` is a
   manager-created artefact of the wrong target and must be handled by
   migration (unlink the recorded link, never delete the native file).
4. Does Codex keyring identity depend on `CODEX_HOME`, and what do
   `auto`/`ephemeral` and a diverged `config.toml` mean for sharing?
   The host proves file mode only.
5. What marker and config fields carry mode, strategy, source role,
   backend/version, and provenance, and how are they published
   atomically with rollback and journal protection? General backups must
   not follow auth symlinks or archive credentials.
6. Can a fleet enforce `isolated`? The current system schema locks only
   toward `shared`; that needs a reviewed policy revision, not a knob
   reinterpretation.
7. What consent shape, if any, authorizes a future credential copy?
   `secret_material_waivers` (environments §7.5) waives an audited
   finding, never extraction; any copy consent needs separate
   operator-owned profile/env, source/destination roles, purpose,
   reason, and expiry — and an explicit revision of the no-copy
   boundary. This increment recommends no copying.

## Compatibility and security impact

No schema, seed, adapter, or runtime behavior changes. Adoption would
touch environments §7.4 (Pi target, marker fields, migration rule, the
§2.1 residual outcome), §7.7 (diagnostics), §10.1 (repair), with
§12.1/§12.2 unchanged, and manager §12.4 (the conflict rule replacing
the implicit remove). Frozen v1 protocol schemas stay untouched;
marker/config changes are manager-config schema 2. The boundary stands:
**the manager never copies credential material and never exports
Keychain secrets into JSON**; `secret_material_waivers` is not
credential-copy consent; `passable_env_names` bounds MCP env-name
passthrough only, not inherited provider credentials; `checkPassthrough`
attests link identity, never authentication. Later tool versions need
versioned capabilities; unknown backends fail closed.
