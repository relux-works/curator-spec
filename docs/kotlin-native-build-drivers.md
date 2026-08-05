# Kotlin build drivers: `kotlin-native-v1` and `kotlin-native-repository-v1`

Implementation-ready reference for the pair selected by
[decision 0010](../decisions/0010-kotlin-native-driver-pair.md), inside the
boundary of [decision 0008](../decisions/0008-additional-language-driver-boundary.md)
and the toolchain contract of
[decision 0007](../decisions/0007-compiled-build-toolchain-preflight.md) and
[`compiled-build-toolchain-requirements.md`](compiled-build-toolchain-requirements.md).

**Both identifiers remain reserved until `TASK-260728-251p01` admits them.**
One tuple — `windows/amd64` — is an **A1–A7 host-qualified candidate**: every
host-side requirement of section 11.1 was discharged on a real host, and section
1.4's registry entry is filled from that run rather than asserted. It is **not
yet admitted**: A8 and A9 are discharged by the conformance corpus, which
`TASK-260728-251p01` authors, and the `platforms` and `compatibility` sets enter
the shipped entry only in the change where that corpus passes. Until then both
retirement branches of section 11.5 stay open. `macos/*` is measured
**permanently unsupported**. `linux/*` is outside the protocol's platform set.

Throughout this document, **A1–A7 host-qualified candidate** means exactly that
state: the host-side acceptance requirements are discharged with recorded argv
and real exit codes, and the corpus-side requirements are not. It never means
admitted, and it never licenses shipping a non-empty `platforms` set ahead of
the corpus.

Evidence markers:

- **MEASURED (win)** — recorded with argv and real exit code on
  Windows 10 Pro 10.0.19045.6456, AMD64, in
  `TASK-260728-168smo_command-evidence-cycle3.log` records W1–W17, against the
  checksum-verified
  official release `kotlin-native-prebuilt-windows-x86_64-2.4.10.zip`
  (`ce99eba1f4faec1d77f4bbd747bb722404ef11f2c349ec70c59d4c002859380f`, equal to
  the published `.sha256` asset) and the checksum-verified Eclipse Temurin
  `OpenJDK21U-jdk_x64_windows_hotspot_21.0.11_10.zip`
  (`d3625e7cadf23787ea540229544b6e2ab494b3b54da1801879e583e1dfee0a64`, equal to
  the Adoptium API checksum).
- **MEASURED (mac)** — recorded on macOS 26.5 arm64 against
  `kotlin-native-prebuilt-macos-aarch64-2.4.10.tar.gz`
  (`55ded039bb56a69aec9df354a92b42df9e916104e3c53d8d9852d9cc6617ed9d`), in
  `TASK-260728-168smo_command-evidence.log` and in corrections C1–C3 of the
  cycle-3 log. These
  runs characterise the pipeline and establish the macOS exclusion; none of them
  admits macOS.
- **UNVERIFIED** — a named per-tuple obligation carried into section 11.6.
- Absent marker — a consequence of an accepted decision.

## 1. The toolchain root: `curator-kotlin-bundle-v1`

### 1.1 Why the vendor archive is not the root

**MEASURED (win) and MEASURED (mac).** The official distribution contains no
regular executable on either platform:

| Platform | `bin/` contents | Regular executables anywhere in the distribution |
|---|---|---|
| macOS arm64 | `konanc`, `kotlinc-native`, `run_konan`, `cinterop`, `klib`, `konan-lldb`, `generate-platform` — all Bourne-Again shell scripts | none |
| Windows x86_64 | the same seven names plus `cinterop.bat`, `generate-platform.bat`, `klib.bat`, `konanc.bat`, `kotlinc-native.bat`, `run_konan.bat` — 13 entries, all scripts | **0** files matching `*.exe` |

The compiler itself is one JAR,
`konan/lib/kotlin-native-compiler-embeddable.jar` (83,903,904 B in the Windows
release).

`run_konan.bat` takes `JAVA_HOME` from the environment, falls back to the bare
name `java` resolved through `PATH`, appends every `-D` argument and the payload
of every `-J` argument to the JVM, honours `_TOOL_CLASS` to select the compiler
main class, and sets `LIBCLANG_DISABLE_CRASH_RECOVERY`. `run_konan` on Unix does
the same through `JAVACMD`, `JAVA_HOME` and `JAVA_OPTS`. Decision 0007 section 3
requires a regular executable at the entry's fixed relpath inside the
fingerprinted tree, and decision 0008 section 6 item 3 forbids
environment-selected pipeline inputs, so neither the archive root nor any script
inside it can be the primary executable.

### 1.2 The bundle layout

The `kotlin` root is an operator-curated tree resolved through decision 0007's
second admissible origin — trusted operator configuration in manager-owned,
owner-protected state — with this exact layout:

```text
<kotlin_root>/
  jdk/
    bin/java.exe                   primary_relpath (windows)
  kotlin-native/
    konan/lib/kotlin-native-compiler-embeddable.jar
    konan/konan.properties
    klib/…
    bin/…                          present, never executed
  konan-data/
    dependencies/<name>/…          the prehydrated closure
    dependencies/.extracted        REQUIRED — see 1.3 step 6
```

The whole tree is fingerprinted, is immutable for the life of the
configuration, and MUST be read-only to the account the manager runs as. The
manager reads no descriptor inside it; the tree digest is the identity.

**MEASURED (win)** for the candidate tuple: 27,867 files, 2,456,792,320 B,
tree digest
`63d96ff7c488e713dedbf7029237cfc6cd030ae4c1caf11c8ba2274395badae3`. That digest
was reproduced independently after the bundle was disturbed and rebuilt from the
same inputs, so the curation procedure below is byte-reproducible rather than
merely repeatable.

### 1.3 Curation procedure (operator, once, outside every operation)

1. Download the official `kotlin-native-prebuilt-<platform>-<version>` archive
   and verify it against the release's published `.sha256` asset.
   **MEASURED (win)**: `kotlin-native-prebuilt-windows-x86_64-2.4.10.zip`,
   222,016,219 B, published and locally computed digests equal.
2. Unpack into `<kotlin_root>/kotlin-native`.
3. Obtain a JDK from a source that publishes a checksum, verify it, and unpack
   it at `<kotlin_root>/jdk`. **MEASURED (win)**: Temurin `jdk-21.0.11+10`,
   205,073,954 B, published and locally computed digests equal;
   `jdk/bin/java.exe` is a regular 50,344 B executable. Any JDK the compiler
   runs on is admissible; its identity is covered by the bundle digest, not by a
   separate probe, and it is **not** a companion toolchain.
4. Read `kotlin-native/konan/konan.properties` and confirm that for the target
   this host will build, none of `targetToolchain.<target>`,
   `targetSysRoot.<target>` or `additionalToolsDir.<target>` resolves to a
   `remote:internal` dependency. **MEASURED**: the file carries 11
   `remote:internal` declarations and every one of them belongs to an Apple
   target — which is why macOS is unsupported (section 11.2). For the candidate
   tuple, `targetToolchain.mingw_x64` and `targetSysRoot.mingw_x64` both resolve
   to `$toolchainDependency.mingw_x64 = msys2-mingw-w64-x86_64-2`,
   `llvm.mingw_x64.user = llvm-21-x86_64-windows-essentials-150`, there is no
   `additionalToolsDir.mingw_x64`, and none is `remote:internal`.
5. Hydrate once, with network access, on this platform: run one throwaway
   `-produce program` compile with `KONAN_DATA_DIR` pointed at
   `<kotlin_root>/konan-data`. **MEASURED (win)**, exit 0 in 68.6 s, exactly four
   dependencies fetched from `https://download.jetbrains.com/kotlin/native`:

   | Dependency | Archive bytes |
   |---|---|
   | `lldb-2-windows` | 54,796,930 |
   | `msys2-mingw-w64-x86_64-2` | 135,111,082 |
   | `llvm-21-x86_64-windows-essentials-150` | 275,594,763 |
   | `libffi-3.3-windows-x64-1` | 111,136 |

   The compiler reports no integrity check for these downloads; verifying them
   is part of curation, not of any Curator operation.
6. Delete `<kotlin_root>/konan-data/dependencies/cache`. It holds only the
   downloaded archives and the compiler's lock file. **Do not delete
   `dependencies/.extracted`.** **MEASURED (win)**: with `.extracted` absent and
   the closure present, the compile fails
   `Cannot find a dependency locally: lldb-2-windows` with exit 2 and no
   download attempted; with `.extracted` restored (103 B, four dependency names,
   LF-separated, trailing LF) the identical compile exits 0. The file is a
   required part of the closure, not a cache artefact.
