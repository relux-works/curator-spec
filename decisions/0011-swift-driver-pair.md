# Decision 0011: the Swift driver pair, `swift-v1` and `swift-repository-v1`

## Context

Decision 0008 reserved six driver identifiers and bound each to the portable
`manager-worker-v2` execution policy, receipt schema 3 for the local source mode
and 4 for the external one, and the single artifact class
`native-executable-v1`. Reservation is not admission: `swift-v1` and
`swift-repository-v1` leave the reserved namespace only when this contract is
accepted and `TASK-260728-251p01` moves them in the same change that mints the
schema admitting them.

Decision 0007 fixed one shared toolchain contract and left the `swift` registry
entry reserved with an explicit obligation list — probe vectors, normalization,
prerelease markers, root layout, primary-executable relpath, fingerprint
algorithm, companions, platforms, baseline, `compatibility` granularity and
initial set, and the metadata disposition table — to be completed on a qualified
host rather than asserted.

Swift's difficulty is not where Rust's is. Rust's problem is that its mainstream
build path executes package-selected code (`build.rs`, procedural macros) that a
bounded metadata query can nevertheless *see* without running. Swift's problem
is one level earlier and worse: **the package manifest is itself a program**.
`Package.swift` is Swift source that SwiftPM compiles and runs in order to learn
what the package declares. There is no `cargo metadata` for Swift — no bounded,
code-execution-free query that reports targets, products, dependencies, plugins
or binary artifacts.

Decision 0008 section 7 does not ask how to accommodate a package-selected
code-execution surface; it requires that every one of them be rejected
deterministically **before** the compile phase, and it states that a surface
which cannot be decided there is grounds to reject the driver rather than to add
a runtime allowance. Applied to SwiftPM that rule is decisive, and section 2
below records the measurement and the consequence.

This decision resolves that problem and fixes the complete `swift-v1` and
`swift-repository-v1` contract: the trusted closure, the manager-owned SDK
presentation, the source-set mapping, the two argument vectors, the
operation-private environment, the exhaustive pre-compile rejection matrix, the
Stage B disposition table and its acceptance layers, the artifact and identity
model, and the platform matrix. The implementation-ready reference is
[`docs/swift-build-drivers.md`](../docs/swift-build-drivers.md).

### Evidence basis

Every measured claim in this decision was produced on one host and is labelled
as such. Nothing here is a platform claim; decision 0008 section 9 keeps both
identifiers at an empty qualified-platform set until `TASK-260728-2bu2q6`.

| | Value |
|---|---|
| Host | macOS 26.5, arm64 |
| Swift | `Apple Swift version 6.3.2 (swiftlang-6.3.2.1.108 clang-2100.1.1.101)`, `swiftlang-6.3.2.1.108` |
| Toolchain root | `XcodeDefault.xctoolchain` from Xcode 26.5, resolved directly by path — never through `PATH`, `xcrun`, `xcode-select`, `DEVELOPER_DIR` or a version manager |
| SDK | `MacOSX.sdk` from the same Xcode |
| Windows | no Swift toolchain present on the reachable Windows host (`TASK-260729-rhjxtx`, 19 cases `not_run`) |
| Linux | not probed |

#### Prerequisite: `TASK-260729-rhjxtx`

`TASK-260729-rhjxtx` is a **prerequisite of this task**, linked `blocked_by` on
the board, not background reading. This decision re-measured every fact it could
re-measure on this host and records the re-measurement, so no unreviewed
observation is load-bearing on its own. Four inherited measurements are traced
individually:

| # | Inherited measurement | Consumed in | Status here |
|---|---|---|---|
| M1 | `swift --version` / `swiftc --version` split one banner across stdout and stderr | section 8, section 11 | **reproduced** on this host; the two agree |
| M2 | finding 6 — a `swift-frontend` job spawns for an unserved-but-known target before the standard-library failure | section 5 | **refined**, not contradicted: reproduces under a compile-only vector, and does **not** reproduce under this driver's linking vector, which fails at job planning with 0 frontend jobs |
| M3 | the Linux linking vector requires `swift-autolink-extract`, a fifth executable beyond the macOS four | sections 3 and 13 | **consumed unchanged**; it is the evidence that the member count is platform-determined |
| M4 | no reachable Windows host carried a Swift toolchain (19 cases `not_run`) | section 13 | **consumed unchanged**; it is why no Windows claim is recorded |

`TASK-260729-rhjxtx` also supplied the metadata-readability,
manifest-execution and selector-inertness observations, all of which were
re-measured here and are cited from this task's own evidence rather than
inherited.

The probe is `swift-boundary-fixture-v1`: 23 cases, 23 matched, 0 divergences,
32 closure checks yielding no verdict, **17 of 17** expected-red controls failing
as required, **70** structural checks with 0 divergences, the executed native
target admission holding, `green: true`, real exit 0.

## Decision

### 1. What the pair admits

`swift-v1` compiles one Swift program from a vendored, dependency-closed build
root inside the consuming skill snapshot. `swift-repository-v1` compiles one
Swift program from a build root inside a locked external Git repository. The two
share everything except source acquisition, audit subject, receipt schema, and
marker state, exactly as `go-v1` and `go-repository-v1` do.

| | `swift-v1` | `swift-repository-v1` |
|---|---|---|
| Source mode | local snapshot | external locked repository |
| Receipt schema | 3 | 4 |
| Execution policy | `manager-worker-v2` | `manager-worker-v2` |
| Source identity | `curator-build-source-v1` over the consuming snapshot | `curator-build-source-v1` over the external snapshot |
| Command shape | `buildCommandV8` | `repositoryBuildCommandV2` + `skillBuildTargetV2` |
| Project metadata | `Package.swift` at the build root, header line only | same, at the selected build root |
| Artifact class | `native-executable-v1` | `native-executable-v1` |

`swift-repository-v1` reuses this decision's trusted closure, SDK presentation,
native target, source-set mapping, argument vectors, environment, rejection
matrix, disposition table, link policy, staging rules and no-execution rule
without reinterpretation or widening. Where a rule below says "the driver", it
means both identifiers.

### 2. SwiftPM is rejected in its entirety, and the reason is measured

**Measured, macOS 26.5 arm64, Swift 6.3.2.** A `Package.swift` whose body writes
to standard error and attempts a filesystem write outside the package:

| Command | Manifest executed | Escape write landed |
|---|---|---|
| `swift package dump-package` | **yes** (`warning: 'probe-pkg': PROBE-MANIFEST-EXECUTED`) | no |
| `swift package --disable-sandbox dump-package` | **yes** | **yes** |

The manifest runs in both cases. The only thing that stopped the write was
SwiftPM's own macOS `sandbox-exec` policy, and a single documented flag removes
it. That is platform-specific containment supplied by the build tool, which is
precisely the class of guarantee decision 0006 says the portable policy does not
provide and decision 0008 section 7 forbids relying on.

There is no bounded alternative. **Measured**: `swift package tools-version`
returns exit 0 and the normalized version for a manifest whose body is
`this is @@ not swift (((`, while `swift package dump-package` on the same file
exits 1. The tools-version query reads the header line and nothing else — so the
*only* thing SwiftPM will tell you without running the package is the one datum
that is already a comment on the first line.

Therefore no `swift package` or `swift build` invocation can compute the
rejection matrix decision 0008 section 7 requires, because learning whether a
package declares a plugin, a macro target, a binary target, a system library
target or a network dependency means running the program that declares them.
Under section 7's own disqualification clause the answer is not to contain
SwiftPM; it is to remove it.

**The driver therefore never invokes `swift build`, `swift package`,
`swift run`, `swift test`, `dump-package`, `describe`, `resolve`,
`show-dependencies` or any other SwiftPM subcommand, in any stage, for any
purpose, including diagnostics.** The compiler is driven directly.

The consequence is stated plainly rather than softened: this driver builds
single-module, dependency-free, **macro-free** Swift programs. A package with
SwiftPM dependencies, plugins, macro targets or binary targets is not buildable
by `swift-v1`, and the rejection matrix of section 9 refuses it from snapshot
bytes before anything runs. Source that *uses* a macro — including one the
toolchain itself ships, such as `@Observable` — is not buildable either: section
4 rejects it at Stage B, from the source bytes, before the graph phase starts.

That rejection is a **byte rule over the compiled source set**, and it
deliberately over-rejects. A source file carrying the byte `0x40` (`@`) or
`0x23` (`#`) **anywhere** — including inside a comment or a string literal — is
rejected. The admitted language is therefore Swift **without attributes and
without pound-directives**: no `@main`, `@available`, `@escaping`, `@inlinable`,
`@Sendable` attribute spelling or property wrapper; no `#if`, `#available`,
`#file`, `#selector`, raw string literal or extended regex literal. What stays
admitted is measured rather than promised: the standard library, `Foundation`,
`Codable`, `Sendable` and `actor` conformances, `async`/`await`, generics,
bare regex literals, string interpolation, multi-line strings and Unicode
identifiers all carry neither byte. Section 4 states why the rule is drawn at
bytes rather than at syntax, and `TASK-260728-1egim2` carries the cost to
authors.

What this buys is a graph phase that is stronger than Rust's rather than weaker.
**Measured**: `swiftc -###` over the driver's exact compile vector exits **0**
and prints its job plan both for a source file containing
`this is not swift @@@ (((` and for a source path that does not exist, and
leaves the source directory byte-for-byte unchanged. Swift's graph phase reads
no package byte as a program at all.

### 3. The trusted closure is one executable-bearing root and one data root

**Measured**, with `PATH` set to a directory of 32 logging shims (`cc`, `clang`,
`ld`, `ld64`, `ld.lld`, `ld64.lld`, `lld`, `ld-classic`, `xcrun`,
`xcode-select`, `ar`, `libtool`, `dsymutil`, `codesign`, `sh`, `env`,
`swift-plugin-server`, `swift-autolink-extract`, `sandbox-exec` and thirteen
more), each of which records its own name and argv and exits 127:

| Run | PATH resolutions | Exit |
|---|---|---|
| the driver's fixed compile vector, `-target` and `-sdk` pinned | **0** | 0 |
| the same vector plus `-use-ld=lld` | **2** (`ld64.lld`, twice) | 1 |

The second row is the control, and it is what makes the first row mean anything:
the shim directory demonstrably intercepts a linker chosen by name, in the same
working directory, in the same run sequence. `-use-ld` is not in the driver's
vector; it exists in the probe only to prove the harness bites. The probe also
carries an expected-red control (`C5`) that reports a zero obtained with the
shim directory off `PATH` as **unearned**, so a future run cannot quietly
substitute a meaningless zero for this one.

Swift differs from Rust here in kind. `rustc` unpinned resolves `xcrun` and `cc`
through `PATH`; `swiftc` unpinned resolves **nothing** through `PATH` and
instead fails closed with
`error: unable to load standard library for target 'arm64-apple-macosx26.0'`.
The pins are still mandatory — a driver that relied on the toolchain's default
SDK search would be depending on unfingerprinted host state — but the property
being protected is narrower than Rust's.

**The required process closure is four executables, and two of them are one
file.** **Measured**: `swiftc` is a symlink to the single `swift-frontend`
binary inside the root, which dispatches on `argv[0]`; the driver plans two
`swift-frontend` frontend jobs and one `clang` job, all named by absolute path
inside the root; and `clang -print-prog-name=ld` reports
`<root>/usr/bin/ld`. No Apple `xcrun`, `ar`, `dsymutil` or `codesign` process
participates, and `swiftc` plans no link job of its own — it starts `clang`, and
`clang` starts the linker.

**`swift` is not a member of that closure**, and the contract says so rather
than leaving it to be inferred. It is the SwiftPM launcher, section 2 forbids it
from every stage, and the driver never invokes it, so requiring it to resolve
would impose a portability constraint that buys no property. Its bytes are
inside the fingerprinted root and are covered by `tree_sha256` regardless. The
conformance probe of section 10 uses it as the upstream oracle, which is a role
outside any manager pipeline. It is therefore **probe-only, and absent from the
runtime closure and from the registry's required member set**.

The member set is **platform-determined**, and the rule that fixes it is
structural rather than a fixed list: *every executable the verified job plan
names, plus the linker the C driver resolves, MUST lie inside the
`swift-toolchain` root.* On this host that instantiates to four. Linux was
**measured** to add a fifth, `swift-autolink-extract`; Windows is unmeasured and
section 13 states its obligation without naming a count it cannot support.

```text
manager parent
  -> identity-verified manager-owned worker
       -> fingerprinted <swift-root>/usr/bin/swiftc        (= swift-frontend)
            -> fingerprinted <swift-root>/usr/bin/swift-frontend   (x2)
            -> fingerprinted <swift-root>/usr/bin/clang
                 -> fingerprinted <swift-root>/usr/bin/ld
```

**The platform SDK is bound as a second fingerprinted root that contributes no
process.** It is data — headers, `.tbd` stubs and framework stubs the compiler
and linker read. Decision 0008 section 6 item 3 names an SDK explicitly among
the components a driver must bind or reject a platform over, so binding it is
required even though it starts nothing.

A link-support root is resolved through the same two declaration channels
decision 0007 section 3 fixes for a toolchain root — a root bundled with the
manager distribution, or trusted operator configuration in manager-owned
owner-protected state — and through nothing else. `PATH`, the inherited
environment, `xcrun`, `xcode-select`, `DEVELOPER_DIR`, a package byte, a
descriptor byte and a version-manager shim are all forbidden origins for it,
with the same force and the same diagnostics as for the primary root. A missing
or unusable link-support declaration is a Stage A failure before any source is
acquired.

