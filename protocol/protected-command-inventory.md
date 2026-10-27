# Protected command-name inventory v1

Owner requirements of 2026-10-27: skill commands never collide with or shadow
important tools; the inventory is broad; the check is fast. This companion
publishes a release-owned artifact and executable specification witnesses. L1
owns the enclosing environments §9.4/§10.2 amendment, lock successor and runtime
integration. No released carrier gains fields by inference. These vectors and
benchmarks do not claim an implemented Curator command capability.

## 1. Artifact, identity and limits

The authoritative dataset is [inventory.json](../data/protected-commands/v1/inventory.json).
Its [closed schema](../schemas/protected-command-inventory-v1/inventory.schema.json)
requires `schema_version:1`, monotonic `inventory_version`,
`normalization:ascii-fold-wrapper-suffix-v1`, source pins, `extractor_version`,
extractor implementation digest, `patterns` and sorted unique `entries`.
Each entry has a normalized `name`, sorted distinct original `spellings` and
sorted distinct `provenance` pairs (`source`, `class`). Classes distinguish
catalogue, system, shell, VCS, package-manager, platform and manager facts.
A catalogue entry is a reservation, never permission to provision/execute a tool.
`curator-` is a typed prefix pattern, not a literal executable `curator-*`.
Exact `curator` and `curator-run` are always reserved too.

Artifact bytes MUST be UTF-8 CCJ-1: lexicographic object keys, compact JSON,
no BOM, whitespace/newline suffix, floating/nonfinite numbers, negative zero,
unsafe integers, duplicate keys or invalid/lone-surrogate text. There is no
signature/checksum member to omit: SHA-256 covers the **whole artifact bytes**.
The release-owned [artifact metadata](../data/protected-commands/v1/artifact.json)
records the digest outside the payload. A checksum proves identity, not source
trust or policy authority. Curator embeds exact reviewed bytes plus expected
identity at a pinned spec revision; profiles cannot supply a replacement list.

The successor portable lock records required `command_inventory` with exactly
`{version, sha256, normalization}`, as defined in the
[identity schema](../schemas/protected-command-inventory-v1/identity.schema.json).
The member participates in canonical lock identity together with the complete
export/alias/owner plan. L1 allocates the complete successor; this schema is a
subtree, not an extension permission for an old lock. Missing identity, unknown
normalization/schema/version, bad digest, untrusted artifact or truncated data
refuses command capability before publication/start. Legacy context-only use
remains under its existing contract, without acquiring new command authority.
Admitted destination PATH and resolved paths belong in a protected generation/
launch receipt bound to lock, command bytes/owners and admission identity, not
in the portable source lock.

Defensive bounds are normative: at most **100,000 unique keys**, **16 MiB**
canonical artifact, **128 ASCII bytes** per spelling/key, **64 source pins**,
**32 provenance pairs** and **32 spellings** per entry. Reject over-limit input;
never truncate. The runtime export grammar remains the existing portable
identifier grammar with Windows device-name, path and control exclusions;
inventory punctuation does not broaden it. Source generation separately bounds
files to 64 MiB (TOML 1 MiB/file), nesting to 32 extraction levels, YAML data
expansion to depth 64 / 2,000,000 nodes and aqua traversal to 200,000 nodes.

Updates are reviewed policy releases: record pins, additions/removals, notices,
coverage witnesses and extractor/parser changes. Every byte-affecting change
requires a new inventory version; registry deletion does not automatically
remove protection. Consumers check the **union of locked and currently required
machine baseline** protections. A conflict from new policy blocks command
capability; no silent lock rewrite or downgrade to a smaller list. Normalization
changes require a new versioned contract and migration. No runtime registry fetch.

## 2. Reproducible extraction and source status

[sources.lock.json](../data/protected-commands/v1/sources.lock.json) pins exact
commits, canonical input-bundle/seed digests, semantic adapter and parser versions,
extractor digest and independent coverage witnesses. Generation is offline from
those bytes. Input acquisition/review is a maintainer step, never install/launch.
The [data README](../data/protected-commands/v1/README.md) gives exact commands.

- **aqua (included MIT with notice):** root `registry.yaml` at the pinned commit,
  strictly decoded to JSON with the pinned data-only adapter. Union effective
  `files[].name`, `build.files[].name`, inherited defaults and all platform/version
  override branches. Include both ordinary and build lists; do not let one hide
  the other. An empty effective file list uses the effective named subpackage/
  repository tail, Go import-path basename, or effective package-name basename
  according to the pinned aqua semantics. Apply name-relevant package-type
  resets; empty override strings inherit, explicit empty lists trigger defaults.
  Registry package aliases are not automatically executable aliases. Templates,
  unknown types, malformed command-bearing values and unresolvable defaults
  fail generation rather than silently dropping coverage. This is a conservative
  name union, not a version/template evaluator or a tool installer.
