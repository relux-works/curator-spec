# Decision 0016: skill command roots in managed homes

## Status

Status: proposed — not adopted

Proposed 2026-09-15. DRAFT for review under TASK-260908-1e55lp,
EPIC-260908-2wp8wn, migration workstream B7. No option is selected.
Filing this proposal authorizes no implementation, workaround, normative
amendment, or landing of the draft.

## Context

[Environments 1.1](../protocol/environments.md) §9.4 materializes a
profile's skills but forwards commands through a singleton user-bin
directory for the machine-current profile. Sections 9.2–9.3 distinguish
machine switching (which repoints shims) from scoped switching (which
does not). A managed launch inherits machine shims, so another profile's
commands may be visible or the desired command may be absent.

Section 10.2 reserves `path_prepend` as one absolute path below the
manager-owned environments root; revision 1 never emits it.
Sections 10.3 and 11 preserve the package-influence boundary and trusted
umbrella discovery. Section 9.4 already prohibits skill-published
executables whose names begin with `curator-`.

The migration input is the 2026-09-07
`agents-infra-to-curator-mapping.md` precondition resource on
EPIC-260908-2wp8wn,
under “What agents-infra installs today.” It is a historical migration
inventory, not evidence of current runtime behavior. The epic's
`goal-launcher-and-infra-migration.md` precondition on the same epic,
workstream B7, asks for this gap to be filed without a workaround.

The mapping's `agents-attachments` CLI row identifies this as a partial
migration: skill-shipped CLIs only reach managed launches through the
machine-current profile's shims.

## Gap statement

A managed home's installed skill set does not imply matching command
availability. There is no emitted profile command root. Switching the
machine profile around a launch or installing extra wrapper layers would
not resolve concurrent profiles or declare command ownership.

## Options and trade-offs

1. **Retain machine-current shims.** Keep the documented limitation and
   make profile mismatches visible to operators. This requires no new
   command surface, but cannot isolate concurrent profiles or guarantee
   that a managed launch uses its own skill commands.
2. **One mutable command root per profile.** A future manager could
   materialize forwarding shims under its environments root and emit the
   reserved `path_prepend`. This fits the fragment's single-path shape
   and gives concurrent profiles separate namespaces, but updating a
   profile could change command targets under a running session.
3. **Immutable roots bound to a profile lock and build identity.**
   Materialize a command root for a resolved generation and pin each
   launch to it. This supports stable concurrent launches and inspection,
   but needs build/artifact identity beyond source pins, atomic publication,
   live-session retention, and garbage collection rules. A lock hash alone
   is not evidence that a platform binary is available or valid.
4. **Explicit manager-mediated command invocation.** Consider a future
   invocation contract selecting profile and command without PATH
   injection. This makes resolution explicit but changes CLI ergonomics
   and does not make bare commands work inside tools. It needs a separate
   ownership review against the existing skill runtime boundary.

## Open questions

1. Does a command root belong to a profile, a lock, a managed home, or a
   platform-specific build generation? What records bind a shim to its
   audited skill and produced executable?
2. Which duplicate command names are refused, and how are collisions with
   machine executables handled? The existing `curator-` exclusion stays
   in force; no option grants skills umbrella subcommands.
3. Does prepending one root intentionally allow missing commands to fall
   through to machine shims? If isolation is required, what separately
   declared policy prevents that fallback without replacing PATH ad hoc?
4. Who validates containment, symlinks, executable availability, and
   reserved names at materialization and immediately before launch?
   How are partial builds, drift, and stale roots reported?
5. When may update, removal, or GC reclaim a root used by a running or
   resumable session? How are old readers and absent `path_prepend`
   handled during capability rollout?
6. What platform-specific evidence is required for forwarding behavior,
   executable naming, PATH ordering, and cross-profile collisions?

## Compatibility and security impact

Revision 1 continues to omit `path_prepend`; no shims or command roots
are created by this filing. Adoption needs a separately reviewed versioned
contract and tests at materialization and launch boundaries, including
reserved-name rejection, containment, command collisions, and stale-root
behavior. Prebuilt CLI distribution and compiler bootstrap stay deferred.