This does **not** coin a new toolchain identifier. Decision 0007's closed set
`{go, rust, swift, kotlin, jdk}` is untouched, the `swift` entry declares **no
companion toolchain**, and `toolchain_identities` carries exactly one element
for both drivers. `curator-swift-toolchain-v1` fingerprints an ordered closure
of roots rather than a single tree, in the same shape decision 0009 introduced
for Rust and with its own domain prefix:

```json
{
  "algorithm": "curator-swift-toolchain-v1",
  "swift_version": "Apple Swift version 6.3.2 (swiftlang-6.3.2.1.108 clang-2100.1.1.101)",
  "swift_compiler_tag": "swiftlang-6.3.2.1.108",
  "native_target": "arm64-apple-macosx",
  "manager_invoked": [
    {"role": "swift-toolchain", "relpath": "usr/bin/clang"},
    {"role": "swift-toolchain", "relpath": "usr/bin/swiftc"}
  ],
  "linker": {"role": "swift-toolchain", "relpath": "usr/bin/ld"},
  "runtime_library_members": [
    {"role": "platform-base-installation", "relpath": "."},
    {"role": "swift-toolchain",            "relpath": "usr/lib/swift/macosx"}
  ],
  "roots": [
    {"role": "swift-toolchain", "tree_sha256": "sha256:..."},
    {"role": "platform-sdk", "tree_sha256": "sha256:..."}
  ],
  "closure_sha256": "sha256:..."
}
```

Every member is a `(role, relpath)` pair, and **the shape is
platform-parametric**: the macOS values above are a measured instance, not
constants of the algorithm. This is the cycle-2 repair. Previously the object
serialized four macOS constants (`usr/bin/swiftc`, `usr/bin/swift-frontend`,
`usr/bin/clang`, `usr/bin/ld`) while the runtime closure was defined
structurally from the job plan and P3, which left a Windows implementation with
no way to serialize a linker that is not `usr/bin/ld` and no rule for more than
one SDK root.

`linker` is now **whatever P3 resolves**, serialized relative to its containing
root by `curator-swift-relpath-v1` (reference section 2.4) — the same function
for `usr/bin/ld` and for an unmeasured `usr/bin/link.exe`, with the extension
part of the final component. `manager_invoked` carries only the executables the
manager itself starts, which are known in Stage A before any plan exists.

No root *path* appears: toolchain location is not portable identity, exactly as
decision 0007 section 3.2 requires. Root roles are a closed manager-owned token
set with **per-platform cardinality**: `exactly-one` roles serialize bare
(`platform-sdk`), `one-or-more` roles serialize with an ordinal
(`platform-sdk[0]`) assigned by declaration order — **always** bracketed, even
for a single root, so that declaring a second root later cannot silently change
the identity of the first. Windows declares `platform-sdk` as `one-or-more`.
`closure_sha256` is domain-separated over the ordered role-token and per-root
digest pairs, so an *n*-root closure can never collide with an *n+1*-root one
that happens to hash the same bytes. `curator-go-toolchain-v1` and
`curator-rust-toolchain-v1` are untouched, and neither Swift driver reuses,
extends or aliases either.

**The plan-derived executable set lives in a second object, and that is
deliberate.** The structural rule above is only decidable after the graph phase,
while this identity is computed in Stage A. So the verified plan's executables
are recorded in `curator-swift-process-closure-v1`, minted at permit time and
carried in the **receipt** rather than in the cache key, in two projections:
`invoked` — the relpaths as spelled, **four** on this host — and `resolved` —
what those spellings resolve to, **three**, because `swiftc` is a symlink to
`swift-frontend`. Binding only `resolved` would lose that the driver invokes
`usr/bin/swiftc`; binding only `invoked` would let a re-pointed symlink keep one
identity while executing other bytes.

Keeping it out of the cache key is a completeness claim, not an omission: the
plan-derived set cannot vary independently of inputs the key already binds —
both root digests, the compiler version and tag, the native target, the fixed
argument vectors and the ordered source set. Putting it in would force a graph
phase before every cache lookup and buy no distinction.

**Measured fingerprint cost, same host.** The toolchain root is 2.57 GiB across
5,109 regular files and 91 symlinks and walks-and-hashes in 5.89 s; the SDK root
is 0.71 GiB across 32,345 regular files and 7,448 symlinks and takes 5.60 s. The
cost is per operation and per root, and it is stated rather than optimised away:
memoising it across operations would weaken exactly the property decision 0007
says fingerprinting proves.

### 4. The macro plugin surface, and why the SDK is presented rather than passed

This is the one place where Swift hides an executable outside the toolchain, and
it is reachable from ordinary package source rather than from a manifest.

**Measured**: the driver injects plugin search paths into every frontend job
without being asked, and the *external* ones are derived from the `-sdk`
argument, three ancestor levels up and then into `Developer/usr`. With the
declared Xcode SDK path passed directly, **two distinct** derived paths exist
outside every fingerprinted root — the plugin directory
`…/MacOSX.platform/Developer/usr/lib/swift/host/plugins` and the server
`…/MacOSX.platform/Developer/usr/bin/swift-plugin-server` — and
`import Foundation; #Predicate { … }` loads `FoundationMacros` **through a
`swift-plugin-server` process in that tree**. Even the toolchain's own
`ObservationMacros` is loaded through that external server when it is available.

The manager therefore never passes the declared SDK path. It creates an
operation-private directory it owns entirely and presents the SDK through it, at
a fixed nesting depth:

```text
<staging>/sdk/                                created by the manager, contains exactly present/
<staging>/sdk/present/                        created by the manager, contains exactly SDKs/
<staging>/sdk/present/SDKs/MacOSX.sdk    ->   <declared platform-sdk root>
```

and passes `-sdk <staging>/sdk/present/SDKs/MacOSX.sdk`. The depth is not
cosmetic: **measured**, the derivation walks three levels up from the SDK path,
so presenting at this depth lands every derived tree inside `<staging>/sdk`,
which the manager creates and keeps empty apart from the presentation chain.

**Measured** with that presentation: the plan carries 14 plugin components over
two frontend jobs — 6 distinct paths, of which 2 exist and both are inside the
toolchain root, 4 do not exist, and **0 exist outside a fingerprinted root**;
every SDK-derived component lands inside `<staging>/sdk` and none of them
exists; `#Predicate` fails to compile with
`error: external macro implementation type 'FoundationMacros.PredicateMacro' could not be found`;
`@Observable` still compiles with exit 0 and its remark now names
`<root>/usr/lib/swift/host/plugins/libObservationMacros.dylib` **with no plugin
server at all**; and the whole run resolves nothing through `PATH`.

So the presentation removes an executable plugin server from the closure. It
does **not** remove macro support that the fingerprinted toolchain itself
provides, and cycle 2 stopped there and called the remainder admitted. That was
wrong against accepted decision 0008 section 7, which requires every driver to
reject every package-selected code-execution surface — **procedural and compiler
macros explicitly named** — before the compile phase, and forbids answering such
a surface with a runtime allowance. `@Observable` in package source is package
bytes selecting which implementation the compiler loads and runs. Fingerprinting
the implementation constrains its provenance; it does not turn the load into a
rejection.

**The load cannot be suppressed while `swiftc` runs its own jobs.** Four
negative measurements, not an argument:

| Attempt | Measured |
|---|---|
| `-resource-dir <manager-owned>` | 0 of 10 plugin components move; they derive from the driver's own executable location |
| present the toolchain the way this section presents the SDK | 0 of 10 move; the driver resolves its own executable before deriving anything |
| point `-in-process-plugin-server-path` at an absent file | the compile still exits 0 and the macro **still loads**, because the implementation is loaded directly rather than through the named server |
| find a disabling flag | neither `swiftc` nor `swift-frontend` defines one |

Cycle 3 answered that by having the manager execute the plan's jobs itself with
the plugin flags deleted. That worked, and it is **not admissible**: accepted
decision 0008 section 7 closes a `manager-worker-v2` session to at most one graph
command and **exactly one** compile command, started by the driver's own trusted
launcher, and a driver that cannot map onto that shape must not be admitted under
v2 at all. **Measured** on the default source set: that design starts **4**
manager commands — one graph plus three plan jobs — and starts `swift-frontend`
and `clang` directly instead of through `swiftc`. It changes both the command
cardinality and the process parentage the policy label names. Expected-red
control `C15` restores it and reports both. This decision keeps the accepted
policy and drops the design.

**So the surface is closed at the other end: the source bytes, before anything
runs.** `curator-swift-source-admission-v1` is a Stage-B rule applied to the
compiled source set after section 6 enumerates it and **before the graph phase
starts**:

```text
a source file is admitted only if
  1. it is well-formed UTF-8 (RFC 3629) and carries no NUL, and
  2. it contains neither the byte 0x40 ('@') nor the byte 0x23 ('#').
```

The rule does not parse Swift, does not normalize, does not skip comments or
string literals, and reads nothing a package supplies except the source bytes
themselves. It is a byte scan, so it is **total over every possible file** and
there is nothing in it to argue with. Rejection is
`build_package_code_execution_forbidden` with the Swift detail
`swift_source_macro_selector_forbidden`, and **no command is started**: no graph
phase, no compile permit, no compile child.

Encoding is checked before the selector scan, and that order is normative. The
scan's claim is "no `0x40` byte implies no U+0040 code point", which only holds
on well-formed UTF-8; a malformed file is rejected rather than scanned.

**Why those two bytes are the whole macro-selection surface is measured, not
argued from the grammar.** Six measurements, on Apple Swift 6.3.2 / macOS 26.5
arm64:

| # | Measured |
|---|---|
| the compiler states the expansion rule | `externalMacro(module:type:)` without the sigil: `error: expansion of macro 'externalMacro(module:type:)' requires leading '#'` |
| the compiler states the declaration rule | a `macro` declaration with no role attribute: `error: macro 'stringify' must declare its applicable roles via '@freestanding' or '@attached'` |
| no bare-name channel | `Observable final class Box {}` is not an attribute; it is a parse error |
| no escape channel | `\u{40}Observable` outside a literal is not syntax; parse error |
| no homoglyph channel | `＠` U+FF20 is an identifier character, not an attribute marker; parse error |
| no encoding channel | an overlong UTF-8 encoding of U+0040 (`0xC1 0x80`) carries no `0x40` byte, is rejected by rule 1 above, and is **independently** rejected by the compiler with `invalid UTF-8 found in source file` |

Swift has exactly two macro-use spellings — an attached macro is a custom
attribute and needs `0x40`, a freestanding macro is an expansion and needs
`0x23` — and the compiler enforces both requirements itself. A source set
carrying neither byte cannot name a macro.

**The injected plugin search paths therefore stay in the plan and are inert.**
The manager cannot remove them without executing the jobs itself, which the
policy forbids, so the contract does not pretend to. **Measured** on the
admitted rich-Swift source set under the contract's own single compile command:
the plan carries **5** plugin components, the compile exits 0, there are **0**
macro-load remarks, and the artifact runs. Importing a macro-bearing module
without using a macro also loads nothing: `import Observation` alone gives **0**
remarks, because a macro-bearing module is a prebuilt `.swiftmodule` whose own
expansion already happened in the library build.

Closure and selection are two independent conditions and both are checked:

- **closure** — section 4's plan verification requires every plugin path in the
  plan to resolve inside a fingerprinted root or to be absent, and re-checks that
  at the compile permit; and
- **selection** — Stage B makes it impossible for an admitted source set to name
  a macro at all.

Neither is asked to carry the other. Expected-red control `C13` restores the
retired Stage B — no source admission — and reports that the macro-selecting
source is then admitted, receives a compile permit and loads
`libObservationMacros.dylib` from inside the toolchain root; structural check
`S55` is the positive assertion that under the live rule the same source is
rejected with **0** manager-started commands and no artifact.

The cost is stated rather than hidden. **This driver compiles no Swift that uses
any macro**, including the toolchain's own, and the byte rule takes every
attribute and pound-directive with it as deliberate collateral: `@main`,
`@available`, `@escaping`, `@inlinable`, the `@Sendable` attribute spelling,
`@_cdecl`, `@_silgen_name`, property wrappers, `#if`, `#available`, `#file`,
`#selector`, raw string literals and extended regex literals. A sigil inside a
comment or a string literal is rejected too. That over-rejection is the price of
a rule that is byte-total and needs no Swift parser in the manager; a narrower
rule would need one, and a parser the manager writes is a second implementation
of a grammar the compiler owns. Section 2 states the consequence as part of what
the pair admits, and `TASK-260728-1egim2` carries it as the second thing an
author meets, after the single-module one.

The presentation is not trusted on its own, because a path-derivation rule is
exactly the kind of thing a toolchain update can change. The manager also
**verifies** it, from the graph phase, against the plan it is about to execute.
That verification is a fail-closed grammar rather than a scan, and it is total
over **every token of every job line**, not merely over the ones that look like
paths. The reference document fixes the closed per-job flag and operand tables,
the five buckets every path value must satisfy, the opaque-value rule that stops
a non-path token becoming a value carrier, and the mandatory rejection for every
line, flag, value and operand the tables do not claim. Nothing is skipped, and
no token is left unclassified.