- **mise (included MIT with notice):** `registry/<short-name>.toml` basename,
  `aliases[]` and `bins[]` are separate provenance categories. Missing bins never
  drops the short name. Strict TOML rejects duplicate keys and non-string values.
  Do not invoke mise, plugins, registry backends or user configuration.
- **Curated seeds (included identifier facts):** system, shell/grammar, VCS,
  package-manager, platform and manager files have pinned sorted LF bytes.
  These are independently maintained identifiers, not copied foreign prose,
  implementation code or a claim of complete system coverage. The reviewed
  `posix`, `coreutils`, `bash` and `zsh` identifier baselines reserve respectively
  **171**, **109**, **61** and **152** names (including Zsh module builtins).
  These are portable reservations even when the destination PATH contains none
  of them. Bash/Zsh identifiers retain shell-class, unwaivable provenance.
- **POSIX, GNU coreutils, Bash, Apple source projects (reference-only):** retain
  pins, license disposition and extraction method, not their uncleared bulk
  derived lists. No standards HTML/table layout, GPL/GFDL code/prose, Apple mixed
  collection or host-observed system export is vendored. The coreutils recipe
  maps source target `ginstall` to `install`, excludes `libstdbuf.so`; Bash counts
  only `$BUILTIN` blocks with `$FUNCTION`, not help-only records. Synthetic
  recipe witnesses test these distinctions. The offline coverage auditor also
  compares the curated baselines with exact pinned reference membership; it
  does not generate release entries or copy reference content into the artifact.
- **Zsh (reference-only in this release):** permissive core notice is recorded,
  but no bulk export pending per-file/module review. The recipe considers literal
  `BUILTIN` declarations, including modules, not completion function names.
- **Host macOS observation:** coverage evidence only, excluded. No host-specific
  executable list or proprietary content becomes portable inventory authority.

MIT notices for included exports are shipped intact. Neither those notices nor
this repository's license license the tools named in the list. Every source's
status is explicit; reference-only sources cannot contribute entry provenance.
The research's 4,412-key mixed specimen is not this production artifact.

Generation MUST yield identical bytes/digest despite source/seed enumeration
order or locale. Strict parsers reject duplicate/ambiguous keys, unsafe coercion,
YAML object tags, cyclic/over-limit data expansion and unresolved names. Maintainer
CI regenerates from authenticated pinned input bundles and compares complete
bytes, digest, counts and independent full system/shell baseline membership.
Digest-pinned private standards pages and source archives are audit inputs,
not artifact provenance. Omission control plants MUST fail even if a candidate
artifact has a self-consistent digest and source counts. New fixture
coverage is required for changed upstream naming semantics, not just a new hash.

## 3. Matching and overlap policy

Validate every **actual exposed** script, built binary, forwarding alias,
retained provider name and generated wrapper, not merely the package/skill name.
ASCII-fold A–Z on every platform, then repeatedly strip terminal `.exe`, `.com`,
`.bat`, `.cmd`, `.ps1` without regard to case. Thus `Git.EXE.CmD` matches `git`;
`git.helper` stays distinct. This portable static key also detects duplicate
selected/retained exports. Never use locale/Unicode folding or package PATHEXT.
All spellings/aliases/hard links occupy names. A context-only package called
`jq` exports nothing; a `system` dependency consumes an admitted command without
publishing a competing shim. Keep the existing `curator-*` skill-name guard too.

Real admitted-base PATH collisions and manager/shell namespaces are **never
waivable**. Captured manager launch aliases and trusted shell builtin/keyword/
function namespaces are checked independently of filesystem PATH. Skills cannot
source RC files, hooks or functions to bypass declarations. Never start a shell
or source startup files to discover namespace state. Require an admitted clean
shell or trusted adapter-owned name witness; a PATH-only check does not discover
arbitrary interactive user aliases.

A static-only overlap also refuses in v1, even for first-party/same-signer tools,
`--yes`, a package-carried grant or purported old approval. Existing
`environment_reserved_command_name` covers static reserved exports. Named
follow-up **command-static-overlap-approval-v1** owns a future explicit operator
protocol and protected storage; no grant schema, exception flag or approval is
implemented/published here. It would have to bind source/commit/directory,
command/alias, build/output bytes, inventory/normalization, scope and admission,
without waiving real collisions, shell/manager names or source/ownership rules.
Until accepted, rename/remove the export or consume an admitted dependency.
The research's grant-positive controls are replaced with these permitted
alternatives in v1; they do not simulate approval authority that does not exist.

