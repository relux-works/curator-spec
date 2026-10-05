# Evidence: CIP-0007 manager-provisioned CLI tools (2026-10-05)

Design research for curator-spec issue #108. Triage (2026-10-04)
recommended option B, a registry-only lane, noting it needs an owner and
service decision. Output: Draft
[`cips/CIP-0007-manager-provisioned-cli-tools.md`](../cips/CIP-0007-manager-provisioned-cli-tools.md)
plus one index row in `cips/README.md`.

Scope and limits: docs-only research against specification rc.14 in this
repository. No Curator implementation revision was inspected, no behavioral
probe was run, and no normative protocol or schema text was changed. All
citations below are file:line or file § in this repository unless noted.

## Sources read

- Issue #108 (full proposal text, `gh issue view 108`), including its
  relations to #100 (provider installs), #101 (newer Go families), #106
  (manager-provisioned Go toolchain), and #107 (shim resolution).
- `cips/README.md` (process, binding section list, index), `cips/TEMPLATE.md`,
  `cips/CIP-0001-curator-improvement-proposals.md` (Accepted process), and
  Draft CIPs 0002–0006 for tone and depth (CIP-0005's options table,
  normative sketch, and numbered open questions were the closest model).
- `protocol/core.md` §4 (skill manifest, system commands), §3 (no package
  code execution), §1 (frozen schemas); `protocol/registry.md` §§1–2, 4–5, 8–9
  (signatures, rotation, federation, rollback, offline, wire contract);
  `protocol/skillfile-sources.md` §§3–4 (lock identity, markers);
  `profiles/manager.md` §§2–4, 10 (install lifecycle, scopes, status).
- `schemas/v1/common.schema.json` (`systemCommand`), `schemas/v1/skillfile-*.schema.json`,
  `schemas/skillfile-sources-v1/skillfile-{v2,lock-v1}.schema.json`.

## Key findings (with citations)

1. System commands today are a bare name plus hint, presence-checked only:
   `protocol/core.md:210-213`; closed schema object
   `schemas/v1/common.schema.json` (`systemCommand`: `type`, `command`,
   `hint`). A missing command fails installation with the hint.
2. Readiness verification happens in read-only planning
   (`profiles/manager.md:163-166`, §2.1 step 7); nothing in the lifecycle
   provisions a tool. Install is plan → private staging → one serialized
   journaled transaction (`profiles/manager.md:134-599`, §§2.1–2.5).
3. No version-constraint or recorded-tool-identity surface exists: the lock
   records skill members and package identity
   (`protocol/skillfile-sources.md:161-170`). `manifest_sha256` is the
   CCJ-1 SHA-256 of the entire parsed *declaring Skillfile* (same §, lines
   161–170), not of member skill manifests — so a member tool-declaration
   change does NOT stale via `source_lock_stale`; member byte changes are
   governed by locked package identity and `content_sha256` with explicit
   refresh, failing replay with `source_snapshot_changed` unless
   refreshed. (Corrected in rework 1; the rev1 note wrongly claimed the
   Skillfile hash covers member manifests.)
4. Collection-versus-member version independence: skill-manifest versions
   are independent of Skillfile versions
   (`protocol/skillfile-sources.md` §1, line 29), and the current
   `skillfile-lock-v1` schema is closed at both root and member objects
   (`additionalProperties: false`). Tool entries therefore require a
   proposed new skill-manifest schema version and a proposed
   `skillfile-lock-v2`, with v1 locks staying valid and tool-less.
4. A reusable signed-registry machine exists: CCJ-1 canonical bytes
   (`protocol/registry.md` §1), Ed25519 envelope (§2), overlap rotation
   (§2.1), canonical URLs (§2.2), snapshot rollback with persisted
   high-water (§5), cache/offline grace with stated revocation residual
   (§8), deny-wins federation (§4). Option B reuses all of it without new
   key semantics.
5. The Go toolchain (§2.2) sets the trust bar any provisioning must meet:
   operator-trusted family, fixed probe vectors, fingerprinted tree, and
   rejection of package-selected executables.
6. CIP-0005 (audit backends) is the interaction point for audit evidence:
   resolved tool identity belongs in audit evidence, and provisioned tool
   paths must not widen analyzer child environments beyond the
   backend allowlist (`cips/CIP-0005-audit-backends-and-cli-secret-transport.md`
   Design §3, lines 99–112: single child environment policy; PATH/HOME
   remain operator trust inputs and the filter is not a filesystem
   sandbox).
7. Manifest-shape caution: core §1 freezes schemas 1–6 behavior and schema 1
   keeps deployed extension behavior, which is why the CIP recommends a new
   dependency block over extending `system` (open question 5).