Cycle 2's totality stopped at path-shaped tokens, and the gap was live: an
unknown `-flag` fell off the end of the dispatch chain, a joined `-flag=value`
was never split, and `-Xllvm` and `-Xcc` hand their value to a second option
parser. **Measured**: this toolchain defines `-load-pass-plugin=<path>`, a
joined flag whose value is a dynamic library the compiler loads, and the retired
verifier accepted it because the token itself is not path-shaped. Of 16
unknown-channel vectors, the retired verifier admits **14** and the closed
grammar rejects **16 of 16**, while the plan the toolchain actually emits — 101
tokens over three jobs — still verifies with 0 rejections. Expected-red control
`C14` reports the gap; a future toolchain token requires a measured contract
revision before it can be allowlisted.

Two properties of that verification are load-bearing and are stated here so they
are not implementation details:

- **Containment is resolved, not lexical.** Both the candidate and the root are
  symlink-resolved before the comparison, and the comparison is byte-exact on
  path components. A path lexically below a root but symlinked out of it is a
  rejection, and on a case-insensitive volume a case variant fails closed rather
  than passing.
- **Every verified path is bound and re-checked at the compile permit, and the
  permit is a step in the session.** The session order is normative:
  `AdmitSources` → `graph_argv` → `VerifyPlan` → **the permit** → `compile_argv`.
  `compile_argv` is reachable only through the permit; a manager that starts it
  any other way is not implementing this driver, whatever else it checks.

  A binding records the raw plan token, the path whose identity was **actually**
  established, that path's resolved target, and its identity. Those first two
  differ in exactly one case — an output that does not exist yet, where what was
  verified is the operation-private **parent** — and the distinction is normative
  rather than incidental: a permit that re-resolves the raw token for such a
  binding rejects every ordinary happy path. Stage B additionally binds the
  **digest** of each admitted source, because file identity is size, mode and
  mtime, all of which a writer can restore.

  Immediately before the compile child starts, the manager re-resolves every
  binding and requires an identical resolution and identity, requires every
  admitted source to still carry its Stage-B digest, and requires every absent
  plugin path to still be absent — where *absent* means the re-resolution
  returned `ENOENT` and nothing else. A permission error, an I/O error or a
  dangling symlink is not evidence of absence and fails closed. Any finding is
  `build_execution_control_unavailable` / `swift_permit_binding_changed`, leaves
  exactly **one** manager-started command, and produces no artifact.

  This narrows the window rather than removing it; what actually closes it is the
  ownership requirement the declaration channels already impose — both
  fingerprinted roots are manager-distribution or owner-protected manager-owned
  state, and staging is operation-private, so no other principal is admitted as a
  writer. The re-check is the defence that does not depend on that assumption.

  **Measured inside the session**, each mutation landing after plan verification
  has already accepted the whole plan: the unmutated session re-checks 35
  bindings, reports nothing and reaches 2 commands; an appearing plugin path, a
  source that gains a `@`, a source replaced by rename, a re-pointed SDK
  presentation, a replaced output parent and a changed executable each stop the
  session at **1** command with no artifact.

A path that exists outside every fingerprinted root, a token no table claims, an
opaque value that carries a path or a separator, a `-Xllvm` or `-Xcc` value
outside the platform's measured allow-set, and a binding that changed between
graph and permit each fail `build_execution_control_unavailable` before the
compile phase. A source file the Stage-B rule rejects fails
`build_package_code_execution_forbidden` before the graph phase, so it fails
earlier than any of these. Nine expected-red controls hold this together: `C6`
restores the unchecked plugin closure and reports the live external plugin tree
it admits, `C7` restores the lenient parser and reports how many malformed plans
it lets through, `C8` restores lexical containment and reports the symlink escape
it admits, `C5` reports an unearned `PATH`-closure zero, `C13` restores the
retired Stage B and reports the macro-selecting source it admits to a compile
permit, `C14` restores path-shape-only totality and reports the 14
unknown-channel vectors it admits, `C15` restores the retired
plan-execution design and reports the 4 manager commands it starts where
`manager-worker-v2` admits 2, `C16` removes the permit step and reports that a
plugin path verified absent may then appear and the session still starts 2
commands, and `C17` restores the retired binding model and reports the 5 findings
it raises on a verified happy path where the live permit raises 0, and the 0 it
raises on an absent plugin path whose state cannot be established where the live
permit raises 1.

### 5. Native target: representability is not admission

**Measured, same host.** `swiftc -print-target-info -target
x86_64-unknown-linux-gnu` exits **0** and reports
`paths.runtimeLibraryPaths` naming `<root>/usr/lib/swift/linux`, a directory
that **does not exist** in the tree. `-print-target-info -target
not-a-real-triple` exits 1.

The native target identity is `target.unversionedTriple` from
`swiftc -print-target-info`, which on this host is `arm64-apple-macosx`. It is
the identity form and **not** a usable `-target` argument: **measured**,
`-target arm64-apple-macosx` fails with
`error: Swift requires a minimum deployment target of macOS 10.9.0`. The value
passed to the compiler is `target.triple` (`arm64-apple-macosx26.0` on this
host), whose deployment-version component is supplied by the SDK. Both are
recorded; only the unversioned form enters identity, because the versioned one
would make cache identity move with an SDK update that changed nothing else
about the closure.

Admission is a manager-side check over the **executed** P2 probe —
`swiftc -print-target-info -target <target.triple>`, the exact triple the
compile passes — and it is a **closed three-class partition**, not a filter over
whatever happens to be in the root.

Cycle 1 required only that entries *already inside the toolchain root* exist.
That is not a closure: it said nothing about an empty list, an entry outside
every root, or a dangling symlink. The obvious repair — every entry must resolve
inside a fingerprinted root — **would reject the host this contract is measured
on**. **Measured**, P2 for `arm64-apple-macosx26.0` returns two entries:
`<root>/usr/lib/swift/macosx`, and `/usr/lib/swift`, the Swift runtime macOS
ships in the OS, which exists and is outside every fingerprinted root.

So the closed set is three classes: **A** in-closure, resolving inside a
fingerprinted root; **B** base-installation, resolving inside a closed,
registry-declared, per-platform prefix set — the *same* trust boundary section
13's acceptance test already accepts when it requires the produced executable's
dynamic dependencies to be base-installation libraries of the declared baseline;
and **C** everything else, which **rejects**. Reference section 1.3 states the
seven rules; the load-bearing ones are that the list must be **non-empty**, that
every entry must **resolve to a directory** (a dangling symlink is a rejection
distinct from an absence), that **at least one** entry must be class A, that
class-B entries enter identity under the reserved role
`platform-base-installation` so a runtime moving between the OS and the closure
moves cache identity, and that a declared base prefix may **not** lie inside a
fingerprinted root, which would launder a class-A obligation.

**The class-B hatch is narrow, and that is measured rather than argued**: the
class-B entry never reaches a compiler child. In the verified job plan the
linker job's search paths are `<root>/usr/lib/swift/macosx` — the class-A entry
— and the presented SDK's `usr/lib/swift`. The bare `/usr/lib/swift` appears as
**zero** tokens in the plan. Section 4's plan verification stays total and
admits no base-installation path in any bucket.

The prefix set is **empty** for every platform but macOS, so an unmeasured
platform fails closed: an out-of-root runtime path rejects rather than being
waved through, and the repair is a measurement.

A target whose standard library is absent fails Stage A with
`build_toolchain_platform_unsupported`, before source acquisition and before any
compiler child. `-print-target-info` remains a representability surface and MUST
NOT be used as the admission test — the admission is the rule above, applied to
its output. **Measured**: for `x86_64-unknown-linux-gnu`, P2 returns exactly one
entry, `<root>/usr/lib/swift/linux`, which is class-A-shaped and does not exist,
so the rule rejects it.

Expected-red control `C11` restores the cycle-1 rule and reports that it admits
**6 of 6** shapes the closed rule rejects.

**A refinement of `TASK-260729-rhjxtx` finding 6, measured rather than
repeated.** That task measured a `swift-frontend` job spawning for
`x86_64-unknown-linux-gnu` before the standard-library failure, and concluded
that Swift rejects an unserved-but-known target only after starting a compiler.
That reproduces here **for a compile-only vector**: `-c -v` spawns 1 frontend
job and then fails. Under **this driver's** vector, which links, the same target
fails at job planning with `error: unableToFind(tool: "swift-autolink-extract")`
and spawns **0** frontend jobs. Both facts are true; the vector is what
separates them. Because the driver always links, its `-###` graph phase already
refuses the target before any compiler child, and the Stage A stat gate refuses
it earlier still.

Cross-compilation is forbidden. The compile command always passes `-target` with
the resolved native triple, so the target is manager-selected rather than
inferred.

### 6. Local source ownership: one build root, one manifest header, one program

`swift-v1` reuses the schema-6 and schema-7 `build_roots` model without change,
and adds exactly the bindings decision 0008 section 4 requires of a local
driver.

- The build root MUST contain `Package.swift` directly, and that file MUST be
  the nearest ancestor `Package.swift` of `source_dir`. It is the bound
  project-metadata file, and the manager's **entire read of it is the bytes up
  to the first LF, with one trailing CR removed** — deliberately *not* the
  bare-CR rejection of section 8, because this is untrusted input authored on an
  unknown host where CRLF is an ordinary fact, whereas the job plan is trusted
  output measured to carry zero CR bytes. No byte after that LF is a
  metadata input, is scanned, or can change any verdict the manager reaches. The
  body is never parsed, compiled, executed, or passed to the compiler, and the
  file is excluded from the compiled source set.
- `source_dir` MUST equal its build root. Swift has no compilable sub-unit a
  directory path can name once SwiftPM is gone, so any other value would either
  be inert or would require a package-controlled selector member the boundary
  forbids.
- The build root MUST contain a `Sources` directory directly.
- The **compiled source set** is exactly every regular file under
  `<build_root>/Sources` whose name ends in `.swift`, taken recursively, ordered
  by relative path in Unicode-scalar order. The set MUST be non-empty.
- Every other entry under `<build_root>/Sources` MUST be a directory. A regular
  file that is not `.swift`, a symlink, a device, a socket or a fifo anywhere in
  that subtree is a rejection, not something to skip.
- Every compiled source relative path MUST be free of ASCII control bytes
  (`0x00`–`0x1F` and `0x7F`). This is the one source-name restriction, it is
  narrow on purpose, and it is **measured** rather than precautionary: a source
  whose name carries a newline splits its job across physical lines of the
  `swiftc -###` plan, which breaks the line-oriented grammar the graph phase
  verifies. A quote, a space, a `#` and a leading `@` are all admitted, because
  the measured quoting grammar renders each of them unambiguously and the
  verifier round-trips every source token against the manager's own ordered
  list. The rejection is `build_source_layout_invalid`, in Stage B, before the
  graph phase.

**The `Package.swift` read is one line, and the classifier of section 10 has no
other input.** That is a stronger statement than "the body is not compiled", and
it is the reason it can be made without qualification. Upstream is different, and
the difference is measured rather than assumed: `swift package tools-version`
reports `9.9.0` with exit 0 for a manifest whose only specification sits **inside
a multi-line string literal**. A whole-file scan would therefore let arbitrary
manifest body bytes set the version a manager compares. Curator reads line 1 and
stops; a specification below it is `rejected-absent-header`, because *absent*
means "line 1 carries none", not "the file carries none". Section 10 records that
refusal as a member of the security partition rather than hiding it.

That chain is the deterministic non-discovering mapping decision 0008 section 4
demands, and it is worth being precise about why an enumeration satisfies
"non-discovering". The rule performs no *selection*: it is total over
`Sources`, so there is no candidate set to search, no heuristic, no preference
order and nothing a package can arrange to be chosen over something else. A
partial rule — "the first file containing a `main`", "the directory matching the
command name" — would be discovery, and is rejected in the alternatives below.
Totality is also what makes the non-`.swift` rejection load-bearing: because
nothing is silently skipped, the set of bytes the compiler sees is exactly the
set of bytes the audit subject contains.

The consuming manifest command key remains the sole naming authority. The
module name passed to the compiler is manager-derived and fixed; no package
string reaches an argument vector.

**The derivation is `curator-swift-module-v1`, and it is total.** The two
grammars do not overlap — a command key matches
`^[A-Za-z0-9][A-Za-z0-9._-]*$`, is unbounded and may start with a digit, while a
Swift module name matches `^[A-Za-z_][A-Za-z0-9_]{0,63}$` — so a mapping is
required, and the obvious one is unsound: replacing every character outside the
module alphabet with `_` merges `my-tool`, `my.tool` and `my_tool` into one
module identity that the protocol keeps distinct. The reference document fixes
the derivation; its properties are that it is total over every protocol-valid
key including punctuation, leading digits and overlength, deterministic,
**injective by construction on the short branch** — a decoder inverts it —
and collision-resistant on the overflow branch through a 160-bit digest of the
whole key rather than of a truncation. The manager-reserved prefix also forces
the result to start with an uppercase letter, so a derived name can never be a
Swift keyword and can never be the `Swift` standard-library module, which a bare
escape would produce for the key `wift`. **Measured**: no module in the
toolchain root or the platform SDK carries the reserved prefix. Expected-red
control `C9` restores the replacement rule and reports the collisions it admits.

