# Unresolved questions

## Muse managed-context residuals

The revision-1 admission in [environments §§7.1, 7.9, and 10.2](protocol/environments.md)
records the Muse Code 1.4.7 monolithic own-file target, measured foreign
personal-context sources, and target-bound `exec` and interactive exclusion.
Skills discovery, system-prompt discovery, model-visible foreign removal,
and a reproducible size threshold remain unverified. Workspace precedence in
observed conflicts is a residual; `serve` cannot exclude foreign personal
context. The required admission vectors are listed in environments §13 for
delivery with the target and both forms' exclusion argv; existing vectors
do not qualify the added requirements.

**CIP-0017 state.** [The Accepted CIP](cips/CIP-0017-muse-root-context-and-credential-store.md)
resolves the no-root-surface case: omit `root_context`, pass neither exclusion,
and retain the foreign-context residual. Native/unset managed Muse backend
selection resolves to file; explicit Keychain refuses. Still open for later
leaves: exact consumer module tag, exact 1.4.8 exclusion build and P1–P4 replay
before consumer release, token-refresh and concurrent-writer behavior,
Linux/Windows native qualification, and broker rotation/lifetime. The credential
admission is optimistic now; unmeasured exclusion and refresh remain separate.

## Advanced repository mappings decided by transport revision 2

Non-default endpoint ports, operator-declared mirrors and operator-declared
host aliases are now decided normatively by [repository transport revision
2](protocol/repository-transport.md) (source-policy schema 2, additive over
schema 1). Ports are machine-policy endpoint properties stripped before
canonicalization; mirrors require an exact-key `mirror_of` attestation;
aliases resolve only from operator source-policy, never from user ssh/git
configuration.

## Still open: reusable alias registries and user-configuration import

Reusable cross-machine logical alias registries and safe translation of user
`insteadOf`/SSH configuration remain undecided and are rejected. Matching
content alone does not authorize identity equivalence, and user configuration
is usable only through explicit operator admission, unchanged from revision 1.

No source extension implementation or release qualification is claimed. A
future release must assign publication metadata and qualify implementations
against the new schema and semantic vectors before advertising support.
Prebuilt binary distribution, compiler bootstrap, broader context/plugin/MCP
imports and toolchain-family reconciliation remain outside this amendment.

## Adopted decisions

These credential/permission decision drafts are **adopted** (operator
decision 2026-09-21, TASK-260921-3qcjsy, STORY-260921-3z0fgr; design
input the Fable-reviewed TASK-260916-2timlf work). Adoption records
the selected options and the resolved choices in each document; the
normative amendments land with the adoption, and the remaining
implementation and spec-revision work is tracked in named follow-up
leaves.

- [Decision 0017: environment credential modes](decisions/0017-environment-credential-modes.md) — adopted 2026-09-21: options 1–3 as recommended, open questions 1–7 resolved.
- [Decision 0018: curator run permission interface](decisions/0018-curator-run-permission-interface.md) — adopted 2026-09-21 with the 2026-09-16 amendment (TASK-260916-2fu85y, rev 2 after review): config-driven mode, interactive default `yolo` / headless default `native`, force-`native` lock, fail-closed legacy transport; open questions 1–7 resolved.

The launch-profile decisions below were adopted 2026-10-01 by the operator.
Their proposal text is preserved; normative amendments and their open
questions remain follow-ups.

- [Decision 0019: fragment consumers and one construction site](decisions/0019-fragment-consumers-and-one-construction-site.md) — adopted 2026-10-01 by the operator.
- [Decision 0021: sessions enter through curator run and are hosted through the ax contract](decisions/0021-sessions-enter-through-curator-run.md) — adopted 2026-10-01 by the operator.

## Managed-home snapshot activation gates

CIP-0014 is Accepted under owner decision 2026-10-15. Its normative leaf 1
is [published separately](protocol/managed-home-snapshots.md). The following
remain open and MUST NOT be inferred from acceptance:

- Exact archive encoding, header/padding/end bytes, resource caps, plan wire
  bindings and cross-service refusal mappings: joint leaf 5 publication.
- Runtime B's sealed-content/private-state view: an interpretation of D6
  awaiting operator confirmation, then per-adapter/platform protection and
  start/login/model-turn/native-resume qualification in leaves 3/6.
