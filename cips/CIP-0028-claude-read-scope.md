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
member's working directory. This CIP grants a narrow, literal `Read` allow set
for exactly those paths, on Claude releases for which that grant is qualified.
Retiring a grant is the hard part. Once Curator writes a rule into the
vendor's `settings.json`, the file's content cannot show who wrote an equal
rule later, and file-system metadata is not a general write proof. The CIP
therefore asks the operator to choose between two delivery models (section 4):

- an in-home projection that never retires a grant automatically, so an
  obsolete grant refuses the home until the operator removes it; or
- a launch-time settings file that Curator owns as a whole, passed with
  `--settings`, which removes the merge and the ownership question at the
  cost of launcher and fragment changes.

Frozen markers and locks do not change under either model.

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
4. **In-home projection with a record of introduced occurrences and no
   automatic retirement (option A, section 4).** A private record lists the
   occurrences Curator inserted. Curator never deletes one; an obsolete one
   refuses the home until the operator removes it.
5. **A launch-time settings file that Curator owns (option B, section 4).**
   No merge into vendor state and no ownership question, but it needs fragment,
   launcher, session-manager and SAM policy changes.
6. **Automatic in-home retirement backed by file-system write evidence** (file
   identity and timestamps). Not proposed. Timestamp resolution is
   implementation-defined and may be coarse, so equal metadata does not prove
   that no write happened, and a write right after Curator's own rename cannot
   be told apart from it. Such a backend would need its own separately
   qualified, bounded proposal.

### Recommendation

The operator chooses between options A and B (section 4 and open question 1);
this proposal recommends B. The adopted model then becomes normative amendment
`protocol/claude-read-scope.md` revision 1, with a Decision record, closed
schemas and paired conformance vectors. Grants are activated per Claude
release only by a separate adapter qualification (section 6).

## Security considerations

- Both options grant only `Read`, and only for literal absolute paths: this
  home's declared skill links, their resolved immutable store roots (sub-option
  A2 widens these to the skill's projection), and its own lock's selected
  context member roots. Neither grants an ancestor, the store root, a sibling
  home, Edit or Write, MCP, a permission mode or `additionalDirectories`. Deny
  and ask rules from every source keep precedence.
- A sibling home's link into the same immutable entry is not admitted, because
  its requested path does not match. A retargeted link is not admitted, because
  its resolved path does not match.
- Under option A, the record is accounting, not authorization. Every use recomputes
  the desired scope from the validated lock and store. The record holds paths,
  rule bytes and digests only. It is private machine state and never enters
  packages, locks, fragments, logs or snapshots.
- Writes follow §8.3.1 no-follow atomic replacement. Under option A, a linked,
  non-regular or unreadable `settings.json`, record or journal stops before
  writes. No content compare-and-swap against an external writer is claimed;
  rereading immediately before the rename narrows that race but does not close
  it. Under option B, Curator writes only its own settings file.
- Tool permissions are not an OS sandbox. A running session is not refreshed,
  and no live-session revocation is claimed.

## Compatibility and migration

- Markers, locks and release metadata stay byte-identical under both options.
  Under option A, fragments stay byte-identical too, and the record refers one
  way to the existing marker, by the digest of its exact bytes. No marker field,
  reverse reference, reinterpreted hash, wire change or global lock is added.
  Under option B, the launch plan or fragment gains one member naming the
  settings file, a versioned change of that schema, and a launcher that does
  not pass it gives no grant: the member prompts, which is fail-safe.
- Under option A, a home without a record has no Curator-introduced occurrences. Absence alone
  is neither corruption nor ownership. Its first publication starts from the
  current `settings.json`, and every preexisting equal rule is recorded as
  operator-satisfied. Such a rule never becomes Curator-owned, including after
  later repairs. No explicit adoption step is needed, because absence grants no
  ownership. This differs from CIP-0027, where absence of the record loses
  authority. A valid pre-amendment home converges through ordinary repair.
- **Supported writers.** A supported writer is a Curator release that
  implements `claude-read-scope/1`. Only supported writers insert projected
  occurrences or write the record or the journal. A supporting reader
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

### 1. Grant set (both options; amends §7.4)

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

### 2. Edit grammar, creation and preservation (option A)

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

### 3. Private record (option A; amends §8.3)

A manager-owned, owner-private regular file `.agent-claude-read-scope.json`
beside `.agent-environment.json`, with closed schema `claude-read-scope/1`:

