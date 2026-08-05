# Swift build drivers: `swift-v1` and `swift-repository-v1`

Implementation-ready reference for the closed local `swift-v1` and external
`swift-repository-v1` drivers decided in
[decision 0011](../decisions/0011-swift-driver-pair.md), under the boundary of
[decision 0008](../decisions/0008-additional-language-driver-boundary.md), the
toolchain contract of
[decision 0007](../decisions/0007-compiled-build-toolchain-preflight.md) and the
execution policy of
[decision 0006](../decisions/0006-portable-manager-worker-execution.md).

Both identifiers are **reserved**, not admitted. Every schema, including manifest
schema 8 as first minted, MUST reject them until `TASK-260728-251p01` moves them
in the same change that mints the schema admitting them. Nothing in this document
is a platform claim.

Measured values below come from one host — macOS 26.5 arm64, Apple Swift 6.3.2
(`swiftlang-6.3.2.1.108`), `XcodeDefault.xctoolchain` and `MacOSX.sdk` from Xcode
26.5 — and from the `swift-boundary-fixture-v1` probe run recorded with
`TASK-260728-1yhuqi`.

### Inherited measurements

`TASK-260729-rhjxtx` is a **prerequisite**, not background reading: this
document consumes four of its measurements rather than re-deriving them, and it
is linked as `blocked_by` on the board. Each inherited fact is used exactly
once, and each is named where it is used:

| # | Inherited from `TASK-260729-rhjxtx` | Used in | Status here |
|---|---|---|---|
| M1 | `swift --version` and `swiftc --version` split one banner across stdout and stderr, so a merged read concatenates them | 1.1 "Forbidden as version probes" | **reproduced** on this host; the two agree |
| M2 | finding 6 — a `swift-frontend` job spawns for an unserved-but-known target before the standard-library failure | 1.3, decision 0011 section 5 | **refined**, not contradicted: it reproduces under a compile-only vector and does **not** reproduce under this driver's linking vector, which fails at job planning with 0 frontend jobs |
| M3 | the Linux linking vector requires `swift-autolink-extract`, a fifth executable beyond the macOS four | 12.3, and the structural closure rule of 2.1 | **consumed unchanged**; it is the evidence that the member count is platform-determined |
| M4 | no reachable Windows host carried a Swift toolchain (19 cases `not_run`) | 12.2 | **consumed unchanged**; it is why no Windows claim is recorded |

No other statement in this document rests on `TASK-260729-rhjxtx`. Where a fact
appears in both tasks it is marked *reproduced*, and the reproduction is in the
`swift-boundary-fixture-v1` command evidence.

---

## 1. `toolchain-registry-v1`: the `swift` entry

| Field | Value |
|---|---|
| `toolchain_id` | `swift` |
| `primary_relpath` | POSIX `usr/bin/swiftc`; Windows `usr\bin\swiftc.exe` |
| `fingerprint_algorithm` | `curator-swift-toolchain-v1` (section 2) |
| `baseline` | `{"kind":"at_least","min":"6.3.2"}` |
| `compatibility` | families `{(6, 3)}`, granularity `(major, minor)` |
| `platforms` | `[(macos, arm64)]` |
| `companions` | none |
| `link_support_roles` | the per-platform table of 2.4 |
| `base_installation_prefixes` | `macos`: exactly `["/usr/lib/swift"]` (section 1.3); every other platform: empty until measured |
| `metadata_sources` | `Package.swift` first-line `swift-tools-version`; `.swift-version` |

`compatibility` and `baseline` are gates, never build inputs. Lowering the
baseline requires measuring the older release. Adding a family requires running
the driver's conformance vectors against it. Neither may be derived from version
ordering, and no package or descriptor byte reaches either.

### 1.1 Probe vectors

Run once per operation from the manager parent during Stage A, from a
manager-owned empty working directory, under the section 5 environment.

| # | argv | Reads |
|---|---|---|
| P1 | `swiftc -print-target-info` | stdout JSON: `compilerVersion`, `swiftCompilerTag`, `target.triple`, `target.unversionedTriple` |
| P2 | `swiftc -print-target-info -target <target.triple>` | stdout JSON: `paths.runtimeLibraryPaths` for the exact triple the compile will use |
| P3 | `clang -print-prog-name=<linker> -target <target.triple>` | stdout: the absolute linker path the C driver will resolve |

`swiftc` and `clang` are the absolute paths `<root>/usr/bin/swiftc` and
`<root>/usr/bin/clang`. A probe MUST NOT be spelled as a bare name.

**All three probes are MANDATORY and all three are run.** P2 is not skipped when
its result appears predictable from P1: the admission of 1.3 is defined on the
triple the compile passes, and P1's default triple is a property of a host, not
of the contract. **Measured on this host**: P1 and P2 return byte-identical JSON
after canonical re-encoding (`p1_equals_p2: true` in the fixture), and P2 is run
and bound anyway. The `<linker>` argument of P3 is the platform's linker name —
`ld` on macOS; on a platform where it differs, P3 is the surface that says so,
and its answer is what enters identity (2.3), never a constant in this document.

**Forbidden as version probes.** `swift --version` and `swiftc --version` each
split one banner across two streams: `swift-driver version: 1.148.6 …` on
stderr without a trailing newline, the Apple version line on stdout. A consumer
that merges the streams sees them concatenated into one line, and an anchored
rule stops matching. Measured on this host and independently in
`TASK-260729-rhjxtx`.

**Forbidden entirely.** No `swift build`, `swift package`, `swift run`,
`swift test`, `dump-package`, `describe`, `resolve` or `show-dependencies`
invocation may appear in any stage, for any purpose, including diagnostics and
dry runs. Reading what a SwiftPM package declares executes the package
(decision 0011 section 2).

### 1.2 Normalization — `swift.printTargetInfo.compilerVersion`

Input: the `compilerVersion` member of P1's **stdout** JSON. The member MUST be
present exactly once and MUST be a JSON string; absent, duplicated or of any
other JSON type is `build_toolchain_version_undetermined`.

This is **one** grammar. Decision 0011 section 11, this section, the registry
`normalization` field and the implementation all state it, and the parser
consumes the **entire** value. There is no prefix match, no "first numeric
token" shortcut, and no unexamined suffix. Stated as ABNF over bytes, because a
regex left the suffix and the byte class ambiguous in cycle 1:

```abnf
banner    = prefix version SP "(" suffix ")"
prefix    = %s"Apple Swift version "        ; exactly 20 bytes, one trailing SP
version   = num "." num "." num
num       = "0" / ( %x31-39 *8%x30-39 )     ; no leading zero, 1..9 digits
suffix    = 1*200sbyte
sbyte     = %x20-27 / %x2A-7E               ; printable ASCII, excluding ( and )
```

with three whole-value rules that the production rules alone do not carry:

1. **Byte class.** Every byte of the value MUST lie in `%x20-7E`. That single
   rule rejects CR, LF, NUL, every other C0 control byte, DEL, and every
   non-ASCII byte — so the value is ASCII-only and is therefore its own
   canonical form, and no UTF-8 continuation byte can reach the version.
2. **Length.** The whole value MUST be 1..255 bytes and is length-checked
   **before** any scan, so an adversarial multi-megabyte value costs one
   comparison. The suffix bound of 200 bytes is inside that.
3. **Anchoring.** The value MUST end with the `)`. No leading byte, no trailing
   byte, no surrounding whitespace is tolerated or trimmed.

Excluding `(` and `)` from `sbyte` is what makes the grammar unambiguous without
balanced-paren parsing: an admitted value carries **exactly one** `(` and
**exactly one** `)`, and the `)` is the final byte. Nested parentheses are
rejected rather than parsed.

The three `num` values are the normalized version, rendered `<major>.<minor>.<patch>`.
`swiftCompilerTag` is recorded in the identity and is **not** the version.

**Measured on this host**, and the whole value is consumed:

```
Apple Swift version 6.3.2 (swiftlang-6.3.2.1.108 clang-2100.1.1.101)
└──── prefix ───────┘└ver┘ └──────────── suffix ──────────────────┘
68 bytes; normalized 6.3.2; suffix "swiftlang-6.3.2.1.108 clang-2100.1.1.101"
```

The fixture records the parsed suffix and asserts that the value **reconstructs
byte-for-byte** from the parsed components (`S29`). A parser that stops at the
first space cannot satisfy that, which is the point.

**Rejection codes.** A value that does not match leaves the version
**undetermined** and fails Stage A with `build_toolchain_version_undetermined`.
It is never guessed, never truncated, and never taken from a second surface. The
parser is **total**: every input yields either a normalized version or exactly
one of these codes, and the conformance vectors assert on the code, not on a
boolean:

| Code | Violated rule |
|---|---|
| `banner_empty` | the value is empty |
| `banner_too_long` | the whole-value length bound |
| `banner_byte` | a byte outside `%x20-7E` — CR, LF, NUL, TAB, DEL, non-ASCII |
| `banner_prefix` | the exact 20-byte prefix |
| `banner_parens` | not exactly one `(` and one `)` |
| `banner_trailing` | a byte after the closing `)` |
| `banner_separator` | the `(` is not preceded by exactly one SP |
| `banner_version_shape` | not exactly three dot-separated components |
| `banner_version_component` | an empty, non-digit, leading-zero or overlong component |
| `banner_suffix_empty` | `()` — the empty suffix |
| `banner_suffix_too_long` | the suffix length bound |

Two forms are named because cycle 1 left them disagreeing between documents, and
both are now **rejected**: `Apple Swift version 6.3.2 ()` (empty suffix) and
`Apple Swift version 6.3.2 x` (unparenthesised trailing byte — the value the
retired prefix-only parser accepted).

- No prerelease marker is admitted. `6.3.2b` is `banner_version_component`.
- The open-source banner form (`Swift version 6.1 (swift-6.1-RELEASE)`) is
  **not** admitted. No host in this task carried one; admitting it is a
  qualification obligation with its own measurement, not a grammar edit.
- Widening for a parenthesised suffix is likewise a measurement obligation on
  the host that emits one.

**Measured, and this is the evidence the narrowing is load-bearing**: over the
32 conformance vectors of section 13, the retired prefix-only parser admits **17** of
the 28 negatives — including every byte-class negative and both named forms
above. Expected-red control `C10` restores that parser and reports exactly that
set.

### 1.3 Native target admission

| Step | Rule |
|---|---|
| identity | `target.unversionedTriple` from P1. Measured: `arm64-apple-macosx`. |
| compiler argument | `target.triple` from P1. Measured: `arm64-apple-macosx26.0`. |
| admission | the **closed rule R2.1–R2.7** below, over P2's `paths.runtimeLibraryPaths` |

The identity is the **unversioned** triple, because the versioned one carries a
deployment-version component supplied by the SDK; using it would move cache
identity on an SDK update that changed nothing else in the closure.

#### The runtime-library closure is a closed three-class partition

Cycle 1 required only that entries *already inside the toolchain root* exist.
That is not a closure: it said nothing about an empty list, an entry outside
every root, or a dangling symlink.

The obvious repair — *every* entry must resolve inside a fingerprinted root —
**would reject the host this contract is measured on**. Measured, P2 for
`arm64-apple-macosx26.0` returns:

```json
["<swift-toolchain root>/usr/lib/swift/macosx", "/usr/lib/swift"]
```

The second entry exists, is a directory, and is outside every fingerprinted
root: it is the Swift runtime macOS ships in the OS. The closed set is therefore
three classes, and the third one rejects:

| Class | Definition |
|---|---|
| **A** in-closure | resolves inside a declared fingerprinted root |
| **B** base-installation | resolves inside a declared, closed, per-platform `base_installation_prefixes` entry — the **same trust boundary** 12.1 step 5 already accepts when it requires the produced executable's dynamic dependencies to be base-installation libraries of the declared platform baseline |
| **C** anything else | **reject** |

The rule, all mandatory, applied to P2's list for the **exact compile triple**:

| # | Rule |
|---|---|
| R2.1 | the list is **non-empty** |
| R2.2 | every entry is **absolute** |
| R2.3 | every entry **resolves** — a dangling symlink is a rejection, distinct from an absence — and resolves to a **directory** |
| R2.4 | every entry classifies **A or B**; a class-C entry rejects. Fingerprinted roots are matched first, so a base prefix can never shadow a root |
| R2.5 | **at least one** entry is class A. This is the standard library for the compiled triple, and it is exactly what the representability surface does not prove |
| R2.6 | every entry is serialized into identity as a `(role, relpath)` pair through `curator-swift-relpath-v1` (2.4); class-B entries take the reserved role `platform-base-installation`, so a runtime moving between the OS and the closure **moves cache identity** |
| R2.7 | a declared base-installation prefix MUST be absolute, MUST exist, MUST be a directory, and MUST NOT lie inside any fingerprinted root — otherwise class B could launder a class-A obligation |

Containment for R2.4 and R2.7 is **resolved** containment compared
component-wise and byte-exactly, the same rule as 4.1 and expected-red control
`C8`.

**Why the class-B hatch is narrow rather than a hole, measured**: the class-B
entry never reaches a compiler child. In the verified job plan the linker job's
search paths are `<root>/usr/lib/swift/macosx` — the class-A entry — and the
presented SDK's `usr/lib/swift`. The bare `/usr/lib/swift` appears as **zero**
tokens in the plan (fixture `S34`). Section 4.1's plan verification stays total
and admits **no** base-installation path in any bucket; class B is an admission
fact about where the runtime could live, never an input the driver hands to a
child.

**Measured, the unserved-target case**: P2 for `x86_64-unknown-linux-gnu`
returns exactly one entry, `<root>/usr/lib/swift/linux`, which is class-A-shaped
and does not exist. R2.3 rejects it. That is the admission test the
representability surface cannot perform.

Expected-red control `C11` restores the cycle-1 rule and reports that it admits
**6 of 6** shapes the closed rule rejects: the empty list, an out-of-closure
directory, a regular file, a dangling symlink, a relative path, and a
base-installation-only list.

The unversioned triple is **not** a valid `-target` argument. Measured:
`swiftc -print-target-info -target arm64-apple-macosx` exits 1 with
`error: Swift requires a minimum deployment target of macOS 10.9.0`.

