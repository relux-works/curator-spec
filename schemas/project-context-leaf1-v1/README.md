# Project context leaf-1 member schemas, revision 1

These Draft 2020-12 schemas publish the closed record grammar of
[CIP-0002 leaf 1](../../cips/CIP-0002-project-context-in-managed-launches.md#leaf-1-candidate-grammar).
They cover one registered checkout, selected profile, environment and admitted
project generation. First-wave environments are `claude_code`, `codex_cli` and
`muse`; adapter platform values are `macos` and `linux`.

| Schema | Closed record or projection |
|---|---|
| `registration.schema.json` | Checkout, retained root binding digest, selected profile, protected home and worktree refs |
| `item.schema.json` | Context, whole-skill or normalized inline-MCP payload, environment and requiredness |
| `approval.schema.json` | Checkout/item/environment, principal, ceiling and optional grant ref |
| `generation.schema.json` | Registration binding and ordered, unique admitted item IDs; at most 256 entries |
| `composition.schema.json` | Profile, generation, policy, adapter, materialization, memory-off, command owner and omissions |
| `lease.schema.json` | Immutable composition/session/owner binding and positive safe generation number |
| `project-context.schema.json` | Required project-context fragment member, including off mode |
| `command-environment.schema.json` | Optional checked destination-PATH operation and protected refs |
| `fragment-members.schema.json` | Required project context and optional command environment together |
| `root-binding.schema.json` | Existing closed workspace-trust repository binding plus decimal device/inode identity |
| `snapshot-manifest.schema.json` | Complete immutable context/skill inventory descriptor |
| `control-receipt.schema.json` | Generated agent-visible control inventory, policy, adapter and worktree binding |
| `adapter.schema.json` | Exact provider release string, environment, platform and sorted capability set |

`common.schema.json` supplies ID, field-specific REF, HEX, profile, inventory
and normalized SERVER definitions. ID is exactly `[a-z][a-z0-9_-]{0,63}`;
HEX is exactly 64 lowercase hexadecimal characters. Refs are `TAG:ID`, at
most 96 ASCII bytes, with the field's matching tag. A final LF is not part of
any ID, REF or HEX. Profile and command names reuse the existing identifier
grammar; they do not acquire the more restrictive project-ID grammar.

## Encoding and supplemental validation

The [publication oracle](../../tools/project_context_leaf1.py) is part of this
schema contract. JSON Schema alone cannot reject duplicate JSON members,
invalid UTF-8, trailing JSON input, unpaired Unicode escapes or unsafe CCJ-1
numbers. It also cannot express UTF-8 byte limits, sorted sets, keyed
uniqueness, normalized inventory aliases, ancestor collisions, total inventory
size, the exact unsigned-64 decimal maximum, normalized MCP digest equality or
matching fragment context bindings. Consumers MUST enforce those constraints
alongside the structural schemas. No validator failure includes input bytes.

Each record is bounded to 1 MiB and 16 nested containers (the root object
counts as one). Ordinary strings are bounded to 256 UTF-8 bytes. Absolute root
paths have a 4096-byte bound; snapshot/control relative paths have a 240-byte
bound and at most 32 segments. Referenced owning schemas keep their explicit
bounds, including MCP command/argument/URL character bounds. Files have exact
nonnegative integer sizes at most 16 MiB each, at most 10,000 entries and at
most 64 MiB total. These limits apply together: the 1 MiB record cap can refuse
an inventory before its file-count ceiling is reached.

Inventory paths are ordered by UTF-8 bytes, unique under NFC/case folding,
portable relative paths, with no file/ancestor collision. This lexical check
does not prove that snapshot entries are regular files or that recorded
sizes, modes and hashes match protected bytes. The manager must establish
those facts, including absence of link traversal, at acquisition and use.

Record identity is unprefixed lowercase SHA-256 of CCJ-1(record), without a
trailing LF and **excluding no member**. Records have no self-digest member.
For inline MCP only, `server_sha256` uses the owning `sha256:` prefix and
hashes the normalized SERVER: `env_names` is present (empty when absent at
input), name/selector sets are sorted unique, scalar strings and argument
order are unchanged, and absent `environments` remains absent. Shorthand or
writer-local install options are not members of this normalized payload.

Generation item order is retained. A project never replaces the profile root
context: the composed managed-home instruction file MUST retain the profile
root first, followed by approved project-general context, then applicable
environment-specific project context. Owning module selectors, pinned closure
rendering and LF joining still apply. These member schemas do not qualify an
adapter's actual rendering or its separate admitted system channel.

## Carrier and authority boundary

These are member schemas, **not full launch fragments, manager configuration,
status, marker or portable package envelopes**. In particular,
`fragment-members` validates only the two new members. Adding existing carrier
members to that projection is invalid; validating the projection alone is
insufficient to accept an enclosing carrier. No outer carrier version or
capability negotiation is allocated here. Published fragment v4/v5 and frozen
schema/release/conformance bytes remain unchanged and reject the additions.

A structurally valid record does not grant authority. Refs resolve only in
protected issuing-manager state, never as paths, URLs or bearer credentials.
Live approvals/grants/revocations, same-root filesystem identity, outside-tree
home/worktree allocation, retained context-package/lock closure, source
suppression, permission enforcement, memory-off, required-surface qualification,
lease transitions and actual checked destination-PATH execution remain required
runtime checks. An adapter declaration may describe an incomplete capability
set; that does not authorize a launch missing a mandatory surface. An exact
release string is a nonempty bounded token without range syntax, not evidence
that the provider release exists or has passed native qualification.

This publication delivers the schema/vector portion of leaf 1. Decision and
protocol amendments, the shared diagnostic registry, coordinated containing
carriers and executable runtime vector families remain separate work. See the
[corpus](../../conformance/project-context-leaf1-v1/README.md) for commands,
paired counterexamples and narrowing controls. Later environments, Windows,
profile-only/untracked roots, remote acquisition, multiple exported commands,
settings/hooks/plugins and new native import dialects are not enabled here.