8. Federation, binding, and replay mechanics grounding the rework:
   `protocol/registry.md` §4 (lines 130–169) requires querying every
   enabled registry with deny-wins revocation and a hardened
   unreachable-registry refusal; §2 (lines 53–60) verifies against
   currently pinned keys only and §7 (lines 345–354) refuses
   embedded-key trust bootstrap, which is why C's `verified` mode needs a
   per-tool expected publisher/subject binding; §5 protects snapshot
   high-water, not semantic tool versions; §2.1 revokes objects signed
   solely by a removed key; §8 bounds offline grace with a stated
   revocation residual; manager §2.1 forbids cache hits from bypassing
   attestation/revocation gates; core §4.1.1 (lines 335–343) builds
   enforced PATH from exactly the resolved interpreter plus declared
   `exec` names.

## Fact-checks performed

- Verified `core.md:211-212` as cited by #108 (bare name, hint, install
  failure) — confirmed at `protocol/core.md:210-213` (line shift only).
- Verified related-issue titles via `gh issue view` for #100, #101, #106,
  #107 (all OPEN; titles match the CIP's Related line).
- Verified the CIP-0001 process requirements (template section list, index
  row, Draft status) and that CIP numbers 0002–0006 are taken, so 0007 is
  the next free number.
- Verified no `cips/` checks exist in `tools/validate.py` (grep for
  `cips|CIP` empty); validation run still recorded below for the repo gate.
- Checked the CIP and this note for the forbidden classes (see
  Validation): the two vendor names from the issue text were replaced in
  rev1 with generic CLI descriptions ("forge-hosted issue-tracker CLI",
  "dashboard-query CLI"). The rev1 note's "none exist" claim was false —
  rev1 contained 2 vendor-name occurrences on 2 lines (reviewer rev1
  finding 1). The rev2 note repeated the mechanism: its Validation
  section published the two vendor tokens inside the scan expression (2
  occurrences on 1 line, reviewer rev2 finding 1), so the rev2
  "0 matches" claim was false for the note's own final bytes. Rework 2
  removes the literal tokens from the public note; the final rescan over
  the saved bytes reports **0 matches** (see Validation). The upstream
  catalogue is named only as the public `aqua-registry` project; the
  field-report source in #108 is described without attribution. These
  are bounded scans of known names and path/host tokens plus manual
  reading, not a universal named-entity detector.
- Corrected the rev1 lock-hash inference (finding 5): re-read
  `protocol/skillfile-sources.md` §1 line 29 and §3 lines 161–187 and
  confirmed `manifest_sha256` covers the declaring Skillfile only; the CIP
  now states member-identity staleness via `source_snapshot_changed` and
  proposes versioned `skillfile-lock-v2` plus a new skill-manifest schema
  version.
- Reflected the finding 3 result: the CIP's mirror/resolver section now
  states the per-tool expected publisher/subject binding, the resolver's
  privileged boundary, and the qualified mirror claim, with
  signer-substitution and valid-signature/wrong-subject negatives in the
  test plan.

## Rework 1: finding → change → location

Reviewer verdict rev1 (RUN-261005-fa0397) requested changes with six
numbered findings (three High, three Medium). Each is addressed as follows
(CIP line numbers are post-rework):

