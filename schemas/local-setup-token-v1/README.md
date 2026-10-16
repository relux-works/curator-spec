# Local setup-token source schemas

The [normative contract](../../protocol/local-setup-token-source.md) publishes
these closed Draft 2020-12 schemas, after the joint L15-0/C0 allocation.
They are unreleased and separate from frozen rc.14 and all earlier carriers.

| Schema filename (suffix `.schema.json`) | Whole object / bound |
|---|---|
| manager-config-v6 | Complete config 5 successor with optional user-owned Claude source selector |
| env-status-v2 | Complete status 1 successor with unchanged frozen rows and node relation |
| agent-environment-marker-v6 | Complete marker 5 successor with required source identity |
| launch-env-fragment-v6 | Complete fragment 5 successor with optional node projection |
| local-final-exec-v1 | Complete dedicated same-user headless entry document; not an ax/hosted envelope |
| credential-source-config-v1 | Selector subtree only; never a complete manager configuration |
| node-source-v1 | Required-understanding extension branch only; never an enclosing transport |
| source-projection-v1 | Source plus active source/policy generations; no secret authorization |
| refusal-v1 | Exact typed command-refusal enum, separate from readiness reasons |
| registration-v1 | Closed lifecycle metadata; no material or material digest |
| local-binding-v1 | Local protected state shape; never installed from a caller plan |

Local binding uses executing UID and a protected local host reference, not
broker peers, leases or cross-user generations. Every selected carrier is
validated in full before using metadata. Marker machine provenance does not
enter package lock identity. The frozen manifest/lock still reject selectors.

The schema cannot prove the provenance of an otherwise valid binding, sanitation
of arbitrary strings, actual runtime confinement or authenticity/expiry of a
token. No schema success authorizes material lookup. The independent Curator
final boundary resolves protected state and qualified policy. Old carriers,
including v4, remain closed and byte-unchanged.

Run `python3 tools/local_setup_token.py`, the focused unittest command in the
[corpus README](../../conformance/local-setup-token-v1/README.md), and
`make validate`. The normal production spec validator invokes this checker.
