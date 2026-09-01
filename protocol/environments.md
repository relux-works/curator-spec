# Environments protocol

This document is normative for the agent-environments capability, revision 1.
It extends, and does not reinterpret, the portable objects in
[`core.md`](core.md) and the manager behavior in
[`../profiles/manager.md`](../profiles/manager.md). It adds new identities and
widens no object defined there. Section references of the form "core §N" name
`core.md`; "manager §N" names the manager profile.

A manager MAY omit this capability entirely and remains a conforming skill
manager. A manager that implements it MUST implement the complete closed
revision-1 surface defined here: partial adapter sets, partial form support,
or partial marker semantics are not a conforming subset. Launcher internals,
MCP write management, settings fragments, hooks, and the `path` source-kind
import mechanics are outside this document; each returns under its own
review.

## 1. Environment profiles and sources

An **environment profile** is a named, versioned set of global agent context
installed from a declared source. A profile carries an ordered root context
(section 3), an OPTIONAL profile-scoped `Skillfile.json` resolved through the
unchanged core closure, audit, and runtime machinery, and no other surface in
revision 1. Surfaces not defined by this revision (MCP servers, settings,
prompts, subagents, hooks, memory) MUST NOT be declared, materialized, or
inferred from profile data.

Profile names are portable identifiers under core §2. Comparison is
case-sensitive.

The closed set of revision-1 source kinds is:

- **`git`** — a network git source under the core §6.1 canonical identity and
  the core §6.2 git safety rules. The declaration carries exactly one of
  `tag`, `branch`, or `revision`. `tag` uses the core §6.3 tag grammar and
  selects only `refs/tags/<value>`; `revision` is a full lowercase commit
  object id; `branch` resolves per core §6.2. A directly installed profile
  MAY track a branch — the same allowance `Skillfile.json` gives direct
  project declarations in core §5 — and the resolved commit is recorded as
  the **effective pin**. Strict-tag policy carries over unchanged: a moved
  tag is a warning, or an error under strict-tag policy (core §10).
- **`local`** — reserved for exactly one builtin migration profile per
  machine (section 9.4). A `local` profile has no git identity, no ref, and
  no effective commit; its store key and effective pin are the core §8
  content hash of its current state, called its **state hash** below.

The source kind `path` — an operator-local profile directory installed by
path and keyed by the core §8 content hash of its snapshot — is reserved. It
is delivered with the onboarding-import capability (tracked as
STORY-260901-2hkq49), not in revision 1. A revision-1 manager MUST reject a
`path` source declaration with `profile_source_kind_unsupported` and MUST NOT
emulate it through the `local` kind.

Profiles are data end to end. No file in a profile snapshot is executed,
sourced, or interpreted as configuration for the manager itself. No adapter,
materializer, form, mode, or channel is ever selected by profile bytes;
every such selection comes from the closed adapter registry (section 7) and
machine configuration.

### 1.1 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| source kind not `git` or `local`, or `path` declared | `profile_source_kind_unsupported` |
| invalid canonical identity, ref form, or ref grammar | `profile_source_invalid` |
| profile name violates the core §2 grammar | `profile_name_invalid` |
| operation names a profile that is not installed | `profile_unknown` |

## 2. Profile repository shape

A profile repository is a git snapshot whose root contains
`Profilefile.json`, a strict schema-1 object:

```json
{
  "version": 1,
  "profiles": {
    "companyA": "profiles/companyA",
    "personal": "profiles/personal"
  }
}
```

Validation is strict under core §1: readers MUST reject duplicate keys,
unknown fields, invalid UTF-8, and a `version` other than `1`. `profiles` is
a non-empty object. Each member name is a profile name under section 1. Each
value is a portable relative path (core §2) that names an existing directory
in the snapshot. Two members MUST NOT name the same directory, and no
declared profile root may be equal to or contained below another declared
profile root. Discovery by directory layout does not exist: a directory not
named by `Profilefile.json` is not a profile.

A profile directory contains:

```text
<profile-root>/
  context/
    context.json        # module manifest, schema 1 (REQUIRED when context/ exists)
    00-base.md
    10-style.md
    20-claude.md
  Skillfile.json        # OPTIONAL profile-scoped skill declarations
  PROFILE.md            # OPTIONAL, informative only
```

`context/` is OPTIONAL. When it exists it MUST contain `context.json`; a
profile without `context/` declares no root-context surface and
materialization writes no root-context file for it (this is distinct from a
manifest with zero applicable modules, section 5.4). `Skillfile.json` uses
the unchanged core §5 schema and semantics. `PROFILE.md` is informative: it
is never materialized, never selected by any rule in this document, and its
bytes participate only in snapshot identity and audit. Files in a profile
directory not named by this section or by `context.json` are inert: they
participate in snapshot identity and audit and are never materialized.

### 2.1 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| `Profilefile.json` absent, malformed, unknown field, wrong version, empty `profiles` | `profile_index_invalid` |
| declared profile root missing, aliased, or nested below another | `profile_root_invalid` |
| `context/` present without `context.json` | `profile_context_manifest_invalid` |

