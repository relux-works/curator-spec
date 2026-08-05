# Rust build drivers: `rust-v1` and `rust-repository-v1`

Implementation-ready reference for decision
[0009](../decisions/0009-rust-driver-pair.md), under the boundary of decision
[0008](../decisions/0008-additional-language-driver-boundary.md) and the shared
toolchain contract of decision
[0007](../decisions/0007-compiled-build-toolchain-preflight.md).

Both identifiers are **reserved**, not admitted. Until `TASK-260728-251p01`
moves them into the admitted wire driver set in the same change that mints
receipt schemas 3 and 4, every schema MUST reject them and a manager MUST treat
each as an unknown driver.

Every measured value in this document was produced on macOS 26.5 arm64 with
Rust 1.91.0 (`rustc 1.91.0 (f8297e351 2025-10-28)`, `cargo 1.91.0 (ea2d97820
2025-10-10)`) against a directly resolved toolchain root, never a `rustup` shim.
Nothing here is a platform claim.

## 1. `toolchain-registry-v1`: the `rust` entry

| Field | Value |
|---|---|
| `toolchain_id` | `rust` |
| `primary_relpath` | `macos`: `bin/cargo` |
| `probe` | `macos`: three vectors, section 1.1 |
| `normalization` | `rust.rustc.vV.release`, section 1.2 |
| `fingerprint_algorithm` | `curator-rust-toolchain-v1`, section 2 |
| `baseline` | `{"kind":"at_least","min":"1.91.0"}` |
| `compatibility` | families `{(1, 91)}`; family granularity `(major, minor)` |
| `platforms` | `(macos, arm64)` |
| `companions` | none |
| `link_support_roles` | `macos`: `["platform-sdk"]` |
| `metadata_sources` | `Cargo.toml` `package.rust-version`; `rust-toolchain.toml`; `rust-toolchain` |

Driver mapping: `rust-v1` and `rust-repository-v1` both map to primary `rust`
with no companion. A driver with no registry entry is unsupported; there is no
generic mapping and no fallback.

`link_support_roles` is a per-operating-system ordered closed list of roles the
Rust distribution does not itself provide. It is a manager-owned registry field
in the same sense as `platforms`; a package MUST NOT name a role, and no
manifest, descriptor, repository byte, environment value or `PATH` entry may
supply or influence one. An entry that declares a role for an operating system
outside its `platforms` set is unreachable data and fails the same release gate
that checks guidance reachability.

`platforms` holds exactly one pair. `(macos, amd64)`, Windows and Linux are
qualification obligations with the acceptance tests of section 13, not claims.
On a host whose pair is not in `platforms`, Stage A fails
`build_toolchain_platform_unsupported` with `check` = `host_pair`, before
resolution, on registry data alone.

### 1.1 Probe vectors

Run once per operation from the manager parent, from a manager-owned empty
working directory, under the operation-private environment of section 6, with
`<root>` the resolved Rust distribution root:

```text
<root>/bin/rustc -vV
<root>/bin/rustc --print host-tuple
<root>/bin/cargo --version
```

Measured output, verbatim:

```text
$ rustc -vV
rustc 1.91.0 (f8297e351 2025-10-28)
binary: rustc
commit-hash: f8297e351a40c1439a467bbbb6879088047f50b3
commit-date: 2025-10-28
host: aarch64-apple-darwin
release: 1.91.0
LLVM version: 21.1.2

$ rustc --print host-tuple
aarch64-apple-darwin

$ cargo --version
cargo 1.91.0 (ea2d97820 2025-10-10)
```

**Measured**: that `rustc -vV` stdout is 192 bytes over 7 lines with exactly one
terminal LF, no CR and no NUL; that `cargo --version` stdout is 36 bytes over
one line. Both streams are multi-use: they are the input to the normalization of
section 1.2 *and* the payloads of the two version records of section 2.3, and
each is read exactly once per operation.

`rustc --version` is deliberately not used: it embeds the commit hash on the same
line, so `-vV` is the narrower surface. The `host:` line of `-vV` carries the
same value as `--print host-tuple` on this host and is deliberately not used as
the target probe, for the same reason.

### 1.2 Normalization — `rust.rustc.vV.release`

Take the `rustc -vV` **V payload** produced by section 2.3 — that is, the
normalized stdout with its single terminal LF already removed. Split it on LF.
Exactly one line MUST match, anchored over the whole line:

```text
^release: (0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?$
```

Groups 1 through 3 are the canonical triple. A non-empty group 4 is a
prerelease: `build_toolchain_prerelease_unsupported`. Zero matches or more than
one match is `build_toolchain_version_undetermined`, never a default.

The **C payload** of section 2.3 MUST match, anchored over the whole payload:

```text
^cargo (0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)? \([0-9a-f]+ [0-9]{4}-[0-9]{2}-[0-9]{2}\)$
```

Its triple MUST equal `rustc`'s and its group 4 MUST be empty. A mismatch, or a
prerelease marker on either, is `build_toolchain_version_undetermined` — a root
whose launcher and compiler disagree is not a usable identity, and the driver
starts both.

Normalization and identity therefore read the same two byte streams. There is no
second invocation of either probe and no second normalization rule.

Architecture mapping for `platforms`: the trailing components of the host tuple
map `aarch64` to `arm64` and `x86_64` to `amd64`; the operating-system component
maps `apple-darwin` to `macos`, `pc-windows-*` to `windows`, `unknown-linux-*`
to `linux`. Any other tuple is `build_toolchain_platform_unsupported` with
`check` = `reported_target`.

### 1.3 Native target admission

Representability and admission are different questions and the ecosystem answers
only the first cheaply.

**Measured**: `rustc --print target-libdir --target x86_64-unknown-linux-gnu`
exits **0** and prints
`<root>/lib/rustlib/x86_64-unknown-linux-gnu/lib` on a host where that directory
does not exist; `cargo build --target x86_64-unknown-linux-gnu` then fails only
after emitting `Compiling probe-positive v0.1.0`, that is after the compile
phase has begun. An unknown triple is refused earlier: `--print target-libdir
--target not-a-real-target` exits **1** with `error: error loading target
specification: could not find specification for target "not-a-real-target"`.

Admission is therefore a manager-side check inside the fingerprinted tree, run
in Stage A after normalization:

1. `<root>/lib/rustlib/<native-tuple>/lib` MUST be an existing directory inside
   the fingerprinted Rust distribution root;
2. it MUST contain at least one regular file whose name matches
   `^libstd-[0-9a-f]+\.rlib$`.

A failure is `build_toolchain_platform_unsupported` with `check` =
`reported_target`, before source acquisition, before cache lookup and before any
compiler child. `rustc --print target-list` and `--print target-libdir` MUST NOT
be used as the admission test.

## 2. `curator-rust-toolchain-v1`

### 2.1 Resolution

The Rust distribution root and every `link_support_roles` root are resolved
through exactly the two declaration channels of decision 0007 section 3 —
`operator_config` then `bundled` — and through nothing else. `PATH`, the
inherited environment (including `RUSTUP_HOME`, `CARGO_HOME`, `RUSTC`,
`RUSTUP_TOOLCHAIN`, `DEVELOPER_DIR`, `SDKROOT`, `TOOLCHAINS`), a runtime root,
project `.agents/bin`, any shim, a manifest or descriptor value, `xcrun`,
`xcode-select` and any version-manager wrapper (`rustup`, `asdf`, `mise`) are
forbidden origins with the diagnostics decision 0007 section 5 fixes. An
operator MAY configure the concrete root that `rustup` produced; the manager
resolves that root directly and never through the shim.

Inside the resolved Rust distribution root the manager requires three regular
executables, and starts no other program below the worker:

| Relpath | Role |
|---|---|
| `bin/cargo` | trusted launcher, the `primary_relpath` |
| `bin/rustc` | compiler |
| `lib/rustlib/<native-tuple>/bin/rust-lld` | linker |

Each MUST be a regular executable inside the tree being fingerprinted, never a
wrapper and never outside it. A missing or non-regular member is
`build_toolchain_untrusted` with `substep` = `shape`.

The list is three, and staying at three is a **conclusion of the gates**, not a
property of Rust. **Measured**: an admitted `[profile.release]` carrying
`split-debuginfo = "packed"` added a fourth, `PATH`-resolved `dsymutil`, under
this exact contract's pinned pipeline, and `cargo build` still exited 0. The
list survives only because section 4.7 rejects that key from snapshot bytes and
section 6 pins `-Csplit-debuginfo`. Any future change that admits a new
manifest surface MUST re-run the acceptance test of section 13.1, step 4
included, before this table may be restated.

### 2.2 Identity

`curator-rust-toolchain-v1` produces exactly:

```json
{
  "algorithm": "curator-rust-toolchain-v1",
  "rust_version": "release: 1.91.0",
  "cargo_version": "cargo 1.91.0 (ea2d97820 2025-10-10)",
  "launcher_relpath": "bin/cargo",
  "rustc_relpath": "bin/rustc",
  "linker_relpath": "lib/rustlib/aarch64-apple-darwin/bin/rust-lld",
  "roots": [
    {"role": "rust-distribution", "tree_sha256": "sha256:<hex>"},
    {"role": "platform-sdk",      "tree_sha256": "sha256:<hex>"}
  ],
  "closure_sha256": "sha256:<hex>"
}
```

The `rust_version` member is the single whole `release:` line extracted by
section 1.2 from the V payload — a one-line human-readable member, not the whole
verbose stream. The `cargo_version` member is the whole C payload, which is one
line by construction. Neither member is the record payload of section 2.3; the
records bind more bytes than the members display, and section 2.3 is normative
for what is hashed.

`roles` is the closed token set `{rust-distribution, platform-sdk}`. No root
path appears anywhere in the identity: toolchain location is not portable
identity. The `roots` array is ordered `rust-distribution` first, then each
`link_support_roles` entry in its registry order.

Per-root `tree_sha256` uses the walk, ordering, record framing, link rules and
`kind` alphabet of `curator-go-toolchain-v1` — walk without following links, the
root itself is not a record, relative components must be valid Unicode scalar
values, `/`-joined paths encoded as UTF-8 without case folding or normalization,
duplicate encoded paths and special files rejected, symlinks relative and
non-dangling and resolving within the root with independent tree records for
their referents, hard links as independent regular-file records, path bytes
sorted in unsigned bytewise order — with SHA-256 initialized by the exact ASCII
`curator-rust-toolchain-v1/<role>` followed by `0x00` and each entry appended as:

```text
kind || uint64be(path_byte_length) || path_utf8 ||
uint64be(payload_byte_length) || payload
```

The `rust-distribution` root appends the two version records of section 2.3
after the last walked entry, in the order `V` then `C`. A `platform-sdk` root
appends no version record.

`closure_sha256` initializes SHA-256 with the exact ASCII
`curator-rust-toolchain-v1/closure` followed by `0x00` and appends, for each
element of `roots` in order:

```text
ASCII("R") || uint64be(role_byte_length) || role_ascii ||
uint64be(32) || raw_tree_digest_bytes
```

so a one-root closure and a two-root closure can never collide even if their
tree digests coincide. Prefix every emitted digest with `sha256:`.

Permissions, ownership, timestamps, ACLs and extended attributes are not hash
inputs, but the three executables of section 2.1 MUST be regular and executable
at use time. Every root MUST remain unchanged through the last child exit, and
every identity MUST be re-verified after the last child exits and before
publication; a change rejects the operation before publication.

**Measured cost**, same host: the Rust distribution root is 657 MB across 167
regular files and hashes in 1.73 s wall clock; the macOS SDK root is 261 MB
across 32,345 regular files and 7,448 symlinks and hashes in 9.01 s. The cost is
per operation and per root and MUST NOT be memoised across operations.

### 2.3 The two version records and their normalization

The `V` and `C` records are the only records with an empty path. Their payloads
are the normalized stdout of `rustc -vV` and of `cargo --version` respectively.
`rustc -vV` stdout is **multiline** — measured, 7 lines — so the normalization
is defined over a multiline stream, and a single-line rule would reject the
toolchain the entry admits.

`normalize(stdout) -> payload`, in this order. Every failure is
`build_toolchain_version_undetermined`; none of them has a default:

1. `len(stdout) <= 8192` bytes. This is the **raw capture bound**, a resource
   limit on how much of the child's stdout is read at all. It is not the
   admission bound; see "why there are two bounds" below.
2. `stdout` is valid UTF-8.
3. `stdout` contains no U+0000.
4. Replace every CRLF (`0x0D 0x0A`) byte pair with a single LF (`0x0A`). This is
   the only rewriting step, and it exists so that a Windows-hosted probe and a
   Unix-hosted probe of the same distribution produce the same payload. It runs
   **before** the admission bound, so line endings cannot change a verdict.
5. `len(folded) <= 4096` bytes. This is the **semantic bound**, and it is the
   only length rule that decides admission.
6. After step 4 the stream contains no CR. A remaining CR — a bare `0x0D` — is a
   rejection, not a line terminator.
7. The stream is at least 2 bytes, its last byte is LF, and the byte before it
   is not LF. That is the exact terminal-LF rule: exactly one terminator, and no
   trailing blank line.