`-print-target-info` is a **representability** surface, not an admission test.
Measured: `-print-target-info -target x86_64-unknown-linux-gnu` exits **0** and
names `<root>/usr/lib/swift/linux`, which does not exist in the tree. An unknown
triple (`not-a-real-triple`) exits 1.

Failure: `build_toolchain_platform_unsupported`, Stage A, before source
acquisition and before any compiler child.

---

## 2. `curator-swift-toolchain-v1`

### 2.1 Resolution

Two roots are resolved, in this order, through exactly the two declaration
channels decision 0007 section 3 fixes — a root bundled with the manager
distribution, or trusted operator configuration in manager-owned owner-protected
state:

| Role | Contents | Contributes a process |
|---|---|---|
| `swift-toolchain` | the toolchain root carrying `usr/bin/{swiftc,swift,swift-frontend,clang,ld}` | yes |
| `platform-sdk` | the SDK tree the compiler and linker read | no |

Forbidden origins for **both**, with the same force and the same diagnostics:
`PATH`, the inherited environment, `xcrun`, `xcode-select`, `DEVELOPER_DIR`,
`TOOLCHAINS`, a package byte, a descriptor byte, a version-manager shim
(`swiftly`, `swiftenv`), a network fetch, an installer.

A missing or unusable declaration fails Stage A with
`build_toolchain_root_undeclared` or `build_toolchain_root_unusable`, before any
source is acquired.

**Closure members.** The required set is defined structurally, not as a fixed
list, because it is platform-determined:

> Every executable the verified job plan names (section 4.1), plus the linker
> P3 resolves, MUST resolve — following symlinks — to a regular executable file
> **inside** the `swift-toolchain` root.

On macOS that instantiates to exactly four **spellings**: `usr/bin/swiftc`,
`usr/bin/swift-frontend`, `usr/bin/clang`, `usr/bin/ld`. Measured on this host:
`swiftc` is a symlink to the single `swift-frontend` binary, which dispatches on
`argv[0]`, so the four spellings resolve to **three distinct files**. Both
projections are recorded in `curator-swift-process-closure-v1` (section 2.3),
and fixture `S35` asserts the 4/3 inequality rather than restating it. A member
resolving outside the root fails `build_toolchain_root_unusable`.

**`usr/bin/swift` is NOT a member.** It is the SwiftPM launcher, section 1.1
forbids it from every stage, and the driver never invokes it, so requiring it to
resolve would add a portability constraint with no property behind it. Its bytes
are inside the fingerprinted root and are covered by `tree_sha256` regardless.
This document uses it in exactly one place — as the upstream oracle of section
7.4 — which is a conformance-probe role outside any manager pipeline. It is
therefore **probe-only: absent from the runtime closure, absent from the
registry's required member set, and forbidden from the pipeline.**

Linux was measured to add a fifth member, `swift-autolink-extract` (section
12.3). Windows is unmeasured; section 12.2 states the obligation without naming
a count it cannot support.

### 2.2 SDK presentation (mandatory)

The manager MUST NOT pass the declared SDK path to `-sdk`. It creates an
operation-private directory it owns entirely and presents the SDK through it, at
a fixed nesting depth:

```
<staging>/sdk/                                created by the manager; contains exactly `present/`
<staging>/sdk/present/                        created by the manager; contains exactly `SDKs/`
<staging>/sdk/present/SDKs/<name>        ->   <declared platform-sdk root>
```

and passes `-sdk <staging>/sdk/present/SDKs/<name>`, where `<name>` is the base
name of the declared root.

Why: the compiler derives external macro plugin search paths from the `-sdk`
argument, **three ancestor levels up and then into `Developer/usr`**. Measured
with the declared Xcode SDK path passed directly, **two distinct** derived paths
exist outside every fingerprinted root —
`…/MacOSX.platform/Developer/usr/lib/swift/host/plugins` and
`…/MacOSX.platform/Developer/usr/bin/swift-plugin-server` — and `#Predicate`
loads `FoundationMacros` through a `swift-plugin-server` process in that tree.

Why *this depth*: three levels up from `<staging>/sdk/present/SDKs/<name>` is
`<staging>/sdk/present`, so every derived tree lands inside `<staging>/sdk`,
which the manager creates and keeps empty apart from the presentation chain.

Measured with the presentation above, over two frontend jobs: 14 plugin
components in the plan; **6 distinct** paths, of which 2 exist and are both
inside the toolchain root, 4 do not exist, and **0 exist outside a fingerprinted
root**. Every SDK-derived component lands inside `<staging>/sdk` and none of
them exists. `#Predicate` fails to compile; `@Observable` compiles with exit 0
and loads `<root>/usr/lib/swift/host/plugins/libObservationMacros.dylib` **in
process**, with no server.

The manager MUST guarantee, at creation and before the graph phase, that:

1. `<staging>/sdk` is freshly created and contains exactly `present/`;
2. `<staging>/sdk/present` contains exactly `SDKs/`;
3. `<staging>/sdk/present/SDKs` contains exactly the one symlink;
4. no entry named `Developer`, `usr`, `SDKs` or `Toolchains` exists directly
   under `<staging>` or `<staging>/sdk` other than the presentation chain, so a
   derivation walking up to four levels still finds nothing; and
5. the whole `<staging>` tree is operation-private manager-owned state with no
   other admitted writer.

Failure: `build_execution_control_unavailable`.

The presentation is a defence, not the proof. Section 4.1's plan verification is
the proof, and it holds whatever the derivation rule becomes — a derived tree
that *did* exist outside a fingerprinted root would be rejected there regardless
of where it came from.

### 2.3 Identity

Every member is a `(role, relpath)` pair serialized through
`curator-swift-relpath-v1` (2.4). **No member names a filesystem path**:
toolchain location is not portable identity (decision 0007 section 3.2). The
shape below is **platform-parametric** — the macOS values are measured
instances, not constants of the algorithm.

```json
{
  "algorithm": "curator-swift-toolchain-v1",
  "swift_version": "<compilerVersion, verbatim>",
  "swift_compiler_tag": "<swiftCompilerTag, verbatim>",
  "native_target": "<target.unversionedTriple>",
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
    {"role": "swift-toolchain", "tree_sha256": "sha256:<hex>"},
    {"role": "platform-sdk",    "tree_sha256": "sha256:<hex>"}
  ],
  "closure_sha256": "sha256:<hex>"
}
```

| Member | Source | Platform-parametric? |
|---|---|---|
| `manager_invoked` | the executables the **manager itself** starts: the registry `primary_relpath` and the C driver P3 is asked through. Known in Stage A, before any plan | the relpaths come from the registry entry for the platform |
| `linker` | **whatever P3 resolves**, serialized relative to its containing root. Measured `usr/bin/ld`; on a platform where P3 answers something else, that is the value, with no new semantics | **yes** — this is the R3 repair |
| `runtime_library_members` | the classified P2 entries of 1.3, rule R2.6 | yes |
| `roots` | the ordered declared roots of 2.4 | yes — cardinality per platform |

- Each `tree_sha256` uses the same walk, ordering, record framing and link rules
  as `curator-go-toolchain-v1`, with the domain prefix
  `curator-swift-toolchain-v1/root`.
- `closure_sha256` is domain-separated over the ordered
  `(role_token, tree_sha256)` pairs with the prefix
  `curator-swift-toolchain-v1/closure`, so a two-root closure can never collide
  with a one-root closure over the same bytes, and an `n`-root closure can never
  collide with an `n+1`-root one.
- `curator-go-toolchain-v1` and `curator-rust-toolchain-v1` are untouched. This
  algorithm does not reuse, extend or alias either.

#### Why the plan-derived executable set is not in this object

The **runtime process closure** is defined structurally — *every executable the
verified job plan names, plus the linker P3 resolves, MUST lie inside the
`swift-toolchain` root* (2.1). That set is only known after the graph phase,
while this identity is computed in Stage A, before any source is acquired. It is
therefore recorded in a **separate** object, `curator-swift-process-closure-v1`,
minted at graph-phase permit time and carried in the **receipt**:

```json
{
  "algorithm": "curator-swift-process-closure-v1",
  "invoked": [
    {"role": "swift-toolchain", "relpath": "usr/bin/clang"},
    {"role": "swift-toolchain", "relpath": "usr/bin/ld"},
    {"role": "swift-toolchain", "relpath": "usr/bin/swift-frontend"},
    {"role": "swift-toolchain", "relpath": "usr/bin/swiftc"}
  ],
  "resolved": [
    {"role": "swift-toolchain", "relpath": "usr/bin/clang"},
    {"role": "swift-toolchain", "relpath": "usr/bin/ld"},
    {"role": "swift-toolchain", "relpath": "usr/bin/swift-frontend"}
  ],
  "closure_sha256": "sha256:<hex>"
}
```

Both projections are bound, because they are different facts:

- `invoked` — the relpaths **as spelled** by the manager, the registry and the
  job plan. **Measured: four** on this host.
- `resolved` — the relpaths those spellings **resolve to**, which is what
  actually executes. **Measured: three**, because `swiftc` is a symlink to
  `swift-frontend`. This is the measured content of "four executables, and two
  of them are one file"; fixture `S35` asserts the 4/3 inequality rather than
  restating it.

Binding only `resolved` would lose the fact that the pipeline invokes
`usr/bin/swiftc`; binding only `invoked` would let a re-pointed symlink keep one
identity while executing other bytes.

**Who starts what, under section 4.2.** The member set and both counts are
unchanged, but the parentage is not, and the change makes the object stronger
rather than weaker. `swiftc` is started by the manager for the **graph phase**;
`swift-frontend` and `clang` are started by the **manager** as the verified
plan's jobs, rather than by `swiftc`; `ld` is still started by `clang`. So
`invoked` now records paths the manager itself passed to `exec`, plus the one
the C driver resolves, instead of paths a child chose after the manager stopped
looking.

This object is **audit evidence, not a cache key**, and that is a deliberate
completeness claim rather than an omission: the plan-derived member set cannot
vary independently of inputs the cache key **already** binds — both root
digests, the compiler version and tag, the native target, the fixed argument
vectors and the ordered source set. Adding it to the cache key would force the
graph phase to run before every cache lookup and would buy no distinction.

#### Windows: what an implementation mints, and what it must still measure

No Windows claim is made (12.2). What is fixed **now**, so the admission task
`TASK-260728-251p01` mints a schema instead of inventing semantics:

| Question the reviewer raised | Answer |
|---|---|
| how is a P3-resolved linker serialized when it is not `usr/bin/ld`? | as `{"role": <containing root role token>, "relpath": <curator-swift-relpath-v1 of the resolved path>}`. `usr/bin/link.exe` and `usr/bin/ld` go through the same function; the extension is part of the final component |
| how do additional plan-derived executables enter identity? | through `curator-swift-process-closure-v1` above, in both projections, ordered and deduplicated by 2.4 |
| how are multiple SDK roots role-named, ordered, presented and hashed? | 2.4's ordinal rule: role token `platform-sdk[<ordinal>]`, ordinal assigned by **declaration order**, each presented under its own `<staging>/sdk/<ordinal>/present/SDKs/<name>` chain per 2.2, each hashed as its own `roots` entry in ordinal order |
| what is the Windows `link_support_roles` value? | the 2.4 table: `platform-sdk`, cardinality `one-or-more`, `data_only: true`, `qualified: false` |
| what closed root-role/member schema must `TASK-260728-251p01` mint? | the `roots`, `manager_invoked`, `linker`, `runtime_library_members` and `curator-swift-process-closure-v1` shapes above, with `role_token` drawn from the closed set of 2.4 |

### 2.4 `curator-swift-relpath-v1`, root roles, ordering and duplicates

One serialization, used by 1.3, 2.3 and the receipt. It is written so the macOS
constants and an unmeasured Windows member go through the **same** rule.

**Serialization.** Given a fully resolved root and a fully resolved member:

1. Both inputs are **fully resolved first** — POSIX `realpath(3)`; Windows
   reparse points, junctions and symlinks through the final path
   (`GetFinalPathNameByHandle`). A relpath is never computed from an unresolved
   argument, which is the lexical-containment defect expected-red control `C8`
   exists to reject.
2. The member MUST equal the root or lie strictly under it, compared
   **component-wise and byte-exactly**. A case variant on a case-insensitive
   volume fails closed rather than matching.
3. The separator in the serialized form is **always U+002F**, on every platform.
   A native separator never appears in identity.
