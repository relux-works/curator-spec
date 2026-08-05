# Decision 0010: Kotlin artifact model and the `kotlin-native` driver pair

Record numbers 0007 and 0008 are taken by accepted sibling records that have not
yet landed on `main`; 0009 is claimed concurrently by `TASK-260728-12pnm1`
(Rust) and `TASK-260728-1jafds` (hardened execution profile). This record takes
0010 so that the set can land in any order. If a lower free number is available
when this record lands, it renumbers rather than contests, exactly as
`TASK-260728-2spy93` did when 0007 was claimed.

## Context

Decision 0008 reserved six additional-language driver identifiers, two of them
Kotlin — `kotlin-native-v1` and `kotlin-native-repository-v1` — and made
`TASK-260728-168smo` responsible for one thing the other two language contracts
did not have to answer:

> `TASK-260728-168smo` additionally decides the Kotlin backend **within**, not
> around, section 3; if no Kotlin backend satisfies it, both Kotlin identifiers
> are retired unused.

Decision 0008 section 3 admits exactly one artifact class,
`native-executable-v1`: one bounded regular file, named solely by the manager,
directly executable by the host program loader using only base-installation
libraries, never executed by the manager. Its section 6 item 3 additionally
requires every executable started below the worker to be a fingerprinted member
of the driver's declared trusted toolchain closure, and states that a
host-resolved tool outside the closure is not admissible.

Decision 0007 reserved the `kotlin` toolchain entry and the companion-only `jdk`
identifier, requires the primary executable to be a regular executable at the
entry's fixed relpath inside the tree being fingerprinted, admits exactly two
resolution origins, and — in section 1.3 — obliges this task to supply **every**
registry field on a **qualified host**, including the `compatibility` family
granularity and its initial tested set.

This record is at revision 4. Revision 1 was written without a Kotlin/Native
distribution on any reachable host and review cycle 1 disproved three of its
load-bearing assumptions. Revision 2 replaced the trusted-root model with an
operator-curated bundle and measured the Apple toolchain path closed, but left
`platforms` and `compatibility` empty, so review cycle 2 correctly refused it as
a reservation rather than an implementable contract. Revision 3 obtained a
root-capable Windows host and ran the host-side acceptance requirements end to
end, filling every registry field from that run — but it then described the
tuple as qualified and the platform retirement branch as closed, which its own
section 12 contradicts, because A8 and A9 are corpus requirements that no run
has discharged.

**Revision 4 corrects two claims and changes nothing that was measured.**
`windows/amd64` is stated as what the evidence supports: an **A1–A7
host-qualified candidate**, whose `platforms` and `compatibility` values are
admitted by `TASK-260728-251p01` when the conformance corpus discharges A8 and
A9, with both retirement branches armed until then. And the normative Windows
base-installation library allow-list is the measured two-entry set
`{KERNEL32.dll, msvcrt.dll}` everywhere; revision 3's obligation table carried a
wider four-entry set that no measurement supports, and it is corrected down, not
justified. Every A1–A7 measurement, the bundle model, the process trace, the
`PATH` and offline evidence, the artifact evidence and the macOS exclusion are
retained unchanged.

Evidence marked **MEASURED (win)** was taken on Windows 10 Pro 10.0.19045.6456,
AMD64, against the checksum-verified official release
`kotlin-native-prebuilt-windows-x86_64-2.4.10.zip`
(`ce99eba1…380f`, equal to the published `.sha256` asset) and the
checksum-verified Eclipse Temurin `jdk-21.0.11+10`
(`d3625e7c…0a64`, equal to the Adoptium API checksum). Evidence marked
**MEASURED (mac)** was taken on macOS 26.5 arm64 against
`kotlin-native-prebuilt-macos-aarch64-2.4.10.tar.gz` (`55ded039…ed9d`). Argv and
real exit codes are in `TASK-260728-168smo_command-evidence-cycle3.log`
(Windows records W1–W17 and macOS corrections C1–C3) and in the retained
cycle-2 record `TASK-260728-168smo_command-evidence.log`.

The complete implementation-ready reference is
[`docs/kotlin-native-build-drivers.md`](../docs/kotlin-native-build-drivers.md).

This record defines no schema file, regenerates no vector, creates no release
metadata, and advances no pin. Both identifiers remain reserved until
`TASK-260728-251p01` admits them; nothing here puts them on the wire.

## Decision

### 1. The artifact model: Kotlin/Native, and it is measured

**MEASURED, and therefore DECIDED.** The Kotlin family is admitted through the
Kotlin/Native backend producing a single native executable, or not at all. The
question decision 0008 section 10 asks — does *any* Kotlin backend satisfy
section 3 — is answered in the affirmative by produced artifacts on two
platforms rather than by argument:

```text
MEASURED (win)  konanc -produce program -target mingw_x64  -o out\app src\main.kt   exit 0
                out\app.exe   570,368 B   PE, machine 0x8664 (AMD64), runs, exit 0
MEASURED (mac)  konanc -produce program -target macos_arm64 -o out/app src/main.kt  exit 0
                out/app.kexe  785,672 B   Mach-O arm64, runs, exit 0
```

One bounded regular file, directly loadable, no runtime to install, no launcher,
no classpath. Every Kotlin/JVM shape remains rejected, and the rejection is a
consequence of section 3 rather than a preference:

| Candidate | Published files | Directly loadable | Verdict |
|---|---|---|---|
| Kotlin/JVM thin JAR plus operator-installed JRE | 1 | no — needs a JVM and a classpath | rejected: `runtime-bundle` |
| Kotlin/JVM fat JAR (`-include-runtime`) | 1 | no — still needs a JVM | rejected: `runtime-bundle` |
| Kotlin/JVM plus `jlink`/`jpackage` runtime image | many | launcher plus runtime tree | rejected: `runtime-bundle` |
| Kotlin/JVM plus GraalVM `native-image` | 1 | yes | rejected: see rejected alternatives |
| **Kotlin/Native `-produce program`** | **1** | **yes, measured** | **selected** |

The fat JAR keeps its explicit row because it is the shape most often described
as self-contained. It is one file and still fails section 3's third bullet. One
file is necessary and not sufficient.

A future Kotlin/JVM driver, if a `runtime-bundle` profile is ever reviewed and
accepted, MUST use a different family segment and MUST NOT reuse either
identifier reserved here, exactly as decision 0008 section 2 requires.

### 2. Identifiers, and no new names

**DECIDED.** This record coins no identifier. It adopts, unchanged, the two
names decision 0008 section 2 reserved:

| Driver | Source mode | Receipt schema | Execution policy | Status |
|---|---|---|---|---|
| `kotlin-native-v1` | local snapshot | 3 | `manager-worker-v2` | reserved; one A1–A7 host-qualified candidate tuple |
| `kotlin-native-repository-v1` | external repository | 4 | `manager-worker-v2` | reserved; one A1–A7 host-qualified candidate tuple |

Reservation is not admission, and neither is host qualification. Until
`TASK-260728-251p01` moves them in the same change that mints the schema
admitting them, every schema MUST reject both and a manager MUST treat both as
unknown drivers. Section 12 fixes the conditions under which they are instead
retired unused; both of them are still armed.

### 3. The trusted root is an operator-curated bundle, not the vendor archive

