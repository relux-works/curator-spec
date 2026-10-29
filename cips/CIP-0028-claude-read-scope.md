# CIP-0028: Read scope of declared skills and selected contexts in Claude managed homes

- **Status:** Draft
- **Owner:** Curator maintainers (contributor proposal); decision: operator
- **Created:** 2026-10-29
- **Related:** [CIP-0020](CIP-0020-workspace-trust-ledger.md) §§5–6 (version-qualified projection, per-key projection journal); [CIP-0027](CIP-0027-provisioning-origin.md) (private record beside the marker, writer lifecycle); [Decision 0029](../decisions/0029-provisioning-origin.md)
- **Affects:** [Environments](../protocol/environments.md) §§7.4, 8.3, 8.3.1, 8.4.1, 9.2, 10.1; Curator `claude_code` resolve, repair and verification

## Summary

A Claude Code member launched by Curator stops on the vendor's "read outside
the working directories" prompt when it reads its own declared skills or
selected context modules. Both live in the Curator contexts store, outside the
member's working directory. This CIP lets repair project a narrow, literal
`Read` allow set for exactly those paths into the managed home's
`settings.json`, on Claude releases for which that projection is qualified.
Ownership comes from a separate private record of the occurrences Curator
itself introduced, never from rule shape or byte equality. An occurrence
stays provably Curator's only while neither the `allow` bytes nor the file's
write evidence (file identity and status-change time) has changed since
Curator's commit, so an identical rewrite also forfeits it. Ownership that has
once become ambiguous is never re-established. Publication and retirement are
recoverable per-home transactions. Frozen markers, locks and fragments do not
change.

## Motivation and user stories

- A managed member runs with native permissions and its project as the working
  directory. It reads
  `<home>/skills/example-skill/references/guide.md`, a file of a skill its
  profile declares. The vendor asks whether to allow a read outside the working
  directories, and an unattended member waits on that prompt indefinitely. The
  same happens when a member reads a context module its profile selected.
- The operator's acceptance: no outside-read prompt for Curator-managed skills
  and selected contexts, delivered as managed-home configuration, for new and
  existing homes. A read of another home's skills directory, an unselected
  context package or another tool's private configuration directory still
  prompts.
- An operator who already wrote an identical allow rule keeps it when a
  profile drops the corresponding skill, and keeps it after any later repair.

## Current state