8. Remove that final LF. The remainder is the `payload`.
9. The `payload` is non-empty and contains no U+007F and no scalar below U+0020
   other than LF.

**Why there are two bounds, and why 8192 is the right one.** Folding replaces a
two-byte CRLF with one byte and rewrites nothing else, so for every stream

```text
len(folded) >= ceil(len(raw) / 2)
```

and therefore `len(raw) > 8192` implies `len(folded) >= 4097`. The raw bound can
only ever reject a stream that the semantic bound would reject anyway: it is
non-lossy by construction, and 8192 is the smallest bound with that property,
because 4096 CRLF pairs is exactly 8192 raw bytes and folds to exactly 4096.
**Measured**: that maximal expansion passes the raw bound, reaches the semantic
rules and is decided by the terminal-LF rule, not by the capture limit; one pair
beyond it is rejected by the capture limit, and its folded length would have been
4097 in any case. Vectors N18 and N19 check both halves, N19 over every raw
length from 0 to 32768.

Applying a single bound to the **raw** stream, which is what the superseded rule
did, made admission depend on line endings. **Measured**: an LF stream of 4093
`x`, LF, `A`, LF is 4096 raw bytes and was admitted; its CRLF form is 4098 raw
bytes and was rejected, although folding the second produces the first byte for
byte. A many-line shape is worse — 410 terminators expand a 4096-byte folded
stream to 4506 raw bytes. A Windows-hosted and a Unix-hosted manager could
therefore disagree about whether the same distribution is admissible at all,
which contradicts the whole point of step 4. Control C11 keeps that divergence
runnable and is required to keep failing.

The `V` payload MAY contain interior LFs; that is the whole point of the rule.
The `C` payload MUST additionally contain no LF at all: `cargo --version` is one
line, and a multiline value there is `build_toolchain_version_undetermined`.

Each record is appended with the framing of section 2.2, with `kind` the single
ASCII byte `V` or `C` and an empty path:

```text
kind || uint64be(0) || uint64be(payload_byte_length) || payload
```

**Worked example, measured on this host.** Reproducible by anyone with the same
distribution root; a different Rust release produces different bytes and
different digests, which is the intended behaviour.

| | `V` | `C` |
|---|---|---|
| raw stdout bytes | 192 | 36 |
| payload bytes | 191 | 35 |
| `sha256(payload)` | `7d8e08339e557ede5a9e565773c4cf17f83dea27f7d0c6591869f184bd1b81b5` | `8d712854de14f22840767bc824c5ac08098f35ddaa44437256e31b53cb546165` |
| framed record bytes | 208 | 52 |
| framed record header, hex | `56` `0000000000000000` `00000000000000bf` | `43` `0000000000000000` `0000000000000023` |
| `sha256(framed record)` | `7fc35c11acae420849418f9c9f9b5681651beedc6d68f00bf1e4db022cd5f06b` | `d677e668d65108419fd197d147f31f2dda30a1364233440f3b0138d5185c2f78` |

The `V` payload, verbatim, with `\n` written for the interior LF bytes:

```text
rustc 1.91.0 (f8297e351 2025-10-28)\nbinary: rustc\ncommit-hash: f8297e351a40c1439a467bbbb6879088047f50b3\ncommit-date: 2025-10-28\nhost: aarch64-apple-darwin\nrelease: 1.91.0\nLLVM version: 21.1.2
```

The `C` payload, verbatim:

```text
cargo 1.91.0 (ea2d97820 2025-10-10)
```

Because the whole verbose stream is bound rather than one extracted line, the
identity changes when the commit hash, the commit date, the host line or the
LLVM version changes, even if the release triple does not. That is stricter than
binding `release: 1.91.0` alone, and it is the reason the multiline rule was
taken rather than the single-line alternative.

Conformance obligations for this rule, all host-independent except the first:

| # | Vector | Required outcome |
|---|---|---|
| N1 | real `rustc -vV` stdout from the resolved root | normalizes, and both digests above reproduce |
| N2 | the same content with every LF rewritten as CRLF | the **same** payload and the same digest |
| N3 | the same content with one interior LF removed | normalizes, digest differs |
| N4 | one payload byte changed | normalizes, digest differs |
| N5 | two whole lines transposed | normalizes, digest differs |
| N6 | a bare CR inserted | rejected |
| N7 | no terminal LF | rejected |
| N8 | two terminal LFs | rejected |
| N9 | a NUL inserted | rejected |
| N10 | invalid UTF-8 inserted | rejected |
| N11 | empty stdout | rejected |
| N12 | a folded stream of 4097 bytes | rejected |
| N13 | a `C` payload containing an interior LF | rejected |
| N14 | an LF stream and its CRLF form, folded stream exactly **4096** bytes, two lines | **both** admitted, with identical payload and identical digest |
| N15 | the same pair with a folded stream of exactly **4097** bytes | **both** rejected |
| N16 | an LF stream and its CRLF form over 410 lines, folded stream exactly **4096** bytes (raw CRLF form 4506 bytes) | **both** admitted, with identical payload and identical digest |
| N17 | the same 410-line pair with a folded stream of exactly **4097** bytes | **both** rejected |
| N18 | 4096 CRLF pairs — the maximal expansion of an in-bound folded stream, 8192 raw bytes | rejected **by a semantic rule**, not by the raw capture limit |
| N19 | every raw length from 0 to 32768 | no length above the capture bound can fold within the semantic bound |

N14 through N17 are the exact property the two bounds exist to guarantee: a
stream and its line-ending translation always receive the same verdict, and when
that verdict is admission they produce the same payload and the same digest. The
implementation is required to check payload and digest equality, not just
verdict equality, because a rule that admitted both while normalizing them
differently would break the identity rather than the admission decision.

## 3. Source layout

Identical for both drivers. For `rust-v1` the root is the command's declared
local build root inside the consuming skill snapshot; for
`rust-repository-v1` it is the descriptor target's `build_root` inside the
locked external repository snapshot.

| # | Requirement | Diagnostic on failure |
|---|---|---|
| L1 | `source_dir` equals `build_root` | `build_rust_source_dir_invalid` |
| L2 | `Cargo.toml` exists directly in `build_root` and is the nearest ancestor `Cargo.toml` of `source_dir` | `build_rust_manifest_missing` |
| L3 | `Cargo.lock` exists directly in `build_root` | `build_rust_lockfile_missing` |
| L4 | `vendor` exists directly in `build_root` and is a directory; it MAY be empty | `build_rust_vendor_missing` |
| L5 | no `.cargo` directory exists anywhere in the `build_root` subtree | `build_rust_package_config_forbidden` |
| L6 | no file in the `build_root` subtree has a native extension from the closed list of section 7.3 | `build_rust_native_input_forbidden` |
| L7 | the `build_root` `Cargo.toml` contains no `cargo-features`, `[patch]`, `[replace]` or `[workspace]` table | `build_rust_manifest_key_forbidden` |

**Measured** that an empty `vendor` directory resolves and reports metadata with
exit 0, so L4 is an authoring requirement rather than a dependency requirement.

Snapshot validation, link-free directory rules, build-root disjointness and the
`build_roots` model are unchanged from manifest schema 6 and are not restated.
For the external mode the whole repository snapshot remains the validation,
identity and audit subject; only the selected build root is compiler-visible;
and input MUST NOT come from the consuming skill, another external repository, a
sibling or parent directory outside the selected build root, a host Cargo
registry cache, a host `CARGO_HOME`, or the network.

L1 through L7 are necessary and not sufficient. Section 4 is the gate that makes
the compiler-visible closure decidable before Cargo starts.

## 4. Stage P — the manager-owned source closure, before any cargo process

Stage P runs after snapshot validation and section 3, and **before** the graph
phase. It is performed by the manager's own TOML parser and filesystem
primitives, over snapshot bytes, with no Cargo process involved.

It exists because the graph phase is not a safe place to discover an escaping
input. **Measured**: a build root whose manifest declares
`outside = { path = "../outside", package = "exfiltrated-outside-name" }` makes
`cargo metadata --format-version 1 --locked --offline --quiet --all-features`
exit 0 and report a package whose `manifest_path` is outside the build root;
with the outside manifest replaced by malformed TOML the same command prints
`error: unclosed table, expected `]`` and `--> ../outside/Cargo.toml:1:9`. Cargo
opened, parsed and reported bytes from a file outside the admitted root. A
verdict computed from that output prevents compilation; it does not prevent the
read. Stage P does.

### 4.1 Manifest inventory

Let `R` be the canonical absolute build root and `V` be `<R>/vendor`.

`M` is the set of every file named `Cargo.toml` at any depth under `R`,
including under `V`, discovered by walking the already validated, link-free
snapshot subtree. `R/Cargo.toml` MUST be a member; its absence is L2.

The walk opens nothing outside `R`. Every subsequent step reads only members of
`M` and files whose paths a previous step has already admitted.

### 4.2 Forbidden-key gate

Every member of `M` MUST parse under the manager's TOML parser; a parse failure
is `build_rust_manifest_unparsable`. Then, for every member:

| Rejected when the manifest contains | Diagnostic |
|---|---|
| a top-level `cargo-features` key | `build_rust_manifest_key_forbidden` |
| a `[workspace]` table, or `package.workspace` | `build_rust_workspace_forbidden` |
| a `[patch]` or `[replace]` table | `build_rust_manifest_key_forbidden` |
| any value equal to the inheritance form `{ workspace = true }` | `build_rust_manifest_key_forbidden` |
| `package.build` whose value is anything other than the boolean `false` | `build_rust_build_script_forbidden` |
| `package.links` | `build_rust_native_link_declaration_forbidden` |
| `lib.proc-macro` or `lib.proc_macro` set to `true`, or `lib.plugin` set to `true` | `build_rust_proc_macro_forbidden` |
| a `crate-type` or `crate_type` array with a member outside `{bin, lib, rlib}` | `build_rust_crate_type_forbidden` |
| a dependency entry carrying `git`, `branch`, `tag`, `rev`, `registry` or `registry-index` | `build_rust_dependency_source_forbidden` |

`package.build` is admitted only when it is exactly `false`. **Measured**: the
`cargo vendor` normalization of `cfg-if 1.0.4` writes `build = false`
explicitly, so a rule that rejected the mere presence of the key would reject
ordinary vendored crates. The manifest inventory covers vendored manifests, so
these rows also decide a vendored crate's build script and crate type before
Cargo reads either.

#### The build-script file rule

A forbidden-key gate cannot close build scripts on its own, because the most
dangerous shape declares **no key at all**. For every member of `M` with
directory `D`:

| Rejected when | Diagnostic |
|---|---|
| any filesystem entry named `build.rs` exists directly in `D` | `build_rust_build_script_forbidden` |

The check is one `lstat` per manifest directory, on the name alone. It consults
neither `package.build` nor the entry's type.

**Measured**, on cargo 1.91.0, what makes Cargo treat a file as a build script:

| Shape | Cargo | Section 4.2 |
|---|---|---|
| `package.build` absent, `build.rs` file present | **discovered**: a `custom-build` target is reported, and `cargo build` compiles and **executes** it | rejected |
| `build = false`, `build.rs` file present | ignored | rejected (stated over-rejection) |
| `build = false`, no `build.rs` — the `cargo vendor` shape | ignored | admitted |
| `package.build` absent, a differently named script file | ignored | admitted |
| `package.build` absent, `build.rs` in a subdirectory | ignored | admitted |
| `package.build` absent, a **directory** named `build.rs` | ignored | rejected (stated over-rejection) |
| edition 2024, `package.build` absent, `build.rs` file present | **discovered** | rejected |

The first row is the gap this rule closes. The manifest carries nothing to
reject, so before this rule the shape was decided only by G2 — after Cargo had
already read and resolved the tree, which is exactly what section 4 exists to
prevent. The execution was measured end to end: an auto-discovered build script
wrote its marker file during `cargo build`.

The rule is stated on the name alone rather than on Cargo's discovery semantics,
so it needs no reasoning about which shapes Cargo currently auto-discovers and
stays correct if that changes. It over-rejects in exactly the two directions
marked above, both of which Cargo ignores and neither of which arises from
`cargo vendor` normalization: those manifests carry `build = false` precisely
when no build script file was packaged. Control C12 keeps the key-only gate
runnable against the first row and is required to keep failing.

This gate over-rejects in one known direction: a `[patch]` table in a vendored
manifest is inert to Cargo outside a workspace root, and Stage P rejects it
anyway. That is deliberate — the rule is closed and needs no reasoning about
which manifest Cargo will treat as the workspace root.

### 4.3 The closed relative-path grammar

A **path-bearing key** is any of:

- `path` inside any entry of `dependencies`, `dev-dependencies`,
  `build-dependencies`, or the same three tables under any `target.<cfg>` table;
- `lib.path`, and `path` inside any entry of `bin`, `test`, `bench` or
  `example`;
- `package.readme` and `package.license-file` when their value is a string.

Every path-bearing value `Vp` in every member of `M` MUST satisfy all of:

