# Changelog

All notable protocol changes are recorded here. Versions follow Semantic
Versioning for the complete specification set.

## Unreleased

### Added

- STORY-260916-1ll22r: absence-versus-read-failure discipline stated once
  (environments §1.1/§1.3/§4/§7.1/§7.3/§7.4/§7.5/§7.6/§7.7/§8.2/§8.3/§8.4/
  §9.4/§9.5/§9.6/§10.1/§10.4/§11/§12/§13, manager §12.2/§12.5/§12.7): new
  §8.4.1 states the general rule once — a failed read, stat, or parse of
  any state or surface file is never reported as absence and never triggers
  an absence-shaped action — with a closed table of the unreadable outcome
  per file class (marker, lock, ledger, backup record, provisioning seed,
  passthrough entry, recorded surface, inventory candidate); every read-site
  section references the rule instead of restating it. New diagnostic
  `environment_passthrough_unreadable` for a recorded passthrough entry
  whose link state cannot be established (status and resolve report it
  non-current with currency unknown; `--repair` leaves the entry untouched);
  lock read/parse failures are entry-class `environment_store_untrusted`,
  never `profile_unknown`, and are never rebuilt from — no mutating
  operation rebuilds, re-materializes, or replaces anything from an
  unreadable lock (recovery is an explicit operator action). New diagnostic
  `environment_backup_record_unreadable` for a backup inventory that cannot
  be listed or read (status reports it non-current with currency unknown;
  restore, scrub, and retention pruning stop before mutating). Conformance
  vectors in `vectors/environments-read-failure.json` (unreadable-but-present
  markers, locks, seeds, passthrough entries, and backup records across the
  applicable failure classes, repair/update no-rebuild cases, absence-side
  positives, and absence-shaped negatives), checked by
  `validate_environments_read_failure_vectors`. Rollout is direct
  (correctness of an existing MUST).
- S1/S3: hardened-defaults profile and the named advisory revocation
  residual (manager §1/§7.1/§10/§12.7, registry §4/§8, SECURITY.md,
  environments §2.1/§2.2/§9.7/§10.3/§10.4/§12/§12.1/§13): one closed
  machine knob `security_posture` (`permissive` or `hardened`, top level
  in `manager-config-v2`, lockable in `system-config-v2` only in the
  direction of `hardened`; schema-1 managers run `permissive`). Under
  `hardened` the effective defaults are `audit.mode: strict`,
  `audit.registry_policy: strict`, `transitive_system_modules: error`,
  and `require_source_signers: true`, while an empty `allowed_sources`
  (`source_allowlist_empty`), an empty `mcp_package_allowlist` for a
  profile carrying an MCP declaration (`mcp_package_allowlist_empty` as
  an error instead of the warning), and an explicit `passable_env_names:
  null` (`passable_env_names_unbounded_refused`) are refused at
  install/update however the value arrived; an explicit per-knob value
  otherwise still wins over the profile default. Warn-first in two
  labelled revisions: revision A admits the knob with default
  `permissive` and warns `security_posture_permissive` once per
  operation with the migration hint; revision B flips the default to
  `hardened`. `curator status` and `env status` carry the
  `security_posture` header row plus thirteen rows, one per gate, with
  the effective value and its provenance (`profile`, `explicit`, `lock`,
  `shipped`) — the thirteenth row is the E3 codex-seed shipped revision
  (`A` or `B`, environments §7.4), directly after
  `update-confirmation`; the per-home `codex_seed_record` rows stay
  outside the posture inventory; `--check` treats a `hardened` machine
  whose effective values contradict the profile as non-current.
  Registry §4 and
  SECURITY.md state the S3 residual — under `advisory` policy revocation
  is network-dependent for up to the offline grace — and managers
  surface an unreachable trusted registry during install/update as the
  prominent gate notice `registry_unreachable_during_install` (warning
  under `permissive`, error under `hardened`), naming the artifacts
  resolved without registry evidence; the routine per-query warning is
  unchanged. Conformance vectors in
  `vectors/security-posture.json` (effective defaults under each
  posture, explicit-vs-lock precedence, the three refusals, the
  revision-A warning, the warning-vs-error notice, posture rows),
  checked by `validate_security_posture_vectors`.
- E6: `path`-kind admission rule and the store-boundary extension to
  `path` source directories (Decision 0012 amendment 2026-09-18;
  environments §1/§2.1/§2.2/§3/§4/§6/§8.5/§9.6/§10.1/§10.4/§12/§13): MCP
  declaration packages MUST resolve from `git` sources — a declaration
  carried by a `path`-kind root, overlay, or onboarding import is refused
  at resolution with the new error
  `mcp_declaration_path_source_refused` naming the package and the
  declaration, never admitted and never warned-through — because a `path`
  source has no canonical identity for the MCP package allowlist and is
  never verified (E1), which makes the allowlist total over canonical
  identities. A `path` source may carry `class: system` modules only when
  directly named (a root or overlay, the E2 direct-naming rule applying as
  is) AND only after its directory passes the §4 protected-boundary
  contract — ownership, private permissions or DACL, containment below the
  declared directory, regular file types, link safety — at every resolve
  and before any materialization, exactly like a store entry; a `path`
  source that fails it is entry-class `environment_store_untrusted` (no
  fragment, non-current, posture row naming the path and the failing
  check) with no rebuild — the source is the operator's directory, the
  operator fixes it — while its `state_sha256` pin remains the integrity
  baseline for its store entry and no pin is recomputed against the live
  directory. `path` overlays and onboarding imports without system modules
  are admitted as today but pass the same contract: the check is on the
  directory, not on the content class. Rollout is direct, not warn-first
  (impact row "E6": under the hood): no knob. Conformance:
  `vectors/environments-path-kind-admission.json` (the `git` MCP
  positive, the `path` root/overlay/import MCP refusals, the admitted
  `path` overlay with a system module, the admitted `path` root,
  overlay, and import without system modules, the boundary-check
  refusals with their posture rows — one per check plus no-system
  overlay and import refusals — the transitive `path` module refused by
  E2's rule, the dry-run cases reporting `environment_store_untrusted`
  with no rebuild planned for a `path` directory failure, and
  negatives), checked semantically by `tools/validate.py`.
