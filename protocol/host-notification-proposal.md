# Machine Host notification selection — revision 1 proposal

**Status:** Review proposal; not accepted, released or runtime-qualified.
[CIP-0031](../cips/CIP-0031-machine-host-notification.md) and
[draft Decision 0036](../decisions/0036-machine-host-notification.md) track adoption.

## 1. Allocation and publication gate

This draft allocates manager configuration **8**, projection
**`curator.launcher-config/2`**, and the Host capability/contract identifier
**`curator-host-notification/1`**. Configuration 6 remains the separate
node-source family; it is not an intermediate launcher carrier. Configuration
7 carries proxy and Claude OAuth selections. Supported configurations 1, 2, 3,
5 and 7 retain `/1`; no implicit migration, `/2` relabeling or notification
member is allowed there. For the same selected path and configuration, their
projection bytes MUST remain byte-identical to the predecessor implementation,
including empty extensions for 1, 2, 3 and 5. Configuration 8 emits `/2` even
when notification is absent or off. A `/2` envelope MUST carry `config_schema:8`;
a `/1` consumer MUST refuse it rather than silently stripping the selection.
Unsupported containing versions require a newer-tool refusal.

The complete containing schemas must preserve every admitted predecessor form
before any producer emits the successor. Draft publication does not satisfy or
defer that gate. This is the same gate as CIP-0029, which may stack configuration
9 and `/3` only after the final schema-8 shape is accepted. No frozen release
schema, vector identity, profile or lock bytes change. Allocation is not adoption.

## 2. Authority and closed selection

Only the selected machine configuration may supply `extensions`. System policy
MUST NOT supply, merge, override or lock these selections, including a lock on
`extensions` or `extensions.notification`. Repository, profile, context,
workflow content and ambient environment cannot supply this machine authority.
Unknown extension names refuse. Absence of `extensions` and `{}` are inert.
Present null or non-object extensions refuse.

`extensions.notification` is optional; absence disables notification. Explicit
`{"backend":"off"}` also disables it but MUST survive projection and edits as
an explicit selection. Off has exactly one member. Host has exactly four:

```json
{
  "backend": "host",
  "contract": "curator-host-notification/1",
  "workflow_reference": "workflow-v1",
  "workflow_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}
```

The digest above is illustrative. `workflow_reference` is exactly 1..128 ASCII
bytes matching `^[A-Za-z0-9._:/@+-]{1,128}$`. It identifies immutable workflow
bytes; it is not a mutable alias or executable/URL instruction. `workflow_sha256`
is exactly 64 lowercase hexadecimal characters matching `^[0-9a-f]{64}$`,
without a `sha256:` prefix, encoding the SHA-256 of those workflow bytes.
The receiver must resolve and verify the admitted immutable bytes independently.

Missing, duplicate, unknown, null, wrongly typed or mixed-variant members refuse.
No endpoint, executable, arguments, credential or arbitrary environment member
is admitted. A syntactically valid reference/digest is neither authorization nor
proof of workflow admission, member enrollment, readiness or continuing lifetime.
Reading, editing and exporting metadata MUST NOT read credential material,
contact a manager, enroll a member, install hooks or start a child.

## 3. Complete containing schemas and predecessor forms

The [schema set](../schemas/host-notification-v1/README.md) supplies closed
configuration 7/8, extension 7/8 and projection `/1`/`/2` containing objects.
Only the three selected schema-8 extension members are admitted: `proxy`,
`claude_auth`, `notification`. Every other containing member retains its
predecessor meaning, defaults and semantic validation. `schema_version`,
`skills_root` and `projects` remain required. All published schema-5 members
are retained by reference, including credential-store and hash-version-2 waiver
forms; the schema-7 reader's build SSH/HTTPS, script bindings and execution
policy are also retained. Optional predecessor null/default forms are retained
where the inspected reader admits them; `environments:null`, `projects:null`,
`permissions:null` and `credential_store:null` remain forbidden.

Proxy is exactly `{profile:reference}`. Claude auth is exactly
`{type:"oauth",store:...}`; file store is exactly `{type:"file",path:absolutePath}`
and Keychain store exactly `{type:"keychain",service:reference,account:reference}`.
Reference strings have 1..4096 UTF-8 bytes, valid Unicode, no Unicode control
characters and no leading/trailing Unicode whitespace. Absolute launcher paths
add target-platform absolute and clean-path requirements; no relative, tilde,
dot-segment or unclean repeated-separator path is admitted. These semantic
constraints supplement JSON Schema's character bounds. They are not new limits
on unrelated predecessor script or credential-path members.

Predecessor semantics also include valid worktree regexes, canonical registry
URLs/keys, canonical build scopes (host at most 253 bytes, no empty/dot segments),
platform path expansion and verified-provider consistency. Schema success alone
does not replace those checks. The new corpus checks structural preservation
and launcher semantics; it does not claim exhaustive production-reader parity.
Before emission, reconcile every admitted form with the final accepted reader,
schemas and independent vectors, rather than narrowing the predecessor to a
few passing examples.

## 4. Refusal diagnostics and precedence

The following stable **corpus diagnostic codes and paths** are proposed for
portable conformance. They do not claim that Core #216 already emits typed
codes. Its compatibility text is recorded separately. Codes/paths are fixed
vocabulary, never copied from untrusted member names, values or parser details.