**MEASURED — the vendor archive cannot be the toolchain root, on either
platform.** Every entry in `<dist>/bin` is a script: seven Bourne-Again shell
scripts on macOS, and on Windows those seven plus six `.bat` wrappers, 13
entries in total. **MEASURED (win)**: the Windows distribution contains **zero**
files matching `*.exe` anywhere. The compiler is one JAR,
`konan/lib/kotlin-native-compiler-embeddable.jar`. There is no regular
executable in either distribution, so decision 0007 section 3 cannot be
satisfied by it. `run_konan.bat` additionally resolves `java` by name from
`PATH` unless `%JAVA_HOME%` says otherwise, appends `-D` and `-J` arguments to
the JVM, and honours `_TOOL_CLASS` to select the compiler main class: a wrapper
taking environment-selected pipeline inputs, which decision 0007 section 3 and
decision 0008 section 6 item 3 both forbid.

**DECIDED — `curator-kotlin-bundle-v1`.** The `kotlin` toolchain root is an
operator-curated tree with a fixed layout, resolved through decision 0007's
second admissible origin — trusted operator configuration in manager-owned,
owner-protected state — and fingerprinted whole:

```text
<kotlin_root>/                                  immutable, fingerprinted whole
  jdk/
    bin/java.exe        (bin/java on Unix)              <- primary_relpath
  kotlin-native/                                the unpacked official distribution
    konan/lib/kotlin-native-compiler-embeddable.jar
    konan/konan.properties
    klib/…
  konan-data/                                   the prehydrated dependency closure
    dependencies/<name>/…
    dependencies/.extracted                     REQUIRED
```

Five properties follow, and each answers one review finding:

1. **The primary executable is real.** `jdk/bin/java.exe` is a regular
   executable at a fixed relpath inside the tree being fingerprinted — decision
   0007 section 3 satisfied literally. **MEASURED (win)**: 50,344 B, ordinary
   file attributes, no reparse point, exec-verified after the tree was made
   write-denied.
2. **There is no companion.** Because the JDK is inside the primary root, the
   companion list is **empty**, `toolchain_identities` is a one-element array,
   and one tree digest covers the entire executable closure. The `jdk`
   identifier reserved by decision 0007 is **not used** and stays reserved with
   no entry and no driver mapping.
3. **The dependency closure is inside the fingerprint.** The Kotlin/Native
   compiler needs LLVM, a target toolchain, a sysroot and per-target extras that
   the release archive does not contain. **MEASURED (win)**: a first run
   downloads exactly four (`lldb-2-windows` 54,796,930 B,
   `msys2-mingw-w64-x86_64-2` 135,111,082 B,
   `llvm-21-x86_64-windows-essentials-150` 275,594,763 B,
   `libffi-3.3-windows-x64-1` 111,136 B) from `download.jetbrains.com`, with no
   integrity check reported by the compiler. Hydration is therefore an
   **operator act performed once, outside any Curator operation**, and its
   result is inside the fingerprinted tree. The manager never downloads a
   dependency, at any time, in any mode.
4. **The closure includes `dependencies/.extracted`, and that is not a
   detail.** **MEASURED (win)**: with every dependency directory present but
   `.extracted` deleted, the compile fails `Cannot find a dependency locally:
   lldb-2-windows` with exit 2 and no download; restoring the file — 103 bytes,
   four dependency names, LF-separated with a trailing LF — makes the identical
   compile exit 0. Curation MUST keep it and the operation-private overlay MUST
   carry a copy of it.
5. **Provenance is the operator's, and the manager proves only stability.** The
   manager reads no bundle descriptor and MUST NOT: a manifest inside the root
   describing the root would be a second trust input the manager cannot verify.
   The identity is decision 0007's — algorithm identifier, normalized native
   version, primary-executable relpath, tree digest — and it proves the tree is
   stable across and identical between operations, not that it is genuinely the
   vendor's. **MEASURED (win)**: the curated bundle is 27,867 files,
   2,456,792,320 B, tree digest
   `63d96ff7c488e713dedbf7029237cfc6cd030ae4c1caf11c8ba2274395badae3`, and that
   digest was reproduced after the tree was disturbed and rebuilt from the same
   inputs — the curation procedure is byte-reproducible, not merely repeatable.

**DECIDED — the process graph, and it is now a complete measurement.**
`manager-worker-v2`'s two lower nodes bind, for both Kotlin drivers, to:

```text
manager parent
  -> identity-verified manager-owned worker
       -> <kotlin_root>\jdk\bin\java.exe               (the trusted launcher)
            -> the Kotlin/Native compiler, in-process in that JVM,
               loaded by -cp from <kotlin_root>\kotlin-native
                 -> <kotlin_root>\konan-data\dependencies\
                      llvm-21-x86_64-windows-essentials-150\bin\clang++.exe
                 -> …\bin\ld.lld.exe
```

**MEASURED (win)** under an ETW `Microsoft-Windows-Kernel-Process` trace with
the `WINEVENT_KEYWORD_PROCESS` keyword, which records **every** process start in
the window by resolved absolute image path: below the compiler JVM there are
exactly two children, `clang++.exe` and `ld.lld.exe`, both regular files inside
`<kotlin_root>`. No `cmd.exe`, `powershell.exe`, `link.exe`, `cl.exe`,
`lib.exe`, `vswhere.exe`, Visual Studio activation script, or MSYS shell
appears. The trace's completeness control fired: a deliberately external
`where.exe` started in the same window was recorded.

The driver MUST NOT execute `bin/konanc`, `bin/konanc.bat`,
`bin/kotlinc-native`, `bin/run_konan`, `bin/run_konan.bat`, `bin/kotlinc`, or
any other launcher script from any distribution, on any platform, including for
either probe vector.

### 4. The operation-private overlay, and the no-download proof

**MEASURED (win) — a hydrated closure is mutated by a compile in exactly one
place.** A compile against a writable bundle data directory adds exactly one
file, `konan-data/dependencies/cache/.lock`, 0 bytes; removing it restores the
baseline tree digest byte for byte. Everything else in 27,867 files is
untouched.

**MEASURED — the data directory must nevertheless be writable.** With writes
denied the compile fails: `java.io.IOException: Access denied` on Windows,
`FileNotFoundException: …/dependencies/cache/.lock (Permission denied)` on
macOS.

**MEASURED — the overlay closes the gap.** With `<kotlin_root>` write-denied and
`KONAN_DATA_DIR` pointed at an operation-private directory holding one entry per
prehydrated dependency, a copy of `.extracted`, and a fresh **writable** `cache/`
that is *not* a link into the bundle, the compile exits 0, produces the
artifact, and the bundle is byte-unchanged.

**DECIDED.** `KONAN_DATA_DIR` is an operation-private writable overlay,
materialised from `<kotlin_root>/konan-data` by a manager-owned mechanism that
copies or links only, adds no entry that is not in the bundle, reaches no
network, and leaves the fingerprinted root byte-unchanged. The overlay is never
fingerprinted, never published, and is discarded with the operation. The exact
materialisation mechanism is per platform and is fixed by that platform's
qualification: **MEASURED (win)** directory junctions, **MEASURED (mac)** a
symlink farm.

**DECIDED — the driver fails closed rather than downloading.** The compile
vector carries the single manager-owned constant override
`-Xoverride-konan-properties=airplaneMode=true`; the distribution ships
`airplaneMode = false`, so the override is load-bearing. **MEASURED (win)**:
with it, a dependency missing from the data directory is
`Cannot find a dependency locally: <name>` with exit 2 and zero download lines;
the only state it leaves behind is four empty scaffold entries in the
operation-private data directory — `dependencies/`, `dependencies/cache/`, a
0-byte `.extracted` and a 0-byte `cache/.lock` — and no dependency content. This
is an in-process guarantee that does not depend on the network being
unreachable, and it composes with the network denial the acceptance test
requires. **MEASURED (win)** independently: with the closure hydrated and
outbound network denied for the bundle JDK at the host firewall, the compile
exits 0 and logs no download, while the paired control — an empty data directory
with `airplaneMode=false` under the same denial — reports
`java.net.SocketException: Permission denied: getsockopt`, retries ten times
with backoff, and obtains nothing.

