# CIP-0017: Muse root-context fragment member and credential store

- **Status:** Draft
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-15
- **Related:** CIP-0015 (per-profile credential backend proposal); owner decision 2026-10-15 (D1, D9, D10, D12)
- **Affects:** environments §§7.1, 7.4, 7.9, 8.2, 10.2, 10.3, 12; Decision 0010; implementations: curator, curator-agent-launcher, skill-agents-management, skill-project-management

## Summary

Curator will explicitly declare a materialized Muse root context with
`root_context: {"exclusive": true}` in a new launch-fragment revision.
The launcher will map this fact to Muse's form-specific exclusion arguments
without inspecting Curator's files. Managed Muse homes will select file
credentials with `TBH_CREDENTIAL_BACKEND=file`, admitting both `isolated`
and `shared` now, optimistically, under owner decision 2026-10-15 (D10).
This proposal corrects the environments §7.4 Muse row using the supplied
Muse 1.4.8 measurements while retaining the unmeasured refresh bound.

## Motivation and user stories

An operator launching a Curator profile expects its declared context to
control the personal sources Muse loads. The launcher must not recognize
Curator headers or infer ownership from a hard-coded managed-home path.
Curator owns content and verification; the launcher applies a fragment and
plan, as required by owner decision 2026-10-15 (D1, D12).

An operator choosing `isolated` needs a login belonging to that managed
home. A global Keychain item cannot supply that separation. An operator
choosing `shared` needs to reuse a native file-backed login explicitly,
without importing credentials or relying on a Keychain fallback.

A non-desktop launch must not need Keychain interaction merely to start
Muse. The measured file backend supplies this behavior; it does not prove
refresh safety, account isolation, sandboxing, or model-visible exclusion.

## Current state

### Reference identities and limits

The spec baseline is curator-spec commit `d34d8a6`,
[environments](../protocol/environments.md). Curator code references below
are at commit `00fec196`. The task-board consumer baseline is
skill-project-management commit `b057ef468`; its
`tools/board-cli/go.mod:11` pins skill-agents-management `v0.5.62`.

The root-context inspection described in the brief is present in
skill-agents-management commit `a8fff5994f4053d2bbd59886fb3eef06137f2c15`,
contained in tag `v0.5.65`. It is not present in the supplied local main
checkout or the `v0.5.62` pin. References to that inspection therefore name
this later revision explicitly; they do not claim the pinned task-board
consumer already implements it. These identities can be inspected without
depending on moving branch heads.

### Layout, exclusions, and transport

Environments §7.1 declares all four XDG parent overrides for Muse, with
root context at `<home>/config/muse/AGENTS.md` and candidate skills at
`<home>/data/muse/skills/`. It records layout evidence from Muse 1.4.1
and root-context/foreign-source evidence from 1.4.7 (1.4.7-R6101.1).
It admits only monolithic context, leaves skills discovery unverified,
and refuses fresh-login `isolated` as `environment_isolated_unsupported`.

The 1.4.7 P1–P4 observations in §7.1 distinguish rules and skills:
native root context suppresses foreign personal rules fallback, but foreign
personal skills persist. `exec` accepts `--no-foreign-personal-context`;
interactive rejects that flag and accepts the JSON boolean override
`-c context.foreign_personal_skills=false`. The override depends on native
root context being present. Workspace precedence and model-visible foreign
removal remain bounded observations, not isolation guarantees.

Environments §10.2 introduced `launch-env-fragment-v3` to carry Muse and
its four XDG variables; v1/v2 readers reject the new revision. The
`Muse managed launch argv` paragraph binds exclusions to materialization
and currently says: “No fragment member, descriptor kind, or channel is
added; the v3 fragment shape and released schema bytes remain unchanged.”
The owner decision 2026-10-15 (D12) reverses the no-member decision, not the
requirement to preserve released schema bytes.

The released `schemas/v1/launch-env-fragment-v3.schema.json` is closed:
top-level unknown members are forbidden; Muse `env` has exactly four XDG
keys, with absolute-path values. `TBH_CREDENTIAL_BACKEND=file` cannot be
added under that grammar either. Environments §10.3 also limits emitted
values to registry-declared home paths, so its influence boundary needs
an explicit constant-valued exception, not a general environment escape.

