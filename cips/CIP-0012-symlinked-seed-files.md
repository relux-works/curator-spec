# CIP-0012: Symlinked seed files

- **Status:** Rejected (provisional; operator, 2026-10-11)
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-11
- **Related:** [CIP-0001](CIP-0001-curator-improvement-proposals.md) (proposal process)
- **Affects:** protocol/environments.md §8.4.1 (no change)

## Operative summary

| Field | Contract |
|---|---|
| Purpose | Record the provisional rejection of admitting symlinked provisioning seeds. |
| Boundary | Seeds remain regular files; a link is unreadable, never absent and never copied through. |
| Authority owner | Operator decides the disposition; the installer owner performs host migration; Curator enforces the existing seed rule. |
| Inputs → outputs | Installer-linked native configuration and the operator's retirement decision → this rejection record and a one-time host migration; no new Curator behavior. |
| Normative links | [Environments §7.4](../protocol/environments.md#74-credential-passthrough-provisioning-seeds-and-isolation), [§8.2](../protocol/environments.md#82-environment-marker-schemas-1-through-3), [§8.4.1](../protocol/environments.md#841-absence-versus-read-failure), [§10.1](../protocol/environments.md#101-env-resolve); all unchanged. |

## Summary

A separate agent-tooling installer creates native configuration symlinks that
conflict with Curator's regular-file provisioning-seed rule. On 2026-10-11 the
operator chose host migration when that installer is retired within days,
retaining the strict rule in environments §8.4.1. Option (b), constrained
symlink admission, is **Rejected (provisional)**. A new revision of this CIP
may revisit it if real Curator users need symlinked seeds or a successor
installer must keep links; this record makes no normative change.

## Motivation and user stories

An operator on a shared host needs a managed Codex home to provision or recover
from staleness without weakening the rule that read failure is not absence.
The separate installer, agents-infra, installs `~/.codex/config.toml` as a
symlink to `~/.agents/.configs/codex-config.toml`. It also links
`~/.claude/settings.json` and Codex rules files. Central edits propagate through
these links, but the Codex configuration link is not an admissible seed.

A user of a dotfile manager, such as stow or chezmoi in symlink mode, could
encounter the same conflict independently of this installer. That possible
future need is a revisit condition, not an adopted feature or scheduled work.

## Current state

[Environments §7.4](../protocol/environments.md#74-credential-passthrough-provisioning-seeds-and-isolation)
declares the seed classes. Among the installer-linked files described above,
only `codex_cli` `config.toml` is copied as a seed: revision A copies it whole;
revision B strips the native `mcp_servers` table and its sub-tables.
`claude_code` `.claude.json` is written as a minimal object, not copied, and a
Claude `settings.json` seed is not declared in revision 1. The linked Codex
rules files are not declared provisioning seeds in §7.4.

The seed rule in §7.4 near the isolation matrix explicitly treats a symlink,
directory, or special file as unreadable-side. The provisioning-seed row of
[§8.4.1](../protocol/environments.md#841-absence-versus-read-failure)
requires `environment_seed_unreadable` and stops provisioning before the first
write. Curator never copies through the link or skips it as absent. Seeds are
one-time, thereafter tool-owned: §7.4 currently excludes them from hashes and
drift checks, and §8.2 records them by home-relative path.

The operator-provided incident account reports first provisioning or stale-home
repair refusing on the linked Codex seed. It also reports a later Curator
release candidate returning `environment_home_stale` with the reason
`passthrough: environment_seed` even on plain resolve, leading to a repair
that refuses. A released board-tool harm-reduction change avoids `--repair`
on its primary path and helps only while the home remains current. These are
reported implementation observations, not probes rerun for this CIP; no
implementation revision or independent runtime measurement is claimed.
[§10.1](../protocol/environments.md#101-env-resolve) supplies the normative
stale-home and repair rules, not evidence that this particular release-candidate
reason is specified.

## Design

### Options considered

| Option | Mechanism and benefit | Cost and security analysis | Disposition |
|---|---|---|---|
| (a) Host migration | Convert the installer's links once into regular files with the same bytes; Curator needs no change. | Central edits cease propagating automatically. Re-running the installer recreates links unless it changes or is retired. Migration must preserve bytes, user ownership, and safe permissions without broadening Curator's read boundary. | Selected at installer retirement. |
| (b) Constrained symlink admission | Amend §8.4.1 to admit a user-owned link to a same-user, regular, protected target inside that user's HOME; record target identity and report later changes as drift. Avoids host migration and could support dotfile managers. | Introduces a target-resolution and TOCTOU surface, new marker semantics, and an exception to the no-copy-through-link boundary. Same-owner admission does not help Nix home-manager links into a root-owned store; widening ownership would require a separate trust decision. | Rejected (provisional). |
| (c) Harm reduction outside Curator | The board tool avoids `--repair` on its primary path, reducing unnecessary repair attempts for a current home. | Necessary but insufficient: first provisioning and actual stale-home repair still meet the strict seed rule; it cannot make a linked seed admissible. The caller must preserve Curator refusals. | Retain as harm reduction, not a resolution. |
| (d) Silent copy through the link | Follow the link and copy target bytes without a new admission contract. | Violates the current seed rule and security boundary; target substitution and unintended cross-user or out-of-HOME reads become possible. | Rejected. |
| (e) Treat the link as absent | Skip the linked seed and continue provisioning. | Violates “read failure is not absence”; silently loses configuration and turns an unreadable entry into an absence-shaped action. | Rejected. |

### Recommendation

The operator decided on 2026-10-11 to retain §8.4.1 and choose (a), with (c)
as interim harm reduction. The installer is being retired within days. At its
retirement, its symlinks are converted once into regular files with the same
bytes on every machine where it was installed; until then, its setup is not
re-run. This is a host-operation decision, not work implemented by this CIP.

Option (b) remains **Rejected (provisional)**. Revisit through a new revision
of this CIP only if real Curator users require symlinked seeds, for example
through dotfile managers, or a successor installer must retain links. No new
mode, configuration key, default, or refusal code is adopted.

## Security considerations

Native configuration is an input to provisioning, not authority to traverse
arbitrary paths. A link can redirect a read across user or HOME boundaries,
select an unintended file, or reach a directory or blocking special file.
Checking a target and then reopening a pathname introduces a substitution
window. An `O_NOFOLLOW`-class check on the final component alone does not
establish that ancestor components are free of links or protected against
replacement. A future design would need a descriptor-relative walk or an
equivalent demonstrably safe no-follow resolution and open.

The proposed same-owner and non-group/world-writable checks would narrow
admission but would not prevent the owning user from changing a target. Target
identity and digest records would need to identify such changes as drift,
never silently refresh seeds. This is a proposed exception to the one-time,
non-drift-checked seed model of §7.4, not a property of the current marker.
Under [§8.2](../protocol/environments.md#82-environment-marker-schemas-1-through-3),
the marker is a record, not a signature; adding identity metadata would not
turn it into authorization or protect against all same-user interference.

No credentials or configuration contents are published by this record. Any
future evidence would need to avoid copying configuration secrets into logs
or marker diagnostics. Options (d) and (e) cannot serve as fallbacks when
admission cannot be established.

## Compatibility and migration

Curator behavior, marker schemas, existing home state, seed-rule revisions,
and refusal codes remain unchanged. Host migration replaces the installer's
symlinks with regular files containing the same bytes; it does not re-seed
existing managed homes. The central source ceases to propagate edits through
those links. Future native edits continue not to propagate into existing
managed seeds under §7.4. A stale or unprovisioned home still follows §10.1
and the existing provisioning requirements after host migration.

The installer owner owns conversion on every affected machine and avoiding
setup re-runs before retirement. This documentation task neither performs nor
attests that migration.

## Specification changes

None. `protocol/environments.md`, including §8.4.1, is unchanged. No normative
prose, schema, decision record, or conformance vector is changed. This CIP and
its README index row only record the provisional rejection.

## Implementation plan

**Conditions for a revisit of (b), not planned work.** A future revision would
need an operator-approved admission and drift contract before implementation:

1. Both the link and its final target would need to be owned by the home's
   user; the target would need to resolve inside that user's HOME, be a regular
   file, and not be writable by group or others.
2. Resolution would need to admit exactly one link hop, then open the resolved
   target without following further links using an `O_NOFOLLOW`-class open or
   descriptor-relative walk. Ancestor traversal and check/open races would
   need an explicit safe contract, with validation bound to the opened object.
3. The marker would need target identity metadata: resolved path, device/inode,
   and digest. Field names, schema versioning, compatibility, and how identity
   is measured would need specification; these are not existing marker fields.
4. A later target identity or content change would need to report drift and
   never silently re-read or re-seed from the changed target. The revision
   would need to reconcile this with §7.4's one-time seed rule and define its
   relationship to §8.2, §8.4, §8.4.1, and §10.1.
5. Any widening beyond same-owner, inside-HOME targets would need a separate
   trust decision. Supporting a root-owned store is not implied by (b).

## Test plan

**Qualification conditions for a revisit of (b), not planned or executed
tests.** A future revision would need tests through actual provisioning,
resolve, and repair entry points, alongside conformance vectors for its
adopted contract. Positive coverage would need a qualifying one-hop seed and
an ordinary regular seed, with existing Codex seed transformations preserved.
Negative coverage would need at least:

| Input or change | Property the future design would need to prove |
|---|---|
| Link owned by another user, or link to another user's file | Same-user ownership is enforced for both link and target. |
| Link outside the user's HOME | Resolution cannot escape the admitted HOME boundary. |
| Chain of links, including a linked ancestor in the resolved path | The one-hop and no-further-links constraints hold for the actual open. |
| Link to a directory or FIFO | Only regular targets are read; a FIFO cannot block provisioning. |
| Group-writable or world-writable target | Unsafe target permissions are refused. |
| Target swapped between check and open, including ancestor replacement | The opened descriptor identifies the validated object; no substituted bytes are adopted. |
| Target path, device/inode, or content changed after provisioning | Drift is reported; the target is never silently re-read as a replacement seed. |
| Missing seed contrasted with unreadable or dangling link | A read failure never triggers the absence fallback. |

Tests would need to narrow each ownership, boundary, link, permission, and
identity gate and demonstrate that the corresponding negative case fails,
including real filesystem race coverage on supported platforms. A passing
helper test alone would not establish that production opens enforce the rule.
No runtime behavior is changed or tested by this rejected proposal.

## Open questions for the operator

None for the present disposition. The operator's 2026-10-11 decision retains
the regular-file rule and selects migration at installer retirement. Evidence
of an actual need from Curator users or a successor installer is the condition
for reopening (b); its admission, marker, drift, and qualification questions
would belong to that future revision.