Identity does not rest on that injectivity at all: section 12 binds the
consuming **command key itself** into the canonical build input alongside the
module name, so two keys could not share a cache identity even if they shared a
module name.

Two programs require two build roots. That duplicates any shared source, and it
is the accepted cost of refusing a package-controlled target selector.

### 7. External source ownership

A `swift-repository-v1` command requires a `skill-build.json` **schema 2**
descriptor. Against a schema-1 descriptor it fails
`build_descriptor_driver_unsupported`, and against an unsupported descriptor
version `build_descriptor_schema_unsupported`, with no fallback to another
target, another driver, `go-repository-v1`, a script, a system command or a
generic build facility.

The descriptor target's `build_root` and `source_dir` carry their schema-1
meaning. For this driver `source_dir` MUST equal `build_root`, by the same
argument as section 6; `build_root` MAY be `.`, which the descriptor already
admits and which does not affect the schema-6 prohibition on a local
`build_root` of `.`. Every rule of section 6 about `Package.swift`, `Sources`,
the compiled source set and the forbidden entry kinds applies unchanged to the
selected external build root.

The whole external snapshot remains the validation, identity and audit subject;
only the selected build root is compiler-visible; no external repository byte is
agent-facing or runtime-copied. Input MUST NOT come from the consuming skill,
another external repository, a sibling or parent directory outside the selected
build root, a host SwiftPM cache, a host `~/.swiftpm`, or the network.

### 8. The fixed process graph and exactly two commands

One `manager-worker-v2` session performs exactly one graph phase and exactly one
compile phase, which is the same session shape `manager-worker-v1` fixes for Go,
under the v2 identity and the v2 process graph.

With the canonical `source_dir` as the working directory, the manager MUST use
exactly these two argument vectors and MUST NOT alter, extend, reorder or repeat
them:

```text
program      := the resolved absolute swiftc inside the swift-toolchain root
compile_args := [ "-swift-version", "6", "-O",
                  "-target", <native-triple>,
                  "-sdk", <presented-sdk>,
                  "-module-name", <module>,
                  "-no-color-diagnostics",
                  <sources…>, "-o", <staged-artifact> ]
graph_args   := [ "-###" ] ++ compile_args
compile_argv := [ program ] ++ compile_args
graph_argv   := [ program ] ++ graph_args
```

The relation is stated as a **construction** rather than as a comparison,
because the cycle-1 wording — "they differ in exactly one token, at index 0" —
is ambiguous when read as complete argv: index 0 is the *program*, and `-###` is
an **insertion after** it. Mechanically, and all asserted rather than assumed:
`len(graph_args) == len(compile_args) + 1`; `graph_args[0] == "-###"`;
`graph_args[i+1] == compile_args[i]` byte-exactly for every `i`;
`graph_argv[1] == "-###"`; `-###` occurs **exactly once** in `graph_argv` and
**never** in `compile_argv`; and both vectors share one `program`.

`-###` cannot collide with another token — sources are absolute paths and the
module name matches `^[A-Za-z_][A-Za-z0-9_]{0,63}$` — but the uniqueness is
asserted anyway, because "cannot collide" is an argument and an assertion is a
check.

That is the property the graph phase rests on: the plan the manager verifies is
the plan the compile phase executes, because both come from **one** builder and
cannot drift. Five negatives are exercised — no insertion, doubled, appended
instead of inserted, present in the compile vector, and a second token co-mutated
under cover of the insertion — and all five must be rejected.

**Both vectors are executed, and they are the only two commands the manager
starts.** `graph_argv` is the graph phase; `compile_argv` is the compile phase,
run once, and only after the permit of section 4 has run and reported nothing.
The manager starts nothing else — no plan job, no
frontend, no `clang`, no linker. `swiftc` starts those itself, as the driver's
own trusted launcher, which is exactly the `manager-worker-v2` process graph
decision 0008 section 7 fixes.

**Measured** on the default source set: **2** manager-started commands,
`swiftc -###` then `swiftc`. The retired cycle-3 design starts **4** for the same
sources — one graph plus three plan jobs — and starts `swift-frontend` and
`clang` directly; expected-red control `C15` restores it and reports both the
count and the parentage.

Because the compile phase re-derives its own plan, "the plan verified is the plan
executed" is an equality of *inputs* rather than of processes: both commands come
from one builder, over one source set, in one environment, and differ by one
inserted token. Section 14 states the residual honestly rather than claiming the
stronger property the retired design had.

`<native-triple>` is the Stage A resolved `target.triple`, `<presented-sdk>` is
the manager-owned presentation of section 4, `<module>` is the
`curator-swift-module-v1` derivation of section 6 over the consuming command
key, `<sources…>` is the ordered source set of section 6, and
`<staged-artifact>` is inside operation-private manager staging. None is copied
from a manifest, a descriptor, or an unvalidated package string.

The planned **job** argv is a different thing from these two vectors and is not
reproducible: **measured**, it carries a per-run temporary directory the driver
creates under the operation-private `TMPDIR`. That is expected and is why the
verification of section 4 is a bucket-and-boundary check over the plan rather
than a comparison against a fixed expected plan.

**The plan's own byte layout is fixed, on every platform**, because a Windows
implementation must not have to choose between two readings. The plan is read as
a **binary stream**; LF (0x0A) is the only line terminator; the **terminal LF is
mandatory** — measured, the plan's final byte is 0x0A, so a plan not ending in
LF is a truncated read and rejects; a **bare CR rejects anywhere**, never
stripped and never normalized, which makes CRLF a rejection; every other control
byte and DEL reject; bytes `0x80–0xFF` are admitted inside a line and compared
byte-exactly, because a POSIX path is a byte string and the plan is not required
to be valid UTF-8; blank lines reject; and the plan, each line and the line
count are bounded. A Windows implementation therefore reads the child's stdout
with **no newline translation**, and a Windows toolchain measured to emit CRLF
extends the grammar by measurement rather than being tolerated at runtime.
Cycle 1's verifier silently removed one trailing CR per line while this contract
rejected every control byte; that contradiction is closed in favour of
rejection, and expected-red control `C12` restores the old splitter.

Three package-independent probe vectors run once per operation from the manager
parent during Stage A, from a manager-owned empty working directory:

```text
swiftc -print-target-info
swiftc -print-target-info -target <native-triple>
clang -print-prog-name=ld -target <native-triple>
```

`swift --version` is deliberately **not** a probe vector. **Measured** by
`TASK-260729-rhjxtx` and unchanged here: it splits one banner across two streams
— `swift-driver version: …` on stderr without a trailing newline, the Apple
version line on stdout — so any consumer merging the streams sees them
concatenated into one line and an anchored rule stops matching. The JSON of
`-print-target-info` is the narrower surface and is the only version authority.

The produced file is `<staged-artifact>` exactly, because `-o` names it. It is
hashed in staging and published as `bin/<command>` or `bin/<command>.exe`
derived solely from the consuming manifest command key.

### 9. The exhaustive pre-compile rejection matrix

The matrix is computed from the validated snapshot and the graph phase, before
the compile phase, and it is total: every surface below has exactly one verdict.

Two properties hold across the whole matrix, and both are stronger than the Rust
analogue.

**No package code runs anywhere in the matrix.** Every row is decided either
from snapshot bytes the manager reads itself, or from a `swiftc -###` job plan
that was **measured** to exit 0 for an unreadable source and for an absent one,
and to write nothing into the source directory. Rust's matrix has to run
`cargo`; Swift's runs a planner that never opens the sources as a program.

**The matrix is host-independent.** It reads bytes and a job plan whose only
host-derived inputs are the resolved triple and the presented SDK path, both
manager-selected. The same snapshot produces the same verdict on every host with
the same declared closure.

**Three verdicts, kept apart on purpose.** Collapsing them would hide which
property is doing the work.

- **reject** — the operation fails with a named diagnostic before the compile
  phase.
- **bound** — the bytes are an input the manager reads deliberately and
  completely: exactly the compiled source set, and exactly the first line of
  `Package.swift`.
- **inert** — the bytes are inside the audit subject, are never opened by the
  manager, never reach the compiler, and are never executed, because no channel
  in the pipeline names them.

That partitions the build-root subtree totally. Inside `Sources` the rule is
total by section 6: `.swift` regular files and directories, everything else
rejected. Outside `Sources` the rule is a closed rejected-name set, the one
bound file, and inert bytes for the remainder.

| Surface | Verdict | Decided by |
|---|---|---|
| any SwiftPM invocation — `swift build`, `swift package`, `swift run`, `swift test`, `dump-package`, `describe`, `resolve`, `show-dependencies` | reject | the driver never emits one; the fixed vectors are the whole command set |
| `Package.swift` first line | bound | section 6; the classifier of section 10 |
| `Package.swift` body — targets, products, dependencies, `unsafeFlags`, `swiftSettings`, `linkerSettings`, `cSettings`, plugins, macro targets, binary targets, system-library targets, prebuild and postbuild commands, conditionals, `#if` in the manifest | reject as an input: never read, never parsed, never compiled, never executed, never compiled-in | section 6: the manager's read stops at the first LF, and the source set excludes the file |
| `Package.resolved` anywhere in the build-root subtree | reject | snapshot bytes: it declares a dependency graph this driver cannot honour, and ignoring it would build something other than what the author declared |
| `Package@swift-*.swift` version-specific manifest anywhere in the subtree | reject | snapshot bytes |
| `.swiftpm` directory, `Plugins` directory, `Snippets` directory anywhere in the subtree | reject | snapshot bytes |
| a package-supplied compiler or linker flag, by any channel | reject | the fixed argument vectors; no flag member exists in either command shape |
| a response file — an `@`-leading argument the compiler expands | reject as unreachable | **measured** that `swiftc` honours `@file`; no vector member begins with `@`, every source token is the absolute path of a snapshot file, and no command shape has a flag member a package could use to add one. **Measured** that a source named `@resp.swift` is compiled as a source path |
| a build configuration selector — debug/release, `-Onone`, an `.xcconfig`, an `.xcodeproj`, a scheme | reject as unreachable | the compile vector fixes `-O`; no configuration member exists in either command shape, and none of those files is compiler-visible |
| a script anywhere in the build-root subtree — `.sh`, `Makefile`, an executable-bit file, a hook | inert outside `Sources`, reject inside it | no channel names it: the process graph of section 3 is fixed, `PATH` is an empty directory, and the plan verification of section 4 rejects any executable it does not already account for. Inside `Sources` it is a non-`.swift` regular file and is rejected outright |
| macro plugin path outside a fingerprinted root | reject | graph-phase plan verification, section 4 — a plugin path pointing outside every root is evidence of a tampered environment rather than an ordinary plan, and the closure condition is checked independently of whether any source could select a macro |
| job executable outside a fingerprinted root, or a plan line the grammar does not cover | reject | graph-phase plan verification, section 4 |
| a verified path whose resolution or identity changes between the graph phase and the compile permit, or an absent plugin path that appears | reject | permit-time re-binding, section 4 |
| an absent plugin path whose state cannot be re-established at the permit — permission, I/O, dangling symlink, anything but `ENOENT` | reject | permit-time re-binding, section 4; absence is `ENOENT` and nothing else |
| an admitted source whose bytes differ at the permit from the bytes Stage B scanned, whether or not the change introduces a selector | reject | permit-time re-binding against the Stage-B digest, section 4 |
| a compile command reached without the permit having run | reject | the session order of section 4 is normative; expected-red control `C16` |
| native object, archive, shared library, framework, C/C++/Objective-C source, header, module map, `.swiftinterface`, `.swiftmodule` anywhere in the build-root subtree, by closed extension list | reject | snapshot bytes. Outside `Sources` these bytes would be inert, and they are rejected anyway: their presence declares an intent the driver cannot honour, exactly as `Package.resolved` does |
| any non-`.swift` regular file under `Sources`, any symlink, device, socket or fifo in the subtree | reject | snapshot bytes |
| a compiled source relative path carrying an ASCII control byte | reject | snapshot bytes; **measured** that it breaks the plan grammar (section 6) |
| an empty compiled source set | reject | snapshot bytes |
| any other file inside the build root and outside `Sources` — `README.md`, `LICENSE`, `.gitignore`, a resources directory, `Tests` | inert | it is in the audit subject and the source identity, the manager never opens it, and no channel passes it to the compiler |
| network access, dependency resolution, registry access, git fetch | reject | no SwiftPM command exists in the pipeline, and the environment carries an empty `PATH` and no network variable |
| package-selected toolchain path, root, channel, mirror, installer, version manager | reject | decision 0007 resolution, and `.swift-version` classified rather than honoured |
| cross-compilation, non-native `-target` | reject | fixed compile vector |
| bridging header, `-import-objc-header`, `-Xcc`, `-Xfrontend`, `-Xllvm`, `-Xlinker`, `-I`, `-L`, `-l` | reject | the fixed vectors contain none of them and the command shapes admit no flag member |
| a compiled source file carrying the byte `0x40` or `0x23` anywhere, including inside a comment or a string literal | reject | `curator-swift-source-admission-v1`, section 4: the Stage-B byte scan, before the graph phase. **Measured**: `@Observable` and `#Predicate` are both rejected with **0** manager-started commands |
| a compiled source file that is not well-formed UTF-8, or carries a NUL | reject | the same rule, checked before the selector scan so that "no `0x40` byte" means "no U+0040 code point". **Measured**: an overlong encoding of U+0040 carries no `0x40` byte and is rejected here, and independently by the compiler |
| any compiler macro or plugin load, including a toolchain-supplied macro reachable from source syntax (`@Observable`), an external macro through a plugin server, and every `-load-pass-plugin=`, `-cas-plugin-path` or `-cas-plugin-option` spelling the plan can carry | reject the selection | section 4: no admitted source set can name a macro, because a macro use requires `0x40` or `0x23` and neither byte survives Stage B. **Measured**: the admitted source set compiles with **0** load remarks while the plan still carries 5 plugin components |
| the plugin search paths `swiftc` injects into its own frontend jobs | inert | section 4: they stay in the plan and are verified for containment; nothing in an admitted source set can name an implementation to load from them. This is stated as inert rather than rejected, because the manager does not edit the jobs — `manager-worker-v2` admits one compile command, not a rewritten job set |
| a plan token no closed table claims — an unknown flag, an unknown joined `-flag=value`, an unexpected positional operand, an `@`-leading response file | reject | section 4: the closed per-job token grammar; totality is over every token |
| an opaque plan value that is path-shaped, embeds `/`, `\` or `#`, fails its charset, or is not the constant the manager chose; a `-Xllvm` or `-Xcc` value outside the measured allow-set | reject | section 4: the opaque-value rule, which stops a non-path token becoming a value carrier |
| `#if` conditional compilation in package **source**, `@_cdecl`, `@_silgen_name`, every other attribute and pound-directive | reject as collateral | `curator-swift-source-admission-v1`, section 4. Cycle 3 admitted these as bounded; the byte rule takes them with the macro surface, and the loss is stated rather than carved out — a carve-out would need the manager to parse Swift |
| `import` of a module the presented SDK exposes | admit, bounded | section 14. **Measured**: importing a macro-bearing module without using a macro loads nothing |

