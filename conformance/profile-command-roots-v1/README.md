# Slice B-a command-root specification models

This separate, unreleased corpus leaves `conformance/v1` and
`conformance/candidate.json` frozen at rc.14. The normative contract is
[profile-command-roots](../../protocol/profile-command-roots.md).

`cases.json` includes root/chain integrity, Windows and script models,
retained-reference/gateway and launcher-state carriers, exact-descriptor
retention, process pins, GC union, manager/launcher age pairs, repair/journal
transitions, two distinct versions and a hook install/upgrade/GC state machine.
Every refusal has an exact reason, not just a generic rejection. Synthetic
`FIXTURE-FORWARD/1` records model fixed chain decoding; they are not executable
shell or batch scripts. Byte-cap negatives model pre-read observed extents and
never allocate a GiB fixture. Proof flags represent authoritative observer or
settings-adapter evidence, never a caller's authority to assert those facts.

`tools/profile_command_roots.py` owns the required case IDs independently of
`tools/generate_profile_command_roots.py`. Data drops, duplicates, coherent
generator drops, expected flips and named review checker mutants must fail.
The two-version witness compares receipt-bound executable digests. The validator
reads `hook_upgrade` and drives the reusable contract state machine, including
idempotent retain, list, activation, rollback retention, release and GC.

Run `python tools/generate_profile_command_roots.py --check`,
`python tools/profile_command_roots.py` and
`python -B -m unittest discover -s tools -p test_profile_command_roots.py`.
These qualify specification decisions only. They prove no real hook execution,
process supervision, signature admission, native Windows/script behavior,
performance, filesystem atomicity or transaction durability. Required real
implementation witnesses and the marked owner gateway question remain in the
contract. Release adoption must bind both the corpus and runtime witnesses.

Fragment fixtures use an in-memory composition of rc7 v5 with the non-emittable
B-a member model, never a second allocated whole-object schema. Positive rc7
Codex and B-a composition checks reject legacy `config_overrides`, mixed ownership,
unknown/missing members and unmerged B-a under the normative rc7 reader. Windows
composition is a path model only; the current normative rc7 reader refuses it.
Session cases bind manager-issued pins to profile/root authority; launcher cases
jointly bind an active pin. Hook revision CAS is modelled; the persistent aggregate,
inventory location and separate Windows dispatcher pin remain closed admission gates.
Repair rows have distinct no-edge/live/unknown inputs, exact refusal reasons and
old-edge/preimage preservation. Unknown repair requires quiescence or fenced,
revision-matched audited break; no persistent store is qualified.

Root paths omit the redundant lock component while binding it in metadata. The
corpus includes an 18-byte manager home with a 23-byte profile, reachable 64-byte
profiles on POSIX and Windows, and adjacent 240/241-byte receipt paths. Stable
gateway naming is a provisional per-settings-resource model; multiple resources
can independently select the same or different generations. The naming decision
and proof/registration contracts remain closed hook gates. Tests inject naming
drift and remove rollback and active-release guards to witness their effects.
Session and hook projections are partial: they do not qualify pin issuance,
OS incarnation observation, protected revision revalidation or process supervision.

Command-path admission uses `home + profile + export <= 135/134/129` on
Linux/macOS/Windows; receipt paths also bound `home + profile <= 101/100/99`.
Shape assertions independently hold the 18-byte home, 23/64-byte profiles and
second distinct settings resource. HookModel fixes `a2a` and omits the second
command dimension in its resource key; it cannot qualify hook admission.
A9/A10 are bounded checks for the pins alternative. They are inapplicable to the
recommended no-GC milestone. Matrix acceptance admits fenced implementation;
accepted receipts precede emission and adoption.

The [native owner packet](../../protocol/profile-command-root-admission.md) keeps
all seven gates CLOSED. `native-admission-proposal.json` and its candidate schema
model operator-prune admission; `native-pins-alternative.json` supplies the optional
one-record pins addition, without
allocating production names. Run
`python -B -m unittest discover -s tools -p test_native_root_admission.py` for
named candidate, pin-authority and repair-edge vectors and noncrashing plants.
Each plant preserves a passing nearby control. Journal staging/backup paths and
native runtime outcomes require owner decisions and actual implementation evidence.

The native admission tests also exercise the allocated closed unpinned-launch
and base-PATH evidence definitions, ordered rechecks, proposed gateway/hosted
refusals, unlocked spawn revision checks and the candidate home-route call.
Named removal plants have valid controls; supplied observations and classified
lists prove neither filesystem enforcement nor actual launcher planning order.