## 3. Context manifest and modules

`context/context.json` is a strict schema-1 object:

```json
{
  "version": 1,
  "modules": [
    { "path": "00-base.md" },
    { "path": "10-style.md" },
    { "path": "20-claude.md", "environments": ["claude_code"] },
    { "path": "90-system.md", "class": "system" }
  ]
}
```

Readers MUST reject duplicate keys, unknown fields at either level, and a
`version` other than `1`. `modules` is REQUIRED and MAY be empty. Each entry
carries:

- **`path`** (REQUIRED) — a portable relative path (core §2) naming a
  regular file below `context/`. Paths are unique across the manifest; a
  duplicate is rejected.
- **`environments`** (OPTIONAL) — a non-empty set-like array of unique
  environment identifiers under the core §2 grammar. An absent selector
  means every environment. An identifier that is not in the machine's
  adapter registry is permitted, produces the warning
  `profile_selector_unknown_environment` at snapshot validation, and selects
  nothing — the manager §5 unknown-identifier discipline.
- **`class`** (OPTIONAL) — exactly `root` or `system`; the default is
  `root`. `system` marks the module as system-prompt content under sections
  5.5 and 7.3.

A module is UTF-8 markdown. Snapshot validation MUST reject a module that is
not valid UTF-8, contains any line ending other than LF, or does not end
with exactly one trailing LF, with `profile_module_bytes_invalid`. There is
no normalization path: a violating module fails the snapshot, it is never
rewritten. A module that validates is thereafter opaque bytes;
materialization MUST reproduce it exactly and MUST NOT apply templating,
variable substitution, inclusion, transcoding, or any other transformation.

A module **applies** to an environment when its selector is absent or
contains that environment's identifier. The **applicable root modules** of a
profile for an environment are its `class: root` modules that apply, in
manifest order; the **applicable system modules** are its `class: system`
modules that apply, in manifest order.

### 3.1 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| manifest malformed, unknown field, wrong version, duplicate or invalid entry | `profile_context_manifest_invalid` |
| declared module file absent or not a regular file | `profile_module_missing` |
| module not UTF-8, non-LF line ending, or trailing-LF violation | `profile_module_bytes_invalid` |
| selector names an unregistered environment (warning) | `profile_selector_unknown_environment` |

## 4. Profile store

Every installed profile has exactly one store entry below the manager home,
keyed by its effective pin: the resolved commit for a `git` profile, the
state hash for a `local` profile. Store entries are immutable regular-file
trees. Every materialization mode of section 8 — `managed-home`, `linked`,
and `copied` — materializes from the same store entry, so the modes cannot
diverge for one pin. Physical store paths are implementation-specific
(manager §1); the store joins garbage collection under section 12.

## 5. Deterministic materialization

Materialized root context is a pure function of (profile store entry,
composition chain, environment identifier, form). Identical inputs MUST
yield byte-identical output on every platform and in every mode. The rules
below define the exact bytes; they are a determinism conformance-vector
surface.

**Parts and joining.** Output is assembled from ordered **parts**. Every
part is a byte string ending with exactly one LF. The document is the parts
joined with exactly one additional LF between adjacent parts — one empty
line — and nothing else. Because every part ends with exactly one LF, the
output is LF-encoded and ends with exactly one trailing LF by construction.

The part sequence for a root-context document is:

1. the generation header (section 5.1);
2. without composition: the applicable root modules of the profile, in
   manifest order;
3. with composition (section 6): for each profile of the composition chain
   in chain order — a chapter part, then that profile's applicable root
   modules in manifest order. The chapter part is emitted for every composed
   profile, including one whose applicable module set is empty.

A **chapter part** is exactly the bytes
`---` LF LF `## Profile: ` `<profile-name>` LF — a thematic-break line, one
empty line, and a heading naming the composed profile:

```text
---

## Profile: <profile-name>
```

No pin, path, or other data appears in a chapter part.

### 5.1 Generation header

Every materialized root-context file begins with the generation header, an
HTML comment that markdown renderers do not display. Its grammar is closed;
a writer MUST emit exactly these lines in exactly this order, each
terminated by one LF:

```text
<!--
curator-root-context-v1
profile: <name> <pin>
compose: <name> <pin>
precedence: <direction>
generated: Curator Protocol environments revision 1 (https://github.com/relux-works/curator-spec)
notice: generated file; direct edits are unsupported and are detected as drift; update the source profile repository or its composed profiles instead
-->
```

- `<pin>` is `commit <full-hex>` — the full lowercase commit — for a `git`
  profile, or `state sha256:<64 lowercase hex>` for a `local` profile.
- The `profile:` line names the activated profile and appears exactly once.
- One `compose:` line per overlay, in declared order, and one `precedence:`
  line — `later-overrides-earlier` or `earlier-overrides-later` — appear
  exactly when composition is active, and are otherwise absent.
- The `generated:` and `notice:` lines are the fixed byte strings above.