4. **No** volume prefix, drive letter, UNC prefix, leading separator or trailing
   separator. The Windows volume forms `C:\`, `\\server\share`, `\\?\C:\` and
   `\\?\UNC\server\share\` are stripped before component splitting.
5. **No** empty, `.` or `..` component; no component may carry a separator byte
   or NUL. A Windows final component keeps its extension verbatim.
6. A member equal to its own root serializes as exactly `"."`.
7. **Case** is taken from the resolved path as the filesystem reports it, never
   from the spelling in an argument or a job plan. On a case-insensitive volume
   the resolved path is the on-disk spelling, so the serialization is
   deterministic for a given tree.

**File identity**, used for permit-time re-verification (4.1) and never part of
the portable identity: POSIX `(st_dev, st_ino)`; Windows
`(dwVolumeSerialNumber, nFileIndexHigh:nFileIndexLow)`.

**Ordering and duplicates**, for any member list:

- two members with the same `(role_token, relpath)` are **one** member, so two
  spellings that resolve to the same file collapse exactly when their canonical
  relpaths are equal;
- the list is sorted by `role_token` byte order, then `relpath` byte order —
  over the **serialized** bytes, never over the local absolute path, so the
  order does not depend on where the roots happen to live;
- two declared roots that resolve to the same real root are a Stage A failure
  (`build_toolchain_root_unusable`), not a silent collapse.

**Root roles and cardinality**, the closed per-platform table:

| Platform | Role | Cardinality | Data-only | Role token | Qualified |
|---|---|---|---|---|---|
| macOS | `swift-toolchain` | exactly-one | no | `swift-toolchain` | yes, one host |
| macOS | `platform-sdk` | exactly-one | yes | `platform-sdk` | yes, one host |
| Windows | `swift-toolchain` | exactly-one | no | `swift-toolchain` | **no** |
| Windows | `platform-sdk` | **one-or-more** | yes | `platform-sdk[<ordinal>]` | **no** |
| Linux | — | deferred to `TASK-260728-1y8u4m` | — | — | no |

`role_token` for `one-or-more` cardinality is **always** bracketed, even when
exactly one root is declared. Otherwise a host that declared one SDK today and
two tomorrow would change the identity of the *first* root, which is a silent
cache collision. `exactly-one` roles are never bracketed, so the two spellings
can never be confused.

Ordinals are assigned by **declaration order** through the two channels decision
0007 section 3 fixes, and the declaration order is part of the trusted
configuration rather than a filesystem-enumeration artefact.

**`-sdk` on a one-or-more platform** takes the ordinal-0 root, presented per
2.2. Every additional root is bound to identity and presented under its own
chain, and may be reached only through a **closed, manager-owned, per-platform
argument template**. No package byte, descriptor byte or environment variable
may add, reorder or select one. That template is **unmeasured** for Windows and
minting it is part of the 12.2 obligation; the identity and presentation rules
above do not wait on it.

**Measured cost, per operation, per root** (walk plus content hash):

| Role | Regular files | Symlinks | Bytes | Wall clock |
|---|---|---|---|---|
| `swift-toolchain` | 5,109 | 91 | 2.57 GiB | 5.89 s |
| `platform-sdk` | 32,345 | 7,448 | 0.71 GiB | 5.60 s |

The cost is stated rather than optimised away. Memoising across operations is
forbidden: it would defeat the property the fingerprint exists to prove.

---

## 3. Source layout

Identical for both drivers; `swift-repository-v1` applies it to the descriptor's
selected build root.

| Requirement | Rule |
|---|---|
| metadata file | `<build_root>/Package.swift` MUST exist as a regular file and MUST be the nearest ancestor `Package.swift` of `source_dir` |
| metadata read | **exactly** the bytes up to the first `LF`, with one trailing `CR` removed. No byte after that `LF` is read, scanned, or able to change any verdict. The body is never parsed, compiled, executed, or passed to the compiler |
| `source_dir` | MUST equal `build_root` |
| sources directory | `<build_root>/Sources` MUST exist as a directory |
| compiled source set | every regular file under `<build_root>/Sources` whose name ends in `.swift`, recursively, ordered by relative path in Unicode-scalar order; MUST be non-empty |
| other entries under `Sources` | every non-`.swift` regular file, every symlink, device, socket and fifo anywhere in the subtree is a **rejection** |
| source path bytes | every compiled source relative path MUST be free of ASCII control bytes (`0x00`–`0x1F`, `0x7F`). See 3.1 |
| source **content** bytes | every compiled source file MUST satisfy `curator-swift-source-admission-v1`: well-formed UTF-8, no NUL, and no `0x40` or `0x23` byte anywhere. See 3.3 |
| module name | `curator-swift-module-v1` over the consuming command key (section 3.2). No package string reaches an argument vector |

`Package.swift` is excluded from the compiled source set by name.

The mapping is **total** over `Sources`: it selects nothing, so there is no
candidate set, no heuristic and no ordering a package can exploit. That totality
is what satisfies decision 0008 section 4's non-discovering requirement, and it
is what makes the non-`.swift` rejection load-bearing — the compiled byte set is
exactly the audited byte set.

Two programs require two build roots.

### 3.1 Source path bytes

Rejected: any ASCII control byte in a compiled source relative path. Diagnostic
`build_source_layout_invalid`, Stage B, before the graph phase.

The rule is narrow on purpose and is **measured** rather than precautionary. A
source named `new\nline.swift` splits its job across physical lines of the
`swiftc -###` plan: measured, the graph command still exits 0 while the plan
carries 7 physical lines for 3 jobs, and the section 4.1 verifier rejects all
seven. Refusing the name at Stage A is the only place the rejection is
attributable to the snapshot rather than to a parse failure.

Admitted, and each **measured** to round-trip through the plan grammar
unambiguously:

| Name | Rendered in the plan as |
|---|---|
| `has space.swift` | single-quoted |
| `has'quote.swift` | single-quoted, the inner quote as `'\''` |
| `has#hash.swift` | single-quoted |
| `back\slash.swift` | single-quoted, the backslash literal |
| `@resp.swift` | bare, as an absolute path — never expanded as a response file |

### 3.2 `curator-swift-module-v1`

The command key grammar and the Swift module grammar do not overlap:

```
command key    ^[A-Za-z0-9][A-Za-z0-9._-]*$      unbounded; may start with a digit
Swift module   ^[A-Za-z_][A-Za-z0-9_]{0,63}$     bounded; may not start with a digit
```

A replacement rule is unsound: `my-tool`, `my.tool` and `my_tool` would all
become `my_tool`, merging three distinct protocol identities. The derivation is:

**Escape.** Map the key into `[A-Za-z0-9]` with a prefix-free code:

| Input byte | Output |
|---|---|
| `z` | `zz` |
| `.` | `zd` |
| `-` | `zh` |
| `_` | `zu` |
| any other `[A-Za-z0-9]` | itself |
| anything else | reject: the key is outside the protocol grammar |

**Branch.** Let `esc` be the escaped key.

| Condition | Result | Length |
|---|---|---|
| `len(esc) ≤ 61` | `Sk_` + `esc` | ≤ 64 |
| otherwise | `Tk_` + `hex40(SHA-256("curator-swift-module-v1\0" + key))` + `_` + `esc[:20]` | exactly 64 |

Properties, each executable rather than argued:

- **Total.** Every protocol-valid key has a result, including punctuation,
  leading digits, and keys longer than the module bound.
- **Deterministic.** No host, clock or filesystem input.
- **Injective on the short branch, by construction.** The escape is decodable;
  the decoder recovers the exact key.
- **Collision-resistant on the long branch.** A 160-bit digest of the **whole**
  key, not of a truncation.
- **Branch-separated.** `Sk_` and `Tk_` are disjoint prefixes, so a short result
  can never equal a long one.
- **Prefix-reserved.** The result always starts with an uppercase letter, so it
  can never be a Swift keyword and can never be `Swift` — which a bare escape
  would produce for the key `wift`. Measured: of 341 module and framework names
  inventoried from the toolchain root and the platform SDK, **0** carry either
  prefix.

Declared mapping, which the conformance vectors carry verbatim:

| Command key | Module name |
|---|---|
| `tool` | `Sk_tool` |
| `my-tool` | `Sk_myzhtool` |
| `my.tool` | `Sk_myzdtool` |
| `my_tool` | `Sk_myzutool` |
| `9.tool` | `Sk_9zdtool` |
| `0` | `Sk_0` |
| `z` | `Sk_zz` |
| `z-z` | `Sk_zzzhzz` |
| `zdz` | `Sk_zzdzz` |
| `a.b-c_d.e` | `Sk_azdbzhczudzde` |
| 41 bytes escaping to exactly 61 | `Sk_…`, exactly 64 long |
| one byte more | `Tk_…`, exactly 64 long |

A key outside the protocol grammar is rejected with
`build_source_layout_invalid`; the manager never coerces one.

**Identity does not depend on this being injective.** Section 8 binds the
command key itself into the canonical build input alongside the module name.

### 3.3 `curator-swift-source-admission-v1`

**Stage B, applied to the compiled source set after 3.0 enumerates it and before
the graph command runs.** Nothing is executed for a source set this rule
rejects: no graph phase, no plan, no compile permit, no compile child.

```abnf
; the whole rule, over the raw bytes of one file
admitted-file  = *admitted-octet
admitted-octet = %x01-22 / %x24-3F / %x41-FF   ; excludes NUL, 0x23 '#', 0x40 '@'
                                               ; and is further constrained to
                                               ; well-formed UTF-8 by A2
```

Evaluation order per file is normative:

| Rule | Check | Diagnostic |
|---|---|---|
| A1 | the file is readable as a regular file | `swift_source_unreadable` |
| A2 | the bytes are well-formed UTF-8 per RFC 3629 — no overlong form, no UTF-16 surrogate half, no code point above U+10FFFF, no truncated or unled sequence — and carry no NUL | `swift_source_encoding_forbidden` |
| A3 | no byte equals `0x40` (`@`) or `0x23` (`#`), at any offset, in any context | `swift_source_macro_selector_forbidden` |

All three report `build_package_code_execution_forbidden`. The rejection record
carries the file path, the rule, the byte offset and the byte, so the diagnostic
is reproducible from the snapshot alone. **Every** rejected file in the source
set is reported, sorted by path, so a multi-file rejection is deterministic
rather than dependent on read order.

**A2 precedes A3 and the order is load-bearing.** A3's claim is "no `0x40` byte
implies no U+0040 code point", which holds only on well-formed UTF-8. A malformed
file is rejected rather than scanned, so the manager does not depend on the
compiler to refuse an overlong encoding — though **measured**, it does:
`0xC1 0x80` in place of `@` produces `error: invalid UTF-8 found in source file`.

**The rule does not parse Swift.** It does not skip comments, does not skip
string literals, does not normalize, and reads no package-supplied artifact other
than the source bytes. It is therefore total over every possible byte sequence.

**Position within Stage B is fixed**, so two Stage-B rejections cannot race for
the diagnostic. The order is: source layout (section 3, including 3.1) →
metadata disposition (section 7) → this rule → the graph command. A layout or
metadata rejection therefore reports its own code and this rule never runs; a
source set that passes both is scanned before anything is executed.

**It adds no build input.** The bytes are already hashed by
`curator-build-source-v1` and already inside the audit subject; this rule reads
them and produces a verdict, and neither the verdict nor the scan enters the
canonical build input, the cache key, the receipt, the marker or the claim.

**It leaves a binding.** For every admitted file the manager MUST record the
digest of the bytes it scanned. The rule runs once per session, on bytes read at
Stage B; the compile command reads the file again, later, and the permit of 4.1.4
is where those two reads are required to agree. Without the binding the rule
would be a statement about a file the manager no longer has. The digest is not a
build input either — it is operation-local, exactly like the verdict.

#### Why `0x40` and `0x23` are the whole macro-selection surface

Swift has exactly two macro-use spellings: an attached macro is a custom
attribute, and a freestanding macro is an expansion. The compiler enforces both
requirements itself, which is what makes this a measurement rather than a reading
of the grammar. All on Apple Swift 6.3.2 / macOS 26.5 arm64:

| Vector | Measured |
|---|---|
| `externalMacro(module:"A",type:"B")` with no sigil | `error: expansion of macro 'externalMacro(module:type:)' requires leading '#'` |
| `macro stringify<T>(_ v: T) -> (T, String) = #externalMacro(…)` with no role attribute | `error: macro 'stringify' must declare its applicable roles via '@freestanding' or '@attached'` |
| `Observable final class Box {}` — attribute name without `@` | not an attribute; `error: consecutive statements on a line must be separated by ';'` |
| `\u{40}Observable` — escape outside a literal | not syntax; same parse error |
| `＠Observable` — U+FF20 fullwidth | an identifier character, not an attribute marker; same parse error |
| overlong UTF-8 for U+0040 | no `0x40` byte present; rejected by A2, and independently by the compiler |
| `import Observation` with no macro use | compiles, **0** macro-load remarks |
| the admitted rich-Swift source set | compiles under one `swiftc` command with the plugin search paths present: **5** plugin components in the plan, **0** load remarks, artifact runs |

#### What the rule rejects as collateral

The over-rejection is deliberate and is inventoried here rather than discovered
one construct at a time. Every entry below is rejected because it carries one of
the two bytes, not because it is a macro:

`@main`, `@available`, `@escaping`, `@inlinable`, the `@Sendable` attribute
spelling, `@objc`, `@_cdecl`, `@_silgen_name`, every property-wrapper use, every
other attribute; `#if` / `#elseif` / `#endif` conditional compilation,
`#available`, `#file`, `#line`, `#function`, `#selector`, `#keyPath`, raw string
literals `#"…"#`, extended regex literals `#/…/#`; and any `@` or `#` inside a
comment or a string literal, including an email address in a message string.

What remains admitted is measured, not promised: the standard library,
`Foundation`, `Codable` and `Sendable` conformances, `actor`, `async`/`await`,
generics and `where` clauses, bare regex literals `/…/`, string interpolation,
multi-line string literals, custom operators, protocols and extensions, and
Unicode identifiers.

#### Conformance vectors

`SA01`–`SA20` are admitted, `SR01`–`SR22` are rejected on the selector byte and
assert the exact byte and diagnostic, `SE01`–`SE10` are rejected on encoding and
each carries **no** raw sigil byte so the encoding rule is what rejects them. Two
further properties are asserted: the hand-written UTF-8 validator agrees with the
standard library on every one- and two-byte sequence that contains no NUL, and
the rule is total — every input yields either an admission or a fully named
rejection.

Expected-red control `C13` restores the retired Stage B, which admitted
everything, and reports that macro-selecting source is then admitted, receives a
compile permit and loads `libObservationMacros.dylib`.

---

**External mode only.** A `swift-repository-v1` command requires
`skill-build.json` **schema 2**. Against schema 1 it fails
`build_descriptor_driver_unsupported`; against an unsupported version,
`build_descriptor_schema_unsupported`. Neither falls back to another target,
another driver, a script, a system command or a generic build facility.
`build_root` MAY be `.`. The whole external snapshot is the validation, identity
and audit subject; only the selected build root is compiler-visible.

---

## 4. The two argument vectors

Working directory: the canonical `source_dir`. The manager MUST use exactly
these vectors and MUST NOT alter, extend, reorder or repeat them.

The relation between the two vectors is stated as a **construction**, not as a
prose comparison, because "they differ in exactly one token, at index 0" is
ambiguous when read as complete argv — index 0 is the program, and `-###` is an
**insertion after** it. This is the normative form, and it is the form the
implementation and the conformance vectors use verbatim:

```text
program      := the resolved absolute swiftc inside the swift-toolchain root
compile_args := [ "-swift-version", "6",
                  "-O",
                  "-target", <native-triple>,
                  "-sdk", <presented-sdk>,
                  "-module-name", <module>,
                  "-no-color-diagnostics",
                  <sources…>,
                  "-o", <staged-artifact> ]

graph_args   := [ "-###" ] ++ compile_args

compile_argv := [ program ] ++ compile_args
graph_argv   := [ program ] ++ graph_args
```

Every one of these MUST be asserted mechanically, not assumed:

| # | Property |
|---|---|
| V1 | `len(graph_args) == len(compile_args) + 1` |
| V2 | `graph_args[0] == "-###"` |
| V3 | `graph_args[i+1] == compile_args[i]` for every `i`, **byte-exact** |
| V4 | `graph_argv[1] == "-###"` — the insertion point in **complete argv** |
| V5 | `count(graph_argv, "-###") == 1` — exactly once, nowhere else |
| V6 | `count(compile_argv, "-###") == 0` — never in the executed vector |
| V7 | `graph_argv[0] == compile_argv[0] == program` |

`-###` cannot collide with any other token — sources are absolute paths, the
module name matches `^[A-Za-z_][A-Za-z0-9_]{0,63}$` (3.2), and every remaining
token is a manager-owned constant or a manager-derived path — but V5 and V6 are
asserted anyway, because "cannot collide" is an argument and an assertion is a
check.

That is the property the graph phase rests on: **the compile phase re-derives
the plan the graph phase verified, from the same inputs**. The manager MUST
produce both vectors from **one** builder, so they cannot drift. Fixture `S38`
asserts V1–V7 on the live vectors; `S39` supplies five negatives — no insertion,
doubled, appended instead of inserted, present in the compile vector, and a
second token co-mutated under cover of the insertion — and requires all five to
be rejected. `S63` additionally asserts the property on the two commands the
session actually started.

**Both vectors are executed, and they are the only two commands the manager
starts.** `graph_argv` is the graph phase; `compile_argv` is the compile phase,
run once after the permit, under section 4.2. V1–V7 are what make the graph
phase meaningful: they establish that the verified plan describes exactly the
requested compilation and nothing else, and that the compile command differs from
it by one token that only suppresses execution. Section 11 records what this does
**not** establish — that the inspected processes are the processes that ran.

| Placeholder | Source |
|---|---|
| `<native-triple>` | Stage A `target.triple` (section 1.3) |
| `<presented-sdk>` | section 2.2 |
| `<module>` | `curator-swift-module-v1` over the consuming command key (section 3.2) |
| `<sources…>` | the ordered compiled source set (section 3) |
| `<staged-artifact>` | operation-private manager staging path |

`<staged-artifact>` MUST be stable for a given operation, because the output
path reaches the Mach-O `LC_UUID` (section 10).

The planned **job** argv is a different thing and is **not** reproducible:
measured, it carries a per-run `TemporaryDirectory.XXXXXX` the driver creates
under the operation-private `TMPDIR`. Section 4.1 is therefore a
bucket-and-boundary check over the plan, never a comparison against a fixed
expected plan.

### 4.1 Graph-phase plan verification

`swiftc -###` prints a job plan and executes nothing. Measured: exit **0** for a
source file containing `this is not swift @@@ (((`, exit **0** for a source path
that does not exist, and the source directory unchanged in both cases. The plan
is written to **stdout**; stderr is empty.

This section is a rejection engine. There is no skip, no ignore and no
best-effort recovery: anything the grammar does not account for fails
`build_execution_control_unavailable` before the compile phase.

#### 4.1.1 The output grammar

Measured on Apple Swift 6.3.2, macOS 26.5 arm64. The plan is POSIX
single-quote-quoted argv, one job per line. It is read as a **binary stream**
and is parsed in two layers, stated separately because the lower one is what a
Windows implementation would otherwise have to guess at.

**Layer 1 — the physical-line grammar.** Total over byte strings: a plan either
splits into lines or is rejected.

```abnf
plan        = 1*line-record
line-record = line LF                  ; the TERMINAL LF IS MANDATORY
line        = 1*lbyte                  ; non-empty
lbyte       = %x20-7E / %x80-FF        ; no C0 control, no CR, no DEL
```

Every previously ambiguous case is decided here:

| Case | Rule |
|---|---|
| terminator | **LF (0x0A) only**, on every platform |
| terminal LF | **MANDATORY**. MEASURED: the plan's final byte is 0x0A. A plan whose final byte is not LF is a truncated read and rejects. This is what removes the `LF?` ambiguity: splitting on LF yields exactly **one** trailing empty element, it is dropped, and a second one is a blank line |
| bare CR | **REJECTED anywhere**, on every platform. Never stripped, never normalized, not even at end of line |
| CRLF | consequently rejected. A Windows implementation MUST read the child's stdout as a **binary stream with no newline translation**. If a Windows toolchain is ever measured to emit CRLF, that measurement extends this grammar; it is never a runtime fallback |
| other control bytes | every byte `< 0x20` other than the LF terminator, and `0x7F`, rejects. This is the **same** class layer 2 rejects, so the two layers cannot disagree |
| bytes `0x80-0xFF` | **admitted** inside a line and compared **byte-exactly**. The plan is not required to be valid UTF-8: a POSIX path is a byte string, and every path token is compared against the manager's own byte set rather than decoded |
| blank line | rejected. A whitespace-only line is non-empty here and then fails layer 2's "first token must be an absolute path" rule |
| bounds | plan ≤ 8 MiB, line ≤ 64 KiB, ≤ 4096 lines. An adversarial plan is never an unbounded read |

**MEASURED** for the driver's own vector: 4808 bytes, final byte 0x0A, 3 LF,
**0 CR**, 0 other control bytes, 0 non-ASCII bytes, longest line 1990 bytes, 3
job lines, stderr empty.

The cycle-1 verifier silently removed one trailing CR from every line while this
document rejected every control byte. That contradiction is now closed in favour
of rejection, and expected-red control `C12` restores the CR-normalizing
splitter: it admits **11** of the 12 malformed physical-line families below,
including the unterminated final line and all three CR shapes.

**Layer 2 — the token grammar**, applied to one line of layer 1:

```abnf
line   = token *( 1*SP token )                  ; MUST be non-empty
token  = 1*( bare / quoted / escaped )
bare   = <any byte except SP, "'", "\", and every ASCII control byte>
quoted = "'" *( <any byte except "'"> ) "'"
escaped= "\" <any byte except an ASCII control byte>
```

Measured token renderings: a value containing a space or a `#` is wrapped in
single quotes; an embedded single quote is rendered `'\''` — close the quoted
run, backslash-escape the quote outside it, reopen; a backslash inside a quoted
run is literal.

The tokenizer MUST fail — not return a shorter token list — when a line ends
inside a quoted run, ends with a dangling backslash, or carries any ASCII
control byte. A shorter token list is exactly how a malformed plan reads as a
clean one.

Line-level rules, all mandatory:

1. the graph command MUST have exited 0, its stderr MUST be empty, and the plan
   MUST satisfy layer 1 above;
2. layer 1 supplies the ordered lines; the verifier strips nothing from them, so
   a line reaching layer 2 is exactly the bytes the compiler emitted between two
   LFs;
3. every line MUST tokenize under layer 2, and its first token MUST be an
   absolute path.

**Physical-line negatives**, each of which MUST reject (conformance group
`LV01`–`LV12` of section 13): the empty plan; no terminal LF; `CRLF`; a bare CR
before the terminator; a bare CR mid-line; a trailing blank line; a leading
blank line; a blank line between jobs; an embedded NUL; an embedded TAB; an
embedded DEL; a line past the 64 KiB bound.

#### 4.1.2 The closed per-job token grammar

Cycle 2's rule was total over tokens the verifier already recognised as
**path-shaped**. That is not closed, and the gap was live rather than
theoretical. Three families passed without any verdict at all:

- an unknown flag beginning with `-` fell off the end of the dispatch chain and
  was accepted;
- a joined `-flag=value` carrier was never split, so its value never became
  path-shaped and was never checked. **MEASURED**: this toolchain defines
  `-load-pass-plugin=<path>`, whose value is a dynamic library the compiler
  loads;
- `-Xllvm` and `-Xcc` hand their value to a **second option parser**, so
  `-Xllvm -load-pass-plugin=<lib>` and `-Xcc -isystem<dir>` carry a path through
  a token that is not itself path-shaped.

Totality is therefore over **every token of every job line**. A token is
admitted only by being named in a table below. A token no table claims is a
rejection, whether or not it looks like a path.

**Job kinds** are read off the plan, never off a file name: a job is a
**frontend** job exactly when its first argument is `-frontend`, and a **link**
job otherwise. Each kind has its own admitted flag set.

**The five path buckets** are unchanged, and are still what a path value must
satisfy:

| Bucket | Rule |
|---|---|
| executable | MUST exist and resolve to a regular executable **inside the `swift-toolchain` root** |
| plugin | MUST resolve **inside a fingerprinted root**, **or** MUST NOT exist. The path stays in the plan; section 3.3 is what makes it unreachable, and section 4.2 measures it inert |
| search | MUST exist and resolve **inside a fingerprinted root** |
| source | MUST equal a member of the manager's own ordered compiled source set, **byte for byte** |
| output | MUST resolve, or have a parent that resolves, **inside operation-private manager state** (staging or the operation `TMPDIR`) |

**Common valued flags**, admitted in either job kind because each one lands in a
bucket that is boundary-checked:

| Flags | Bucket |
|---|---|
| `-sdk`, `-isysroot`, `--sysroot`, `-resource-dir`, `-I`, `-F`, `-L` | search |
| `-o` | output |
| `-new-driver-path` | executable |
| `-primary-file` | source |
| `-plugin-path`, `-external-plugin-path`, `-in-process-plugin-server-path`, `-load-plugin-library`, `-load-plugin-executable`, `-load-resolved-plugin`, `-cas-plugin-path` | plugin |

**Per-kind nullary flags**, MEASURED on Apple Swift 6.3.2, macOS 26.5 arm64:

| Kind | Flags |
|---|---|
| frontend | `-frontend`, `-c`, `-enable-objc-interop`, `-stack-check`, `-no-color-diagnostics`, `-O`, `-empty-abi-descriptor`, `-no-auto-bridging-header-chaining`, `-disable-clang-spi`, `-enable-default-cmo` |
| link | `-O3` |

**Opaque-value flags** — the frontend kind only — and the rule that keeps an
opaque value from becoming a value carrier. Every opaque value MUST NOT be
path-shaped, MUST NOT contain `/`, `\` or `#`, MUST match its class charset,
and, where the manager itself chose the value, MUST equal what the manager chose
**byte for byte**:

| Flag | Class | Rule |
|---|---|---|
| `-target`, joined `--target=` | triple | `[A-Za-z0-9._-]+`, and equal to the manager's `target.triple` |
| `-swift-version` | language version | equal to the manager's constant |
| `-module-name` | module | the section 3.2 shape, and equal to the derived module name |
| `-target-sdk-version` | version | `[0-9.]+` |
| `-target-sdk-name` | SDK name | `[A-Za-z0-9._-]+` |
| `-Xllvm` | pass-through | member of the platform's **measured** value allow-set — `-aarch64-use-tbi` on this host |
| `-Xcc` | pass-through | member of the platform's **measured** value allow-set — `-fno-color-diagnostics` on this host |

The two pass-through flags are the reason an allow-set exists rather than a
charset: their value is parsed by another option parser, so admitting an
unmeasured value would delegate the boundary to that parser.

**Joined spellings**: `--target=`, `-I<path>`, `-L<path>`, `-F<path>`. Longest
prefix wins. A joined form with an empty value is a rejection.

**Positional operands**: in a frontend job a positional token MUST be a compiled
source-set member; in a link job it MUST resolve inside operation-private state.

**Remaining flag/value rules**, all mandatory:

- a valued flag admits `-flag value` and `-flag=value`; no following token, or an
  empty value, is a rejection;
- `-external-plugin-path` carries exactly `<dir>#<server>`: exactly one `#`,
  both components non-empty and absolute. Any other shape is a rejection;
- every **other** plugin flag carries exactly one path; a `#` in its value is a
  rejection, because that flag defines no separator;
- a token beginning with `@` is a **response file** and is rejected before every
  other rule, so no later rule can be reached by argument expansion;
- an empty token is a rejection.

**Extension is a measured contract change.** If a future Swift patch emits a
token none of these tables claims, the operation fails closed with
`build_execution_control_unavailable`. Adding it requires measuring the emitted
plan and revising this section; it is never a runtime accommodation, and it is
never an allowlist entry added because a build broke.

#### 4.1.3 Containment

Containment is computed on the **symlink-resolved** path of both the candidate
and the root, and compared byte-exactly on path components:

```
contained(p, r)  :=  resolve(p) == resolve(r)  OR  resolve(p) starts with resolve(r) + separator
```

- `/root-evil/bin/ld` is not inside `/root` — a shared prefix is not containment;
- a path lexically below a root but symlinked out of it is **rejected**;
- the root itself is inside itself, because `--sysroot` names it directly;
- on a case-insensitive volume a case variant does not match and therefore fails
  closed;
- a **dangling symlink** is an entry that exists and resolves nowhere. It is
  neither inside a root nor absent, so it is a rejection.

#### 4.1.4 Binding and the compile permit

The graph phase and the compile phase are two moments. The compile permit is the
step that joins them, and it is a **step in the session**, not a capability the
manager has: `compile_argv` MUST NOT start until it has run.

**The session order is normative.**

```text
1. AdmitSources            curator-swift-source-admission-v1 (3.3), before any process
2. graph_argv              manager command 1 of 2, executes nothing
3. VerifyPlan              the closed grammar of 4.1.2 over every token
4. the compile permit      this section
5. compile_argv            manager command 2 of 2
```

A manager that runs step 5 without step 4 is not implementing this driver, even
if every other check passes.

**What a binding is.** For each path the plan named, the manager MUST record:

| Field | Meaning |
|---|---|
| `raw` | the token the plan carried, byte for byte |
| `checked` | the path whose identity was **actually** established |
| `resolved` | the symlink-resolved target of `checked` |
| `identity` | the file identity of `resolved` |
| `present` | whether `checked` existed at graph time |

