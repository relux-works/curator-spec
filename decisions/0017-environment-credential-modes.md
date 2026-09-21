# Decision 0017: environment credential modes

## Status

Status: adopted

Proposed 2026-09-16. DRAFT for review under TASK-260916-vht714,
STORY-260916-1on1d2.

Adopted 2026-09-21 by operator decision under TASK-260921-3qcjsy
(STORY-260921-3z0fgr): options 1–3 adopted as recommended below, and
open questions 1–7 resolved to the recorded choices in Adoption
choices. The normative amendments land in the same revision
(environments §7.4, §7.7, §8.2, §8.4.1, §10.1, §10.4; manager §12.4,
§12.5); the marker-schema extension, the fleet `isolated` policy, and
the manager implementation work are named follow-ups (Compatibility
and security impact).

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
adopted: options 1–3 adopted as recommended, open questions 1–7
resolved to the recorded choices.

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

All three options are adopted as recommended (2026-09-21).

1. **Keep `environments.isolation.<profile>.<env-id> = shared|isolated`
   (manager-config schema 2) as the canonical v1 knob.** Adopted as
   recommended. The review recommends this: the knob is already parsed,
   resolved, and locked
   (system map lockable only toward `shared`, whole-map replacement;
   environments §12.2, manager §1). It must be described as
   credential-store sharing, not a security sandbox. A new
   `environments.credential_mode.<env-id>` default, a rename to
   `environments.credentials.<env-id>.mode`, and a per-run credential
   flag are all deferred: the first two need compatibility, precedence,
   and lock migration for no present gain; a per-run flag risks silent
   credential-ownership migration of an existing home.
2. **Registry-owned strategies per environment × GOOS.** Adopted as
   recommended. The review recommends: `codex_cli` keyring-preferred →
   `auth.json` file-link
   (unchanged); `pi` file-link `auth.json` with the native root
   corrected to `~/.pi/agent` (the link path `auth.json` is right, only
   the native target is wrong); `claude_code` on Linux file-link
   (unchanged, expected-to-detach until refresh behavior is verified);
   `claude_code` on macOS keeps isolated-by-default with shared refused
   exactly as coded until the experiment below passes; `opencode`
   ambient only. Rejected: `keychain-shared` (no manager-linkable item
   exists; the same Keychain is not the same item) and copy-at-provision
   (contradicts the manager §12.4 no-copy boundary; see below).