1. `Vp` is a TOML string, valid UTF-8, non-empty, at most 1024 bytes;
2. `Vp` contains no U+0000, no scalar below U+0020, and no U+007F;
3. `Vp` contains no `\` — a Cargo manifest path uses `/` on every platform, and
   a backslash is rejected rather than interpreted;
4. `Vp` does not begin with `/`;
5. `Vp` has no `<letter>:` drive prefix, no `//` UNC prefix, and no first
   component equal to `~`;
6. splitting `Vp` on `/`, no component is empty, `.` or `..`;
7. no component ends with `.` or U+0020, and no component, case-folded and
   truncated at its first `.`, is one of `CON PRN AUX NUL COM1`…`COM9`
   `LPT1`…`LPT9`.

Rules 4 through 6 make `D/Vp` — the lexical join with the directory of the
containing manifest — provably a descendant of `D`, and `D` is a descendant of
`R` by section 4.1, so the admitted path set is closed under `R` by
construction. Rules 3, 5 and 7 exist so that the same snapshot is admitted or
rejected identically on macOS and on Windows.

A violation is `build_rust_input_outside_build_root`, and it is decided **on the
declared string**, before any filesystem call is made with that string. The
manager MUST NOT stat, open, canonicalize or resolve a value that has not passed
rules 1 through 7.

#### The physical check, as a total algorithm

The physical half must be defined so that **every** lexically admitted string
reaches a verdict, whatever exists on disk. In particular it may not ask the
platform to canonicalize a path that the same rule permits to be absent.
**Measured** on macOS 26.5: `realpath(3)` on an absent leaf returns `NULL` with
`ENOENT`, and Go's `filepath.EvalSymlinks` fails identically. The superseded
rule required the canonical form of the joined path in both cases while
explicitly permitting a non-dependency leaf to be absent, so it had no
implementation. Worse, canonicalizing an absent leaf below a symbolic link was
measured to report a path **outside** the package directory before failing,
which is the opposite of a containment check.

Containment therefore rests on two mechanisms that are both total, and
canonicalization is demoted to a cross-check where it is defined.

Let `D` be the directory of the containing manifest, already a descendant of
`R`, and let `J` be the lexical join `D/Vp`, computed with no filesystem call.

1. **Walk**, component by component, from `R` down to the leaf. For each
   component, `lstat` it **without following links**:
   - it does not exist → the leaf is **absent**; stop. Nothing below a
     non-existent component is opened.
   - it is a symbolic link or a reparse point → reject. This applies at every
     depth **including the leaf itself**, and it happens before anything deeper
     is looked at.
   - it is not a directory and components remain → the leaf cannot exist, so the
     leaf is **absent**; stop.
   Because no component may be a link, no component can redirect the path, and
   `J` is a lexical descendant of `R` by rules 4 through 6. Containment is
   decided here.
2. **Anchor.** Canonicalize the deepest component that actually exists. It is
   always defined — in the worst case it is `R` itself — and it MUST have `R` as
   a path-component prefix. This catches a platform whose canonical form differs
   from the lexical one, such as case folding or Windows short names, without
   ever depending on the leaf.
3. **Leaf policy**, which is the only place the two kinds of key differ:
   - a dependency `path` MUST exist, MUST be a directory, and MUST contain a
     `Cargo.toml` that is already a member of `M`;
   - any other path-bearing key: if the leaf exists it MUST be a regular file or
     a directory; if it is absent that is **not** a Stage P failure, because a
     vendored crate may declare a target whose sources were not vendored and no
     admitted compile command builds it. Nothing is canonicalized for an absent
     leaf.

A physical-check failure is `build_rust_input_outside_build_root`.

Conformance obligations for the physical half:

| # | Vector | Required outcome |
|---|---|---|
| P31 | the canonical form of a permitted absent leaf | the platform cannot produce one — the premise of the algorithm |
| P32 | an absent target leaf below real directories | admitted; the anchor is the deepest existing directory, under `R` |
| P33 | an absent target leaf below a symbolic-link ancestor | rejected **at the link component**, before the leaf is looked at |
| P34 | the same shape as a dependency path | rejected at the link component |
| P35 | a path below an existing regular file | target admitted as absent; dependency rejected as non-existent |
| P36 | a target leaf that is itself a symbolic link, pointing inside `R` | rejected — a link inside `R` is still a redirection the manager did not admit |
| P37 | the build-script file rule over a manifest directory, with and without `build.rs` | admitted without, rejected with |

### 4.4 Dependency origin closure

After section 4.2 has removed `git`, `rev`, `branch`, `tag`, `registry` and
`registry-index`, every dependency entry in every member of `M` has exactly one
admitted origin:

- a `path` value admitted by section 4.3, which resolves inside `R`; or
- a plain registry dependency with no `registry` key, which the manager-written
  source replacement of section 6.1 binds to `V` and to nothing else.

Anything else is `build_rust_dependency_source_forbidden`.

### 4.5 Lock and vendor closure

`R/Cargo.lock` — and only that lock file; the nested `Cargo.lock` a vendored
crate carries is not read — MUST parse, and every `[[package]]` entry MUST have
either no `source` key or a `source` exactly equal to

```text
registry+https://github.com/rust-lang/crates.io-index
```

Any other value, including any `git+`, `sparse+`, `path+` or alternate
`registry+` form, is `build_rust_dependency_source_forbidden`.

Every direct child of `V` MUST be a directory containing both `Cargo.toml` and
`.cargo-checksum.json`, and the number of such children MUST equal the number of
`[[package]]` entries carrying the crates.io source. **Measured** on two
fixtures: 1 registry package and 1 vendor child; 2 and 2. A mismatch is
`build_rust_vendor_incomplete`.

### 4.6 Ancestor staging obligations

Two inputs reach Cargo with **no byte inside `R` naming them**, so no walk of
the snapshot can see them. Both are manager staging obligations, checked from
the parent of `R` upward to the filesystem root before the graph phase, and both
fail `build_execution_control_unavailable` when they cannot be met:

1. no ancestor directory of `R` contains a `.cargo` directory;
2. no ancestor directory of `R` contains a `Cargo.toml`.

Obligation 1 is unchanged. **Measured**: a `.cargo/config.toml` in an ancestor
directory above the build root is discovered and applied.

Obligation 2 is new and is the answer to a measured escape. **Measured**: with
`parent/Cargo.toml` carrying `[workspace] members = ["build_root"]` and
`[patch.crates-io] cfg-if = { path = "evil" }`, where `parent/evil` is an
outside path package declaring `build = "build.rs"`, the graph phase reported
`workspace_root` = `parent`, `workspace_members` of length **1** whose single
element **is** the `R` package, `resolve.root` equal to that same package, and a
`cfg-if` package whose `manifest_path` is `parent/evil/Cargo.toml` with target
kinds `[["lib"], ["custom-build"]]`. G1 as written passes that shape. The
redirect is caught only downstream, after Cargo has read the outside tree.
Removing the ancestor manifest moved `workspace_root` back to `R` in the same
fixture.

### 4.7 The closed profile grammar

A `[profile]` table was measured to start a package-selected process under the
exact pipeline of this contract, so the previous revision's blanket admission of
profiles is withdrawn and replaced by a closed grammar decided from snapshot
bytes.

**The measurement.** On macOS 26.5 arm64 with Rust 1.91.0, this otherwise
ordinary root manifest

```toml
[profile.release]
debug = 2
split-debuginfo = "packed"
```

run through the exact two argument vectors of section 5, the operation-private
environment of section 6, an absolute `RUSTC`, the pinned `rust-lld`, the
`ld64.lld` flavour, the pinned SDK, the manager-written config and a `PATH`
holding thirty logging shims — the twenty-five of section 13.1 plus `objdump`,
`dwp`, `llvm-dwp`, `llvm-strip`, `xcode-select`, `swiftc`, `dtrace` and
`rust-lld` — **resolved `dsymutil` through `PATH`**. The shim
executed, returned 127, and `cargo build` still exited **0** with only
`warning: processing debug info with 'dsymutil' failed`. Zero `PATH`
resolutions were recorded for the same fixture without the profile table.

Two further measurements decide the *shape* of the rule rather than its
existence.

**An unrecognized value is worse than `"packed"`.** With
`split-debuginfo = "wat"`, and with `split-debuginfo = ""`, Cargo forwards
**no** `-Csplit-debuginfo` flag to `rustc` at all — captured from a logging
`RUSTC` wrapper — and `rustc`'s own default for `aarch64-apple-darwin` is
`packed`, so `dsymutil` runs anyway, with no warning, no error and exit 0. A
deny-list naming `"packed"` is therefore bypassed by any garbage string. The
same wrapper shows Cargo emitting `-Csplit-debuginfo=unpacked` when the key is
absent, which is the only reason the previous revision's pipeline was safe.

**An unknown key is accepted silently.** `[profile.release]
totally-unknown-key = 42` exits 0 with no diagnostic, so a key deny-list cannot
stay closed against a future stabilization.

The gate is therefore a **positive allowlist**, in the same spirit as row G5's
exact-match allowlist of two source values. For every member of `M`:

| Admitted table shape |
|---|
| `[profile.<name>]` |
| `[profile.<name>.package.<spec>]` |
| `[profile.<name>.build-override]` |

`<name>` matches `^[A-Za-z0-9_-]{1,64}$`. Any other table under `profile`,
including a bare `[profile]` and any deeper nesting, is rejected.

| Admitted key | Admitted values |
|---|---|
| `opt-level` | `0` `1` `2` `3` `"s"` `"z"` |
| `debug` | `false` `true` `0` `1` `2` `"none"` `"line-directives-only"` `"line-tables-only"` `"limited"` `"full"` |
| `strip` | `false` `true` `"none"` `"debuginfo"` `"symbols"` |
| `debug-assertions`, `overflow-checks`, `incremental`, `rpath` | `false` `true` |
| `lto` | `false` `true` `"off"` `"thin"` `"fat"` |
| `panic` | `"unwind"` `"abort"` |
| `codegen-units` | an integer in `[1, 65536]` |
| `inherits` | a string matching the `<name>` grammar |

Every other key is rejected, and `split-debuginfo` is rejected **outright, at
every value**, because the driver publishes one executable and discards every
by-product, so no packaging of debug information has an admitted purpose. A
violation is `build_rust_manifest_key_forbidden`; nothing new is minted.

**The over-rejection is measured, not assumed.** Across the 506 published crate
manifests in the host's registry cache, 37 carry a `[profile*]` table and they
use exactly seven keys — `debug`, `lto`, `opt-level`, `codegen-units`, `panic`,
`incremental`, `inherits` — with values `2`/`true`, `"fat"`/`"thin"`/`true`,
`1`/`2`/`3`, `1`, `"abort"`, `false` and `"release"`. **Zero** use
`split-debuginfo`. Every one of those manifests passes this gate.

The gate runs over every member of `M`, not only `R/Cargo.toml`, for the same
reason the `[patch]` row does: the rule stays closed and needs no reasoning
about which manifest Cargo will treat as the workspace root. That direction is
an over-rejection and is stated rather than hidden. **Measured**: a `[profile]`
table in a path dependency inside `R` is silently inert, and a checksum-valid
`[profile.release] split-debuginfo = "packed"` inside a **vendored** crates.io
manifest is also inert — 0 `PATH` resolutions, exit 0 — so only the root
manifest's profiles are honoured. **Measured** in the same fixture: editing a
vendored `Cargo.toml` without repairing `.cargo-checksum.json` makes
`cargo metadata` exit **0** and only `cargo build` exit 101, so the vendor
checksum is not a pre-compile gate and cannot be the mechanism here.

**The second mechanism is a manager-owned pin, and it is load-bearing.**
Section 6 adds `-Csplit-debuginfo=<pin>` to `CARGO_ENCODED_RUSTFLAGS`, where
`<pin>` is a manager constant resolved per operating system and is `off` on
macOS. **Measured**: with the pin present, `"packed"`, an unrecognized value,
the empty string and a `[profile.release.package.<root>]` override all produce
**0** `PATH` resolutions, build with exit 0 and yield a running executable;
without it, each of them resolves `dsymutil`. The pin is not hygiene: the
`rustc` default that an unrecognized value falls back to is a *toolchain*
property, reachable with no package byte selecting it, so the closure claim of
section 2 would otherwise rest on Cargo continuing to emit a flag this contract
does not control. Repeated builds in one location with one pin were measured
byte-identical; changing the pin changes the artifact bytes, so the pin belongs
to the driver policy object and to cache identity.

Conformance obligations, all host-independent:

| # | Vector | Required outcome |
|---|---|---|
| F1–F7 | no profile table; the inventory's `opt-level`/`lto` vector; every key and value measured in the wild; a custom profile with `inherits`; a `package."*"` override; a `build-override`; `strip`/`rpath`/`debug-assertions`/`overflow-checks` | admitted |
| F8–F13 | `split-debuginfo` as `"packed"`, `"off"`, an unrecognized value, the empty string, inside a package override, inside a build-override | rejected at every value and in every table shape |
| F14–F17 | an unknown key; `rustflags`; `codegen-backend`; `trim-paths` | rejected |
| F18–F20 | `opt-level = 9`; `lto = "aggressive"`; `codegen-units = 0` | rejected — an admitted key with a value outside its set |
| F21–F24 | a table nested past the three shapes; a subtable that is neither `package` nor `build-override`; a bare `[profile]`; `inherits` carrying a non-name value | rejected |
| F25 | an admitted value written as a TOML **literal** string, `opt-level = 's'` | admitted — a literal and a basic string with the same content are the same value |
| F26–F27 | the rejected key spelled as a **quoted** TOML key; a profile header written as an **array of tables**, `[[profile.release]]` | rejected |

