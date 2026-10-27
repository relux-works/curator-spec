# Profile command root and launcher PATH companion

Status: unreleased specification allocation, not implementation or runtime
qualification. This is the detailed companion to environments
[§9.4](environments.md#94-profile-scoped-skills-and-migration) and
[§10.2](environments.md#102-the-launch-environment-fragment).

## 1. Availability and rollout

Command selection comes from the admitted lock's skill plan, not installed
shims or ambient PATH. Apply these rows in order on each new agent process,
including one-shot and restart/resume that creates a child:

| Condition | Root decision | Launch result from this companion |
| --- | --- | --- |
| No active command exports | `none`, no root or `path_prepend` | Proceed, no commands-unavailable diagnostic |
| Hosted, command exports, no jointly supported carrier | Explicit `empty`, reason `hosted-carrier-unavailable` | Proceed with commands-unavailable diagnostic; no profile prepend |
| Slice A, command exports, selected profile not machine-current | Explicit `empty`, reason `slice-a-non-current` | Proceed with commands-unavailable diagnostic; no profile prepend |
| Native Slice A, command exports, selected profile machine-current | `active`, independently verified isolated current root | Apply verified `path_prepend`; verification failure refuses |
| Hosted with jointly published and supported carrier | Same availability rules, carried to final child | Apply and witness only after independent hosted qualification |

`empty` is an explicit **zero-command root decision**, represented by null
root/receipt and omitted `path_prepend`, never an empty PATH component, `.`,
an inherited singleton root, or a new field smuggled into an old wire object.
The current-profile fact comes from protected manager routing records, never
profile or environment assertions. The diagnostic MUST state why, for example
`profile commands unavailable: slice A serves only the machine-current profile`
or `profile commands unavailable: hosted command carrier not available`.
It is informational and MUST NOT itself refuse launch. `none` differs from
`empty`: no commands were requested. Other existing launch gates still apply.
Neither unavailable case may be reported as successful command delivery.

Native delivery comes first. `launch-delegated/1` has no PATH member and its
reserved `child_env` names cannot carry PATH. It MUST stay closed. A joint
hosted carrier amendment (for example `launch-delegated/2`) is a dependency,
owned by **curator-run and the session host** (tb-sessiond / swarma-session-host),
with Curator for root binding. It must publish required-understanding
capability, request/schema/module pins, effective PATH, root/receipt binding,
start verification and manager provenance together. This document allocates
no such hosted request. Until then, the caller records the explicit empty
decision and diagnostic locally; it does not claim this metadata or a changed
PATH reached the old hosted child. Ordinary hosted launch remains available.

Slice A can satisfy the owner's command requirement for the current profile
now, after native qualification. Slice B must deliver every selected profile's
lock-bound generation root, including concurrent different command versions,
with joint root/carrier/lease/GC publication. Active and retained generations
must stay live; updates cannot retarget a running process. The combined
completion/adoption gate `profile_skill_companion_required` remains until the
required allocations and applicable native/hosted/all-profile qualifications,
including protected-command admission, exist. Empty-root launch permission
does not clear it.

## 2. Closed root receipt and independent verification

Curator publishes the closed
[`profile-command-root/1` receipt](../schemas/profile-command-path-v1/root-receipt.schema.json)
as `.curator-profile-command-root.json` in an active command root. It is a
regular protected metadata file, not a command. It contains the selected
profile, complete CCJ-1 lock digest, plan digest and generation; root metadata;
and the complete root command inventory with each shim/target chain. All selected
active exports must be present. Already-retained exports may appear only with
their existing protected ownership/generation records under the carrier
proposal's selective-preservation rule; they are not re-resolved or newly
activated by this companion. Unknown root commands refuse. Artifact
hashes stay outside the portable lock. Commands sort by name, uniquely under
the target lookup rules; chain order is execution order. Every first hop is
`root/name`; each nonfinal hop points to the next; the final hop is the reached
executable with null target. Digests are SHA-256 of exact file bytes, or UTF-8
link text for a symlink, without newline insertion. The receipt itself is
hashed from its exact UTF-8 bytes, not recursively embedded in itself.

The closed metadata variants are POSIX owner ID, device/inode identity and
permission mode; or Windows owner SID, volume/file identity and native security
descriptor digest. Identity strings carry the platform's lossless native
values; they are never inferred from path spelling. A descriptor digest alone
does not prove its ACL safe. The protected generation/source/driver records
and section 4's boundary checks remain the trust anchor. A receipt cannot
authorize its own owner, admitted cache roots or permissions.

curator-run MUST perform this read-only procedure independently, rather than
trusting Curator's `verified` assertion:

1. Obtain the selected complete lock, admitted plan and protected generation
   records from the independently admitted manager boundary. Recompute CCJ-1
   lock and plan digests; compare fragment profile/pin, plan selection/source
   pins, generation and receipt binding. Verify receipt schema and canonical
   command order/completeness against the selected plan and protected generation
   records, including existing retained-owner references.
2. Starting from the trusted manager and cache boundaries, inspect each path
   component without following unchecked links. Root and receipt are directory
   and regular file respectively, owned by the expected operator. The root
   is not a symlink. Receipt metadata cannot enlarge the admitted boundaries.
   On POSIX, require expected UID, no group/other mutation bits (`mode & 0022`
   is zero), no special permission bits, and owner read/search for directories,
   read for receipt/data, read/execute for executables. On Windows, independently
   verify owner SID and the section 4 private-mutation DACL equivalent, then
   compare the native descriptor digest with the protected admitted record.
   POSIX symlink mode bits are not mutation authority; verify its owner,
   identity and protected parent instead. Inability to prove native access
   semantics refuses verification.
3. Compare root and every hop's filesystem/object identity, type, owner and
   access metadata with the protected generation record and receipt. Verify
   confinement at every hop to the admitted root/cache boundaries, using
   component and filesystem identity, not string prefixes. Unlisted executable
   root entries, special files, hard-link aliases, cycles, missing or unreadable
   components refuse. Only declared command shims may be links; the receipt
   and surrounding directory boundaries remain link-free.
4. Read each declared shim and target through the checked boundary, recompute
   its digest, and compare with both receipt and protected generation records.
   Decode symlink text or the admitted trusted driver's forwarding format
   without executing it. The decoded target must equal the next hop. Unknown
   forwarder formats, hidden extra hops or a final artifact disagreeing with
   its admitted selected/retained export refuse. Never execute a shim to discover trust.
5. Hold Slice A's supervisor-issued exclusive routing admission over verification
   and process start, serialized with routing mutation under its existing
   contract. Recheck identities, access, bytes and binding at that boundary;
   substituted or stale evidence refuses with no repair, re-resolution,
   singleton fallback or provider start. A current root with unproven routing
   is an integrity refusal, not the non-current-profile availability case.

The current-profile test precedes any attempt to verify that profile through
another profile's singleton root. No-export and unavailable cases do not
require an active receipt. These checks do not replace source/signer, driver,
reserved-name or command-inventory admission. Same-user mutation between check
and use remains a residual unless held handles or equivalent enforcement close
it. Schema validity and abstract filesystem facts do not qualify any platform.

## 3. PATH construction and admission

Construct once: **protected tools → active verified profile root → admitted
base PATH**. With `none` or `empty`, the middle list is empty. Interactive
native launches have an empty protected-tools list by default. An operator
may configure one Curator-owned directory; verify its boundary with section 2
and place it first. Profile or project data cannot choose it. Managed or
unattended executor D-PATH protected-directory/dispatcher rules remain in force.
Never invent a workstation protected directory or promote an inherited one.

Classify base components in original order using the following closed set.
Use the target platform's PATH separator, absolute-path and identity rules;
no component, including an active root, may contain that separator.
The POSIX fixture strings in the corpus do not qualify Windows parsing.

| Predicate | Exact meaning | Interactive native | Unattended or managed |
| --- | --- | --- | --- |
| empty | Zero-length component | Drop | Drop |
| relative | Not an absolute directory path | Drop | Drop |
| non-canonical | Contains a `.` or `..` path segment | Drop | Drop |
| control-characters | Contains U+0000–001F or U+007F–009F | Drop | Drop |
| unreadable | Cannot establish directory identity, read/search access or safety metadata; includes missing/non-directory entries | Drop | Refuse |
| world-writable | Anyone/everyone can mutate the directory; POSIX other-write bit, or native equivalent | Drop | Refuse |
| duplicate | Same platform-normalized path as an earlier retained component or protected/profile root | Drop later entry | Drop later entry |
| alias | Different spelling resolves to the same directory identity as an earlier retained component or protected/profile root | Drop later entry | Drop later entry |

Evaluate empty/relative first, then control-characters/non-canonical, then
unreadable/world-writable before deduplication: an alias cannot hide an unsafe
directory. The two new spelling predicates are benign drops on both policies,
not refusals. A segment is delimited by the target platform's path separators;
`.hidden` and `..hidden` are not dot segments. Do not lexically rewrite or
resolve away a rejected spelling: traversal through a symlink can change
identity. Retain the checked canonical, control-free absolute spelling and the
first admitted identity.
User-writable directories are not world-writable merely because the operator
can write them; this is not a rule rejecting all developer PATH directories.
Interactive native means the operator's interactive route. Trusted supervisor
or executor admission selects managed/unattended policy; that stricter policy
wins in overlap. Selecting a profile alone does not turn a workstation
interactive launch into an unattended one; a caller cannot downgrade a managed
launch by claiming a terminal.

On any drops or refusal, emit exactly one admission diagnostic line listing
the offending entries in input order with their predicates and actions.
Escape control characters so an entry cannot forge another line. A refusal
starts no provider and leaves live state unchanged. A valid launch with drops
records the retained PATH and separately lists profile-root source exclusions;
it does not silently change lookup. This line is separate from an availability
diagnostic, when both are applicable.

Before generic base admission, remove inherited entries within **known
manager-published profile command-root namespaces**, including the selected
root; only the newly verified root may enter the middle list. Record these as
root-source exclusions in the same line. This is authority separation, not a
further generic PATH safety predicate. Resolve aliases before exclusion;
unreadable evidence follows the unreadable rule. An arbitrary unrecognized
directory is not labeled foreign by spelling alone; the separate protected
command-admission companion covers dynamic command collisions. Empty-root
launches must not borrow another profile's exports. On the old hosted route,
the caller can exclude its own roots but cannot assert control over daemon
PATH; no final-child command delivery or isolation is claimed there.

**Nonempty final PATH.** The composed PATH MUST contain at least one admitted
absolute directory. If no base entry remains (including an empty input), scan
only the fixed platform default list through the same predicates, authority
exclusions and identity deduplication against protected tools. On Unix the list
is exactly `/usr/bin`, `/bin`, `/usr/sbin`, `/sbin`, in that order. Keep only
admitted defaults, after protected tools and any active root; record default
selection and its drop/refuse decisions in the same admission diagnostic line.
Do not retry a managed unreadable/world-writable refusal with defaults. An
unsafe default also follows that policy; the fixed list grants no trust.
Another platform needs its fixed native list published with its supported
launcher contract; neither inherited PATH nor CWD supplies a default.

If protected tools, active root and admitted base/defaults together contain no
directory, refuse before child start with the distinct launcher diagnostic
`launch_path_unavailable`. Never serialize or deliver an empty PATH string,
an empty component, `.` or an implicit CWD fallback; emit no successful state
record for this refusal. An already-admitted protected directory or active
root can satisfy the nonempty invariant when no base/default survives.
This is PATH-safety refusal, separate from B1's prohibition on refusing merely
because profile commands are unavailable. It allocates no hosted wire code.

Apply the constructed value to the actual native child, overriding inherited
module PATH; do not recompose after a later ambient change. Preserve existing
dispatcher placement/authentication and heavy-command gates. Existing
`command_environment` plus `path_prepend` remains forbidden until a joint
combined carrier is published. A no-prepend availability case does not invent
that combination.

## 4. Provenance and witnesses

For native launch curator-run MUST durably publish a per-launch state file
under `${XDG_STATE_HOME}/swarma/launcher/` (`${HOME}/.local/state` is the state
home when unset), before child start. Use an unpredictable launch identifier,
an operator-owned directory with private mutation permissions and a regular
owner-only file, no symlink traversal, exclusive creation and atomic publish.
It records the closed
[`launcher-path-state/1`](../schemas/profile-command-path-v1/launcher-state.schema.json)
shape: nonempty canonical, control-free absolute PATH components and their
nonempty serialized value, exact fragment digest,
profile/lock/plan binding, generation, availability, root/receipt digest or
explicit nulls, and admission diagnostic entries. Failure to safely persist
refuses before start. Do not log the full environment, credentials or argv.
The record is provenance, not authority, session identity or runtime proof.

The future hosted request and manager session record MUST carry the same
PATH/binding/provenance, covered by the process digest for exact-plan execution
or the jointly published delegated contract. The host must verify at its start
boundary and preserve the sealed value without merging daemon PATH. Dropping
a negotiated active root refuses. This applies after the hosted carrier exists;
before then the explicit empty decision is only caller-local provenance.

Conformance for **active delivery** requires all three correlated final-child
witnesses: actual serialized/parsed PATH; command actually reached as artifact
path plus digest, including shim chain; and binding to the complete lock,
plan and generation. A no-export or empty launch instead proves no profile
prepend, no borrowed export and the correct availability/diagnostic. Hosted
without-carrier proves continuation and caller decision only, not an assertion
about inaccessible child PATH. Each route/form/platform needs real independent
qualification. The [closed corpus](../conformance/profile-command-path/README.md)
provides paired specification controls; it launches no product.