The shared semantic class for a rejection in this matrix is
`build_package_code_execution_forbidden`, except where a row's own class is named
above; the reference document names the per-surface diagnostic beneath it for
each row.

### 10. Stage B metadata dispositions and Swift's acceptance layers

Decision 0007's disposition framework, precedence rule and channel
classification are fixed there and are not reopened. This section completes the
`swift` rows on a qualified host and supplies the acceptance-layer analysis
decision 0007 requires.

Swift has exactly two metadata sources, and they are unusual: one is a comment
and the other is inert.

**`.swift-version` is `compared`.** **Measured**: a `.swift-version` file
carrying `5.9.9-nonexistent` beside the sources changed nothing — the compile
exited 0. The file is honoured by the `swiftly` version manager, which decision
0007 forbids resolving through, and is completely inert against the direct
resolution decision 0007 mandates. That is what admits it as `compared` rather
than `forbidden`: it names a version, not an origin.

**`swift-tools-version` is `classified`, with three host-independent layers plus
a floor and a host gate.** Curator reads the first line of `Package.swift`
itself; it never runs SwiftPM to do so. **The first line is the classifier's
entire input**, so `rejected-absent-header` means "line 1 carries no
specification in any case or spacing form" and `rejected-non-canonical-header`
means "line 1 carries one, but not canonically". A specification below line 1
falls in the first class, not the second, because Curator never looked. The
classifier is therefore Curator-owned, and its alignment with upstream is
measured rather than assumed, using `swift package tools-version` as the
isolated representability oracle and `swift build` as the corroborating command.

Swift is in one respect better placed than Go, for the same structural reason
Rust is: the isolated command **cannot** be applying the host gate.
**Measured**, `swift package tools-version` reports `99.0.0` with exit **0** on
a 6.3.2 host, while `swift build` on the same package exits 1 with
`error: 'probe-pkg': package 'probe-pkg' is using Swift tools version 99.0.0 but
the installed version is 6.3.2`.

**Measured**, one value per fixture, exit code and first diagnostic line:

| Header | isolated | corroborating | Layer |
|---|---|---|---|
| `// swift-tools-version:6.0` | 0, `6.0.0` | 0 | accepted |
| `// swift-tools-version:4.0` | 0, `4.0.0` | 0 | accepted — the lowest supported |
| `// swift-tools-version:3.1` | 0, `3.1.0` | 1, `… is using Swift tools version 3.1.0 which is no longer supported…` | floor |
| `// swift-tools-version:1.0` | 0, `1.0.0` | 1, same shape | floor |
| `// swift-tools-version:99.0` | 0, `99.0.0` | 1, `… but the installed version is 6.3.2` | host gate |
| `// swift-tools-version:6` | 1, `… '6' is misspelt or otherwise invalid…` | 1, same with a package infix | grammar |
| `// swift-tools-version:6.0.0.0` | 1, same shape | 1, same shape | grammar |
| `// swift-tools-version:notaversion` | 1, same shape | 1, same shape | grammar |
| `// swift-tools-version:` | 1, `… specification is possibly missing a version specifier…` | 1, same shape | missing specifier |
| no header | 1, `package 'package.swift' is using Swift tools version 3.1.0 which is no longer supported…` | 1, same shape | absent header |
| BOM before the header | 1, same as no header | 1, same as no header | absent header |

The floor is **measured**, not assumed: 3.1 is refused and 4.0 is accepted by
the corroborating command, so the floor is exactly 4.0.0 on this toolchain.

The layers are pairwise independent in the sense decision 0007 established: the
document layer refuses a BOM that the grammar would parse; the grammar refuses
`6` that the floor comparison would happily order; the floor refuses `3.1` that
the grammar accepts; and the host gate refuses `99.0` that all three admit. The
host gate is **excluded from the layer measurement**, for the reason decision
0007 gives: a gate that depends on the runner cannot be part of a value's
grammar.

**Curator is deliberately narrower than upstream, and the narrowing is declared
rather than hidden.** Upstream accepts, and silently reinterprets, a family of
header forms:

| Header | upstream | Curator | why Curator refuses it |
|---|---|---|---|
| `//swift-tools-version:6.0` | `6.0.0` | non-canonical | not the canonical prefix |
| `// SWIFT-TOOLS-VERSION:6.0` | `6.0.0` | non-canonical | case-insensitive matching of a security-relevant token |
| `//   swift-tools-version:  6.0` | `6.0.0` | non-canonical | free whitespace in a token that gates a version comparison |
| `// swift-tools-version:06.0` | `6.0.0` | non-canonical | silent leading-zero normalization |
| `// swift-tools-version:6.0-beta` | `6.0.0` | non-canonical | **silently discards the prerelease component** |
| `// swift-tools-version:6.0+build` | `6.0.0` | non-canonical | silently discards build metadata |
| `import Foundation` then the header on line 2 | `6.0.0` | absent header | the specification sits below arbitrary manifest code, which Curator does not read |
| the header only inside a multi-line string literal | `9.9.0` | absent header | **measured**: upstream's scan reaches bytes inside a string literal |

The first six are cases where the bytes an author wrote and the version upstream
compares are different. Curator's rule for them is the canonical first line
`// swift-tools-version:` with at most one space after the colon and a two- or
three-component decimal version with no leading zeros and no suffix; each is
`rejected-non-canonical-header`, never a grammar rejection, because calling it a
grammar error would claim upstream refuses it too.

The last two are a different shape and are the reason the line-1 rule is
normative rather than stylistic. Upstream scans the whole file, and the
**measured** consequence is that `swift package tools-version` reports `9.9.0`
with exit 0 for a manifest whose only specification is written inside a
multi-line string literal on line 3. Under a whole-file scan the version a
manager compares would be selectable from anywhere in a program the manager
otherwise refuses to read. Curator reads line 1 and stops, so both classify as
`rejected-absent-header` — a truthful statement of what was examined.

Those eight forms are the classifier's **security partition** `F`. The probe
asserts P1 (no widening: Curator accepts nothing upstream refuses) over all
cases, and P2 (no narrowing) over cases outside `F`; **measured**, both hold,
with `F` non-empty and enumerated. This is the case decision 0007 anticipated
when it allowed a non-empty `F` rather than collapsing P1 and P2 to equality.

Two nearby cases are deliberately **not** in `F`, because Curator and upstream
agree on them, and they bound the narrowing rather than widening it.
**Measured**: a canonical line 1 followed by a second specification on line 2
yields `6.0.0` from upstream — line 1 decides for both, and the later value is
never reached. **Measured**: a specification inside a single-line string literal
(`let s = "// swift-tools-version:9.9"`) is found by neither, because the line
does not begin with the comment marker.

The recognised outcome set is closed and whole-line exact. Every predicted line
is built before the command runs from the value under test plus constants the
probe fixes from the resolved toolchain — the full compiler version `6.3.2`, its
major-minor form `6.3`, and the package directory name upstream renders as an
infix in every `swift build` diagnostic. Two expected lines of different classes
matching inside one output is `unknown`, not first-wins. A lead with an
unconstrained tail, and a substring found anywhere in the output, are families
rather than outcomes and MUST NOT be recognised.

Closure is measured, not asserted, in both laundering directions: 4 real
unrelated command failures, 20 value-bearing outcomes cross-fed over 338 pairs,
and 27 constructed cases in which a measured diagnostic is extended the way a
later release would extend it — a tail appended, a wrapper in front, the line
embedded in a longer one. All 32 emitted rows yield no verdict. The constructed
ones are disclosed as constructed, because an outcome upstream has not yet
written cannot be measured on any host. Twenty outcomes are **excluded** from
the cross-feed and the exclusion is printed with its reason: an exit-0
acceptance, a missing-specifier diagnostic and an absent-header diagnostic name
no value under test, so feeding them under another value would test the
classifier against text that was never about a value.

The confirmed `swift` disposition table is:

| Source | Field | Disposition |
|---|---|---|
| `Package.swift` | first-line `swift-tools-version` | `classified` — three layers plus the floor and the host relation, per the reference document |
| `Package.swift` | every byte after the first LF | not a metadata source and not read at all: rejected as an input by section 9 |
| `.swift-version` | the bare version string | `compared`, by decision 0007's channel table |
| `Package@swift-*.swift` | any field | not reachable: the file is rejected by section 9 |

Both files are evaluated in Unicode-scalar lexical order of relative source
path, so `.swift-version` precedes `Package.swift`, and a snapshot carrying a
forbidden surface is deterministically a package-influence rejection before any
comparison runs.

### 11. The `swift` registry entry

| Field | Value |
|---|---|
| `toolchain_id` | `swift` |
| `primary_relpath` | `usr/bin/swiftc`; `usr/bin/swiftc.exe` on Windows |
| `probe` | `swiftc -print-target-info`, `swiftc -print-target-info -target <native-triple>`, `clang -print-prog-name=ld -target <native-triple>`, from a manager-owned empty working directory under the operation-private environment |
| `normalization` | the `compilerVersion` string of `-print-target-info` **stdout** JSON, matched **as a whole value** against the single byte-exact grammar of reference section 1.2; `swiftCompilerTag` is recorded and is not the version |
| `prerelease markers` | none are admitted by the grammar above; a banner that does not match it leaves the version **undetermined** and fails Stage A rather than being guessed |
| `base_installation_prefixes` | `macos`: exactly `["/usr/lib/swift"]`; every other platform: **empty** until measured (section 5) |
| `fingerprint_algorithm` | `curator-swift-toolchain-v1`, section 3 |
| `baseline` | `{"kind":"at_least","min":"6.3.2"}` |
| `compatibility` | families `{(6, 3)}`; family granularity `(major, minor)` |
| `platforms` | `(macos, arm64)` only |
| `companions` | none |
| `link_support_roles` | `macos`: exactly `[platform-sdk]`, data-only, presented per section 4 |
| `metadata_sources` | `Package.swift` first-line `swift-tools-version`; `.swift-version` |

`swift --version` is deliberately not the version probe, for the split-stream
reason in section 8. `swiftc --version` carries the same defect: **measured**,
its stdout holds the Apple banner while its stderr holds
`swift-driver version: 1.148.6 …`, so a merged read concatenates them.

**All three probes are run.** P2 is not skipped because its result looks
predictable from P1: the admission of section 5 is defined on the triple the
compile passes. **Measured on this host**, P1 and P2 return byte-identical JSON
after canonical re-encoding — and P2 is run and bound anyway, because that
equality is a property of a host, not of the contract.

**One normalization grammar, stated once.** Cycle 1 left three descriptions of
the compiler banner in circulation — this section admitted an empty
parenthesised suffix, the reference required a non-empty one, and the
implementation examined only the prefix and the numeric token before the first
space, so `Apple Swift version 6.3.2 x` passed the implementation and failed
both written rules. There is now exactly one grammar, in reference section 1.2,
and this table points at it rather than restating it in a second notation. Its
load-bearing properties:

- it consumes the **whole value** — no prefix match, no unexamined suffix, and
  the fixture asserts the value reconstructs byte-for-byte from the parsed
  components;
- every byte must lie in `%x20-7E`, which rejects CR, LF, NUL, every other
  control byte, DEL and every non-ASCII byte in one rule, so the value is
  ASCII-only and is its own canonical form;
- the whole value and the suffix are length-bounded, and the length is checked
  before any scan;
- the suffix is **non-empty** and admits no parentheses, so an admitted value
  carries exactly one `(` and one `)` and needs no balanced-paren parsing;
- it is **total**: every input yields a normalized version or exactly one of
  eleven typed rejection codes, and the conformance vectors assert on the code.