7. Make the whole tree read-only **to the account the manager runs as**, then
   register it in operator configuration. Obligation **K-11**: a deny ACE on a
   single user is not sufficient on a host where that user is also a member of a
   group holding Full Control. **MEASURED (win)**: with writes denied to the
   running user SID the compile could not write into the bundle and failed
   `java.io.IOException: Access denied`, while a delete of a bundle file still
   succeeded because `BUILTIN\Administrators` retained `FILE_DELETE_CHILD` on the
   parent. The operator MUST own the bundle from an account the manager does not
   run as, and grant the manager's account read and execute only.

Nothing in this procedure is performed by a manager, in any mode, at any time.

### 1.4 The `kotlin` registry entry

| Field | Value |
|---|---|
| `toolchain_id` | `kotlin` |
| `fingerprint_algorithm` | `curator-kotlin-toolchain-v1` |
| companions | **empty** |
| `metadata_sources` | `kotlin-native-module.json` → `kotlin_version` |
| `baseline` | `{"kind":"at_least","min":"2.4.10"}` |
| `compatibility` | family granularity `(major, minor)`; candidate set `{(2, 4)}`, admitted under the binding rule below |
| `platforms` | candidate set `{(windows, amd64)}`, admitted under the binding rule below |
| `primary_relpath` (windows) | `jdk\bin\java.exe` |
| `probe` (windows) | the two vectors of section 1.5 |
| `normalization` | `kotlin.konanc.dashversion.stdout` and `kotlin.konanc.listtargets.default.stdout`, section 1.5 |

The `jdk` identifier decision 0007 reserved is **not used**: the JDK is a
component of the `kotlin` root, so there is no companion entry, no second probe,
and no second tree digest. `toolchain_identities` in the canonical build input is
a one-element ordered array.

`primary_relpath` and `probe` are declared for `windows` and for no other
operating system, because decision 0007 section 1.1 declares them per operating
system and only for operating systems in `platforms`, and its release gate
rejects a declaration outside that set. A macOS or Linux relpath is therefore
**absent by construction**, not omitted.

**The binding rule for both candidate sets.** `compatibility` and `platforms`
are the fields decision 0007 section 1.3 requires this task to supply from a
host measurement, and the measurement exists: 2.4.10 is the release the host run
of section 11.1 exercised end to end, and `(windows, amd64)` is the tuple it ran
on. Neither set is yet admitted, because admission is a corpus event, not a host
event:

- decision 0007 section 1.1.1 admits a family only after it has been tested
  against the driver's conformance vectors — requirement A9;
- section 11.1's own rule admits a tuple only after **all** of A1–A9, and A8 is
  the allow-list corpus walk.

Both vectors are authored by `TASK-260728-251p01` in the same change that mints
manifest schema 8 and admits these identifiers; before that change no manager
can resolve either driver at all, because every frozen schema rejects them. So:
**the entry ships with `compatibility = {(2, 4)}` and `platforms =
{(windows, amd64)}` only in a change where the section 14 vectors pass, A8
included; if they do not pass, the entry has no admissible family and no
admissible tuple, and section 11.5 retires both identifiers.** No other family
and no other tuple may enter either set from this record. A manager MUST NOT add
a family or a tuple from version ordering, probe output, or any package byte.

### 1.5 Probe and normalization

The entry's `probe` is **two ordered, package-independent argument vectors**,
both run once per operation from the manager parent, from a manager-owned empty
working directory, under the section 5.1 operation-private environment, and
memoized only in operation-private state. Neither is a worker command: the
worker session shape of section 6 — zero graph-phase commands, exactly one
compile-phase command — is unchanged by them, exactly as the `go` entry's three
bootstrap vectors do not change the Go session shape.

**MEASURED (win)**: both vectors exit 0 with `KONAN_DATA_DIR` pointing at an
empty manager-owned directory, and that directory holds 0 entries afterwards.
The probes are therefore independent of the hydrated closure and cannot mutate
it, which is what lets Stage A run them before any cache lookup or compiler
work.

#### 1.5.1 P1 — release version

```text
<kotlin_root>\jdk\bin\java.exe
  -ea -Xmx3G -XX:TieredStopAtLevel=1
  -Dfile.encoding=UTF-8 -Duser.language=en -Duser.country=US
  -Dkonan.home=<kotlin_root>\kotlin-native
  -cp <kotlin_root>\kotlin-native\konan\lib\kotlin-native-compiler-embeddable.jar
  org.jetbrains.kotlin.cli.utilities.MainKt konanc -version
```

**MEASURED (win)**, exit 0:

| Stream | Content |
|---|---|
| stdout | 23 bytes, `4b6f746c696e2f4e61746976653a20322e342e31300d0a` = `Kotlin/Native: 2.4.10\r\n` |
| stderr | 50 bytes, `info: kotlinc-native 2.4.10 (JRE 21.0.11+10-LTS)` |

**MEASURED (mac)**: the same stdout with an LF terminator, 22 bytes.

Normalization `kotlin.konanc.dashversion.stdout` reads **stdout only**, bounded
to the first 4 KiB. The byte stream is split into lines where a line terminator
is `LF` or `CRLF` and is **not part of the line**; the CRLF/LF difference between
the two measured platforms is absorbed here and nowhere else. Line 1 is matched
whole against:

```text
^Kotlin/Native: (0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(\S*)(?:\s.*)?$
```

Groups 1–3 are the canonical triple; a non-empty group 4 sets the prerelease
flag, and a prerelease host never satisfies any requirement. Output that the
rule does not match, or matches more than once, is
`build_toolchain_version_undetermined` — never a default.

The literal `Kotlin/Native: ` prefix asserts the **backend**. A Kotlin/JVM
distribution writes `info: kotlinc-jvm <version>` to stderr with an empty
stdout, so it cannot satisfy this rule at all, and a misconfigured root holding
the wrong distribution fails the probe rather than reaching a compile that
cannot produce `native-executable-v1`.

#### 1.5.2 P2 — resolved default native target

```text
<kotlin_root>\jdk\bin\java.exe
  -ea -Xmx3G -XX:TieredStopAtLevel=1
  -Dfile.encoding=UTF-8 -Duser.language=en -Duser.country=US
  -Dkonan.home=<kotlin_root>\kotlin-native
  -cp <kotlin_root>\kotlin-native\konan\lib\kotlin-native-compiler-embeddable.jar
  org.jetbrains.kotlin.cli.utilities.MainKt konanc -list-targets
```

**MEASURED (win)**, exit 0, stdout 131 bytes, stderr **0 bytes**:

```text
linux_x64
linux_arm32_hfp (deprecated)
linux_arm64
mingw_x64 (default)
android_x86
android_x64
android_arm32
android_arm64
```

Normalization `kotlin.konanc.listtargets.default.stdout`:

1. **Stream and bound.** stdout only, bounded to the first 4 KiB. stderr is not
   read. The vector's exit code MUST be `0`.
2. **Lines.** Split as in 1.5.1. Empty lines are skipped.
3. **Grammar.** Every non-empty line MUST match
   `^([a-z][a-z0-9_]*)((?: \([a-z]+\))*)$`. Group 1 is the target token; group 2
   is zero or more space-separated parenthesised lowercase annotations.
4. **Exactly-one-default rule.** Exactly one line's annotation list MUST contain
   the annotation `(default)`. That line's token is the **resolved default
   native target token**. Zero such lines, or two or more, is a failure; the
   manager never picks one, never orders the list, and never falls back to a
   host-derived guess.
5. **Token to claim mapping.** Closed, manager-owned, and the only mapping that
   exists:

   | Token | `(operating_system, architecture)` |
   |---|---|
   | `mingw_x64` | `(windows, amd64)` |
   | `linux_x64` | `(linux, amd64)` |
   | `linux_arm64` | `(linux, arm64)` |
   | `macos_x64` | `(macos, amd64)` |
   | `macos_arm64` | `(macos, arm64)` |

   Every other token — `linux_arm32_hfp`, every `android_*`, every Apple
   embedded target, `mingw_x86`, `watchos_*`, `tvos_*`, `wasm*` — is
   **unmapped**. Mapped-but-not-in-`platforms` and unmapped are distinct inputs
   with the same outcome, and neither is a fallback.