`raw` and `checked` are the same path in every bucket except one: an output that
does not exist yet. There the manager verified the **operation-private parent**
(4.1.2, output bucket), so the parent is what was identified and the parent is
what MUST be re-checked. A permit that re-resolves `raw` for such a binding
rejects the ordinary happy path, because the output is correctly still absent
when the permit is granted; the two fields exist so that cannot be written by
accident.

The manager MUST additionally record, for every source admitted at step 1, the
**digest of the bytes the rule scanned**. File identity is size, mode and mtime,
all of which a writer can restore; the digest is what actually answers "are these
the bytes that were admitted?".

**What the permit re-checks.** Immediately before starting `compile_argv`, and
after nothing else has run in between, the manager MUST reject unless:

- every bound path still resolves to the identical resolved path;
- every bound path still has the identical file identity;
- every plugin path bound as **absent** is still absent, where *absent* means the
  re-resolution returned `ENOENT` and nothing else. A permission error, an I/O
  error, a dangling symlink, or any other failure is **not** evidence of absence
  and MUST fail closed; and
- every admitted source still has the digest Stage B recorded.

**The failure is one outcome.** Any finding reports
`build_execution_control_unavailable` with the Swift detail
`swift_permit_binding_changed` (section 9), leaves **exactly one**
manager-started command — the graph command — and produces **no** artifact. The
manager MUST NOT retry, re-plan, re-run the graph phase, or fall back to a
narrower vector.

This **narrows** the window; it does not remove it. What closes it is the
ownership requirement section 2.1 already imposes: both fingerprinted roots are
manager-distribution or owner-protected manager-owned state, and `<staging>` is
operation-private, so no other principal is an admitted writer. The re-check is
the defence that does not depend on that assumption holding.

**Measured, inside the session** — Apple Swift 6.3.2 / macOS 26.5 arm64, over the
default two-source vector. Each adversarial row mutates state **after** step 3
has already accepted the whole plan, which is the only window the graph phase
leaves open, and each one is required to name its own mechanism rather than to
produce any finding at all:

| Case | Mutation between step 3 and step 4 | Measured |
|---|---|---|
| `S65` | none | permit ran over **35** bindings (33 plan + 2 sources), **0** findings, **2** commands, artifact produced; **10** absent plugin paths and **5** absent-output bindings re-checked at their parent |
| `S66` | an absent plugin path is created | rejected, **1** command, no artifact |
| `S67` | an admitted source gains a `@` | rejected, **1** command, no artifact; the finding names `swift_source_macro_selector_forbidden` |
| `S68` | an admitted source is replaced by rename | rejected, **1** command, no artifact; the finding names the digest change |
| `S69` | the presented SDK is re-pointed | rejected, **1** command, no artifact |
| `S70` | the output's recorded parent is replaced | rejected, **1** command, no artifact |
| `S71` | a bound executable's bytes change | rejected, **1** command, no artifact |

`S71` runs against a **synthetic** manager-owned toolchain root, because the real
one is read-only host state. Its plan is verified by the same closed grammar and
the same bucket rules; only the executables behind it are writable, and the claim
is about this section's permit step rather than about Swift.

Two expected-red controls hold the section: `C16` removes step 4 and measures
that the same plugin appearance then reaches a compile permit and **2** commands;
`C17` restores the retired binding model and measures that it reports **5**
findings on a verified happy path where the live permit reports **0**, and **0**
findings on an absent plugin path whose state cannot be established where the
live permit reports **1**.

#### 4.1.5 Measured results

With the section 2.2 presentation, over the default two-source vector:

| Quantity | Measured |
|---|---|
| planned jobs | 3 — two `swift-frontend`, one `clang` |
| executable bucket | 5 bindings (3 job executables, 2 `-new-driver-path`), 0 outside the root |
| plugin bucket | 14 components; 6 distinct; 2 existing, both inside the toolchain root; 4 absent; **0 existing outside a fingerprinted root** |
| search bucket | 5 bindings, all inside a fingerprinted root |
| source bucket | 4 bindings, each byte-equal to a manager source-set member |
| output bucket | 5 bindings, all inside operation-private state |
| rejections | **0** |

The whole plan is **101 tokens** over the three jobs, and the closed grammar of
4.1.2 claims every one of them with **0 rejections**.

Negative coverage, one vector per failure family, all **rejected**.

*Path and line families* (cycle 1): relative executable; unknown wrapper line;
executable outside the root; executable that does not exist; unmatched quote;
dangling backslash; plugin flag with no value; plugin flag with an empty value;
`-external-plugin-path` with one component; with three components; `#` in a
single-path plugin flag; plugin path existing outside every root; search path
outside every root; joined search path outside every root; search path that does
not exist; source not in the manager's set; output outside operation-private
state; unclaimed absolute positional; blank line; empty plan; ASCII control
byte; `-new-driver-path` outside the root. Measured: **20 of 20 rejected**; the
retired lenient scan admits **16 of the 20**.

*Unknown-channel families* (cycle 3), each one an otherwise valid job carrying
exactly one extra or substituted token: unknown flag; unknown joined flag with
an absolute value; unknown joined flag with a relative value; joined
`-load-pass-plugin=<lib>`; `-Xllvm` carrying a plugin load; `-Xcc` carrying a
recognised search path; `-Xcc` carrying an **unrecognised** search path
(`-isystem<dir>`); `-Xllvm` with an unmeasured value; an opaque value carrying a
path; an opaque value carrying a separator; an opaque value that is not the
manager's; an opaque target that is not the manager's; a stray non-path operand;
a response file; a link-only flag in a frontend job; an otherwise valid plan
with one extra unknown token. Measured: **16 of 16 rejected**, while the plan
the toolchain actually emits still verifies with 0 rejections. The retired
path-shape-only verifier admits **14 of the 16** — it catches only `-Xcc -I<dir>`
and `-module-name <abs path>`, and both by accident, because those two values
happen to match its joined-search and path-shape scans.

The linker never appears in this plan: the link job is `clang`, and `clang`
starts the linker. Its resolution is checked by probe vector P3, which measured
`<root>/usr/bin/ld` and confirmed resolved containment.

Failure: `build_execution_control_unavailable`, before the compile phase.

### 4.2 The compile phase is one command, and the plugin channel is inert

`swiftc` plans jobs and then runs them. The frontend jobs it spawns carry plugin
search paths the manager never asked for, and package **source** — not a
manifest, not a flag — selects which macro implementation the frontend loads from
them. Decision 0008 section 7 forbids exactly that surface and forbids answering
it with a runtime allowance.

#### 4.2.1 What cannot be done, and why

Four **negative measurements**, all on Apple Swift 6.3.2 / macOS 26.5 arm64,
establish that no argument, environment or presentation suppresses the load while
`swiftc` runs its own jobs:

| Attempt | Measured |
|---|---|
| `-resource-dir <manager-owned>` | **0 of 10** plugin components move; they derive from the driver's own executable location |
| present the toolchain the way 2.2 presents the SDK — invoke `swiftc` through a manager-owned symlink | **0 of 10** components move; the driver resolves its own executable first |
| point `-in-process-plugin-server-path` at an absent file | the compile still exits 0 and the macro **still loads**; the implementation is loaded directly, not through the named server |
| look for a disabling flag | neither `swiftc` nor `swift-frontend` defines one; the option list has no `-no-plugins`, `-disable-plugin-search` or equivalent |

The channel is entirely flag-driven — **measured**, the same frontend job with no
plugin flag rejects `@Observable` with `plugin for module 'ObservationMacros' not
found` and loads nothing — so deleting the flags from the plan and executing the
jobs directly does close it. That is what cycle 3 of this task shipped, and it is
**retired**, because deleting flags requires the manager to start the jobs, and
accepted decision 0008 section 7 admits **exactly one** compile command started
by the driver's own trusted launcher.

| | manager-started commands | compile-phase parentage |
|---|---|---|
| this contract | **2** — `swiftc -###`, then `swiftc` | `swiftc` starts `swift-frontend`, `clang`, `ld` |
| the retired plan-execution design | **4** measured for the default source set — 1 graph + 3 plan jobs | the manager starts `swift-frontend` and `clang` directly |

Expected-red control `C15` restores the retired design and reports both numbers.
The surface is closed instead at Stage B, by `curator-swift-source-admission-v1`
(section 3.3), before any command runs.

#### 4.2.2 The compile phase

```text
after the permit of 4.1.4 has run and reported nothing, the manager runs
compile_argv exactly once and starts nothing else
```

"After the permit" is a precondition, not a description of ordering in prose:
`compile_argv` is reachable only through 4.1.4, and a session that reaches it
another way is rejected by control `C16`.

`swiftc` re-derives its own plan and starts its own children. The manager MUST
NOT start a plan job, a frontend, a `clang` or a linker, and MUST NOT retry,
re-plan, or issue a second compile command; any of those is a session shape
`manager-worker-v2` does not admit.

The graph phase's verification (4.1) therefore constrains the compile phase
through an equality of **inputs**: both commands share one `program`, one source
set, one environment and one working directory, and differ by exactly one
inserted token (4.0). Every path the graph phase bound is re-resolved and
re-checked at the permit (4.1.4). What is **not** claimed is that the processes
inspected are the processes that ran; section 11 records that residual.

#### 4.2.3 Measured

| Quantity | Measured |
|---|---|
| manager-started commands for the default source set | **2** — `swiftc -###`, `swiftc` |
| plugin components in the plan for the admitted source set | **5**, every one inside a fingerprinted root or absent (4.1.5) |
| macro-load remarks for the admitted source set | **0** |
| macro-load remarks for `import Observation` with no macro use | **0** |
| the admitted rich-Swift set | Foundation, `Codable`, a bare regex literal, string interpolation and `Sendable` build, and the artifact runs |
| `@Observable` / `#Predicate` | rejected at Stage B with **0** manager-started commands and no artifact |
| determinism | two full sessions to the same output path give **1** distinct digest over 4 commands |

`-Rmacro-loading` is **not** a member of either contract vector — the closed
token grammar of 4.1.2 rejects the `-Xfrontend` pass-through that carries it — so
the remark counts above come from a separate evidence-only compile of the same
source to a throwaway path. The contract session is what is verified; the
evidence run is what distinguishes "nothing loaded" from "nothing reported".

Failure: `build_package_code_execution_forbidden` at Stage B for a rejected
source file, before the graph phase.

---


## 5. Operation-private environment

The environment starts empty except for indispensable operating-system process
variables, and carries exactly:

| Variable | Value |
|---|---|
| `PATH` | a manager-owned **empty** directory |
| `HOME` | operation-private |
| `TMPDIR` | operation-private, MUST exist before the first child starts |
| `LC_ALL`, `LANG` | `C` |
| Windows: `APPDATA`, `LOCALAPPDATA`, `USERPROFILE`, `TEMP`, `TMP` | operation-private |

Nothing else. In particular the following MUST be absent, not merely overridden:
`DEVELOPER_DIR`, `TOOLCHAINS`, `SDKROOT`, `SWIFT_EXEC`, `SWIFT_DRIVER_*`,
`SWIFTPM_*`, `SWIFT_BACKTRACE`, `MACOSX_DEPLOYMENT_TARGET`, `CPATH`,
`C_INCLUDE_PATH`, `LIBRARY_PATH`, `LD_LIBRARY_PATH`, `DYLD_*`, `CC`, `CXX`,
`LD`, `LDFLAGS`, `CFLAGS`, `NSUnbufferedIO`, every proxy variable, and every
version-manager variable.

There is no manager-written tool configuration file for Swift. There is no
SwiftPM in the pipeline, so there is no `$SWIFTPM_HOME`, no registry
configuration, no mirror file and no netrc to write or neutralise.

A `TMPDIR` that does not exist is a hard failure, not a warning: measured, the
driver aborts with `error: couldNotFindTmpDir(…)` and produces nothing.

---

## 6. Pre-compile rejection matrix

Total. Every surface has exactly one verdict, decided before the compile phase.
The shared semantic class is `build_package_code_execution_forbidden` unless a
row names another.

### 6.1 Properties

- **No package code runs.** Every row is decided from snapshot bytes the manager
  reads itself, or from the `-###` plan, which was measured to execute nothing.
- **Host-independent.** The only host-derived inputs are the resolved triple and
  the presented SDK path, both manager-selected.
- **Three verdicts, kept apart.** `reject` fails the operation with a named
  diagnostic. `bound` means the manager reads the bytes deliberately and
  completely. `inert` means the bytes are in the audit subject and the source
  identity, are never opened by the manager, never reach the compiler, and are
  never executed, because no channel in the pipeline names them.

The build-root subtree is partitioned totally:

| Region | Rule |
|---|---|
| inside `Sources` | `.swift` regular files and directories only; everything else rejected (6.2) |
| `<build_root>/Package.swift` | **bound**: first line only (section 3, section 7) |
| inside the build root, matching a rejected name or extension | rejected (6.2) |
| everything else inside the build root | **inert** (6.6) |

### 6.2 Rows decided by snapshot bytes

| Surface | Verdict | Diagnostic |
|---|---|---|
| `Package.resolved` anywhere in the build-root subtree | reject | `build_package_dependency_declaration_forbidden` |
| `Package@swift-*.swift` anywhere in the subtree | reject | `build_package_alternate_manifest_forbidden` |
| `.swiftpm`, `Plugins`, `Snippets` directory anywhere in the subtree | reject | `build_package_plugin_forbidden` |
| native or foreign input anywhere in the build-root subtree, by closed extension list: `.o .a .dylib .so .bundle .framework .c .cc .cpp .cxx .m .mm .h .hpp .modulemap .swiftinterface .swiftmodule .tbd .obj .lib .dll` | reject | `build_package_native_input_forbidden` |
| any non-`.swift` regular file under `Sources` — including a script, a `Makefile` or an executable-bit file | reject | `build_package_native_input_forbidden` |
| any symlink, device, socket or fifo in the build-root subtree | reject | `build_package_unsupported_entry_kind` |
| a compiled source relative path carrying an ASCII control byte | reject | `build_source_layout_invalid` |
| a command key outside `^[A-Za-z0-9][A-Za-z0-9._-]*$` | reject | `build_source_layout_invalid` |
| empty compiled source set | reject | `build_source_layout_invalid` |
| missing `Package.swift`, missing `Sources`, `source_dir` ≠ `build_root` | reject | `build_source_layout_invalid` |

