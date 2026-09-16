# Decision 0018: curator run permission interface

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
`{model, effort}` schema (SPEC §4.3). The legacy
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

## Gap statement

There is no typed `curator run` surface for requesting a native
permission posture: today a bypass flag can only arrive as raw text
after `--`, untracked and unvalidated, while the legacy wrapper's
`-d|--danger|--yolo` aliases have no launcher equivalent. Any new
surface must map to exactly the verified native flags above, refuse
conflicts and unsupported environments, and preserve the Decision 0013
rule that no bypass spelling enters a tracked `ax` document.

## Options and trade-offs

1. **`--permissions <native|yolo>` before `--`, default `native`, with
   `--yolo` as an exact alias.** The review recommends this:
   `native` means no launcher override (argv forwarded verbatim), not
   a guaranteed prompting posture; omission equals `native`; `yolo`
   requests the declared native bypass below, not an
   outside-policy bypass. The per-environment mapping (one reviewed
   provider-mapping owner; a reviewed capability table, never runtime
   help parsing):

   | env | yolo maps to | placement |
   |---|---|---|
   | `claude_code` | `--dangerously-skip-permissions` | before native args, interactive |
   | `codex_cli` | `--dangerously-bypass-approvals-and-sandbox` | top-level and after `exec` (both helps list it) |
   | `pi` | none — refuse `permission_mode_unsupported` (`--approve` is not equivalent) | — |
   | `opencode` | `env_unsupported` (already refused by launcher mapping) | — |

2. **Refusal rules (usage exit 2 unless noted).** Explicit yolo plus a
   conflicting native selector after `--` is refused, in `=` and
   separate forms, including aliases and `exec` placement: Claude
   `--permission-mode`, `--allow-dangerously-skip-permissions`,
   `--restricted`, duplicate `--dangerously-skip-permissions`; Codex
   `-a/--ask-for-approval`, `-s/--sandbox`, `--approve-for-me`, any
   `--dangerously-bypass-*`, and `-c`/`--config` keys
   `approval_policy`, `sandbox_mode`, `sandbox_permissions`. Invalid
   value, repeated flag, and unknown env/version fail closed (a failed
   probe is not known support). Native mode performs no argv
   inspection: the raw contract is unchanged, and raw bypass may remain
   available untracked — the interface is UX, not a security perimeter;
   raw requests are recorded separately.
3. **Tracked mode: refuse yolo.** `--ax-profile` stays unchanged and
   independent (tracking-only). Tracked mode plus `--permissions yolo`
   is refused (`permission_mode_tracked_unsupported`) until a versioned
   `ax` capability admits a permission posture (SPEC §4.6, Decision
   0013 D5/D3.6); no fallback to untracked, because equal names do not
   prove equivalence. Full tracked parity needs an approved ax-owned
   permission representation and stays an open implementation decision.
4. **Provenance and config exclusion.** One stderr line in untracked
   mode: `curator-run: permissions=<native|yolo>
   source=<flag|alias|absent> mapped=<flag or none>` — so an operator
   can distinguish "native" from "nothing was requested". The tracked
   document schema is unchanged; no argv, credential, or inherited-env
   dumps. **No config surface can ever set yolo**: `defaults.json`
   stays closed to `{model, effort}` and rejects any permission
   member; yolo is explicit per invocation only, never derived from
   profile, model, prompt, credentials, environment, defaults, or ax.
   Rejected spellings: `--permissions standard|yolo` (`standard`
   implies a uniform safe posture the tools do not share),
   ask/auto/never/yolo or split sandbox/approval grammars (false
   equivalence), reusing `--ax-profile yolo` (tracked-only concept,
   distinct ownership), and `-d`/`--danger` aliases (Claude's native
   `-d` is debug).

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
   defaults rejection, tracked refusal), and what narrowing mutants
   prove each refusal's bound?
6. Later tool versions change flag grammar: what versioned-capability
   rule re-verifies each mapping, and what fails closed first?

## Compatibility and security impact

No launcher flag, mapping, default, composition, `ax` document, or
`defaults.json` change. Adoption would touch launcher SPEC §3 (flag
table), §4.2 (mapping table), §4.3 (defaults exclusion), §4.5
(composition placement and conflicts), §4.6 (tracked refusal), §6
(diagnostics), the README options table, and `internal/cli` parse,
`internal/mapping` capability table, `internal/composition` placement,
and `internal/execution` refusal plus provenance — with Decision 0013
D3.6/D5/D6.4 satisfied before any tracked bypass. Raw bypass after
`--` stays available untracked by design; the typed flag adds
validated UX, not a perimeter. `--dangerously-bypass-hook-trust` is
never mapped. Historical `full-auto`/`untrusted` alias spellings are
not exposed in the installed help and are not canonical mappings.