6. **Ordering.** P2 runs after P1, in Stage A step 4, for the same resolved
   root, in the same operation-private environment. P1's failure is reported
   first. P2's normalized token is consumed by Stage A step 6.
7. **Typed failures.**

   | Condition | Diagnostic | Site |
   |---|---|---|
   | P2 exits non-zero; stdout exceeds the bound; a non-empty line fails the grammar; the `(default)` line count is not exactly 1 | `build_toolchain_version_undetermined` | Stage A step 4 — decision 0007 section 5's declared site for probe output that is unbounded, unmatched, or ambiguous |
   | the resolved token is unmapped, or maps to a pair different from the manager's native pair | `build_toolchain_platform_unsupported` with `check` `native_target` | Stage A step 6 — decision 0007 section 5's declared site for a reported target that differs from the native target |

   No new diagnostic code and no new firing site is introduced.
8. **Binding.** The resolved token is the sole source of the `-target` value in
   the section 6 compile vector, is the `native target` input of the canonical
   build input of section 9, and is the token obligation K-6 and acceptance
   requirement A7 record. Nothing else may supply it, and no package,
   descriptor, manifest, module-file, or environment byte can reach it.
   **MEASURED (win)**: the token is `mingw_x64`, which maps to
   `(windows, amd64)` and equals the host pair.

Resolution origins are decision 0007 section 3's two and only two. The ambient
or user `PATH`, `JAVA_HOME`, `KOTLIN_HOME`, `KONAN_DATA_DIR`, `SDKMAN_DIR`, a
runtime root, project `.agents/bin`, a shim, a manifest or descriptor value, an
inherited environment variable, and any version-manager wrapper are all
forbidden origins.

## 2. Identity

`curator-kotlin-toolchain-v1`. A resolved identity is the algorithm identifier,
the normalized native version string, the primary-executable relpath, and the
tree digest of `<kotlin_root>`. Toolchain location is not portable identity.

Because the JDK, the compiler and the whole dependency closure are inside that
one tree, the digest covers every executable the pipeline can start. There is no
second root, no cross-root closure hash, and no component the cache key cannot
see. **MEASURED (win)**: the two executables the compiler spawns both resolve
inside `<kotlin_root>` (section 3).

Fingerprinting proves that the tree is stable across an operation and identical
across operations. It does **not** prove upstream authenticity: the hydration
download in section 1.3 step 5 carries no integrity check the compiler reports,
so verification is the operator's responsibility at curation time. A
`content_sha256` in a receipt MUST NOT be read as provenance.

## 3. The trusted launcher and the process graph

```text
manager parent
  -> identity-verified manager-owned worker
       -> <kotlin_root>\jdk\bin\java.exe
            -> Kotlin/Native compiler, in-process, loaded by -cp from
               <kotlin_root>\kotlin-native
                 -> <kotlin_root>\konan-data\dependencies\
                      llvm-21-x86_64-windows-essentials-150\bin\clang++.exe
                 -> <kotlin_root>\konan-data\dependencies\
                      llvm-21-x86_64-windows-essentials-150\bin\ld.lld.exe
```

**MEASURED (win), and this is the candidate tuple's A3 evidence.** A successful
`-produce program -target mingw_x64` compile was run inside an ETW
`Microsoft-Windows-Kernel-Process` trace with the `WINEVENT_KEYWORD_PROCESS`
keyword, which records **every** process start in the window by resolved image
path — a complete kernel-level inventory rather than an iterative enumeration.
Below the compiler JVM the trace records exactly two images, both regular files
inside `<kotlin_root>`: `clang++.exe` and `ld.lld.exe`. The operation-private
overlay materialises its dependency entries as junctions, and the kernel reports
the resolved target path, so an image reached through the overlay is reported at
its bundle path. No `cmd.exe`, `powershell.exe`, `link.exe`, `cl.exe`,
`lib.exe`, `vswhere.exe`, Visual Studio activation script, `msys2` shell, or any
other host executable appears below the compile. The trace's completeness control
fired: a deliberately external `where.exe` started in the same window was
recorded.

**Normative.** The driver MUST NOT execute `bin/konanc`, `bin/konanc.bat`,
`bin/kotlinc-native`, `bin/kotlinc-native.bat`, `bin/run_konan`,
`bin/run_konan.bat`, `bin/kotlinc`, `bin/cinterop`, `bin/klib`,
`bin/konan-lldb`, `bin/generate-platform`, or any other launcher script from any
distribution, on any platform, including for either probe vector.

**Per-tuple obligation K-2.** Every executable the compiler spawns must resolve
inside `<kotlin_root>` or the operation-private overlay of section 5.2. Any
other executable fails that tuple; there is no toolchain identifier for a
platform SDK that contributes a process, and Rust's data-only SDK root is not a
precedent for an executed linker. **`windows/amd64`: satisfied, measured.
`macos/*`: fails, and section 11.2 is the consequence.**

## 4. Source layout and the module file

### 4.1 Local mode

`build_roots` is the schema-6/7 model, unchanged: a portable relative path other
than `.`, a real link-free directory in the immutable raw snapshot, unique and
pairwise disjoint, never equal to or nested with a runtime root, referenced by
at least one build command, statically excluded from agent context and from the
runtime copy before cache lookup, identically for real builds, exact cache hits,
and dry-runs.

The build root MUST contain `kotlin-native-module.json` **directly**, and that
file MUST be the nearest ancestor of `source_dir`. The manager does not search
for it, does not walk upward, and does not infer it.

### 4.2 External mode

`skill-build.json` schema 2, target `driver: "kotlin-native-repository-v1"`,
with `build_root`, `source_dir` and the OPTIONAL `toolchain`. The command and
descriptor drivers MUST be equal. The whole repository snapshot is the
validation, identity and audit subject; only the selected build root is
compiler-visible; no external repository byte is agent-facing or runtime-copied.
`kotlin-native-module.json` MUST exist directly in the descriptor's
`build_root`. Against a schema-1 descriptor the command fails
`build_descriptor_driver_unsupported`, with no fallback.

### 4.3 `kotlin-native-module.json`

```json
{"schema_version": 1, "kotlin_version": "2.4.10"}
```

Exactly two members, both REQUIRED, `additionalProperties: false`.

| Member | Type | Meaning |
|---|---|---|
| `schema_version` | `const` integer `1` | file-shape gate only |
| `kotlin_version` | canonical `major.minor.patch` | the Kotlin compiler version the sources are written against |

`kotlin_version` matches decision 0007 section 2.1's grammar exactly:
`^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$`, each component at most
`999999`, no prefix, prerelease, build metadata, leading zero, or wildcard.

The file is never passed to the compiler, contributes no argument, and selects
nothing.

### 4.4 `source_dir` to program

The program is the recursive `.kt` set under `source_dir`, compiled in `program`
mode with the compiler's **default** entry point. The manager never names,
searches for, or infers an entry point. Zero or multiple entry points is a
compiler error and is therefore deterministic. No new command member is
introduced, and the consuming manifest command key remains the sole naming
authority for the artifact.

## 5. Environment and the operation-private overlay

### 5.1 Environment

On top of the `manager-worker-v2` portable control set and the mandatory
portable controls of `protocol/core.md` section 4.2.1:

| Variable | Action | Reason |
|---|---|---|
| `KONAN_DATA_DIR` | set to the overlay of 5.2 | the bundle is read-only; the compiler needs a writable data dir |
| `TMPDIR`, `TMP`, `TEMP` | set to operation-private staging | **MEASURED**: JVM and compiler intermediates land there |
| `KONAN_USE_INTERNAL_SERVER` | unset | **MEASURED**: selects the dependency host `https://repo.labs.intellij.net/kotlin-native` |
| `JDK_JAVA_OPTIONS` | unset | honoured by the JVM launcher; injects arbitrary JVM options |
| `JAVA_TOOL_OPTIONS` | unset | same |
| `_JAVA_OPTIONS` | unset | same family |
| `CLASSPATH` | unset | would extend the compiler classpath |
| `JAVA_HOME`, `JAVACMD`, `JAVA_OPTS` | unset | `run_konan` / `run_konan.bat` inputs; closed structurally by never running them, unset as defence in depth |
| `KOTLIN_HOME`, `KOTLIN_COMPILER`, `KOTLIN_TOOL`, `KOTLIN_RUNNER`, `_TOOL_CLASS` | unset | same; `KOTLIN_COMPILER` and `_TOOL_CLASS` select the compiler main class |
| `LIBCLANG_DISABLE_CRASH_RECOVERY` | unset | set only by the launcher, which is never run |
| `PATH` | manager-owned minimal value | no toolchain is resolved through it |
| `LANG`, `LC_ALL` | `C`/`POSIX` per the portable policy | locale-independent diagnostics |