**Measured**: over the 32 banner vectors, the retired prefix-only parser admits
**17** of the 28 negatives. Expected-red control `C10` restores it and reports
that set, so the narrowing is evidenced rather than asserted.

The open-source toolchain banner (`Swift version 6.1 (swift-6.1-RELEASE)`) is
**not** admitted, and that is deliberate: no host in this task carried one, and
an unmeasured rule is not a rule. Admitting it — or a prerelease marker, or a
parenthesised suffix — is a qualification obligation with its own measurement,
not a one-line grammar change.

The baseline and the compatibility set are both `6.3` because 6.3.2 is the only
release this contract was measured against. Lowering the baseline requires
measuring the older release; adding a family requires testing it against the
driver's conformance vectors. Neither may be derived from version ordering, and
no package byte can reach either.

`platforms` holds one pair, and that is the honest consequence of the evidence
rather than a scoping choice. On a host whose pair is not in `platforms`, Stage
A fails `build_toolchain_platform_unsupported` from the pre-resolution half of
the check, on registry data alone.

### 12. Artifact, cache, receipt, marker and claim identity

The artifact class is `native-executable-v1` and nothing else. **Measured** on
this host that the pipeline produces exactly one `Mach-O 64-bit executable
arm64` whose every dynamic dependency is a base-installation library
(`/usr/lib/libSystem.B.dylib`, `/usr/lib/libobjc.A.dylib`, the
`/usr/lib/swift/*` runtime dylibs, and
`/System/Library/Frameworks/Foundation.framework/…`), that it is `adhoc,
linker-signed`, and that it runs. That signature is applied by `ld` as part of
linking, which is exactly the case decision 0008 section 3 names as compiler
output rather than a manager signing step: it is produced by the driver's fixed
argument vector, selects no signing identity, credential or notarization, and
reaches no network. The driver performs no manager post-build signing, and a
platform policy requiring a locally signed binary must wait for the separately
reviewed signer profile.

**Measured** on reproducibility, stated because it is easy to over-claim: two
compiles of the same sources to the **same** output path produce byte-identical
files, and changing only the output path changes the bytes, because the path
reaches the Mach-O `LC_UUID`. Identity stays input-keyed as decision 0008
section 3 requires; this is not a reproducible-build claim, and a manager whose
staging path varied per operation would produce different bytes for the same
inputs.

Every other file the compiler could leave — object files, `.swiftmodule`,
`.swiftdoc`, `.swiftsourceinfo`, `.dSYM` bundles, dependency files — stays in
operation-private staging, is discarded with it, and never enters cache
identity, the receipt, the marker, the shim relationship, or publication.
**Measured** that the compile phase writes nothing into the source directory.
The manager MUST NOT execute the artifact for validation, version discovery,
smoke testing, post-processing, receipt generation, rollback or any other
reason.

The canonical build input binds, in addition to the members decision 0008
section 8 requires of every new driver, the complete
`curator-swift-toolchain-v1` identity of section 3 — including both root digests
and the closure digest — the unversioned native triple, the ordered relative
paths of the compiled source set, the consuming **command key**, the derived
module name, and this closed policy object.

The command key is bound alongside the module name rather than instead of it, and
the reason is stated so it is not read as redundancy: the module name is what the
compiler was given and therefore belongs in the input that identifies the build,
while the key is what the protocol keeps distinct. Binding both means two
commands cannot share a cache identity even under a hypothetical module-name
collision, so identity does not depend on the derivation of section 6 being
injective.

```json
{
  "package_manager": "none",
  "dependency_mode": "source-inlined",
  "network": "none",
  "manifest_execution": false,
  "plugins": false,
  "macros": false,
  "binary_targets": false,
  "system_library_targets": false,
  "target_mode": "native",
  "optimization": "release",
  "linker": "toolchain-ld",
  "link_mode": "internal",
  "native_inputs": false,
  "sdk_presentation": "manager-owned-symlink-root",
  "plugin_closure_check": "job-plan-verified-v2",
  "source_admission": "curator-swift-source-admission-v1",
  "job_execution": "driver-launched-v1",
  "compiler_directives": "reject-nonstandard-native-inputs-v1",
  "incremental": false,
  "execution_policy": "manager-worker-v2"
}
```

`execution_policy` is the `const` `manager-worker-v2`, so a Swift entry can never
alias a Go entry, and `driver` differs besides. `network: "none"` denotes the
absence of any network-capable command in the pipeline together with the empty
`PATH`; it is not a claim of kernel-enforced network denial, which remains the
deferred `total-network-denial` guarantee.

Receipt schema 3 carries the local mode and schema 4 the external mode, each a
strict `oneOf` discriminated by the `driver` `const`, each carrying this policy
object, this toolchain identity and this native target. Marker schema 4 records
the driver, `receipt_schema_version` and `execution_policy` per build entry, and
a reader rejects a `swift-v1` entry claiming `manager-worker-v1` rather than
inferring the policy from the driver name. Conformance claim schema 4 asserts
`swift-v1` and `swift-repository-v1` with `execution_policy`
`manager-worker-v2` bound by the assertion's own `driver` `const`, and only if
this contract is accepted and `TASK-260728-251p01` moves both identifiers in the
same change that mints the schema.

The effective toolchain requirement and the `compatibility` set stay gates
rather than build inputs, exactly as decision 0007 fixes them.

### 13. Platform matrix

| Platform | Status |
|---|---|
| macOS arm64 | the complete pipeline is measured on one host; it enters a claim only through `TASK-260728-2bu2q6` with immutable native evidence for that exact tuple |
| macOS amd64 | qualification obligation; the toolchain ships an `x86_64-apple-macosx` standard library, and the acceptance test is a probe run on an x86_64 macOS host |
| Windows | implementation contract only, stated below; **no** platform claim, because no reachable Windows host had a Swift toolchain |
| Linux | excluded until `TASK-260728-1y8u4m`, then qualified by the same acceptance test |

**Windows implementation contract.** The obligation is to reproduce section 3's
property — a process closure with no `PATH`-resolved executable — and section
4's — a verified plugin closure. Neither is claimed here. The contract an
implementation MUST satisfy before Windows enters `platforms`:

1. The required closure is whatever the structural rule of section 3 names on
   that host: every executable the verified job plan carries, plus the linker
   `clang -print-prog-name` resolves, each proven to lie inside the fingerprinted
   toolchain root. The macOS instance is four **spellings** resolving to three
   distinct files. The Windows instance is **not asserted here**: the expected
   shape is `usr\bin\swiftc.exe`, `swift-frontend.exe`, `clang.exe` and the
   resolved linker, but the plan on that host is unmeasured, so an
   implementation MUST take the member set from the plan it verifies and record
   it in `curator-swift-process-closure-v1` (section 3), rather than reading a
   count out of this paragraph. `swift.exe` is not a member, for the reason
   section 3 gives: the driver never invokes it. **The unmeasured count blocks
   nothing else**: the linker relpath, additional plan-derived members, multiple
   SDK roots, the `link_support_roles` value and the plan's physical-line
   grammar are all serializable today by rules that do not depend on it.
2. The platform SDK role is whatever the Windows toolchain requires to link
   against the base installation, bound as one or more data-only `platform-sdk`
   roots through the two declaration channels of section 3, and presented
   through a manager-owned directory as in section 4 so that any derived plugin
   tree is manager-controlled. **The serialization of that is fixed now, not at
   implementation time**: role token `platform-sdk[<ordinal>]` with the ordinal
   assigned by declaration order and the bracket present even for a single root;
   one presentation chain per ordinal under `<staging>/sdk/<ordinal>/`; one
   `roots` entry per ordinal, hashed in ordinal order; `-sdk` takes ordinal 0.
   Any additional root is reachable only through a **closed, manager-owned,
   per-platform argument template** that no package byte, descriptor byte or
   environment variable can add to, reorder or select from. That template is
   **unmeasured** and minting it is part of this obligation; nothing else waits
   on it.
3. The poisoned-`PATH` acceptance test is run with a Windows shim set covering
   at least `link.exe`, `lld-link.exe`, `cl.exe`, `clang.exe`, `ld.exe`,
   `swift-plugin-server.exe`, `where.exe` and `vswhere.exe`, and it MUST produce
   zero resolutions for both the graph and the compile phase, **with a control
   run that produces resolutions when a linker is named rather than defaulted**.
   Without a firing control the zero is unearned and MUST NOT be accepted.
4. The graph-phase plan verification of section 4 MUST pass with **every**
   token of the emitted plan claimed by a closed table, every job executable and
   every plugin path inside a fingerprinted root or absent. The per-kind nullary
   flag set and the `-Xllvm` / `-Xcc` value allow-sets are per-platform and MUST
   be **measured on that host** and written into the reference document first; a
   Windows plan carrying an unmeasured token fails closed until it is.
5. The Stage-B source admission of section 4 is **platform-independent** and
   MUST hold unchanged: it reads bytes, not a host. What a Windows
   implementation MUST measure is the other half — that the plugin search paths
   the Windows driver injects are **inert** for an admitted source set, reported
   as zero load remarks under the host's own remark flag, and that the session
   is still exactly two manager-started commands. An implementation MUST NOT
   answer an awkward Windows plan by executing the plan's jobs itself; that is
   the retired design and expected-red control `C15` exists to reject it.
6. The produced `.exe` MUST depend only on base-installation libraries of the
   declared Windows baseline.

An implementation MUST NOT ship a Windows path that resolves `link.exe`,
`cl.exe`, `vswhere.exe` or a Visual Studio activation script from `PATH`, the
registry, or an environment variable, MUST NOT answer the gap with a
host-resolved tool or a downgraded control, and MUST NOT record a Windows
platform claim from a cross-compiled or emulated run. Until that evidence
exists, both drivers fail `build_toolchain_platform_unsupported` on Windows.

**Linux qualification rules.** Linux enters `platforms` only when, on the
qualifying host: `swiftc -print-target-info` reports a triple whose
`runtimeLibraryPaths` entries inside the fingerprinted root all exist;
the poisoned-`PATH` run is clean for both phases with a firing control; the
graph-phase plan verification passes under the closed token grammar with the
platform's flag tables measured on that host; the injected plugin channel is
measured **inert** for an admitted source set and the session is exactly two
manager-started commands; the produced ELF executable's dynamic
dependencies are all base-installation libraries of the declared distribution
baseline; and the `platform-sdk` role is either absent or resolved from a
declaration channel. Two Linux-specific questions are named rather than
answered, because this host cannot answer them: the linking vector was
**measured** to require `swift-autolink-extract`, which is a **fifth** executable
beyond the macOS four and must be shown to resolve inside the fingerprinted root
and to appear in the verified plan; and the open-source
toolchain banner is not admitted by the section 11 normalization rule, so a
Linux qualification must either measure that form and extend the rule or be
rejected.

### 14. Residual exposures, stated rather than closed

Decision 0008's security section requires each driver contract to state its own
compiler-input exposure honestly and to refrain from relying on containment this
protocol does not provide.

**Macro expansion is no longer an exposure, because no admitted source can
select one.** Cycle 2 listed source-selected toolchain macro execution here as an
admitted exposure. Section 4 now rejects the selection at Stage B, from the
source bytes, before any command starts, and the compiler itself is the evidence
that the two rejected bytes are the whole selection surface. This entry is kept,
inverted, so the change is recorded rather than quietly dropped.

**The plugin search paths are still in the plan.** This is the honest form of the
statement above. `swiftc` injects them into its own frontend jobs and, under a
one-compile-command policy, the manager cannot remove them. What is measured is
that they are **inert** for an admitted source set — 5 components in the plan, 0
load remarks — and that every one of them is verified to resolve inside a
fingerprinted root or to be absent. The residual is a toolchain that begins
loading a plugin without a source-side selector; nothing in the pipeline would
stop that, and no control here claims otherwise. It is bounded by the closure
check, not eliminated by it.

**The compile phase re-plans.** The manager verifies the plan `graph_argv`
printed and then runs `compile_argv`, which derives its own. Both come from one
builder over one source set in one environment and differ by one inserted token,
and the verified paths are re-bound and re-checked at the permit — but the
processes that run are not literally the ones inspected. Cycle 3 had the stronger
property and paid for it with a session shape `manager-worker-v2` does not admit;
this contract keeps the accepted policy and states the weaker property. Closing
the gap properly needs an execution-policy identity that admits a manager-driven
job set, which is a decision 0008 change and not this contract's to make.

**The permit narrows the mutation window; it does not remove it.** The re-binding
runs immediately before `compile_argv`, so a write that lands between the permit
and the compile child's own `open` is outside it. The honest statement is that
the permit converts "the graph phase verified this at some earlier time" into
"nothing observable had changed when the command was started", and that the last
interval is bounded by the ownership requirement on the declaration channels
rather than by a check. Closing it needs a compiler that accepts
content-addressed inputs, which this toolchain does not offer.

**Compile-time filesystem reads are bounded but not proven absent.** The Swift
language admitted by this driver has no counterpart to Rust's `include_str!`:
there is no core-language directive that reads an arbitrary file into the
compilation. The surfaces checked and found not to be reachable under this
contract are `-import-objc-header`, `-Xcc -include`, module maps, bridging
headers and `.swiftinterface` inputs — all of them flags or file kinds the fixed
vectors and the rejection matrix exclude. This is a **bounded statement about
the surfaces enumerated**, not a proof that none exists. With macro expansion
removed, the compile-time read surface Swift contributes is the compiler front
end itself; `STORY-260728-327soo` still receives the Rust compile-time read
surface, since none of the six deferred hardened guarantees covers compile-time
filesystem reads.