3. **Fix-first manager repairs, then an explicit migration step.**
   Adopted as recommended. The two inspection-derived hazards (curator
   `18f05497`,
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

## Adoption choices

Open questions 1–7 resolved at adoption (2026-09-21). Each row states
the question and the recorded choice; normative sections carry the
choice where the Compatibility section says so.

| # | Question | Adopted choice |
|---|---|---|
| 1 | What is the supported macOS `claude_code` shared store, if any? | **Unsupported until the experiment is recorded.** No shared store is supported: `environment_shared_unsupported` stands, and the §7.4 residual is answered negatively (a 2.1.273 managed-home login wrote a file under `CLAUDE_CONFIG_DIR`, not a suffixed Keychain item). Gate for reconsideration: an authorized disposable-account experiment proving (a) which store Claude reads first when file and Keychain both exist, (b) whether the file is rewritten in place on refresh, (c) under which conditions, if any, a suffixed Keychain item is written. The manager never exports Keychain secrets to JSON. |
| 2 | Is `isolated` bounded store separation or strict account separation? | **Bounded store separation.** `isolated` means the managed home does not share the declared credential stores with the native home. It is not account separation (ambient auth — helpers, cloud credentials, auth variables, native selectors — is unchanged) and never filesystem isolation. Normative §7.4 and manager §12.4 say so. |
| 3 | Which Pi root wins when both `~/.pi/auth.json` and `~/.pi/agent/auth.json` exist? | **Native root `~/.pi/agent` (option 2).** Migration inventories both roots; on conflict the operator chooses and the bytes are preserved. The existing 2 B `~/.pi/auth.json` is a manager-created artefact of the wrong target: migration unlinks the recorded link, never deletes the native file. |
| 4 | Does Codex keyring identity depend on `CODEX_HOME`, and what do `auto`/`ephemeral` and a diverged `config.toml` mean for sharing? | **Keyring identity assumed operator-global; probe defined.** The manager assumes Codex keyring identity is independent of `CODEX_HOME` until the probe proves otherwise. Probe: a disposable-account launch with a scratch `CODEX_HOME` observing login state (logged-in ⇒ global; not-logged-in ⇒ per-home); secrets are never exported. Consequences (normative §7.4): under native `keyring` or `auto` storage `isolated` is `environment_isolated_unsupported` — `isolated` for `codex_cli` is available under `file` storage only, because under `auto` the file-link is inert on a keyring host and the home would authenticate through the operator-global keyring; a future revision may admit `auto` only where the manager proves the effective store is `file`, probe-gated. Sharing is defined by the native effective storage only — a diverged managed `config.toml` changes nothing and the manager never realigns configs; any selector outside the verified `file`/`keyring`/`auto` set (including `ephemeral`) fails closed with `environment_credential_unsupported`. |
| 5 | What marker and config fields carry mode, strategy, source role, backend/version, and provenance, and how are they published? | **Fields named; schema enactment is a follow-up.** Config: `isolation.<profile>.<env-id>` stays the only config field. Marker: each passthrough record carries `isolation` (effective mode), `strategy`, `source_role` (`native` = bytes owned by the native home, `managed` = bytes owned by the managed home), `backend` (`file`/`keychain`/`ambient`), `backend_version` (verified tool release), and `provenance` (`provisioned`/`repaired`/`migrated`); linkless strategies (macOS per-home-keychain under isolated, ambient) record without a path. A schema-1 marker records `path` and `strategy` only and is never rewritten to add the record. Publication is under the manager-home mutation lock via same-directory temp plus atomic rename with journal protection; rollback restores the preceding marker. Backups and discovery never follow auth symlinks (`lstat` semantics) and never archive credential bytes. The marker-schema extension is a named follow-up spec revision. |
| 6 | Can a fleet enforce `isolated`? | **Not in this adoption — follow-up.** The system schema still locks only toward `shared`; enforcing `isolated` fleet-wide needs a reviewed policy revision, not a knob reinterpretation. Named follow-up. |
| 7 | What consent shape, if any, authorizes a future credential copy? | **No consent shape authorized — copy stays refused.** No copy consent exists in this revision; `secret_material_waivers` waives an audited finding, never extraction. Any future copy needs operator-owned profile/env, source/destination roles, purpose, reason, and expiry, plus an explicit revision of the no-copy boundary. |

## Compatibility and security impact

Adoption touches environments §7.4 (Pi native root, keyring-identity
assumption, the credential-record content the follow-up marker
revision defines, migration rule, the §7.4 residual answered
negatively), §7.7 (`environment_credential_conflict` and
`environment_credential_unsupported` diagnostics), §8.4.1 (passthrough
absence row), §10.1 (repair conflict rule, never-silent migration),
§10.4 (conflict row), and manager §12.4 (the conflict rule replacing
the implicit remove) and §12.5 (repair mirror), with §8.2 and
§12.1/§12.2 unchanged — a schema-1 marker records `path` and
`strategy` only.
No seed, adapter, or runtime behavior changes beyond the repair
refusals above. Frozen v1 protocol schemas stay untouched; the
marker-schema extension is a follow-up spec revision, as is the fleet
`isolated` policy (choice 6). The manager implementation — fix-first
repairs, the explicit migration step, and production-entry tests
against a temporary store, with narrowing mutants per refusal — is a
curator follow-up leaf. The boundary stands:
**the manager never copies credential material and never exports
Keychain secrets into JSON**; `secret_material_waivers` is not
credential-copy consent; `passable_env_names` bounds MCP env-name
passthrough only, not inherited provider credentials; `checkPassthrough`
attests link identity, never authentication. Later tool versions need
versioned capabilities; unknown backends and unknown storage selectors
fail closed.