No manager-written configuration file is placed anywhere for this driver. Rust
needed one because Cargo discovers ancestor `.cargo/config.toml`; this pipeline
reads no configuration file, because the launcher that would is never run and
the compiler is given an explicit, complete argument vector.

**MEASURED (win)**: every compile recorded in this document ran with `PATH` set
to a single manager-owned empty directory and exited 0. Zero `PATH` resolutions
are required. The paired control fired: the shipped `bin\konanc.bat` under the
same `PATH` exits **9009** — `'"java"' is not recognized as an internal or
external command` — because it resolves `java` by bare name through `PATH`. That
is acceptance requirement A2 for this tuple.

### 5.2 The overlay

**MEASURED, and the three facts that fix this section hold on both platforms.**

| Run | Outcome |
|---|---|
| hydrated `KONAN_DATA_DIR` inside the bundle, compile | exit 0; the tree gains exactly one file, `konan-data/dependencies/cache/.lock`, 0 bytes (**MEASURED (win)**; removing it restores the baseline tree digest byte for byte) |
| the same tree made write-denied, compile | fails — **MEASURED (win)** exit 2, `java.io.IOException: Access denied`; **MEASURED (mac)** exit 2, `FileNotFoundException: …/dependencies/cache/.lock (Permission denied)` |
| bundle write-denied, `KONAN_DATA_DIR` = overlay | exit 0, artifact produced, bundle byte-unchanged |

So the closure is not mutated by a compile except for one lock file, the data
directory must nevertheless be writable, and an operation-private overlay
satisfies both.

**Normative.** For each operation the manager materialises a private writable
directory whose `dependencies/` holds one entry per dependency present in
`<kotlin_root>/konan-data/dependencies`, a copy of `dependencies/.extracted`,
and a fresh **empty writable** `dependencies/cache/`. The materialisation
mechanism MUST copy or link only, MUST add no entry that is not in the bundle,
MUST reach no network, and MUST leave `<kotlin_root>` byte-unchanged. The
overlay is never fingerprinted, never published, and is removed with the
operation.

`dependencies/.extracted` is REQUIRED in the overlay, not optional: **MEASURED
(win)**, an overlay without it fails `Cannot find a dependency locally` with
exit 2 even though every dependency directory is present.

`dependencies/cache/` MUST NOT be a link to the bundle. It is where the
compiler takes its lock, so linking it would write into the fingerprinted tree.

**Obligation K-10 — the mechanism is per platform and is fixed by that
platform's qualification.** **MEASURED (win)**: directory **junctions**
(`New-Item -ItemType Junction`) over a write-denied bundle work, need no
privilege beyond the manager's own, and leave the bundle byte-unchanged.
**MEASURED (mac)**: a symlink farm works. Neither is assumed for an unqualified
platform.

### 5.3 No download, twice

The compile vector carries `-Xoverride-konan-properties=airplaneMode=true`, a
manager-owned constant no package byte can reach. The distribution ships
`airplaneMode = false`, so the override is load-bearing.

**MEASURED (win)**: with the override and a data directory missing a dependency,
the compiler fails
`Cannot find a dependency locally: lldb-2-windows. Set airplaneMode = false in
konan.properties to download it.` with exit 2 and zero `Downloading dependency`
lines. It creates exactly four entries in the data directory —
`dependencies/`, `dependencies/cache/`, a 0-byte `dependencies/.extracted`, and
a 0-byte `dependencies/cache/.lock` — all of it empty scaffold, all of it inside
the operation-private overlay, and none of it dependency content. That is why
the overlay is the writable surface and the bundle is not.

**MEASURED (win)**, independently: with the closure hydrated and outbound
network denied for the bundle JDK at the host firewall, the compile exits 0 and
logs no download line. The paired control fired: an empty data directory with
`airplaneMode=false` under the same denial reports
`Cannot download a dependency https://download.jetbrains.com/kotlin/native/lldb-2-windows.zip:
java.net.SocketException: Permission denied: getsockopt`, retries ten times with
backoff, obtains nothing, and fails the compile. Without that control the
zero-download result would prove nothing.

Both layers are required. The override is a driver property that holds on any
host; network denial is an operator or platform property that may be
unavailable. Section 11.1 A4 requires both.

## 6. The worker session and the argument vector

**Session.** Zero graph-phase commands, exactly one compile-phase command.
Decision 0008 section 7's "at most one" graph phase admits this. No retry, no
second phase, no daemon, no additional executable, no shell, no VCS operation,
no dependency download, no generator, no test, no run, no tool request. The
Stage A probe vectors of section 1.5 are manager-parent registry probes and are
not part of the worker session.

The Kotlin compile daemon is **forbidden**: `kotlin-daemon.jar` and
`kotlin-daemon-client.jar` ship in the distribution, and a daemon is a
persistent process outside the session shape. The driver passes no daemon
argument and MUST fail rather than fall back to one.

**Compile vector**, as measured on the candidate tuple:

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
  -target <resolved default native target token, section 1.5.2>
  -o <staging>\<command>
  <abs source 1> … <abs source N>