**Foreign symbol declarations are no longer reachable.** Cycle 3 admitted
`@_silgen_name` and `@_cdecl` as bounded, on the reasoning that a package cannot
supply a library to link. Both spellings begin with `0x40`, so Stage B now
rejects them outright and the reasoning is no longer load-bearing. What remains
admitted is `import` of a module the presented SDK exposes: the package cannot
supply a library to link and cannot add a search path — native files in the tree
are rejected, no flag member exists, and there is no admitted path that adds one
— so the artifact depends only on base-installation libraries, which decision
0008 section 3 already requires. This is inside the artifact class rather than an
escape from it. It is not a claim that the produced program is safe; the artifact
remains untrusted package output that the manager never executes.

**Ordinary compiler-input exposure remains.** Denial of service through resource
consumption, and compiler vulnerabilities reached by adversarial source, are
bounded by the parent-enforced deadline, output and artifact limits and by
whichever native-control inventory entries the host provides, and by nothing
stronger. The six deferred hardened guarantees are not claimed, named as
controls, or implied.

### 15. Downstream obligations

- `TASK-260728-2jaw7h` lands the shared `toolchain` object; this decision adds
  no wire field and MUST NOT be read as adding one.
- `TASK-260728-251p01` integrates `swift-v1` and `swift-repository-v1` into
  manifest schema 8, descriptor schema 2, receipt schemas 3 and 4, marker schema
  4, claim schema 4 and the generated corpus, moving both identifiers from the
  reserved namespace to the admitted wire driver set in the same change that
  mints the schema admitting them, and extends decision 0008's boundary gate
  member-set table accordingly.
- `TASK-260728-21x3yc` and `TASK-260728-2lnhci` implement the pair in Curator,
  `TASK-260728-3j60e3` and `TASK-260728-2ztr3c` in csk, against the reference
  document rather than against this decision's prose.
- `TASK-260728-2bu2q6` qualifies the candidate and emits only evidence-backed
  driver and platform claims; `(macos, arm64)` is the only pair this contract
  supplies evidence for.
- `TASK-260728-3lqm4z` and `TASK-260728-1xviwb` verify cross-manager interop;
  `TASK-260728-1y8u4m` runs the Linux qualification of section 13.
- `TASK-260728-1egim2` documents authoring and operations, including the
  single-module, dependency-free consequence of section 2, which is the fact
  authors will meet first, and the Stage-B byte rule of section 4, which is the
  second — no `@` and no `#` anywhere in a compiled source, so `@Observable`,
  `#Predicate`, `@main`, `#if`, raw string literals and every other attribute or
  pound-directive are rejected before the build starts, with
  `swift_source_macro_selector_forbidden` naming the file and byte offset.
- `STORY-260728-327soo` no longer receives a Swift macro-expansion
  filesystem-read surface: section 4 rejects the selection at Stage B, and
  section 14 records the inversion together with the residual it does not close.
  It still receives the Rust compile-time read surface.

### 16. Enforcement

The boundary gate of decision 0008 section 11 needs no new mechanism for this
contract: `swift-v1` and `swift-repository-v1` are already two of the six
reserved identifiers it holds out of every surface file. Five additions belong
to `TASK-260728-251p01` at admission time and are named here so the gate is
extended rather than weakened:

1. the two identifiers move from the reserved namespace to the admitted set in
   the same change that mints receipt schemas 3 and 4, and the gate's driver
   `const` sets move with them;
2. the policy object of section 12 joins the exact member-set table, closed and
   `additionalProperties: false`, with `execution_policy` pinned to the
   `manager-worker-v2` `const`; and
3. the `curator-swift-toolchain-v1` identity joins the table as an object schema
   with its closed member set, its role-token set closed by `const` and by the
   per-platform cardinality table of reference section 2.4 — including the
   bracketed `platform-sdk[<ordinal>]` form for `one-or-more` platforms — and no
   member naming a filesystem path;
4. the canonical build input's `command_key` and `module_name` members join the
   table with the `curator-swift-module-v1` relationship between them fixed by
   conformance vectors, so a manager cannot substitute another derivation and
   keep the same cache identity; and
5. `curator-swift-process-closure-v1` joins the receipt schemas as an object with
   its two ordered projections, its members serialized by
   `curator-swift-relpath-v1`, and a validator that rejects an absolute path, a
   native separator, a volume prefix or a `.`/`..` component in any relpath.

## Stable failure classes

These are architecture-level semantic classes and MUST remain distinguishable
from each other, from a cache hit, from an audit success, from source
unavailability and from a generic fallback. The reference document maps each to
its exact trigger and stage.

- `build_package_code_execution_forbidden`, the shared class of section 9,
  including the Stage-B source-admission rejections
  `swift_source_macro_selector_forbidden`, `swift_source_encoding_forbidden`
  and `swift_source_unreadable`, which are raised **before the graph phase**
  and therefore before any command starts;
- `build_execution_control_unavailable`, for a job plan the fail-closed grammar
  refuses, for a plan whose executable, plugin, search or output path leaves the
  root it must stay inside, for a binding whose resolution, identity or admitted
  source bytes changed between the graph phase and the compile permit, and for a
  staging precondition the manager cannot meet. Two Swift details sit beneath it
  and MUST stay distinguishable: `swift_plan_token_unclaimed` for a token the
  closed grammar does not claim, and `swift_permit_binding_changed` for every
  permit-time re-binding finding;
- `build_descriptor_driver_unsupported` and
  `build_descriptor_schema_unsupported`, unchanged from decision 0008;
- `build_artifact_class_unsupported`, for a platform that cannot produce a
  single self-contained executable; and
- the twelve `build_toolchain_*` codes of decision 0007, unchanged, with
  `build_toolchain_platform_unsupported` carrying both the unsupported host pair
  and the absent-standard-library case of section 5, and
  `build_toolchain_metadata_mismatch` carrying the `swift-tools-version`
  classifier of section 10.

## Rejected alternatives

- **Keep cycle 3's design: execute every verified plan job from the manager
  with the plugin channel deleted.** Rejected, and it is the mechanism that works
  best. Accepted decision 0008 section 7 closes a `manager-worker-v2` session to
  at most one graph command and exactly one compile command, started by the
  driver's own trusted launcher, and says in terms that a driver which cannot map
  onto that shape must not be admitted and that widening the shape requires
  another execution-policy identity, a new claim schema version and its own
  review. **Measured**: the design starts 4 manager commands for the default
  source set and starts `swift-frontend` and `clang` directly, so it changes both
  the cardinality and the parentage the label names. Keeping the mechanism would
  have meant either mislabelling the session or reopening an accepted decision
  from inside a driver contract. Expected-red control `C15` reports the count.
- **Mint a third execution-policy identity that admits a manager-driven job
  set.** Rejected **here**, not on the merits. It is the change that would let the
  stronger property survive, and it is a decision 0008 change: a new policy
  identity, a new `capability-evidence` version, a new claim schema and its own
  review. A driver contract that mints one unilaterally would do exactly what
  decision 0008 section 7 forbids. Section 14 records the property that is lost
  so the option stays visible to whoever reopens it.
- **Detect macro use by asking the compiler instead of scanning bytes.**
  Rejected on a **measurement**: `swift-frontend -scan-dependencies` reports
  `macroDependencies` as the module's dependency *closure*, not its use, so a
  macro-free file still lists `SwiftMacros` while loading nothing. A detector
  with a false-positive rate that high is not a boundary. The deeper objection is
  that any syntax-aware detector is a second implementation of a grammar the
  compiler owns, maintained by the manager, and wrong in a direction nobody
  notices until it is exploited.
- **Reject only `@` at the start of a token, or only outside comments and string
  literals.** Rejected: both need a Swift lexer in the manager to know where a
  token starts and where a literal ends, and Swift's raw string delimiters make
  "inside a literal" itself a `#`-counting problem. The byte rule needs no lexer,
  is total over every possible file, and its cost is a smaller admitted language
  rather than a subtler boundary. The rejected constructs are inventoried in
  section 4 rather than discovered by authors one at a time.
- **Rely on the compiler rejecting a macro it cannot load.** Rejected: that is
  the cycle-3 state the cycle-4 review named. The rejection happens inside a
  compile child that already has a permit, which decision 0008 section 7 calls a
  runtime allowance and forbids as an answer to a package-selected surface.
- **Drive `swift build` and reject dangerous manifests after reading them.**
  Rejected on measurement: reading what the manifest declares *is* running it.
  `dump-package` executed a manifest body under both sandbox settings, so there
  is no order of operations in which the matrix is computed before package code
  runs. Decision 0008 section 7 disqualifies exactly this shape.
- **Rely on SwiftPM's manifest sandbox, which did block the escape write.**
  Rejected: `--disable-sandbox` removed it in the same probe, it exists only on
  Apple platforms, and decision 0006 forbids resting a portable guarantee on
  containment the protocol does not itself provide. A control an argument can
  switch off is not a boundary.
- **Admit a manifest allowlist — a "declarative subset" of `Package.swift`
  recognised by parsing rather than running.** Rejected: recognising a subset of
  a Turing-complete language from bytes is exactly the unsound-in-both-directions
  check decision 0007 retired on the Go side, and a manifest that parsed as
  declarative would still be compiled and run by every other tool the author
  uses, so the two views would diverge silently.
- **Mint a curator-owned declarative metadata file for Swift build roots
  instead of binding `Package.swift`.** Rejected for this version: decision 0008
  section 4 asks for a *project* metadata file, and a curator-only file would be
  invisible to every other Swift tool, so an author would maintain two
  descriptions of one program with no mechanism keeping them consistent.
  Binding the one line of `Package.swift` that is already a comment keeps the
  build root a normal Swift package for humans while giving Curator a metadata
  surface that is not a program. The cost — that the manifest's declared targets
  and dependencies are invisible to Curator — is answered by section 9 rejecting
  the surfaces that would make the divergence matter, and by an unresolved
  import failing to compile rather than silently building something else.
- **Let the compiled source set be chosen rather than enumerated — the file
  containing `main`, or the directory matching the command name.** Rejected:
  that is discovery, it hands selection to package layout, and it makes the set
  of audited bytes differ from the set of compiled bytes. The total enumeration
  of `Sources` selects nothing, which is why it satisfies decision 0008 section
  4's non-discovering requirement.
- **Silently skip non-`.swift` files under `Sources` instead of rejecting the
  build root.** Rejected: skipping would mean the audit subject contains bytes
  the operator has no reason to think were examined, and it would make a
  `.c` file beside the sources look admitted. Totality is the property that
  makes the enumeration sound.
- **Ignore `Package.resolved` rather than rejecting it.** Rejected: its presence
  means the author declared dependencies, and building without them would either
  fail confusingly or — worse — succeed against vendored copies the author did
  not intend. Rejecting names the mismatch at the boundary.
- **Pass the declared SDK path to `-sdk` and fingerprint the platform tree that
  the plugin paths derive into.** Rejected: it would add a third root of 33,319
  files whose only purpose is to legitimise a `swift-plugin-server` process, and
  the process would still be started by package source choosing a macro. The
  manager presentation removes the process, and the section 4 Stage-B rule
  removes the selection, so the third root would legitimise a surface no admitted
  source can reach.
- **Trust the measured SDK-relative derivation rule and skip the plan
  verification.** Rejected: a derivation rule is an implementation detail of the
  driver and can change in a patch release, and the failure mode is silent
  re-admission of an unfingerprinted executable. The verification reads the plan
  the compile phase will execute, so it holds whatever the rule becomes.
- **Reject macro syntax in package source outright, so no plugin is ever
  loaded.** Rejected: it is unsound in both directions — a macro use is a token,
  not a byte pattern — and a byte scan would refuse ordinary source while still
  missing a spelling it had not anticipated. The replacement reaches the same
  boundary from the other side: deleting the plugin channel from the executed
  jobs makes every macro unloadable without the manager reading package source
  for syntax at all.
- **Keep admitting macros whose implementation is inside a fingerprinted
  root.** Rejected: this was the cycle-2 position and it contradicts accepted
  decision 0008 section 7, which names compiler macros as a package-selected
  code-execution surface that MUST be rejected before the compile phase and MUST
  NOT be answered with a runtime allowance. Fingerprinting bounds where the code
  came from; it does not stop package bytes deciding that it runs. Amending
  decision 0008 to allow fingerprinted toolchain macros would be a legitimate
  alternative, but it is that decision's own reviewed change to make, not
  something this contract may do implicitly.
- **Detect the macro load instead of removing the channel — run a dependency
  scan or a parse-only pass and reject when a macro appears.** Rejected on
  measurement: `swift-frontend -scan-dependencies` reports `macroDependencies`
  for the *closure*, not for use. **Measured**, a source file with no macro at
  all still reports `SwiftMacros` from the standard library while its compile
  loads nothing, so the scan over-approximates in a way that would reject every
  build, and a narrower reading would admit a package that really does use a
  stdlib macro. A parse-only pass has the opposite problem: distinguishing a
  macro attribute from an ordinary one needs name resolution. Removing the
  channel needs neither.
