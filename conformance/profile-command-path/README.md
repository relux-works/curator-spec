# Profile command PATH companion vectors

This normative, unreleased corpus accompanies
[environments §§9.4/10.2](../../protocol/environments.md#94-profile-scoped-skills-and-migration),
the [detailed companion](../../protocol/profile-command-path.md), and
[hosted delivery](../../protocol/local-hosted-launches.md#4-exact-process-and-runtime-writers).
It follows the accepted design's
[D-PATH placement](https://github.com/relux-works/curator/blob/05102ddb4f4911f25c49fee5ba55221a5dd16a3e/docs/design/profile-skill-runtime.md#slice-b-command-roots-bound-to-profile-locks)
and the [carrier's required companions](../../protocol/profile-skill-plan-proposal.md#required-companion-allocations).
Native delivery comes first. Neither spec acceptance nor an empty-root launch
clears `profile_skill_companion_required` or qualifies runtime behavior.

`baseline.json` supplies **abstract admitted and observed filesystem facts**,
not a launcher request. Its root receipt has the published closed shape;
`cases.json` deep-merges changes (arrays replace) into the baseline. Every row
names a positive control and pins its independent expected outcomes. No child,
filesystem, manager or provider is actually run. `live_preimage`, `fallbacks`
and `starts` describe the required effects; they are not observed process counts.

The baseline lock/plan hashes are recomputed independently from the existing
`profile-skill-plan-v1/baseline.json`. This reuses its admitted selection of
`memory`; this checker does not repeat package acquisition, graph or signer
admission. Protected generation records are trusted inputs, not authority a
receipt can grant itself. Artifact and link-text hashes are recomputed from
literal synthetic UTF-8 bytes. Owner, mode, directory identity, confinement,
shim chain, hard-link aliases and root inventory have isolated controls.
`FIXTURE-FORWARD/1` in a checker control is a synthetic forwarding format,
not an allocated shell or product shim grammar.

## Outcome pairs

| Cases | Required outcome and control |
| --- | --- |
| `current-native`, `configured-protected-tools` | Native active delivery, default empty protected-tools list or configured verified directory first |
| `no-export`, `no-export-hosted` | No prepend, no availability refusal or diagnostic; no active receipt needed |
| `non-current`, `non-current-no-root-needed` | Explicit empty root decision, one commands-unavailable diagnostic, launch continues; paired with current native |
| `hosted-without-carrier`, `hosted-with-carrier` | Old hosted route continues with caller-local empty decision/diagnostic, no final-PATH claim; future jointly supported carrier has active witnesses |
| `interactive-drops`, `managed-drops`, `non-canonical-duplicate-spelling` | Closed predicate classification, retained order and one admission line; managed benign entries drop as interactive does |
| `managed-refuses-world-writable`, `managed-refuses-unreadable`, `unsafe-alias-not-hidden` | Exact unsafe refusal, zero provider starts/fallbacks; paired with `managed-valid` |
| `user-writable-valid` | Operator/group writable alone is not world-writable; no broad developer-directory rejection |
| `foreign-root-excluded`, `non-current-foreign-root-excluded` | Known inherited profile root excluded; only newly verified root inserted, no borrowed singleton on empty native launch |
| `missing-root`, `unreadable-root`, `tampered-root` | Exact active-root verification failure; current-native positive control |
| `stale-lock`, `wrong-plan`, `wrong-generation` | Protected receipt/complete-lock/plan/generation mismatch, no start |
| `routing-unproven`, `root-extra-export`, `protected-owner-wrong`, `receipt-symlink` | Corresponding boundary/inventory refusal, with a valid nearby control |

The 21 additional composition rows pair `no-export` and `non-current` safe
bases with all-dropped fixed-default success and `launch_path_unavailable`
refusal when no directory survives. Empty input, partial/unsafe defaults,
managed default scanning and a surviving active root are distinct controls.
Interactive and managed `*-drop-parent-segment`, `*-drop-dot-segment`,
`*-drop-newline`, `*-drop-del` and `*-drop-c1-control` cases drop benign
spellings and retain the paired safe base. Every successful new row passes the
unchanged effective PATH through supplied-child comparison and the mandatory
state validator; refusals produce no successful state. The existing duplicate
spelling with `.` is now classified non-canonical before deduplication.

Availability `empty` means a zero-command decision with null root/receipt and
omitted prepend, not an empty PATH entry. Both explicit empty and no-export
launches preserve other admission gates. Hosted without the joint carrier
proves only caller continuation/diagnostic; it does **not** claim daemon PATH
was changed or a root/binding crossed `launch-delegated/1`.

`schema-cases.json` pins closed root-receipt and launcher-state positives and
unknown/missing/invalid field negatives. `launcher-state.json` is an active
native state example, with synthetic exact fragment bytes identified in the
test. Digest/binding and PATH serialization need semantic comparison as well
as schema validation. Native state persistence is required under
`${XDG_STATE_HOME}/swarma/launcher/`; this corpus does not create real launcher
state there. The future hosted request/manager record allocation remains joint.

## Child witnesses and limits

Real qualification must collect, from the **actual final agent child**, its
serialized and parsed PATH; command actually reached as artifact path plus
SHA-256, including verified shim chain; and the complete lock/plan/generation
binding correlated with fragment and protected receipt. Cross native and
supported hosted routes with interactive, managed one-shot and new-child
resume/restart forms. Maintain existing dispatcher placement/authentication,
protected-command admission and heavy-command gates.

The checker compares supplied abstract witnesses and plants missing/dropped
roots, inert prepend, reordered protected tools, late ambient substitution,
wrong reached path/digest and lock binding. A negotiated hosted carrier dropping
an active root fails the same check; today's unsupported carrier is the
explicit-empty positive case. No-export/empty witnesses instead establish no
profile prepend and the right availability/diagnostic. Their permitted launch
must never be relabeled successful command delivery.

POSIX strings and metadata support the semantic fixtures; a Windows metadata
schema example proves **shape only**, not SID/DACL interpretation, lookup,
separators or filesystem behavior. Every claimed real platform needs independent
owner/mode/identity and actual-child evidence. Six bounded checker mutants
(reject non-current, reject old hosted, prepend on no-export, admit unsafe
managed PATH, start with no admitted directory, retain a parent segment) must
fail the intended corpus assertion; positive controls also pass. A lookup-only
POSIX shell control finds a private fixture via `PATH=""`, while retained-safe
and fixed-default PATHs do not find it. The executable is never run. This
control is skipped on non-POSIX hosts; the abstract policy/schema checks still
run there. These checks qualify no Curator/launcher/hosted runtime behavior.

Curator owns publication and protected receipt authority; curator-run owns
independent verification, PATH application and native per-launch provenance;
curator-run and session host jointly own the hosted carrier/record and final
hosted delivery. Slice B root/lease/GC, concurrent version witnesses, the
separate protected-name inventory and joint runtime qualifications remain gates.
The project `command_environment`/`path_prepend` exclusion stays in force.

Run `python3 -B -m unittest discover -s tools -p 'test_profile_command_path.py' -v`.
`make validate` includes the same gate. Outputs are test verdicts; logs belong
in `.temp/`. Released carriers and qualification records remain unchanged.