Curator `internal/envfragment/envfragment.go:54–69` defines `Fragment`
without `root_context` and chooses v3 for Muse; `:107–138` serializes it.
Its `variables` method at `:163–169` returns immediately after the adapter's
home-variable list. Adding a fifth environment value must update env/shell
rendering too, or JSON and those formats would disagree.

At skill-agents-management `a8fff59`,
`pkg/agentic/systems/muse/personal_context.go:21–60` gates suppression on
1.4.7, an optional matching frozen build, no managed network override,
and `hasCuratorRootContext`. That helper uses `Lstat` plus `IsRegular`,
opens `config/muse/AGENTS.md`, checks inode identity, and reads a Curator
header prefix. A symlink is rejected before the header read.
`pkg/agentic/systems/muse/args.go:131–133` adds the exec exclusion;
`:169–178` selects and protects the interactive override. The same file
inspection is used in `pkg/agentic/systems/muse/seal.go:215`.

Curator normally links root context to its rendered profile document:
`internal/envprofile/managed.go:447–513` assembles the surface and assigns
`p.links[target] = storeDoc`; `:1408–1421` publishes the link, with a copy
fallback when symlinks are unavailable. Thus `Lstat` plus `IsRegular`
does not recognize the normal linked target. Environments §8.3.1 requires
entry replacement and no-follow write discipline; changing the launcher
to follow the link would still leave ownership in the wrong component.

Curator `internal/envprofile/status.go:342` currently reports 1.4.7 root
context, exec exclusion, the serve gap, observed workspace precedence,
and unverified refresh/discovery/model-visible behavior. It does not yet
express the full P1–P4 interactive distinction required by the current spec.

### Credentials and supplied measurements

Environments §7.4 currently lists `config/muse/auth.json` as a `file-link`
to native effective `XDG_CONFIG_HOME/muse/auth.json`, captured before
managed overrides, defaulting to `~/.config/muse/auth.json`. The row
records four surviving runs, no Keychain prompt and a model turn, while
explicitly leaving refresh and login writes unverified.

Its Muse refresh rule requires liveness checks on every resolve, including
repair. Detached state is non-current; a bare resolve emits no fragment.
An absent link can be repaired only against a readable regular native
target. A forked regular file, unexpected link target, or dangling native
target refuses repair with `environment_credential_conflict`. Metadata
read failures are `environment_passthrough_unreadable`, never absence.

The supplied `rc7-decisions.md`, measured facts dated 2026-10-14, records
Muse 1.4.8 on macOS 27:

- Default login is Keychain-first, using global item
  `ai.meta.dev.credentials`; `auth.json` is a fallback. Recorded backend
  labels are `keychain`, `keychain_fallback_file`, and `file`.
- Without Keychain access the default login is not saved, reporting
  `keychain write failed (os status -60006)`.
- `TBH_CREDENTIAL_BACKEND=file` saves login to
  `$XDG_CONFIG_HOME/muse/auth.json`, mode 0600. Subsequent measured runs
  used backend `file` with zero Keychain access.
- A home linking its `auth.json` to another home's file worked.
  A minted key supplied by `exec --api-key-stdin` billed the subscription;
  `META_API_KEY` left the store untouched.
- Token-refresh write behavior is unmeasured.

These are supplied measurements, not probes rerun for this documentation
change. Owner decision 2026-10-15 (D9) assigns backend selection per
profile × environment; D10 admits both Muse modes without waiting for
refresh evidence. The historical 1.4.7 exclusion evidence must remain
separate from the newer 1.4.8 credential evidence.

## Design

### Options considered

#### Root-context authority and revision