| Member | Meaning |
| --- | --- |
| `record` | Exactly `claude-read-scope/1` |
| `binding` | Profile name, `sha256:` lock identity, managed-home target, and the digest of the exact marker bytes at publication |
| `generation` | Per-home publication counter, incremented by each committed publication |
| `encoder` | Rule encoder revision (escaping, variant and POSIX rules above) |
| `inputs` | Selected skill names with lexical path, resolved root and projection hash version; context member names with store root |
| `introduced` | Every occurrence Curator inserted that has not yet left `allow`, each with its exact rule bytes and the generation that introduced it |
| `satisfied` | Desired rules that were already present when Curator first needed them; operator-owned, never refused over and never retired |
| `created` | Whether Curator created the file, the `permissions` member or the `allow` member |

A rule is *introduced* only if no equal element existed in `allow` immediately
before Curator inserted it. Equal bytes never establish ownership, and the
record is accounting, not proof: it tells Curator which rules it once inserted,
not who owns an equal element today.

### 4. Retirement: decision packet

**Constraint.** Retiring a grant means deleting an element from a file the
operator and the vendor also write. Content cannot show who wrote an equal
element: when the operator removes a rule Curator inserted and adds the same
element back, the file can return to exactly the bytes Curator committed.
File-system metadata does not close that gap in general. Timestamp resolution
is implementation-defined and may be coarse, so equal size, modification time
and status-change time do not prove that no write happened. A write between
Curator's rename and its first metadata capture is indistinguishable from
Curator's own. Any evidence backend would need a separately qualified,
explicitly bounded proposal, and unknown or unsupported evidence could never
authorize deletion. This unit therefore offers two delivery models that need
no ownership proof. The operator chooses one.

**Option A: in-home projection without automatic retirement.** Sections 1–3,
5 and 6 as sketched. Curator inserts desired rules and never deletes one.

- An introduced occurrence that is no longer desired refuses a usable resolve
  with `claude_read_scope_cleanup_required`, naming the rule, until the
  operator removes it from `settings.json`. The next repair then drops it from
  the record. An equal element the operator adds later is the operator's own.
- A satisfied rule that is no longer desired is the operator's and changes
  nothing.
- **Cost.** The resolved-root rule names the immutable entry of one skill
  version (`…/v<n>/<digest>`). Every skill update therefore leaves an obsolete
  introduced rule, and the member refuses until the operator edits
  `settings.json`. So does every dropped skill or context. For unattended
  members, a routine skill update stops launches.
- **Sub-option A2.** Emit the resolved-root rule one level up, at
  `contexts/skill-context/<projection>/**`. Updates of the same skill then
  produce no obsolete rule, and only drops need cleanup. The grant widens to
  every immutable version of that skill's projection.

**Option B: a launch-time settings file that Curator owns.** Curator never
edits the vendor's `settings.json`.

- Resolve publishes, per home generation, a manager-owned, owner-private file
  holding exactly `{"permissions":{"allow":[...]}}` with the rules of section 1,
  written under §8.3.1 no-follow atomic replacement outside `settings.json`.
- The launch carries that file to Claude Code with `--settings <file>`.
  Retirement is publishing the next generation's file. No operator byte is
  touched, so no ownership record, proof or cleanup refusal exists.
- **Required contracts.**
  - A launch-plan or fragment member naming the file (curator-spec).
  - `curator-run` passing it, and refusing when the native arguments already
    carry `--settings` (launcher).
  - Hosted session managers forwarding it (session-manager contract).
  - The SAM Claude permission policy admitting the settings source for the
    release and mode. The proposed 2.1.312 policy row scans an explicit
    settings source on yolo launches and admits a `permissions` member of
    string arrays; other modes need their own check.
  - Qualification that Claude Code adds `allow` rules from `--settings` to
    those of the user settings, while `deny` and `ask` from every source keep
    precedence.
- **Cost and limits.** Work in several repositories before the first grant. A
  session started without the carrier, for example a plain `claude` with the
  home's configuration directory, gets no grant and prompts. That is
  fail-safe.

| Aspect | A (in-home, no automatic retirement) | A2 (A, projection-level rule) | B (launch-time file) |
| --- | --- | --- | --- |
| Operator bytes in `settings.json` | Element insertions, container or file creation | Same as A | None |
| Skill update | Refuses until the operator removes the old rule | No effect | No effect |
| Skill or context dropped | Refuses until the operator removes the rule | Same as A | No effect |
| Grant width | Exact skill version | Every version of the skill's projection | Exact skill version |
| Launch outside `curator-run` | Grants apply (in-home) | Same as A | No grant; prompts |
| Repositories changed | curator-spec, curator | Same as A | curator-spec, curator, curator-agent-launcher, session-manager contract, SAM policy |
| Record, journal, recovery | Needed (sections 3 and 5) | Same as A | Only the file's own atomic publication |

**Recommendation: option B.** It is the only model in which an obsolete grant
leaves without operator work, and it never touches operator bytes. If B is
not chosen, A2 limits refusals to drops. Plain A stops unattended members at
every skill update.

