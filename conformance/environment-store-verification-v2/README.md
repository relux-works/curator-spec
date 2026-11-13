# Environment store verification, revision 2 (unreleased proposal)

This corpus proposes the incompatible structural-before-repair behavior in
[the revision-2 contract](../../protocol/environment-store-verification-v2.md).
It does not change the released revision-1 corpus, select a runtime configuration
schema or establish implementation qualification.

## Coverage and carriers

`manifest.json` records all 38 predecessor rows and their exact original
diagnostic/outcome, successor and disposition. The predecessor's file hash is
checked. The case carrier is a closed nonempty JSON array, with an explicit
revision-2 discriminator on every case. A legacy object reader cannot consume
it as an empty set of revision-1 case groups. Missing, unknown or mixed
discriminators, duplicate keys, unknown fields and old object carriers refuse
before case evaluation. `cases.schema.json` and `manifest.schema.json` define
the closed proposal metadata; the Go reader adds semantic checks.

The 24 legacy resolve and status rows retain the released drivers'
path/state fixture roots (`source_kind: path`). The four dry-run rows remain Git;
the ten repair rows retain their explicit Git/path/local mapping. Labelling
those 24 as Git would replace their predecessor fixture. Mapping controls reject
both that substitution and a dry-run Git row relabelled as path.

The original 104 cases comprise 12 intact neighbors, 38 predecessor dispositions and
54 structural refusals: context/MCP/skill members, six boundary violations and
resolve/repair/dry-run, each at levels 1, 2, 3 and 4. For level 4 the fixture has
no centre configured and must use the specified level-3 fallback with a warning.
Other local checks pass. Strict ordinary-byte and home restoration cases apply
at levels 3 and 4. These are not additional runtime diagnostic codes.

Twenty-six additional cases distinguish whole-entry absence from missing payloads
for context, MCP and skill members: strict Git repair restores the same pin;
permissive repair and all read-only calls refuse without writes; strict Git
dry-run reports the existing plan without writing; permissive dry-run refuses;
strict context path/local repair has no Git snapshot and refuses without writing.
Missing named payloads remain structural refusals for resolve, repair and
dry-run at all four levels. The complete proposal now has 130 cases: 124 implementation rows/444 declared
level slots and 6 checker controls/22 slots (466 total). These
fixtures require safe existing ancestors, exact no-follow leaf `ENOENT`, all
other selected members checked before any write, and repeated authority and
boundary checks under the lock and before publication. A late structural plant
must survive its named refusal. Missing ancestors and ambiguous metadata are
never equivalent to whole-entry absence.

A predecessor pointer is part of the fixture definition: replay MUST preserve
that row's original `object`, `surface`, source kind, home state and plant,
including enclosing roots, locks and markers. The case's `condition` is a
summary, not permission to replace an enclosing-boundary test with an entry test.
New matrix cases plant the named condition in the selected immutable member.
Managed adapter links remain outside payload-link plants.

Every implementation case has a matching intact member/operation neighbor.
`expected` describes the required primary diagnostic and observable post-state.
`writes` lists observable product-state changes; permitted rejection telemetry is
excluded. Same-pin recovery for an already-current home changes only the store;
stale or absent homes retain their required home and marker restoration.
Runtime witnesses preserve bytes, types, link targets, identity and mtime, with
paired known-write controls. These poststate witnesses do not prove the absence
of every syscall that leaves the same observable state.
An intact dry-run may return the existing current fragment without writing.
Every fatal case preserves its plant and lock, performs no repair write and
emits no fragment. A runtime driver additionally asserts the original home and
marker bytes, no payload-link traversal and zero child execution.

`forbidden_observations` are deliberately nonconforming observations, not
alternative successful outcomes. Historical known-bad rows remain checker
controls. The metadata checker rejects each recorded counterexample and accepts
its required observation; it cannot manufacture a real manager observation.

## Retained member-source admission

The existing lock4/lock6 carriers admit state pins only for context members;
MCP and skill members retain Git sources. The case schema and Go checker
reject other member/source combinations before interpreting observations.
Context path/local and Git MCP/skill cases remain valid positive neighbors.

The following four unreleased rows are removed; no predecessor row is removed.
Each disposition is **unreachable: lock4/lock6 Validate refuses MCP/skill
path/local state pins (contextlock.go:294-295)**.

| Removed row | Member/source |
| --- | --- |
| `mcp-path-repair-strict` | MCP/path |
| `mcp-local-repair-strict` | MCP/local |
| `skill-path-repair-strict` | Skill/path |
| `skill-local-repair-strict` | Skill/local |

Paired metadata controls reject reintroduction of each forbidden combination.
Implementation qualification must also assert the exact retained lock refusal
under both schemas with valid context and Git neighbors. If those carriers
change to admit a combination, that regression must fail and coverage must be
reconsidered. This proposal expands no runtime package or lock admission.

## Changed predecessor expectations

| Predecessor row | Previous diagnostic/outcome | Revision-2 requirement |
| --- | --- | --- |
| `dry-run-untrusted-reports-would-rebuild` | `would-rebuild-untrusted-store` | `environment_store_untrusted`; preserve the violation; no repair plan |
| `repair-path-entry-cannot-rebuild` | `environment_repair_failed` | `environment_store_untrusted` before attempting repair |
| `repair-local-entry-cannot-rebuild` | `environment_repair_failed` | `environment_store_untrusted` before attempting repair |
| `repair-rebuilds-entry-boundary-failure` | Success, rebuild and fragment | `environment_store_untrusted`; no rebuild or fragment |
| `dry-run-mutates` (already known bad) | Mutation with `would-rebuild-untrusted-store` | Remains negative; required observation now refuses structurally without mutation |
| `repair-reapplies-untrusted` (already known bad) | Reapplication followed by `environment_repair_failed` | Remains negative; required observation refuses before reapplication |

The last two rows change their required counterfactual observation, not a
previously accepted implementation behavior. All other predecessor rows retain
their disposition. In particular these positive repairs remain:

- `repair-rebuilds-git-entry-from-snapshot`;
- `repair-stale-old-marker-succeeds`;
- `repair-swapped-old-marker-never-adopted`;
- `repair-unprovisioned-intact-provisions`;
- `repair-unprovisioned-swapped-rebuilds`.

Ordinary-byte repairs restore the same verified recorded pin; home repairs use
verified inputs and the existing atomic transaction. They never accept a changed
expected identity or turn a structural violation into a rebuild.

## Tools and evidence

From the specification checkout:

```sh
go test -p=1 -parallel=1 ./tools/check-store-verification-v2
go run -p=1 ./tools/check-store-verification-v2 -root .
# Equivalent combined target:
make store-verification-v2-check
```

The checker reads only the proposal and predecessor files and writes no product
state. Tests use in-memory mutations. CLI output reports metadata/control
validation, not runtime conformance. Duplicate/version/shape refusals, missing
coverage, changed predecessor identity and undetected counterexamples have
paired valid controls.

Runtime qualification remains separate and pending. It must execute the actual
version-aware reader, both carrier directions, all fixture entry points,
post-failure state, retained positive repairs and known-bad instrument plants.
A structural array refusal by a representative legacy JSON object reader is
only carrier evidence, not qualification of any particular implementation.
Historical revision-1 replay failures must be reported explicitly. Selecting
this proposal is never a way to turn them into skipped or green results.

Canonical adoption additionally requires a reviewed, landed specification pin
and exact-head implementation qualification. An open proposal or metadata PASS
does not satisfy those gates.