The header contains no timestamp, machine path, operator identity, hostname,
or locale. Nothing else may be added: an unknown header line is a
conformance failure, not an extension point.

### 5.2 Monolithic form

In the `monolithic` form each applicable root module contributes one part:
its exact validated bytes. The output is one file at the adapter's declared
root-context target (section 7.1). Every adapter supports `monolithic`.

### 5.3 Referenced form

In the `referenced` form the applicable root modules materialize as
individual files that the root file references through the tool's native
mechanism. The layout is fixed:

- Module files land below the managed directory `.agent-context/modules/`
  beside the root-context file, grouped per source profile:

  ```text
  <home>/.agent-context/modules/<profile-name>/<module-path>
  ```

  `<module-path>` is the module's manifest `path` verbatim. Grouping by
  profile name makes two composed profiles carrying the same module filename
  collision-free by construction; within one profile, manifest paths are
  unique by section 3. The literal path segment `modules` is fixed and is
  not a profile name, so no profile-name value can collide with the sibling
  `system-prompt.md` of section 5.5.

- Each materialized module file is the module's exact bytes. No header,
  chapter, or reference line is added to a module file.

- The root file is assembled by the section 5 part rules, with each module
  part replaced by that module's **reference part** — for `claude_code`, the
  single line:

  ```text
  @.agent-context/modules/<profile-name>/<module-path>
  ```

  Chapter parts and the generation header are unchanged. References stay
  inside the home, so `claude_code` referenced output never requires the
  tool's external-include approval.

- For `opencode`, the tool's reference mechanism is the `instructions` array
  of `<home>/opencode.json`, not root-file syntax. The root file is the
  generation header part alone. The manager maintains the `instructions`
  member as the ordered list of `.agent-context/modules/<profile-name>/<module-path>`
  values, in exactly the order the modules would appear monolithically. The
  `opencode.json` surface is then a managed surface recorded in the
  environment marker. When `<home>/opencode.json` exists and is not recorded
  by the preceding marker, the referenced form is unavailable: the adapter
  MUST warn `environment_form_unavailable` and materialize `monolithic`
  instead — it MUST NOT edit the unmanaged file.

The effective form per environment is chosen by machine configuration with
the adapter's default (section 7.2), never by profile data. When the
configured form is unavailable — the tool gates it, or an unmanaged file
blocks it — the adapter falls back to `monolithic` with
`environment_form_unavailable`; it never fails the operation for form
availability alone.

### 5.4 Zero applicable modules

A root-context materialization whose applicable module set is empty produces
the header part alone — under composition, the header followed by the empty
chapters. Empty output (zero bytes) never occurs, the file is always
written, and a zero-module materialization is valid, not an error. In the
referenced form no module files are materialized and, for `opencode`, the
managed `instructions` array is empty. This is distinct from a profile with
no `context/` directory (section 2), for which no root-context surface
exists and no file is written.

### 5.5 System-prompt output

The applicable system modules — under composition, of every profile in
chain order — materialize as one file assembled by the part-joining rule
with **no generation header and no chapter parts**: system-prompt bytes
reach the model verbatim, so no generated text is injected. Provenance and
drift detection for this surface come from the environment marker's recorded
content hash, not from an in-file header.

The system output materializes only into managed homes (section 8.1), at:

```text
<home>/.agent-context/system-prompt.md
```

This file is inert: no revision-1 tool reads that path natively. It exists
so the launch fragment (section 10.2) can name it. When the profile and its
composition carry no applicable system modules, the file is absent and the
fragment carries no system-prompt section.

For `pi` only, machine configuration MAY additionally set, per
profile × environment, `system_prompt_files` to exactly `off` (default),
`append`, or `replace`. `append` materializes the system output additionally
at `<home>/APPEND_SYSTEM.md`; `replace` materializes it at
`<home>/SYSTEM.md`. Both are live channels the tool applies unconditionally
when present (section 7.3), so under `off` neither file is written and a
plain launch of a managed home carries no active system prompt. System
modules MUST NOT materialize into a native in-place home in any mode, and
secondary fixed-home targets (section 7.6) never receive system modules in
revision 1.

### 5.6 Content-hash binding

Every materialized surface binds a content hash recorded in the environment
marker (section 8.2). The surface hash is the core §8 content hash over the
surface's materialized file set, where each file's protocol path is its
home-relative portable path. For a single-file surface this degenerates to
one record; for the referenced form the set contains the root file, every
materialized module file, and — for `opencode` — the managed
`opencode.json`. Identical (store entry, composition chain, environment,
form) MUST yield an identical surface hash on every platform; this equality
is a conformance-vector surface.

### 5.7 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| configured form unavailable; monolithic emitted (warning) | `environment_form_unavailable` |
| materialization would overwrite a file the marker does not record | `environment_surface_unmanaged_conflict` |

## 6. Composition

A machine MAY declare, per installed profile, an ordered **overlay list**:
installed profiles whose root context, system modules, and skills are
appended when that profile is activated or resolved. The declaration lives
in machine configuration only; profile data MUST NOT declare, request, or
alter composition. Any installed profile may serve as an overlay — an
overlay is not a distinct package shape.

