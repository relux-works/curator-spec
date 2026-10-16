# Profile Codex settings conformance, revision 1

This unreleased corpus belongs to [CIP-0018 leaf 1](../../protocol/profile-codex-settings.md)
and is outside the frozen rc.14 manifest and candidate pin.
[`schema-cases.json`](schema-cases.json) contains named positive/negative
instances for every [member schema](../../schemas/profile-codex-settings-v1/README.md).
[`vectors.json`](vectors.json) supplies semantic expectations for future
cross-repository entrypoint harnesses. No complete successor wire envelope is
allocated or silently accepted by this corpus.

With `requirements-dev.txt` installed, run:

```bash
python3 -B -m unittest discover -s tools -p 'test_profile_codex_settings.py' -v
make validate
make regenerate-check
```

The first command compiles the five schemas, executes every structural case,
checks the empty package vocabulary and machine launch enum against adversarial inputs, verifies old
carriers still reject settings, and checks semantic-vector inventory. The
other commands retain existing schema/vector/link, Python, Go and generator
checks. Logs belong in `.temp/`. Local structural tests exercise actual
JSON Schema validation; they do not implement a mock resolver or launcher.

Consumers MUST drive each vector's `entry` through the named repository's real
production path, establish its input state, and compare the expected outcome
and forbidden observations. Resolve inputs name context-package contributions
and effective weights after environments section 6's ordinary weight rules.
Raw `settings_bytes` are inserted as the settings object before decoding the
complete allocated manifest, avoiding a duplicate-key witness invalidated only
by unrelated envelope fields. An error has no replacement lock or usable fragment. Credential cases describe
an explicit machine selector `credential_store`, never profile settings.
`keychain` maps to transport `keyring`; `native` emits no override. Former
package-store selection vectors now require `context_manifest_invalid` before
precedence and no replacement lock, fragment or launch data. Absent and empty
package settings have separate positive controls. `absent` means a successfully
read native file with no key; `read-failure` and `parse-failure` are failures,
not absence. `admit-private-file` requires a separately prepared private
credential and never a native link. Unsupported qualification always refuses.

Launch vectors compare the settings argv block; other provider blocks retain
their own rules. Login, app-server and refresh require disposable-store probes,
not an argv-only assertion. Seed identity compares bytes before and after
resolve, repair and launch. Relay and resume must observe covered identity and
actual backend, not merely a repeated expected label. Secret bytes MUST NOT
be copied into test output.

Specification-data success is **0 measured runtime cases**. Structural cases
cannot establish semantic resolution, strict carrier support or any consumer's
backend selection. Full carrier positive/negative cases await coordinated wire
allocation. Producer activation remains gated on those cases, CIP-0015 matrix
adoption and supported-release qualification, including scalar precedence over
a conflicting seed, login, app-server and token refresh. No released or native
platform conformance claim is made here.

## Coordinated containing publication

The [whole-carrier corpus](../rc7-carriers-v1/README.md) validates the allocated successors, canonical bytes
and old/new reader compatibility. The earlier member/row fixtures remain
frozen inputs; runtime qualification remains separate.