| Option | Mechanism | Pros | Cons | Security |
|---|---|---|---|---|
| A: inspect files | Keep or repair the path/header check in the launcher | No new wire member | Duplicates Curator ownership; depends on links and layout; contradicts D12 | Absence and read failure can silently disable exclusion |
| B: extend v3 | Add `root_context` and the backend constant under the existing token | Fewer revision identifiers | Existing closed readers reject it; changes released bytes | Permissive old readers could silently drop the requirement |
| C: new revision | Add a closed fact and backend constant in v4; retain v3 bytes | Explicit reader admission; one authority; obeys D12 | Requires coordinated consumer rollout | Unknown revision fails before execution; no filesystem inference |

Recommend C. The launcher needs only the exclusive-root-context fact.
A path, rendered hash, header version, or arbitrary argv descriptor would
expand its responsibilities without helping select either exclusion form.

#### Credential store and admission

| Option | Mechanism | Pros | Cons | Security |
|---|---|---|---|---|
| A: default backend | Let Muse choose Keychain or fallback file | Existing native behavior | Global Keychain does not isolate homes; fails without Keychain | A linked file does not prove the active store |
| B: wait for refresh | Force file but postpone one or both modes | More write evidence before admission | Contradicts D10; blocks measured login reuse | Avoids optimistic refresh exposure at the cost of availability |
| C: file now | Force file in managed fragments; isolated own login or shared native link | Explicit store; works without Keychain; follows D9/D10 | Refresh and concurrent writer behavior remain unknown | Existing liveness/conflict rules protect bytes at resolve, not during refresh |

Recommend C. File selection and sharing are distinct settings: `file`
selects the backend, while `isolated` versus `shared` selects whose file
the managed home uses. Neither choice claims account or process isolation.

### Recommendation

#### 1. Closed root-context fact

Introduce `launch-env-fragment-v4`, preserving the common v3 members and
existing adapter contracts except for the explicit Muse additions below.
The optional top-level member has exactly this shape:

```json
{"root_context": {"exclusive": true}}
```

The member is an object with required `exclusive`, boolean constant `true`,
and `additionalProperties: false`. Reject `null`, `{}`, `false`, strings,
extra members, duplicate keys, and use on any adapter other than Muse.
Absence means no Curator root-context exclusion requirement for this
launch; it never grants permission to infer one by reading a file.

Curator MUST emit the member exactly when a successful resolve establishes
that the Muse root-context target is materialized for the selected home
and profile. Both freshly materialized targets and verified current
targets qualify; a plan to write one does not. Applicable root modules
and the verified surface/marker determine this fact inside Curator, not
the number of bytes or a guessed path inside the launcher.
With no root-context surface, omit the member. A stale, missing, drifted,
or unreadable required surface follows the existing resolve refusal and
repair rules; it MUST NOT yield a successful fragment with the member
silently omitted. A failed repair emits no fragment.

The launcher validates the whole fragment, transports the typed fact
through the launch request, and maps presence to:

| Muse form | Required argv |
|---|---|
| `exec` | `--no-foreign-personal-context` |
| interactive | two elements: `-c`, `context.foreign_personal_skills=false` |

The interactive value is JSON boolean false, not the string `"false"`.
The mapping is independent of permission mode, MCP, system prompts,
credential isolation, and the linked/copied form of the materialized file.
Dry-run uses the identical argv builder. Native arguments that override
the exclusion are rejected rather than applied after it.

No launcher path may stat, lstat, open, readlink, hash, or recognize a
header in Curator content to decide whether to add these arguments.
Remove the inspection from both argv building and sealing. Tool-release
qualification remains a separate responsibility: if the selected build
cannot apply the required form, refuse before exec instead of dropping it.
This CIP defines no new refusal-code spelling for that future gate.

If a launch transformation relocates the effective XDG home, it must
preserve the Curator-established root context through the admitted
snapshot/materialization contract or refuse the required launch.
It must not suppress the member for a network launch or recreate a
second layout verifier. `serve` remains outside the qualified exclusion
forms: a request requiring this fact cannot silently launch through serve.

#### 2. Managed file credentials

For managed Muse, the v4 fragment `env` MUST include the four existing
XDG parent paths and the constant `TBH_CREDENTIAL_BACKEND=file`.
Keep `HOME` unchanged. The new schema closes the Muse environment to those
five keys, keeps path validation and one-parent semantics for XDG, and
admits only the literal string `file` for the backend key. Other adapters
retain their existing environment sets; unknown names remain invalid.