The **composition chain** is the activated profile followed by its declared
overlays in declared order. Only the activated profile's overlay list
applies: an overlay's own overlay declarations are ignored, so composition
never recurses and cannot cycle. A chain member that repeats, or an overlay
that is not an installed profile, is `environment_composition_invalid`.

The declaration names the **precedence direction**; the default is
`later-overrides-earlier`, with `earlier-overrides-later` available
explicitly. Instruction text cannot be merged mechanically: precedence is
declared to the reader and the agent — in the generation header (section
5.1) and the chapter structure — never resolved silently by the manager.

Skill-set composition is mechanical. The composed closure resolves the union
of every chain member's `Skillfile.json`; when two chain members declare the
same skill, the declaration from the profile that precedence favors wins,
and a version divergence between chain members is reported as a warning
naming both profiles and both refs. The winning declarations resolve through
the unchanged core §7 closure and manager §2 lifecycle.

The composition chain and precedence direction are recorded in the
generation header, the environment marker, and the launch fragment, so
status, drift detection, and session resume always see exactly what was
assembled.

| Condition | Diagnostic |
| --- | --- |
| chain repeats a member or names an uninstalled overlay | `environment_composition_invalid` |
| two chain members declare one skill at diverging versions (warning) | `environment_composition_skill_divergence` |

## 7. Environment adapter registry

The manager §5 agent-adapter table generalizes to a closed **environment
adapter registry**. Adapters are manager code, never package code. Admitting
a new adapter is a specification revision with its own review — the core
§12.3 closed-set discipline. An environment identifier not in the registry
keeps the manager §5 behavior: a warning and no output, except where a
section below requires an error for an explicit operand.

### 7.1 Revision-1 adapters

The closed revision-1 adapter set is exactly:

| Environment | Home mechanism | Home shape | Root-context target | Skills target |
|---|---|---|---|---|
| `claude_code` | `CLAUDE_CONFIG_DIR=<home>` | variable names the home | `<home>/CLAUDE.md` | `<home>/skills/` |
| `codex_cli` | `CODEX_HOME=<home>` | variable names the home | `<home>/AGENTS.md` | `<home>/skills/` |
| `opencode` | `XDG_CONFIG_HOME=<parent>` | tool reads `<parent>/opencode/` as the home | `<home>/AGENTS.md` | the manager §5 native surface (`~/.agents/skills`), unchanged in revision 1 |
| `pi` | `PI_CODING_AGENT_DIR=<home>` | variable names the home | `<home>/AGENTS.md` | `<home>/skills/` |

`gemini`, `cursor`, and `windsurf` remain skills-only adapters under the
unchanged manager §5 table in revision 1. Tools with no home-isolation
mechanism are out of scope.

`XDG_CONFIG_HOME` is a generic XDG variable: every XDG-conforming child of a
launched `opencode` session resolves configuration under the managed parent.
Revision 1 accepts and narrows this: when a managed `opencode` parent is
provisioned, the manager seeds it with symlinks to every entry of the
operator's effective XDG config home except `opencode/`. Seed links are
recorded in the environment marker; refresh adds missing recorded seeds and
removes recorded seeds whose target no longer exists, and MUST NOT touch an
entry the marker does not record. A dedicated opencode home variable, should
the vendor ship one, supersedes the XDG mechanism in a later revision.

### 7.2 Root-context forms

| Environment | Forms supported | Default form |
|---|---|---|
| `claude_code` | `monolithic`, `referenced` | `monolithic` |
| `codex_cli` | `monolithic` | `monolithic` |
| `opencode` | `monolithic`, `referenced` | `monolithic` |
| `pi` | `monolithic` | `monolithic` |

The effective form is machine configuration with these defaults; profile
data cannot select a form. Requesting `referenced` for an adapter that does
not support it is a configuration error, not a fallback case.

### 7.3 System-prompt channels

Each adapter declares its closed channel-descriptor list. A descriptor's
`kind` is exactly `flag`, `config-key`, `variable`, or `file`; its
`semantics` is exactly `append` or `replace`.

| Environment | Channels |
|---|---|
| `claude_code` | `flag`/`append`: `--append-system-prompt-file`; `flag`/`replace`: `--system-prompt-file` |
| `codex_cli` | `config-key`/`replace`: `model_instructions_file` |
| `opencode` | none in revision 1 |
| `pi` | `flag`/`append`: `--append-system-prompt-file`; `flag`/`replace`: `--system-prompt-file`; `file`/`append`: `APPEND_SYSTEM.md`; `file`/`replace`: `SYSTEM.md` |

`pi`'s two `file` channels are applied by the tool unconditionally when the
file exists in the agent home; section 5.5 therefore keeps both absent
unless machine configuration explicitly materializes one. Channel
descriptors are data about a channel: nothing in this document applies one.
Application is the launcher's surface, behind its explicit opt-in and
warnings, outside this specification.

### 7.4 Credential passthrough

