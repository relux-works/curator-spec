# Profile MCP native writer adaptation, revision 1

This adoption sheet extends [stage A](skillfile-mcp.md), CIP-0022 decision 5,
and [environments §5.8](environments.md#58-mcp-launch-channel-output).
Its separately advertised capability is `profile-mcp-native-writer-v1`.
The sheet fixes a writer contract; publication does not attest that a manager
implements it. The [model corpus](../conformance/mcp-native-writer-v1/README.md)
and [new private carriers](../schemas/mcp-native-writer-v1/README.md) are
separate from every released carrier, byte vector and suite pin.

## 1. Scope and home binding

Only **profile-scoped**, package-backed declarations may reach a shared
profile home: an admitted profile/global declaration or an audited exact
`agent-mcp.json` package in that profile's resolved requirements. Global here
means the manager's profile installation scope, never a project gaining
machine authority. The registered profile identifier, exact profile lock and
canonical environment select the existing managed home from environments §7.
No current-profile fallback may substitute for that explicit binding.
A profile's native servers are intentionally available wherever that profile
is selected; they are not project-specific admission.

A project declaration MUST NOT write a shared profile home, whether its arm
is package or inline. Report `mcp_contribution_policy_refused` with the bounded
reason `project_scope_shared_home`; preserve all prior state. Project inline
arms also retain stage A's `mcp_inline_approval_unsupported` grammar/admission
refusal. This writer grants no inline authority at any scope. Project
contributions require CIP-0002 admission, composition with same-ID conflicts
refused, and a checkout/profile/environment-bound Werkstatt home under
`project-views/<checkout>/<profile>/<environment>`; those adapters and leases
are outside this sheet.

This sheet does not add a global/profile Skillfile parser or silently widen a
closed carrier. A reader must first admit its declaration format under its
own versioned contract. In particular, project Skillfile schema 3 remains
project-only; machine-global schema 3 retains the existing upgrade refusal.
Schemas 1/2, their empty/absent MCP behavior, and legacy profile package
resolution remain unchanged. A future profile/global `mcp_servers` grammar
needs its own dispatch contract; this writer may consume only already admitted
package inputs, never interpret unknown global fields as permission.

## 2. Native surfaces and evidence boundary

`<home>` is the explicitly bound profile/environment managed home, never the
operator's native home. Paths in ownership and writer rows are relative to
that home (not to an unrelated project checkout). This profile writer uses
its own plan namespace, not a project `mcp-plan-v1` with a fabricated project
identity. Rows otherwise use stage A's outcome vocabulary and ordering.

| Adapter | Exact path and native entry encoding | Frozen evidence / disposition |
| --- | --- | --- |
| `claude_code` | `.agent-context/mcp/claude_code.json`; root `mcpServers`, NAME to `{"type":"stdio","command":COMMAND,"args":ARGS}` | Claude Code 2.1.305, macOS arm64, executable SHA-256 `ea3ea3c08d2a9634a4651e687fcf900d410c489bce2b00f22bd7352b91ba704f`; selected JSON file with `--mcp-config FILE --strict-mcp-config`, including an empty `{"mcpServers":{}}`, has startup stdio positive/negative controls. |
| `codex_cli` | `curator-mcp.config.toml`; `[mcp_servers.NAME]`, `command = "COMMAND"` then `args = ["ARG", ...]`, TOML basic strings and LF | Codex CLI 0.162.1, macOS arm64, executable SHA-256 `74c6a6d263f40d65f99c27a815275f5b4ed0bcc2baecc396b4cf3255498bdfc0`; production MCPFile bytes load through the sole `-p curator-mcp` layer and disappear without that layer. Missing layer is silently ignored by the vendor; managed pre-exec verification remains mandatory. |
| `muse` | Observed discovery candidate only: `config/muse/settings.json` inside the multi-variable managed home (`XDG_CONFIG_HOME=<home>/config`), root `mcpServers`. **No writable path is certified by this sheet.** | Muse 1.4.11-R6667.1, macOS arm64, executable SHA-256 `6c04ce1719844685153ef6f04b98113cb61b942d97f0a8b0bfb3932c343984d9`; selected user configuration is discovered, but successful MCP loading/handshakes/tools and an exclusive channel are unmeasured. Required writes refuse. |

Evidence is retained in Curator at commit
`92f6e004dbcfcc7568079fc99206c2e8828edf2f`:
[Claude qualification](https://github.com/relux-works/curator/blob/92f6e004dbcfcc7568079fc99206c2e8828edf2f/docs/qualification/project-source-exclusion-claude.md),
[Codex qualification](https://github.com/relux-works/curator/blob/92f6e004dbcfcc7568079fc99206c2e8828edf2f/.research/codex162/README.md),
[Codex MCP fixture](https://github.com/relux-works/curator/blob/92f6e004dbcfcc7568079fc99206c2e8828edf2f/.research/codex162/evidence/TestCodex162ManagedChannels/curator-mcp.config.toml), and
[Muse qualification P5](https://github.com/relux-works/curator/blob/92f6e004dbcfcc7568079fc99206c2e8828edf2f/docs/qualification/project-source-exclusion-muse.md).
The observations establish native surface behavior at those exact identities,
not qualification of the future transactional writer. No evidence here
certifies HTTP entry loading, other versions/platforms, arbitrary reload,
resume, children, authentication or strict managed-launch isolation.

Only the two measured stdio surfaces may be offered for writer qualification
at these pins. A required Muse/HTTP/other-build/other-platform surface refuses
`mcp_contribution_policy_refused`, reason `native_writer_unqualified`, null
path when no surface is certified. Do not invent a Muse path in a plan.
Known adapters outside this wave (`opencode`, `pi`) remain `skipped: unsupported`
with null path/code. An absent selector selects only currently qualified,
writable adapters; explicit selectors retain every determinable pair,
including unqualified required surfaces. Unknown ids are invalid declarations.
Native writes never start servers, probe endpoints, install runtimes or
attempt authentication. Per-tool setup hints are printed, never executed.

For newly created owned entries, use environments §5.8 encodings and escaping;
no extra native ownership keys, `env`, credentials or values are inserted.
For a shared document, preserve every foreign record's original bytes,
comments, whitespace, order and unrelated native settings. Use syntax-aware
lossless entry edits; do not parse/reserialize the whole file as JSON/TOML.
Duplicate keys, ambiguous TOML table definitions and unreadable preimages
refuse as `environment_surface_unreadable`; a failed read is never absence.
A foreign same-NAME entry conflicts even when its semantic value is identical.
The legacy canonical whole-file encoding is unchanged outside this explicit
capability; the lossless-edit exception applies only to this writer's shared
native document. Native discovery/loading semantics are unchanged.

## 3. Separate protected ownership and actions

The namespace is `<manager-home>/mcp-native-v1/`. Ownership lives at
`ownership/<K>.json`, where K is lowercase SHA-256 hex of CCJ-1 bytes of
`[PROFILE_ID, ENVIRONMENT, PATH]` (no LF). The closed
`ownership-v1.schema.json` defines the document: capability/version,
`scope: profile`, explicit profile/environment/path, and NAME-sorted unique
records. Each record carries `owner: curator`, normalized server and content
digests, native entry preimage digest (null for an absent preimage), and the
last installed native entry digest. Native entry digests are SHA-256 over the
**exact selected-entry bytes**, not reserialized semantics; the declaration's
server digest remains separate. Container separators belong to the edit,
not another record's bytes. Status must use the same parser byte spans.

A record is owned only when its complete marker is present in this protected
namespace, validates and matches the exact profile/environment/path/NAME.
Owning a file or using a reserved filename confers no record ownership.
A marker next to the repository, in native config, in `install` options or
with a different scope/profile/path is never authority. Readers apply existing
private-store/ledger permissions, ownership and no-follow rules. Hashes alone
do not establish provenance. A markerless existing record is foreign; a
missing or malformed marker must never be reconstructed from native bytes.
A well-formed marker that cannot be read refuses rather than downgrading to
absence. Empty/absent declarations never enroll foreign configuration.

Protected actions live at `actions/<A>.json`, where A is lowercase SHA-256
hex of the complete CCJ-1 `action-v1` object. They bind the profile,
environment/path/NAME, exact server/content identities, operation
(`replace`, `restore`, `remove`, `release`), approver, active/revoked state and
current effective policy digest. The latter is CCJ-1 SHA-256 of the manager's
complete effective action policy after fleet/manager ceilings, passable names
and operator/agent authority have been resolved, with no secret values.
That effective policy is an admitted protected input, not project claims.
Every action rechecks provenance, all bindings, current policy permission and
active state under the mutation lock immediately before publication.
Repository records, ordinary content pins, passive plan hashes, and the
project-scoped `mcp-approval-v1` carrier cannot authorize a profile action.
Refuse missing, mismatched or denied authority with
`mcp_contribution_policy_refused`. A protected action never takes over a
foreign entry. Ordinary first package installation still requires all existing
package trust/audit gates and no ownership action.

| Observed record and requested operation | Outcome and effects |
| --- | --- |
| Absent entry, absent marker, admitted package, no action | `added`; publish native entry and ownership together. |
| Exact owned installed bytes and same server/content identities | `unchanged`; preserve native bytes, including optional whitespace. |
| Changed/missing owned entry, no explicit action | `skipped: drift`; no native or ownership change, including repair. |
| Drift, explicit `restore` with exact active protected authorization | `restored`; restore current admitted locked package, update native digest and record the observed preimage. |
| Changed package identity, clean owned preimage, explicit authorized `replace` | `updated`; new admitted bytes and ownership publish together. An unapproved replacement refuses. |
| Previously owned removed declaration, no explicit action | `skipped: drift` pending explicit cleanup; include the old pair in the plan. |
| Explicit authorized `remove` | `removed`; remove only the selected owned entry and marker, preserving all foreign bytes. |
| Explicit authorized `release` | `released`; remove only the ownership marker, leaving native bytes untouched. Later installs see a foreign entry. |
| Same-NAME entry without matching protected marker | `conflict: foreign entry`, summary `mcp_native_entry_conflict`; no takeover, even with an action. |

Restore/replace authorization binds the desired locked server/content;
remove/release binds the last installed protected server/content. Removed
pairs obtain their identities and path from protected ownership, never a
missing declaration. Every such action is explicit; status and generic repair
must not synthesize it. Existing whole-file profile MCP markers do not become
per-entry markers automatically. An ambiguous/legacy linked surface requires
an explicitly qualified migration; until then refuse
`mcp_contribution_policy_refused`, reason `native_writer_migration_required`.
The sheet introduces no implicit migration or relaxed symlink following.

## 4. Publication, status and recovery

Preflight the entire set: explicit profile/home binding, selectors, exact
locked source snapshot, current source/MCP allowlists, signer/revocation/audit
and ceilings, protected actions, every native preimage and every ownership
record. Enumerate NAME/environment in UTF-8 order, exactly one row per pair,
including previously owned removals. A failed transaction reports all
independently determinable pairs; no successful mutation outcome may coexist
with a refusal/conflict. Convert other tentative mutation rows to refusals
with the summary code. Unsupported rows keep null path/code. A conflict row
itself has no row code, only its typed summary. A profile writer plan includes
its capability, explicit profile id, exact profile lock digest, dry-run flag,
rows and ignored option names; it must never masquerade as a project plan.
This sheet does not publish a portable profile-plan carrier.

Use the existing managed-home journal engine with all native edits,
per-record ownership, applicable skills and profile lock as **one transaction**.
Direct payload writes under a lock are insufficient. Capture no-follow parent
and leaf identities, permission/owner boundaries and full preimage digests;
revalidate them and all source/policy/action inputs at publication. Refuse
symlinks, directory/file substitutions and aliasing outside the proven target
set. Never edit through an existing profile store link. Retain original
native files and ownership on every preflight failure. Recovery after durable
intent may complete the exact new generation; before durable intent preserve
the old one. Complete recovery before exposing a launch fragment, so readers
see an old or new coherent generation, never a mixed pair set. Recovery may
not re-resolve a moving source or silently consume a newly changed policy.
A conflicting recovery input must refuse under the existing transaction rules.

Status checks these records read-only; it does not fetch missing snapshots,
probe auth, enroll entries or repair drift. Explicit recovery is reported
separately from status. Repair preserves drift and foreign records, refuses
unreadable/ambiguous preimages and may replay only already admitted durable
intent. Dry-run performs no writes, fetches, recovery or ownership/action
changes and prefixes rendered rows `would:`. After successful native
publication print `MCP configuration installed. Authentication not checked.`
No unchanged/skip-only report claims a new successful native publication.

## 5. Codex seeds and a single writer

Revision B removes the whole top-level `mcp_servers` table and all subtables
from the one-time `config.toml` seed. The profile writer alone creates owned
entries in `curator-mcp.config.toml`. It does not recopy seeds during repair,
move entries out of seed/native config, edit the operator's source config or
reinterpret an imported server as approved. Seed B is not a native exclusion
control after later external edits; inspect the actual managed base read-only
for collisions before every writer operation.

Revision A may retain ungoverned base servers. Preserve them byte-for-byte and
retain `mcp_native_servers_ungoverned` / `mcp_seed_unstripped` reporting. A
same-NAME base entry conflicts (`mcp_native_entry_conflict`) even if the layer
would shadow it or the values match. Disjoint foreign base entries remain
outside ownership and MUST NOT be described as a profile-only effective set.
Re-provisioning to B is explicit and outside a record restore. Also inspect
base entries introduced after B; a recorded B seed revision is not evidence
that the live base is still stripped. A foreign same-NAME layer entry always
conflicts. Only one component writes owned MCP entries: seed processing never
writes owned entries and the legacy whole-file writer must not overwrite a
surface enrolled under this capability. No server is run to discover a
collision; inspect the native config read-only and refuse ambiguous input.

## 6. Consumer exit evidence

A writer may advertise this capability for an adapter only after real
install/preview/status/repair consumers in disposable managed homes establish:
positive installs beside foreign conflicts and unreadable preimages;
byte-for-byte foreign preservation; markerless-entry refusal; drift skip
beside explicitly authorized restore; all action binding/revocation/ceiling
replays; no-follow/race refusal; transactional failure and recovery for each
advertised adapter; Codex A/B and post-B collisions; schema 1/2 unchanged;
and no runtime/auth/network calls, with bounded tripwire controls.
Narrowing controls must catch writing without a valid ownership marker and
overwriting a same-NAME foreign entry for the intended invariant. Muse and
other unqualified surfaces need refusal controls, not fake native writers.
The separate model vectors test only declared observations and expected plans;
passing them never establishes external provenance, filesystem atomicity or
native loading. Keep that distinction in capability reports and handovers.