Integrate this with CIP-0015's per profile × environment backend setting,
defaulting managed Muse to `file` for both credential modes. CIP-0015 owns
the persisted configuration spelling and precedence; this CIP does not
invent a competing key. An explicitly selected Keychain backend cannot
claim the file-backed isolation or sharing contract: this initial Muse
admission rejects that combination with existing
`environment_credential_unsupported`, with a file-selection hint.
Do not silently override an explicit operator setting or migrate secrets.

The launcher's effective environment applies the fragment constant over
an ambient backend selection. Later environment merging must not undo it;
an incompatible explicit plan override refuses. No general profile-owned
env map is introduced. JSON, env, and shell renderers include the same
five values, with XDG entries in declared order followed by the backend.

`isolated` creates no passthrough link and runs Muse's native login inside
the managed XDG home with the file backend selected. Login may be invoked
through the preparation/login surface proposed with CIP-0015; it uses
the same resolved backend as inference. Curator does not copy a native
login, read token values for status, or synthesize `auth.json`.
An already logged-in native Keychain is irrelevant to readiness in this
mode. Isolation separates the declared store, not ambient API keys or
other authentication injected by the operator.

For `shared`, the operator first performs one native Muse login with
`TBH_CREDENTIAL_BACKEND=file` in the native effective XDG environment.
A Keychain-only login is insufficient; Curator must not export it.
Capture native effective `XDG_CONFIG_HOME` before applying managed XDG
overrides, and link the managed `config/muse/auth.json` to that native
file. Verify a readable regular target under the existing liveness rules.
If it is missing, request native file-backed login and emit no shared
fragment; never create a placeholder or fall back to the Keychain.

Admission is optimistic now, as owner decision 2026-10-15 (D10) requires.
Do not make a successful token-refresh probe a prerequisite. Preserve
every §7.4 Muse liveness, unreadability, and conflict rule at status and
each resolve, including repair. If refresh replaces the managed symlink
with a regular file, report detached/non-current; bare resolve returns
`environment_home_stale`, and repair returns
`environment_credential_conflict` without modifying either credential.
Absent links and empty directories are repairable only as §7.4 permits;
dangling targets, unexpected links, and non-empty directories are not.
Native replacement behind an intact link is judged by current target
liveness, not by an assumed stable inode. No directory link, automatic
copy-back, or destructive relinking of a forked file is admitted.

#### 3. Corrected environments §7.4 row and version evidence

Replace the Muse row with the following proposed normative row:

| Environment | Passthrough entries | Strategy | Write behavior |
|---|---|---|---|
| `muse` | `shared`: `config/muse/auth.json`; `isolated`: none | Managed launches set `TBH_CREDENTIAL_BACKEND=file`. `shared` uses `file-link` to native effective `$XDG_CONFIG_HOME/muse/auth.json` (default `~/.config/muse/auth.json`), captured before managed overrides and requiring a native file-backed login. `isolated` logs in inside the managed XDG home. Both modes are admitted optimistically. | Muse 1.4.8 on macOS 27: file-backed login at mode 0600, subsequent backend `file` with zero Keychain access, and a link to another home's file worked. Default backend is global Keychain-first and fails to save without Keychain access. Token-refresh and concurrent refresh behavior remain unmeasured; every-resolve liveness and conflict-preserving repair remain mandatory. |

Update §7.1's isolated refusal and Keychain warning in the same adoption
change; preserve its monolithic-only and discovery bounds. Do not present
the row as proof that default Muse behavior is file-backed. Update §7.9
and §12 to distinguish the historical 1.4.7 exclusion pin from the 1.4.8
credential pin. The candidate managed integration target is Muse 1.4.8;
its exact build identity must be recorded by the implementation before
claiming form-specific exclusion qualification on that release.