```

Binding rules:

1. The JVM options are `run_konan.bat`'s own, minus everything it takes from
   the environment. `-Duser.language`/`-Duser.country` are the one element added
   beyond the vendor vector, for locale determinism; the qualification measured
   the vector including them.
2. **Sources are enumerated by the manager**, recursively under `source_dir`,
   sorted by Unicode-scalar order of relative path, and passed as **absolute**
   paths. A directory is never passed as a source root: that hands file
   discovery to the compiler and would compile files the section 7 walk
   rejected.
3. **No argv token may begin with `@`** — see 7.2; this is what makes the
   absolute-path form a structural backstop rather than a convention.
4. No entry point, module name, opt-in marker, `-language-version`,
   `-api-version`, optimisation, debug, cache, memory-model, bitcode, library,
   or plugin argument is passed, and none is package-derivable.
5. `-target` names the host's own default native target only.
   **Cross-compilation is not admitted.** Its value comes from section 1.5.2 and
   from nothing else.
6. **MEASURED (win), obligation K-4 for the candidate tuple**: `-o <staging>\app`
   produces exactly `app.exe`, 570,368 B for the sample program, and **no**
   by-product beside it. The suffix is compiler-applied; the rename to the
   published name happens **inside operation-private staging only**, before
   hashing. K-4 is re-measured per tuple because the suffix and the by-product
   set are platform-dependent — **MEASURED (mac)** produced `app.kexe` plus an
   `app.kexe.dSYM/` directory.

## 7. Pre-compile rejection matrix

Decision 0008 section 7 requires an exhaustive, deterministic, pre-compile
rejection matrix. Kotlin's code-execution surfaces are an open set — a
general-purpose script engine, a script dialect the compiler can execute,
annotation processing, compiler plugins, C interop — so the matrix is a **closed
allow-list**, computed by a manager-side walk of the validated snapshot that
runs no compiler and reaches no network.

### 7.1 The allow-list, and it is the only thing that admits or rejects

| # | Admitted | Rule |
|---|---|---|
| A1 | directories | name matches `^[A-Za-z0-9_][A-Za-z0-9_.-]*$` |
| A2 | Kotlin sources | name matches `^[A-Za-z0-9_][A-Za-z0-9_.-]*\.kt$`, regular file |
| A3 | the module file | exactly `kotlin-native-module.json`, regular file, **directly** in the build root and nowhere else |

Anything else is `build_package_code_execution_forbidden`. The walk is total: it
classifies every entry it encounters, follows no symlink and no reparse point,
and has no depth, count, or size exemption that would leave an entry
unclassified.

The leading-character class excludes every dot-leading name — file **and**
directory alike, so `.gradle/`, `.mvn/`, `.idea/`, `.kotlin/` and every dotfile
are rejected — **and every name beginning with `@`**.

#### 7.1.1 Inert directories are admitted, deliberately

A directory is admitted on name shape alone. Because the walk is total, an
admitted directory can contain only A1 directories and A2 `.kt` files, and A3
exists in exactly one place. A directory named `gradle`, `kapt`, `ksp`,
`META-INF`, or `services` is therefore admitted **as a container** and can never
carry a Gradle script, a wrapper JAR or properties file, a plugin service
registration, a `.pro` file, or any other non-`.kt` regular file. The rejection
happens at the entry that would carry the executable meaning, never at an
ancestor's name.

This contract deliberately does **not** add a build-system directory-name
deny-list. Such a list would be exactly the enumerated deny-list this design
rejects for file names: it could not be exhaustive (`gradle-8`, `Gradle`,
`gradle.d`, a confusable homoglyph), it would need a case-folding and
normalization policy the protocol does not define, and it would close nothing
that the file-level rule does not already close. An earlier revision of this
document listed `gradle/` and `.gradle/` among the rejected build-system inputs
in section 7.2 while the normative classifier admitted the first of them; that
contradiction is resolved here in favour of the classifier.

### 7.2 Naming a rejection: an ordered, total classification

Section 7.2 does **not** admit or reject anything. Every row below applies only
to an entry section 7.1 has already rejected, and its only effect is to choose
the per-surface diagnostic carried in the `build_package_code_execution_forbidden`
payload. Rows are evaluated **in order**, the first match wins, and the last row
is a total catch-all, so exactly one diagnostic fires for every rejected entry.

| # | Rejected entry | Diagnostic |
|---|---|---|
| 1 | not a regular file and not a directory — symlink, junction or other reparse point, device, socket, FIFO | `kotlin_non_regular_entry_forbidden` |
| 2 | name begins with `@` | `kotlin_response_file_name_forbidden` |
| 3 | name ends with `.kts` — `build.gradle.kts`, `settings.gradle.kts`, any script source | `kotlin_script_source_forbidden` |
| 4 | name is one of `build.gradle`, `settings.gradle`, `gradle.properties`, `gradlew`, `gradlew.bat`, `gradle-wrapper.properties`, `gradle-wrapper.jar`, `pom.xml`, `mvnw`, `mvnw.cmd`, or ends with `.pro`, or is a regular file directly inside a `services` directory whose parent is `META-INF` | `kotlin_build_system_file_forbidden` |
| 5 | name ends with `.def`, `.h`, `.hpp`, `.c`, `.m`, `.mm`, `.cpp`, `.cc`, `.s`, `.S`, `.o`, `.obj`, `.a`, `.lib`, `.so`, `.dylib`, `.dll` | `kotlin_native_interop_input_forbidden` |
| 6 | name ends with `.klib`, `.jar`, `.aar` | `kotlin_prebuilt_library_forbidden` |
| 7 | any other rejected entry, file or directory, including every dot-leading name and every directory name outside A1 | `kotlin_non_source_entry_forbidden` |

Row 4's `META-INF/services` clause is a naming rule for a file that row 7 would
otherwise name generically; it rejects nothing that row 7 does not, and it does
not make the ancestor directory rejectable.

### 7.3 The `@` response-file channel, and the corrected reason

**MEASURED on both platforms.** The compiler strips a leading `@` from an argv
token and reads the remainder as a response-file path. Windows, run from the
probe directory:

| Argument token | File on disk | Expanded | Outcome |
|---|---|---|---|
| `@inject` | `inject` (containing `-version`) | yes | exit 0, `Kotlin/Native: 2.4.10` on stdout |
| `@.\inject` | `inject` | yes | exit 0, same |
| `@<abs>\inject` | `inject` | **yes** | exit 0, same |
| `<abs>\@inject` | `@inject` | no | `error: source entry is not a Kotlin file: …/@inject`, exit 1, stdout 0 bytes |
| `.\@inject` | `@inject` | no | same, exit 1, stdout 0 bytes |
| `@nonexistent` | — | n/a | the missing file does not abort argument processing; this run exits 1 with `error: you have not specified any compilation arguments` only because no argument survived it |

**MEASURED (mac)**: the same expansion column, and `@nonexistent` alongside
other arguments produces `warning: argfile not found` and continues. Both
readings agree that a missing response file is not itself a hard failure, which
is why a partial mitigation fails silently.

Expansion is therefore decided by the
**first character of the argv token**, not by whether the path is absolute. An
absolute package path is safe because it starts with `/` or a drive letter, and
a driver that ever prefixed a path with `@` would reopen the surface even in
absolute form. Because a missing response file is only a warning, a partial
mitigation fails silently.

Two independent layers close it, and both are required:

- **normative** — A1/A2/A3 reject the name before the compile phase, which is
  what decision 0008 section 7 demands;
- **structural backstop** — rule 3 of section 6: the driver never emits a token
  whose first character is `@`.

### 7.4 Surfaces closed structurally rather than by the walk

Argv-only, and unreachable because the closed command surface gives a package no
way to supply an argument and the driver's vector is fixed. They are listed so
the matrix is exhaustive over *surfaces*, and so that any future change letting
package data reach argv is visibly a change to this section.

| Surface | Flag | Why unreachable |
|---|---|---|
| compiler plugin by classpath | `-Xplugin=<path>` | not in the vector; no package-controlled argv |
| compiler plugin, new form | `-Xcompiler-plugin=…`, `-Xcompiler-plugin-order=…` | same |
| plugin option | `-P plugin:<id>:<opt>=<v>` | same |
| script templates | `-script-templates`, `-Xdefault-script-extension`, `-Xscript-resolver-environment` | same |
| explicit script execution | `-script`, `-expression`/`-e` | same, **and** reachable only through the `@` vector 7.3 rejects |
| toolchain re-pointing | `-Xkonan-data-dir`, further `-Xoverride-konan-properties` keys | same; the driver's own single override is a manager-owned constant |
| JVM passthrough | `-J…`, `-D…` | `run_konan` / `run_konan.bat` features; neither is ever run |

### 7.5 Network

No dependency resolution exists to perform: section 4 admits no dependency
declaration and 7.1 admits no prebuilt library, so there is nothing to fetch.
Section 5.3 closes the compiler's own dependency fetch twice.

## 8. Stage B — metadata disposition

Runs after local snapshot validation, or after exact external acquisition and
audit, and before any artifact-cache candidate is read or any compiler child is
started. Ordered steps per decision 0007 section 4: recompute the effective
requirement now that the descriptor requirement is readable, re-evaluate the
resolved version against the narrowed interval, gate on file shape, then
evaluate dispositions.

### 8.1 File-shape gate

`build_toolchain_metadata_mismatch`, before cache lookup, if any of:

1. `kotlin-native-module.json` is absent from the build root, is not a regular
   file, or is present anywhere other than directly in the build root;
2. it is not well-formed JSON, or is not a JSON object;
3. `schema_version` is absent or is not the integer `1`;
4. `kotlin_version` is absent;
5. any member other than those two is present;
6. a member is duplicated.

### 8.2 Disposition table

| File | Field | Disposition | Rule |
|---|---|---|---|
| `kotlin-native-module.json` | `kotlin_version` | `compared` | canonical triple; strictly above the resolved compiler triple ⇒ `build_toolchain_metadata_mismatch` |
| `kotlin-native-module.json` | `schema_version` | file-shape gate only | not a metadata source |

There is **no `forbidden` class**, because the field's value space is a version
and nothing else — no spelling of it names *where* a toolchain comes from.

### 8.3 The classifier is two classes

| Class | Condition | Disposition |
|---|---|---|
| C1 | matches the canonical triple grammar exactly | `compared` |
| C2 | anything else | `build_toolchain_metadata_mismatch` (8.1 step 4 or the grammar) |

Total by construction, with C2 as the mandatory catch-all. Because Curator owns
the grammar there is no document layer, no ecosystem grammar layer, and no
edition floor for the layers to be independent of. Decision 0007's alignment
properties reduce accordingly: the security partition `F` is empty, so P1
(`C ⊆ Upstream`) and P2 (`Upstream \ F ⊆ C`) collapse to the satisfiable
equality `C = Upstream`, where `Upstream` is Curator's own canonical grammar.
Both hold trivially and are checked as such. There is consequently no ecosystem
boundary probe to extend for Kotlin: decision 0007's obligation to measure two
independent acceptance layers is satisfied vacuously, because the ecosystem
supplies neither layer. The host-version gate decision 0007 requires each
ecosystem to name is `kotlin_version` versus the resolved triple in 8.2, and it
is deliberately outside the grammar.

## 9. Identity, cache, receipt, marker, claim

`curator-build-source-v1` is reused unchanged for both source modes. The
protected external snapshot key of `protocol/core.md` section 9.4 is unchanged.

The logical cache key is the SHA-256 of `CCJ-1` over the complete build input,
which binds:

| Input | Local | External |
|---|---|---|
| `receipt_schema_version` | `3` | `4` |
| `driver` | `const kotlin-native-v1` | `const kotlin-native-repository-v1` |
| source state | `curator-build-source-v1` over the raw snapshot | repository snapshot identity per decision 0005 |
| consuming command name | yes | yes |
| build root and `source_dir` | yes | yes |
| native target | the section 1.5.2 resolved default target token | same |
| `toolchain_identities` | ordered one-element array `[kotlin]` | same |
| policy object | closed, below | same |

Policy object, closed to exactly two members:

```json
{"execution_policy": "manager-worker-v2", "compile_profile": "kotlin-native-program-v1"}
```

`execution_policy` is the `const` decision 0008 section 2's closed table binds to
these identifiers. `compile_profile` is a `const` naming the session shape, the
source-enumeration rule, the fixed argument vector including the
`airplaneMode=true` override, the two Stage A probe vectors, and the
default-entry-point mapping together, so that a future semantic change to any of
them cannot happen without a cache-identity change.

The effective toolchain requirement and the `compatibility` set are gates, not
build inputs, so the wire `toolchain` object never enters a cache key, receipt,
marker, or claim. What enters is the resolved identity.

Install marker v4 records `driver`, `receipt_schema_version` and
`execution_policy` per entry; a reader validates both recorded values against
decision 0008 section 2's closed tables and rejects a mismatch rather than
inferring. Top-level `build_source` is REQUIRED exactly when at least one active
local build command of any admitted local driver exists.

Claim schema 4 asserts these identifiers only under section 11.5.

## 10. Artifact

`native-executable-v1`, and nothing else:

- exactly one bounded regular file, produced into operation-private staging,
  hashed there, published immutably under the manager-home mutation lock;
- named solely by the manager from the consuming manifest command key, as
  `bin/<command>.exe` on Windows and `bin/<command>` on Unix;
- directly executable by the host program loader using only base-installation
  libraries;
- never executed by the manager during validation, installation, status, repair,
  rollback, or garbage collection.

**MEASURED (win)** on the candidate tuple: the produced file is a PE image with
`MZ`/`PE\0\0` signatures and machine `0x8664` (AMD64), 570,368 B for the sample
program, runs and prints its output with exit 0. Its by-product set is empty:
after the compile, operation-private staging held only the JVM's own
`hsperfdata_*` directory and no compiler intermediates survived.

By-products, where a platform emits them, stay in staging and are discarded with
it: **MEASURED (mac)**, the `*.dSYM` bundle the compiler emits beside the
executable, `$TMPDIR/konan_temp*` intermediates, `.klib` intermediates, and the
compiler cache. None enters cache identity, the receipt, the marker, the shim
relationship, or publication.

Bit-reproducibility is not required. A linker-applied ad-hoc signature is
compiler output, not a manager signing step, and must be produced by the fixed
vector without selecting a signing identity, credential, or network interaction.

### 10.1 Platform libraries and the published-artifact dynamic dependency gate

**MEASURED.** The distribution ships per-target platform klibs under
`klib/platform/<target>/` — 8 for `mingw_x64`
(`builtin`, `gdiplus`, `iconv`, `opengl32`, `posix`, `windows`, `winhttp`,
`zlib`), 200-plus for each Apple target. Source importing them compiles and
links with no `-library` argument and no `.def` file, and it changes the
produced artifact's dynamic dependency set.

**Policy.** The fixed, distribution-owned platform library surface is
**allowed**: it is inside the fingerprinted bundle, a package cannot extend it
or name one, and rejecting it would require the manager to parse Kotlin source.
Everything a package could *supply* remains rejected by 7.1 — `.def` files,
headers, native sources, objects, archives, shared libraries, prebuilt `.klib` —
and `cinterop` is a second tool the session admits in neither position. The
accurate capability statement is **no user-defined C interop**, not "no C
interop".

**Normative gate.** Because the artifact's dynamic dependency set is a function
of package source, decision 0008 section 3's base-installation clause cannot be
discharged by any pre-compile walk. In operation-private staging, before hashing
and before publication, the manager MUST read the produced file's dynamic
dependency list — the PE import directory on Windows, the Mach-O load commands
or ELF `DT_NEEDED` entries elsewhere — and MUST fail with
`build_artifact_class_unsupported` if any entry is outside the closed
base-installation library allow-list the platform matrix fixes for that tuple.
Reading a file's headers is not executing it, so this does not touch decision
0008 section 3's "never executed by the manager" clause. The manager parses the
image itself; it MUST NOT invoke a tool from the bundle or the host to do it.

**Obligation K-9 — each qualified tuple supplies that allow-list, and a tuple
with no allow-list cannot be qualified.**

`windows/amd64` base-installation library allow-list, **MEASURED (win)** by
parsing the PE import directory of two produced artifacts:

| Sample | Size | Imports |
|---|---|---|
| plain `fun main() { println(…) }` | 570,368 B | `KERNEL32.dll`, `msvcrt.dll` |
| `import platform.posix.getpid` + `import platform.windows.GetTickCount` | 582,656 B | `KERNEL32.dll`, `msvcrt.dll` |

The allow-list for this tuple is therefore exactly
**`{KERNEL32.dll, msvcrt.dll}`**, and **this table is the single normative
source for it**. Section 11.6's K-9 row, the section 14 artifact-gate vectors,
and decision 0010 section 9 restate this set and MUST NOT diverge from it; an
earlier revision of the K-9 row carried a wider four-entry set that no
measurement supports, and that row is corrected. Both are present in every
supported Windows
installation. The platform-library sample added **no** import, because the two
bindings it uses resolve into `KERNEL32.dll`; the surface still had to be
measured, because on other tuples it does move the list — **MEASURED (mac)**,
for reference only since that tuple is unsupported, `import platform.Foundation`
adds `/usr/lib/libresolv.9.dylib` to a set that is otherwise
`libSystem.B.dylib`, `libc++.1.dylib`, `libobjc.A.dylib`, `Foundation` and
`CoreFoundation`.

Any import outside the two measured entries is
`build_artifact_class_unsupported`. That includes imports a MinGW-linked binary
could plausibly acquire — `libgcc_s_seh-1.dll`, `libwinpthread-1.dll`,
`libstdc++-6.dll`, all present in the bundled MinGW runtime and in no base
Windows installation — and it also includes Windows system DLLs that a wider
program would reach through the distribution's other platform klibs
(`USER32.dll`, `ADVAPI32.dll`, `GDI32.dll`, `GDIPLUS.dll`, `OPENGL32.dll`,
`WINHTTP.dll`). **The set is deliberately what was measured, not what is
plausible.** Widening it is a re-qualification: a run of A6 whose sample
actually produces the new import, recorded the same way. A closed set that is
smaller than reality fails safe and is visibly extendable; a closed set built
from assertion fails open exactly once and silently.

### 10.2 Signing and credential boundary

Unchanged from decision 0008 section 9, restated because it is easy to reopen:

- neither driver performs manager post-build signing, timestamping, or
  notarization;
- no manifest, descriptor, module file, or repository byte may select a signing
  identity, certificate, entitlement, provisioning profile, keychain, or
  notarization credential — no such field exists, and none may be added;
- `codesign`, `productsign`, `notarytool`, `stapler` and `signtool.exe` MUST NOT
  appear anywhere in the process graph;
- a platform policy that requires a locally signed binary MUST reject the build
  until the separately versioned and reviewed signer profile of
  `protocol/core.md` section 12.2 exists. It MUST NOT be answered by a
  self-signed identity, an ad-hoc `codesign` invocation, or a
  quarantine-attribute removal;
- credentials, host-verification state, transport executables, proxy policy,
  timeouts and authentication modes stay operator-owned and MUST NOT appear in a
  manifest, descriptor, repository, module file, compiler environment, receipt
  trust field, or marker.

## 11. Platform matrix and qualification

`{(windows, amd64)}` is the **candidate** `platforms` set for both identifiers,
and the only tuple that may ever enter the shipped set from this record. It
enters that set in the change described by the section 1.4 binding rule, and not
before. No other tuple is claimed or claimable here.

### 11.1 The acceptance test

A tuple is admitted only when all of A1–A9 are discharged with recorded argv and
real exit codes. A1–A7 are **host requirements**, discharged by a run on that
exact tuple on an immutable native host. A8 and A9 are **corpus requirements**:
they execute no compiler, need no host, and are discharged by the section 14
conformance vectors. A tuple with A1–A7 discharged and A8/A9 outstanding is an
**A1–A7 host-qualified candidate** and is not admitted.

| # | Requirement | `windows/amd64` |
|---|---|---|
| A1 | The bundle is curated per 1.3 from a checksum-verified official archive and a checksum-verified JDK; `primary_relpath` resolves to a regular executable; both probe vectors and both normalizations of 1.5 are reproduced on that host | **PASS** — digests matched the published values; `jdk\bin\java.exe` is a regular 50,344 B executable; P1 and P2 exit 0 with the anchored forms |
| A2 | The full compile runs with `PATH` set to a manager-owned directory that resolves nothing, **and** the paired control through the shipped launcher fails on a `PATH` resolution. Without the control firing the negative proves nothing | **PASS** — compile exit 0; `konanc.bat` exit 9009, `'"java"' is not recognized` |
| A3 | Under a **kernel-level process trace that records every process start in the window by resolved absolute image path** — not an iterative-denial enumeration — the compile exits 0 and every image below the compiler is a regular file inside `<kotlin_root>` or the operation-private overlay. The trace's completeness control MUST be shown to fire on a deliberately external executable — obligation K-2 | **PASS** — ETW `Microsoft-Windows-Kernel-Process`; exactly two children, `clang++.exe` and `ld.lld.exe`, both inside `<kotlin_root>`; control `where.exe` recorded |
| A4 | With `airplaneMode=true` **and** all network denied, the compile exits 0, logs no download, and `<kotlin_root>` is byte-identical before and after; every write lands in operation-private state — obligation K-3 | **PASS** — see 5.2 and 5.3; tree digest unchanged across every operation in the run |
| A5 | Exactly one file is produced for publication; its exact name and compiler-applied suffix are recorded; renaming happens inside staging only; every by-product stays in staging — obligation K-4 | **PASS** — `-o app` ⇒ `app.exe`, no by-product |
| A6 | The published file is a native executable for the tuple, runs, and every entry of its dynamic dependency list is inside that tuple's closed base-installation allow-list, which this run supplies. The sample MUST include a source importing distribution platform libraries, because that is what moves the list — 10.1 | **PASS** — PE AMD64, runs; both samples import exactly `KERNEL32.dll` and `msvcrt.dll`, the whole 10.1 allow-list |
| A7 | The default native target is read from the 1.5.2 probe vector and mapped to `(operating_system, architecture)` — obligation K-6 | **PASS** — `mingw_x64 (default)` ⇒ `(windows, amd64)`, equal to the host pair |
| A8 | 7.1 is exercised with the admitted cases of 7.1.1 — nested directories, an inert `gradle/` and an inert `META-INF/services/` holding only `.kt` files, the module file in the build root — and with one rejected entry per row of 7.2, including a name beginning with `@`, a `.kts` file, a `.klib`, and a dot-leading directory | **NOT DISCHARGED** — owned by the section 14 vectors, which `TASK-260728-251p01` authors; the classifier is manager-side and needs no host, but no corpus exists yet |
| A9 | `compatibility` gains the tested family, and only that family, once the driver's conformance vectors pass against it | **NOT DISCHARGED** — `{(2, 4)}` is the candidate family under the 1.4 binding rule; it is admitted when those vectors pass and not before |

**`windows/amd64` is an A1–A7 host-qualified candidate, not an admitted tuple.**
A1–A7 were discharged on the host. A8 and A9 are discharged by the conformance
corpus rather than by a host run — the allow-list walk executes no compiler and
the compatibility set is manager policy — and that corpus does not exist yet.
Under the admission rule above, the tuple therefore stays a candidate, section
1.4's `platforms` and `compatibility` stay candidate sets, and both retirement
branches of 11.5 stay open. `TASK-260728-251p01` owns the transition; an
implementation MUST NOT anticipate it.

### 11.2 macOS — measured unsupported

`macos/arm64` and `macos/amd64` are **not admissible**, on two independent
grounds, either one sufficient.

**Ground one — the process closure.** **MEASURED (mac)**: under exec containment
allowing only the JDK root, the distribution and the data directory, a
hello-world `-produce program -target macos_arm64` fails at
`CurrentXcode.bash(Xcode.kt:144)`. Two iterative-denial runs were made:

| Run | Seed | Discovered | Result |
|---|---|---|---|
| `run7` | empty | `/bin/bash`, `/usr/bin/xcrun` required; its raw output additionally shows `/usr/bin/xcode-select` and `/usr/libexec/PlistBuddy` denied through `bash` and `<Xcode>/Contents/Developer/usr/bin/xcodebuild` denied through `xcrun` | stopped — the `xcrun` denial message has a different shape than the JVM's |
| `run8` | those four | `<Xcode>/…/XcodeDefault.xctoolchain/usr/bin/ld`, `…/usr/bin/dsymutil` | **exit 0** with six externals allowed |

So the **union of externals observed** across both runs is seven, and the set
**sufficient** for a successful compile is six; `run8`'s final
`evidence/allowed-externals.txt` correctly holds those six. The difference is
path-dependent: with `/usr/bin/xcode-select` allowed the compiler does not fall
back to `xcrun xcodebuild -version`. An earlier revision of this document called
the set "exactly seven", conflating the two; that claim is withdrawn.

Iterative denial establishes that each listed executable is required on the path
taken and that the listed set is sufficient. It does **not** establish that no
other executable is spawned on any path, so **no completeness claim is made for
macOS**. The exclusion does not need one. Decision 0008 section 6 item 3 is
violated by the first external executable; `/bin/bash`, `/usr/bin/xcode-select`,
`/usr/libexec/PlistBuddy` and `/usr/bin/xcrun` are absolute OS paths compiled
into the compiler that no operator-curated root can contain; and ground two is
independent of the process count entirely. This is also why A3 now requires a
kernel-level trace rather than iterative denial for a tuple that is to be
*admitted*: sufficiency is enough to exclude, and only completeness is enough to
qualify.

**MEASURED (mac)**: no manager-fixed input removes them — with
`ignoreXcodeVersionCheck=true` and `targetToolchain`, `targetSysRoot` and
`additionalToolsDir` all overridden to absolute local paths, the compile still
fails with `Cannot run program "/usr/bin/xcrun"` at
`CurrentXcode.getToolchain(Xcode.kt:92)` ←
`AppleConfigurablesImpl.getAbsoluteTargetToolchain(Apple.kt:45)`. The cause is
structural: `konan.properties` declares the Apple toolchain, sysroot and addon
as `remote:internal` — all 11 of its `remote:internal` declarations are Apple —
and `XcodePartsProvider` has exactly two implementations: `InternalServer`,
gated on `KONAN_USE_INTERNAL_SERVER` and pointing at
`https://repo.labs.intellij.net/kotlin-native`, and `Local`, the host's Xcode.