| Condition | Code | Path | Core #216 compatibility text |
| --- | --- | --- | --- |
| Malformed/duplicate/invalid-UTF-8 JSON | `config_json_invalid` | `$` | `malformed JSON in config <selected-path>` |
| Unsupported containing version (including 6 in this reader) | `config_schema_unsupported` | `schema_version` | `unsupported config schema_version N; this config requires a newer tool` |
| System selection or selection lock | `launcher_selection_machine_only` | `extensions` | supply: `launcher selections belong only to the selected machine configuration`; lock: existing non-lockable-field refusal (see below) |
| Extensions in schemas 1/2/3/5 | `launcher_extensions_schema` | `extensions` | `extensions: requires manager-config schema_version 7 or 8` |
| Schema-7 notification, invalid/unknown extension or selection | `launcher_selection_invalid` | `extensions` | `extensions: invalid launcher selection` |
| Wrong projection identifier/configuration pair | `launcher_projection_invalid` | `schema` | consumer refusal; no downgrade |
| Invalid unrelated containing shape | `config_shape_invalid` | `$` | retain unrelated configuration diagnostic |

The inspected system-lock diagnostic currently quotes the rejected lock name;
that is source evidence, not permission to echo arbitrary input under this
proposal. A conforming input-free selection-lock refusal uses the fixed code/path
above. Likewise #216's untyped messages do not yet implement this code registry.

Strict-file validity precedes interpretation; system authority precedes selected
machine parsing; supported version precedes extension admission; extension
admission precedes unrelated configuration shape checks. Unsupported version
text MAY name only a validated numeric version. The selected config file path
is an operator-selected source locator, not echoed JSON. Refusals MUST NOT echo
input names, values, duplicate keys or parser excerpts. There is no partial
projection, config write, secret read or launch on refusal. A valid containing
control must pass before a member-negative case can establish its intended
refusal; a broken carrier or test setup is not successful detection.

## 5. Edit preservation — owner decision F3

Owner decision for review F3: **the claude-auth editor admits schema 8 and
preserves it**. This supersedes documenting a schema-8 refusal as the chosen
behavior; it does not assert that #216 implements the editor fix already.
Plan, apply and restore MUST keep schema 8 (`SchemaTo` equals the source for
7/8). Environment/credential-store edits and ordinary project edits also retain
8. No editor may downgrade a file carrying notification to schema 7 or 5.

An unrelated edit MUST preserve notification, proxy and claude_auth selections
exactly as JSON values. A requested claude-auth change may change only that
selection; it MUST preserve proxy and notification. Guarded equivalence and
stale-plan checks MUST include notification byte-for-byte (compare its stable
serialized selection), so an intervening notification change cannot be lost on
apply or restore. Refused/stale edits leave the file unchanged. The same
admit-and-preserve rule applies later to schema 9, once admitted; this proposal
does not allocate or activate 9. Schema-2 auth edits may promote to 7, and
schema-7 edits remain 7; neither invents notification.

Qualification needs real editor plan/apply/restore and env set/unset roundtrips,
paired stale-plan/no-downgrade controls and unchanged unrelated selections.
The specification vectors state these transitions; they do not execute editors.

## 6. Contract ownership and CIP-0023

[CIP-0023 §4](../cips/CIP-0023-exact-plan-hosted-launches.md#4-doorbells-without-post-digest-process-changes)
assigns the protected notification binding and concrete transport/destination
record publication to the **manager owner**. Its migration section requires
**launcher and manager owners jointly** to publish notification binding/event
and restart contracts. It names `session-doorbell-v1`, binding bytes covered by
`binding_sha256`, a reserved session/generation, metadata-only events and a
private outbox; it does not name `curator-host-notification/1`.

This selection is a machine workflow reference/digest, not that binding record
or its digest. The contract names are distinct. No implicit conversion, shared
digest, authorization equivalence or replacement is defined. Launcher draft
#92 requires a matching manager capability and independently admitted member
and workflow; it rejects combining Host selection with legacy doorbells.
That behavior is useful implementation evidence, not proof of ownership.

**Open owner question:** who owns and publishes the complete
`curator-host-notification/1` capability, request/result, workflow admission and
continuing-attachment lifecycle contract, and is it an adapter to CIP-0023's
protected binding or a separate lifecycle? The current spec does not allocate
that named contract to an identified publisher. The manager-owner binding role
above cannot be silently promoted into an answer. The owner must name the
publisher and approve the relationship before receiver activation; this draft
allocates the identifier and selection only, with no invented publisher or
runtime authorization.

## 7. Evidence and qualification boundary

Source evidence: [Core #216](https://github.com/relux-works/curator/pull/216),
head `f5d7cd472db973b9864f87e5ca4526f20e4a893c`, especially
[launcher extensions](https://github.com/relux-works/curator/blob/f5d7cd472db973b9864f87e5ca4526f20e4a893c/internal/config/launcher_extensions.go)
and config/env editors; [launcher #92](https://github.com/relux-works/curator-agent-launcher/pull/92),
head `802895a2fbbc3e49a7bb01ac59674343ec1f720d`,
[consumer](https://github.com/relux-works/curator-agent-launcher/blob/802895a2fbbc3e49a7bb01ac59674343ec1f720d/internal/launcherconfig/notification.go).
Agreement between implementations is not normative acceptance. This proposal
adds independent [vectors and checker controls](../conformance/host-notification-v1/README.md).
Old-reader `/1` byte equality, actual editor preservation and all runtime effects
still need implementation qualification on the accepted rebased head. Current
source review also reports a claude-auth call-site build conflict; passing spec
fixtures does not resolve that code blocker or F3's missing implementation.
