# Private workspace policy-grant event v1

The closed [event schema](workspace-trust-policy-grant-v1.schema.json) belongs
to [CIP-0020 §2.1](../../cips/CIP-0020-workspace-trust-ledger.md#21-policy-derived-grants-q1-first-slice).
It adds private policy-derived consent without widening the original A1
event enum, published portable schemas or frozen rc.14 bytes.

Structural validity is necessary, not authority. Semantic admission also
requires authenticated operator approval; the complete approved policy entry
digest; a current protected registration and exact no-follow checkout identity;
canonical transport destination; environment/lane matching; unexpired,
unrevoked consent; and qualified hook/projection state. Issuer strings in a
package-supplied record establish none of these facts. Credentials and secret
hook definitions are not carried here.

Paths in this first slice use the macOS/Linux registration binding; Windows
registration identity and broader remote spellings are not allocated here.
Semantic constraints, transitions and paired witnesses live in the
[separate corpus](../../conformance/workspace-trust-policy-grant-v1/README.md).
This publication enables no runtime adapter.