Minimal re-verification on 1.4.8 is the 1.4.7 P1–P4 contrast on both
forms, native root loading through Curator's link and snapshot file,
workspace-conflict residual, and the file-backend credential contrasts
listed in the Test plan. No 1.4.7 equality check may silently disable an
otherwise required v4 exclusion on 1.4.8. Until those exclusion probes
pass, report the 1.4.8 exclusion result unknown and refuse a launch
requiring unqualified exclusion; this does not defer D10 credential-mode
admission or invent an interim path-inspection hack.

#### 4. Swarm boundary

Under the broker, the minting owner retains the Muse login and the child
receives the minted key as `META_API_KEY` or `exec --api-key-stdin`;
`TBH_CREDENTIAL_BACKEND=file` keeps the child away from the Keychain.
This is consistent with owner decision 2026-10-15 (D11) and the supplied
Muse 1.4.8 billing/store observations. It does not authorize copying OAuth
tokens or linking the broker owner's `auth.json` into a child: local
`shared` homes and broker key delivery are different contracts. The
existing broker spec §10.2 proposes the same key channel but still has
qualification and refresh/rotation/lifetime questions; its statement that
file writes replace the inode must not be promoted into measured refresh
evidence here. Broker qualification and lifetime policy remain broker work.

## Security considerations

Treat a Curator fragment as trusted manager output only after the existing
revision, schema, provenance, and plan binding checks. Repository content
must not mint the root-context fact or choose arbitrary environment names.
The fact is control metadata, not a new secret or a proof of sandboxing.

File credentials replace a global desktop store with filesystem access
control. Muse-created credential files must retain mode 0600 on the
measured platform; managed directories must exclude unrelated users.
Never log tokens, dump `auth.json`, put credentials in the profile lock,
or include them in root-context hashes. Status carries metadata only.
Generic home paths and non-secret backend names are sufficient diagnostics.

A shared credential deliberately couples two homes to the same login.
Liveness checks have a resolve-to-exec race and cannot prove coordinated
refresh: each home can have a separate lock. Refuse ambiguous repairs and
preserve both stores for explicit operator recovery. A missing file and a
failed metadata read must remain distinguishable through every entry point.

Root-context exclusivity describes required loader controls. Workspace
rules can still prevail; model-visible foreign removal and managed skills
discovery remain unverified. The public guarantee must retain those bounds.

## Compatibility and migration

1. Publish the v4 schema and conformance vectors under a new identity.
   Keep released v1/v2/v3 schema bytes and their old interpretation frozen.
   Add explicit v4 handling to the launcher specification and readers.
2. Release skill-agents-management with typed root-context transport and
   no layout inspection. Allocate the next available module tag after
   `v0.5.65`; `v0.5.66` is the proposed tag, not a published capability.
   Update skill-project-management's `tools/board-cli/go.mod` pin from
   `v0.5.62` to the actual released tag and regenerate its vendor tree.
   Update curator-agent-launcher's dependency and its v4 acceptance too.
3. Ship Curator v4 Muse emission, backend selection, login preparation,
   status corrections, and consumer support in a coordinated release.
   Existing non-Muse adapters can keep emitting their supported revisions.
4. While old and new versions coexist, old consumers reject v4. New
   readers may decode v3 for compatibility, but the managed Muse entry
   point refuses v3 and asks for a compatible Curator resolve. It must
   not treat missing v3 metadata as evidence of no materialized context,
   synthesize v4, inspect files, or retry an older fragment revision.
5. Remove the old inspector from the new module rather than retaining it
   as a v3 fallback. Old binaries remain old; their behavior is not the
   transition mechanism. A partially upgraded managed pair fails closed.
6. Backend migration is explicit: native Keychain-only users perform a
   file-backed login for shared mode; isolated users log in per home.
   Existing regular credentials or unexpected links are preserved and
   require explicit conflict resolution. Repair never exports a Keychain
   credential or overwrites a credential to make migration appear current.

## Specification changes

Adoption makes these normative edits together; this Draft edits none of
the normative artifacts itself:

- Environments §§7.1 and 7.4: replace the isolated prohibition and Muse
  credential row with the file-backed modes and preserve refresh bounds.
- Environments §§7.9 and 12: record version-separated evidence and the
  complete rules-fallback/skills/interactive/serve status note.