`rustflags`, `codegen-backend` and `trim-paths` are additionally **measured** to
require an unstable `cargo-features` opt-in on cargo 1.91.0, which section 4.2
already rejects, so they are fail-closed twice.

Two spelling rules keep the gate from being defeated by TOML syntax rather than
by semantics: a key is compared after its TOML quoting is removed, and a value
written as a literal string is compared as its basic-string equivalent. A basic
string carrying an escape sequence is **not** unescaped and therefore fails the
allowlist, which is the fail-closed direction.

### 4.8 What Stage P proves, and what it does not

It proves that every filesystem path Cargo can reach from snapshot bytes lies
inside `R`, decided before Cargo starts, on declared strings rather than on
resolved output. Together with section 4.6 it closes the two origins that are
not declared in snapshot bytes at all, with the build-script file rule of
section 4.2 it closes the one package-code entry point that snapshot bytes
declare through a **file name** rather than through a manifest key, and with
section 4.7 it closes the one admitted table that was measured to select a
process.

#### The admitted path set `A`

The superseded text required every graph `manifest_path` and `src_path` to be
"in the Stage P admitted set" while defining only `M` and the declared
path-bearing values. An ordinary package uses `src/main.rs` with **no**
`[[bin]].path` key, so that text left an implementation two bad choices: reject
an ordinary positive build at G11, or reimplement Cargo's target auto-discovery
inside Stage P. Neither is acceptable, and the set is therefore defined by the
walk Stage P already performs:

> `A` is every path the link-free walk of section 4.1 enumerated under `R` —
> every file and every directory, at any depth, including under `V` — together
> with every leaf that section 4.3 admitted and permitted to be absent.

The walk never follows a symbolic link or reparse point and never descends below
one, so nothing reachable only through a link is a member. `A` is finite, is
computed before any cargo process, and requires no knowledge of Cargo's
discovery rules at all.

**Why that is sufficient**, measured rather than argued. Every path
`cargo metadata` reports is one of exactly two things:

1. an **existing** file under `R`. Auto-discovery finds targets by looking at
   the filesystem, so a discovered source exists and the walk enumerated it.
   **Measured** over `src/main.rs`, `src/lib.rs`, `src/bin/<n>.rs`,
   `src/bin/<n>/main.rs`, `examples/<n>.rs`, `examples/<n>/main.rs`,
   `tests/<n>.rs`, `benches/<n>.rs`, `build.rs`, an explicit
   `[[bin]] name = <package name>` with no `path`, and every vendored package's
   `manifest_path` and target sources: all present, all under `R`;
2. a path a **path-bearing key declared**, which section 4.3 has already
   decided. **Measured**: `[[bin]] path = "src/ghost.rs"` with no such file is
   reported with that `src_path` and `exists = false`, and `[lib] path` behaves
   the same way, which is exactly the absent-leaf case 4.3 admits.

There is no third case. **Measured**: a name-only `[[bin]]` or `[lib]` with no
discoverable file makes the graph phase exit **101** —
``can't find `<name>` bin at `src/bin/<name>.rs` or `src/bin/<name>/main.rs` ``
— rather than report a phantom `src_path`, and a package with no target at all
exits 101 with `no targets specified in the manifest`.

Three cases the reviewer asked to be stated explicitly:

- **Unreachable manifests inventoried under `R`.** `M` covers every `Cargo.toml`
  under `R`, including a vendored crate no dependency references. They and their
  files are in `A`; membership is a superset property, so an unreferenced
  manifest costs nothing and never causes a rejection.
- **Missing default source leaves.** A declared absent leaf is in `A`, so G11
  passes and the compile phase fails with Cargo's own error if that target is
  ever built. An **undeclared** absent path is not in `A` — and cannot be
  reported, by the measurement above.
- **The root's single-bin rule.** `A` says nothing about how many targets exist.
  An auto-discovered `src/bin/<n>.rs` adds a second `bin` target and is rejected
  by G9, which is unchanged. Target *shape* is G9's job; target *containment* is
  `A`'s.

#### The graph phase after Stage P

Stage P does not replace the graph phase. Sections 7.2 and 7.4 still run, and
their role is a **consistency cross-check** rather than the primary gate: every
`manifest_path` and every target `src_path` the graph reports MUST be a member
of `A`, compared as cleaned absolute paths, and `workspace_root` MUST equal `R`.
A disagreement means Cargo reached a file the manager did not admit; it is
`build_rust_graph_inconsistent`, it is a defect in the manager rather than a
property of the package, and it MUST NOT be reported as a package rejection.

It is not a containment guarantee. It bounds what Cargo *resolves*; it does not
bound what `rustc` reads through `include_str!`, which stays the stated residual
exposure of section 12.

## 5. The two argument vectors

The working directory is the canonical `source_dir` for both. Neither the parent
nor the worker MAY alter, extend, reorder or repeat them.

```text
cargo metadata --format-version 1 --locked --offline --color never --quiet --all-features
cargo build --locked --offline --color never --quiet --release --target <native-tuple> --bin <bin-target-name>
```

`<native-tuple>` is the Stage A resolved host tuple. `<bin-target-name>` is the
single `bin` target name from the graph phase, validated against
`^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}$` **before** it is placed in an argument
vector; a name outside that grammar is `build_rust_bin_target_invalid` and no
compile phase starts.

`--locked` is load-bearing. **Measured**: without it, `cargo metadata` writes
`Cargo.lock` into the source tree — a write to the frozen snapshot. With it and
no lock file present, `cargo metadata` exits **101** with
`error: the lock file <path> needs to be updated but --locked was passed to
prevent this` and writes nothing.

`--all-features` is load-bearing and its exact meaning is fixed in section 7.1.

The produced file is:

```text
<CARGO_TARGET_DIR>/<native-tuple>/release/<bin-target-name>          (Unix)
<CARGO_TARGET_DIR>\<native-tuple>\release\<bin-target-name>.exe      (Windows)
```

`CARGO_TARGET_DIR` is an operation-private manager staging root. The manager
hashes the file there, sets manager-defined executable permissions, publishes it
as `bin/<command>` or `bin/<command>.exe` derived solely from the consuming
manifest command key, and MUST NOT execute it for validation, version discovery,
smoke testing, post-processing, receipt generation, rollback or any other
reason. Every other file in the target directory is a compiler by-product,
stays in staging, is discarded with it, and never enters cache identity, the
receipt, the marker, the shim relationship or publication.

## 6. Operation-private environment

The environment starts empty except for indispensable operating-system process
variables, and is identical for the probe vectors, the graph phase and the
compile phase.

| Variable | Value |
|---|---|
| `PATH` | a manager-owned empty directory |
| `HOME`, `TMPDIR`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` | operation-private roots |
| `APPDATA`, `LOCALAPPDATA`, `USERPROFILE`, `TEMP`, `TMP` | operation-private roots, Windows only |
| `LC_ALL`, `LANG` | `C` |
| `CARGO_HOME` | operation-private root holding only the manager-written config of section 6.1 |
| `CARGO_TARGET_DIR` | operation-private staging root |
| `RUSTC` | absolute `<root>/bin/rustc` |
| `RUSTDOC` | absolute `<root>/bin/rustdoc` |
| `RUSTC_WRAPPER`, `RUSTC_WORKSPACE_WRAPPER` | set and empty |
| `CARGO_ENCODED_RUSTFLAGS` | exactly `-Clinker=<root>/lib/rustlib/<native-tuple>/bin/rust-lld` `0x1F` `-Clinker-flavor=<flavor>` `0x1F` `-Csplit-debuginfo=<pin>` |
| `CARGO_ENCODED_RUSTDOCFLAGS` | set and empty |
| `CARGO_INCREMENTAL` | `0` |
| `CARGO_NET_OFFLINE` | `true` |
| `CARGO_NET_RETRY` | `0` |
| `CARGO_NET_GIT_FETCH_WITH_CLI` | `false` |
| `CARGO_TERM_COLOR` | `never` |
| `SDKROOT` | the resolved `platform-sdk` root, macOS only |

`<flavor>` is `ld64.lld` on macOS. `<pin>` is `off` on macOS. Both are manager
constants resolved per operating system; the Windows and Linux values are
qualification obligations, section 13, and an implementation MUST NOT ship a
platform whose `<pin>` has not passed the acceptance test of section 13.1 with a
firing control.

`-Csplit-debuginfo=<pin>` is the second mechanism of section 4.7 and is not
hygiene. **Measured**: an unrecognized `split-debuginfo` profile value makes
Cargo forward no such flag, `rustc`'s own macOS default is `packed`, and
`packed` runs a `PATH`-resolved `dsymutil`. That default is a *toolchain*
property that no package byte has to select, so without the pin the closure
claim of section 2 would depend on Cargo continuing to emit a flag this contract
does not control. With the pin, `"packed"`, an unrecognized value, the empty
string and a package override each produced **0** `PATH` resolutions and a
running artifact. Because `CARGO_ENCODED_RUSTFLAGS` participates in Cargo's
fingerprint, adding the pin changes the produced bytes; the value therefore
belongs to the driver policy object and to cache identity, and repeated builds
under one pin in one location were measured byte-identical.

Every other Rust, Cargo, `rustup`, compiler, linker, SDK and executable-search
variable MUST be absent, and none may be inherited. In particular
`RUSTC_BOOTSTRAP` MUST be absent, because it makes a release toolchain accept
`-Z` flags; and `RUSTFLAGS`, `RUSTDOCFLAGS`, `CARGO_BUILD_*` other than the
target directory, `CARGO_TARGET_*_LINKER`, `CARGO_TARGET_*_RUSTFLAGS`,
`CARGO_REGISTRIES_*`, `CARGO_REGISTRY_*`, `CARGO_HTTP_*`, `CARGO_UNSTABLE_*`,
`RUSTUP_*`, `RUSTC_LOG`, `DEVELOPER_DIR`, `MACOSX_DEPLOYMENT_TARGET`,
`LD_LIBRARY_PATH`, `DYLD_*`, `LIBRARY_PATH`, `CPATH`, `CC`, `CXX` and `AR` MUST
be absent.

The private `CARGO_HOME` and `HOME` are not hygiene. **Measured**: a build root
with no `vendor` directory and no manager-written config resolves with exit 0
when the operator's `HOME` and `CARGO_HOME` are visible, because the operator's
registry cache satisfies the dependency; the same tree under an
operation-private `HOME` and `CARGO_HOME` fails with exit 101 and
`error: no matching package named 'itoa' found` / `location searched: crates.io
index`. Operator Cargo state is a real source of package bytes, and isolating it
is what makes `vendor` the only admitted source.

Three further settings answer measured behaviour rather than hygiene:

- **`RUSTC` absolute.** Cargo otherwise resolves `rustc` by name from `PATH`;
  under a minimal `PATH` `TASK-260729-rhjxtx` measured
  `could not execute process 'rustc -vV' (never executed)`, and under a
  populated one the second node of the process graph would be chosen by `PATH`
  order.
- **`SDKROOT` set.** **Measured**: without it, `rustc` runs
  `xcrun --sdk macosx --show-sdk-path` resolved from `PATH`; with it, no `xcrun`
  lookup occurs.
- **`RUSTC_WRAPPER` and `RUSTC_WORKSPACE_WRAPPER` set and empty.** **Measured**:
  a package `.cargo/config.toml` carrying `[build] rustc-wrapper` executed the
  named script three times during `cargo build`; setting `RUSTC_WRAPPER` to the
  empty string in the manager environment neutralised it, and a config
  `[env] RUSTC_WRAPPER = { value = "...", force = true }` did not override the
  neutralisation.

Environment neutralisation is a second layer, never the answer. `[source]`,
`[registries]`, `[patch]` and `[http]` config tables have no environment
counterpart and a package config file outranks the manager's own `$CARGO_HOME`
config, so L5 rejects the file outright and section 4.6 rejects the ancestor
case.

### 6.1 The manager-written `$CARGO_HOME/config.toml`

Written by the manager before the graph phase, with exactly these four tables
and nothing else:

```toml
[source.crates-io]
replace-with = "curator-vendor"

[source.curator-vendor]
directory = '<canonical absolute path of <build_root>/vendor>'

[net]
offline = true