Outside `Sources` the native-input list would be inert bytes. It is rejected
anyway, for the same reason as `Package.resolved`: its presence declares an
intent the driver cannot honour, and naming the mismatch at the boundary is
better than building something the author did not describe.

### 6.3 Rows decided by the graph-phase plan

| Surface | Verdict | Diagnostic |
|---|---|---|
| a plan line the section 4.1.1 grammar does not cover — unmatched quote, dangling backslash, control byte, blank line, non-absolute first token | reject | `build_execution_control_unavailable` |
| a flag with a missing or empty value; an `-external-plugin-path` value that is not `<dir>#<server>`; a `#` in a single-path plugin flag | reject | `build_execution_control_unavailable` |
| a job executable or `-new-driver-path` value outside the `swift-toolchain` root | reject | `build_execution_control_unavailable` |
| a plugin path that exists outside every fingerprinted root, or a dangling symlink | reject | `build_execution_control_unavailable` |
| a search path outside every fingerprinted root, or absent | reject | `build_execution_control_unavailable` |
| an output path outside operation-private manager state | reject | `build_execution_control_unavailable` |
| a source token that is not byte-equal to a manager source-set member | reject | `build_execution_control_unavailable` |
| **any token no table of 4.1.2 claims** — an unknown flag, an unknown joined `-flag=value`, an unexpected positional operand, an `@`-leading response file, an empty token | reject | `build_execution_control_unavailable` |
| an opaque value that is path-shaped, embeds `/`, `\` or `#`, fails its charset, or is not the constant the manager chose | reject | `build_execution_control_unavailable` |
| a `-Xllvm` or `-Xcc` value outside the platform's measured allow-set | reject | `build_execution_control_unavailable` |
| a binding whose resolution or identity changed between graph and permit; an absent plugin path that appeared | reject | `build_execution_control_unavailable` |
| an empty plan, or a non-zero graph command | reject | `build_execution_control_unavailable` |
| **every macro/plugin load channel in the plan** — `-plugin-path`, `-external-plugin-path`, `-in-process-plugin-server-path`, `-load-plugin-library`, `-load-plugin-executable`, `-load-resolved-plugin`, `-cas-plugin-path`, `-cas-plugin-option`, joined `-load-pass-plugin=` | the path bucket applies: inside a fingerprinted root or absent, or reject. The **load** is rejected at Stage B instead, by 3.3, because no admitted source can name an implementation | `build_execution_control_unavailable` for the path; `build_package_code_execution_forbidden` at Stage B for the selection |

### 6.4 Rows decided by the fixed vectors and environment

| Surface | Verdict | Why it cannot occur |
|---|---|---|
| any SwiftPM invocation | reject | the two vectors of section 4 are the whole command set |
| `Package.swift` body — targets, products, dependencies, `unsafeFlags`, `swiftSettings`, `linkerSettings`, `cSettings`, plugins, macro targets, binary targets, system-library targets, prebuild and postbuild commands, manifest `#if` | reject as an input | the manager's read stops at the first `LF` (section 3); the file is excluded from the source set; and neither command shape has a flag member |
| a package-supplied compiler or linker flag, by any channel | reject | neither command shape has a flag member |
| a response file — an `@`-leading argument | reject as unreachable | measured that `swiftc` honours `@file`, and measured that a source named `@resp.swift` reaches the compiler as an absolute path and is compiled. No vector member begins with `@` |
| a build configuration selector — debug/release, `-Onone`, `.xcconfig`, `.xcodeproj`, a scheme | reject as unreachable | the compile vector fixes `-O`; no configuration member exists; none of those files is compiler-visible |
| a script outside `Sources` — `.sh`, `Makefile`, a hook, an executable-bit file | inert | no channel names it: the process graph is fixed, `PATH` is an empty directory, and section 4.1 rejects any executable it does not already account for |
| `-import-objc-header`, `-Xcc`, `-Xfrontend`, `-Xllvm`, `-Xlinker`, `-I`, `-L`, `-l` | reject | absent from both vectors |
| network access, dependency resolution, registry access, git fetch | reject | no network-capable command exists in the pipeline; `PATH` is an empty directory |
| package-selected toolchain path, root, channel, mirror, installer, version manager | reject | decision 0007 resolution; `.swift-version` is classified, not honoured |
| cross-compilation, non-native `-target` | reject | the compile vector fixes `-target` |

### 6.5 Admitted surfaces

| Surface | Bound |
|---|---|
| `import` of a module the presented SDK exposes | the SDK is a fingerprinted data root; **measured** that importing a macro-bearing module without using a macro loads nothing |
| the standard library, `Foundation`, `Codable` and `Sendable` conformances, `actor`, `async`/`await`, generics, bare regex literals, string interpolation, multi-line strings, custom operators, Unicode identifiers | measured to carry neither sigil byte and to build under the contract vectors |

`#if` conditional compilation, `@_cdecl` and `@_silgen_name` were admitted as
bounded in the previous revision and are **no longer admitted**: section 3.3
rejects them as collateral, and section 11 records the change rather than
dropping it.

**No macro is admitted.** Not an external one, not a platform one, and not one
whose implementation ships inside the fingerprinted toolchain. The rejection is
at Stage B, from the source bytes, before any command starts — section 3.3 —
because under a one-compile-command policy the manager cannot edit the frontend
jobs. It does not depend on the compiler failing to find an implementation.

The failure a package author sees is therefore a **manager** diagnostic naming a
file and a byte offset, not a compile error:
`build_package_code_execution_forbidden` /
`swift_source_macro_selector_forbidden`. **Measured**: `@Observable` is rejected
at offset 19 on byte `0x40` and `#Predicate` on byte `0x23`, each with **0**
manager-started commands and no artifact. Section 12 of decision 0011 states
this narrowing as the authoring consequence it is.

### 6.6 Inert bytes

Files inside the build root, outside `Sources`, that no row above rejects, and
that are not `Package.swift`: `README.md`, `LICENSE`, `.gitignore`, a resources
directory, `Tests`, a `.editorconfig`, a CI configuration.

They are **inert**, which is a precise statement rather than a shrug:

- they are inside the audit subject and inside `curator-build-source-v1`, so
  they are identified and reviewable;
- the manager never opens them — the only files it reads are the compiled source
  set and the first line of `Package.swift`;
- they never reach the compiler — the compiler-visible set is exactly the
  ordered source set, and section 4.1's source bucket rejects any token that is
  not byte-equal to one of its members;
- they are never executed — the process graph is fixed (section 2.1), `PATH` is
  an empty directory (section 5), and section 4.1 rejects any executable the plan
  names that is not inside the toolchain root.

---

## 7. Stage B — metadata dispositions

| Source | Field | Disposition |
|---|---|---|
| `Package.swift` | first-line `swift-tools-version` | `classified` (7.2) |
| `Package.swift` | every byte after the first `LF` | not a metadata source and not read at all; rejected as an input by section 6 |
| `.swift-version` | the bare version string | `compared`, decision 0007 channel table |

Evaluation order is Unicode-scalar lexical order of relative source path, so
`.swift-version` precedes `Package.swift`. A snapshot carrying a section 6.2
surface is deterministically a package-influence rejection before any comparison
runs.

`.swift-version` is `compared` rather than `forbidden` because it names a
version, not an origin, and because it is inert against the direct resolution
decision 0007 mandates. Measured: a `.swift-version` of `5.9.9-nonexistent`
beside the sources changed nothing; the compile exited 0.

### 7.1 Curator reads the header itself, and reads only line 1

The manager reads `Package.swift`'s first line as bytes. It MUST NOT invoke
`swift package tools-version` or any other SwiftPM subcommand to do so. That
command appears in this document only as the upstream oracle the classifier is
measured against.

**First line = bytes up to the first `LF`, with one trailing `CR` removed. That
is the classifier's entire input.** No byte after that `LF` is read, scanned, or
able to change the verdict.

This is **deliberately not** the rule of 4.1.1 layer 1, which rejects a bare CR
outright, and the two are not in tension. They read different things from
different producers. `Package.swift` is **untrusted input authored on an unknown
host**, where a CRLF line ending is an ordinary fact about a text file and
rejecting the whole build over it would be a false positive; one trailing CR is
therefore removed, and exactly one, before a byte-exact comparison. The job plan
is **output the trusted compiler just produced on this host**, measured to carry
zero CR bytes, so a CR there is evidence that the read or the producer is not
what the contract assumes — and the fail-closed answer is rejection. Trusted
output is held to a stricter grammar than untrusted input, which is the correct
direction.

Upstream is different, and the difference is measured, not assumed:
`swift package tools-version` reports `9.9.0` with exit 0 for a manifest whose
only specification sits inside a **multi-line string literal** on line 3. A
whole-file scan would therefore let arbitrary manifest body bytes — including
bytes inside a string constant — set the version the manager compares, which is
the exact input this driver exists to exclude. The narrowing is declared as
section 7.3's security partition rather than hidden.

Two nearby cases are **not** narrowings, and both are measured. A canonical line
1 followed by a second specification on line 2 yields `6.0.0` from upstream —
line 1 decides for both. A specification inside a single-line string literal
(`let s = "// swift-tools-version:9.9"`) is found by neither, because the line
does not begin with the comment marker.

### 7.2 Classifier — `swift-tools-version`

Ordered, exhaustive, with a mandatory catch-all. Every rule reads line 1 and
nothing else.

| # | Class | Rule |
|---|---|---|
| 1 | `rejected-absent-header` | **line 1** carries no tools-version specification in any case or spacing form. Whether a later line does is not consulted |
| 2 | `rejected-non-canonical-header` | line 1 carries a specification, but not in the canonical form (see below) |
| 3 | `rejected-missing-specifier` | canonical prefix present, version text empty after trimming |
| 4 | `rejected-grammar` | version text present, fails the grammar, and upstream does not represent it either |
| 5 | `rejected-unsupported-floor` | version < `4.0.0` |
| 6 | `host-gate` | version > the resolved normalized compiler version |
| 7 | `accepted` | otherwise |

Class 1 is the honest name for what happened: *line 1 carried none*. It does not
claim the file carries none, and the manager never learns whether it does.

**Canonical form.** Line 1 matches, whole line:

```
^// swift-tools-version: ?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))?$
```

Exactly two slashes, one ASCII space, the lowercase keyword, a colon, at most
one space, a two- or three-component decimal version with no leading zeros, no
prerelease, no build metadata, nothing after it.

**Grammar** for the version text: two or three decimal components, no component
with a leading zero unless it is `0`, no prerelease, no build metadata.

**Floor**: `4.0.0`. Measured, not assumed: `3.1` is refused by the corroborating
command with `… is using Swift tools version 3.1.0 which is no longer supported…`
and `4.0` is accepted.

### 7.3 The security partition `F`

`F` is the set of forms upstream represents and Curator refuses. It has two
shapes.

**Shape A — line 1 carries the specification, and upstream reinterprets it.**
The compared version differs from the bytes the author wrote.

| Header | upstream normalizes to | Curator |
|---|---|---|
| `//swift-tools-version:6.0` | `6.0.0` | class 2 |
| `// SWIFT-TOOLS-VERSION:6.0` | `6.0.0` | class 2 |
| `//   swift-tools-version:  6.0` | `6.0.0` | class 2 |
| `// swift-tools-version:06.0` | `6.0.0` | class 2 |
| `// swift-tools-version:6.0-beta` | `6.0.0` | class 2 |
| `// swift-tools-version:6.0+build` | `6.0.0` | class 2 |

**Shape B — the specification is below line 1, so Curator never reads it.**

| Manifest | upstream normalizes to | Curator |
|---|---|---|
| `import Foundation` then the header on line 2 | `6.0.0` | class 1 |
| the header only inside a multi-line string literal | `9.9.0` | class 1 |

These eight are `F`. **No member of `F` may classify as `rejected-grammar`**:
calling it a grammar error would assert that upstream refuses it too. Shape A
members classify as `rejected-non-canonical-header`; shape B members classify as
`rejected-absent-header`, which is what Curator actually determined.

**Alignment properties.** P1 (no widening) is asserted over **all** cases:
Curator accepts nothing upstream refuses. P2 (no narrowing) is asserted over
cases **outside** `F`. Measured: both hold, `F` non-empty and enumerated.

A byte-order mark before the header is **not** in `F`: measured, upstream's own
recognition fails on it too and falls back to `3.1.0`, so both refuse it. A
second specification on line 2 below a canonical line 1 is **not** in `F`:
measured, upstream also takes line 1. A specification inside a single-line string
literal is **not** in `F`: measured, neither finds it.

### 7.4 Recognised command outcomes are a closed set

Used only by the conformance probe, which measures Curator's classifier against
upstream. Every line is predicted **before** the command runs, from the value
under test plus constants the probe fixes from the resolved toolchain:
`<full>` = normalized compiler version (`6.3.2`), `<mm>` = its major-minor form
(`6.3`), `<pkg>` = the package directory name, `<raw>` = the version text as
written, `<norm>` = its upstream normalization.

Isolated command — `swift package tools-version`:

| Whole line / condition | Stream | Class |
|---|---|---|
| `<norm>` with exit 0 | stdout | `accepted` |
| `error: the Swift tools version '<raw>' is misspelt or otherwise invalid; consider replacing it with '// swift-tools-version: <full>' to specify the current Swift toolchain version as the lowest Swift version supported by the project` | stderr | `rejected-grammar` |
| `error: the Swift tools version specification is possibly missing a version specifier; consider using '// swift-tools-version: <full>' to specify the current Swift toolchain version as the lowest Swift version supported by the project` | stderr | `rejected-missing-specifier` |
| `error: package 'package.swift' is using Swift tools version 3.1.0 which is no longer supported; consider using '// swift-tools-version: <mm>' to specify the current tools version` | stderr | `rejected-absent-header` |

Corroborating command — `swift build`. Every diagnostic carries a `'<pkg>': `
infix the isolated forms do not, which is why the two sets cannot share one
predictor:

| Whole line / condition | Class |
|---|---|
| exit 0 | `accepted` |
| `error: '<pkg>': package '<pkg>' is using Swift tools version <norm> but the installed version is <full>` | `host-gate` |
| `error: '<pkg>': package '<pkg>' is using Swift tools version <norm> which is no longer supported; consider using '// swift-tools-version: <mm>' to specify the current tools version` | `rejected-unsupported-floor` |
| `error: '<pkg>': the Swift tools version '<raw>' is misspelt or otherwise invalid; …` (as above, with the infix) | `rejected-grammar` |
| `error: '<pkg>': the Swift tools version specification is possibly missing a version specifier; …` (as above, with the infix) | `rejected-missing-specifier` |
| `error: '<pkg>': package 'package.swift' is using Swift tools version 3.1.0 which is no longer supported; …` | `rejected-absent-header` |

Rules:

- recognition is **whole trimmed line equality**; a lead with an unconstrained
  tail and a substring found anywhere are families, not outcomes, and MUST NOT
  be recognised;
- two expected lines of **different** classes matching inside one output is
  `unknown`, not first-wins;
- anything outside the set is `unknown`, yields no verdict, and fails the probe.

**Isolated vs corroborating.** `swift package tools-version` cannot be applying
the host gate: measured, it reports `99.0.0` with exit **0** on a 6.3.2 host
while `swift build` on the same package exits 1 with the host-gate line. The
corroborating outcome is required to be *reachable* from the isolated one — an
`accepted` isolated outcome may become `accepted`, `rejected-unsupported-floor`
or `host-gate` — never equal to it.

### 7.5 Closure is measured, not asserted

Three kinds, both laundering directions reported (A = a fabrication agreeing
with an isolated-accepted value, B = with an isolated-rejected one):

| Kind | Count | What it is |
|---|---|---|
| measured, unrelated | 4 | a real command, a real non-zero exit, nothing about the value |
| measured | 20 outcomes over 338 pairs | every value-bearing outcome classified under every other case's value |
| measured, extended (**constructed**) | 27 | a measured diagnostic with a tail appended, a wrapper in front, or embedded in a longer line |

The third kind is constructed and is labelled so in the fixture: a fail-closed
property is a claim about outcomes no host has emitted yet.

**Exclusions are printed with their reason.** 20 outcomes are excluded from the
cross-feed because they name no value under test: an exit-0 acceptance, a
missing-specifier diagnostic and an absent-header diagnostic. Feeding those
under another value would test the classifier against text that was never about
a value. The exclusion is by *measured property* — the recognised line does not
contain the value — not by an allowlist of case names.

Measured result: 32 emitted rows, **0** yielding a verdict.

### 7.6 Controls required to fail

Each restores a retired defect from the same binary and MUST exit non-zero.

| Control | Guards | Measured findings |
|---|---|---|
| `C1` lead-only recognition | an outcome is a whole line, not a lead | 3 |
| `C2` substring recognition | a diagnostic embedded in a longer line is not that diagnostic | 1 |
| `C3` exit status as semantics | the floor, the host gate and a grammar rejection are not one exit status | 7 |
| `C4` `swift build` as the isolated command | representability is measured by a command that cannot apply the host gate | 3 |
| `C5` unearned `PATH`-closure zero | a zero without a firing control is not evidence | 1 |
| `C6` plugin closure unchecked | the macro plugin surface is inside the fingerprinted closure | 2 |
| `C7` lenient plan parsing | a plan shape the grammar does not cover is a rejection, not a skip | 16 |
| `C8` lexical containment | containment is resolved, not a string prefix | 1 |
| `C9` collapsing module derivation | two distinct command keys never share one module name | 3 |
| `C10` prefix-only banner parser | the compiler banner is matched as a whole value, not by its prefix | 17 |
| `C11` lenient runtime-library admission | the standard-library closure is total, not "whatever is already in the root" | 6 |
| `C12` CR-normalizing plan splitter | LF is the only terminator and a bare CR is a rejection, never a stripped byte | 4 |
| `C13` macro source admitted without Stage B | a compiler macro selected by package source is rejected before the graph phase, not left to fail inside a compile child | 1 |
| `C14` path-shape-only totality | totality is over every token, not over the tokens already recognised as paths | 14 |
| `C15` multi-command compile under v2 | one `manager-worker-v2` session is at most one graph command and exactly one compile command | 3 |
| `C16` compile permit without permit-time re-binding | the single compile command is started only after every binding is re-resolved and re-identified at the permit | 1 |
| `C17` retired permit re-check binding model | a binding re-checks the path whose identity it recorded, and an absent plugin path stays absent only on `ENOENT` | 6 |

`C5` through `C17` are the Swift-specific ones. `C5` reports a zero obtained with
the shim directory off `PATH`. `C6` uses the declared SDK path and reports the 2
distinct live plugin paths it derives outside every fingerprinted root. `C7`
restores the lenient scan and reports that it admits 16 of the 20 malformed
plans of section 4.1.5. `C8` restores lexical prefix containment and reports the
symlink escape it admits. `C9` restores the replacement module rule and reports
that `my-tool`/`my.tool`/`my_tool`, `a.b-c`/`a-b.c` and `9.tool`/`9-tool` each
collapse to one name.

`C14` is the cycle-3 control that survives unchanged: it restores
path-shape-only totality and reports the **14** unknown-channel vectors of 4.1.5
it admits that the closed grammar rejects, including the joined
`-load-pass-plugin=<lib>` and both pass-through carriers.

`C13` and `C15` are the cycle-4 controls, one per finding. `C13` restores the
retired Stage B — no source admission at all — and reports that the
macro-selecting source is then admitted, receives a compile permit, and loads
`libObservationMacros.dylib` from inside the fingerprinted toolchain root under
the contract's own single compile command. `C15` restores the retired
plan-execution design and reports that it starts **4** manager commands for the
default source set where `manager-worker-v2` admits 2, and that it starts
`swift-frontend` and `clang` directly instead of through the driver's trusted
launcher. `C13` keeps its identifier from cycle 3, where it guarded the same
property through a different mechanism; the guard text records the change.

`C16` and `C17` are the cycle-5 controls, one per repair. `C16` restores the
retired session — graph command, plan verification, then straight to
`compile_argv` — and reports that a plugin path verified **absent** may then
appear after verification and the session still starts **2** manager commands.
`C17` restores the retired binding model and reports both of its defects against
the live permit on the same bindings, at the same moment: **5** findings on a
verified happy path where the live permit reports **0**, and **0** findings on an
absent plugin path whose state cannot be established where the live permit
reports **1**. Neither control is a restatement of the review: both restore code
from the same binary and report measured numbers.

`C10` through `C12` are the cycle-2 controls, and each one restores exactly the
rule the reviewer found underspecified. `C10` restores the prefix-only banner
parser and reports the **17** negative banner vectors it admits that the
whole-value grammar of 1.2 rejects. `C11` restores the cycle-1
"entries-already-inside-the-root-must-exist" rule and reports **6 of 6**
runtime-library shapes it admits that the closed rule of 1.3 rejects. `C12`
restores the splitter that made the terminal LF optional and stripped one
trailing CR per line, and reports the **4** plan shapes it admits that the
physical-line grammar of 4.1.1 rejects.

A control that does **not** fail is itself a failure: it means the property it
guards is no longer being checked.

---

## 8. Identity, cache, receipt, marker, claim

The canonical build input binds, in addition to the members decision 0008
section 8 requires of every new driver:

| Member | Value |
|---|---|
| `toolchain_identity` | the whole `curator-swift-toolchain-v1` object of section 2.3, including `manager_invoked`, `linker`, `runtime_library_members`, every root digest and the closure digest |
| `native_target` | `target.unversionedTriple` |
| `source_set` | the ordered relative paths of the compiled source set |
| `command_key` | the consuming manifest command key, verbatim |
| `module_name` | the `curator-swift-module-v1` derivation of section 3.2 |
| `policy` | the closed object below |

`command_key` and `module_name` are both bound, and that is not redundancy. The
module name is what the compiler was given, so it belongs in the input that
identifies the build; the command key is what the protocol keeps distinct.
Binding both means two commands cannot share a cache identity even under a
hypothetical module-name collision, so identity does not depend on the section
3.2 derivation being injective.

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

`execution_policy` is the `const` `manager-worker-v2`. `network: "none"` denotes
the absence of any network-capable command together with the empty `PATH`; it is
**not** a claim of kernel-enforced network denial, which remains the deferred
`total-network-denial` guarantee.

| Artifact | Rule |
|---|---|
| receipt schema 3 | local mode; strict `oneOf` on the `driver` `const`; carries the policy object, the toolchain identity, the native target and the graph-phase `curator-swift-process-closure-v1` object of 2.3 |
| receipt schema 4 | external mode; same shape, plus the external source identity |
| marker schema 4 | records `driver`, `receipt_schema_version` and `execution_policy` per build entry; a reader rejects a `swift-v1` entry claiming `manager-worker-v1` rather than inferring the policy from the driver name |
| claim schema 4 | asserts `swift-v1` / `swift-repository-v1` with `execution_policy` bound by the assertion's own `driver` `const` |

The effective toolchain requirement and the `compatibility` set stay gates, never
build inputs.

---

## 9. Diagnostics

| Code | Stage | Trigger |
|---|---|---|
| `build_toolchain_root_undeclared` | A | no declaration for `swift-toolchain` or `platform-sdk` |
| `build_toolchain_root_unusable` | A | a required closure member (section 2.1) missing, non-executable, or resolving outside the root |
| `build_toolchain_version_undetermined` | A | `compilerVersion` absent, duplicated, not a JSON string, or not matching the whole-value grammar of 1.2; the section 1.2 rejection code is carried as the diagnostic detail |
| `build_toolchain_platform_unsupported` | A | host pair not in `platforms`, or any rule R2.1–R2.7 of section 1.3 rejects; the violated rule number is carried as the diagnostic detail |
| `build_toolchain_metadata_mismatch` | B | `swift-tools-version` classifier classes 2–6, or a `.swift-version` comparison mismatch |
| `build_package_code_execution_forbidden` | B | the shared class for section 6 rejections, and the class for every `curator-swift-source-admission-v1` rejection of section 3.3, raised **before the graph phase**. Swift details beneath it: `swift_source_macro_selector_forbidden`, `swift_source_encoding_forbidden`, `swift_source_unreadable`, each carrying the file path, the rule, the byte offset and the byte |
| `build_package_dependency_declaration_forbidden` | B | `Package.resolved` present |
| `build_package_alternate_manifest_forbidden` | B | `Package@swift-*.swift` present |
| `build_package_plugin_forbidden` | B | `.swiftpm`, `Plugins` or `Snippets` present |
| `build_package_native_input_forbidden` | B | a native/foreign input, or a non-`.swift` regular file under `Sources` |
| `build_package_unsupported_entry_kind` | B | symlink, device, socket or fifo in the subtree |
| `build_source_layout_invalid` | B | layout requirement of section 3 unmet, a control byte in a source path (3.1), or a command key outside the protocol grammar (3.2) |
| `build_execution_control_unavailable` | B | plan verification failed (4.1), a binding changed between graph and permit (4.1.4), or the SDK presentation could not be established (2.2). Swift details beneath it: `swift_plan_token_unclaimed` for a token no table of 4.1.2 claims, carrying the line number and the token; `swift_permit_binding_changed` for every 4.1.4 permit finding, carrying the bucket, the path re-checked and what differed |
| `build_descriptor_driver_unsupported` | B | schema-1 descriptor for an external Swift command |
| `build_descriptor_schema_unsupported` | B | unknown descriptor schema version |
| `build_artifact_class_unsupported` | B | the platform cannot produce a single self-contained executable |

Each MUST remain distinguishable from the others, from a cache hit, from an
audit success, from source unavailability, and from a generic fallback.

---

## 10. Artifact

| Property | Measured |
|---|---|
| shape | `Mach-O 64-bit executable arm64` |
| dynamic dependencies | `/usr/lib/libSystem.B.dylib`, `/usr/lib/libobjc.A.dylib`, `/usr/lib/swift/*`, `/System/Library/Frameworks/Foundation.framework/…` — all base-installation |
| signature | `adhoc, linker-signed`, applied by `ld` during linking |
| runs | yes |

The signature is compiler output, not a manager signing step: it is produced by
the fixed vector, selects no identity, credential or notarization, and reaches
no network. The manager performs **no** post-build signing. A platform policy
requiring a locally signed binary waits for the separately reviewed signer
profile.

Published as `bin/<command>` or `bin/<command>.exe`, derived solely from the
consuming manifest command key.

**Reproducibility, stated precisely.** Measured: two compiles of the same sources
to the **same** output path are byte-identical; changing only the output path
changes the bytes, because the path reaches the Mach-O `LC_UUID`. Identity is
input-keyed, as decision 0008 section 3 requires. This is **not** a
reproducible-build claim, and a manager whose staging path varied per operation
would produce different bytes for the same inputs.

Every other compiler product — object files, `.swiftmodule`, `.swiftdoc`,
`.swiftsourceinfo`, `.dSYM`, dependency files — stays in operation-private
staging and is discarded with it. Measured: the compile phase writes nothing
into the source directory.

The manager MUST NOT execute the artifact, for validation, version discovery,
smoke testing, post-processing, receipt generation, rollback, or any other
reason.

---

## 11. Residual exposures

- **Macro expansion is not an exposure, because no admitted source can select
  one.** Section 3.3 rejects both spellings at Stage B, before any command runs,
  and the compiler itself is the evidence that both spellings need one of the two
  rejected bytes. This is stated here to record that the cycle-2 contract's
  "toolchain macros run inside the compiler" exposure has been **closed**, not
  restated.
- **The plugin search paths remain in the plan.** This is the honest form of the
  entry above. `swiftc` injects them into its own frontend jobs, and under a
  one-compile-command policy the manager cannot remove them: doing so requires
  starting the jobs itself, which `manager-worker-v2` does not admit. What is
  measured is that they are **inert** for an admitted source set — 5 components
  in the plan, 0 load remarks — and that every one resolves inside a
  fingerprinted root or is absent (4.1.3). The residual is a toolchain that
  begins loading a plugin with no source-side selector; nothing in this pipeline
  would stop that. Bounded by the closure check, not eliminated by it.