Credentials are never profile content and never managed surfaces. Each
adapter declares the closed passthrough set a managed home shares with the
native home, by symlink or seeding:

| Environment | Passthrough entries |
|---|---|
| `claude_code` | macOS: none (Keychain is ambient); Linux: `.credentials.json`; Windows: none in revision 1 (reserved pending platform verification) |
| `codex_cli` | `auth.json` |
| `opencode` | none (auth lives in the XDG data directory, which the config swap never touches) |
| `pi` | `auth.json` |

The default per profile × environment is `shared`: every managed home reuses
the operator's existing authentication through exactly these entries. A
profile × environment pair MAY be configured `isolated`: no passthrough, the
tool authenticates fresh inside the managed home — the supported shape for
genuinely separate accounts. Passthrough entries are excluded from surface
content hashes and drift detection, are never copied into the profile store,
and are never audited as profile content. Materialization, refresh, switch,
and garbage collection MUST NOT create, rewrite, or delete a credential file
beyond maintaining the declared passthrough links themselves.

### 7.5 Shadowing paths

An adapter declares its known **shadowing paths**: higher-precedence
unmanaged files whose presence makes a managed surface inert. The closed
revision-1 declarations are:

| Environment | Shadowing path | Shadowed surface |
|---|---|---|
| `pi` | `AGENTS.override.md` beside the root-context target | root context |

`claude_code`, `codex_cli`, and `opencode` declare none in revision 1. The
adapter ledger and environment marker protect only managed paths, so
materialization and `env status` MUST warn `environment_shadowing_path_present`
when a declared shadowing path exists; the file itself is never touched.

### 7.6 Secondary fixed-home targets

Some hosts embed an agent environment at a fixed home no environment
variable can retarget, with the primary home's internal layout. An adapter
MAY declare a closed list of such targets: a target identifier (core §2
grammar), a probe path, a home path, and the subset of surfaces the embedded
host honors. Revision 1 declares exactly two, recorded from vendor
documentation for Xcode's CodingAssistant; the paths verify against a pinned
Xcode release before the conformance vectors freeze:

| Adapter | Target id | Probe path | Home | Surfaces honored |
|---|---|---|---|---|
| `claude_code` | `xcode-coding-assistant` | `~/Library/Developer/Xcode/CodingAssistant/` | `~/Library/Developer/Xcode/CodingAssistant/ClaudeAgentConfig/` | root context, skills |
| `codex_cli` | `xcode-coding-assistant` | `~/Library/Developer/Xcode/CodingAssistant/` | `~/Library/Developer/Xcode/CodingAssistant/codex/` | root context, skills |

A secondary target is an in-place surface set: it carries the environment
marker and ledger discipline of section 8, defaults to `copied` mode, and
always reflects the current profile for its scope — an embedded host
launches its agent itself, so managed homes can never reach it. The embedded
hosts' own files (`.claude.json`, `commands/`, `config.toml`, caches) are
unmanaged in revision 1 and MUST NOT be written.

Target participation is machine configuration, never profile data: `auto`
(default), `off`, or an explicit per-target enable. Under `auto` the target
participates exactly when its probe path exists: a machine without the probe
path materializes nothing there and reports nothing missing; a machine with
it re-materializes the target on every install, `use`, and `sync`. Probe
results appear in `env status`. A target identifier not declared by the
registry is `environment_target_unknown`.

### 7.7 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| explicit operand names an unregistered environment | `environment_unknown` |
| explicit operand names an undeclared target | `environment_target_unknown` |
| declared shadowing path exists (warning) | `environment_shadowing_path_present` |

## 8. Materialization modes and the environment marker

### 8.1 Modes

A profile materializes into an environment in exactly one of three modes:

- **`managed-home`** — the manager provisions a complete home directory per
  profile × environment below a manager-owned **environments root** in the
  manager home. The only profile-derived path component below that root is
  the profile name, bounded by the core §2 grammar. Managed surfaces inside
  the home are symlinks into the profile store, with copies where a surface
  or platform requires bytes. The environment's own mutable state — session
  logs, history, caches, trust records — lives beside them, owned by the
  tool, giving each profile naturally isolated session state. A managed
  home is activated only by consuming a resolved fragment (section 10);
  nothing in this document applies one to a running process.
- **`linked`** — in-place materialization into the environment's native
  default home as symlinks into the profile store: the manager §5
  symlink-with-copy-fallback discipline extended from skills to root
  context. Only the current profile for the applicable scope (section 9.2)
  is materialized in place.
- **`copied`** — in-place materialization as plain files with recorded
  content hashes, for surfaces or targets where symlinks are unreliable:
  secondary fixed-home targets, link-hostile tools, network filesystems.

Mode defaults: the four adapters default to `linked` for their in-place
surfaces; secondary fixed-home targets default to `copied`; managed homes
always link from the store. An adapter MAY declare a different in-place
default in the registry; profile data cannot.

All three modes materialize from the same store entry (section 4), so they
cannot diverge for one effective pin.

### 8.2 Environment marker, schema 1