- Environments §§8.2 and 10.1: keep credentials outside managed content;
  record only the effective non-secret backend using CIP-0015's adopted
  metadata contract, and bind the fact to successful home verification.
- Environments §10.2: add v4, its closed optional Muse `root_context`,
  and the five-key Muse environment. Replace the quoted no-member rule
  with the member-driven argv contract; retain the two distinct forms.
- Environments §10.3: allow only the registry-owned constant backend
  value as a non-path exception. Do not generalize profile env injection.
- Add `schemas/v1/launch-env-fragment-v4.schema.json` and positive/negative
  conformance cases, including old-reader rejection; freeze old schemas.
- Amend Decision 0010 to record owner decision 2026-10-15 (D10, D12).
  Align curator-agent-launcher fragment acceptance and the broker cross-
  reference without asserting unmeasured refresh or subscription lifetime.

## Implementation plan

Ordered leaves use S/M/L as scope estimates, not elapsed-time promises.

1. **curator-spec — M:** adopt v4 prose, schema, revision rejection
   vectors, corrected §7.4 row, evidence matrix, and influence boundary.
2. **skill-agents-management — M:** carry the validated fact through the
   real launch request, map both forms, reject overriding native args,
   remove argv/sealer file inspection, and publish the module tag.
3. **curator-agent-launcher — M:** consume v4, bind the fact and backend
   into plans, enforce environment precedence and legacy managed-Muse
   refusal, and retain qualification refusals across exec/interactive.
4. **curator — M:** derive the fact from successful root materialization
   and verification; implement file selection via CIP-0015, all renderers,
   both modes, login readiness, repair preservation, and status corrections.
5. **skill-project-management — S:** update the spm module pin/vendor to
   the new agents-management release; drive its real hosted launch path
   using the new fragment, without reproducing home-content checks.
6. **curator / skill-agents-management — M:** run the minimal 1.4.8
   integration probes, record exact build qualification and residuals,
   and release compatible producer/consumers together.
7. **swarma-dispatcher — S:** verify broker-key forwarding plus the file
   backend in the existing child launch; never create a linked OAuth store.
   Archive/snapshot work remains owned by its separate materialization CIP.

## Test plan

These are implementation acceptance tests to add in the named repositories,
not tests claimed to have run for this Draft. Exercise production resolve,
login, launch-plan, seal, and exec entry points, not just JSON helpers.

| Named test | Entry and assertion | Negative case |
|---|---|---|
| `TestMuseV4RootContextFromVerifiedSurface` | curator resolve with linked target, copy fallback, current home and repaired home emits the fact | No root surface omits it; stale/unreadable surface emits no fragment |
| `TestMuseV4ClosedShape` | spec/launcher actual fragment decoder accepts the chosen shape | Reject unknown revision, duplicate key, false/null/extra member, wrong adapter, and v3 with either addition |
| `TestMuseRootContextBothLaunchForms` | agents-management plan/seal/argv emits each exact exclusion, including dry-run and both permission modes | Missing fact emits neither; unsupported form/build refuses; no file access decides argv |
| `TestMuseRootContextOverrideRefused` | interactive production launch rejects a later native argument enabling foreign skills | Alternate accepted config spellings cannot bypass the protected boolean |
| `TestMuseFileBackendAllFormats` | curator resolve emits five identical env values in JSON/env/shell | Reject extra variables, non-file backend, changed HOME, or mismatched XDG parents |
| `TestMuseBackendSurvivesLaunchMerge` | launcher child env retains file over ambient Keychain selection | Explicit conflicting plan override refuses, no silent last-write override |
| `TestMuseIsolatedFileLogin` | curator native-login entry uses the managed XDG home and file backend | Native Keychain-only login does not establish isolated readiness; no native file link |
| `TestMuseSharedNativeFileRequired` | curator shared resolve links the pre-override native file | Missing native file and unreadable target are distinct refusals; no Keychain fallback |
| `TestMuseSharedRefreshDetachment` | status, bare resolve and repair drive each existing §7.4 state | Forked file, retarget, dangling target, read failure and non-empty directory preserve bytes and emit no fragment |
| `TestMuseManagedV3RequiresUpgrade` | actual managed launch rejects a legacy Muse fragment | No retry, filesystem inference, or silently omitted exclusion/backend |

