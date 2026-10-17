# Unreleased section 9.1 network-contact vectors

[`network-contacts.json`](network-contacts.json) supplements the released
[`context-detectors.json`](../v1/vectors/context-detectors.json) with the
[environments sections 9.1 and 9.4](../../protocol/environments.md#91-installation-resolution-and-audit)
network-declaration boundary. It leaves the frozen rc.14 corpus, manifest,
candidate pin, secret detectors and other audit gates unchanged.

The 40 cases exercise loopback, all four special-use last labels, single-label
exceptions, mixed case, a single trailing dot, Unicode/punycode pairs,
lookalikes, documentation domains and their subdomains, the static canary,
mixed files in both orders, and covering/missing capability declarations.
Each expected finding names the normalized host and source file. A clean
capability projection does not establish that the other audit gates pass.

Consumers drive their strict member-audit entry point for profile installation
and legacy global skill migration with each case's file bytes and skill-manifest
capability projection (including absence), then compare `expected.findings`.
`capability_check_passes` reports only this finding class. The fixed
`static_canary_blocks` projection must remain independent, including when
`exfiltrate.example.com` has a covering declaration.

The local executable model extracts HTTP(S) URL hosts and recomputes all
40 cases. The input `manifest` is only a capability projection, not a complete
installable package manifest. Broader source-code detection syntax, installation,
migration transactions and runtime consumption by a manager are unverified;
this publication does not claim implementation conformance.

Run from the repository root, using the documented development dependencies:

```sh
python3 tools/network_contacts.py
python3 -B -m unittest discover -s tools -p 'test_network_contacts.py' -v
make validate
make regenerate-check
```

`tools/validate.py` dispatches the network-contact checker, so `make validate`
includes these vectors. No network request or DNS lookup is performed.
Logs belong in `.temp/`.

These controls plant narrowing mutants into the model, leaving the audit
present. Each command is **expected to fail with exit code 1**, with
`NetworkContactTests.test_network_contact_vectors` naming the violated case:

```sh
python3 tools/check_network_contact_controls.py --mutant example-domain
python3 tools/check_network_contact_controls.py --mutant substring
```

| Mutant | Weakened boundary | Required failing case |
|---|---|---|
| `example-domain` | Adds `example.com` to the exemptions | `documentation-com` |
| `substring` | Exempts any normalized host containing `test` | `lookalike-nested-test` |

Both are bounded instrument controls; they establish no coverage beyond the
authored cases and the HTTP(S) fixture-extraction subset.