Every in-place surface set and every managed home carries a per-home
**environment marker**, `.agent-environment.json`, a strict schema-1 object
beside the managed surfaces. The marker records:

- `version` — exactly `1`;
- `profile` — name, source kind, canonical source identity and declared ref
  for `git`, and the effective pin (`commit` for `git`, `state_sha256` for
  `local`);
- `composition` — the ordered overlay chain with each member's name and
  effective pin, present exactly when composition is active, together with
  the declared `precedence`;
- `mode` — exactly `managed-home`, `linked`, or `copied`;
- `surfaces` — one entry per managed surface: its home-relative file
  paths, its form where the surface has one, its content hash under section
  5.6, and — for a `linked` home — whether any entry fell back from symlink
  to copy under the manager §5 discipline. Surface keys are sorted; required
  arrays are present even when empty;
- for a managed `opencode` parent, the recorded seed links of section 7.1.

Readers MUST reject an unsupported marker version and MUST NOT infer newer
semantics from unknown fields. An unreadable or invalid marker fails closed:
the home's surfaces are treated as unmanaged — nothing is removed or
replaced — and status reports `environment_marker_invalid`. The marker joins
the `agent-*` identifier family deliberately; the frozen core §1.1
identifiers keep their exact spellings.

The marker is a record, not a signature: it MUST NOT be used as an
authorization token or provenance proof (core §10 discipline).

### 8.3 Ledger discipline and backups

The marker is the ledger of record for environment surfaces, extending the
core §11 rule unchanged: a manager MUST remove or replace only files its
preceding marker records and MUST fail with
`environment_surface_unmanaged_conflict` rather than overwrite an unmanaged
file. Skill entries keep the core §11 adapter ledger; the two records never
merge.

Takeover and onboarding backups (section 9.5) land in
`.agent-environment-backup/` beside the marker, preserving each file's
home-relative path. A backup, once written, is never overwritten: an
operation that would replace an existing backup path MUST fail with
`environment_backup_exists`. Backups are outside every surface hash and are
never garbage-collected by revision-1 rules.

### 8.4 Drift

For `linked` surfaces, drift is a link that no longer targets the expected
store path or a target whose bytes fail the recorded hash. For `copied` and
`managed-home` surfaces, drift is a recorded content hash that no longer
matches. Drift detection MUST state both halves explicitly: the surface was
modified outside the manager, and the file was left untouched; the
installation is non-current, and `repair` restores the managed bytes. A
drifted file is never silently overwritten outside `repair`.

An absent surface file and a failed read are different facts: a read failure
is `environment_marker_invalid` or an I/O error, never treated as a
legitimate absence, and no absence-shaped fallback may fire on it.

### 8.5 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| marker unreadable, malformed, or unsupported version | `environment_marker_invalid` |
| managed surface bytes or link differ from the record (non-current) | `environment_surface_drift` |
| recorded surface file absent (non-current) | `environment_surface_missing` |
| write would touch a file the marker does not record | `environment_surface_unmanaged_conflict` |
| backup path already exists | `environment_backup_exists` |

## 9. Profile lifecycle

### 9.1 Installation and audit

`profile install <git-url>` resolves the source under section 1, validates
the snapshot under sections 2 and 3, audits it, and installs **every**
profile the repository declares as independent pinned profiles. Profiles
installed from any number of repositories coexist as one machine profile
set.

Profile installation always runs the manager §7 source audit in strict
mode; an advisory profile install does not exist. The audit pipeline is
unchanged — raw-tree hashing, the static canary whose failure always
blocks, deterministic detectors, revocation — and gains one REQUIRED
detector class for profile snapshots:

- **`context-secret-material`** — a deterministic detector over context
  modules, `Profilefile.json`, `context.json`, and `PROFILE.md` that reports
  credential-like material (keys, tokens, passwords, and equivalent secret
  classes) as a verifiable finding at blocking severity. Because profile
  installation is always strict, a profile carrying such a finding fails
  installation.

Root-context modules are prompt material: audit tooling SHOULD surface them
for human prompt-injection review; the pipeline guarantees provenance and
immutability, not intent.

Activation on install follows operator intent without magic: `install` sets
the machine current profile only when the machine has none — first install,
and the activation is reported, never silent — or when the operator passes
`--use <name>`. `--use` without a name is valid exactly when the repository
declares one profile; with more than one it is `profile_index_ambiguous`. In
every other case the manager prints the installed profiles and how to
activate one.

### 9.2 Current profile and switching

Machine configuration records at most one machine **current profile**, plus
per-scope current profiles under section 9.3. `profile use <name>`:

1. re-materializes every in-place surface of every registered adapter —
   native default homes and every participating secondary fixed-home
   target — from the selected profile's store entry, atomically per entry,
   under the manager-home mutation lock, journaled like any other
   manager-home transaction (manager §2.5);
2. updates the recorded current profile for the affected scope;
3. warns that already-running agent sessions keep the previous context in
   memory and may write state derived from it, and recommends launching
   through managed homes for concurrent multi-profile work.

The switch never touches environment-owned mutable state, credential files
beyond section 7.4 links, unmanaged files, or backups.