| Finding | Change | Location |
| --- | --- | --- |
| 1 (Medium) vendor names + false "none" claim | Replaced the two vendor examples with generic CLI descriptions ("forge-hosted issue-tracker CLI", "dashboard-query CLI"); corrected this note with the rescan counts (see Fact-checks and Validation) | CIP Summary (~L18); this note Fact-checks + Validation |
| 2 (High) first-match vs federation-wide revocation | Two-phase resolution (federation-wide revocation scan with proposed match keys, then first-layer positive selection); built-in-permit plus later-revocation blocks; B-lane unreachable registry refuses with a gate notice; allow-vs-revocation precedence (revocation wins); new negative vectors | CIP Option B (~L110), Recommendation (~L210), Security "Registry compromise" (~L274), Spec sketch items 2+4 (~L420), Test plan (~L507) |
| 3 (High) upstream publisher/subject binding | Per-tool expected publisher/subject binding for C `verified` mode (checksum AND attestation against allowed identity; unknown signer refused); upstream identity revocation; resolver privileged boundary; qualified mirror claim; signer-substitution and valid-signature/wrong-subject negatives | CIP Option C (~L165), Security "Author-controlled downloads" (~L266) and "Mirror and resolver compromise" (~L304), Spec sketch item 5 (~L440), Test plan (~L507) |
| 4 (High) rollback vs downgrade vs replay | Downgrade policy separated from §5 snapshot rollback (initial resolve highest; refresh never downgrades without explicit approval; replay re-authorizes); store hash presence alone never authorizes replay; pre-seeded air-gapped snapshots expire per §5/§8 unless re-seeded/re-authorized; availability residual stated; new negatives | CIP Recommendation `tools.refresh` (~L220), Security "Downgrade policy" (~L255), "Signature and key rotation" (~L296), "Offline, replay, and air-gapped" (~L340), Spec sketch items 6–7+9 (~L444), Test plan (~L507), Open question 10 |
| 5 (Medium) lock-hash coverage + versioned extensions | Tool declarations in member skill manifests (proposed schema 9); `manifest_sha256` covers the declaring Skillfile only so member changes fail replay with `source_snapshot_changed`, not `source_lock_stale`; proposed `skillfile-lock-v2` with per-member `tools[]`; v1 locks tool-less; this note's fact-check corrected | CIP Compatibility (~L372), Spec sketch item 6 (~L444) and Schemas paragraph; this note Key findings 3–4 + Fact-checks |
| 6 (Medium) B runtime-exposure consistency + execution controls | B minimal provisioned-only binding (declared-only launcher visibility; enforced PATH unwidened per core §4.1.1; collisions fail closed); C adds refined composition + probes; probe refs fixed (issue #108 §6, open question 8); new exposure negatives | CIP Option B (~L128), Option C (~L180), Recommendation (~L232), Security "Hostile skill author" (~L241) and "Version probes" (~L334), Spec sketch item 10 (~L466), Test plan (~L507), Impl leaf 3 |

Every security claim in the CIP now cites a spec § or is marked
"(proposal)".

## Rework 2: finding → change → location

Reviewer verdict rev2 (RUN-261005-5e340e) confirmed the three High
findings and the other Medium findings addressed. One Medium finding
remained (repeat-of rev1/F1): the rev2 note published both vendor
tokens in its scan expression while claiming zero matches.

| Finding | Change | Location |
| --- | --- | --- |
| 1 (Medium) vendor tokens in note + false zero claim | Removed the literal token expression; generic scan labels only; recorded pre-correction (2 on 1 line) vs final (0) counts over saved bytes; added named check `final-public-doc-name-scan` with negative control | This note Fact-checks + Validation |

## Validation

- `python -B tools/validate.py` — exit code **0**
  (`validated 73 schemas and 1294 vector files`), run 2026-10-05 via an
  isolated venv with `requirements-dev.txt` (`jsonschema==4.25.1`); bare
  `python` is absent on this host so the venv interpreter was used. No
  normative files were touched, so no digest or vector regeneration was
  needed.
- Rework 1 (2026-10-05): reran `/tmp/cip0007-venv/bin/python -B
  tools/validate.py` — exit code **0** (`validated 73 schemas and 1294
  vector files`). The validator does not inspect `cips/` prose, so this
  attests the repo gate only, not the design.
- Rework 2 (2026-10-05): reran `/tmp/cip0007-venv/bin/python -B
  tools/validate.py` — exit code **0** (`validated 73 schemas and 1294
  vector files`). Docs-only change; no digest or vector regeneration
  needed.
- Rework 2 name/path rescans (generic labels only; literal token
  patterns were held in ephemeral 0600 files outside the repo and never
  placed on argv or in a committed file): vendor-name scan (the two
  vendor names from the issue text, case-insensitive) over the CIP and
  this note — pre-correction **2 occurrences on 1 line** (this note's
  former scan expression; CIP 0), **0 matches** after the correction,
  scanned over the final saved bytes; issue-org token scan
  (word-boundary, over the CIP, this note, and `cips/README.md`):
  **0 matches**; personal path/host token scan (home-dir prefixes plus
  this host's hostname, same three files): **0 matches**. Bounded scans
  plus manual reading, not a universal named-entity detector.
- Named check `final-public-doc-name-scan`: scans the final saved bytes
  of the CIP and this note with the vendor-name pattern from the
  ephemeral file; passes only at 0 matches. Negative control: a
  prohibited token was placed only in an ephemeral temp copy of this
  note — the full scan detected it (1 occurrence), while the same scan
  narrowed to the CIP alone missed it (0 matches), proving the check
  sees the note and the CIP-only narrowing hides note violations. The
  control was ephemeral and never committed. Result: **pass** (final
  documents 0 matches; control detected then discarded).
- Changed paths in this revision: `cips/CIP-0007-manager-provisioned-cli-tools.md`,
  `.research/261005_manager-provisioned-cli-tools.md`, `cips/README.md`
  (index row only). No protocol, profile, schema, conformance, CHANGELOG,
  or LOGBOOK edits.