Keep all committed reviewer tests under their original names. Extend existing
Muse liveness tests rather than replacing them. Record each source/test/
configuration/environment identity with its command, exit code, and log.

Minimal tool probes use disposable homes and synthetic context sentinels,
without disturbing an active native login. On macOS with Muse 1.4.8:

1. Record exact version/build; replay P1–P4 with native root present/absent,
   foreign rules and skills separately, both forms, and both exclusion
   spellings. Observe loader records separately from model-visible output.
2. Resolve a real Curator link and a materialized regular-file snapshot;
   confirm native root loading and exclusions. Repeat a workspace conflict
   only to record the residual, not to promise a precedence guarantee.
3. In disposable login contexts, contrast default backend with and without
   Keychain access, then file backend in both contexts. Record backend,
   save result, mode and Keychain access count, never credential bytes.
4. Login isolated, reuse via shared link, and make a model turn; retain
   unmeasured refresh as unknown if no refresh occurred. Later force a
   legitimate refresh and inspect only entry type/target/inode metadata;
   this follow-up is not a D10 admission gate.
5. For broker qualification, contrast minted key via stdin and env, record
   subscription billing and unchanged store metadata without logging keys.

The credential facts supplied here cover macOS 27 only. Portable schema,
argv and synthetic filesystem tests run on supported platforms; Linux and
Windows native Muse login/refresh qualification remains unclaimed until
measured. No iOS app target exists in this spec repository.

Narrowing mutants for the implementation tests must be run and reported
with their named failing test; the following are planned, not killed here:

| Mutant | Narrows the gate to | Test expected to fail |
|---|---|---|
| Recognize only regular root files | Excludes Curator's normal linked target | `TestMuseV4RootContextFromVerifiedSurface` |
| Emit only exec exclusion | Drops interactive protection | `TestMuseRootContextBothLaunchForms` |
| Accept only 1.4.7 then omit on mismatch | Silently loses the required fact on 1.4.8 | `TestMuseRootContextBothLaunchForms` |
| Emit backend only in JSON | Omits env/shell control | `TestMuseFileBackendAllFormats` |
| Force file only for isolated | Shared launch can use ambient Keychain | `TestMuseBackendSurvivesLaunchMerge` |
| Liveness only on bare resolve | Repair bypasses the credential gate | `TestMuseSharedRefreshDetachment` |
| Collapse metadata errors into absence | Unreadable entries become repairable | `TestMuseSharedRefreshDetachment` |
| Accept v3 when no fact is carried | Legacy transport bypasses the upgrade gate | `TestMuseManagedV3RequiresUpgrade` |

A surviving mutant proves no bound beyond its exercised input class;
report it as a survivor with the missing class rather than claiming coverage.
Documentation validation does not establish these runtime properties.

## Open questions for the operator

1. **Exact module tag:** use proposed `v0.5.66` if still available, or the
   next unused tag after it? Recommended: allocate the next unused tag at
   implementation and pin that exact release in spm and the launcher;
   never reuse a published tag. This is release coordination, not a reason
   to retain the old inspector.
2. **CIP-0015 setting integration:** should Muse initially accept an
   explicit Keychain choice? Recommended: default to file and reject
   Keychain for this managed contract; adopt CIP-0015's single persisted
   setting/precedence without a second Muse-only config key. D9/D10 remain
   binding regardless of that spelling.
3. **Refresh follow-up:** should a delayed refresh result postpone mode
   admission? Recommended: no, per owner decision 2026-10-15 (D10); retain
   the existing conflict-preserving liveness contract and schedule the
   pinned refresh probe as follow-up evidence. A discovered fork requires
   explicit operator recovery, not automatic credential copy-back.
4. **Muse 1.4.8 exclusion build:** promote 1.4.7 evidence automatically or
   replay P1–P4 on the exact 1.4.8 artifact? Recommended: replay, record the
   build and separate each evidence dimension; do not disable required
   exclusions silently or claim the credential probe verified context.