### 5. The project-metadata file: `kotlin-native-module.json`

**DECIDED**, unchanged from revision 1, which neither review cycle contested.

Decision 0008 section 4 requires each local driver to bind exactly one closed
**driver-defined** project-metadata file that exists directly in the build root
and is the nearest ancestor of `source_dir`. Decision 0007 section 1.3 requires
the `kotlin` entry to name exactly one file and one field. Kotlin has no such
file, and every ecosystem candidate fails:

| Candidate | Why rejected |
|---|---|
| `build.gradle.kts` / `build.gradle` | Reading it is executing it. `TASK-260729-rhjxtx` measured that the pure metadata query `gradle properties` compiles the build script as a program source unit (`_BuildScript_`) before it can answer. This is the generic Gradle escape hatch the epic exists to refuse. |
| `settings.gradle{,.kts}` | Same class, same measurement. |
| `gradle.properties` | Not executable, but a Gradle input whose `kotlin.*` keys select compiler and daemon behaviour — package-selected build behaviour under a name that merely looks inert. |
| `pom.xml` | Parsable without execution, but the Maven project model is its `<build><plugins>` graph; reading one field while ignoring that graph would let a package ship a plugin declaration Curator silently does not honour. |
| A bare marker file with no field | Fails decision 0007 section 1.3, which requires one file **and** one field. |
| `.kotlin-version` plain text | No schema version, no closure, no way to reject an added line. |

The driver therefore binds a Curator-owned file, which is exactly what
"driver-defined" permits and what `skill-build.json` already establishes as
protocol style for a Curator-owned file inside package-supplied source:

```json
{"schema_version": 1, "kotlin_version": "2.4.10"}
```

Exactly `schema_version` and `kotlin_version`, both REQUIRED,
`additionalProperties: false`. `schema_version` is the `const` integer `1` and
participates in the file-shape gate only. `kotlin_version` is the sole
`metadata_sources` field of the `kotlin` entry: a canonical `major.minor.patch`
triple in decision 0007 section 2.1's grammar, asserting the Kotlin compiler
version the sources are written against. It is never passed to the compiler and
contributes no argument.

Three consequences, each a simplification rather than a special case. The
classifier is two classes rather than seven, because Curator owns the grammar.
The security partition `F` is empty, because a version cannot name where a
toolchain comes from, so decision 0007's P1 and P2 collapse to the satisfiable
equality `C = Upstream`. And the file is inert to the compiler, so deleting it
produces a deterministic Curator rejection and an unchanged compiler.

`source_dir` maps to exactly one compiled program without discovery: the program
is the recursive `.kt` source set under `source_dir`, compiled in `program` mode
with the compiler's default entry point. Zero or multiple entry points is a
compiler error and therefore deterministic; the manager never names, searches
for, or infers one.

### 6. The command surfaces

**DECIDED.** Nothing Kotlin-specific is added to either command shape. The local
command is decision 0008's `buildCommandV8` with `driver` the `const`
`kotlin-native-v1`:

```json
{"type":"build","driver":"kotlin-native-v1","source_dir":"build/cmd/tool",
 "toolchain":{"id":"kotlin","version":{"kind":"at_least","min":"2.4.10"}}}
```

The external command is `repositoryBuildCommandV2` with `driver` the `const`
`kotlin-native-repository-v1`, and the descriptor target is
`skillBuildTargetV2` with the same `const`, `build_root`, `source_dir`, and the
OPTIONAL `toolchain`. `toolchain.id` MUST be `kotlin`; there is no companion to
express and none may be added.

No member is added anywhere. In particular no manifest, descriptor, or metadata
file may express a target, a Kotlin/Native target triple, an entry point, a
module name, a klib, a library, a linker option, an opt-in marker, a language or
API version flag, a compiler plugin, a plugin option, a memory model, a GC
selection, a bitcode or debug setting, a cache mode, a JVM option, a classpath,
a `KONAN_DATA_DIR`, a `konan.properties` override, or a dependency source.

### 7. The pre-compile rejection matrix: an allow-list, not a deny-list

**DECIDED.** Decision 0008 section 7 requires an exhaustive, deterministic,
pre-compile rejection matrix over every package-selected code-execution surface.
Kotlin's surfaces are an open set — a general-purpose script engine, a script
dialect the compiler itself can execute, annotation processing, compiler
plugins, C interop — so an enumerated deny-list could not be exhaustive.

The matrix is a **closed allow-list over the compiler-visible tree**, computed
from the validated immutable snapshot, before the compile phase, by a
manager-side walk that runs no compiler and reaches no network. The build root
and every directory below it admit exactly:

1. directories whose names match `^[A-Za-z0-9_][A-Za-z0-9_.-]*$`;
2. regular files whose names match `^[A-Za-z0-9_][A-Za-z0-9_.-]*\.kt$`; and
3. exactly one additional regular file, `kotlin-native-module.json`, directly in
   the build root and nowhere else.

Every other entry is rejected under `build_package_code_execution_forbidden`.
There is no exception, no opt-out, no advisory mode, and no configuration that
widens it.

**DECIDED — inert directories are admitted, and the contradiction review cycle 2
found is resolved in favour of the classifier.** Revision 2 listed `gradle/`,
`.gradle/`, `.mvn/`, kapt and KSP directories and `META-INF/services` among the
rejected build-system inputs while rule 1 admitted several of them by name
shape. The classifier wins. Because the walk is total, an admitted directory can
contain only admitted directories and `.kt` files, so a directory named
`gradle`, `kapt`, `ksp`, `META-INF` or `services` is admitted **as a container**
and can never carry a build script, a wrapper JAR or properties file, a plugin
service registration, or any other non-`.kt` regular file. Dot-leading names —
`.gradle`, `.mvn`, `.idea` — remain rejected by rule 1's leading-character
class, directories included. The rejection happens at the entry that would carry
executable meaning, never at an ancestor's name.

Adding a build-system directory-name deny-list was considered and refused: it
would be exactly the enumerated deny-list this section rejects for file names —
not exhaustive (`gradle-8`, `Gradle`, `gradle.d`), dependent on a case-folding
and normalization policy the protocol does not define, and closing nothing the
file-level rule does not already close.

**DECIDED — naming a rejection is an ordered, total classification.** The
reference's section 7.2 is a list of ordered rows that choose the per-surface
diagnostic for an entry the allow-list has *already* rejected. No row admits or
rejects anything, the first matching row wins, and the last row is a total
catch-all, so exactly one diagnostic fires for every rejected entry and the
conformance corpus can require a case per row. The rule subsumes, by
construction rather than by enumeration, Gradle and Maven files and wrappers,
`.kts` script sources, kapt and KSP configuration files, `META-INF/services`
registrations, C-interop `.def` files, headers and native sources, objects,
archives and shared libraries, prebuilt `.klib`, `.jar` and `.aar`, every
non-regular entry, every dotfile, and every name beginning with `@`.

**MEASURED on both platforms — the `@` row.** On the native backend:

| Argument token | File on disk | Outcome |
|---|---|---|
| `@inject` | `inject` | expanded — `-version` honoured, exit 0 |
| `@./inject` / `@.\inject` | `inject` | expanded, exit 0 |
| `@/abs/inject` / `@<abs>\inject` | `inject` | **expanded**, exit 0 |
| `/abs/@inject` / `<abs>\@inject` | `@inject` | not expanded — `source entry is not a Kotlin file`, exit 1 |
| `./@inject` / `.\@inject` | `@inject` | not expanded, exit 1 |
| `@nonexistent` | — | `warning: argfile not found` — a warning, not an error |

Expansion is decided by the **first character of the argv token**; the `@` is
stripped and the remainder is the response-file path, absolute or not. So an
absolute package path is safe because it starts with `/` or a drive letter, not
because it is absolute — and a driver that ever prefixed a path with `@` would
reopen the whole surface even in absolute form. A missing response file is a
warning, so a partial mitigation fails silently.

Two independent layers close it, and the contract requires both: the normative
layer is the allow-list, which rejects the name before the compile phase as
decision 0008 section 7 demands; the structural backstop is the argv discipline
of section 8, which never emits a token whose first character is `@`.

The four argv-only plugin surfaces — `-Xplugin=`, `-Xcompiler-plugin=`,
`-P plugin:`, and `-script-templates` — are structurally unreachable, because
the closed command surface gives a package no way to supply an argument and the
driver's vector is fixed. They are named so the matrix is exhaustive over
surfaces rather than over file names, and so that any future change letting
package data reach argv is visibly a change to this paragraph.

### 8. The worker session, the probe vectors, the argument vector, and the environment

**DECIDED — session shape.** A Kotlin operation uses **zero** graph-phase
commands and exactly one compile-phase command. Decision 0008 section 7's "at
most one" graph phase is what admits this: there is no dependency resolution to
perform, because section 7 admits no package-supplied library and section 6
admits no dependency declaration, so the source set is decided by a manager-side
directory walk rather than by asking a tool. The Kotlin compile daemon is
forbidden; no daemon argument is passed and the driver MUST fail rather than
fall back to one.

**DECIDED — the entry's `probe` is two vectors, and the default native target
comes from the second.** Review cycle 2 found that revision 2 consumed a
"resolved default native target" in the compile vector and the cache identity
while declaring only `konanc -version` as the probe. Decision 0007 section 1.1
declares `probe` as *the exact package-independent argument vectors* — plural,
as the `go` entry already uses — and its Stage A step 6 already exists to
compare the toolchain's own reported host target against the native target. The
`kotlin` entry therefore declares:

- **P1**, `konanc -version`, normalized by
  `kotlin.konanc.dashversion.stdout` into the canonical triple. **MEASURED
  (win)**: stdout 23 bytes, `Kotlin/Native: 2.4.10\r\n`; **MEASURED (mac)**: the
  same line with an LF terminator, 22 bytes. The normalization splits lines on
  LF or CRLF with the terminator excluded, so the platform difference is
  absorbed in the rule rather than in the caller.
- **P2**, `konanc -list-targets`, normalized by
  `kotlin.konanc.listtargets.default.stdout`: stdout only, bounded to 4 KiB,
  every non-empty line matching `^([a-z][a-z0-9_]*)((?: \([a-z]+\))*)$`, exactly
  one line carrying the `(default)` annotation, and that line's token mapped
  through a closed table to `(operating_system, architecture)`. **MEASURED
  (win)**: exit 0, stdout 131 bytes, stderr 0 bytes, eight lines, exactly one
  marked `mingw_x64 (default)`, mapping to `(windows, amd64)`.

Both vectors are manager-parent registry probes run once per operation from a
manager-owned empty working directory under the operation-private environment,
memoized only in operation-private state. Neither is a worker command, so the
one-compile-command session shape is unchanged — exactly as the `go` entry's
three bootstrap vectors leave the Go session shape unchanged. **MEASURED
(win)**: both exit 0 with `KONAN_DATA_DIR` pointing at an empty directory and
leave 0 entries in it, so they are independent of the hydrated closure and
cannot mutate it.

Failure routing introduces no new code and no new site: an unbounded,
ungrammatical, or ambiguous P2 output — including a `(default)` count other than
one — is `build_toolchain_version_undetermined` at Stage A step 4; an unmapped
token, or one mapping to a pair other than the host pair, is
`build_toolchain_platform_unsupported` with `check` `native_target` at Stage A
step 6. The normalized token is the sole source of `-target`, is the native
target input of the canonical build input, and is what acceptance requirement A7
records.

**DECIDED — argument vector.** One process, one command, no retry, no second
phase:

```text
<kotlin_root>\jdk\bin\java.exe
  -ea -Xmx3G -XX:TieredStopAtLevel=1
  -Dfile.encoding=UTF-8 -Duser.language=en -Duser.country=US
  -Dkonan.home=<kotlin_root>\kotlin-native
  -cp <kotlin_root>\kotlin-native\konan\lib\kotlin-native-compiler-embeddable.jar
  org.jetbrains.kotlin.cli.utilities.MainKt
  konanc
  -Xoverride-konan-properties=airplaneMode=true
  -produce program
  -target <the P2-resolved default native target token>
  -o <operation-private-staging>\<command>
  <absolute path to source 1>
  …
  <absolute path to source N>
```

The JVM options are the vendor launcher's own, minus everything it takes from
the environment. `-Duser.language`/`-Duser.country` are the one element added
beyond the vendor vector, for locale-independent diagnostics, and the
qualification measured the vector including them. Binding rules:

- sources are the recursive `.kt` set under `source_dir`, enumerated by the
  manager, sorted by Unicode-scalar order of relative path, and passed as
  absolute paths — never as a directory source root, because a directory hands
  file discovery to the compiler and would compile files the allow-list walk
  rejected;
- no entry point, module name, opt-in, language-version, API-version,
  optimisation, debug, cache, memory-model, or plugin argument is passed, and
  none is package-derivable;
- `-target` names the host's own default native target only. **Cross-compilation
  is not admitted in this version**;
- `-Xoverride-konan-properties` carries exactly the constant above. Its value is
  manager-owned and no package byte can reach it;
- no argv token may begin with `@`.

**DECIDED — operation-private environment.** In addition to the
`manager-worker-v2` portable control set:

| Variable | Action | Why |
|---|---|---|
| `KONAN_DATA_DIR` | set to the operation-private overlay | section 4 |
| `TMPDIR`, `TMP`, `TEMP` | set to operation-private staging | **MEASURED**: intermediates land there |
| `KONAN_USE_INTERNAL_SERVER` | unset | **MEASURED**: selects a JetBrains-internal dependency host, `https://repo.labs.intellij.net/kotlin-native` |
| `JDK_JAVA_OPTIONS`, `JAVA_TOOL_OPTIONS`, `_JAVA_OPTIONS` | unset | honoured by the JVM launcher; inject arbitrary JVM options |
| `CLASSPATH` | unset | would extend the compiler classpath |
| `JAVA_HOME`, `JAVACMD`, `JAVA_OPTS` | unset | launcher inputs; closed structurally by never running the launcher, unset as defence in depth |
| `KOTLIN_HOME`, `KOTLIN_COMPILER`, `KOTLIN_TOOL`, `KOTLIN_RUNNER`, `_TOOL_CLASS` | unset | same; `KOTLIN_COMPILER` and `_TOOL_CLASS` select the compiler main class |
| `PATH` | manager-owned minimal value | no toolchain is resolved through it |

**MEASURED (win)**: every compile in the qualification ran with `PATH` set to a
single manager-owned empty directory and exited 0 — zero `PATH` resolutions are
required — and the paired control fired: `bin\konanc.bat` under the same `PATH`
exits 9009 because it resolves `java` by bare name.