[term]
quiet = true
color = "never"
```

**The file is a fixed byte template with exactly one variable region.** It is
UTF-8 with no byte-order mark, LF line terminators only, and exactly one
terminal LF. The constant part is 150 bytes: 89 bytes before the directory value
and 61 bytes after it. Written as an escaped literal, the whole file is

```text
[source.crates-io]\nreplace-with = "curator-vendor"\n\n[source.curator-vendor]\ndirectory = '<D>'\n\n[net]\noffline = true\n\n[term]\nquiet = true\ncolor = "never"\n
```

where `<D>` is the serialized directory value.

#### The directory value is package-influenced, and this is how that is contained

The claim that no package-derived byte reaches this file is **withdrawn**. The
value is the canonical absolute path of `<build_root>/vendor`, and `build_root`
is a relative path selected by the consuming manifest's `build_roots` entry or by
the external descriptor target. Those bytes are manager-validated, but they are
package-derived, and the contract must say so.

Containment is a closed representability rule plus a serialization that cannot
escape, not a claim of purity.

**Serialization.** Compute the canonical absolute path of `<build_root>/vendor`
after snapshot validation and section 4 — fully resolved, with no `.` or `..`
component and no symbolic link. Encode it as UTF-8 and require all of:

1. valid UTF-8, non-empty, at most 4096 bytes;
2. absolute for the host operating system;
3. no U+0000, no scalar below U+0020, no U+007F;
4. no U+0027 `'`;
5. on Windows, not a verbatim or UNC prefix form — no leading `\\?\`, `\\.\` or
   `\\<server>\<share>`.

A path that fails any rule is `build_execution_control_unavailable`: the manager
chose a staging location it cannot represent, and that is a manager fault
reported before any cargo process, never a package diagnostic.

A path that passes is emitted **verbatim between two `'` characters**. Because a
TOML literal string has no escape sequences and can contain every scalar except
`'`, a newline and the control characters rule 3 already rejects, the writer is
a concatenation and there is no escaping routine to get wrong. A backslash
separator on Windows, a space, and a non-ASCII component all pass through
unchanged, so the value keeps the host's native path spelling.

**Measured** with only this value varying, `cargo metadata` exit code:

| serialization | exit |
|---|---|
| literal string, ASCII absolute path | 0 |
| literal string, path containing `ö` | 0 |
| basic string, ASCII absolute path | 0 |
| basic string, path containing `ö` written literally | 0 |
| basic string containing an unescaped `\` | 101, `could not load Cargo configuration` |
| relative value `vendor` | 101, `failed to load source for dependency` |

The unescaped-backslash row is why a basic string is not used: a Windows path
written into one without an escaping pass is a parse failure, and an escaping
pass is a routine that can be wrong. The relative row is why the value is
absolute: a relative `directory` resolves against the config file's parent, which
is `$CARGO_HOME` and not the build root.

**Write-back verification.** After writing, the manager MUST re-read the file it
wrote, parse it with its own TOML parser, and require the result to be exactly
four tables with exactly the members above and a `directory` value byte-equal to
the serialized path. A mismatch is `build_execution_control_unavailable`. This
turns a serialization defect into a pre-compile failure rather than into a
silently different build: **measured**, a naive writer that concatenates a path
containing `"` into a basic string produced a file that really did carry extra
`[net]` and `[junk]` tables, with `offline = false` among them.

The manager MUST NOT write any other key into this file, and `$CARGO_HOME` MUST
contain nothing else.

## 7. Pre-compile rejection matrix

Computed from the validated snapshot, Stage P, and the graph phase, before the
compile phase. Total by construction: every row has one verdict, and the list of
rows is closed. Rows are evaluated in the order given; the first failure is the
reported diagnostic.

### 7.1 Graph-phase properties and the exact feature semantic

**Measured**: `cargo metadata --format-version 1 --offline` over a build root
whose path dependency declares `build = "build.rs"` with a `build.rs` that
writes a marker file, and whose second path dependency declares
`[lib] proc-macro = true` with a macro that writes a second marker file,
produced **neither** marker and exited 0. The same run reported
`kind: ["custom-build"]` for the build-script target, `kind: ["proc-macro"]` and
`crate_types: ["proc-macro"]` for the macro crate, `links: "probelib"` for the
package declaring a native library, and a `source` value per package.

The graph command passes `--all-features` and does **not** pass
`--filter-platform`. The exact resulting semantic, stated without overclaim:

> `packages[]` is the resolution over **every platform**, over **every
> dependency kind**, and over **every feature of the root package** together
> with everything those features transitively activate.

It is **not** the union over every feature of every package. **Measured**, with
root -> `mid` and `mid` carrying `leafpm` optional behind `mid`'s own feature
`x`: when no root feature names `mid/x`, `leafpm` is absent from `Cargo.lock`
and from the `--all-features` graph; when the root adds `y = ["mid/x"]`,
`leafpm` appears in both, and is still absent from the graph without
`--all-features`.

**The subset property.** Every package unit the compile vector of section 5 can
build is present in the graph the matrix checks, for four independent reasons,
each measured:

1. **Features.** The compile vector activates the root package's default feature
   set, which is a subset of its full feature set, and Cargo feature activation
   is additive: activating a superset of root features yields a superset of
   resolved packages. **Measured** on a fixture with an optional proc-macro
   dependency behind the non-default feature `extra` and a second optional
   dependency behind its implicit feature: `packages[]` is
   `['feat', 'winonly']` without the flag and
   `['feat', 'implicit', 'pm', 'winonly']` with it, and under the flag `pm`
   carries `kind ["proc-macro"]` and `crate_types ["proc-macro"]`, so G3 fires.
2. **Platform.** Without `--filter-platform`, a dependency gated behind
   `target.'cfg(target_os = "windows")'` is present on a macOS host.
   **Measured**: `winonly` is in `packages[]` in both runs above.
3. **Dependency kind.** `cargo metadata` reports normal, development and build
   dependencies; `cargo build --bin` builds no development dependency, and a
   build dependency implies a build script, which G2 has already rejected.
4. **Lock compatibility.** `--all-features` does not make `--locked` fail on a
   normally vendored tree, because `Cargo.lock` already records the optional
   dependencies reachable from root features and `cargo vendor` vendors the
   whole lock. **Measured**: a root with `itoa` optional behind `extra` locks
   `cfg-if`, `itoa`, `optreg`; plain `cargo vendor` vendors `cfg-if` and `itoa`;
   the `--all-features` graph reports all three and the default-feature build
   exits 0. `cargo vendor` has no `--all-features` flag — **measured**,
   `error: unexpected argument '--all-features' found`.

The matrix is therefore host-independent and deliberately over-approximating: a
dependency that would only be built on another platform, or only under a feature
this build does not enable, still rejects the command. Two further costs are
stated rather than hidden: `--all-features` can make resolution fail on a
package whose features are mutually exclusive, and it can pull a build-script
dependency into the graph that the default build would never touch. Both are
fail-closed, and both reject the command rather than admit a surface.

### 7.2 Rows decided by the graph phase

Let `R` be the build root and `V` be `<R>/vendor`.

| # | Rejected when | Diagnostic |
|---|---|---|
| G0 | `workspace_root` differs from `R` | `build_rust_workspace_forbidden` |
| G1 | `workspace_members` has other than exactly one element, or that element is not the `R` package, or `resolve.root` is null or differs | `build_rust_workspace_forbidden` |
| G2 | any package has a target whose `kind` contains `custom-build` | `build_rust_build_script_forbidden` |
| G3 | any package has a target whose `kind` or `crate_types` contains `proc-macro` | `build_rust_proc_macro_forbidden` |
| G4 | any package has a non-null `links` | `build_rust_native_link_declaration_forbidden` |
| G5 | any package `source` is neither null nor exactly `registry+https://github.com/rust-lang/crates.io-index` | `build_rust_dependency_source_forbidden` |
| G6 | a package with null `source` has a `manifest_path` outside `R`, or any target `src_path` outside `R` | `build_rust_input_outside_build_root` |
| G7 | a package with the crates.io `source` has a `manifest_path` outside `V` | `build_rust_input_outside_build_root` |
| G8 | any target has a `crate_types` member outside `{bin, lib, rlib}` | `build_rust_crate_type_forbidden` |
| G9 | the `R` package has other than exactly one target whose `kind` is exactly `["bin"]` | `build_rust_bin_target_ambiguous` |
| G10 | that target's `name` is outside `^[A-Za-z0-9_][A-Za-z0-9_-]{0,63}$` | `build_rust_bin_target_invalid` |
| G11 | any reported `manifest_path` or target `src_path` is not in the Stage P admitted set | `build_rust_graph_inconsistent` |

G0 and G11 are the graph half of section 4.8, and G11's input set `A` is defined
there rather than left implicit. G0
exists because **measured**, an ancestor workspace manifest moves
`workspace_root` above `R` while leaving `workspace_members` at length one and
`resolve.root` at the `R` package, so G1 alone does not see it. G11 is a manager
self-check, never a package rejection.

G2, G3, G4, G5 and G8 are the `build_package_code_execution_forbidden` semantic
class; the rest are driver-specific structural rejections. G5 covers git
dependencies, alternate registries, `local-registry` and `sparse` sources and any
future source kind, because it is an exact-match allowlist of two values rather
than a deny-list. **Measured**: a git dependency under `--offline` fails inside
the graph phase with `error: failed to get 'anyhow' as a dependency of package
'gd v0.1.0 (...)'` / `Caused by: failed to load source for dependency 'anyhow'`,
before any compile phase, so G5 has a fail-closed backstop in cargo itself.

After Stage P, every row G2 through G8 has a snapshot-byte counterpart that
fires earlier, and each counterpart is named here rather than asserted
collectively:

| Row | Fail-before-Cargo counterpart |
|---|---|
| G2 | the `package.build` key row of section 4.2, **and** the build-script file rule for the auto-discovered case that declares no key |
| G3 | the `lib.proc-macro` / `lib.proc_macro` / `lib.plugin` row of section 4.2 |
| G4 | the `package.links` row of section 4.2 |
| G5 | the dependency-source row of section 4.2 and the lock-source rule of section 4.5 |
| G6 | the relative-path grammar and physical check of section 4.3, plus the ancestor obligations of section 4.6 |
| G7 | the vendor closure of section 4.5 |
| G8 | the `crate-type` row of section 4.2 |

The one package-selected process that has **no** graph row at all is the profile
one: `cargo metadata` reports no profile information, so the auxiliary process a
`[profile]` table selects is invisible to every row G0 through G11. That is why
section 4.7 decides it from snapshot bytes and section 6 pins it in the
environment, and why the matrix carries no `G` row for it. A contract that
relied on the graph phase here would have no verdict to give.

The G2 entry is why the file rule exists. A `build.rs` with no `package.build`
member is declared by **no manifest key**, so the forbidden-key gate has nothing
to reject and — before the file rule — G2 was the only row that saw it, after
Cargo had already read and resolved the tree. The counterpart claim was false
for exactly that shape.

The graph rows are retained because they also cover what Cargo derives rather
than declares, and because a disagreement between the two is exactly what G11
must be able to see.

### 7.3 Rows decided by snapshot bytes

L5 and L7 of section 3, the whole of section 4 — including the profile grammar
of section 4.7, which is the only pre-compile verdict for a surface the graph
phase cannot see — plus the closed native-input extension list of L6, case
folded for comparison:

```text
.o .obj .a .lib .so .dylib .dll .tbd .rlib .rmeta .bc .ll .pdb .exp .res
.s .S .asm .c .cc .cpp .cxx .h .hh .hpp .m .mm .def .rc
```

and any path component ending in `.framework` or `.dSYM`. A match is
`build_rust_native_input_forbidden`. This is defence in depth over an already
closed path — without build scripts there is no admitted way to compile or link
such a file — and it is the direct analogue of `go-v1`'s `SysoFiles`, `CFiles`
and `SFiles` rejection.

### 7.4 Rows decided by the fixed environment and argument vectors

| Surface | Closed by |
|---|---|
| network, registry index, git fetch, crate download | `--offline`, `--locked`, `CARGO_NET_OFFLINE`, the manager-written config, the private `CARGO_HOME`, and an empty `PATH` |
| operator registry cache and operator Cargo configuration | operation-private `CARGO_HOME` and `HOME`, measured load-bearing in section 6 |
| package-selected linker, linker flavour, link argument, library search path | `CARGO_ENCODED_RUSTFLAGS` fixed by the manager, no package config file, no ancestor config file, no build script |
| package-selected `rustc`, `rustdoc`, wrapper | absolute `RUSTC` and `RUSTDOC`, empty `RUSTC_WRAPPER` and `RUSTC_WORKSPACE_WRAPPER` |
| package-selected debug-info packaging, and the toolchain default it falls back to | `-Csplit-debuginfo=<pin>` in `CARGO_ENCODED_RUSTFLAGS`, section 6, over the section 4.7 rejection |
| `-Z` flags, unstable manifest keys, nightly features | release-channel toolchain, `RUSTC_BOOTSTRAP` absent, `cargo-features` rejected by L7 and section 4.2 |
| cross-compilation | `--target` fixed to the resolved native tuple |
| incremental state | `CARGO_INCREMENTAL=0` |
| package-selected toolchain path, root, channel, mirror, installer, version manager | decision 0007 resolution; `rust-toolchain*` classified rather than honoured, section 8 |

### 7.5 Admitted surfaces