- **Use `swift package tools-version` as the manager's own metadata reader.**
  Rejected: it is a SwiftPM invocation, and section 2 admits none. It is used in
  the probe as the upstream oracle the Curator classifier is measured against,
  which is a different role and never runs in a manager pipeline.
- **Accept upstream's own header recognition, so Curator and SwiftPM agree
  exactly.** Rejected: upstream was **measured** to accept a header below
  arbitrary manifest code, to match the keyword case-insensitively, and to
  discard prerelease and build components silently. Agreeing exactly would mean
  comparing a version the author did not write. The narrowing is declared as the
  security partition `F` and is checked, rather than being an accident.
- **Scan the whole manifest for a specification so the diagnostic can say "your
  header is on line 2".** Rejected, and this is the sharpest version of the
  previous entry. A scan makes the manager's verdict a function of manifest body
  bytes, which contradicts the one sentence the whole metadata story rests on —
  that the body is not an input. It is not a theoretical contradiction:
  **measured**, upstream's scan reports `9.9.0` for a specification written
  inside a multi-line string literal, so under a scan an author could set the
  compared version from inside a string constant. The better diagnostic is not
  worth making the security boundary depend on the bytes it exists to exclude.
  Curator reads line 1 and stops, and the refusal of a below-line-1
  specification is declared as a member of `F`.
- **Derive the module name by replacing every character outside the Swift module
  alphabet with an underscore.** Rejected: it is not injective. `my-tool`,
  `my.tool` and `my_tool` are three distinct protocol command keys and would
  become one module identity, and a leading digit or an overlength key has no
  answer at all. Expected-red control `C9` restores the rule and reports the
  collisions. The replacement is `curator-swift-module-v1`, which is total,
  injective on the short branch by construction, and digest-separated on the
  overflow branch.
- **Parse the `-###` plan leniently: take the executable when the first token
  looks absolute, take a plugin value when one follows the flag, and ignore
  anything else.** Rejected: every "ignore" is a path that entered the compile
  without being checked. **Measured**, the lenient scan admits 16 of 20
  malformed plans that the fail-closed grammar rejects, including a plugin flag
  with no value, an unmatched quote and an executable outside the root.
  Expected-red control `C7` restores it.
- **Keep totality over path-shaped tokens only, and treat an unrecognised path
  carrier as a stated limit.** Rejected: it is not a limit, it is a hole, and it
  was live. An unknown `-flag` was accepted outright, a joined `-flag=value` was
  never split, and `-Xllvm`/`-Xcc` hand their value to a second option parser —
  and this toolchain really does define `-load-pass-plugin=<lib>`, whose value
  is a dynamic library the compiler loads. **Measured**, the path-shape-only
  verifier admits 14 of 16 unknown-channel vectors. The registry admits the
  tested `(6,3)` family rather than only these exact bytes, so a later
  compatible toolchain emitting a new token has to fail closed, not pass.
  Expected-red control `C14` restores it.
- **Test containment with a string prefix.** Rejected: a path lexically below a
  root can be a symlink out of it, and the failure mode is that an
  unfingerprinted executable is admitted with no diagnostic at all. Containment
  resolves both sides first. Expected-red control `C8` restores the prefix check
  and reports the escape it admits.
- **Verify the plan once and execute it, without re-checking at the permit.**
  Rejected: the verification and the execution are two moments, and a plugin
  path that was absent at the first can exist at the second. The binding and the
  permit-time re-check narrow that window; the ownership requirement on the
  declaration channels is what closes it. Keeping only one of the two would
  either rest the property on an assumption or pay for a re-check that proves
  nothing. **Measured** by expected-red control `C16`, which removes the permit
  step from the session and reports that the same appearing plugin path then
  reaches a compile permit and 2 manager-started commands.
- **State the permit in the contract and exercise it only in isolation.**
  Rejected. A re-check that every unit test calls and no session calls is a
  documented intention, not a defence — and this is not hypothetical: it is what
  cycle 4 shipped, and the reviewer found it by reading the session rather than
  by any check going red. The permit is therefore a step in the normative session
  order, the session records that it ran and over how many bindings, and seven
  integrated cases mutate real state after plan verification and require the
  compile command not to start.
- **Re-check the raw plan token for every binding.** Rejected: it is wrong for
  the one binding that matters most. An output that does not exist yet was
  verified at its operation-private parent, so re-resolving the absent final path
  fails while the session is behaving correctly — the ordinary happy path is
  rejected and the check has to be weakened or bypassed to ship. A binding
  therefore records the path whose identity was actually established and
  re-checks that. Expected-red control `C17` restores the raw-token model and
  reports the 5 findings it raises on a verified happy path where the live permit
  raises 0.
- **Treat any error while re-checking an absent plugin path as continued
  absence.** Rejected: `ENOENT` is evidence of absence and nothing else is. A
  permission error, an I/O error or a dangling symlink means the manager cannot
  establish the state of a path it is about to hand to a compiler, which is a
  fail-closed condition. The same control reports that the retired branch raises
  0 findings there where the live permit raises 1.
- **Bind only the derived module name in the canonical build input, since the
  derivation is injective.** Rejected: that makes cache identity depend on a
  property of a mapping rather than on the protocol's own distinctness. Binding
  the command key as well costs one member and removes the dependency.
- **Recognise upstream's diagnostics by their leading `error:` token.**
  Rejected: the grammar rejection and the missing-specifier rejection share a
  lead and differ only later, and the `swift build` forms carry a package-name
  infix the isolated forms do not, so a lead-only classifier answers for a
  family rather than an outcome. The probe's control `C1` restores that defect
  and reports what it fabricates.
- **Measure representability with `swift build`'s exit status.** Rejected for
  the reason decision 0007 established for Go: that status is representability
  conjoined with the floor and the host gate, and it scores every representable
  future release as unrepresentable. **Measured** that
  `swift package tools-version` reports `99.0.0` with exit 0 on a 6.3.2 host and
  therefore structurally cannot be applying the host gate. Control `C4` restores
  the wrong choice.
- **Use `swift --version` or `swiftc --version` as the version probe.**
  Rejected on measurement: both split one banner across two streams, so a
  consumer that merges them sees a concatenated line and an anchored rule stops
  matching. `-print-target-info` is JSON on stdout and is the narrower surface.
- **Use `target.triple` as the target identity.** Rejected: it carries a
  deployment-version component supplied by the SDK, so identity would move with
  an SDK update that changed nothing about what was built.
  `target.unversionedTriple` is the identity; the versioned form is what the
  compiler is given, and **measured** that the unversioned form is not itself a
  valid `-target` argument.
- **Admit the open-source Swift banner in the normalization rule so Linux works
  later.** Rejected: no host in this task carried one. Writing a rule for output
  nobody measured is the same defect as an unearned platform claim, and it would
  be the load-bearing input to a Linux qualification.
- **Claim macOS amd64 because the toolchain ships an `x86_64-apple-macosx`
  standard library.** Rejected: shipping a standard library is not evidence that
  the pipeline runs, and decision 0008 section 9 requires immutable native
  evidence for the exact tuple.
- **Report a Windows contract as qualified because the pipeline is
  platform-neutral.** Rejected: no Swift toolchain exists on the reachable
  Windows host, so the poisoned-`PATH` property, the linker resolution and the
  plugin closure are all unmeasured there. Section 13 states the contract and
  withholds the claim.
- **Memoise the toolchain fingerprint across operations to recover the 11.5 s.**
  Rejected: decision 0007 says fingerprinting proves the tree is stable across
  an operation and identical across operations, and a memo keyed on anything
  cheaper than the content proves neither.

## Compatibility impact

This decision changes no bytes. It adds no schema, no vector, no generated case
and no release metadata; it does not alter the rc.5 conformance manifest digest
or any pin. Manifest schemas 1 through 7, `skill-build.json` schema 1, receipt
schemas 1 and 2, marker schemas 1 through 3, claim schemas 1 through 3,
`Skillfile.dev.json` schema 2, `manager-worker-v1`, `capability-evidence-v1`,
`rc5-native-control-inventory-v1`, `curator-go-toolchain-v1`,
`curator-rust-toolchain-v1`, `curator-build-source-v1` and every rc.4 and rc.5
conformance byte keep their exact contents and meanings, and every `go-v1` and
`go-repository-v1` identity is unchanged.

`swift-v1` and `swift-repository-v1` remain reserved. Until
`TASK-260728-251p01` moves them, every schema including manifest schema 8 as
first minted MUST reject both, and a manager MUST treat each as an unknown
driver.

`curator-swift-toolchain-v1`, `curator-swift-module-v1`,
`curator-swift-relpath-v1`, `curator-swift-process-closure-v1` and
`curator-swift-source-admission-v1` are new identifiers that no existing artifact
names, so introducing them moves no frozen byte. None reuses, extends or aliases
`curator-go-toolchain-v1` or `curator-rust-toolchain-v1`, and all are scoped to
this driver pair: no other driver derives a module name or admits source bytes,
and none is retrofitted.

`manager-worker-v2` is used exactly as decision 0008 section 7 defines it, and
this contract mints **no** new execution-policy identity, claim schema version or
capability-evidence version. The session is at most one graph command and exactly
one compile command, both `swiftc`, with the tool executables started by the
driver's own trusted launcher. Cycle 3 of this task proposed a manager-driven job
set; it is retired here precisely because it would have required one.

Decision 0007 left the `swift` registry entry reserved with an obligation list
rather than an expected disposition table, so section 10 completes a reservation
rather than correcting a landed row. No schema or vector currently depends on
any `swift` field.

This decision takes `0011` as its number, which is the lowest unclaimed one at
the time of writing. Three in-flight records claim lower numbers and none is
landed: `TASK-260728-12pnm1` (`0009-rust-driver-pair.md`),
`TASK-260728-1jafds` (`0009-hardened-build-execution-profile.md`) and
`TASK-260728-168smo` (`0010-kotlin-native-driver-pair.md`) — so `0009` is itself
contested between two records. If review lands them in a different order, this
record renumbers rather than contests, exactly as `TASK-260728-2spy93` did when
`0007` was claimed. The renumber is mechanical and touches exactly three things:
this filename, this title, and the two references by number in
[`docs/swift-build-drivers.md`](../docs/swift-build-drivers.md).

## Security impact

The central claim of section 2 is narrow, checkable and measured: SwiftPM cannot
tell a manager what a package declares without running the package, so this
driver does not use SwiftPM at all. That removes the surface rather than
containing it, and it removes it in a direction that also removes the surface
Rust had to contain — there is no `build.rs` analogue left to reject, because
there is no manifest execution left to host one.

The central claim of section 3 is equally narrow: on the probed host, the
driver's compile vector resolves nothing through `PATH`, and the control run
that names a linker resolves two shims, so the zero is earned. The required
process closure is four executables inside one fingerprinted root, two of which
are the same file reached under different names, and the SDK is a data-only
second root that starts nothing. `swift` is present in the root and is
deliberately outside that closure: the driver never invokes it.

The claim of section 4 is stronger than "the plugin paths were checked". The
graph-to-permit gate is a fail-closed grammar that is **total over the plan's
path surface**: every path-shaped token must be claimed by one of five buckets
and boundary-checked, and a line, flag, value or path the grammar does not
account for rejects the operation. Containment is computed on symlink-resolved
paths, and every verified path is re-checked immediately before the compile
child starts. **Measured**, twenty malformed plans covering every failure family
are rejected while the plan the toolchain actually emits verifies clean — a
grammar that refused everything would prove nothing, and one that refused nothing
would prove less. Totality is over **every token**, not over the ones that
already look like paths, so a future toolchain introducing any new channel —
path-shaped or not — fails closed and requires a measured contract update rather
than being silently admitted.

The exposure this driver adds relative to `go-v1` is real and is not minimised.
A Swift front end is a larger untrusted parser and code generator than the Go
one, and by default it can load macro implementations into the compiler. Section
4 closes the selection rather than the mechanism: no source set carrying neither
`0x40` nor `0x23` can name a macro, the compiler itself enforces that both
spellings need one of those bytes, and the rejection happens before any command
starts. The mechanism remains present and is measured inert; section 14 states
that residual rather than claiming it away. What remains beyond it is the
ordinary compiler-input exposure the portable policy already admits, bounded by
the parent-enforced deadline, output and artifact limits and by whichever
native-control inventory entries the host provides, and by nothing stronger.

The narrowing this contract imposes on authors is a security property and is
stated as one: a package that needs SwiftPM dependencies, plugins, macro targets
or binary targets — or that merely *uses* a macro, including one the toolchain
ships — is not buildable by this driver, and no configuration, allowlist or flag
changes that. The honest consequence is a smaller admitted
package set, not a weaker execution boundary.

Fingerprinting remains honest about what it proves. It proves that both roots
are stable across an operation and identical across operations. It does not
prove that the toolchain is genuinely Apple's, and it does not prove that the
SDK is; verifying either remains the operator's responsibility at configuration
time, and this contract performs no signature verification of a toolchain or an
SDK. A `tree_sha256` in a receipt must not be read as provenance.

Refusing auto-install, prerelease hosts, package-selected paths, channels,
mirrors, registries and version managers is inherited unchanged from decision
0007 and is not reopened here. The one thing this decision adds to that surface
is the link-support root and its manager-owned presentation, and both are
resolved through the same two declaration channels, with the same forbidden
origins and the same diagnostics, precisely so that admitting them introduces no
new way for a package to influence what runs.