### 9.3 Scoped switching

`profile use` accepts `--env <env-id>` and `--target <target-id>` to narrow
the switch to a subset of registered adapters or to one secondary fixed-home
target. A scoped switch records a per-scope current profile. `env status`
and `profile list` MUST surface every scope whose current profile differs
from the machine default: a split-brain configuration is always visible,
never implicit. An unknown `--env` operand is `environment_unknown`; an
unknown `--target` operand is `environment_target_unknown`.

### 9.4 Profile-scoped skills and migration

The existing machine-global skill scope becomes profile-scoped. Each
profile's `Skillfile.json` resolves through the unchanged closure, audit,
build, and runtime machinery; the resolved skills materialize into that
profile's managed homes and — for the current profile of each scope — the
in-place adapter surfaces under the manager §5 discipline. Global skill
operations act on the current profile and accept `--profile <name>` and
`--all-profiles`. `profile sync` re-materializes every installed profile
across every registered adapter and participating target; it is the
actualization path when a new adapter or target is registered on the
machine.

Migration: on first use of the profile surface, the existing machine-local
global scope is renamed into a builtin profile `default` with its current
`Skillfile.json` and no root context. `default` carries source kind `local`:
no git identity, no ref, no commit; its store key and effective pin are its
state hash, recomputed when its state changes. Switching, `profile sync`,
and `env status` treat a `local` profile exactly like an installed one. A
machine that never installs another profile observes no behavior change:
`default` simply is the current profile and existing global installations
keep their behavior byte-for-byte.

### 9.5 Onboarding, revision-1 subset

A machine with hand-maintained global context must reach managed state
without loss. Revision 1 ships detection, the foreign-manager stop, the
replace notice, backup, and takeover; the import machinery — lossless/lossy
classification, the lossy consent branch, the `path` source kind, and
native-skill migration — is deferred with the `path` kind
(STORY-260901-2hkq49).

On bootstrap, or on the first profile operation that meets unmanaged state,
the manager:

1. **Inventories**, per registered adapter and participating target:
   existing unmanaged root-context files; existing global skills; and
   managed-surface paths that are already symlinks pointing outside the
   manager's store. The last is evidence of another manager and stops the
   operation with `environment_foreign_manager_detected` and an explicit
   choice — abort, or take over with backup — never a silent absorption.
2. **Notifies**: before any write, the operator is told that native global
   context files are being replaced by managed ones and where the backup
   lands.
3. **Backs up, always**: every file the operation will replace is copied
   into the section 8.3 backup location before the first write, whether or
   not any import was requested, subject to `environment_backup_exists`.

Takeover of a specific unmanaged file outside onboarding requires the
explicit takeover flag and performs the same notice and backup; without the
flag, section 8.3 applies and the operation fails rather than overwrite.
Authentication is never part of onboarding or takeover: credential files
stay where the section 7.4 passthrough expects them, untouched.

### 9.6 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| foreign-manager symlink detected during onboarding | `environment_foreign_manager_detected` |
| audit finding from the secret-material detector class (blocking) | finding class `context-secret-material` |
| `--use <name>` names an undeclared profile | `profile_unknown` |
| bare `--use` with more than one declared profile | `profile_index_ambiguous` |

## 10. Resolution and the launch fragment

### 10.1 `env resolve`

The manager's only execution-facing primitive is:

```text
env resolve <env-id> [--profile <name>] [--format json|env|shell]
```

It resolves a profile — the named one, otherwise the current profile for the
applicable scope — and an environment to a **launch environment fragment**.
Resolution is a pure function from (profile, composition chain, environment,
machine configuration) to the fragment; it launches nothing and applies no
channel.

Resolution verifies that the profile's managed home for the environment is
materialized and current under section 8, and repairs it from the store when
it is not — re-materializing managed surfaces and passthrough links while
leaving environment-owned mutable state, unmanaged files, and backups
untouched. Repair restores managed bytes from the store entry; it MUST NOT
adopt candidate bytes found in the home. A repair that cannot complete —
the store entry is missing or fails validation — is
`environment_repair_failed`, and no fragment is emitted.

`--format json` prints the closed `launch-env-fragment-v1` object.
`--format env` prints one `NAME=value` line per fragment variable,
LF-terminated, in the adapter's declared variable order. `--format shell`
prints one POSIX `export NAME='value'` line per variable with single-quote
escaping. An unregistered `<env-id>` is `environment_unknown`; an
uninstalled `--profile` operand is `profile_unknown`.

### 10.2 `launch-env-fragment-v1`

The fragment is a closed object; readers MUST reject unknown fields,
unknown kinds, and unknown semantics values:

```json
{
  "fragment": "launch-env-fragment-v1",
  "environment": "claude_code",
  "profile": { "name": "companyA", "commit": "<full lowercase hex>" },
  "composition": [ { "name": "personal", "commit": "<full lowercase hex>" } ],
  "precedence": "later-overrides-earlier",
  "env": { "CLAUDE_CONFIG_DIR": "<absolute managed-home path>" },
  "system_prompt": {
    "path": "<absolute path to .agent-context/system-prompt.md>",
    "channels": [
      { "kind": "flag", "semantics": "append", "flag": "--append-system-prompt-file" },
      { "kind": "flag", "semantics": "replace", "flag": "--system-prompt-file" }
    ]
  }
}
```

