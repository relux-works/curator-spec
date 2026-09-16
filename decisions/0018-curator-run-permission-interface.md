# Decision 0018: curator run permission interface

## Status

Status: proposed — not adopted

Proposed 2026-09-16. DRAFT for review under TASK-260916-vht714,
STORY-260916-1on1d2. No option is selected.
Filing this proposal authorizes no implementation, workaround, normative
amendment, or landing of the draft.

Amended 2026-09-16 by operator decision under TASK-260916-2fu85y
(STORY-260916-1on1d2): the permission mode is configured, not only
flagged — a launcher-global default, a per-profile setting, a CLI
override, and a built-in default of `yolo` for interactive launches,
with a lockable fleet-wide force-`native`. Headless, CI, and tracked
silence defaults to `native`, and legacy policy/lock transport fails
closed (revision 2, same task, after independent review). Still
proposed — not adopted; no option is selected, and the amendment
authorizes nothing beyond the draft.

Numbering: the existing decision series ends at 0016; 0011 remains
reserved as recorded in Decision 0013. This filing uses the next two
unused numbers, 0017–0018.

## Context

The launcher (`curator-agent-launcher` `b34e1e2`) accepts `--profile`,
`--system-prompt`, `--model`, `--effort`, `--name`, and
`--ax-profile <standard|yolo>`, then forwards native arguments after
`--` verbatim; repeated or unknown flags are a usage error, and
`--ax-profile` in untracked mode is a usage error (`internal/cli/cli.go`,
README options table, SPEC §3). `--ax-profile` is tracking-only:
[Decision 0013](0013-execution-ownership-and-launch-plans.md) Decisions
3.6, 5, and 6.4 keep permission bypass out of interactive plans and out
of the composed `ax` document, and the launcher SPEC refuses to derive
an `ax` yolo profile from native argv. `defaults.json` is a closed
`{model, effort}` schema (SPEC §4.3, schema `curator-run-defaults-v1`;
the amendment below proposes v2). The legacy
`agents-infra claude|codex -d|--danger|--yolo` aliases expand to the
native bypass flags (relux-agents-infra-main `459742ea`,
`claude_launch.go`, `codex_launch.go`); native Claude `-d` means debug,
so verbatim forwarding is not parity with those aliases.

The design input is the Fable-reviewed research on board task
TASK-260916-2timlf: the outcome resource
`TASK-260916-2timlf_report.md` (Astra research report, 2026-09-16),
the outcome resource `TASK-260916-2timlf_review-verdict.md`
(independent review, VERDICT ACCEPT with corrections, whose §3/§4 are
authoritative where they differ from the report), and the outcome
resource `TASK-260916-2timlf_native-help.txt` (each capture exit 0;
embedded line numbers below refer to it). Tool versions: Claude
2.1.273, Codex 0.153.4, Pi 0.84.2. The verdict's FINAL recommended
design (§3) is recorded below as a proposal, not an adoption.

Verified native flags (all quotes from the installed `--help`):