No manager-written configuration file is placed anywhere for this driver. The
pipeline reads no configuration file, because the launcher that would is never
run and the compiler is given an explicit, complete argument vector.

### 9. Platform libraries, native interop, and the published-artifact gate

**MEASURED.** The distribution ships platform klibs per target under
`klib/platform/<target>/` — eight for `mingw_x64`, 200-plus for each Apple
target. Source importing them compiles and links with no `-library` argument and
no `.def` file, and changes the produced artifact's dynamic dependency set.

**DECIDED — the surface is allowed, and its consequence is bound.** The fixed,
distribution-owned platform library surface is **admitted**: it is inside the
fingerprinted bundle, it is selected by source rather than by any package
control input, a package cannot add to it or name one, and rejecting it would
require the manager to parse Kotlin source, which it does not do. What is
rejected is everything a package could *supply*: `.def` files, headers, native
sources, objects, archives, shared libraries and prebuilt `.klib` are all
rejected by the section 7 allow-list, and `cinterop` is a second tool and a
second command that `manager-worker-v2`'s session admits in neither position.
The honest statement is therefore: **no user-defined C interop, and the
distribution's own platform bindings are available as part of the fingerprinted
toolchain.**

**DECIDED — the published-artifact dynamic dependency gate.** Because the
artifact's dynamic dependency set is a function of package source, decision 0008
section 3's third bullet cannot be discharged by any pre-compile file walk.
Before hashing and before publication, in operation-private staging, the manager
MUST read the produced file's dynamic dependency list — the PE import directory
on Windows — and MUST reject the build with `build_artifact_class_unsupported`
if any entry is outside the closed base-installation library allow-list that the
platform matrix fixes for that tuple. The manager parses the image itself and
MUST NOT invoke a tool from the bundle or the host to do it. Reading a file's
headers is not executing it, so this does not touch decision 0008 section 3's
"never executed by the manager" clause. Each qualified tuple MUST supply that
allow-list; a tuple with no allow-list cannot be qualified.

The `windows/amd64` list is exactly **`{KERNEL32.dll, msvcrt.dll}`**, fixed in
the reference section 10.1 — the single normative source — from the measured
import directories of both a plain program and one importing `platform.posix`
and `platform.windows`, which produced the same two entries. It is deliberately
what was measured, not what is plausible: `ADVAPI32.dll`, `USER32.dll`,
`GDI32.dll` and the rest of the obviously-base-installation Windows set are
**excluded**, and widening the list is a fresh run of section 12's A6 whose
sample actually produces the new import. A closed set smaller than reality fails
safe and is visibly extendable; a closed set built from assertion fails open
once, silently.

### 10. Registry entry

**DECIDED — every field has a measured value, and the two set-valued fields are
admitted by `TASK-260728-251p01`, not here.**

| Field | Value |
|---|---|
| `toolchain_id` | `kotlin` |
| `fingerprint_algorithm` | `curator-kotlin-toolchain-v1` |
| companions | empty |
| `metadata_sources` | `kotlin-native-module.json` → `kotlin_version` |
| `baseline` | `at_least 2.4.10` |
| `compatibility` | family granularity `(major, minor)`; candidate set `{(2, 4)}`, admitted under the binding rule below |
| `platforms` | candidate set `{(windows, amd64)}`, admitted under the binding rule below |
| `primary_relpath` (windows) | `jdk\bin\java.exe` |
| `probe` (windows) | P1 `konanc -version` and P2 `konanc -list-targets`, section 8 |
| `normalization` | `kotlin.konanc.dashversion.stdout`, `kotlin.konanc.listtargets.default.stdout` |

`primary_relpath` and `probe` are declared for `windows` and for no other
operating system, because decision 0007 section 1.1 declares them per operating
system and only for operating systems in `platforms`. A macOS or Linux relpath
is absent by construction, not omitted, and declaring one would fail decision
0007 section 4's release gate.

**The binding rule for both set-valued fields.** Decision 0007 section 1.3
requires this task to supply the initial tested `compatibility` set and the
`platforms` set from a qualified host, and the host measurement exists: 2.4.10
is the release the acceptance test exercised end to end, and `(windows, amd64)`
is the tuple it ran on. Neither set is admitted by that measurement, because
admission is a corpus event:

- decision 0007 section 1.1.1 admits a family only after it has been tested
  against the driver's conformance vectors — section 12's A9;
- section 12's own admission rule admits a tuple only after **all** of A1–A9,
  and A8 is the allow-list corpus walk.

Both are authored by `TASK-260728-251p01` in the same change that mints manifest
schema 8 and admits these identifiers; before that change no manager can resolve
either driver at all. The binding rule is therefore: the entry ships with
`compatibility = {(2, 4)}` and `platforms = {(windows, amd64)}` only in a change
where the reference section 14 vectors pass, A8 included; if they do not pass,
the entry has no admissible family and no admissible tuple, and section 12's
retirement branches apply. No other family and no other tuple may enter either
set from this record.

**Normalization P1, MEASURED.** `konanc -version` writes exactly
`Kotlin/Native: 2.4.10` to **stdout** and exits 0, while stderr carries
`info: kotlinc-native 2.4.10 (JRE …)`. The rule reads line 1 of stdout, bounded
to the first 4 KiB, anchored whole-line:

```text
^Kotlin/Native: (0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(\S*)(?:\s.*)?$
```

Groups 1–3 are the triple; a non-empty group 4 sets the prerelease flag.
Unmatched or multiply-matched output is `build_toolchain_version_undetermined`,
never a default. The literal `Kotlin/Native: ` prefix is load-bearing: it
asserts the **backend**, not merely a version, so a JVM-backend distribution —
which writes `info: kotlinc-jvm …` to stderr with an empty stdout — cannot
satisfy the rule at all.

### 11. Platform position

**DECIDED — `windows/amd64` is an A1–A7 host-qualified candidate.** The tuple
passed every host-side requirement of section 12 on a real host:
checksum-verified inputs, a regular primary executable, both normalizations
reproduced, a zero-resolution `PATH` with a firing control, a complete
kernel-level process trace showing only in-bundle children, a byte-unchanged
bundle under network denial, one produced file with no by-product, a running
AMD64 PE whose imports are exactly the two entries of its base-installation
allow-list, and a default target token that maps to the host pair.

It is **not admitted**. Section 12 admits a tuple on A1–A9; A8 and A9 are
discharged by the conformance corpus, that corpus does not exist yet, and this
record does not anticipate its result. `windows/amd64` is therefore the only
tuple that may enter `platforms`, and it enters under the section 10 binding
rule. `windows/arm64` is a separate tuple and is not implied.

**DECIDED — macOS is excluded, and the exclusion is measured, not pending.**
`macos/arm64` and `macos/amd64` are **not admissible for this driver family at
Protocol 1.0**, on two independent grounds, either one sufficient.

*Ground one — the process closure.* Under exec containment allowing only the
curatable roots, a hello-world `-produce program -target macos_arm64` cannot
run without host executables. Two iterative-denial runs were made. `run7`,
seeded empty, established `/bin/bash` and `/usr/bin/xcrun` as required and its
raw output additionally shows `/usr/bin/xcode-select`, `/usr/libexec/PlistBuddy`
and `<Xcode>/Contents/Developer/usr/bin/xcodebuild` denied. `run8`, seeded with
the first four, reached exit 0 after adding
`<Xcode>/…/XcodeDefault.xctoolchain/usr/bin/ld` and `…/usr/bin/dsymutil`. So the
**union observed** is seven and the set **sufficient** for a successful compile
is **six**; `run8`'s final `allowed-externals.txt` correctly holds those six, and
the difference is path-dependent because an allowed `xcode-select` removes the
`xcrun xcodebuild -version` fallback. Revision 2 called the set "exactly seven",
conflating the two; that claim is **withdrawn**.

