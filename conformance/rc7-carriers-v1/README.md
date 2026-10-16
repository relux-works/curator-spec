# Coordinated carrier publication corpus

The [normative allocation](../../protocol/rc7-carriers.md) defines this separate,
unreleased corpus. `index.json` inventories complete valid/invalid JSON carrier
files; refusals distinguish `carrier_schema_invalid` and
`carrier_semantics_invalid` in specification tooling only. They are not new
public CLI error codes. `canonical.json` binds no-newline CCJ-1 byte files and
their SHA-256 checksums. `compatibility.json` pairs published old controls and
successor controls under both readers. `delivery-vectors.json` records supported/unsupported full JSON, direct login,
and native/nonempty env/shell outcomes (including zero partial output). These
are checked requirements, not executed renderer outcomes.
`decisions.json` pins bounded published
seam requirements, including forbidden effects; it is not a runtime oracle.

```sh
python3 tools/rc7_carriers.py
python3 -B -m unittest discover -s tools -p 'test_rc7_carriers.py' -v
python3 tools/check_rc7_carrier_controls.py
make validate
make regenerate-check
python3 tools/verify_skillfile_sources_independence.py
git diff --check
```

`tools/validate.py` calls this full-corpus checker. The unit tests also validate
old/new compatibility, UTF-8/duplicate JSON input, package restrictions,
containing fields versus valid member projections, one policy owner, and the
publication's Muse/status/renderer clauses. Narrowing mutants name their
killing tests; the bounded plant changes only a valid enclosing discriminator
and requires the production corpus dispatch to report that intended mismatch.
The full status checker relates known Muse home/shared candidates to the file
backend without rejecting external-source or uncertain rows. Publication checks
pin the bounded execution-prohibition clauses in every amended status document
(allocation, login readiness, environments, CLI and manager); a central link
alone cannot pass. Token-preserving auth-status exceptions in each consuming
document have regression tests and narrowing controls. These are checks of the
specified clauses, not a parser or proof of arbitrary English consistency.

Coverage counts measure only this explicit carrier inventory. No Curator,
launcher, dispatcher or vendor executable runs here. The paired runtime
requirements remain in the login-readiness and profile-codex-settings corpora;
no installed state, login ceremony, Keychain access, metadata reader, env/shell
renderer, token refresh or launch is qualified. Tests check that validation
leaves its input unchanged; real transaction preservation/no partial output
must be established by each owning implementation. Closed legacy status
formats have no published schema in this repo and cannot be structurally
replayed here: rejection of extending those formats remains a downstream
consumer obligation; the new status token/whole grammar is executable here.