**Ground two — cache identity.** The Apple toolchain and SDK are in no
fingerprinted tree, so the build input cannot bind them and two hosts with
different Xcode versions would alias in the cache.

An implementation MUST fail `platform_unsupported` on macOS. It MUST NOT resolve
a host tool, ship a shim, declare the SDK data-only while executing from it, or
publish a second file.

### 11.3 Windows — A1–A7 host-qualified candidate

`windows/amd64` is an **A1–A7 host-qualified candidate**: A1–A7 were discharged
on Windows 10 Pro 10.0.19045.6456, AMD64. A8 and A9 are the corpus-owned
requirements named in 11.1, they are **not discharged**, and until they are the
tuple is not admitted. The reason macOS fails does not apply, and this is
now a measurement rather than a reading of distribution data: the entire
toolchain closure for `mingw_x64` — `msys2-mingw-w64-x86_64-2` as both target
toolchain and sysroot, `llvm-21-x86_64-windows-essentials-150` as the LLVM
home — lives under `<kotlin_root>/konan-data/dependencies`, and the kernel trace
of a successful compile shows only two children, both from that LLVM
dependency.

An implementation MUST NOT resolve `cmd.exe`, `powershell.exe`, `link.exe`,
`cl.exe`, `lib.exe`, `vswhere.exe`, or a Visual Studio activation script. None
appeared in the trace, and their appearance in a future release is a
qualification regression that MUST retire the tuple rather than be tolerated.