Iterative denial proves each listed executable is required on the path taken and
that the listed set is sufficient. It does not prove that no other executable is
spawned on any path, so **no completeness claim is made for macOS** — and none
is needed. Decision 0008 section 6 item 3 is violated by the first external
executable; `/bin/bash`, `/usr/bin/xcode-select`, `/usr/libexec/PlistBuddy` and
`/usr/bin/xcrun` are absolute OS paths compiled into the compiler that no
operator-curated root can contain; and ground two is independent of the process
count. This asymmetry is why section 12's A3 now requires a **kernel-level trace
that records every process start by resolved image path** for a tuple that is to
be *admitted*: sufficiency is enough to exclude, only completeness is enough to
qualify.

**MEASURED**: no manager-fixed input closes it. With
`ignoreXcodeVersionCheck=true` and `targetToolchain`, `targetSysRoot` and
`additionalToolsDir` all overridden to absolute local paths, the compile still
fails with `Cannot run program "/usr/bin/xcrun"` at
`CurrentXcode.getToolchain(Xcode.kt:92)` ←
`AppleConfigurablesImpl.getAbsoluteTargetToolchain(Apple.kt:45)`. The structural
cause is in the distribution's own data and code: all 11 `remote:internal`
declarations in `konan.properties` are Apple toolchain, sysroot and addon
entries, and the only implementations of `XcodePartsProvider` are
`InternalServer` — gated on `KONAN_USE_INTERNAL_SERVER` and pointing at
`https://repo.labs.intellij.net/kotlin-native`, which no operator can reach —
and `Local`, which is the host's installed Xcode. There is no third source.

*Ground two — cache identity.* The Apple toolchain and SDK are not in any
fingerprinted tree, so the canonical build input cannot bind them. Two hosts
with different Xcode versions would compute the same cache key for different
artifacts, which is exactly the aliasing decision 0008 section 6 item 4 and
section 8 exist to prevent.

An implementation MUST fail with `platform_unsupported` on macOS. It MUST NOT
answer this by resolving a host tool, shipping a shim, declaring the SDK
data-only while executing from it, or publishing a second file.

**DECIDED — Linux stays outside the protocol.** `linux/*` is excluded until
`TASK-260728-1skseh`, then qualified by `TASK-260728-3u1nho` with the identical
acceptance test. The properties reading —
`targetToolchain.linux_x64 = $gccToolchain.linux_x64/…`,
`targetSysRoot.linux_x64 = $gccToolchain.linux_x64/…/sysroot`,
`llvm.linux_x64.user = llvm-21-x86_64-linux-essentials-116`, none
`remote:internal` — remains a reading of distribution data and is not a claim.

### 12. The acceptance test and the remaining retirement branch

**DECIDED.** A `(driver, operating_system, architecture)` tuple enters
`platforms` only when all of the following are discharged, each with recorded
argv and real exit code. A1–A7 are **host requirements**: they are discharged by
a run on that exact tuple, on an immutable native host. A8 and A9 are **corpus
requirements**: they execute no compiler, need no host, and are discharged by the
driver's conformance vectors. A tuple with A1–A7 discharged and A8/A9 outstanding
is an **A1–A7 host-qualified candidate** and does not enter `platforms`.

| # | Requirement |
|---|---|
| A1 | The bundle is curated per section 3 from a checksum-verified official archive and a checksum-verified JDK; `primary_relpath` resolves to a regular executable; both probe vectors and both normalizations of section 8 are reproduced on that host. |
| A2 | The full compile runs with `PATH` set to a manager-owned location that resolves nothing, **and** the paired control run through the shipped launcher fails on a `PATH` resolution. Without the control firing the negative proves nothing. |
| A3 | Under a **kernel-level process trace that records every process start in the window by resolved absolute image path** — not an iterative-denial enumeration — the compile exits 0 and every image below the compiler is a regular file inside `<kotlin_root>` or the operation-private overlay. The trace's completeness control MUST be shown to fire on a deliberately external executable. |
| A4 | With `airplaneMode=true` and all network denied, the compile exits 0, logs no download, and `<kotlin_root>` is byte-identical before and after; every write lands inside operation-private state. |
| A5 | Exactly one file is produced for publication; its exact name, any compiler-applied suffix, and its by-product set are recorded; renaming happens inside operation-private staging only; every by-product stays in staging. |
| A6 | The published file is a native executable for the tuple, runs, and every entry of its dynamic dependency list is inside that tuple's closed base-installation allow-list, which the qualification supplies. A source importing distribution platform libraries is included in the sample, because that is what moves the list. |
| A7 | The default native target is read from the P2 probe vector and mapped to the claim vocabulary `(operating_system, architecture)`. |
| A8 | The section 7 allow-list is exercised with the admitted inert-directory cases and one rejected entry per ordered diagnostic row, including a name beginning with `@`, a `.kts` file, a `.klib`, and a dot-leading directory. |
| A9 | `compatibility` gains the tested family, and only that family, once the driver's conformance vectors pass against it. |

**`windows/amd64` passed A1–A7 on the host, and A8 and A9 are not discharged.**
Those two are discharged by the conformance corpus rather than by a host run,
because the allow-list walk executes no compiler and the compatibility set is
manager policy; they are owned by `TASK-260728-251p01`. Under the rule above the
tuple is therefore an **A1–A7 host-qualified candidate**, not an admitted tuple,
and this record makes no claim about how the corpus will land.

**DECIDED — retirement, and both branches stay armed.** Revision 3 declared the
platform branch closed on an A1–A7 result, which contradicts the A1–A9 admission
rule directly above it; that closure is **withdrawn**. Two branches remain, and
both resolve at the single event where `TASK-260728-251p01` mints manifest
schema 8 and lands the reference section 14 corpus:

- *platform branch.* If no tuple has passed A1–A9 at that point — which requires
  A8 to pass for the classifier — no tuple is admissible.
- *compatibility branch.* If those vectors do not pass against the 2.4 family,
  the entry has no admissible family and every host fails
  `build_toolchain_untested_release`.

If either fires, both `kotlin-native-v1` and `kotlin-native-repository-v1` are
**retired unused** rather than shipped as an entry that can never succeed.
Retired means what decision 0008 section 2 says: the identifiers are not
reassigned to another language, backend, artifact class, or source mode, and are
not enabled by relaxing another driver. Claim schema 4 is then minted over the
admitted set without them and both become structurally unassertable. If neither
fires, the section 10 candidate sets become the shipped `platforms` and
`compatibility` values in that same change.

### 13. Capability limitations, stated rather than discovered

**DECIDED.** These are consequences of the design, not defects, and the
authoring guide MUST state all five:

1. **No third-party dependencies.** A package cannot supply or name a `.klib`,
   and the driver passes no `-library`. A build root compiles against the
   distribution's own libraries and nothing else.
2. **No user-defined C interop.** `cinterop` is a second tool and a second
   command, which `manager-worker-v2`'s session admits in neither position, and
   `.def` files, headers and native sources are rejected by the allow-list. The
   distribution's own platform bindings remain available, subject to section 9's
   published-artifact gate.