Cargo **features** are admitted: they select which package source compiles,
which is the same class of choice as a Go build constraint, and the build always
uses the root package's default feature resolution because the command object
cannot express one. The rejection matrix is nevertheless computed over the
root's full feature set, per section 7.1.

`[profile]` tables are admitted **only through the closed grammar of section
4.7**. The previous revision admitted them wholesale on the argument that a
release toolchain cannot unlock per-profile `rustflags`; that argument is sound
and irrelevant, because the process a profile can start does not arrive through
a flag the package injects. It arrives through `split-debuginfo`, which was
**measured** to make the exact compile vector run a `PATH`-resolved `dsymutil`
while `cargo build` still exits 0. Section 4.7 rejects the key from snapshot
bytes at every value and in every table shape, section 6 pins
`-Csplit-debuginfo` so the class is inert whatever Cargo forwards, and the
process-graph row below records the result. Within that grammar a profile
selects codegen tuning only: link-time optimisation, `strip`, `rpath` and
`panic = "abort"` were each measured to record zero `PATH` resolutions, and
`strip` was measured to be *effective* — the artifact shrank from 407 088 to
336 656 bytes — so the zero is an absence of process rather than an absence of
behaviour. Link-time optimisation stays inside `rustc` and its bundled LLVM.

| Profile surface | Verdict | Decided by |
|---|---|---|
| `opt-level`, `debug`, `debug-assertions`, `overflow-checks`, `lto`, `panic`, `incremental`, `codegen-units`, `rpath`, `strip`, `inherits`, each within its value set | admit | section 4.7 allowlist; measured 0 `PATH` resolutions |
| `split-debuginfo`, any value, any table shape | reject | section 4.7, before any cargo process; and the section 6 pin |
| any other profile key, including a future stabilization | reject | section 4.7 allowlist — cargo accepts unknown keys silently |
| `rustflags`, `codegen-backend`, `trim-paths` | reject | section 4.7, and `cargo-features` already rejected by section 4.2 |
| a profile table nested past the three admitted shapes | reject | section 4.7 |
| a profile table in a path or vendored dependency | reject | section 4.7 over every member of `M`; measured inert, stated over-rejection |

Two further surfaces are admitted with bounds and are stated as residual
exposures rather than closed; see section 12.

## 8. Stage B — metadata dispositions

Decision 0007's disposition framework, precedence rule, file-shape gate and
channel classification are fixed there and are not reopened. Files are evaluated
in Unicode-scalar lexical order of relative source path, so `Cargo.toml`
precedes `rust-toolchain` precedes `rust-toolchain.toml`; within each file
`forbidden` classes precede `compared` classes.

| Source | Field | Disposition |
|---|---|---|
| `Cargo.toml` | `package.rust-version` | `classified`, section 8.2 |
| `Cargo.toml` | `workspace.package.rust-version` | unreachable: a workspace is rejected by section 4.2 and G0/G1 |
| `rust-toolchain.toml` | `toolchain.path` | `forbidden` |
| `rust-toolchain.toml` | `toolchain.channel` | `compared`, section 8.3 |
| `rust-toolchain.toml` | `toolchain.components`, `toolchain.targets`, `toolchain.profile` | `ignored` |
| `rust-toolchain` | the bare channel string | `compared`, section 8.3 |

**Measured**: a build root carrying a `rust-toolchain.toml` with *both*
`path = "/nonexistent"` and `channel = "nightly"` built successfully through a
directly resolved `cargo`, with zero `PATH` resolutions. The same file redirects
the `rustup` shim — `TASK-260729-rhjxtx` measured `error: invalid toolchain: the
path '/nonexistent/trusted/root' has no bin/ directory` for `path`, and
`info: syncing channel updates for 'nightly-aarch64-apple-darwin'` followed by a
download attempt for `channel = "nightly"`. The file is a live selector through
the shim and completely inert against direct resolution, which is exactly what
admits `channel` as `compared` and keeps `path` `forbidden`.

### 8.1 File-shape gate

For each `metadata_sources` file present in the validated tree, the gate covers
file **syntax** only: a file the ecosystem's own grammar rejects, including a
key the ecosystem permits at most once appearing more than once, is
`build_toolchain_metadata_mismatch` with `assertion` = `unclassifiable` and a
`source_ref` naming the file or the field path. It asserts nothing about the
semantics of fields the entry does not read.

For `Cargo.toml` the gate is "the TOML document does not parse". A `rust-version`
whose TOML *type* is wrong is deliberately **not** a gate case: the document
parses and the field extracts as a TOML value, so it is classifier class 1 of
section 8.2, for the same reason decision 0007 refused to route a shape-valid
but unrepresentable Go value to its gate.

### 8.2 Classifier — `Cargo.toml` `package.rust-version`

Rust has **three host-independent acceptance layers** plus one host gate, where
Go has two plus one. All four are measured, one value per fixture, with
`cargo metadata --no-deps --format-version 1 --offline`:

| Value | Exit | Layer | First diagnostic line |
|---|---|---|---|
| `"1.85"` | 0 | — | accepted, `rust_version` `1.85` |
| `"1.85.0"` | 0 | — | accepted, `rust_version` `1.85.0` |
| `1.85` | 101 | document | `error: invalid type: floating point '1.85', expected a semver or workspace` |
| `"1.85.0-beta"` | 101 | grammar | `error: unexpected prerelease field, expected a version like "1.32"` |
| `"not-a-version"` | 101 | grammar | `error: unexpected prerelease field, expected a version like "1.32"` |
| `"1.85.0+build"` | 101 | grammar | `error: unexpected build field, expected a version like "1.32"` |
| `"1.85.0.1"` | 101 | grammar | `error: expected a version like "1.32"` |
| `"stable"` | 101 | grammar | `error: expected a version like "1.32"` |
| `""` | 101 | grammar | `error: expected a version like "1.32"` |
| `"1"` @ edition 2015 | 0 | — | accepted, `rust_version` `1` |
| `"1"` @ edition 2018 | 101 | edition floor | `rust-version 1 is older than first version (1.31.0) required by the specified edition (2018)` |
| `"1.31"` @ edition 2018 | 0 | — | accepted |
| `"1.31"` @ edition 2021 | 101 | edition floor | `rust-version 1.31 is older than first version (1.56.0) required by the specified edition (2021)` |
| `"1.56"` @ edition 2024 | 101 | edition floor | `rust-version 1.56 is older than first version (1.85.0) required by the specified edition (2024)` |
| `"1.85"` @ edition 2024 | 0 | — | accepted |

Measured edition floors: 2015 admits `"1"`; 2018 requires 1.31.0; 2021 requires
1.56.0; 2024 requires 1.85.0. The floor depends on the manifest's own `edition`
field and on no host input.

The three layers are pairwise independent, and the independence is measured
rather than argued: the document layer accepts `"not-a-version"` which the
grammar layer rejects; the grammar layer accepts `"1"` which the edition floor
rejects at edition 2018 and above; and the edition floor would accept `1.85`
which the document layer rejects as a float. No layer contains another.

**The host gate is excluded from the layer measurement.** **Measured**:
`cargo metadata --no-deps` reports `rust_version` `1.99` on a 1.91.0 host with
exit 0, so it structurally cannot be applying the host gate; and `cargo build
--offline` with the same manifest exits 101 with
`error: rustc 1.91.0 is not supported by the following package:` and
`probe-future@0.1.0 requires rustc 1.99`, with compilation not started.

Canonicalization: a value of `MAJOR` canonicalizes to `(MAJOR, 0, 0)`,
`MAJOR.MINOR` to `(MAJOR, MINOR, 0)`, `MAJOR.MINOR.PATCH` to itself.

The ordered exhaustive classifier. There is no `forbidden` class, because the
field's value space is a version and nothing else. The catch-all is mandatory
and last.

| # | Class | Disposition | Outcome |
|---|---|---|---|
| 1 | the TOML value is not a string, or is the table form `{ workspace = true }` | — | `build_toolchain_metadata_mismatch`, `assertion` `unclassifiable` |
| 2 | a string the grammar cannot represent: a prerelease field, a build field, more than three dot-separated components, an empty string, or any non-numeric component | — | `build_toolchain_metadata_mismatch`, `assertion` `unclassifiable` |
| 3 | a grammar-representable string strictly below the floor of the manifest's `edition` | — | `build_toolchain_metadata_mismatch`, `assertion` `unclassifiable` |
| 4 | a grammar-representable string at or above the edition floor whose canonical triple is **above** the resolved toolchain triple | `compared` | `build_toolchain_metadata_mismatch`, `assertion` the derived canonical `at_least` |
| 5 | a grammar-representable string at or above the edition floor whose canonical triple is at or below the resolved toolchain triple | `compared` | permitted, and never honoured |
| 6 | the field is absent | — | contributes no assertion |
| 7 | anything else | — | `build_toolchain_metadata_mismatch`, `assertion` `unclassifiable` |

Classes 1 through 3 are host-independent, so their vectors need no Rust
toolchain on the runner. Classes 4 and 5 take the resolved version as fixture
input, exactly as decision 0007 fixes for every Stage B classification case.

Class 1 includes the workspace-inheritance table because a workspace is rejected
by section 4.2 and G0/G1 and the value would otherwise have no resolvable
meaning. It is deliberately not routed there: a Stage B classification is a
statement about a value, and the workspace rows are statements about the tree
and the graph.

### 8.3 Classifier — `rust-toolchain.toml` `toolchain.channel` and the legacy `rust-toolchain` file

Decision 0007's channel table applies unchanged and is not restated: a
canonicalizable version literal becomes an `at_least` assertion; `stable` is
permitted and never honoured; `beta`, `nightly` and dated channels are a
mismatch because they assert a prerelease host that is never resolved; anything
else is `build_toolchain_metadata_mismatch`, never a default and never a
selector.

The legacy one-line `rust-toolchain` file carries a bare channel string and uses
the identical classifier. Its file-shape gate is "the file is not exactly one
line of printable non-empty content after trimming a single trailing newline".

`toolchain.path` is `forbidden` and is evaluated before every `compared` class,
so a file carrying both `path` and `nightly` is deterministically
`build_toolchain_package_influence_forbidden` with the `toolchain-root`
`origin_class`.

### 8.4 Recognised command outcomes are a closed set

The corroborating command classifier is closed. A recognised outcome is one
whole diagnostic line, matched **exactly** against a form predicted before the
command ran from the value under test and the probe's own fixed constants. An
outcome outside the set is **unknown**, yields no verdict and fails the probe. A
lead with an unconstrained tail, and a substring found anywhere in the output,
are families rather than outcomes and MUST NOT be recognised.

Every grammar and document rejection renders a caret block whose third line is
exactly `<N> | rust-version = <literal>`, where `<N>` is the fixture's fixed
line number and `<literal>` is the value under test as written. The recognised
form is therefore the **pair** of one predicted first line and one predicted
source line, because three distinct grammar rejections share the first line
`error: expected a version like "1.32"` and none of the first lines names the
value.

| Class | First line, exact | Second element, exact |
|---|---|---|
| document | `error: invalid type: <toml-type-phrase>, expected a semver or workspace` | `<N> \| rust-version = <literal>` |
| grammar/prerelease | `error: unexpected prerelease field, expected a version like "1.32"` | `<N> \| rust-version = <literal>` |
| grammar/build | `error: unexpected build field, expected a version like "1.32"` | `<N> \| rust-version = <literal>` |
| grammar/other | `error: expected a version like "1.32"` | `<N> \| rust-version = <literal>` |
| edition floor | `error: failed to parse manifest at \`<manifest-path>\`` | `  rust-version <literal-body> is older than first version (<floor>) required by the specified edition (<edition>)` |
| host gate | `error: rustc <host-version> is not supported by the following package:` | `  <package>@<version> requires rustc <literal-body>` |
| accepted | exit 0 | `packages[0].rust_version` equals `<literal-body>` |

`"1.32"`, the edition floors `1.31.0`, `1.56.0` and `1.85.0`, and the manifest
line number are probe fixed constants. If a later cargo release changes any of
them the probe turns red rather than quietly changing what it measures, which is
the correct direction for a check whose purpose is to notice upstream moving.

The command forms are the narrowest that exercise the layer under test:
`cargo metadata --no-deps --format-version 1 --offline` for the three layers,
because it was measured not to apply the host gate; and `cargo build --offline`
as the corroborating measurement, whose outcome is classified into `accepted`,
`rejected-document`, `rejected-grammar`, `rejected-edition`, `host-gate` and
`unknown`, never into pass and fail.

### 8.5 Closure is measured, not asserted

The probe carries a closure section that feeds the classifier outcomes
deliberately outside the recognised set and requires each to yield no verdict,
reporting for every fabrication which of the two laundering directions it
belongs to:

- **direction A, acceptance laundering**: real unrelated command failures — a
  missing manifest, an unreadable working directory, an unknown subcommand, a
  `--locked` lock-file failure — must not be scored as upstream acceptance;
- **direction B, rejection laundering**: every measured outcome cross-fed under
  a different value, and every measured diagnostic extended the way a later
  release would extend it, must not be scored as a rejection verdict for the
  value actually under test.

