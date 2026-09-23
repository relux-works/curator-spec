# TASK-260906-1xbrz6 results — takeover closed set excludes import activation and §9.4 global ops

Decision implemented (orchestrator 2026-09-22): keep the five-member
takeover-carrier set; resolve the import/global question by text.

## Sentences added (exact)

§9.5 (`protocol/environments.md`, after the 8.3.1-write sentence):

> By design, `profile import` activation and the section 9.4 global
> operations are outside this closed set: on
> `environment_surface_unmanaged_conflict` they fail closed exactly as
> section 8.3 states, and the recovery is `profile sync --takeover` or
> `profile use --takeover`, then a retry of the blocked operation.

§9.6 mirror (after "Activation follows the section 9.1 rules without
magic."):

> That activation carries no takeover flag: it is outside the section
> 9.5 closed set, fails closed with
> `environment_surface_unmanaged_conflict` exactly as section 8.3
> states, and recovers through `profile sync --takeover` or `profile
> use --takeover`, then a retry.

§9.4 mirror (after the global-operations sentence):

> Those global operations carry no takeover flag: they are outside the
> section 9.5 closed set, fail closed with
> `environment_surface_unmanaged_conflict` exactly as section 8.3
> states, and recover through `profile sync --takeover` or `profile
> use --takeover`, then a retry.

`profiles/manager.md` §12.3 agreement (after the ledger-discipline
sentence):

> `Profile import` activation and the environments §9.4 global
> operations carry no takeover flag: they are outside the environments
> §9.5 closed set, fail closed with
> `environment_surface_unmanaged_conflict` exactly as environments §8.3
> states, and recover through `profile sync --takeover` or `profile
> use --takeover`, then a retry.

`cli/curator.md`: no change — the `profile import` row, the `global`
row, and the import example already carry no `--takeover`, and the five
carrying rows already publish `[--takeover]`. Per-row takeover clauses
stay with the editorial follow-up leaf (TASK-260906-3o75d6).

## Validator pin (no vector family enumerates the carriers)

`conformance/v1/vectors/environments-write-nofollow.json` enumerates
write *classes* (materialize/takeover/repair/backup), not CLI carrying
operations; no schema/vector family lists the five carriers, so per the
brief no schema/vector case was added. Instead `tools/validate.py`
`validate_takeover_closed_set_text` (wired into `main()`, i.e. the
`make validate` gate) pins:

- the §9.5 carrier enumeration equals exactly
  `profile install`, `profile use`, `profile sync`, `profile update`,
  `env resolve --repair`, in order — widening, narrowing, or
  reordering fails;
- the carrier list equals the §9.5 onboarding-trigger list (stays
  sourced) — drift either way fails;
- one sentence in each of §9.5, §9.4, §9.6, and manager §12.3 names
  every exclusion component (excluded ops, closed set, by-design /
  no-flag, `environment_surface_unmanaged_conflict`, §8.3, both
  recovery ops, retry) — deletion, narrowing, or scattering across
  sentences fails;
- every `cli/curator.md` line naming `curator profile import` or
  `curator global` carries no `--takeover`.

`tools/test_validate.py::TakeoverClosedSetTextTests`: 19 tests
(published-inputs pass, closed-section guards, widening/narrowing/
deletion/scatter mutants, CLI mutants). Production call site:
`tools/validate.py:main` via `make validate` (also CI `validate` job).

## Gap analysis (escape-path coverage — no decision packet needed)

Checked for a blocked state the `sync --takeover` / `use --takeover`
+ retry recovery does not cover; found none:

- import installs the lock/store first (no native writes), so a
  conflict can only surface at activation, when the profile is already
  installed and `profile use <imported> --takeover` completes it;
- global ops act on the current profile's installed lock, whose
  in-place surfaces `profile sync --takeover` re-materializes;
- first-install activation (no prior current profile) still leaves an
  installed profile behind, so a carrying op is always available;
- `environment_store_untrusted` (unreadable lock) blocks the carriers
  too, but that is a different failure with its own recovery
  (reinstall), not an unmanaged-conflict escape gap.

## Files touched

- `protocol/environments.md` (§9.4/§9.5/§9.6 sentences)
- `profiles/manager.md` (§12.3 agreement sentence)
- `tools/validate.py` (pin + gate wiring)
- `tools/test_validate.py` (`TakeoverClosedSetTextTests`, 19 tests)
- `CHANGELOG.md` (Unreleased → Changed entry)

## Validation (observed exit codes, all on the final tree)

- `tools/validate.py`: exit 0 ("validated 62 schemas and 1124 vector
  files"), run after all edits and again after the foreign-churn
  revert below.
- `test_validate.py` full file: 520 tests / 29 classes, all OK —
  P1 56 OK, P2 194 OK (clean tree); P3 182 with 2 errors caused
  solely by the foreign vector churn mid-run (the two
  `test_published_vector_passes` pinnners of the churned vectors);
  after the revert, affected classes re-run clean:
  DotfileManagers+ReadFailure+UmbrellaProvider 56 OK, WriteNofollow 12
  OK, all 12 `test_published_vector_passes` OK; P4 88 OK.
- `go test ./tools/...`: exit 0 (twice, incl. post-revert).
- `gofmt -l tools`: clean; `git diff --check`: exit 0.

Interpreter: curator-spec `.temp/venv` (jsonschema 4.25.1, per
requirements-dev.txt); system `python3` has no jsonschema installed.
The full `make validate` landing suite runs once at handoff by the
runtime; the manual full-`discover` run was stopped early per the
campaign rule (narrow tests only) and replaced by the partitions above.

## Incident: foreign vector churn reverted (not my edit)

At 16:29/16:35 UTC+4, while my test partitions were running, a
concurrent process in this shared story worktree rewrote
`conformance/v1/manifest.json`,
`conformance/v1/vectors/environments-dotfile-managers.json`,
`conformance/v1/vectors/environments-read-failure.json`, and
`release/1.0.0-rc.9.json` with fresh generator output (case-content
changes plus `\\u2014` escaping churn) that fails the repo gate
(`validate.py` exit 1; the 2 unit errors above). Cause was not my
`go test` run (suite uses `t.TempDir`, verified). I preserved the
diff (`TASK-260906-1xbrz6_foreign-vector-churn.diff`, attached) and
reverted the four files with `git checkout --`: the bytes are
byte-regenerable (`go run ./tools/generate-vectors -root .`), no
hand-authored content was lost, and the tree is green again.
Orchestrator/sibling note: whoever needs a regeneration should redo
it from a deterministic generator state — the reverted output did
not validate.

## Revision 2 — exact sentence pins and recovery bounds

Kept the five-carrier set. Clarified that import recovery retries the
installed profile's activation, not `profile import` itself. Added explicit
`global add` and `global install` subjects, with the §9.5/§9.4/§9.6 and
manager §12.3 recovery wording pinned as four whitespace-normalized exact
sentences.

### Exact sentences

§9.5 (`protocol/environments.md`):

> By design, `profile import` activation and section 9.4 `global add` and `global install` are outside this closed set and fail closed on `environment_surface_unmanaged_conflict` exactly as section 8.3 states; recover activation by running `profile use --takeover` or `profile sync --takeover`, then retry activation rather than `profile import`, and recover a blocked global operation by running `profile sync --takeover` or `profile use --takeover`, then retry that operation.

§9.4 (`protocol/environments.md`):

> The `global add` and `global install` operations carry no takeover flag: they are outside the section 9.5 closed set and fail closed on `environment_surface_unmanaged_conflict` exactly as section 8.3 states; recover by running `profile sync --takeover` or `profile use --takeover`, then retry the blocked global operation.

§9.6 (`protocol/environments.md`):

> That activation carries no takeover flag: it is outside the section 9.5 closed set and fails closed on `environment_surface_unmanaged_conflict` exactly as section 8.3 states; recover by running `profile use --takeover` or `profile sync --takeover`, then retry activation rather than `profile import`.

Manager §12.3 (`profiles/manager.md`):

> `Profile import` activation and the environments §9.4 `global add` and `global install` operations carry no takeover flag: they are outside the environments §9.5 closed set and fail closed on `environment_surface_unmanaged_conflict` exactly as environments §8.3 states; recover activation by running `profile use --takeover` or `profile sync --takeover`, then retry activation rather than `profile import`, and recover a blocked global operation by running `profile sync --takeover` or `profile use --takeover`, then retry that operation.

### Recovery evidence and decision packet

Import activation is retried against the installed profile: §9.6 says the
assembled package installs through the ordinary §9.1 pipeline; §9.1 says
installation writes the lock and installs store entries before its activation
policy; and §9.2 `profile use <name>` materializes from the installed lock.
Repeating the import is not the recovery: §9.6 says an already-installed
chosen name stops with `profile_import_name_taken` before any write. The text
therefore says to retry activation, not the import.

The §9.4 text does not settle global lock publication order. It says direct
global declarations write into the profile lock and that resolved skills
materialize into current-scope surfaces; §9.2 says sync/use materialize from
installed locks. There is no §9.4 clause establishing whether the extended
lock remains installed before a surface conflict, so I have not asserted
that the recovery succeeds for every transaction ordering. The exact open
question and options are attached as
`TASK-260906-1xbrz6_global-recovery-decision-packet.md`.

### Regression tests and checks

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools /Users/administrator/Developer/ReluxWorks/curator/curator-spec/.temp/venv/bin/python -m unittest tools.test_validate.TakeoverClosedSetTextTests -v`: exit 0, 21 tests.
- The four rev-1 reproductions are committed as `test_fail_open_predicate_mutation_fails`, `test_inside_predicate_mutation_fails`, `test_renamed_heading_fails`, and `test_lowercase_sentence_split_fails`. Subject swap is covered by `test_excluded_subject_swap_fails`; sentence movement is covered by `test_section_95_sentence_moved_to_section_94_fails`.
- Narrowing mutant: `test_dropped_carrier_fails` rejects loss of a member from the five-operation carrier set. Widening, reordering, onboarding-trigger drift, and CLI flag mutants also remain covered.
- `git diff --check`: exit 0.
- The repository has no Python lint target or configured Python linter; no separate Python lint command was run. The CI formatting job checks Go formatting, and this revision changes no Go files.
- Conformance search found no family enumerating the takeover-carrier set. The two `profile install` rows are update-confirmation cases in `environments-source-signers.json`; `environments-write-nofollow.json` lists filesystem write classes, not CLI operations. No schema or vector was added.
- The configured board gate (`make validate` via `spec-gate.sh`) is run by the board runtime once at handoff, per task instructions; it was not run manually. The handoff result is the source for its real exit code.

### Files changed in revision 2

- `protocol/environments.md` — §9.4, §9.5, §9.6 wording.
- `profiles/manager.md` — §12.3 agreement.
- `tools/validate.py` — exact whitespace-normalized sentence pins, exact H3 headings, section boundaries at the next same-or-higher heading; validator remains called by `main()`.
- `tools/test_validate.py` — predicate, subject, section-heading, sentence-splitting, movement, recovery, and carrier-set mutants.
- `CHANGELOG.md` — unreleased entry.
- `cli/curator.md` unchanged: import/global rows still carry no `--takeover`; the CLI editorial follow-up remains separate.
