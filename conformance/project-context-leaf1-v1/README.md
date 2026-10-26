# Project context leaf-1 grammar corpus

This corpus accompanies the [closed member schemas](../../schemas/project-context-leaf1-v1/README.md).
It publishes 61 positive and 366 negative complete-record byte fixtures across
all 13 record/projection schemas. `manifest.json` binds every raw fixture by
SHA-256, names its claim and exact expected diagnostic/gate, and gives every
negative a positive sibling of the same record type. Positive fixtures are
CCJ-1 bytes with no trailing LF and have an independently checked record
identity. Structurally representable negatives are also canonical; malformed
encoding, duplicate-member, size, depth and trailing-input witnesses retain
their deliberately noncanonical raw bytes. Local Git attributes preserve those
witnesses without text conversion or whitespace interpretation.

The complete grammar refusal code is `project_context_invalid`. `gate` is
specification-test metadata identifying the failed assertion, not an added
wire member, new exit status or allocation in the shared diagnostic registry.
No operational `project_item_unapproved`, lease or native qualification verdict
is manufactured from these syntax fixtures. Example paths are fictional;
refs/digest slots in separately validated records are not a connected manager
state or an approval chain.

Run from the repository root after installing `requirements-dev.txt`:

```sh
python3 tools/project_context_leaf1.py
python3 -B -m unittest discover -s tools -p 'test_project_context_leaf1.py' -v
python3 tools/check_project_context_leaf1_controls.py
python3 tools/generate_project_context_vectors.py --check
make validate
```

`tools/validate.py` calls the corpus checker, and the unit suite checks exact
regeneration without rewriting fixtures. To regenerate reviewed fixtures, run
`python3 tools/generate_project_context_vectors.py`. The generator refuses
obsolete unexpected JSON files; it does not delete them silently. Logs and
scratch belong under `.temp/`; committed outputs live in this corpus.

The controls runner mutates real schema definitions or compiles a changed copy
of the actual decoder/semantic checker in memory. It changes no published
schema, fixture, expected verdict or product state. Each of the 366 negative
fixtures carries a narrowing control: admit only its field/subclass or relax
one boundary, preserving neighboring rejection. The runner first checks the
baseline and valid sibling, requires the mutant to retain that positive and a
different closed-record rejection, then requires the target's named assertion
to fail. A skipped plant, crash, setup error or surviving assertion is failure.
A separate 10,000/10,001 file-count schema test/control checks that limit in
memory, since those complete records exceed the earlier 1 MiB cap. An additional identity control drops only `sig` from hashing and must fail
the full-member identity assertion. All 368 grammar controls must be killed; the aggregate command exits 0 on that success.

An individual control is deliberately red:

```sh
python3 tools/check_project_context_leaf1_controls.py --mutant ref-home-wrong-tag
```

It must print `EXPECTED RED ref-home-wrong-tag` and exit 1. Other names come
from negative entries in `manifest.json`. Schema cases assert rejection by the
actual schema before subsequent semantic checks, so a mutation cannot count a
later crash as schema enforcement. Decoder/semantic cases assert their typed
gate, including cases where relaxing an early gate exposes a later refusal.
The publication-entry plant separately changes a lease-zero verdict and
requires the repository validator to identify that exact mismatch, with a
passing baseline before and after.

Coverage includes closed/missing/null members and versions; nested records;
all field-used REF tags; ID/HEX terminal-newline rejection; item payload arms;
first-wave environments; grant presence; generation order/count/uniqueness;
command count; source modes, off/admitted admission and fragment binding; filesystem decimal identity;
portable inventory aliases/order/ancestor/size limits; normalized stdio/HTTP
MCP, reserved env names and owning argument bounds; adapter release/capability
syntax; strict JSON and CCJ-1 identities. File contents are not read and no
agent tool is launched.

This is the grammar part of `ProjectClosedGrammar`. It does **not** claim
completion of CIP-0002's runtime vector families:
`ProjectRegistrationBinding`, `ProjectItemApproval`,
`ProjectContextSelectionBinding`, `ProjectContextPackageValidation`,
`ProjectContextClosureRendering`, `ProjectInlineMCP` authority/audit behavior,
`ProjectSourcesClaudeCodexMuse`, `ProjectPermissionsAndMemory`,
`ProjectLeaseLifecycle`, `ProjectDestinationPATH` or `ProjectLaunchRoutes`.
Those require actual manager/runner/provider and native adapter evidence after
normative amendments, diagnostics and carrier coordination. The schema tests
also do not replace whole-skill/package audit, protected snapshot acquisition,
revocation or lease liveness checks.

Review regressions also cover lexical negative zero in both inventory records,
final-LF rejection throughout inherited patterns, portable component suffixes
and semver x/X wildcard selectors. The private schema catalog adds true-end
guards to inherited whole-string patterns without editing released schemas.

The 2026-10-22 native-project amendment adds `mode-cases.json`: 26 static
mode-policy and instruction-byte projections, including paired strict/native
controls. Their independently stated verdicts cover explicit advertised mode,
registration/composition agreement, off/admitted admission, required permission
and memory-off surfaces, strict exclusion, native-project context refusal,
selected skill/MCP delivery surfaces, profile-only native instructions, strict
LF/order and the exact **project sources not isolated** notice. Twenty-four named
control targets exercise twenty-one distinct in-memory narrowing plants through
the repository publication entry. Skips, crashes, an unapplied plant or an
unrelated publication mismatch fail these tests.

Run `python3 -B -m unittest discover -s tools -p 'test_project_context_modes.py' -v`
for these projections and plants. These are specification-test metadata, not a
new wire record, an approval chain, evidence of actual permissions/memory
programming, or native discovery qualification. The oracle assumes separately
validated protected records and independently certified surfaces; it does not
establish those facts. Native-project deliberately permits repository-native
instructions/config/skills/MCP/hooks/plugins under harness rules. Only the
Curator-delivered whole skills/MCP are pinned and audited here. Strict still
requires native-source exclusion; neither mode silently selects the other.