The extended-diagnostic checks are constructed and are disclosed as such: an
outcome upstream has not yet written cannot be measured on any host. Taking text
upstream did emit and changing it the way a later release would is the honest
form of that check.

### 8.6 Controls required to fail

Each is runnable from the probe binary and each MUST fail; a control that stops
failing is a regression.

| # | Control | What it guards |
|---|---|---|
| C1 | an open classifier with a fall-through verdict | closure in both directions |
| C2 | lead-only recognition, dropping the caret source line | three grammar classes collapsing into one |
| C3 | exit status as the semantic measurement (`cargo build` exit 0 means representable) | folding the host gate and the edition floor into the grammar layer |
| C4 | `cargo build` as the isolated representability command | the same folding, arrived at by choosing a wider command |
| C5 | the edition floor folded into the grammar classifier | one host-independent layer swallowing another |
| C6 | substring matching anywhere in combined output | recognising a family rather than an outcome |
| C7 | the graph vector without `--all-features` | a feature-gated proc macro invisible to the matrix |
| C8 | Stage P omitted, deciding escape from graph output alone | Cargo reading and reporting an outside-root manifest |
| C9 | the config directory value concatenated into a basic string without the representability rule | a package-influenced path changing the parsed configuration |
| C10 | operator `HOME` and `CARGO_HOME` inherited | the operator registry cache satisfying a dependency `vendor` does not hold |
| C11 | the byte limit applied to the raw stream, before CRLF folding | line-ending-equivalent version streams receiving different verdicts |
| C12 | a build-script gate that inspects manifest keys only | an auto-discovered `build.rs` that no manifest key declares |
| C13 | `[profile]` tables admitted wholesale | an admitted profile table starting a fourth, `PATH`-resolved process |
| C14 | a deny-list naming `split-debuginfo = "packed"` | an unrecognized value falling back to `rustc`'s process-capable default |
| C15 | G11 against the superseded input set of manifests and declared values only | an ordinary auto-discovered `src/main.rs` reported as a manager fault |

C3 and C4 are not redundant: C3 changes how the outcome is read, C4 changes
which command produces it, and either alone leaves the other's defect
reachable. C7 through C10 are the controls for the four changes two revisions
back, C11 and C12 for the previous revision's two, and C13 through C15 for this
revision's; each must fail, and each failing is what makes the corresponding
positive result meaningful.

C13 and C14 are not redundant either. C13 shows that the *documented*
process-capable value reaches `dsymutil` under the exact pipeline; C14 shows
that the obvious fix for C13 — reject the literal `"packed"` — is bypassed by
any unrecognized string, because Cargo then forwards nothing and `rustc`'s own
default applies. Removing either leaves a real defect reachable.

C11 through C15 each carry a second assertion beyond "the superseded rule is
broken": the replacement is applied to the same inputs, and the control reports
itself as **not** failing if the replacement admits what the superseded rule
should have rejected. C14 additionally re-runs its fixture with the
`-Csplit-debuginfo` pin and reports itself as not failing if the pin leaves any
`PATH` resolution. A control that only demonstrated the old defect could stay
green after a regression in the new rule.

## 9. Identity, cache, receipt, marker, claim

The canonical build input binds, in addition to the members decision 0008
section 8 requires of every new driver:

- the complete `curator-rust-toolchain-v1` identity of section 2, including both
  per-root digests and `closure_sha256`, as the single element of
  `toolchain_identities`;
- the resolved native tuple;
- the validated `bin` target name; and
- this closed policy object, whose `execution_policy` is the `const`
  `manager-worker-v2`:

```json
{
  "dependency_mode": "vendor-directory",
  "network": "none",
  "workspace": false,
  "build_scripts": false,
  "proc_macros": false,
  "plugins": false,
  "features": "manifest-default",
  "feature_audit": "root-all-features",
  "source_closure": "manager-prewalk-v1",
  "profile_policy": "closed-grammar-v1",
  "debuginfo_packaging": "pinned-off",
  "target_mode": "native",
  "profile": "release",
  "linker": "toolchain-rust-lld",
  "link_mode": "internal",
  "native_inputs": false,
  "package_config": "rejected",
  "compiler_directives": "reject-nonstandard-native-inputs-v1",
  "incremental": false,
  "execution_policy": "manager-worker-v2"
}
```

`features` stays `manifest-default` because that is what the compile phase
activates. `feature_audit` is `root-all-features` and records the section 7.1
semantic: the matrix is computed over the root package's full feature set.
`source_closure` is `manager-prewalk-v1` and records that section 4 ran before
any cargo process. `profile_policy` is `closed-grammar-v1` and records that the
profile allowlist of section 4.7 was applied rather than the superseded blanket
admission. `debuginfo_packaging` is `pinned-off` on macOS and names the
`-Csplit-debuginfo` value of section 6; it is the one member whose value is
platform-resolved, and it enters cache identity because the pin was measured to
change the produced bytes. All four members are `const` in the receipt schema;
none is a selector, and no package byte can reach any of them.

`network: "none"` denotes the fixed offline Cargo configuration, `--offline`,
`--locked`, the manager-written `$CARGO_HOME` config, the operation-private
`CARGO_HOME` and `HOME`, and the empty `PATH`. It is not a claim of
kernel-enforced network denial; that guarantee is `total-network-denial`,
deferred to `STORY-260728-327soo`.

The logical cache key is the SHA-256 of `CCJ-1` over the complete input, exactly
as for the Go drivers. Receipt schema 3 carries the local mode and schema 4 the
external mode, each a strict `oneOf` discriminated by the `driver` `const`.
Marker schema 4 records `driver`, `receipt_schema_version` and
`execution_policy` per build entry; a reader rejects a `rust-v1` entry claiming
`manager-worker-v1` rather than inferring the policy from the driver name.
Conformance claim schema 4 asserts each identifier with `execution_policy`
selected by the assertion's own `driver` `const`.

The effective toolchain requirement and the `compatibility` set are gates, not
build inputs.

`rust-repository-v1`'s input additionally carries the members decision 0008
section 5 and `protocol/core.md` section 9.2 already fix for an external
command — repository identifier, declared and effective source state,
substitution, external `curator-build-source-v1`, descriptor path and selected
target — plus `"source_kind":"locked-external-git-v1"`.

**Measured local/external equivalence.** The same build-root bytes placed in a
local snapshot and at a nested `build_root` of a Git repository, cloned and
checked out at a fixed revision, produced an identical digest over the build
root, an identical graph JSON after substituting the build root and the
operation-private staging root, and a byte-identical executable. The equality of
the artifact is recorded as an observation; the driver does not require
bit-reproducible artifacts, and section 11 is unchanged.

## 10. Diagnostics

Driver-specific codes, all beneath the `build_package_code_execution_forbidden`
semantic class where marked, all fired before the compile phase:

| Code | Stage | Trigger | Class |
|---|---|---|---|
| `build_rust_source_dir_invalid` | validation | L1 | structural |
| `build_rust_manifest_missing` | validation | L2 | structural |
| `build_rust_lockfile_missing` | validation | L3 | structural |
| `build_rust_vendor_missing` | validation | L4 | structural |
| `build_rust_package_config_forbidden` | validation | L5 | code execution |
| `build_rust_native_input_forbidden` | validation | L6 | code execution |
| `build_rust_manifest_key_forbidden` | validation, Stage P | L7, 4.2, 4.7 | code execution |
| `build_rust_manifest_unparsable` | Stage P | 4.2 | structural |
| `build_rust_vendor_incomplete` | Stage P | 4.5 | structural |
| `build_rust_workspace_forbidden` | Stage P, graph | 4.2, G0, G1 | structural |
| `build_rust_build_script_forbidden` | Stage P, graph | 4.2, G2 | code execution |
| `build_rust_proc_macro_forbidden` | Stage P, graph | 4.2, G3 | code execution |
| `build_rust_native_link_declaration_forbidden` | Stage P, graph | 4.2, G4 | code execution |
| `build_rust_dependency_source_forbidden` | Stage P, graph | 4.2, 4.4, 4.5, G5 | code execution |
| `build_rust_input_outside_build_root` | Stage P, graph | 4.3, G6, G7 | structural |
| `build_rust_crate_type_forbidden` | Stage P, graph | 4.2, G8 | code execution |
| `build_rust_bin_target_ambiguous` | graph | G9 | structural |
| `build_rust_bin_target_invalid` | graph | G10 | structural |
| `build_rust_graph_inconsistent` | graph | G11 | manager fault |

The profile grammar of section 4.7 mints no code: a rejected table, key or value
is `build_rust_manifest_key_forbidden` with a `source_ref` naming the manifest
and the dotted field path.

`build_rust_manifest_unparsable`, `build_rust_vendor_incomplete` and
`build_rust_graph_inconsistent` were new in the previous revision. The first two are
package rejections; the third is a manager fault and MUST NOT be presented as a
package property.

`build_execution_control_unavailable` carries the two ancestor staging
obligations of section 4.6 and the unrepresentable-path and write-back-mismatch
cases of section 6.1.

The twelve `build_toolchain_*` codes of decision 0007 apply unchanged.
`build_toolchain_platform_unsupported` carries `check` = `host_pair` for a pair
outside `platforms` and `check` = `reported_target` for a reported tuple that
does not map or whose standard library is absent by section 1.3.
`build_toolchain_version_undetermined` additionally carries every failure of the
normalization of section 2.3.
`build_descriptor_driver_unsupported` and `build_descriptor_schema_unsupported`
apply to the external mode unchanged. `build_artifact_class_unsupported` applies
to a platform that cannot produce a single self-contained executable.

No diagnostic reproduces an unvalidated package byte.

## 11. Artifact

Exactly one bounded regular file, class `native-executable-v1`.

**Measured** on this host: the pipeline produces a `Mach-O 64-bit executable
arm64` whose only dynamic dependency reported by `otool -L` is
`/usr/lib/libSystem.B.dylib`, a base-installation library, and whose code
signature is `adhoc, linker-signed`. That signature is applied by `rust-lld` as
part of linking: it is produced by the driver's fixed argument vector, selects no
signing identity, credential, entitlement or notarization, and reaches no
network. It is compiler output, not a manager signing step. The driver performs
no manager post-build signing, timestamping or notarization, and a platform
policy requiring a locally signed binary must wait for the separately versioned
and reviewed signer profile.

The driver does not require bit-reproducible artifacts.

## 12. Residual exposures

Two surfaces are admitted with bounds rather than rejected. Both are stated so
that no reader, receipt, marker or claim can imply otherwise.

**Compile-time file inclusion.** `include!`, `include_str!` and `include_bytes!`
resolve a path relative to the including file and can name a path outside the
build root. They are reads, not code execution, so decision 0008 section 7 does
not require their rejection; the portable policy does not contain the compiler's
filesystem access, and none of the six deferred hardened guarantees covers
compile-time reads. Stage P does not close this: it constrains what **Cargo**
resolves, and an `include_str!` argument is a token inside a source file that
`rustc` opens directly. No sound deterministic pre-compile rejection exists: the
macro name is a token rather than a byte pattern, so `include ! ( "x" )` and
`cfg_attr` forms defeat a byte scan, while a scan for the substring `include`
rejects ordinary comments and identifiers. Recorded as a new input to
`STORY-260728-327soo`.

**Foreign function declarations against base-installation libraries.** Package
source may declare `extern` blocks and `#[link]` attributes. The package cannot
supply a library to link — native files are rejected by L6, `links` by section
4.2 and G4, build scripts by section 4.2 and G2, and no admitted path adds a
library search path — so `#[link]` can only name a library the pinned link
environment already resolves, which is a base-installation library. Decision
0008 section 3 already requires the artifact to depend on exactly those. This is
not a claim that the produced program is safe; it remains untrusted package
output the manager never executes.

## 13. Platform matrix and qualification

| Platform | Status |
|---|---|
| macOS arm64 | complete pipeline measured on one host; enters a claim only through `TASK-260728-2bu2q6` |
| macOS amd64 | qualification obligation |
| Windows | implementation contract only; no platform claim |
| Linux | excluded until `TASK-260728-1skseh` |

### 13.1 The acceptance test

Identical on every candidate platform, and it is what `platforms` membership
means:

1. `PATH` is set to a directory containing logging shims for at least `cc`,
   `c++`, `clang`, `clang++`, `ld`, `ld64`, `xcrun`, `ar`, `ranlib`, `dsymutil`,
   `strip`, `sh`, `bash`, `env`, `lld`, `ld.lld`, `ld64.lld`, `gcc`,
   `install_name_tool`, `codesign` and, on Windows, `link`, `cl`, `lib`,
   `vswhere`, `cmd`; each records its name and argv and exits 127.
2. The graph phase and the compile phase both run to completion with **zero**
   recorded entries, over a build root carrying at least one real vendored
   crates.io dependency, with the manager-written config of section 6.1 and an
   operation-private `CARGO_HOME` and `HOME`.
3. A control run with the linker pin and the SDK pin removed records at least
   one entry. Without the control, the zero proves nothing.