### 5. Recoverable per-home publication (option A; amends §§8.3.1, 8.4.1, 9.2, 10.1)

Add to the §8.3.1 closed lists, with the same no-follow atomic replacement:

- the structured edit or creation of the managed `settings.json` (section 2);
- the record `.agent-claude-read-scope.json`;
- the journal `.agent-claude-read-scope.journal.json`, which holds one
  in-flight unit;
- the recovery evidence file `.agent-claude-read-scope.recovery.json`.

**Targets.** One unit covers `settings.json`, the record, and the marker when
the same repair changes it, under the existing manager-home mutation lock. For
each target the journal holds whether it existed, the digest of its preimage
and its planned postimage digest, plus the input identities and the complete
planned record.

**Order.**

1. The journal is written.
2. `settings.json` is replaced or created.
3. The record is committed.
4. The marker change of the same repair follows the existing marker
   transaction, which stays the commit point of the repair.
5. The journal is removed.

Before each destructive step the writer rechecks that the target still matches
its journaled preimage. A mismatch stops the unit before that step.

**Recovery** runs after a restart, before the home emits any fragment and
before the marker transaction's own recovery. It never deletes an element and
never deletes a file, because deletion would need the ownership proof this
option does not have.

| State found | Action |
| --- | --- |
| `settings.json` still has its journaled preimage bytes (or is still absent) | The unit is abandoned; the record keeps its preimage |
| `settings.json` has the journaled postimage bytes | The unit completes with the journaled record |
| `settings.json` matches neither image | Keep the operator's bytes. Move the journal to the recovery evidence file and refuse until a later repair converges from the current file |
| The record matches neither its preimage nor its planned postimage | Refuse; keep the journal and every file |

The recovery evidence file is kept until a later publication converges, and is
removed in that publication. A second conflict while a recovery evidence file
exists refuses a usable resolve and never overwrites the evidence. No
callback-only recovery is allowed. The external-writer race narrowed by the
preimage recheck stays a stated limit; no exclusion is claimed.

Generations follow §9.2's per-home convergence. A lock change marks the home
stale (§9.2 step 6), and the next repair publishes generation N+1. A lock
change alone is not a global revocation.

**Verification (§10.1).** The integrity checks in the first four rows apply
to every `claude_code` home that has a record, a journal or a recovery
evidence file, whatever release it now selects:

| Condition | Result |
| --- | --- |
| The record is unreadable, invalid, of an unsupported revision, or bound to another marker digest | Refused under the §8.4.1 read-failure row; never treated as absent |
| A journal is pending, or a second recovery conflict exists | Refused until recovery completes |
| An introduced occurrence that is no longer desired is still present | `claude_read_scope_cleanup_required`; refused, no deletion |
| `settings.json` is unprojectable: a link, a non-regular file, an entry that exists but cannot be read, not UTF-8, not a JSON object, a duplicate member name on the edited path, a non-object `permissions`, or a non-array `allow` or one with a non-string element | `claude_read_scope_unprojectable`; stops before writes and refuses a usable resolve. Link targets, every operator byte and the preimages stay untouched |
| Qualified release: a desired rule is absent | Stale; repair converges |

There is no warning-as-success path. A home without a record, journal or
recovery evidence file on an unqualified release is the legacy case. It is
neither corrupt nor owned, gets no edit, and carries no qualification or
no-prompt claim.

### 6. Vendor qualification (CIP-0020 boundary)

The `claude_code` adapter names the Claude releases on which read-scope
grants are qualified. A home requires the grants only when its release is in
that set. Qualification covers grammar and matching on that release, with
positives for own skill links and selected contexts, and negatives for a
sibling home's link, a shared store target, a retargeted link, an unselected
context and another tool's private configuration. Under option B it also
covers how `--settings` rules combine with the user settings. It is admitted
separately from this CIP, and adopting this CIP qualifies no release.

On an unqualified release every read-scope edit is frozen. Documentation
confidence authorizes neither a grant nor a claim that the member will not
prompt. Repair reports `claude_read_scope_adapter_unqualified` with a
qualification hint, as CIP-0020 §5 requires. Under option A, existing record,
journal and recovery state is still validated by section 5 and is never
skipped because of the release selected.

## Implementation plan

1. The operator chooses the delivery model (open question 1). The CIP is then
   revised to that model alone. Publish `protocol/claude-read-scope.md`, its
   closed schemas, a Decision record and paired vectors in curator-spec after
   an exact-head independent review and the required checks. The Decision
   number is the next free one at that time.
2. A separate adapter qualification admits the first Claude release.
3. Successor changes implement the chosen model: in curator for A, or in
   curator, the launcher, the session-manager contract and the SAM policy for
   B. They may reuse the earlier candidate's emission, escaping and variant
   code where it still holds. No implementation starts before step 1 is
   accepted.