- `profile` carries `commit` for a `git` profile and `state_sha256` for a
  `local` profile, never both.
- `composition` and `precedence` are present exactly when composition is
  active; `composition` members carry the same pin shape as `profile`.
- `env` maps each registry-declared variable name for the environment to a
  managed-home path.
- `system_prompt` is present exactly when the resolved chain carries at
  least one applicable system module. It is data about a channel, never an
  applied override: `path` names the inert section 5.5 file and `channels`
  reproduces the adapter's section 7.3 descriptors (`flag`, `config-key`
  with `key`, `variable` with `variable`, or `file` with `filename`).
  Resolving a fragment activates nothing.

### 10.3 The profile-influence boundary

Fragment variable names come only from the closed adapter registry.
Fragment values are absolute paths below the manager-owned environments
root. Profile bytes MUST NOT select, add, rename, or retarget an
environment variable and MUST NOT move a value outside that root; the only
profile-derived component of a value is the profile-name path segment,
bounded by the core §2 grammar — no separators, no traversal. A profile
chooses what the context says, never how a process is launched. This is the
package-influence boundary of the core execution policies, applied to
environment injection.

### 10.4 Diagnostics

| Condition | Diagnostic |
| --- | --- |
| operand names an unregistered environment | `environment_unknown` |
| named or current profile not installed | `profile_unknown` |
| managed home cannot be repaired from the store | `environment_repair_failed` |

## 11. Umbrella subcommand discovery

A CLI subcommand the manager does not implement resolves to an executable
named `curator-<name>` on `PATH` and is executed with the remaining
arguments verbatim — the established git/kubectl/docker external-subcommand
convention. The rules are closed:

- `<name>` is the operator's typed subcommand and MUST match the core §2
  identifier grammar; anything else is a usage error, not a lookup.
- An implemented subcommand always wins; discovery runs only for unknown
  names.
- The manager carries no knowledge of any provider: no provider registry,
  no provider-specific flags, no version coupling.
- A missing provider fails with the exact executable name and installation
  guidance; nothing is downloaded or installed implicitly.
- Profile data, marker data, and fragment data MUST NOT influence the
  dispatched name, the resolved path, or the argument vector. Dispatch input
  is operator argv and `PATH` alone.

This is the one place the manager executes an executable it does not ship;
the trust model is exactly the host plugin convention named above. The
first providers, informative here, are `curator-run` (the launcher, its own
specification) and `curator-session` (a shim to the agent session manager).

| Condition | Diagnostic |
| --- | --- |
| unknown subcommand with no `curator-<name>` on `PATH` | `subcommand_provider_missing` |

## 12. Status and garbage collection

`profile list` reports every installed profile: name, source identity,
declared ref, effective pin, and current markers — the machine default and
every section 9.3 scope that differs. A `local` profile reports `local` as
its source, `-` for ref, and its state hash as the effective pin.

`env status [--check] [--json]` reports the
profile × environment × surface matrix: mode, form, materialized pin,
content-hash currency, drift, missing surfaces, marker validity,
unregistered adapters found in machine configuration, every declared
shadowing path that exists, the active composition chain per activation,
every scope whose current profile differs from the machine default, and
secondary-target probe results. Both commands follow the manager §10
discipline exactly: recompute and report, never mutate — no fetch, no
repair, no adoption, no channel application. `--check` returns non-zero
when any row is non-current.

An installation row is current only when its marker is valid and supported;
profile identity, pin, composition chain, precedence, mode, and form match
the effective machine state; and every recorded surface hash verifies. A
drifted, missing, shadow-inert, or unreadable state is non-current;
unreadable evidence is reported as unreadable, never as absence (section
8.4).

Garbage collection extends the manager §10 and core §9.4 rules: it runs
under the manager-home mutation lock, and its live roots additionally
include every profile store entry referenced by an installed profile's
effective pin, every managed home and in-place surface set referenced by a
valid environment marker, and every entry referenced by an in-flight
transaction journal. An unreadable marker or unprovable reference fails
safe: the uncertain entries are retained and the uncertainty reported.
Environment-owned mutable state inside managed homes is never collected.

## 13. Conformance surfaces

The following surfaces of this document are conformance-vector surfaces,
with schemas and vectors delivered separately (`schemas/v1/`, positive and
negative vectors, and byte-exact determinism vectors): `Profilefile.json`
schema 1, `context.json` schema 1, module byte validation, the section 5
materialization bytes — generation header, part joining, chapter parts,
zero-module output, referenced-form layout, and system-prompt output — the
section 5.6 hash binding, `.agent-environment.json` schema 1, and
`launch-env-fragment-v1`. A manager claiming this capability MUST pass the
complete vector set; there is no partial claim.