- **The compile phase re-derives its own plan.** The manager verifies the plan
  `graph_argv` printed, then runs `compile_argv`. Both come from one program over
  one source set in one environment and differ by one inserted token, and every
  bound path is re-resolved and re-checked at the permit (4.1.4) — but the
  processes inspected are not literally the processes that run. The retired
  cycle-3 design had the stronger property and paid for it with a session shape
  the accepted execution policy does not admit. Closing this properly needs a new
  execution-policy identity, which is a decision 0008 change, not this document's.
- **The permit narrows the mutation window; it does not remove it.** 4.1.4 runs
  immediately before `compile_argv`, so a write that lands between the permit and
  the compile child's own `open` is not caught by it. That window is bounded by
  ownership (section 2.1) rather than by a check, and the honest statement is
  that the permit turns "the graph phase verified this at some earlier time" into
  "nothing observable changed up to the moment the command was started". Closing
  the last interval needs the compiler to accept content-addressed inputs, which
  is not a property this toolchain offers.
- **Compile-time filesystem reads are bounded, not proven absent.** The admitted
  language has no `include_str!` analogue. The surfaces checked and excluded are
  `-import-objc-header`, `-Xcc -include`, module maps, bridging headers and
  `.swiftinterface` inputs. With macro selection removed, the largest remaining
  read surface is the compiler front end itself, which is a bounded statement
  about the surfaces enumerated rather than a proof that none exists.
- **Foreign symbol declarations are no longer reachable.** The previous revision
  admitted `@_silgen_name` and `@_cdecl` as bounded. Both begin with `0x40`, so
  section 3.3 now rejects them outright; the entry is kept so the narrowing is
  recorded. What remains admitted is `import` of a module the presented SDK
  exposes, and the artifact still depends only on base-installation libraries.
  Not a claim that the produced program is safe.
- **Ordinary compiler-input exposure.** Resource-consumption denial of service
  and compiler vulnerabilities reached by adversarial source, bounded by the
  parent-enforced deadline, output and artifact limits, and whichever
  native-control inventory entries the host provides. The six deferred hardened
  guarantees are not claimed, named as controls, or implied.

---

## 12. Platform matrix and qualification

| Platform | Status |
|---|---|
| macOS arm64 | measured on one host; enters a claim only via `TASK-260728-2bu2q6` |
| macOS amd64 | qualification obligation |
| Windows | implementation contract only, **no** claim |
| Linux | excluded until `TASK-260728-1y8u4m` |

### 12.1 The acceptance test

Identical on every candidate platform. All nine MUST hold:

1. **Poisoned `PATH`, pinned run**: the pinned build exits 0 with **zero**
   resolutions against a shim directory covering every plausible tool name.
2. **Firing control**: the same harness, with a linker named rather than
   defaulted, produces at least one resolution. *Without this the zero is
   unearned and MUST NOT be accepted.*
3. **Closure members**: the structural rule of section 2.1 holds — every
   executable the verified plan names, plus the linker `clang -print-prog-name`
   resolves, resolves inside the `swift-toolchain` root, following symlinks. The
   member set is read off the plan on that host and recorded; it is not asserted
   in advance. `swift` is not a member.
4. **Plan verification**: section 4.1 passes on that host — the closed grammar
   accepts the emitted plan with 0 rejections, **every** token is claimed by a
   table, and both negative families of 4.1.5 all reject. The platform's
   per-kind nullary set and its `-Xllvm` / `-Xcc` value allow-sets MUST be
   **measured on that host** and written into 4.1.2 before qualification; a host
   whose plan carries an unmeasured token fails closed until it is.
5. **Artifact**: the produced executable's dynamic dependencies are all
   base-installation libraries of the declared platform baseline, and it runs.
6. **Version rule**: `compilerVersion` matches the whole-value grammar of
   section 1.2 — the whole value, suffix included — or the grammar is extended
   by measurement first.
7. **Runtime-library closure**: probe P2 is run with the exact compile triple
   and rules R2.1–R2.7 of section 1.3 all hold, with the platform's
   `base_installation_prefixes` **measured on that host** rather than carried
   over. A platform whose prefix set is unmeasured has an empty set, so every
   out-of-root runtime path rejects and the platform simply does not qualify
   yet.
8. **Identity serialization**: every closure member, the P3-resolved linker and
   every declared root serialize through `curator-swift-relpath-v1` (2.4) with
   no absolute path, no native separator and no volume prefix, and the
   graph-phase `curator-swift-process-closure-v1` object is recorded from the
   plan that was actually verified.
9. **Session shape and channel inertness**: section 4.2 holds on that host —
   the manager starts exactly **2** commands, `swiftc -###` then `swiftc`, and
   starts nothing else; ordinary admitted Swift still builds and the artifact
   runs; and an admitted source set compiles with **0** macro-load remarks under
   that host's own remark flag while the plan still carries plugin components.
   Section 3.3 is platform-independent and needs no per-host measurement: it
   reads bytes.

### 12.2 Windows implementation contract

No claim is made. An implementation MUST satisfy 12.1 with a Windows shim set
covering at least `link.exe`, `lld-link.exe`, `cl.exe`, `clang.exe`, `ld.exe`,
`swift-plugin-server.exe`, `where.exe` and `vswhere.exe`; MUST bind whatever the
Windows toolchain needs to link against the base installation as one or more
data-only `platform-sdk` roots through the two declaration channels, presented
per section 2.2; and MUST NOT resolve `link.exe`, `cl.exe`, `vswhere.exe` or a
Visual Studio activation script from `PATH`, the registry or an environment
variable, answer the gap with a host-resolved tool or a downgraded control, or
record a platform claim from a cross-compiled or emulated run.

An implementation MUST additionally measure, on that host and before
qualification, the per-kind nullary flag set and the `-Xllvm` / `-Xcc` value
allow-sets of 4.1.2, and MUST measure the channel-inertness result of 4.2.3 —
a Windows plan carrying a token or a value this document has not measured fails
closed until it is added by measurement. An implementation MUST NOT answer an
awkward Windows plan by executing the plan's jobs from the manager; that is the
design expected-red control `C15` exists to reject.

**The Windows closure member count is not asserted here.** The expected shape is
`usr\bin\swiftc.exe`, `swift-frontend.exe`, `clang.exe` and the resolved linker,
matching the macOS four — but the plan on that host is unmeasured, and Linux was
measured to add a fifth member (**M3**), so the count is evidently
platform-determined. An implementation MUST take the member set from the plan it
verifies under 12.1 step 3, and MUST record it in
`curator-swift-process-closure-v1` (2.3), rather than reading a count out of
this paragraph. `swift.exe` is not a member on any platform, for the section 2.1
reason: the driver never invokes it.

**What is fixed now, so the count being unmeasured blocks nothing else.** Every
serialization question the member count touches is answered by rules that do not
depend on it:

| Question | Fixed by | Windows value |
|---|---|---|
| the P3-resolved linker relpath when it is not `usr/bin/ld` | 2.4 serialization + 2.3 `linker` member | whatever P3 answers, serialized by the same function; the `.exe` extension is part of the final component |
| additional plan-derived executables | 2.3 `curator-swift-process-closure-v1`, `invoked` and `resolved` projections | taken from the verified plan, ordered and deduplicated by 2.4 |
| multiple SDK roots — naming, order, presentation, hashing | 2.4 ordinal rule and 2.2 presentation | role token `platform-sdk[<ordinal>]`, ordinal by declaration order, one presentation chain per ordinal under `<staging>/sdk/<ordinal>/`, one `roots` entry per ordinal in ordinal order |
| the `link_support_roles` registry value | the 2.4 cardinality table | `platform-sdk`, `one-or-more`, `data_only: true`, `qualified: false` |
| the closed root-role/member schema `TASK-260728-251p01` mints | 2.3 and 2.4 | the `roots` / `manager_invoked` / `linker` / `runtime_library_members` / process-closure shapes, `role_token` from the closed set of 2.4 |
| the physical-line grammar of the plan | 4.1.1 layer 1 | LF-only, mandatory terminal LF, bare CR rejected; stdout MUST be read as a binary stream with no newline translation |
| `base_installation_prefixes` | 1.3 R2.7 and the registry entry | **empty until measured** — so an out-of-root runtime path rejects rather than being waved through |

Two things remain genuinely **unmeasured** and are named as obligations rather
than filled in: the plan-derived member **count**, and the per-platform
**argument template** for any SDK root beyond ordinal 0 (2.4).

Reason the claim is withheld: `TASK-260729-rhjxtx` measured **no Swift toolchain
on the reachable Windows host** (**M4**, 19 cases `not_run`), so the `PATH`
property, the linker resolution and the plugin closure are all unmeasured there.

### 12.3 Linux qualification rules

12.1 plus three Linux-specific questions this host cannot answer:

1. the linking vector was measured (**M3**) to require `swift-autolink-extract`,
   a **fifth** executable beyond the macOS four, which must be shown to resolve
   inside the fingerprinted root and to appear in the verified plan;
2. the open-source toolchain banner is not admitted by the section 1.2 grammar,
   so a Linux qualification must measure that form and extend the grammar, or be
   rejected. It must not be extended speculatively;
3. `base_installation_prefixes` is **empty** for Linux. A distribution that ships
   a Swift runtime outside the toolchain root would return a class-C
   `runtimeLibraryPaths` entry and fail R2.4, and the repair is to measure that
   distribution's prefix and declare it — not to widen the class.

---

## 13. Conformance vector inventory

Owned by `TASK-260728-251p01` at admission time; enumerated here so the shape is
fixed before a vector exists.

| Group | Positive | Negative |
|---|---|---|
| manifest schema 8, local command | 2 | 8 — `swift-v1` while reserved; unknown driver; `source_dir` ≠ `build_root`; extra command member; `build_root` of `.`; missing `build_roots` entry; duplicate command key; `manager-worker-v1` claimed |
| descriptor schema 2, external target | 2 | 6 — `swift-repository-v1` against schema 1; unknown schema version; extra target member; `source_dir` ≠ `build_root`; unknown driver; missing target |
| receipt schema 3 / 4 | 4 | 12 — wrong `execution_policy`; missing policy member; extra policy member; missing root in the identity; a path-bearing identity member; wrong role token; role order swapped; missing `closure_sha256`; versioned triple as `native_target`; source set out of order; `module_name` not the 3.2 derivation of `command_key`; `command_key` absent |
| marker schema 4 | 2 | 4 — `swift-v1` with `manager-worker-v1`; missing `receipt_schema_version`; unknown driver; policy inferred from the driver name |
| claim schema 4 | 2 | 4 — claim for a platform outside `platforms`; `execution_policy` not bound by the `driver` `const`; reserved identifier asserted; unmeasured banner form asserted |
| `swift-tools-version` classifier | 10 | 14 — one per class 1–6, plus each of the eight `F` forms. The positives add the three agreement cases of 7.1: later specification ignored, single-line string literal found by neither, one canonical form per class |
| module name (3.2) | 12 | 8 — a key outside the protocol grammar; a leading `.`, `-` or `_`; an empty key; a non-ASCII key; a `Sk_` result for an overlength key; a `Tk_` result for a short key; a collapsed `my-tool`/`my.tool` pair; a name outside `^[A-Za-z_][A-Za-z0-9_]{0,63}$` |
| plan token grammar (4.1.2–4.1.5) `PV01`–`PV36` | 1 | 36 — the 20 path-and-line families and the 16 unknown-channel families enumerated in 4.1.5 |
| source admission (3.3) `SA01`–`SA20`, `SR01`–`SR22`, `SE01`–`SE10` | 20 | 32 — 22 selector-byte rejections asserting the exact byte and offset, and 10 encoding rejections each of which carries **no** raw sigil byte |
| session cardinality (4.2) `XV01`–`XV04` | 1 | 4 — a second compile command; a manager-started plan job; a manager-started frontend or linker; a retry after a non-zero compile |
| compile permit (4.1.4) `CP01`–`CP08` | 1 | 8 — a compile command reached without the permit; an absent plugin path created after verification; an absent plugin path whose re-resolution fails with anything other than `ENOENT`; an admitted source whose bytes change; an admitted source replaced by rename; a bound executable whose bytes change; a search or SDK binding re-pointed; the recorded output parent replaced. The positive is the happy path: the permit runs over every plan binding and every admitted source, reports nothing, and only then is the compile command started |
| plan physical-line grammar (4.1.1 layer 1) `LV01`–`LV12` | 1 | 12 — the empty plan; no terminal LF; `CRLF`; a bare CR before the terminator; a bare CR mid-line; a trailing blank line; a leading blank line; a blank line between jobs; an embedded NUL; an embedded TAB; an embedded DEL; a line past the 64 KiB bound |
| compiler banner (1.2) `BV01`–`BV32` | 4 | 28 — one per rejection code of 1.2, with both named cycle-1 disagreements (`()` and an unparenthesised trailing byte) and the full byte-class family (LF, CR, NUL, TAB, DEL, non-ASCII) |
| runtime-library admission (1.3) `RV01`–`RV10` | 1 | 10 — an empty list; a relative entry; an absent in-root entry; a dangling symlink; a regular file; an out-of-closure directory; a symlink escaping every root; a base-installation-only list; a base prefix declared inside a fingerprinted root; an empty entry |
| relpath serialization (2.4) `SV01`–`SV06` | 3 | 6 — an ancestor; a sibling sharing a lexical prefix; a case variant; an unresolved `..` component; an empty root; an empty member |
| vector relation (4) `VV01`–`VV05` | 1 | 5 — no insertion; inserted twice; appended instead of inserted; present in the compile vector; a second token co-mutated under cover of the insertion |
| layout | 2 | 11 — one per section 6.2 row |

Every negative MUST fail with the exact section 9 code, never with a generic
schema error. For the 1.2 and 1.3 groups the diagnostic MUST additionally carry
the specific rejection code or rule number, so a vector asserts on the reason
rather than on a boolean.