- Specification a9c5e03, [Environments §7.4](../protocol/environments.md#74-credential-passthrough-provisioning-seeds-and-isolation),
  seed table, `claude_code` row: "a `settings.json` seed is not declared in
  revision 1". §8.3 makes the marker the surface ledger; §8.3.1 enumerates a
  closed list of write classes and destinations. None of them covers a managed
  `settings.json` edit, a read-scope record or its journal.
- Curator main 12b2d57: `internal/envregistry/envregistry.go:265` declares only
  `.claude.json` as the Claude seed, and `internal/envprofile/managed.go:1002`
  (`prepareClaudeSeed`) merges only project trust into it.
  `internal/envprofile/native_mcp.go:77` (`nativeMCPLedger`) is a manager-private
  ownership record precedent. It does not decide Claude ownership, recovery or
  retirement.
- The managed home's `skills/<name>` is a symbolic link into
  `contexts/skill-context/<projection>/v<n>/<digest>`. Selected context members
  live in `contexts/context/<name>/<pin>[/<directory>]`.
- Per the vendor documentation (code.claude.com/docs/en/permissions,
  "Symlinks"), an allow rule matches a read through a symbolic link only when
  both the requested path and the resolved path match, and a deny or ask match
  on either path wins. This is documentation confidence only. No runtime probe
  is claimed here, and it is not established that the only failure mode of a
  wrong projection is a prompt.
- An earlier implementation candidate (Curator PR #206, not accepted)
  demonstrated rule emission and the separation between a home's own link and a
  sibling home's link to the same store entry, in fixtures. It derived
  ownership from rule shape and equality. That adopted an identical
  preexisting operator rule, and retirement failed to converge after a skill
  digest change (`cmd/curator TestGlobalNativeOwnerNewDeclarationAfterProfile`).
  Both outcomes are forbidden below.

## Design

### Options considered

1. **`additionalDirectories` or `--add-dir`.** Widens Edit and the sandbox
   write scope and admits whole directories. Rejected.
2. **Answer the vendor prompt with "keep allowing".** Admits every outside
   read, including other homes and private configuration. Rejected.
3. **Allow rules owned by shape or equality.** No record, but it cannot tell an
   operator's identical rule from Curator's and cannot prove retirement.
   Rejected.
4. **Recorded introduced-occurrence ownership with per-home recoverable
   publication.** A private record lists exactly the occurrences Curator
   inserted and whether each is still provably Curator's. Retirement removes
   only occurrences that are still provable. Selected.
5. **A launch-time settings file (`--settings <file>`).** No merge into vendor
   state, but it needs a fragment schema and a launcher change. Outside this
   unit; a later CIP may propose it as a successor.

### Recommendation

Adopt option 4 as normative amendment `protocol/claude-read-scope.md`
revision 1 (sketch below), with a Decision record, a closed schema for
`claude-read-scope/1` and paired conformance vectors. Projection is activated
per Claude release only by a separate adapter qualification (section 6).

## Security considerations

- The projection grants only `Read`, and only for literal absolute paths: this
  home's declared skill links, their resolved immutable store roots, and its own
  lock's selected context member roots. It never grants an ancestor, the store
  root, a sibling home, Edit or Write, MCP, a permission mode or
  `additionalDirectories`. Deny and ask rules from every source keep precedence.
- A sibling home's link into the same immutable entry is not admitted, because
  its requested path does not match. A retargeted link is not admitted, because
  its resolved path does not match.
- The record is ownership accounting, not authorization. Every use recomputes
  the desired scope from the validated lock and store. The record holds paths,
  rule bytes and digests only. It is private machine state and never enters
  packages, locks, fragments, logs or snapshots.
- Writes follow §8.3.1 no-follow atomic replacement. A linked, non-regular or
  unreadable `settings.json`, record or journal stops before writes. No content
  compare-and-swap against an external writer is claimed. Rereading immediately
  before the rename narrows that race but does not close it.
- Tool permissions are not an OS sandbox. A running session is not refreshed,
  and no live-session revocation is claimed.

## Compatibility and migration

- Markers, locks, fragments and release metadata stay byte-identical. The
  record refers one way to the existing marker, by the digest of its exact
  bytes. No marker field, reverse reference, reinterpreted hash, wire change or
  global lock is added.
- A home without a record has no Curator-introduced occurrences. Absence alone
  is neither corruption nor ownership. Its first publication starts from the
  current `settings.json`, and every preexisting equal rule is recorded as
  operator-satisfied. Such a rule never becomes Curator-owned, including after
  later repairs. No explicit adoption step is needed, because absence grants no
  ownership. This differs from CIP-0027, where absence of the record loses
  authority. A valid pre-amendment home converges through ordinary repair.
- **Supported writers.** A supported writer is a Curator release that
  implements `claude-read-scope/1`. Only supported writers create, change or
  retire projected occurrences, the record or the journal. A supporting reader
  refuses a record whose `record` value or revision it does not support, and a
  pending journal, before it emits a usable fragment.
- **Old writers.** A release without this amendment does not read the record
  or the journal. Not handling the private record is not proof that an old
  writer cannot return a usable fragment for a home that a supported writer
  would refuse. This CIP claims no control over an old binary and no
  revocation of a session it launched. The observable boundary is the release
  that resolves the home: under a supported writer, the refusals below apply;
  under an old writer, the last published `settings.json` stays in place,
  nothing is retired, and no read-scope verdict is made.

## Specification changes (normative sketch)

### 1. Projection (amends §7.4)

For a `claude_code` managed home whose Claude release is qualified (section 6),
repair evaluates a **read-scope projection**: the exact rule set

- `Read(//<P>/**)` for P = `<home>/skills/<name>` of each declared skill, and
  for P = that skill's resolved immutable projection root;
- `Read(//<P>/**)` for P = each selected context member's store root in the
  home's lock.

Each P is clean and absolute. When the lexical path and the path below the
canonical location of its deepest existing ancestor differ, both are emitted.
Paths use POSIX form (`C:\x` becomes `/c/x`), and the gitignore metacharacters
`\ * ? [ ]` are escaped with a backslash. `settings.json` remains undeclared as
a seed.

### 2. Edit grammar, creation and preservation

The projection changes `settings.json` only through these named spans. The
editor works on the original bytes and never re-encodes the document. Every
preexisting byte outside the named spans is preserved exactly, including
whitespace, member order, string escapes, number lexemes, `deny`, `ask` and
every other member.

- **Element insertion.** One string element, in the canonical JSON string form
  of the rule, appended at the end of `allow`. The span is the element plus
  one separating comma when `allow` was not empty.
- **Element removal.** Exactly one recorded occurrence plus one adjoining
  comma.
- **Container creation.** When `permissions` or `allow` is absent from an
  existing document, one member is appended at the end of its parent object:
  `"permissions":{"allow":[]}` or `"allow":[]`. The span is the member plus
  one separating comma when the parent was not empty. This is the only
  exception to element-only edits. The record notes the creation, and a
  created container is never removed: emptied containers are retained.
- **File creation.** When `settings.json` is absent (the no-follow `lstat`
  reports that no entry exists), a new home may receive exactly
  `{"permissions":{"allow":[...]}}` followed by a newline, holding only the
  inserted elements. The record notes that Curator created the file.
  Absence is distinct from an entry that exists but cannot be read: that is
  unprojectable (section 5).

There is no other permitted change. A document that this grammar cannot edit
is unprojectable.

### 3. Private record (amends §8.3)

A manager-owned, owner-private regular file `.agent-claude-read-scope.json`
beside `.agent-environment.json`, with closed schema `claude-read-scope/1`:

| Member | Meaning |
| --- | --- |
| `record` | Exactly `claude-read-scope/1` |
| `binding` | Profile name, `sha256:` lock identity, managed-home target, and the digest of the exact marker bytes at publication |
| `generation` | Per-home publication counter, incremented by each committed publication |
| `encoder` | Rule encoder revision (escaping, variant and POSIX rules above) |
| `inputs` | Selected skill names with lexical path, resolved root and projection hash version; context member names with store root |
| `occurrences` | Every occurrence Curator inserted and has not yet retired, each with its exact rule bytes, the generation that introduced it, and a `state` of `proven` or `unresolved`. An `unresolved` occurrence also carries the generation and the reason (`content`, `write_observed`, `evidence_unavailable` or `recovery`) at which its proof was lost |
| `satisfied` | Desired rules that were already present when Curator first needed them; operator-owned and never retired |
| `created` | Whether Curator created the file, the `permissions` member or the `allow` member |
| `postimage` | Digests of the exact `permissions.allow` array bytes and of the whole file as Curator committed them |
| `write_evidence` | The file-system identity of `settings.json` read immediately after Curator's committed rename: device, file identity, size, modification time and status-change time at full precision (on Windows, the volume serial number, file ID, last-write time and change time) |

A rule is *introduced* only if no equal element existed in `allow` immediately
before Curator inserted it. Equal bytes never establish ownership.

### 4. Ownership evidence and its limits

Equal bytes cannot show who wrote them. When the operator removes an occurrence
Curator introduced and later adds the same element back, the array can return
to the exact bytes Curator committed, and no comparison of content can tell
that state from an untouched file. Ownership therefore rests on two
independently observable facts at the start of every publication, before any
write:

1. the current `permissions.allow` array bytes equal the recorded `allow`
   postimage; and
2. the current file-system identity of `settings.json` equals the recorded
   `write_evidence`.

The status-change time is the decisive part. Every write, rename or
metadata change moves it, and an ordinary process cannot set it back to an
earlier value on POSIX systems. An identical rewrite therefore changes it even
when the bytes come back unchanged. A replacement through a new file changes
the file identity as well.

When both facts hold, every `proven` occurrence stays `proven`. When either
fails, every `proven` occurrence becomes `unresolved` with its reason. The
array differs (`content`); the bytes match but a write happened since Curator's
commit (`write_observed`); or the platform or file system does not supply
stable identity and status-change time (`evidence_unavailable`). That covers
reordering, duplicates, edits, removals, an identical remove-and-re-add, any
write by the operator or by the vendor's own tools, a restore from backup and
a copy of the home to another place.

Limits of this evidence, stated as part of the contract:

- It shows that no write happened since Curator's commit. It does not show who
  wrote, so every observed write forfeits all earlier proofs, including writes
  the vendor makes itself, for example when a session saves a permission rule.
- On Windows the change time can be set through
  `SetFileInformationByHandle`. A process that deliberately forges file
  metadata defeats the evidence there; that is outside this guarantee. On
  POSIX, the same holds for an actor that can change the system clock or write
  the raw device.
- A file system without stable file identity or status-change time (some
  network and FUSE mounts, FAT) never yields a proof. Occurrences on it are
  `unresolved` from the first publication and are never retired.

The `unresolved` state is permanent for that occurrence. No later
publication, postimage equality, equal bytes, metadata match, position or
neighbor match makes it `proven` again. A later publication records new
evidence, which only makes occurrences introduced by that publication
provable. A later operator occurrence is never redefined as Curator-owned.

Retirement of an occurrence that is no longer desired:

- a `proven` occurrence is removed in the same committed publication;
- an `unresolved` occurrence is never deleted. Its bytes and the record are
  kept. If the rule is still present in `allow`, the home is not converged,
  the generation is reported with `claude_read_scope_ownership_ambiguous`, and
  a supported writer refuses a usable resolve for that home until a repair can
  prove convergence;
- convergence for an `unresolved` obsolete occurrence is proven only when no
  element equal to it remains in `allow`. A repair then drops it from the
  record. This needs no new command: it happens when the operator edits
  `settings.json`. After that, an equal element added by the operator is the
  operator's own, under the absence rule above.

An `unresolved` occurrence that is still desired leaves the home converged,
because the desired rule is present. It still never becomes retirable.

If file-system evidence is not accepted as ownership evidence, no in-home
proof remains that survives an identical rewrite. The clean alternatives are
then to never retire an introduced occurrence (every obsolete one refuses
until the operator removes it), or a launch-time settings file that Curator
owns as a whole, which is outside this unit. Open question 1 asks for that
decision.

### 5. Recoverable per-home publication (amends §§8.3.1, 8.4.1, 9.2, 10.1)

Add to the §8.3.1 closed lists, with the same no-follow atomic replacement:

- the structured edit or creation of the managed `settings.json` (section 2);
- the record `.agent-claude-read-scope.json`;
- the journal `.agent-claude-read-scope.journal.json`, which holds one
  in-flight unit;
- the recovery evidence file `.agent-claude-read-scope.recovery.json`.

**Targets.** One unit covers `settings.json`, the record, and the marker when
the same repair changes it, under the existing manager-home mutation lock. For
each target, the journal holds whether it existed, the digest of its
preimage, and its planned postimage digest. For `settings.json` it also holds
the file-system identity before the unit. It also holds the input identities
and the complete planned record, including every `unresolved` state decided in
section 4.

**Order.**

1. The journal is written (phase 1).
2. `settings.json` is replaced or created.
3. Its new file-system identity is read and added to the journal (phase 2).
4. The record is committed with that identity as `write_evidence`.
5. The marker change of the same repair follows the existing marker
   transaction, which stays the commit point of the repair.
6. The journal is removed.

Before each destructive step the writer rechecks that the target still matches
its journaled preimage. A mismatch stops the unit before that step.

**Recovery** runs after a restart, before the home emits any fragment and
before the marker transaction's own recovery. It never recomputes ownership
from the current file, so it cannot turn an `unresolved` occurrence back into
`proven`.

| State found | Action |
| --- | --- |
| `settings.json` still has its journaled preimage identity and bytes (or is still absent) | The rename did not happen. The record keeps its preimage and the unit is abandoned. Nothing in `settings.json` changes |
| `settings.json` has the journaled postimage bytes and the phase-2 identity | Complete the unit with the journaled record |
| `settings.json` has the postimage bytes but no phase-2 identity was journaled, or a different identity | Complete the unit, and record every occurrence of the home `unresolved` with reason `recovery`: a write after the rename cannot be excluded |
| `settings.json` matches neither image | Keep the operator's bytes and do not compensate. Move the journal to the recovery evidence file and record every occurrence `unresolved` with reason `recovery` |
| The record matches neither its preimage nor its planned postimage | Refuse; keep the journal and every file |

Compensation deletes a file Curator created only when its current bytes and
identity still equal the created postimage. Otherwise the file is kept.

The recovery evidence file is kept until a later publication proves
convergence, and is removed in that publication. A second conflict while a
recovery evidence file exists refuses a usable resolve and never overwrites
the evidence. No callback-only recovery is allowed.

Generations follow §9.2's per-home convergence. A lock change marks the home
stale (§9.2 step 6). The next repair publishes generation N+1 and retires the
`proven` obsolete occurrences of N in the same committed transaction. A lock
change alone is not a global revocation.

**Verification (§10.1).** The integrity checks in the first five rows apply
to every `claude_code` home that has a record, a journal or a recovery
evidence file, whatever release it now selects:

| Condition | Result |
| --- | --- |
| The record is unreadable, invalid, of an unsupported revision, or bound to another marker digest | Refused under the §8.4.1 read-failure row; never treated as absent |
| A journal is pending, or a second recovery conflict exists | Refused until recovery completes |
| An `unresolved` obsolete occurrence remains | `claude_read_scope_ownership_ambiguous`; refused, no deletion |
| A `proven` obsolete occurrence remains | Qualified release: stale, and repair converges. Unqualified release: `claude_read_scope_adapter_unqualified`; refused, because the frozen state cannot converge |
| `settings.json` is unprojectable: a link, a non-regular file, an entry that exists but cannot be read, not UTF-8, not a JSON object, a duplicate member name on the edited path, a non-object `permissions`, or a non-array `allow` or one with a non-string element | `claude_read_scope_unprojectable`; stops before writes and refuses a usable resolve. Link targets, every operator byte and the preimages stay untouched |
| Qualified release: a desired rule is absent | Stale; repair converges |

There is no warning-as-success path. A home without a record, journal or
recovery evidence file on an unqualified release is the legacy case. It is
neither corrupt nor owned, gets no edit, and carries no qualification or
no-prompt claim.

### 6. Vendor qualification (CIP-0020 boundary)

The `claude_code` adapter names the Claude releases on which the projection is
qualified. A home requires the projection only when its release is in that
set. Qualification covers grammar and matching on that release, with
positives for own skill links and selected contexts, and negatives for a
sibling home's link, a shared store target, a retargeted link, an unselected
context and another tool's private configuration. It is admitted separately
from this CIP, and adopting this CIP qualifies no release.

On an unqualified release every read-scope edit is frozen: no insertion and no
retirement. Documentation confidence authorizes neither a projection nor a
claim that the member will not prompt. Repair reports
`claude_read_scope_adapter_unqualified` with a qualification hint, as CIP-0020
§5 requires. Existing record, journal and recovery state is still validated by
section 5 and is never skipped because of the release selected. A
narrowing-only path on unqualified releases would be a separate proposal.

## Implementation plan

1. The operator accepts or amends this proposal. Publish
   `protocol/claude-read-scope.md`, the closed schema, a Decision record and
   paired vectors in curator-spec, after an exact-head independent review and
   the required checks. The Decision number is the next free one at that time.
2. A separate adapter qualification admits the first Claude release.
3. A successor Curator change implements the record, the edit grammar, the
   journaled transaction and the ownership evidence. It may reuse the earlier
   candidate's emission, escaping and variant code where they still hold. No
   implementation starts before step 1 is accepted.

## Test plan

Each rule below has a valid control (V) and a forbidden scenario (F). All are
production-entry `Resolve` tests on temporary homes, with mutant controls that
must fail for the named reason.

### Declaration scenarios

| Declaration | V (projected and matched) | F (never projected or matched) |
| --- | --- | --- |
| Profile declares skill `example-skill` | `<home>/skills/example-skill/SKILL.md` and `.../references/guide.md`, by lexical and by resolved path | A file of an undeclared skill present in the store |
| Profile selects context `example-context` | Its member's store root | An unselected context package, or the store root |
| Two homes share a store entry | Each home's own link | Home A's rules matching home B's link to the same entry |
| A link is retargeted after publication | Nothing for the new target | The old rule matching the new target |
| Outside paths | Nothing | Another tool's private configuration directory, the home outside `skills/`, an ancestor |
| The profile drops a skill whose rule Curator introduced | Untouched file: the rule is retired | Identical rewrite (the operator removes the rule and adds the same element back, restoring the exact array): the rule is retired |

### Ownership, preservation and recovery

| Rule | V (must hold) | F (must not happen) |
| --- | --- | --- |
| Literal encoding | Paths with `[ ] * ? \` and spaces match only themselves | An escaped path matches a neighbor; a glob rule is emitted |
| Introduced vs satisfied | A desired rule absent before insertion is recorded as introduced | A preexisting equal operator rule is recorded as introduced, now or after any later repair |
| Operator rule survives | The profile drops skill S: the operator's preexisting equal rule for S stays | It is removed |
| Proven retirement | Untouched file; the skill digest changes: N+1 retires both variants of the old introduced rules, and verification after repair is current | An old-digest rule survives and repair reports stale, or a non-introduced rule is removed |
| Identical rewrite | Publish A; the operator removes A and adds the same element back, restoring the exact bytes; the profile drops A: A stays, `unresolved` with reason `write_observed`, refused with `claude_read_scope_ownership_ambiguous` | A is removed because the bytes match |
| Any observed write | A write that restores identical bytes, or a vendor write, forfeits earlier proofs | A proof survives an observed write |
| No rebaseline | Publish A; the operator reorders, duplicates or extends `allow`; a repair appends B; a later repair drops A: A stays, unresolved, bytes kept, generation not current | A is removed, or the generation is reported current |
| Evidence unavailable | A file system without stable identity or change time never proves an occurrence | A proof from content alone |
| Ambiguity resolved by the operator | After an ambiguous case, the operator removes A, and repair drops A from the record and converges | A new command is required, or A is re-added |
| Preservation | Every byte outside the named spans is identical: whitespace, member order, escapes, number lexemes, `deny`, `ask`, other members, operator allow entries | Any byte change outside an insertion, removal or creation span |
| Creation | An absent `settings.json` is created with only `permissions.allow`; a missing `permissions` or `allow` is created as one appended member and is kept when emptied | A created container is removed; an unreadable existing file is treated as absent |
| Unprojectable | A link, non-regular, unreadable, non-object or duplicate-member `settings.json` is left byte-identical, the link target untouched, resolve refused | Any write through or over it, or a usable resolve |
| Record failures | An unreadable, invalid, unsupported or mismatched record refuses a usable resolve without writes | It is treated as absent, or a fragment is emitted |
| Crash recovery | A crash at each step of the order: before the rename, the unit is abandoned; after the phase-2 journal, the unit completes with its proofs; between the rename and the phase-2 journal, the unit completes with every occurrence `unresolved` | A partial unit is visible to resolve; recovery turns an occurrence `proven` again; compensation overwrites a later operator change or deletes a created file the operator changed |
| Qualification change | A home with a record moved to an unqualified release still refuses a pending journal, a mismatched record and an ambiguous or obsolete occurrence, and gets no edit | The release switch makes such a home usable, or reports a current projection |
| Legacy home | A home without a record on an unqualified release gets no edit and no claim, and is not refused | It is refused, or its equal rules become owned |
| New and existing homes | A home without a record gains the projection at the next repair on a qualified release | A home without a record is refused, or its existing equal rules become owned |
| Writer lifecycle | A supporting reader refuses an unsupported record revision | A claim that an old writer enforces retirement or refusal |

A real Claude Read on a qualified release, with the positive and paired
negatives above, is adapter qualification, not a source fixture.

## Open questions for the operator

1. **File-system evidence for ownership.** Recommended: accept the write
   evidence of section 4 (file identity and status-change time, with the limits
   stated there), which detects an identical rewrite on POSIX file systems.
   Alternatives, if it is not accepted: never retire an introduced occurrence,
   so every obsolete one refuses until the operator removes it; or move the
   projection to a launch-time settings file that Curator owns as a whole, in
   a separate unit.

Resolved by the source owner and applied above: read-scope edits freeze on an
unqualified release, while existing state is still validated; one recovery
evidence file per home, never overwritten; emptied containers are retained.
The whole-array comparison stays as the content half of the evidence.