- Opencode profile-local skills discovery and ambient state bounds; export
  refuses meanwhile. Muse skill discovery and refresh writes remain unverified.

The materialize diagnostic family is resolved in snapshot §5. D12's portable
Muse root-context fact is coordinated with CIP-0017; its fragment revision
and credential policy remain outside this leaf.

## Filed proposals

These decision drafts are **proposed — not adopted** (0014–0016 from
migration workstream B7).
Filing does not authorize implementation, normative changes, workarounds,
or draft landing.

- [Decision 0014: tool-configuration surfaces](decisions/0014-tool-configuration-surfaces.md)
- [Decision 0015: per-project policy and profile selection](decisions/0015-per-project-policy.md)
- [Decision 0016: skill command roots in managed homes](decisions/0016-managed-home-command-roots.md)


## Local hosted publication and qualification

[CIP-0016](cips/CIP-0016-local-hosted-launches.md) is Accepted by owner decision
2026-10-15. [Local hosted launches §8](protocol/local-hosted-launches.md#8-publication-questions-retained)
retains four open questions: exact successor wire/capabilities/preparation
framing; backend configuration and migration spelling; supported Codex policy
layering across cold resume; and CIP-0014's Curator-owned credential exceptions.
Recommended answers are not frozen fields or measured behavior. Launcher SPEC
§§3, 4.6, 4.8–4.9 amendments and receiver qualification remain follow-up work;
local activation must not defer Codex, wait for dispatcher, or use live homes.

## Login readiness publication and qualification

[CIP-0015](cips/CIP-0015-login-readiness-and-profile-preparation.md) is Accepted;
[login readiness revision 1](protocol/login-readiness.md) freezes leaf 1's row,
selector and store projection. Full containing manager-config/status revisions and fragment 5 are now
[published](protocol/rc7-carriers.md) with the Codex successors.
No v1–v3 fragment extension is admitted. Metadata-only platform probes, Codex
keyring scope/precedence, Windows, Muse refresh, optional explicit
vendor diagnostics, broker adoption and destination readiness remain later-leaf
work. The strict all-participants aggregate is decided: a participating ambient
OpenCode row currently prevents green check/prepare, deliberately and visibly.

## Profile Codex settings (CIP-0018)

1. **Carrier allocation published.** [Containing carriers](protocol/rc7-carriers.md)
   allocates manifest 2, lock 4, marker 5 and fragment 5 with one policy payload;
   snapshot descriptors remain separate. Runtime enablement still needs the
   following qualification and strict covered consumer support.
2. **Supported-release qualification.** Establish scalar CLI precedence over
   a conflicting seed and backend selection for login, app-server and token
   refresh on every supported Codex release. Until measured, these capabilities
   remain unknown and producers remain disabled. CIP-0015 must also adopt the
   explicit eligibility matrix before isolated/file is enabled.

The accepted [normative text](protocol/profile-codex-settings.md#7-wire-allocation-conformance-and-rollout)
and [CIP questions 4–5](cips/CIP-0018-profile-level-codex-settings.md#open-questions-for-the-operator)
define the required decisions and evidence. These are later adoption gates,
not behavior inferred or implemented by the normative leaf.

## Local setup-token activation gates

The [local-source publication](protocol/local-setup-token-source.md) settles
the C7 same-user sequencing carve-out, carriers and public facade contract.
Remaining delivery gates are the separately reviewed launcher SPEC entry/plan
companion, the T3a public API module pin, T1/T2 custody/policy implementation,
T3b real final-executor qualification and T4 real task-board headless uptake.
No supported tuple is established by the metadata corpus. Direct-only and
interactive hosted rows remain distinct. `tb-sessiond` lookup/restart is
refused under existing hosted §§4/6; enabling it requires an explicit later
amendment, not a callback or hidden wrapper. Unqualified vendor child-leak or
settings-reload behavior keeps capability unavailable.

## Project Skillfile MCP declarations (CIP-0022)

[Draft CIP-0022](cips/CIP-0022-mcp-server-declarations-in-project-skillfile.md#open-questions-for-the-operator)
keeps the stage-A adapter set, nested `install` contract, runtime pin grammar,
inline audit waivers and versioned carrier/writer details open for operator
review. Its package-first and digest-approved inline design is proposed only;
filing the Draft enables no native writer or managed-launch admission.