`windows/arm64` is a separate tuple, is **not** implied by `windows/amd64`, and
is not claimed.

### 11.4 Linux — excluded, then candidate

Excluded from the protocol until `TASK-260728-1skseh`, then qualified by
`TASK-260728-3u1nho` with the identical A1–A9 test. The same properties reading
applies: `targetToolchain.linux_x64 = $gccToolchain.linux_x64/…`,
`targetSysRoot.linux_x64 = $gccToolchain.linux_x64/…/sysroot`,
`llvm.linux_x64.user = llvm-21-x86_64-linux-essentials-116`; none is
`remote:internal`. That is a reading, not a claim.

### 11.5 Retirement — both branches are open

The retirement trigger of decision 0010 section 12 is: if no tuple has passed
A1–A9 when `TASK-260728-251p01` mints manifest schema 8, both identifiers are
retired unused. `windows/amd64` has passed A1–A7 and no tuple has passed A1–A9,
so **the platform branch remains armed**. It is disarmed only when the section
14 corpus discharges A8 for the classifier and A9 for the 2.4 family, in the
change that mints schema 8.

The compatibility branch of 1.4 is armed on the same event: if those vectors do
not pass against the 2.4 family, the entry has no admissible family, every host
fails `build_toolchain_untested_release`, and shipping it would be shipping an
entry that can never succeed.