## Test plan

Each rule below has a valid control (V) and a forbidden scenario (F). All are
production-entry tests on temporary homes, with mutant controls that must fail
for the named reason.

### Declaration scenarios (both options)

| Declaration | V (granted and matched) | F (never granted or matched) |
| --- | --- | --- |
| Profile declares skill `example-skill` | `<home>/skills/example-skill/SKILL.md` and `.../references/guide.md`, by lexical and by resolved path | A file of an undeclared skill present in the store |
| Profile selects context `example-context` | Its member's store root | An unselected context package, or the store root |
| Two homes share a store entry | Each home's own link | Home A's rules matching home B's link to the same entry |
| A link is retargeted after publication | Nothing for the new target | The old rule matching the new target |
| Outside paths | Nothing | Another tool's private configuration directory, the home outside `skills/`, an ancestor |

### Option A

| Rule | V (must hold) | F (must not happen) |
| --- | --- | --- |
| Literal encoding | Paths with `[ ] * ? \` and spaces match only themselves | An escaped path matches a neighbor; a glob rule is emitted |
| Introduced vs satisfied | A desired rule absent before insertion is recorded as introduced | A preexisting equal operator rule is recorded as introduced, now or after any later repair |
| Operator rule survives | The profile drops skill S: the operator's preexisting equal rule for S stays and nothing refuses | It is removed, or the home refuses over it |
| No automatic retirement | The profile drops a skill, or a skill update obsoletes its resolved-root rule: the introduced rule stays and the home refuses with `claude_read_scope_cleanup_required` | Curator removes the rule |
| Identical rewrite | The operator removes an introduced rule and adds the same element back; the profile then drops it: the rule stays and the home refuses | The rule is removed because the bytes match |
| Cleanup by the operator | After a refusal, the operator removes the rule; repair drops it from the record and converges | A new command is required, or the rule is re-added |
| Preservation | Every byte outside the named spans is identical: whitespace, member order, escapes, number lexemes, `deny`, `ask`, other members, operator allow entries | Any byte change outside an insertion or creation span |
| Creation | An absent `settings.json` is created with only `permissions.allow`; a missing `permissions` or `allow` is created as one appended member | A created container or file is removed; an unreadable existing file is treated as absent |
| Unprojectable | A link, non-regular, unreadable, non-object or duplicate-member `settings.json` is left byte-identical, the link target untouched, resolve refused | Any write through or over it, or a usable resolve |
| Record failures | An unreadable, invalid, unsupported or mismatched record refuses a usable resolve without writes | It is treated as absent, or a fragment is emitted |
| Crash recovery | A crash before the rename abandons the unit; after it, the unit completes; a later operator change is kept with recovery evidence | A partial unit is visible to resolve; recovery deletes an element or a file |
| Qualification change | A home with a record moved to an unqualified release still refuses a pending journal, a mismatched record and an obsolete introduced rule, and gets no edit | The release switch makes such a home usable |
| Legacy home | A home without a record on an unqualified release gets no edit and no claim, and is not refused | It is refused, or its equal rules become owned |
| Writer lifecycle | A supporting reader refuses an unsupported record revision | A claim that an old writer enforces refusal |

### Option B

| Rule | V (must hold) | F (must not happen) |
| --- | --- | --- |
| Carrier | A `curator-run` launch passes exactly the current generation's file with `--settings`; a hosted launch forwards it | A launch carries another generation's file, or none while claiming the grant |
| No vendor-file edit | `settings.json` is byte-identical before and after every resolve | Any write to it |
| Retirement | A dropped skill or a skill update is absent from the next generation's file, with no refusal | An obsolete rule survives in the current file |
| Operator `--settings` | Native arguments that already carry `--settings` refuse before launch | Two settings sources are passed, or one replaces the other silently |
| Precedence | An operator `deny` or `ask` for a granted path still applies | The carrier overrides it |
| Outside the carrier | A plain `claude` with the home's configuration directory gets no grant | A grant appears without the carrier |

A real Claude Read on a qualified release, with the positive and paired
negatives above, is adapter qualification, not a source fixture.

## Open questions for the operator

1. **Delivery model.** Recommended: option B, a launch-time settings file that
   Curator owns, because it retires grants without operator work and never
   touches operator bytes, at the cost of changes in several repositories.
   Alternatives: option A2 (in-home, projection-level resolved rule; refuses
   only on drops until the operator cleans up) or option A (in-home, exact
   rule; refuses after every skill update until the operator cleans up). A
   file-system evidence backend for automatic in-home retirement is not
   proposed here; it would need its own separately qualified, bounded
   proposal.

Resolved by the source owner and applied above: integrity checks run whatever
the release; read-scope edits freeze on an unqualified release; one recovery
evidence file per home, never overwritten; emptied containers are retained.