3. **The build root is not an IDE project.** The allow-list rejects every Gradle
   and Maven file, so an author keeps the IDE project outside the build root. A
   directory named `gradle` may exist and may hold only `.kt` sources. Build
   roots are context-excluded and never runtime-copied, so this costs the agent
   nothing and costs the author a duplicated source layout.
4. **No cross-compilation.** One host builds for its own default target only.
5. **`windows/amd64` only, once it is admitted.** It is the only tuple this
   record can put in `platforms`, and it gets there through section 10's
   binding rule. macOS is permanently unsupported (section 11) and Linux is
   outside the protocol's platform set. Everywhere else the driver fails closed;
   it does not silently fall back to anything.

### 14. Downstream obligations

- `TASK-260728-1koh5v`, `TASK-260728-gmfxdg` (Curator) and
  `TASK-260728-3ar1qp`, `TASK-260728-1uj0bc` (csk): implement against
  [`docs/kotlin-native-build-drivers.md`](../docs/kotlin-native-build-drivers.md),
  including the section 9 published-artifact dynamic dependency gate and the
  two-vector Stage A probe, and implement `(windows, amd64)` as the only claimable
  tuple.
- `TASK-260729-2vfvgi`: the `windows/amd64` qualification run this record
  reports. Its remaining scope is to re-run A1–A7 against the landed
  implementation rather than against the reference pipeline, and to record any
  divergence as a qualification regression.
- `TASK-260728-3u1nho`: Linux qualification, after `TASK-260728-1skseh`, with
  the identical acceptance test.
- `TASK-260728-r3j8ef` and `TASK-260728-1aveb2`: cross-manager interop
  verification for this pair cannot run on macOS under section 11 and MUST be
  sequenced onto the `windows/amd64` host.
- `TASK-260728-251p01`: mint manifest schema 8 with both identifiers admitted
  and land the section 14 vectors of the reference in the same change. That
  change **owns A8 and A9**, and therefore owns admission: it is what turns
  section 10's candidate `platforms` and `compatibility` sets into shipped
  values. If A8 does not pass for the classifier, or the 2.4 family does not
  pass the vectors, apply section 12's retirement branches and mint claim
  schema 4 without the two identifiers.
- `TASK-260728-2uh7em`: authoring and operations guidance, which MUST carry
  section 13 in full, MUST carry the bundle curation procedure of section 3
  including the `.extracted` and ownership obligations, and MUST NOT present a
  Gradle project as a supported layout.
- `TASK-260728-1g0z69`'s reserved `kotlin` entry is completed by this record;
  its reserved `jdk` entry is **not** claimed and remains reserved with no
  driver mapping.

## Stable failure classes

No new architecture-level class is introduced. Kotlin's per-surface diagnostics
sit beneath decision 0008's existing classes:

- `build_package_code_execution_forbidden` — the section 7 allow-list, with the
  ordered per-surface diagnostics `kotlin_non_regular_entry_forbidden`,
  `kotlin_response_file_name_forbidden`, `kotlin_script_source_forbidden`,
  `kotlin_build_system_file_forbidden`,
  `kotlin_native_interop_input_forbidden`, `kotlin_prebuilt_library_forbidden`,
  and the catch-all `kotlin_non_source_entry_forbidden`;
- `build_artifact_class_unsupported` — the section 9 published-artifact gate, and
  a platform that cannot produce a single directly loadable file;
- `build_toolchain_metadata_mismatch` — `kotlin-native-module.json` shape or
  `kotlin_version` comparison;
- `build_toolchain_untested_release`, `build_toolchain_version_undetermined`,
  `build_toolchain_prerelease_unsupported`, `build_toolchain_untrusted`,
  `build_toolchain_platform_unsupported` — decision 0007, unchanged, with P2's
  failures routed to the two sites decision 0007 section 5 already declares;
- `build_descriptor_driver_unsupported` and
  `build_descriptor_schema_unsupported` — decision 0008 section 5, unchanged.

## Rejected alternatives

- **The official Kotlin/Native archive as the toolchain root, with the JDK as a
  companion.** Rejected on measurement, and this is the alternative revision 1
  chose. Neither the macOS nor the Windows archive contains a regular
  executable, so decision 0007 section 3 has nothing to point at; the Apple
  dependency closure is not in the archive at all; and a companion root would be
  a second operator-asserted tree outside the primary fingerprint.
- **A "narrow reading" of decision 0007 section 3 under which the pipeline's
  primary executable may live in a companion root.** Withdrawn in revision 2.
  It was a request to reinterpret an accepted invariant in order to keep a
  design; the design changed instead.
- **Shipping the pair with empty `platforms` and `compatibility` and no host
  measurement at all.** Rejected, and this is the alternative revision 2 chose.
  Decision 0007 section 1.3 obliges this task to supply every field from a
  qualified host; an entry whose `platforms` has no candidate value fails every
  host before the compiler, which is a fail-closed reservation rather than the
  paired driver the acceptance criterion requires. The remedy was to obtain a
  host and measure, which revision 3 did. Note the difference from what this
  record now says: the sets have measured candidate values and a fixed admission
  event, rather than no values and no path to any.
- **Declaring the tuple admitted on the A1–A7 host result.** Rejected in
  revision 4, and this is the alternative revision 3 chose. Section 12 admits on
  A1–A9; calling a tuple qualified while its own table assigns A8 and A9 to a
  future task is a claim the evidence does not carry, and shipping a non-empty
  `platforms` on it would admit an unexercised classifier. Candidate plus a
  named admission event costs nothing an implementer needs and asserts only what
  was run.
- **Retiring both identifiers because the only measurable host could not
  qualify.** Rejected in revision 2 as an unmeasured negative, and still
  rejected: `windows/amd64` discharged A1–A7, so the negative is now disproved
  rather than merely unmeasured. Retirement remains armed on the corpus event of
  section 12, not on this.
- **Widening the Windows base-installation allow-list to the plausible base set
  — `ADVAPI32.dll`, `USER32.dll` and their neighbours.** Rejected. Revision 3's
  obligation table carried the wider set while its own normative table carried
  the measured two, leaving an implementer with two closed sets and no rule to
  pick between them. Every one of the wider entries is reachable through the
  distribution's other platform klibs, so admitting them unmeasured would let an
  artifact publish with a dependency no A6 run ever produced. The list is what
  was measured; widening it is a fresh A6 run.
- **Admitting macOS by treating `/usr/bin/xcrun`, `/bin/bash` and the Xcode
  toolchain as part of the platform's base installation.** Rejected on two
  independent grounds. Decision 0008 section 6 item 3 requires every executable
  started below the worker to be a fingerprinted member of the closure and names
  a host-resolved tool outside it as inadmissible; and the Xcode SDK would be an
  unfingerprinted build input, so two hosts with different Xcode versions would
  alias in the cache. The base-installation clause of section 3 is about the
  *artifact's* dynamic dependencies, not about the compiler's process graph.
- **Admitting macOS by copying the Xcode toolchain and SDK into the curated
  bundle.** Rejected on measurement: four of the required externals are absolute
  paths compiled into the compiler, and with every Apple property overridden to
  point inside a curated tree the compiler still spawned `/usr/bin/xcrun`. The
  copy would also redistribute Apple-licensed material, which is not a decision
  this record may take.
- **Using `KONAN_USE_INTERNAL_SERVER` to obtain the Apple parts as ordinary
  dependencies.** Rejected: it points at a JetBrains-internal host, so it is not
  an origin any operator can use, and depending on it would make the contract
  unimplementable outside one company.
- **Letting the manager hydrate the dependency closure itself on first use.**
  Rejected: it is a manager-initiated download of hundreds of megabytes of
  executable content, over a channel with no integrity check the compiler
  reports, inside a Curator operation — the auto-install decision 0007 refuses,
  under a different name.