- E5: nofollow write discipline for managed-surface writes (environments
  §8.3.1, with pointers from §5/§5.8/§7.5/§8.1/§8.4/§9.5/§10.1/§12/§13
  and the manager profile §12.2): every materialization, takeover,
  repair, or backup write to a managed surface in any mode, a backup,
  the marker, or the adapter ledger replaces the directory entry —
  operation-private temp file plus rename — and MUST NOT follow a
  symlink at the target path or at any path component below the managed
  root that the manager did not create in this operation
  (`O_NOFOLLOW`-class open, `lstat`-class inspection). A manager-owned
  target link is replaced as an entry; the §9.5 foreign-manager stop
  keeps its disposition, with an authorized takeover backing up the
  link itself (same link text, never dereferenced) before replacing
  the entry; any other unowned target link follows the ledger rule
  (`environment_surface_unmanaged_conflict` unless a takeover
  authorization covers the path). One new diagnostic,
  `environment_write_would_follow_link`, refuses writes that would
  traverse a non-manager link below the managed root, or open through
  one at a backup, marker, or ledger destination — no takeover flag
  authorizes traversal. `env status` reports link-blocked paths as
  non-current rows naming the path. Direct rollout, under the hood: a
  tampered or symlinked target now yields a refusal or an
  entry-replacement, never a write through. Conformance vectors in
  `vectors/environments-write-nofollow.json` (authorized-takeover
  replace, unauthorized stop, symlinked-parent refusals under both
  authorization states, planted-link and manager-owned-link repairs,
  backup-destination refusal, inside-link ledger refusal, clean-path
  and recorded-file positives — every foreign-link case asserting the
  link's former target is byte-identical afterwards), checked
- S5: protected-boundary contract for the environments root and profile
  store (environments §4/§1.3/§8.2/§8.4/§8.5/§10.1/§10.4/§12/§13,
  manager §12.2/§12.5/§12.7), mirroring core §9.3: the environments root
  and every store entry are protected state — manager-created,
  manager-protected, resolved independently of package input. On every
  `env resolve`, and again under the manager-home mutation lock for every
  mutating profile operation (install, update, use, sync, repair,
  garbage collection), the manager MUST verify ownership, private
  mutation permissions or DACL, containment, regular file types, and link
  safety (`lstat`, no symlink at the root, the entry root, or any
  component the manager did not create) for the environments root, the
  profile store root, the lock and marker files, and every store entry
  the lock names; link-target identity is necessary but no longer
  sufficient currency at resolve. Store integrity is verified against the
  pin, not the marker: resolve recomputes every named entry's tree hash
  from its bytes and requires equality with the pin (`git` tree identity,
  `path`/`local` `state_sha256`), with no marker required and before any
  provisioning or repair, at O(store entry bytes named by the lock) —
  missing hashes never pass — so a same-user byte swap of a
  system-prompt or root-context file (or any entry file) is detected even
  for an unprovisioned home. Home currency is separate: a marker that
  belongs to another lock is `environment_home_stale` repaired from the
  verified store, never `environment_store_untrusted`; an absent marker
  is unprovisioned while an unreadable or malformed marker is
  `environment_marker_unreadable` (never "absent"). Two failure classes
  in order (enclosing boundary → entries → pin hashes → home currency):
  an enclosing boundary (environments root or store root) that cannot be
  proven refuses every resolve and every mutating operation before its
  first write with nothing rebuilt (operator repairs out of band), while
  an entry-class failure (store entry, lock, marker) inside a proven
  enclosing boundary is `environment_store_untrusted` (error): resolve
  emits no fragment, status is non-current, `env status` reports the row
  naming the failing check and the boundary; a real operation rebuilds a
  `git` entry from the revalidated snapshot into newly established
  protected state via operation-private staging and atomic publication (a
  `path` or `local` entry has no second copy, so repair fails with
  `environment_repair_failed` and the operator reinstalls); dry-run
  evaluation of an entry-class failure reports
  `would-rebuild-untrusted-store` and mutates nothing, while dry-run of
  an enclosing failure reports `environment_store_untrusted` with no
  rebuild planned. Repair re-applies only from entries that passed the
  contract and the pin hash, so `env resolve --repair` is not persistence
  for a tampered store (audit note E7). Rollout is direct, not warn-first
  (impact row "S5"): no knob — the contract is not configurable.
  Conformance: `vectors/environments-store-boundary.json` (intact
  resolve, swapped bytes, symlinked root, ownership, permissions,
  containment, non-regular, and pin-hash refusals, enclosing-root and
  store-root refusals with no rebuild, intact-old-marker stale repair and
  swapped-old-marker untrusted, unprovisioned intact/swapped,
  unreadable-marker, the entry-class dry-run outcome and the enclosing
  no-rebuild case, repair rebuild/entry-rebuild/enclosing-refusal/stale/
  unprovisioned, the non-current posture rows, and negatives), checked
  semantically by `tools/validate.py`.
- E3: the `codex_cli` provisioning seed stops inheriting native
  `mcp_servers` (environments §7.4/§7.7/§7.8/§8.2/§12/§13): a whole-copy
  seed runs every native MCP server outside the profile lock and the
  §2.2 allowlist while `claude_code` runs only the profile set, so the
  seed rule ships in two labelled revisions — revision A (warning
  release, ships first) still copies `config.toml` whole but provisioning
  warns `mcp_native_servers_ungoverned` naming every inherited entry with
  the migration hint (declare the server in the profile's MCP set, or
  accept the loss), and revision B (flip release) copies every top-level
  member except `mcp_servers` and reports the stripped names once with
  `mcp_native_servers_not_inherited`. Both revisions write the marker
  `codex_seed_record` (`revision` exactly `A` or `B`, `native_mcp_servers`
  the provisioning-time name snapshot, names only); a managed `codex_cli`
  home whose marker predates the rule — and a revision-A home now served
  by a revision-B manager — reports `mcp_seed_unstripped` (warning) with
  the re-provision hint, and existing homes keep their bytes. `env status`
  reports the active codex-seed revision with its behaviour and, per
  managed `codex_cli` home, the record with the native entries listed as
  ungoverned (revision A, including an A-record home under a B manager)
  or not inherited (revision B); all three rows are warnings and never
  make a row non-current. §7.8 gains the closed per-adapter residual
  table (what each channel does to the home's own MCP configuration).
  Conformance vectors in `vectors/environments-codex-seed.json`
  (provisioning under both revisions, the no-server and empty-table
  negatives, the pre-rule-home and the A-home-under-B-manager
  `mcp_seed_unstripped` postures, and the non-codex negative), pinned by
  the `validate_environments_codex_seed_vectors` gate. Manager/README follow-up
  (`TASK-260916-33abdk`): a managed codex home runs only the profile MCP
  set; native `~/.codex/config.toml` servers are not inherited.
- E1: per-source signer allowlist and `profile update` delta confirmation
  (Decision 0012 amendment 2026-09-17; environments
  §1.1/§1.3/§1.4/§9.2/§9.7/§12/§12.1/§12.2/§13): the new closed machine knob
  `source_signers.<source>` maps a canonical source identity to its signer
  allowlist — entries `{ type: "ssh", key }` (OpenSSH public key line) or
  `{ type: "gpg", fingerprint }` (exactly 40 uppercase hex characters),
  default empty — and
  `require_source_signers` (boolean, default `false`) requires every `git`
  source to carry one. Both are lockable; a locked `source_signers` map is
  fleet policy per source (the machine file adds signers only for sources
  the lock does not name), and `require_source_signers` locks only to
  `true`. Resolution verifies the selected candidate's annotated tag
  signature OR the commit signature against an allowed signer before the
  candidate enters the lock — either suffices, exact `tag`/`revision`
  selections included — and fails closed with `context_source_unsigned`,
  `context_source_signer_rejected`, or `context_source_signers_missing`,
  never falling through to a lower candidate; `path` sources are never
  verified. `env status` reports the per-source posture (`enforced` with
  the verified signer, `unconfigured`, or `required-missing`) with the
  machine-level `require_source_signers` value, and the active
  update-confirmation revision (`A-warning` or `B-flip`) with its
  behaviour. `profile update` prints the resolved-version delta
  (`lock-delta` added/removed/moved lines with pins) before the lock is
  published; when the delta introduces or changes a `class: system` module
  or an MCP declaration — a moved `mcp` member triggers on any byte
  difference of its declaration's CCJ-1 form, `url` and `environments`
  selector included — revision A warns with
  `profile_update_system_delta` (carrying the migration hint) and
  proceeds, while revision B refuses with
  `profile_update_confirmation_required` unless the per-run flag
  `--confirm-system-delta` is given — no configuration knob may
  pre-confirm, `profile install` takes the same flag on its reinstall
  path, and `--all` confirms every profile of the run with one flag.
  An `ssh` allowlist entry matches by key type plus key material; the
  trailing comment is not part of the identity. Warn-first rollout in two
  labelled revisions: revision A ships first, revision B flips to refusal.
  `latest` stays `*`: with an allowlist it follows every signed in-range
  tag of that source, without one it follows any tag. Conformance vectors
  in `vectors/environments-source-signers.json` (verification, merge,
  posture, delta, reinstall, update-confirmation-posture, and `--all`
  cases) with schema cases for both knobs; the lock schema is unchanged —
  verification results are posture, not lock content.
- R3/P2: the restore-checkpoint enforcement point is the startup checkpoint
  comparison (registry-service profile §5/§6/§9/§10/§11, registry protocol
  §5): a conforming service accepts an operator-supplied signed
  `registry-snapshot-v1` checkpoint at start and, AFTER the §5 startup
  integrity verification and BEFORE it binds its listener or reports ready,
  verifies the checkpoint signature against its accepted signing keys (the
  staged rotation set) and compares the live boundary with it. A failed
  signature refuses with `checkpoint_signature_invalid`; a live
  `version`/`log_size` below the checkpoint refuses with
  `restore_below_checkpoint`; an equal version with a different `head`,
  `merkle_root`, or `log_size` refuses with
  `restore_inconsistent_with_checkpoint`; a live state above the checkpoint
  serves only when the live log reproduces the checkpoint boundary at its
  `log_size` (head and Merkle root at that prefix), otherwise
  `restore_inconsistent_with_checkpoint`. A refusal is non-ready with
  writes disabled and no automatic truncation or repair — the operator
  recovers the missing verified suffix or the service stays unavailable —
  and `/health` reports `503` like a failed §5 verification (the
  `health-response-v1` schema is unchanged). Without a configured
  checkpoint the service starts with no behavior change but MUST record the
  `checkpoint_not_configured` posture in startup diagnostics and the audit
  log; with one they carry the compared boundary (`version`, `log_size`,
  `head`) and the outcome. The offline `verify-backup`-style comparison
  stays as the operator procedure for vetting candidate backups; the
  startup comparison is the normative "before the service becomes ready"
  gate. Rollout is direct, not warn-first (impact row "R3/P2"): no knob,
  no behavior change without a checkpoint. Conformance: `checkpoint_cases`
  in `vectors/registry-service.json` (below-live consistent, equal
  consistent/inconsistent, live below, above with prefix mismatch, bad
  signature, not configured), generated by `tools/generate-vectors` and
  recomputed by `tools/validate.py`. Specified for
  `STORY-260910-35tbgb`.
- S6: shell-hook project env trust gate (manager profile section 8):
  the cached hook sources only `.agents/env.sh` / `.agents/env.ps1`
  bytes whose digest the manager recorded (`manager`) or the operator
  approved once (`curator hook approve <path>`); an unknown file, or a
  recorded file whose digest changed, warns once per shell session with
  `shell_hook_env_unapproved` / `shell_hook_env_changed`, naming the path
  and the approval command, and continues. Approval records
  `{ path, sha256, approved_by: manager | operator, approved_at }` live
  in manager-home shell-hook approval state below `<manager-home>`,
  outside every profile/package/project surface and never read from
  package, project, or profile data; `sha256` is lowercase hex SHA-256
  over the exact bytes sourced; re-approval is required after a change.
  `curator hook approvals` lists records read-only and
  `curator hook revoke <path>` removes one; `curator status` and
  `curator env status` report each known file as approved, unapproved, or
  changed. Warn-first rollout in two labelled revisions: Revision A
  (`A-warning`, warning release, old sourcing kept with the warning and a
  migration hint naming the approval command, shipped first), then
  Revision B (`B-enforcing`, flip release, unapproved/changed files are
  not sourced). Vectors:
  `conformance/v1/vectors/shell-hook-trust.json` (approved, unapproved,
  and changed files under both rollout profiles for both env files, with
  byte fixtures, exact manager-state records, a forged project-supplied
  record the hook must ignore, and the §8.7 downstream execution
  binding).
- Opt-in Skillfile sources revision 1: backwards-compatible project schema 2,
  local/Git acquisition, individual and collection selection, frozen package
  identities, physical input/output guards and full runtime/build contracts.
- Separately scoped repository transport revision 1 with stable identity and
  bounded operator-owned endpoint/authentication policy. Draft schemas and
  conformance vectors are isolated from rc.9 release artifacts; no manager
  implementation or release qualification is claimed.
- Repository transport revision 2 (unreleased, opt-in): non-default endpoint
  ports, operator-declared mirrors with exact-key `mirror_of` attestation and
  operator-declared host aliases via source-policy schema 2, an additive
  superset of unchanged schema 1. Canonical `host/path` stays the only portable
  identity; new fail-closed classes `repository_mirror_undeclared` and
  `repository_alias_unknown`; draft schemas and conformance vectors are
  isolated from rc.9 release artifacts; no manager implementation or release
  qualification is claimed.
- Amended draft Decision 0018 (proposed — not adopted, no normative
  change): the `curator run` permission mode is configured (launcher
  `defaults.json` v2 member, environments §12.1 per-profile knob, CLI
  `--permissions` override) with built-in default `yolo` for
  interactive launches (`native` for headless/CI/tracked silence),
  precedence flag > profile > global > default, a §12.2
  force-`native` lock, provenance
  `source=flag|profile|global|default-interactive|default-headless`,
  and fail-closed legacy policy/lock transport
  (`permission_policy_unsupported`); mapping, refusals, and the
  tracked-mode outcome are unchanged.
- E2 direct-only `class: system` modules (environments §3/§5.5/§12.1/§12.2):
  only the system modules of direct packages — the root itself, an active
  overlay, or a package named by the root's or an active overlay's
  `requires.contexts` entry — plus transitive packages admitted by the new
  closed machine knob `system_module_waivers` (list of `{ package, reason }`,
  default empty, not lockable) enter the system-prompt output and the
  launch-fragment `system_prompt` section. The new closed knob
  `transitive_system_modules` (`drop` default, `error` opt-in; lockable to
  `error` only) selects the refusal shape: `drop` skips a transitive module
  at materialization with the warning `context_system_module_dropped`
  naming package and module, while `error` fails resolution with
  `context_system_module_transitive` naming package and module. The default
  `drop` policy is non-breaking — resolution, installation, and update never
  fail for admission — so no warn-first split applies. `env status` gains
  the posture row reporting the effective policy with every dropped module,
  `context-system-module-present` stays the always-warn finding over every
  member, and the Decision 0013 `works.relux.curator.system-modules` key
  keeps refusing `ax` resume on drift. Conformance vectors cover direct,
  transitive-drop (byte-exact), transitive-error, waiver, and overlay-edge
  cases, with schema cases for both knobs.
- Manager CLI environment operands accept `claude` and `codex` as aliases of
  the canonical `claude_code` and `codex_cli` ids (manager profile §12.1):
  `env resolve`, `profile use --env`, and `env unmanage --env` normalize an
  alias to the canonical id before validation or lookup; outputs,
  diagnostics, markers, fragments, configuration records, and locks keep the
  canonical id and aliases are never persisted, while any other unknown
  spelling keeps the `environment_unknown` refusal. The launcher's `curator
  run <env-id>` follows the same rule under the launcher SPEC
  (curator-agent-launcher README). No schema, vector, or wire change; frozen
  v1 bytes untouched.
- R1/P1: records and log pages carry their committed snapshot boundary
  (registry protocol §5/§9 with new §9.3, registry-service profile
  §2/§5/§10/§11): every `/v1/records` GET and `/v1/log` success page
  carries a REQUIRED `boundary` member holding the complete signed
  snapshot (`registry-snapshot-v1`, all fields including `sig`) at which
  the page was evaluated, and all pages of one cursor chain carry a
  byte-identical boundary. The wire moves to the new
  `records-response-v2` and `log-response-v2` envelopes (v1 fields plus
  `boundary`, `additionalProperties: false`); the v1 schemas stay
  byte-frozen and a client validating v1 treats `boundary` as ignorable.
  Before a page contributes records, a conforming client verifies the
  boundary signature (§2), applies the §5 rollback rules to it —
  below-high-water and equal-version-different-body rejected as
  `registry_page_boundary_stale`, a higher version advancing the
  high-water exactly like an accepted snapshot — and requires every page
  of the chain to carry the first page's boundary
  (`registry_page_boundary_mismatch`). A page without a valid boundary
  is reported as `registry_page_boundary_missing`, naming the registry
  URL, and the registry contributes no record for that operation.
  Rollout is direct, not warn-first (impact row "R1"): no
  legacy-accept mode, no knob. Service side (P1): a cursor is bound to
  its first page's boundary; serving it at a differing boundary refuses
  `404 invalid_cursor`, and the service never re-evaluates a cursor at a
  newer boundary. The boundary is the stated page inclusion evidence;
  log replay stays optional as the independent re-derivation of a
  boundary's claims. Read-only status reports, per trusted registry,
  the persisted high-water (`version`, `log_size`) and whether the last
  page boundary was verified. Conformance: `page_boundary_cases` in
  `vectors/registry-client.json` (fresh advance, equal accept/reject,
  stale, mismatch, missing, bad signature) and boundary emission plus
  cursor-boundary-disagreement cases in
  `vectors/registry-service.json`, with v2 schema cases. Specified for
  `STORY-260910-25yc0h` with `STORY-260910-3rvvxh`.
- S2: signed bootstrap checkpoint interchange and the TOFU/equivocation
  residuals (registry protocol §2.1/§5 with new §5.1/§8/§10,
  registry-service profile §10, manager profile §1/§10, SECURITY.md): a
  registry entry MAY carry `bootstrap_checkpoint`, a path to a signed
  `registry-snapshot-v1` checkpoint file — the same portable object the
  R3/P2 operator checkpoint uses, byte-identical so one file serves both;
  there is no inline-object form. On first use the client verifies the
  checkpoint against the pinned keys and persists it as the initial
  high-water BEFORE any network response is accepted, and the first
  network snapshot or page boundary MUST satisfy §5 against it (below,
  or equal with a different `head`, `merkle_root`, or `log_size`,
  the snapshot is rejected as tampered and a page boundary reports
  `registry_page_boundary_stale`); there is no trust-on-first-use for
  that registry. Without a checkpoint first use stays
  trust-on-first-use but MUST report it once as posture
  (`registry_bootstrap_tofu`, warning, naming the registry and the hint
  to pin a checkpoint). Rebootstrap after loss uses the same object: a
  checkpoint below a still-present persisted high-water, or equal with
  a different body, is refused with `registry_checkpoint_regression`
  and the state is left unchanged — a checkpoint never lowers or forks
  state. A checkpoint failing signature verification, or a missing,
  unreadable, or malformed checkpoint file, is a configuration error
  naming the path, not a new diagnostic, and fails closed. Equivocation
  is named as the residual the protocol does not close (a registry can
  serve each client a monotonic but divergent view; §5 detects it only
  when two views meet), with an OPTIONAL client detection (§5.1, MAY):
  with two or more enabled registries sharing one `mirror_group`, the
  client compares `merkle_root` at the same `log_size` and reports a
  difference as `registry_view_divergence` (warning under advisory
  registry policy, error under strict) without changing resolution and
  with no quorum. `curator status` (and `curator env status` where the
  environments capability is implemented) list, per registry, the
  high-water, its bootstrap source (`checkpoint` or `first-use`), and
  the last mirror-group comparison outcome. Rollout is direct, not
  warn-first (impact row "S2"): no behavior change without a
  checkpoint or a mirror group, except the new once-per-registry
  `registry_bootstrap_tofu` warning on checkpoint-less first use.
  Schema: the `manager-config-v2`
  registry entry gains exactly the two closed members
  (`bootstrap_checkpoint`, `mirror_group`); the v1 schema stays
  byte-frozen and a schema-1 reader rejects both as unknown fields.
  Conformance: `bootstrap_cases` in
  `vectors/registry-client.json` (first-use accept, below/equal-
  different tampered, TOFU posture, bad-signature fail-closed,
  rebootstrap advance/no-op/regression/equal-inconsistent/bad-
  signature, divergence detected under both policies/agreeing/sizes-
  skipped/single-skipped), generated by `tools/generate-vectors` and
  recomputed by `tools/validate.py`, plus `bootstrap`/`divergence`
  summaries in `vectors/registry-behavior.json`, v2 vectors, and v2
  schema cases. Specified for `STORY-260910-6bo7ej`.

### Changed

- Made the section 6 `path` overlay declarable: the environments section
  12.1 `overlays.<profile>` row now requires the `range | tag | revision`
  form only for a `git` source and states `{ source, weight? }` for a
  `path` source, and `manager-config-v2` `$defs/overlay` enforces the same
  split (a network-spelled source requires exactly one requirement form; a
  path-spelled source admits none of `range`, `tag`, `revision`, or
  `directory`, with `branch` rejected by the closed object as before).
  The git spelling follows the core section 6.1 canonical identity (the
  four schemes in any letter case, SCP `[user@]host:path` with the section
  6.1 host grammar, and no backslash immediately after the SCP colon), so a
  Windows absolute path such as `C:\Users\operator\context` classifies as a
  `path` source. A `://` URL whose scheme is two or more characters and is
  outside the `ssh`/`git`/`http`/`https` set is refused outright — a
  one-character prefix before `://` is a drive path, so `C://Users/…` stays
  a `path` — and so
  is an SCP-shaped spelling whose host is not a section 6.1 host, because
  core section 6.1 requires an invalid network form to be rejected rather
  than treated as local. A `file:` URL is neither section 1 kind — core
  section 6.1 gives it no network identity and the section 1 path operand
  names a directory, not a URL — so it is refused too.
  Sections 1 and 6 are unchanged, and the manager profile states the same
  shape as a manager-side obligation citing section 12.1. The published
  `manager-config-v2` cases and vectors stop giving the
  `/Users/operator/context` overlay a `revision` and gain positives and
  negatives pinning every classification arm: Windows spellings
  (`C:\…`, `C:/…`, `C://…`), project-relative paths, a colon in a later
  path segment, SCP forms with and without a user, a single-character host,
  each scheme in uppercase, and the refused shapes: an unknown scheme, a
  `file:` URL, an SCP host outside the grammar, and a backslash after the
  SCP colon. `vectors/manager-config.json` is untouched.
- `agent-environment-marker-v1`: `surfaces` is closed to the four keys
  `mcp`, `root-context`, `skills`, and `system-prompt`; `form` is required
  on `root-context` and admitted nowhere else; `tools/validate.py`
  rejects a copy whose path is not one of its surface's paths.
  `launch-env-fragment-v1`: every absolute path rejects a `..` segment.
  `context-lock-v1` wire semantics reject a member whose `required_by`
  names itself. `manager-config-v2` gains negative cases for the overlay
  `range`, `tag`, and empty `source` grammars, and `tools/validate.py`
  cross-checks every closed knob enum against the environments section
  12.1 `Values` column. Decision 0012 carries an erratum (2026-09-05).
- Closed the environments section 9.5 takeover shape gap: the explicit
  takeover is now stated as a flag carried by exactly the mutating
  onboarding triggers (`profile install`, `profile use`, `profile sync`,
  `profile update`, `env resolve --repair`) covering only the unmanaged
  files the carrying operation would write, never an operation of its own;
  the manager profile states the matching manager-side obligation; and
  `cli/curator.md` publishes `[--takeover]` on those rows (with the
  section 9.5 notice, section 8.3 backup, and refusal clauses) instead of
  a standalone command. No diagnostic is added or renamed, and the
  document stays revision 1.
- E4: umbrella provider resolution no longer trusts the ambient `PATH`
  (environments §11). The trust roots are the manager install directory
  (resolved after symlinks) and the new closed §12.1 knob
  `provider_directories` (list of absolute paths, default `[]`, §12.2
  lockable), searched in that order with first match winning; the
  manager-published and managed directory refusal keeps applying wherever
  the match is found, and an unreadable root fails with the new
  `subcommand_provider_root_unreadable` (never absence, never a fallback).
  This closes the S6-injected `PATH` attack in which a project
  `.agents/env.sh` plants a `curator-run` that dispatch would execute as
  the launcher. Warn-first rollout in two labelled revisions: revision A
  keeps ambient-`PATH` selection exactly and only warns
  `subcommand_provider_outside_trust_roots` with the migration hint to
  list the provider's directory (e.g. a `curator-run` in `/usr/local/bin`);
  revision B searches only the trust roots, never `PATH` (a diagnostic-only
  `PATH` probe names the refused path), and refuses a `PATH`-only provider
  with `subcommand_provider_untrusted`, naming the refused path and the
  trust roots consulted. `env status` names the resolved provider path and
  trust verdict per discovered `curator-<name>`, and an unreadable root
  with its directory. Conformance:
  `vectors/umbrella-provider-resolution.json` (install/listed positives,
  ordering, revision-A `PATH`-selection cases, revision-A warning vs
  revision-B refusal including the S6-planted case, published/managed
  refusals, unreadable failures, missing) and new `provider_directories`
  schema cases and vectors for `manager-config-v2` and `system-config-v2`.
  Blocks proposal 0016 / `path_prepend` (`STORY-260916-2otjbn`).
- S4 (MCP env passthrough and declaration surfacing): the environments
  section 12.1 `passable_env_names` default is now empty (opt-in per name)
  instead of `null` (unbounded); an explicit `null` keeps meaning unbounded
  as a lockable-away operator choice (sections 2.2, 10.3; section 12.2
  already lockable, unchanged). An empty `mcp_package_allowlist` still
  permits every network identity but now warns
  `mcp_package_allowlist_empty` at `profile install`, `profile update`,
  and in `env status`, stating that every declaration package in the
  closure is admitted. `profile install` and `profile update` print one
  closed-column surfacing row per MCP declaration package (new section
  2.3: `package`, `version`, `transport`, `command`, `args`, `env_names`),
  repeated by `env status`. Warn-first rollout in two labelled steps
  (impact row "S4 passthrough default"): profile `s4-warn` keeps the
  unbounded default but warns `mcp_env_passthrough_unlisted` for every
  passed operator variable outside the knob (naming the variables and the
  knob, with a migration hint); profile `s4-enforce` makes the default
  empty and drops unlisted names with `mcp_env_passthrough_dropped`. The
  `manager-config-v2` schema default and its vectors follow the new empty
  default, with new cases for absent/explicit-`null`/explicit-list, plus
  `vectors/environments-env-passthrough.json` pinning both profiles, the
  allowlist warning, and the surfacing bytes. The closed interpreter
  contract for MCP launch stays a later revision.

### Added

- Added `system-config-v2.schema.json`: `system-config-v1` plus one closed
  `environments` object carrying exactly the environments section 12.2
  lockable keys (`overlays_allowed`, `precedence`, `mcp_package_allowlist`,
  `passable_env_names`, `require_current_profile`, `isolation`) with their
  section 12.1 grammars by reference to `manager-config-v2`, `isolation`
  narrowed to `shared`, and a `locked` enum extended by
  `environments.<key>` for each of them; with
  `schema-cases/system-config-v2` (every key present and locked; minimal,
  empty-`environments`, and schema-1-`locked` positives; one negative per
  closed-object rule, per value grammar, per `locked` entry outside the
  section 12.2 set, and a schema-1 rejection). Manager section 1 names the
  keys and the precedence between a system lock and the machine file's
  schema-2 knob. `tools/validate.py` cross-checks the schema against
  schema 1, `manager-config-v2`, and the section 12.2 sentence.
  `system-config-v1` stays byte-frozen and valid; see `COMPATIBILITY.md`.

- Added `manager-config-v2.schema.json`: schema 1 plus one closed
  `environments` object carrying exactly the environments section 12.1
  machine-configuration knobs with their value grammars and defaults, with
  `schema-cases/manager-config-v2` (every knob present; one negative per
  closed-object rule and per value grammar; a schema-1 rejection) and the
  new `vectors/manager-config-v2.json` family whose schema-2 cases'
  `expected.environments` pins the defaults a reader fills.
  `vectors/manager-config.json` stays the byte-frozen schema-1 family.
  Schema 1 is byte-frozen and stays valid; see `COMPATIBILITY.md`.
  `tools/validate.py` now validates both manager-config families against
  the schema each case's `schema_version` selects and cross-checks the schema-2 knob names and
  literal defaults against the section 12.1 table.

- Delivered the environments.md revision 1.1 conformance surfaces of section
  13. Schemas: new `agent-context-v1`, `agent-mcp-v1`, and `context-lock-v1`;
  `agent-environment-marker-v1` and `launch-env-fragment-v1` rewritten in
  place on the lock model (`argument` required on every `flag` descriptor,
  `name` exactly when `argument` is `name`, `precedence` as the two closed
  primitives); every schema with positive cases per optional-member
  combination, one violated rule per negative case, and unknown-member
  rejection. Vectors: `context-versions.json` (tag grammar, precedence, the
  section 1.4 coercion table and excluded forms, prerelease admission, the
  resolution algorithm with its diagnostics, lock canonicalization and
  `lock_sha256`), `context-detectors.json` (section 9.1 classes, waiver,
  unpinnable, system-module warning), and `environments.json` regenerated
  under `curator-root-context-v2` with the retired empty-chapter set re-cut as
  the no-chapter set, emitted-order sets under both `winner` and both
  `placement` primitives, and MCP byte sets per adapter. `tools/validate.py`
  recomputes every hash, byte length, order, lock, finding, and materialized
  byte independently of the generator and fails on a hand-edited expected
  file.
- Added the environments section 1.2 snapshot byte-exactness rule: a snapshot
  produced from a commit carries exactly the committed blob bytes, and neither
  working-tree conversion (`core.autocrlf`, `text`/`eol`, filters, `ident`) nor
  attribute-driven archive processing (`export-subst`, `export-ignore`) may
  alter, add, or omit an entry. Content hashes, state hashes, effective pins,
  and every hash-bound identity are therefore platform- and
  configuration-independent, which the section 5.6 cross-platform equality
  claim had assumed without stating. `git archive` violates the rule under
  `core.autocrlf=true` and for `export-subst` entries; object-database
  extraction satisfies it.
- Added the `snapshot-acquisition.json` vector over the new
  `fixtures/byte-exact` tree (`* text=auto`, an `export-subst` entry, LF, CRLF,
  and mixed-ending files) with its expected content hash, fixture blobs
  committed through plumbing so they survive every checkout unconverted under
  the repository's `eol=lf` policy (a root `.gitattributes` note explains why
  no attribute rule can protect them against the fixture's own nested
  `* text=auto`), and validator cross-checks that fail on a normalized
  checkout, an expanded placeholder, or a hash that omits `.gitattributes`.
- Documented the previously unsurfaced section 9.6 onboarding import in
  `cli/curator.md`: `curator profile import [--as <name>]
  [--allow-lossy] [--use]` (the optional profile name defaulting to
  `imported`, the per-operation lossy-import consent flag, and the
  section 9.1 activation control), with one example line. No normative
  rule is added or changed.

### Changed

- Rewrote manager profile section 12 on the environments 1.1 model per the
  Decision 0012 compatibility impact rows: the MCP channel rows and the
  reserved `curator-mcp` codex layer name (12.1), marker contents and
  versioned backups (12.2), the single-root install grammar, `profile
  update`, `profile remove [--purge]`, `env unmanage`, scoped `--clear`, and
  the lock-writing skill scope (12.3), the `isolation` knob and liveness row
  (12.4), the lock-free `env resolve` with `--repair` and the fragment `mcp`
  section (12.5), the widened detector scope and waivers (12.6), and the
  environments section 12 status rows and GC roots (12.7); every section
  12.1 knob is stated with its manager-side obligation.
- Rewrote the `cli/curator.md` profile and env rows: install
  `--range|--tag|--revision` with one root and a name-less `--use`, the
  `profile list` columns, `profile update`, `profile remove [--purge]`,
  `profile use --clear`, `env unmanage [--restore-backups]`, `env backups
  scrub`, `env resolve --repair`, the informative `profile compose` and
  `env config` rows, and the `curator run` provider pointer to Decision 0013
  Decision 6.4.

### Removed

- Withdrew `profilefile-v1` and `context-manifest-v1` with their schema cases
  and the `monolithic-composed-empty-chapter` expected set, replaced under
  section 13 by the lock model.

## 1.0.0-rc.9 - 2026-08-23

### Added

- Added manifest schema 8 as the single shared schema bump for the
  `script-worker-v1` execution policy and first-party module roots.
- Added install marker schema 4, script-worker capability and evidence vectors,
  module-root filesystem/build-graph vectors, and legacy-schema rejection cases.
- Added an implementation coverage contract. Presence of a family in the
  conformance root was never evidence that a pinned implementation read it, and
  both pinned managers exited 0 against the schema-8 surface while consuming
  none of it. `.github/ci/implementation-coverage.tsv` now names the cases each
  pinned implementation must be observed passing against this suite, and
  `tools/implementation_coverage.py` enforces the ledger against that run's own
  `go test -json` and pytest `--junitxml` streams and against this suite's
  published manifest.

### Changed

- Advanced the normative version through claim schema 5, conformance suite
  identity, generated release metadata, and regeneration inventory to rc.9.
- Moved the live candidate-suite pin to `release/1.0.0-rc.9.json`; rc.8 and
  earlier release metadata remain byte-frozen historical evidence.
- Advanced the pinned implementation references in the same commit as the new
  normative bytes, so no interval of `main` pairs schema 8 with pins that do
  not consume it: the Go manager to `a3abcf34` and the Python manager to
  `3ecca1db`, each qualified against this exact suite manifest
  (`sha256:803918bf...`) through its own candidate lane. The registry pin is
  unchanged; schema 8 adds no registry surface.

## 1.0.0-rc.8 - 2026-08-19

### Changed

- Superseded the failed immutable rc.7 publication with rc.8 while preserving
  the rc.7 tag and release metadata bytes as historical evidence.
- Disabled Python bytecode generation for the entire release workflow before
  validation starts, preventing validation imports from dirtying the tagged
  checkout before the clean-tree release gate.
- Advanced the normative version, claim-v4 protocol pins, conformance suite
  identity, generated release metadata, and regeneration inventory to rc.8.

### Compatibility and security

- The portable-default and explicit fail-closed verified assurance contract is
  unchanged. Rc.8 ships no provider implementation and emits no verified
  implementation or platform claim.
- No rc.7 or earlier release metadata is rewritten. The rc.8 metadata pins the
  exact rc.7 metadata digest and signed merged source commit.

## 1.0.0-rc.7 - 2026-08-19

### Added

- Added the closed `portable` and `verified` assurance model. Portable is the
  default CLI-only `portable-cli-policy-v1`; verified is the explicit,
  provider-backed `verified-provider-policy-v1` and never falls back.
- Added the platform-neutral `host-execution-provider-v1` contract shared by
  macOS, Linux, and Windows, plus typed provider descriptors, capability
  receipts, execution permits, execution receipts, checkpoints, and claim v4.
- Added generated valid and invalid schema cases, timestamp and phase-specific
  checkpoint semantics, a fully hash-linked provider evidence flow, stable
  relational rejection mutations, cache non-aliasing, validator mutation
  tests, and rc.7 release gates.
- Added Decision 0007, normative assurance protocol text, operator guidance,
  and migration/security notes.

### Compatibility and security

- Rc.6 and earlier release metadata and wire schemas remain byte-frozen. No
  historical receipt, marker, cache entry, checkpoint, or claim is upgraded.
- Portable evidence cannot satisfy verified requirements. Mode, policy,
  provider contract, provider binary, capability receipt, permit, execution
  receipt, cache identity, checkpoint, and claim identities are disjoint.
- Providers are separately installed trusted host components. Skill-vendored
  provider binaries and every other vendored compiled artifact remain
  prohibited. Rc.7 ships no provider implementation and emits no verified
  platform claim.

## 1.0.0-rc.6 - 2026-07-30

### Added

- Restored the 22 schema-6 compiled manager lifecycle cases for audit and
  provider ordering, read-only dry runs, private staging, protected cache
  publication, concurrent projects, deterministic transactions, recovery,
  currentness, repair, and locked garbage collection.
- Added fail-closed generator, validator, and release-gate coverage for every
  restored lifecycle group and name and for the exact portable
  `manager-worker-v1` build input, cache key, receipt, and artifact identity.
- Added `release/1.0.0-rc.6.json` with the exact regenerated suite-manifest pin
  and an explicit immutable reference to the published rc.5 metadata.
- Added `conformance/v1/expected/marker-v2.json`, the marker-v2 writer golden
  for the shared schema-5 golden skill. Managers write marker schema 2 for
  schema 1 through 6 mutations, so a writer is compared against this file;
  `expected/marker.json` stays byte-frozen marker-v1 legacy-read evidence.
  Generator, validator, and release-gate coverage require the writer golden,
  reject a legacy marker edited in place, and reject a writer golden that
  invents build state or describes a different installation.

### Changed

- The shared-suite manifest and current candidate metadata now identify
  `1.0.0-rc.6`.
- The compiled lifecycle fixture now reuses the published rc.5 portable
  `go-v1` identity instead of the pre-execution-policy rc.4 identity.
- Release validation now rejects a missing or renamed schema-6 artifact, a
  dropped lifecycle case, a stale compiled fixture, changed claim-v1/v2
  history, stale or duplicate suite pins, and any byte change to the published
  rc.5 metadata.

### Compatibility

- Manifest schemas 1 through 7, build receipts v1/v2, install markers v1/v2/v3,
  and claims v1/v2/v3 retain their bytes and meaning. Claim v3 remains bound to
  rc.5; rc.6 defines no new claim schema and emits no conformance claim.
- `release/1.0.0-rc.5.json` remains byte-identical to the signed and published
  rc.5 commit. Rc.6 uses a new metadata file and suite identity; it does not
  rewrite historical release evidence or advance a downstream implementation
  pin.

### Reconciliation

- Reconciled the accepted schema-7 schemas, corpus, documentation, and gates
  against the published rc.6 tree. The published tree already contains the
  accepted bytes, so this integration records the no-loss reconciliation and
  supersedes PR #14 without changing protocol semantics.

### Security

- All restored rejection and lifecycle evidence remains declarative. The
  generator and validator execute no package-provided code, and all build
  rejections continue to require `artifact_executed=false`.

## 1.0.0-rc.5 - 2026-07-28

### Added

- Manifest schema 7, repository-root `skill-build.json` descriptor schema 1,
  development substitution schema 2, build receipt schema 2, install marker
  schema 3, and conformance claim schema 3 for the closed `go-repository-v1`
  driver. The descriptor filename is manager-neutral: it names the artifact a
  skill is built from, not the manager that reads it.
- Platform-neutral shared fixtures and vectors for SHA-1/SHA-256 tagged and
  untagged acquisition, HTTPS/SSH/local identities, exact Git config/refs/raw
  objects/pack/index/LFS bytes, and fail-closed repository features.
- Whole-snapshot audit ordering, cache, offline, mixed-build, rollback,
  status/repair/GC, shim/PATH, signing-boundary, and claim-qualification cases.
- Author/operator guidance and generated rc.5 metadata carrying the exact
  downstream candidate suite-manifest pin.
- The portable `manager-worker-v1` execution policy for `go-v1` and
  `go-repository-v1`: one identity-verified manager-owned worker in the fixed
  process graph, an exact worker session state machine, the mandatory portable
  control set, the exhaustive versioned `rc5-native-control-inventory-v1`
  per-platform inventory, the closed `capability-evidence-v1` reporting record,
  a single explicit failure boundary, and the `build_execution_*` stable
  diagnostics.
- An explicit statement, in normative text and in vectors, of the portable
  mechanism behind each rule and the kernel-enforced guarantee it is not, so
  `network: "none"`, the frozen snapshot, and the fixed manager-selected graph
  can no longer be read as network denial, read-only presentation, or executable
  allowlisting.
- Executable `go-host-execution-policy` vectors covering the worker graph and
  session order, mandatory controls, the per-platform native-control inventory,
  the closed capability-evidence record and its negatives, the six deferred
  hardened guarantees with their non-rejection guards, worker identity and
  protocol negatives, closed package-influence surfaces, and distinct portable,
  reserved-hardened, and pre-revision cache identities.
- Decision 0006 recording the portable execution policy, the rejected
  hardened-Linux-only and direct-Go alternatives, and the deferral of the
  fail-closed profile to `STORY-260728-327soo`.

### Changed

- The shared-suite manifest and repository version metadata now identify
  `1.0.0-rc.5`.
- Claim v3 qualification requires immutable native evidence for every emitted
  driver/platform tuple. This candidate emits no native manager claim; macOS
  and Windows remain pending downstream evidence and Linux remains excluded
  until `TASK-260728-1skseh`.
- `goBuildPolicyV1` and `goRepositoryBuildPolicyV1` require
  `execution_policy: "manager-worker-v1"`; marker-v3 build records and claim-v3
  driver assertions require the same closed constant. Every `go-v1` logical
  cache key and the generated `go-v1` receipt example change accordingly.
- Decision 0004 supersedes its direct-Go process-graph clause before
  publication.

### Compatibility

- Manifest schemas 1 through 6, the `build-receipt-v1`, `install-marker-v2`,
  and `conformance-claim-v2` schema bytes, markers v1/v2, claim v1/v2, and the
  `go-v1` package-controlled surface retain their prior meaning and frozen
  guards. No manifest or descriptor gains a package-controlled field.
- The unreleased execution-policy revision intentionally changes `go-v1` cache
  identity so a pre-revision candidate entry misses instead of aliasing. The
  exact rc.4 candidate key
  `sha256:3fcd714a40e8918eb67dbd35d435875dcce6c9047da811a1fa26626e5e57be48`
  is retained in the suite only as that non-aliasing proof.
- A future hardened execution profile requires a new execution-policy identity
  and a new claim schema version; claim v3 cannot express one.
- Schema-7 mixed builds keep receipt v1 for local `go-v1`, use receipt v2 only
  for `go-repository-v1`, and write marker v3.
- Candidate suite consumption is explicit and digest-pinned; no committed
  downstream released-suite pin is advanced by this candidate metadata.

### Security

- Exact source and raw-object proof, full-snapshot validation, Git LFS
  rejection, and independent external audit precede both artifact-cache lookup
  and compiler execution.
- Compiled builds apply their mandatory controls inside an identity-verified
  manager-owned worker before any package byte reaches a compiler, and reject
  the build before the worker or Go when a mandatory control is unavailable.
- The portable policy does not claim total network denial, kernel-enforced
  read-only source and toolchain, private-build-root-only writes, hard aggregate
  descendant resource bounds, exact executable allowlisting, or fail-closed
  capability preflight. Those six guarantees are deferred to
  `STORY-260728-327soo`, their absence never rejects a portable build, and
  recording them under `manager-worker-v1` is an error.
- Exactly one control set can reject at this boundary: a mandatory portable
  control that cannot be applied rejects before the worker starts. An unavailable
  inventory native control is reported and never rejects, and capability evidence
  stays out of cache, receipt, marker, and claim identity.
- Source hooks, helpers, filters, submodules, LFS hydration, alternates,
  replacements, grafts, promisor/lazy fetch, package PATH/output control,
  package influence over the execution boundary, and install-time signing remain
  outside the closed driver.

## 1.0.0-rc.4 - 2026-07-20

### Added

- Manifest schema 6 with the closed compile-only local `go-v1` build command.
- Build receipt schema 1, install marker schema 2, conformance claim schema 2,
  protected artifact-cache rules, mixed lifecycle planning, and deterministic
  build vectors.

### Compatibility

- Schemas 1 through 5 and marker schema 1 retain their published bytes and
  meanings. Schema 6 is selected only by exact `schema_version`.

### Security

- Package source is compiler input only. Package-controlled recipes, hooks,
  argv, environment, output selection, dynamic/native toolchains, produced
  program execution, and receipt self-attestation are rejected.

## 1.0.0-rc.3 - 2026-07-14

### Added

- Canonical `agent-skill.json` schemas for skill runtime, capability, command,
  skill, and MCP dependency declarations.
- Shared manifest-resolution vectors covering canonical-only, legacy-only,
  equal dual manifests, conflicting dual manifests, invalid-manifest
  fail-closed behavior, and `agents/runtime.json` fallback.

### Changed

- Made `agent-skill.json` the implementation-neutral filename that conforming
  writers emit.
- Reserved `csk-skill.json` as a protocol 1.x read alias and preserved its
  published schema bytes unchanged.
- Required readers to reject unequal dual manifests with
  `conflicting_skill_manifests` instead of choosing one silently.

### Compatibility

- Existing `csk-skill.json` packages remain readable without migration.
- Packages may temporarily ship equal canonical and legacy manifests during a
  staged rollout; `agent-skill.json` is authoritative in that case.
- `agents/runtime.json` remains readable only when neither modern filename is
  present.

### Security

- The rename adds no execution surface. Dual-file ambiguity and attempts to
  hide an invalid manifest behind a fallback now fail closed.

## 1.0.0-rc.2 - 2026-07-13

### Added

- A normative registry-service profile for stable pagination, serialized
  append transactions, durability, recovery, backup/restore, key operations,
  resource controls, health, observability, and an explicit threat model.
- Executable registry-service and registry-client vectors covering conjunctive
  queries, exact artifact identity, snapshot-bound cursors, auditor-scoped
  idempotency, concurrent writers, rollback, recovery, retry safety, and limits.
- A decision record separating the registry HTTP wire contract from production
  service guarantees without changing deployed response objects.
- A machine-validated independent review report format, stable-release gate,
  and release checklist that forbid normative drift after review.
- Manager lifecycle vectors for self-contained command launchers, idempotent
  bootstrap, closure-scoped upgrades, and side-effect-free dry runs.

### Changed

- Defined artifact identity as name, source identity, commit, and content hash,
  preserving evidence when one source and commit produce different content.
- Bound every pagination chain to one immutable signed snapshot boundary.
- Scoped idempotency keys to an auditor and compared the submitted record's
  CCJ-1 digest.
- Required snapshot creation time to remain fixed for one committed boundary
  and registry-service snapshot version to equal log size.
- Defined an external high-water checkpoint as a signed registry snapshot and
  made stable release artifacts conditional on two passing independent reports.
- Added review-report schema v2, requiring separate public reviewer identities
  and explicit non-maintainer/non-author attestations, with executable
  stable-gate regression tests. Draft v1 reports remain readable but are not
  valid stable-release evidence.
- Separated durable client rollback state from disposable response caches and
  required existing corruption and persistence failures to fail closed.
- Made shell activation an explicitly optional interactive convenience and
  required agent command execution to remain independent from user profiles.
- Defined portable direct project-shim locations and safe, non-destructive
  publication of global forwarding shims.
- Clarified finite upward search, activation reentrancy guards, Git Bash
  handling of native Windows paths, and cached hook installation.
- Added manager guidance for warning about prompt-visible runtime source paths
  and missing shell-neutral command resolution.
- Required command launchers to carry their runtime dependency environment on
  Unix and Windows while preserving inherited `PATH`, arguments, and exit
  status.
- Defined selected-closure upgrade behavior, cross-project fetch
  deduplication, create-if-absent bootstrap, and dry-run purity across source,
  cache, security-state, runtime, and project surfaces.
- Accepted GitHub-verified protected-main merge commits as release targets
  while retaining maintainer-signed release tags and exact-target checks.

### Compatibility

- Existing protocol filenames, signed object schemas, endpoints, and response
  shapes are unchanged.
- Registry services must tighten behavior before claiming the production
  registry-service class; existing clients continue to parse the same wire
  objects.

## 1.0.0-rc.1 - 2026-07-13

### Added

- Split normative protocol core, registry, manager profile, and conformance
  documents from the implementation-specific Curator CLI guide.
- Draft 2020-12 JSON Schemas for every versioned wire object and HTTP response.
- Authoritative positive and negative conformance vectors with deterministic
  regeneration.
- Compatibility, security, governance, and release policies.
- Cross-platform CI and shared Go/Python conformance gates.
- A repository-pinned SSH signer allowlist verified by release CI for both the
  release tag and its target commit.
- GitHub Actions dependencies pinned to verified full commit IDs.

### Changed

- Declared machine-home paths, command names, global environment variables,
  cache layouts, and managed comment text implementation-specific.
- Replaced implementation-oracle conformance language with schema, prose, and
  vector authority.
- Defined Curator Canonical JSON 1, complete snapshot validation, Merkle byte
  layout, bundle authentication, HTTP errors and limits, and key rotation.
- Defined deterministic closure ordering and portable Windows path rules.
- Added shared identifier, expanded path, source-identity, and signed-number
  rejection vectors.
- Clarified that project aliases are operator-facing Unicode labels while
  canonical registry source identities remain whitespace-free lowercase-host
  values of bounded length.
- Made paginated record envelopes tolerant of individually malformed object
  candidates so federation can ignore one bad record without dropping a page.
- Aligned manager and system configuration schemas with both implementations:
  strict unknown fields, portable matching aliases, registry key and URL
  validation, explicit defaults, and configurable cache/snapshot time bounds.
- Removed the undefined per-registry `required` flag; strict registry policy is
  the protocol 1.0 fail-closed mechanism for unknown artifacts.

### Compatibility

- Existing deployed wire filenames and `.agents/` layout are preserved.
- The signed JSON profile preserves bytes for all valid pre-RC registry
  objects; previously ambiguous numeric and string forms are now rejected.