- Claude: `--dangerously-skip-permissions` — "Bypass all permission
  checks." (0065–0067); `--allow-dangerously-skip-permissions` —
  "Enable bypassing all permission checks as an option, without it
  being enabled by default." (0018–0021); `--permission-mode` —
  choices `"acceptEdits", "auto", "bypassPermissions", "manual",
  "dontAsk", "plan" (0144–0147); `-d, --debug` is debug mode
  (0068–0070); `--restricted` "refuses bypassPermissions" (0188–0202).
- Codex, identically in `codex --help` and `codex exec --help`:
  `--dangerously-bypass-approvals-and-sandbox` — "Skip all
  confirmation prompts and execute commands without sandboxing."
  (0097–0099 / 0061–0063); `-s, --sandbox` — read-only,
  workspace-write, danger-full-access (0089–0092 / 0053–0056);
  `--approve-for-me` — "Route approval requests through automatic
  review using the workspace-write sandbox" (0094–0095 / 0058–0059);
  `--dangerously-bypass-hook-trust` (0101–0103 / 0065–0067);
  `-c, --config <key=value>` overrides (0046–0052 / 0019–0025).
  `-a, --ask-for-approval` (on-request, never) appears only in the
  top-level help (0111–0117); no `--full-auto` spelling exists.
- Pi: no permission-bypass flag in the full help; only `--approve, -a`
  ("Trust project-local files for this run") and `--no-approve, -na`
  ("Ignore project-local files for this run") (0055–0056).

The launcher SPEC delimits configuration ownership: `defaults.json`
(operator over machine per member, with the machine file's `locked`
rule) and `ax.json` (machine over operator, no `locked` member) are the
launcher's whole file family (SPEC §§4.3, 4.6, 4.7). Curator's machine
configuration is the closed knob table of environments §12.1, carried by
`manager-config` schema 2 under one `environments` object — "no knob
lives in an implementation-private file" — with per-profile knobs
already (`isolation.<profile>.<env-id>`,
`system_prompt_files.<profile>.pi`); §12.2 names the lockable subset,
enforced through the manager §1 system-file `locked` rules. The launcher
reads no §12.1 knob: every knob that shapes a launch reaches it only
through the `env resolve` fragment, resolved by Curator (SPEC §4.7).

Operator decision 2026-09-16 (this amendment's only new input): on
operator-owned machines the launch permission mode is a configured
default, not a per-invocation flag only; the built-in default is `yolo`
for interactive launches; and a lockable knob forces `native`
fleet-wide where bypass must never run. The per-environment mapping,
the refusals, and the tracked-mode outcome below are unchanged from
the review recommendation; only the default, the config exclusion, the
provenance source enum, and the transport precondition change.
Independent review (same task, revision 2) corrected two fail-open
rules so the draft meets the brief's explicit requirement: headless,
CI, and tracked silence never inherits `yolo`, and a legacy fragment
or config that cannot carry the policy or the lock fails closed
instead of resolving as silence.

## Gap statement

There is no typed `curator run` surface for requesting a native
permission posture: today a bypass flag can only arrive as raw text
after `--`, untracked and unvalidated, while the legacy wrapper's
`-d|--danger|--yolo` aliases have no launcher equivalent. Any new
surface must map to exactly the verified native flags above, refuse
conflicts and unsupported environments, and preserve the Decision 0013
rule that no bypass spelling enters a tracked `ax` document. The
operator further requires the mode to be configurable (launcher-global
and per-profile) with `yolo` as the built-in default for interactive
launches (headless, CI, and tracked silence staying `native`),
without weakening the mapping, the refusals, or the tracked rule, and
with legacy policy/lock transport failing closed.

## Options and trade-offs

1. **`--permissions <native|yolo>` before `--`, resolved by precedence
   with an interactive-only built-in default `yolo`, and `--yolo` as an
   exact alias.** The review recommends the flag; the operator decision
   changes only what silence means. `native` still means no launcher
   override (argv forwarded verbatim), not a guaranteed prompting
   posture; `yolo` still requests the declared native bypass below, not
   an outside-policy bypass. Omission no longer equals `native`: a
   launch that names no mode resolves through item 2, and total
   silence resolves `yolo` only for interactive untracked launches —
   headless, CI, and tracked silence resolves `native` per item 5. The
   per-environment mapping is unchanged (one reviewed
   provider-mapping owner; a reviewed capability table, never runtime
   help parsing):

   | env | yolo maps to | placement |
   |---|---|---|
   | `claude_code` | `--dangerously-skip-permissions` | before native args, interactive |
   | `codex_cli` | `--dangerously-bypass-approvals-and-sandbox` | top-level and after `exec` (both helps list it) |
   | `pi` | none — refuse `permission_mode_unsupported` (`--approve` is not equivalent) | — |
   | `opencode` | `env_unsupported` (already refused by launcher mapping) | — |

2. **Configuration surfaces and precedence.** The mode resolves per
   launch, first naming level wins:

   CLI `--permissions` (or `--yolo`) > per-profile setting > launcher
   global default > built-in default (`yolo` when interactive,
   `native` when headless, per item 5).

   - **Global default.** A `permissions` member on each env-id entry of
     the launcher's `defaults.json`, values `native|yolo`, unset when
     absent. Schema `curator-run-defaults-v2`: v1 plus this one
     optional member — a new major version, not v1.1, because SPEC §4.3
     closes v1 ("readers MUST reject an unknown member"), so a v1 file
     carrying the member is rejected by v1 readers whatever the new
     revision is called; the new token keeps that failure precise, and
     v2 readers accept v1 files (an absent member is a silent level).
     This mirrors the repo's own additive closed extensions
     (`manager-config` v1→v2, `system-config` v1→v2: new version, old
     version byte-frozen and still valid). The §4.3 operator-over-machine
     per-member merge and the machine file's `locked` rule cover the new
     member mechanically: under a locked machine file the operator
     member is ignored for named env-ids, and a flag for a member the
     machine entry sets is a `usage` error.
   - **Per-profile setting.** A new environments §12.1 knob
     `permissions.<profile>`, values `native|yolo`, default absent (a
     silent level). It is a Curator knob, not a launcher-file entry:
     profiles are Curator's naming authority, §12.1 forbids knobs in
     implementation-private files, and SPEC §4.7 forbids the launcher
     from duplicating §12.1 values into its own files — so the launcher
     learns the profile level the way it learns every §12.1 knob that
     shapes a launch, resolved by Curator and delivered through the
     `env resolve` fragment (the adopting revision amends the fragment
     schema accordingly). Keying launcher-global state by env-id and
     Curator policy by profile keeps each authority single; this
     proposal creates no launcher section in machine configuration
     (the §4.7 open item stays open).
   - The mode is still never derived from anything but these surfaces:
     never inferred from model, prompt, credentials, environment, or
     `ax`. An unknown value on any surface fails closed (`usage` for
     the flag, `defaults_config_invalid` for `defaults.json`, a
     configuration error for the §12.1 knob); a v1 `defaults.json`
     carrying a `permissions` member is rejected as a closed-schema
     violation, never read as v2.
3. **Fleet-wide force-`native` lock.** `permissions` joins the §12.2
   lockable set, lockable only in the direction of `native` — mirroring
   the §12.2 `isolation`-to-`shared` one-direction rule (locking `yolo`
   would be perverse beside a `yolo` default). The system file names
   `environments.permissions` under manager §1: the locked key must be
   set by the system file, replaces the machine knob whole with a
   warning when the machine file set it, and malformed enforced
   configuration fails closed. The launcher learns the engagement
   through the fragment, like the profile level. Under an engaged lock
   any `yolo` the launcher can see — the flag or the `defaults.json`
   member — is a `usage` error naming the locked knob, never a silent
   downgrade and never applied (the §4.3 locked-member rule); the
   machine-knob `yolo` never reaches the launcher because Curator
   already overrode it with a warning. Total silence under an engaged
   lock resolves `native`: the lock redefines the effective default on
   that machine. The lock sits above the whole item-2 precedence,
   including a locked machine `defaults.json` naming `yolo`: that
   combination is a `usage` error naming both, because "force" that
   loses to a launcher file forces nothing. When the launcher cannot
   establish the engagement at all — the fragment predates the lock
   transport — item 5 applies instead: would-be `yolo` is refused,
   never silently admitted past a possibly engaged lock.
4. **Refusal rules (usage exit 2 unless noted).** Effective `yolo` from
   any item-2 level plus a conflicting native selector after `--` is
   refused, in `=` and separate forms, including aliases and `exec`
   placement: Claude `--permission-mode`,
   `--allow-dangerously-skip-permissions`, `--restricted`, duplicate
   `--dangerously-skip-permissions`; Codex `-a/--ask-for-approval`,
   `-s/--sandbox`, `--approve-for-me`, any `--dangerously-bypass-*`,
   and `-c`/`--config` keys `approval_policy`, `sandbox_mode`,
   `sandbox_permissions`. Invalid value, repeated flag, and unknown
   env/version fail closed (a failed probe is not known support).
   Native mode performs no argv inspection: the raw contract is
   unchanged, and raw bypass may remain available untracked — the
   interface is UX, not a security perimeter; raw requests are recorded
   separately.
5. **Headless, CI, and tracked launches never inherit `yolo`;
   their silence is `native`.** A launch is headless when any of
   these holds: stdin or stdout is not a TTY; the native arguments
   select a non-interactive form (`-p`/`exec`-style native args); a
   non-interactive marker is present (`CI`, `GITHUB_ACTIONS`, or an
   equivalent marker the adopting revision enumerates); or the launch
   is tracked. The built-in `yolo` default applies only to interactive
   untracked launches on an operator-owned machine. An untracked
   headless or CI launch that names no mode resolves `native`
   (provenance `source=default-headless`); it may still select `yolo`
   explicitly — flag, profile setting, or global default — subject to
   the item-3 lock, the item-1 mapping, and the item-4 refusals. A
   tracked launch that names no mode likewise resolves `native`
   (`source=default-headless`), so tracked sessions never inherit
   bypass implicitly — a default that smuggled bypass into the composed
   `ax` document would violate D5/D3.6; tracked mode plus effective
   `yolo` from any level is refused
   (`permission_mode_tracked_unsupported`) until a versioned `ax`
   capability admits a permission posture (SPEC §4.6, Decision 0013
   D5/D3.6), with no fallback to untracked, because equal names do not
   prove equivalence. `--ax-profile` stays unchanged and independent
   (tracking-only). Full tracked parity needs an approved ax-owned
   permission representation and stays an open implementation decision.
   Verified support for the permission-policy and lock transport is a
   precondition for admitting `yolo`: a fragment that predates the
   adopting revision — one that cannot carry the profile level or the
   item-3 lock engagement — is not silence. When the launcher cannot
   establish that support, any launch that would otherwise resolve
   `yolo`, from the flag, the profile setting, the global default, or
   the built-in default, is refused
   (`permission_policy_unsupported`); the flag is included because the
   item-3 lock sits above it and an invisible lock cannot be enforced
   except by refusal. A launch that resolves `native` — explicit
   `native`, or headless/CI/tracked silence — proceeds as `native`.
   Legacy transport therefore yields `native` or a refusal, never
   `yolo`, including past an unenforced lock. An absent knob in a
   current-version configuration is still a silent level; only an
   unproven transport fails closed. The minimum fragment/Curator
   version token stays open question 7; the fail-closed rule itself is
   specified here, not deferred.
6. **Provenance.** One stderr line in untracked mode:
   `curator-run: permissions=<native|yolo>
   source=<flag|profile|global|default-interactive|default-headless>
   mapped=<flag or none>` — so an operator can distinguish "native"
   from "nothing was requested" and can see which level won:
   `default-interactive` means the built-in `yolo` default won
   (interactive silence), `default-headless` the built-in `native`
   default (headless or CI silence). The tracked document schema is
   unchanged;
   no argv, credential, or inherited-env dumps. The draft's config
   exclusion ("defaults.json and every config surface can never set
   yolo") is replaced by items 2–3: configuration sets the mode, the
   flag only overrides it. Rejected spellings (unchanged):
   `--permissions standard|yolo` (`standard` implies a uniform safe
   posture the tools do not share), ask/auto/never/yolo or split
   sandbox/approval grammars (false equivalence), reusing
   `--ax-profile yolo` (tracked-only concept, distinct ownership), and
   `-d`/`--danger` aliases (Claude's native `-d` is debug).

## Open questions

1. Should `--yolo` ship in the same increment as `--permissions`
   (review recommendation, for legacy-wrapper parity) or follow after
   the mapping settles? `-d`/`--danger` stay rejected either way.
2. What is the exact `ax` admission precondition for tracked yolo — an
   ax-owned permission representation, validated natively-mapped
   admission, or both — and which version carries it?
3. How are unknown future native policy forms (new Codex `-c` keys,
   new Claude modes) detected without false resolved-policy claims?
   The provider grammar must distinguish prompt text from flags.
4. What does the launcher print, and where is it recorded, when native
   stored settings relax the posture beneath a `native` request?
5. Which negative tests drive the real `curator run` entry with a fake
   process (mappings, refusals, `=`/separate forms, raw conflicts,
   precedence across flag/profile/global/default, v1-file-with-member
   and unknown-value rejection, lock refusal, tracked refusal from
   every level, headless/CI silence resolving `native` with
   `source=default-headless`, legacy-fragment refusal of would-be
   `yolo` from every level including the flag), and what narrowing
   mutants prove each refusal's bound?
6. Later tool versions change flag grammar: what versioned-capability
   rule re-verifies each mapping, and what fails closed first?
7. What minimum Curator/fragment version token carries the profile
   level and the lock engagement to the launcher? The fail-closed rule
   is specified — item 5 refuses would-be `yolo` with
   `permission_policy_unsupported` when the transport support cannot be
   established — so only the token value and the exact fragment member
   names are open. Which non-interactive markers beyond
   `CI`/`GITHUB_ACTIONS` complete the item-5 headless detector
   enumeration, and where is that list versioned?

## Compatibility and security impact

No launcher flag, mapping, default, composition, `ax` document, or
`defaults.json` change. Adoption would touch launcher SPEC §3 (flag
table), §4.1 (fragment members and the transport version
precondition), §4.2 (mapping table), §4.3 (defaults v2 and item-2
precedence), §4.5 (composition placement and conflicts), §4.6 (tracked
refusal from every level, the item-5 headless detector, headless/CI/
tracked default `native`), §4.7 (file family note), §6 (diagnostics,
including `permission_policy_unsupported`), the README options table,
and `internal/cli` parse, `internal/mapping` capability table,
`internal/composition` placement, and `internal/execution` refusal plus
provenance — with Decision 0013 D3.6/D5/D6.4 satisfied before any
tracked bypass — and, on the Curator side, environments §12.1 (new
knob), §12.2 (lockable set), manager §1 (system `locked` list),
`manager-config-v2`, `system-config-v2`, and the launch-env fragment
schema, each by its own specification revision. Raw bypass after `--`
stays available untracked by design; the typed flag adds validated UX,
not a perimeter. `--dangerously-bypass-hook-trust` is never mapped.
Historical `full-auto`/`untrusted` alias spellings are not exposed in
the installed help and are not canonical mappings.

Bypass by default is an explicit operator choice, scoped to interactive
untracked launches on operator-owned machines — not a claim that bypass
is safe. The fleet control is the item-3 force-`native` lock; headless,
CI, and tracked silence resolves `native` (item 5), so no
non-interactive launch inherits bypass implicitly — an untracked
headless or CI launch selects `yolo` only explicitly, and a tracked
launch only once the `ax` capability admits it. A legacy fragment or
config that cannot carry the policy or the lock is a refusal or
`native`, never `yolo`. The refusal table and the tool mapping are
unchanged by this amendment.