- **A manager-read bundle descriptor recording the bundle's provenance and
  component digests.** Rejected: the manager cannot verify such a file against
  anything, so it would be a trust input that looks like a proof.
- **Pointing `KONAN_DATA_DIR` at the fingerprinted bundle directly.** Rejected
  on measurement: the compiler opens `dependencies/cache/.lock` for writing, so
  a write-denied root fails, and a writable root would let an operation mutate
  the tree whose digest is the toolchain identity.
- **Linking the overlay's `dependencies/cache` back into the bundle.** Rejected
  on the same measurement: that directory is exactly where the lock is taken, so
  linking it reintroduces the write into the fingerprinted tree that the overlay
  exists to remove.
- **Treating `dependencies/.extracted` as a cache artefact and dropping it
  during curation.** Rejected on measurement: without it the compile fails
  `Cannot find a dependency locally` even with the full closure present.
- **Relying only on network denial for the no-download guarantee.** Rejected as
  the sole layer: it is an operator or platform property rather than a driver
  property, and it fails open on a host where denial is unavailable.
  `airplaneMode=true` makes the guarantee in-process and measurable, and the
  network denial is retained as the independent second layer in A4.
- **Describing the response-file defence as "absolute paths do not expand".**
  Rejected on measurement: `@/abs/path/inject` and `@<abs>\inject` both expand.
  The token's first character is what decides.
- **A deny-list of forbidden filenames instead of the allow-list.** Rejected:
  Kotlin's code-execution surfaces are an open set, so a deny-list cannot be
  exhaustive, which decision 0008 section 7 requires. The `@` vector is the
  proof — it is a name shape, not a known filename.
- **A build-system directory-name deny-list, to make `gradle/` and `META-INF/`
  rejectable directories.** Rejected for the same reason as the filename
  deny-list, and because the file-level closure already prevents an inert
  directory from carrying anything executable. Revision 2's section 7.2 listed
  such directories as rejected while its classifier admitted them; the
  contradiction is resolved in favour of the classifier, not by adding the list.
- **Declaring the default native target without a probe that reads it.**
  Rejected on review: revision 2's compile vector and cache identity consumed a
  "resolved default native target" that no declared Stage A stage produced.
  Either the value has a package-independent probe vector with an exact grammar
  and typed failures, or it is an undeclared input. The `probe` field is plural
  and Stage A step 6 already exists for it, so it costs no new code and no new
  site.
- **Kotlin/JVM plus GraalVM `native-image`.** Rejected on four independent
  grounds, any one sufficient: it needs a second compile-phase command, which
  `manager-worker-v2`'s session shape refuses; it needs a third toolchain
  outside decision 0007's closed identifier set; assembling its classpath needs
  either a package manager or a package-controlled classpath member, both
  refused; and it is a different backend, so decision 0008 section 2 requires a
  different family segment.
- **Gradle in any role, including a metadata-only query.** Rejected on
  measurement: `gradle properties` compiles the build script as a program source
  unit before answering. There is no read-only Gradle, and no `--offline`,
  `--dry-run`, or init-script variant changes what it is.
- **Maven as the metadata file, reading only one field.** Rejected: the Maven
  project model is its plugin graph; reading one field while ignoring the graph
  would let a package ship a plugin declaration Curator silently does not run.
- **Claiming `windows/arm64` or `linux/amd64` from the `windows/amd64`
  result.** Rejected: each tuple is qualified by its own run of section 12, and
  a passing sibling is not evidence.

## Compatibility impact

None on the wire. This record admits no identifier, mints no schema, and moves
no frozen byte. `go-v1` and `go-repository-v1` identities, `manager-worker-v1`,
`capability-evidence-v1`, `curator-go-toolchain-v1`, the rc.4 and rc.5
conformance corpora, and the rc.5 pin are untouched. Manifest schemas 1 through
7, descriptor schema 1, receipt schemas 1 and 2, marker schemas 1 through 3, and
claim schemas 1 through 3 continue to reject both Kotlin identifiers, as
decision 0008 section 11 item 12 requires.

`kotlin-native-module.json` is a new package-authored file bound by a reserved
driver. It reaches no wire surface until manifest schema 8 is minted with
`kotlin-native-v1` admitted, and it is inert for every other driver.

Decision 0007's reserved `kotlin` entry moves from "no fields" to **every field
supplied**: shape, metadata source, baseline, two probe vectors, two
normalizations, identity, a per-operating-system `primary_relpath` declared for
`windows` alone, and the two set-valued fields as candidates —
`platforms = {(windows, amd64)}` and `compatibility = {(2, 4)}` — which ship
under the section 10 binding rule when `TASK-260728-251p01` discharges A8 and
A9, and otherwise trigger retirement. Its
reserved `jdk` entry is **released**: this record does not use it, so it stays
reserved with no driver mapping. That supersedes the "`jdk` if JVM" expectation
in decision 0007's driver-mapping table; the JDK is a component of the `kotlin`
root rather than a toolchain of its own.

## Security impact

Net positive, and concentrated in six places.

The curated bundle makes the entire executable closure one fingerprinted tree,
and on the candidate tuple that is now a complete measurement rather than an
argument: a kernel-level trace of a successful compile records every process
start in the window, and the only children below the compiler are two LLVM
executables inside the bundle. A single tree digest covers the launcher, the
compiler, and every tool the compiler spawns, and the cache key binds it.

Refusing the shipped launcher removes the `PATH` resolution of `java` and the
environment-selected pipeline inputs — `JAVACMD`, `JAVA_HOME`, `JAVA_OPTS`,
`KOTLIN_RUNNER`, `KOTLIN_COMPILER`, `KOTLIN_TOOL`, `_TOOL_CLASS` — from the
process graph structurally rather than by neutralisation. `KOTLIN_COMPILER` and
`_TOOL_CLASS` in particular select the compiler main class.

Hydration is moved out of the operation entirely. The measured download path has
no integrity check the compiler reports, so performing it inside an operation
would be a manager-initiated fetch and execution of hundreds of megabytes of
third-party executable content. `airplaneMode=true` makes the exclusion
enforceable in-process rather than by hoping the network is unreachable, and the
measured fail-closed behaviour writes nothing into the data directory.

The measured `@`-response-file vector is a real property of the Kotlin CLI on
both backends and both platforms: a token whose first character is `@` is a
response file, and a missing one is only a warning, so a partial mitigation
fails silently. The contract closes it twice.

Read-only enforcement is an operator obligation with a measured sharp edge.
Denying writes to the running user was sufficient to stop the compiler writing
into the bundle, and was **not** sufficient to stop a delete, because the same
account held Full Control through a group that grants delete-child on the
parent. Curation therefore requires ownership by an account the manager does not
run as, not a per-user deny.

The macOS exclusion remains a refusal rather than a mitigation. A Kotlin build
integration that runs on macOS necessarily executes at least six host binaries
the manager cannot fingerprint, and binds an Xcode SDK into the output that the
cache key cannot see. Both are refused, the platform is excluded, and nothing
compensates for it.

Two exposures are recorded rather than closed. The compiler-input exposure of
decision 0008's security section is unchanged: a trusted compiler parsing
adversarial source under the portable, non-hardened controls is the same
exposure the other drivers carry. And the artifact's dynamic dependency set is
package-source-dependent through the distribution's platform libraries; section
9's published-artifact gate is what converts that from an unbounded property
into a checked one, and a tuple without a base-installation allow-list cannot be
qualified.