## 4. Dynamic guard and publication boundary

The base PATH is the destination's ordered PATH **after child-environment
admission and before proposed profile commands**. It is not the producer's shell
PATH or a package literal. L1 owns the admission witness and D-PATH transport;
this companion neither invents arbitrary-directory admission nor reorders PATH.
An absent/excluded/malformed/unreadable witness refuses command capability,
never becomes an empty namespace or default PATH. Context-only behavior remains
separate. No repository `.agents/bin`, relative/current/empty element or
unadmitted source/runtime directory gains authority through this check.

At install/update/repair/sync/use or other command publication, plan the complete
selected/retained export set read-only. Under existing routing-domain/manager
mutation exclusion, check duplicates, static protections, manager/shell names
and destination base resolution; revalidate admission/owners immediately before
publication. Refusal publishes no lock, shim, generation receipt or unmanaged
destination change. Existing permitted private source-cache acquisition is a
separate effect, not permission for partial publication. Recovery keeps the
owning transaction/lease no-write guards.

Every launch exposing commands, including resume/recycle, repeats destination
admission/owner and collision validation even with an unchanged portable lock.
Probe only explicit `(export, admitted directory, approved executable suffix)`
candidates in directory order, using the actual filesystem's case/executable
semantics. Stop at a resolvable collision; report its original spelling and
admitted owner/target safely. Static folding is intentionally stricter than
case-sensitive Unix resolution. Non-executable Unix files are not command hits.
Broken/unreadable/unsafe links are typed admission failures, not clean misses.

Subtract only exact forwarders proven manager-owned by captured routing-domain,
generation, owner, content and link identity; separately validate retained owners.
Never exempt an entire mixed user-bin directory. Fake/stale/foreign wrappers
remain collisions/refusals. Base drift blocks before child start without fallback,
PATH reorder, tool execution, unlink/overwrite, or implicit lock regeneration.
The executable fixture oracle checks captured wrapper inode, content digest and
owner/generation tuples, but supplies no manager ownership/admission authority
or production mutation exclusion.

The algorithm is **O(commands × admitted directories × suffixes)**, independent
of inventory size after one immutable index is built. No network, subprocess,
version probing, recursive disk scan or directory enumeration is allowed at
publication/launch. Source parsing/enumeration happens only offline. A cached
absence requires valid namespace/link/permission/owner/admission exclusion, never
directory mtime alone. Arbitrary writable PATH can change after a probe: require
supervised routing-domain mutation exclusion/protected namespaces or checked
captured dispatch for the stronger command capability. Do not advertise a
PATH scan as a lifetime sandbox or protection from explicit absolute-path use.

## 5. Latency and qualification

The **20 ms added per launch** qualification budget applies precisely to the
**canonical-spelling path**: up to **64 explicit exported names/aliases**, up to
**12 local admitted directories**, and **one literal executable candidate per
export per directory** (at most **768 probes**). Generated wrapper filenames
are explicit exports and count toward the 64-name bound; static suffix folding
does not add filesystem candidates on this path. Both cold and every warm
sample must satisfy the same 20 ms bound. Count all inventory/index initialization if
it is not already immutable process state, identity checks, witness revalidation
and candidate probes. No process/network work may be hidden outside the timer.
Fixture creation and prior source generation are outside the measured check.
The reference resolver's separate safety limits (64 directories and 6 fixed
suffixes) are not this latency-qualified envelope. Multi-spelling lookup,
including Windows suffix resolution, and larger or network-filesystem envelopes
need **separate qualification**; a canonical-spelling result cannot qualify them.
The six-spelling stress retains the unchanged 20 ms target for comparison.
Recorded prior runs exceed it; it remains **unqualified** even when an isolated
later sample passes, and cannot support a passing launch claim. Consumers
must qualify their actual platform/filesystem/load and all required checks.
Slow envelopes require qualified admission/checked-dispatch design, not an
unsound absent-name cache, a raised budget or silent omission of checks.

The [benchmark witness](../conformance/protected-command-inventory-v1/README.md)
measures cold initialization plus bounded filesystem misses and warm checks at
64 exports and 12 local directories using one literal spelling on Unix. It
does not qualify Windows executable suffix lookup. A separate six-spelling portable
stress run is retained, including budget failures. It records the platform, input
identity, timings and bound, and checks the 20 ms target. It is
not a Windows/Linux runtime qualification or a whole-launcher benchmark. L1 and
Curator must supply real publication/launch, ownership/race and platform latency
proof before claiming the capability. The 27 paired vectors include preimages,
late drift, invalid authority and independent coverage/determinism controls.
