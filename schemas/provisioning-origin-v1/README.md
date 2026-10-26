# Provisioning origin, revision 1

The complete closed Draft 2020-12 record implements
[provisioning-origin/1](../../protocol/provisioning-origin.md).
It is separate private machine state, never a marker extension or portable
snapshot input. Path cleanliness and adapter/selector relations are semantic
constraints checked by `tools/provisioning_origin.py` through the production
publication validator. Filesystem identity and lifecycle require independent
manager qualification.

Patterns require the actual end of the string with the portable ECMAScript
`$(?![\s\S])` suffix: `$` alone also matches before a final LF in some engines.
The semantic validator independently rejects C0/DEL controls in paths, profile,
lock identity and selector value. The corpus includes terminal LF/CR and embedded
LF neighbors for all six affected members, plus malformed-origin authority cases.