4. The **profile replay**: the same build root, with
   `[profile.release] debug = 2` and `split-debuginfo = "packed"` added, and
   again with an unrecognized value such as `"wat"`, records **zero** entries
   with the `-Csplit-debuginfo=<pin>` of section 6 in place, and **at least one**
   with the pin removed. The unpinned run is the control for this step, and it
   is required to fire; without it the platform's `<pin>` value is unverified.
   Section 4.7 rejects both fixtures from snapshot bytes, so on a conforming
   implementation this step is reached only with the gate disabled — it measures
   the second mechanism, not the first.
5. The produced executable runs and its dynamic dependencies are all
   base-installation libraries of the declared platform baseline.
6. `<root>/lib/rustlib/<tuple>/lib` contains `libstd-*.rlib` inside the
   fingerprinted tree.
7. The directory value of section 6.1 serializes under the platform's native
   path spelling and survives the write-back verification.

**Measured on macOS arm64**: steps 1, 2 and 5 pass with twenty shims and zero
entries for both phases, with `cfg-if 1.0.4` vendored and the exact two argument
vectors; step 3 recorded `xcrun --sdk macosx --show-sdk-path` and
`cc <full link line>` and the build failed with
`error: linking with 'cc' failed: exit status: 127`; **step 4** passes with
thirty shims in the standalone replay and with the twenty-five of step 1 in the
probe — pinned `"packed"` 0 entries, unpinned `"packed"` 1 entry
`dsymutil`, pinned unrecognized value 0 entries, unpinned unrecognized value 1
entry `dsymutil`, pinned package override 0 entries, unpinned package override 1
entry `dsymutil`, every pinned run exiting 0 with a running artifact; step 6
passes; step 7 passes for a POSIX absolute path, including one containing a
non-ASCII component.

### 13.2 Windows implementation contract

Two candidate paths, neither claimed:

1. `x86_64-pc-windows-msvc` with
   `-C linker=<root>/lib/rustlib/<tuple>/bin/rust-lld` and
   `-C linker-flavor=lld-link`, with the MSVC and Windows SDK import libraries
   bound as one or more data-only `platform-sdk` link-support roots. `lld-link`
   is present alongside the macOS flavours in `lib/rustlib/<tuple>/bin/gcc-ld/`
   on the measured root, which makes this the path to test first.
2. `x86_64-pc-windows-gnu` with the target's bundled self-contained linking
   artifacts, which if sufficient would need no link-support root at all.

The Windows `<pin>` value of section 6 is part of this contract and is
unmeasured. On `x86_64-pc-windows-msvc` the packaging that produces a `PDB` is
performed by the linker, which is the pinned `rust-lld`, so the macOS value
`off` is **not** assumed to transfer and may not even be a supported value
there; which value passes step 4 with a firing control is a qualification
question, not a claim. The same holds for Linux, where `packed` invokes an
external `dwp`.

The Windows serialization obligations of section 6.1 are part of this contract
and are unmeasured: that a drive-letter absolute path with `\` separators is
accepted inside a TOML literal string by the Windows Cargo build, and that the
verbatim and UNC rejection rules do not exclude a staging location the manager
must be able to use. Both are qualification questions, not claims.

Until section 13.1 passes with a firing control, `platforms` excludes Windows
and both drivers fail `build_toolchain_platform_unsupported` there. An
implementation MUST NOT ship a Windows path that resolves `link.exe`, `cl.exe`,
`gcc`, `ld`, `vswhere` or a Visual Studio activation script from `PATH`, the
registry or an environment variable, and MUST NOT answer the gap with a
host-resolved tool or a downgraded control.

### 13.3 Linux qualification rules

Linux enters `platforms` only when section 13.1 passes on the qualifying host
and, in addition: the produced ELF executable's dynamic dependencies are all
base-installation libraries of the declared distribution baseline, and the
`platform-sdk` role is either absent or resolved from a declaration channel.
`x86_64-unknown-linux-gnu` is expected to need a `platform-sdk` root holding the
C runtime startup objects and `libc` stubs; `x86_64-unknown-linux-musl` may need
none. Which of those holds is the qualification question, not a claim. Step 4
applies unchanged and is expected to be the sharper test there, because the
Linux counterpart of `dsymutil` is an external `dwp`.

## 14. Conformance vector inventory

Positive:

1. local vendored build root, one package, one `bin`, no dependencies, builds
   and publishes `bin/<command>`;
2. the same with one vendored crates.io dependency;
3. the same with an empty `vendor` directory;
4. external repository target with `build_root` `.`;
5. external repository target with a nested `build_root`;
6. `rust-version` at the resolved toolchain triple, permitted;
7. `rust-version` below the resolved toolchain triple, permitted;
8. `rust-toolchain.toml` `channel = "stable"`, permitted and never honoured;
9. `rust-toolchain.toml` `channel` a version literal at or below the resolved
   triple, permitted and never honoured;
10. a `[profile.release]` table setting `opt-level` and `lto`, admitted;
11. a package with an enabled non-default feature reached through the default
    feature set, admitted;
12. cache hit on an unchanged input, with both preflight stages still run;
13. cache miss on a changed `closure_sha256` with an unchanged source identity;
14. a vendored dependency declaring `build = false`, admitted by section 4.2;
15. a vendored dependency declaring `[lib] path` and `[[test]] path` inside its
    own directory, admitted by section 4.3;
16. a build root whose `vendor` child count equals the lock's crates.io package
    count, admitted by section 4.5;
17. local and external source modes over byte-identical build roots, producing
    equal graph output after staging substitution;
18. a package with no `package.build` member and no `build.rs` file — the
    ordinary default shape — admitted by the build-script file rule of
    section 4.2;
19. an ordinary default-layout package whose `bin` target is the
    auto-discovered `src/main.rs`, required to receive a **defined** G11 verdict
    of admitted against the Stage P admitted set of section 4.8;
20. a package declaring a target path that does not exist, reported by the graph
    with that `src_path`, required to be a member of `A` as an admitted absent
    leaf.

Negative, rejection matrix:

21. build script in the root package; 22. build script in a path dependency;
23. build script in a vendored dependency; 24. proc-macro crate type in a path
dependency; 25. proc-macro crate type in a vendored dependency; 26. proc-macro
reachable only through a non-default feature, rejected by the root-all-features
graph; 27. non-null `links`; 28. git dependency; 29. alternate-registry
dependency; 30. two workspace members; 31. virtual manifest; 32. zero `bin`
targets; 33. two `bin` targets; 34. `cdylib` crate type; 35. `staticlib` crate
type; 36. path dependency outside the build root, rejected by Stage P before any
cargo process; 37. vendored package outside `vendor`; 38. `.cargo/config.toml`
at the build root; 39. `.cargo/config.toml` in a subdirectory;
40. `cargo-features` key; 41. `[patch]` table; 42. `[replace]` table;
43. `[workspace]` table; 44. a `.a` file in the tree; 45. a `.c` file in the
tree; 46. a `.dylib` file in the tree; 47. missing `Cargo.lock`; 48. missing
`vendor`; 49. `source_dir` below rather than equal to `build_root`;
50. `Cargo.toml` absent from the build root; 51. an intervening `Cargo.toml`
between build root and `source_dir`; 52. a `bin` target name outside the closed
grammar; 53. a `build.rs` file with **no** `package.build` member — the
auto-discovered shape — required to be rejected from snapshot bytes before any
cargo process; 54. a `build.rs` file beside `build = false`, required to be
rejected as the stated over-rejection.

Profile grammar — all host-independent:

55 through 81. the twenty-seven vectors F1 through F27 of section 4.7: seven
positive shapes covering every key and value measured across the host's 506
cached crate manifests, six `split-debuginfo` rejections spanning `"packed"`,
`"off"`, an unrecognized value, the empty string, a package override and a
build-override, four unknown-or-unstable key rejections, three
value-outside-its-set rejections, four table-shape rejections, and three
spelling vectors — a literal-string value admitted, a quoted forbidden key
rejected, and an array-of-tables profile header rejected.

Admitted path set and G11 — all host-independent:

82 through 97. the sixteen vectors A1 through A16 of section 4.8: the root
manifest, the six auto-discovered target shapes including `src/main.rs` and
`src/lib.rs`, an unreachable vendored manifest and its source, a declared absent
leaf, an undeclared absent path, an outside path, a file below a symbolic link
and the link component itself, the superseded input set failing on
`src/main.rs`, and G11 itself over a reported list carrying one escaping
manifest.

Negative, Stage P closure — all host-independent:

98. dependency `path` beginning with `/`; 99. dependency `path` with a `..`
component; 100. dependency `path` with a Windows drive prefix; 101. dependency
`path` with a `\` separator; 102. dependency `path` with a `//` UNC prefix;
103. dependency `path` whose component is a Windows reserved device name;
104. dependency `path` whose component ends in `.` or a space; 105. dependency
`path` containing a control character; 106. a target `path` escaping the package
directory; 107. `package.workspace` naming an outside manifest; 108. a dependency
entry carrying `git`; 109. a dependency entry carrying `registry`; 110. a
`Cargo.lock` package whose `source` is a `git+` form; 111. a `Cargo.lock` package
whose `source` is an alternate registry; 112. a vendor child missing
`.cargo-checksum.json`; 113. a vendor child count that disagrees with the lock;
114. a manifest in the tree that does not parse; 115. a dependency `path` that
traverses a symbolic link; 116. an ancestor `.cargo` directory; 117. an ancestor
`Cargo.toml`; 118. a graph `manifest_path` outside the Stage P admitted set,
required to be reported as a manager fault; 119 through 125. the seven physical
vectors P31 through P37 of section 4.3 — the absent leaf that has no canonical
form, the absent leaf with safe ancestors, the absent leaf below a symbolic-link
ancestor, the same shape as a dependency, the path below an existing regular
file, the symbolic-link leaf pointing inside `R`, and the build-script file gate.

Negative, configuration serialization — all host-independent:

126. a vendor path containing `'`; 127. a vendor path containing a control
character; 128. a vendor path containing U+007F; 129. a relative vendor path;
130. a Windows verbatim `\\?\` prefix; 131. a UNC `\\server\share` prefix;
132. a written file whose re-parse yields more than four tables; 133. a written
file whose re-parse yields a different `directory` value; 134. a vendor path
containing a non-ASCII component, required to be **accepted** and emitted
verbatim.

Negative, toolchain identity and normalization — host-independent except N1:

135 through 153. the nineteen vectors N1 through N19 of section 2.3, of which
N14 through N17 are the four LF/CRLF pairs at the 4096- and 4097-byte folded
boundary and N18 and N19 are the two raw-capture-bound properties.

Negative, Stage B classifier — all host-independent except where noted:

154. `rust-version` as a TOML float; 155. as a TOML integer; 156. as the
workspace inheritance table; 157. with a prerelease field; 158. with a build
field; 159. with four components; 160. `"stable"`; 161. the empty string;
162. `"1"` at edition 2018; 163. `"1.31"` at edition 2021; 164. `"1.56"` at
edition 2024; 165. `"1"` at edition 2015, permitted; 166. `rust-version` above
the resolved triple, resolved version as fixture input; 167. `Cargo.toml` that
does not parse as TOML, file-shape gate; 168. `rust-toolchain.toml` `path`;
169. `rust-toolchain.toml` `channel = "nightly"`; 170. a dated channel;
171. an unknown channel token; 172. `rust-toolchain.toml` carrying both `path`
and `nightly`, disposition precedence; 173. legacy `rust-toolchain` with a bare
channel; 174. legacy `rust-toolchain` with more than one line, file-shape gate;
175. both `rust-toolchain` and `rust-toolchain.toml` present, lexical ordering.

Negative, toolchain and platform:

176. host pair outside `platforms`, before resolution; 177. reported tuple that
does not map; 178. reported tuple whose `libstd-*.rlib` is absent;
179. prerelease `rustc` release line; 180. `rustc` and `cargo` triples disagree;
181. `rustc -vV` with no `release:` line; 182. resolved version outside
`compatibility`; 183. resolved version outside the effective requirement at
Stage A; 184. descriptor requirement narrowing past the resolved version at
Stage B; 185. `rust-v1` against a schema-1 descriptor; 186. an unsupported
descriptor schema version; 187. command and descriptor drivers disagree;
188. a missing `platform-sdk` declaration on macOS.

Negative, boundary and identity:

189. every frozen schema rejects `rust-v1`; 190. every frozen schema rejects
`rust-repository-v1`; 191. a marker-v4 entry pairing `rust-v1` with
`manager-worker-v1`; 192. a claim asserting `rust-v1` with `manager-worker-v1`;
193. a build input whose policy object carries an extra member; 194. a
`curator-rust-toolchain-v1` identity carrying a root path; 195. a one-root and a
two-root closure with identical tree digests, required not to collide.

The inventory is 195 vectors: 150 in the previous revision, plus the
twenty-seven profile-grammar vectors F1 through F27 of section 4.7, the sixteen
admitted-path-set vectors A1 through A16 of section 4.8, and two positive
vectors — the ordinary auto-discovered `src/main.rs` receiving a defined G11
verdict, and a declared absent target leaf reported by the graph.