Both branches therefore resolve at one point — the schema-8 change — and both
resolve the same way. If the corpus passes, `platforms` becomes
`{(windows, amd64)}` and `compatibility` becomes `{(2, 4)}`. If it does not,
both `kotlin-native-v1` and `kotlin-native-repository-v1` are **retired unused**.
Retired means what decision 0008 section 2 says: not reassigned to another
language, backend, artifact class, or source mode, and not enabled by relaxing
another driver.

### 11.6 Open per-tuple obligations

| # | Question | `windows/amd64` | Failure consequence elsewhere |
|---|---|---|---|
| K-2 | every spawned child inside `<kotlin_root>` or the overlay | satisfied (kernel trace) | that tuple is excluded (macOS: **fails**) |
| K-3 | no download, bundle byte-unchanged | satisfied | that tuple is excluded |
| K-4 | exact produced filename, suffix and by-product set | `app.exe`, no by-product | blocks A5 |
| K-6 | default native target token and mapping | `mingw_x64` ⇒ `(windows, amd64)` | blocks A7 |
| K-9 | the tuple's closed base-installation library allow-list | exactly `KERNEL32.dll`, `msvcrt.dll` — the measured set of 10.1, which is normative | blocks A6 |
| K-10 | the overlay materialisation mechanism available on that platform | directory junctions | blocks A4 |
| K-11 | the bundle is read-only to the manager's account through ownership, not a per-user deny under a Full-Control group | curation obligation, 1.3 step 7 | operator configuration defect |

## 12. Diagnostics

| Code | Fires when |
|---|---|
| `build_package_code_execution_forbidden` | any 7.1 allow-list rejection, with the ordered 7.2 per-surface diagnostic in the payload |
| `build_toolchain_metadata_mismatch` | 8.1 file-shape gate, or `kotlin_version` strictly above the resolved triple |
| `build_toolchain_requirement_invalid` | `toolchain.id` not `kotlin`; malformed requirement literal |
| `build_toolchain_requirement_unsatisfiable` | empty intersection of baseline, manifest and descriptor requirements |
| `build_toolchain_version_undetermined` | P1 stdout unmatched or multiply matched; P2 non-zero exit, unbounded output, ungrammatical line, or a `(default)` count other than 1 |
| `build_toolchain_prerelease_unsupported` | P1 group 4 non-empty |
| `build_toolchain_untrusted` | a declared `<kotlin_root>` that does not exist, or whose `primary_relpath` is missing or not a regular executable |
| `build_toolchain_untested_release` | resolved family not in `compatibility` — every family other than 2.4 |
| `build_toolchain_platform_unsupported` | `check` `host_pair`: host pair not `(windows, amd64)`, which is the permanent outcome on macOS; `check` `native_target`: the P2 token is unmapped or maps to a pair other than the host pair |
| `build_artifact_class_unsupported` | the 10.1 published-artifact gate, or a platform that cannot produce a single directly loadable file |
| `build_descriptor_driver_unsupported` | schema-1 descriptor named by a `kotlin-native-repository-v1` command |
| `build_descriptor_schema_unsupported` | unsupported descriptor version |
| `build_execution_control_unavailable` | any mandatory portable control unavailable, unchanged under `manager-worker-v2` |

## 13. Capability limitations

Authoring guidance (`TASK-260728-2uh7em`) MUST carry all five:

1. **No third-party dependencies.** No `.klib` may be supplied or named, and the
   vector passes no `-library`. A build root compiles against the distribution's
   own libraries only.
2. **No user-defined C interop.** `cinterop` is a second tool and a second
   command; `manager-worker-v2` admits neither. The distribution's own platform
   bindings are available and are subject to the 10.1 gate.
3. **The build root is not an IDE project.** 7.1 rejects every Gradle and Maven
   file, so an author keeps the IDE project outside the build root. A directory
   named `gradle` may exist and may hold only `.kt` sources (7.1.1). Build roots
   are context-excluded and never runtime-copied, so this costs the agent
   nothing and costs the author a duplicated source layout.
4. **No cross-compilation.** One host builds for its own default target only.
5. **`windows/amd64` only, and no macOS.** The only tuple that can ever be
   admitted from this record is `windows/amd64`, and it is admitted only when
   the 11.1 corpus requirements pass. macOS is permanently unsupported (11.2)
   and Linux is outside the protocol's platform set (11.4). The driver fails
   closed everywhere else and falls back to nothing.

## 14. Conformance vector inventory

Vectors are authored by `TASK-260728-251p01`.

| Group | Cases | Notes |
|---|---|---|
| reserved-identifier rejection | 10 | each frozen manifest, descriptor, receipt, marker and claim schema rejects both identifiers |
| command shape | 8 | `buildCommandV8` and `repositoryBuildCommandV2` with the `kotlin-native` consts; missing member; extra member; `toolchain.id` not `kotlin` |
| descriptor | 4 | schema-2 positive; schema-1 with a Kotlin driver ⇒ `build_descriptor_driver_unsupported`; unknown schema; command/descriptor driver mismatch |
| module file shape | 12 | six 8.1 gate cases, plus duplicate member, non-object, wrong `schema_version` type, absent file, file outside the build root, file not a regular file |
| `kotlin_version` classifier | 10 | C1 equal, below, above ⇒ mismatch; C2 for prefix, prerelease, build metadata, leading zero, two-component, wildcard, empty |
| allow-list — admitted | 6 | nested directories; an inert `gradle/` holding only `.kt`; an inert `META-INF/services/` holding only `.kt`; the module file directly in the build root; a `.kt` name at the shape boundary; an empty admitted directory |
| allow-list — rejected | 9 | one entry per ordered row of 7.2, including the `@`-name case, a `.kts` file, a `.klib`, a `META-INF/services` registration file, a dot-leading directory, and a reparse point |
| probe normalization | 10 | P1 exact, prerelease, unmatched, multiply matched, CRLF and LF terminators; P2 with zero `(default)` lines, two `(default)` lines, an ungrammatical line, and an unmapped default token |
| requirement intersection | 6 | baseline ∩ manifest ∩ descriptor, including the non-empty-but-excludes-resolved case decision 0007 section 4 names |
| policy and identity | 6 | policy object closed to its two members; `execution_policy` const; `compile_profile` const; single-element `toolchain_identities`; v1/v2 non-aliasing; receipt schema 3 vs 4 |
| artifact gate | 5 | the allow-list fixture is exactly `{KERNEL32.dll, msvcrt.dll}` per 10.1; an import list equal to it publishes; a subset of it publishes; an import list adding any other name — `ADVAPI32.dll` and `USER32.dll` are the two the corpus MUST cover, because an earlier revision wrongly allowed them — ⇒ `build_artifact_class_unsupported`; a second produced file is never published; a by-product stays in staging |
| platform | 4 | `(windows, amd64)` admitted; every other host pair ⇒ `platform_unsupported` with `check` `host_pair`; macOS ⇒ `platform_unsupported` permanently; a P2 token mapping to a non-host pair ⇒ `platform_unsupported` with `check` `native_target` |

Every vector declares the `compatibility` set, the `platforms` set and the 10.1
base-installation allow-list as fixture input, so outcomes are deterministic
across managers, exactly as decision 0007 section 1.1.1 requires.

This corpus is what discharges A8 and A9. Landing it passing, in the change that
mints manifest schema 8, is the event that turns the section 1.4 candidate sets
into the shipped `platforms` and `compatibility` values; landing it failing is
the event that fires both retirement branches of 11.5.
