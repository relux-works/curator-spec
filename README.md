# CocoaSkills Specification

**Version:** 1.0.0-draft  
**Date:** 2026-07-12  
**Authors:** Ivan Oparin, Alexey Grigorev  
**Status:** Draft  
**Compatibility target:** CocoaSkills 0.12.x  
**Reference implementation:** [github.com/ivanopcode/cocoaskills](https://github.com/ivanopcode/cocoaskills) (`csk`, Python 3.11+, stdlib-only runtime)  
**Reference registry server:** [github.com/ivanopcode/cocoaskills-registry](https://github.com/ivanopcode/cocoaskills-registry)

---

## Abstract

CocoaSkills is a dependency manager for AI agent skills: reusable instruction packages that give coding agents specialized capabilities. The skill ecosystem is young, growing rapidly, and lacks standard tooling for declarative dependency management, reproducible installation, or supply chain security.

This document specifies the CocoaSkills protocol and formats as implemented by the reference implementation: the skill package format (a constrained profile of the common SKILL.md convention plus the `csk-skill.json` manifest, schemas 1 through 5), the project manifest (`Skillfile.json`) with development substitutions, machine and system configuration, dependency closure resolution with exact references, the installation contract (context and runtime separation, per-agent adapters, install markers, content hashing), install scopes (project, global, hybrid), MCP server requirements, the source audit pipeline, and the audit registry protocol (Ed25519 signed audit records, deny-wins federation, signed snapshots, and an HTTP registry service with a hash-chained log and air-gap bundles).

The architecture draws from classical dependency managers (Bundler, SPM, Gradle, Cargo) but addresses problems specific to an infrastructure that remains immature. Skills are a new embodiment of source code: even a plain markdown skill file with no executables can be a vector for prompt injection, and as skills grow in complexity they pull in commands and external tools that demand explicit security boundaries. CocoaSkills answers this with declared capabilities, a machine-level source allowlist, a static audit gate, and registry-backed attestation and revocation verified with public key cryptography.

The goal of this specification is interoperability. An independent skill manager built from this document alone works with the same skills, the same project manifests, and the same audit registries as the reference implementation. Normative sections describe only behavior that exists in the reference implementation; ideas that are not implemented live in the non-normative Future work appendix.

---

## Table of Contents

- [1. Overview](#1-overview)
- [2. Terminology](#2-terminology)
- [3. Architecture](#3-architecture)
  - [3.1 Machine Layout](#31-machine-layout)
  - [3.2 Project Layout](#32-project-layout)
  - [3.3 Data Flow](#33-data-flow)
- [4. Skill Package Format](#4-skill-package-format)
  - [4.1 Package Layout](#41-package-layout)
  - [4.2 Context Whitelist](#42-context-whitelist)
  - [4.3 Localization](#43-localization)
  - [4.4 Relationship to the Common SKILL.md Convention](#44-relationship-to-the-common-skillmd-convention)
- [5. The csk-skill.json Manifest](#5-the-csk-skilljson-manifest)
  - [5.1 Schema Versions](#51-schema-versions)
  - [5.2 Identifiers](#52-identifiers)
  - [5.3 runtime_roots](#53-runtime_roots)
  - [5.4 commands](#54-commands)
  - [5.5 capabilities](#55-capabilities)
  - [5.6 dependencies.commands](#56-dependenciescommands)
  - [5.7 dependencies.skills](#57-dependenciesskills)
  - [5.8 dependencies.mcp_servers](#58-dependenciesmcp_servers)
  - [5.9 No Install Hooks](#59-no-install-hooks)
  - [5.10 Legacy Runtime Manifest](#510-legacy-runtime-manifest)
  - [5.11 Complete Example](#511-complete-example)
- [6. Skillfile: Project Manifest](#6-skillfile-project-manifest)
  - [6.1 Format (schema 1)](#61-format-schema-1)
  - [6.2 Development Substitutions: Skillfile.dev.json](#62-development-substitutions-skillfiledevjson)
  - [6.3 Managed .gitignore Block](#63-managed-gitignore-block)
- [7. Machine and System Configuration](#7-machine-and-system-configuration)
  - [7.1 User Configuration](#71-user-configuration)
  - [7.2 Enforced System Configuration](#72-enforced-system-configuration)
- [8. Resolution and Installation](#8-resolution-and-installation)
  - [8.1 Phase Order](#81-phase-order)
  - [8.2 Source Fetching and the Allowlist](#82-source-fetching-and-the-allowlist)
  - [8.3 Closure Resolution](#83-closure-resolution)
  - [8.4 Command Collisions](#84-command-collisions)
  - [8.5 Install Markers](#85-install-markers)
  - [8.6 Runtime Store and Command Shims](#86-runtime-store-and-command-shims)
  - [8.7 Consumers and Garbage Collection](#87-consumers-and-garbage-collection)
- [9. Install Scopes](#9-install-scopes)
  - [9.1 Project Scope](#91-project-scope)
  - [9.2 Global Scope](#92-global-scope)
  - [9.3 Hybrid Scope](#93-hybrid-scope)
- [10. Multi-Agent Delivery](#10-multi-agent-delivery)
  - [10.1 Adapters](#101-adapters)
  - [10.2 Native-Discovery Agents](#102-native-discovery-agents)
- [11. MCP Server Requirements](#11-mcp-server-requirements)
  - [11.1 Configuration Surfaces](#111-configuration-surfaces)
  - [11.2 Verification Semantics](#112-verification-semantics)
  - [11.3 Static Availability Warnings](#113-static-availability-warnings)
- [12. Source Audit](#12-source-audit)
  - [12.1 Pipeline](#121-pipeline)
  - [12.2 Decisions and Policy](#122-decisions-and-policy)
- [13. Audit Registry Protocol](#13-audit-registry-protocol)
  - [13.1 Records](#131-records)
  - [13.2 Canonical Bytes and Signatures](#132-canonical-bytes-and-signatures)
  - [13.3 Client Resolution: Deny-Wins Federation](#133-client-resolution-deny-wins-federation)
  - [13.4 Snapshot Verification](#134-snapshot-verification)
  - [13.5 Caching and Offline Grace](#135-caching-and-offline-grace)
  - [13.6 Registry Service HTTP API](#136-registry-service-http-api)
  - [13.7 Submission, Tokens, and Countersigning](#137-submission-tokens-and-countersigning)
  - [13.8 Transparency Log](#138-transparency-log)
  - [13.9 Air-Gapped Federation: Bundles](#139-air-gapped-federation-bundles)
  - [13.10 Publishing from the Client](#1310-publishing-from-the-client)
- [14. Shell Integration](#14-shell-integration)
  - [14.1 Shell Hook](#141-shell-hook)
  - [14.2 Environment Files](#142-environment-files)
- [15. CLI Reference](#15-cli-reference)
- [16. CI/CD Integration](#16-cicd-integration)
- [17. Conformance and Compatibility](#17-conformance-and-compatibility)
  - [17.1 Conformance for Independent Implementations](#171-conformance-for-independent-implementations)
  - [17.2 SKILL.md Compatibility](#172-skillmd-compatibility)
  - [17.3 Coexisting Tools](#173-coexisting-tools)
- [18. Reference Implementation Notes](#18-reference-implementation-notes)
- [Appendix A: Future Work (Non-Normative)](#appendix-a-future-work-non-normative)
- [Appendix B: Field Reference: csk-skill.json](#appendix-b-field-reference-csk-skilljson)
- [Appendix C: Field Reference: Skillfile.json](#appendix-c-field-reference-skillfilejson)
- [References](#references)

---

## 1. Overview

CocoaSkills is a dependency manager for AI agent skills and contexts. It provides declarative, reproducible, security-gated installation of agent skill packages into project repositories.

CocoaSkills solves three problems:

1. **Non-declarative skill management.** The dominant workflow in the ecosystem remains imperative: skills are added one at a time, with limited manifest-driven resolution and no separation between what the model reads and what the machine executes. CocoaSkills combines a committed project manifest, transitive dependency resolution with exact references, a context and runtime split, and multi-agent delivery into one workflow.

2. **Non-reproducible environments.** Teams need every developer and CI runner to operate with the same skills at the same versions. CocoaSkills pins every skill to an exact git reference, resolves each closure name to exactly one commit and one source identity, records install markers with content hashes, and detects local tampering and moved tags on the next install.

3. **Fragmented supply chain security.** Content scanning alone does not protect against publisher impersonation, artifact tampering, or silent content mutation within a pinned version. CocoaSkills layers defenses: a machine-level source allowlist, declared capabilities, a manifest that cannot execute code at install time, a static audit gate, and an audit registry protocol where machines verify Ed25519-signed audit and revocation records from registries they explicitly trust (Section 13).

The name "CocoaSkills" alludes to CocoaPods, the first dependency manager for iOS development, which brought order to a similarly immature ecosystem.

This document is the protocol and format specification. The reference implementation is the `csk` CLI at [github.com/ivanopcode/cocoaskills](https://github.com/ivanopcode/cocoaskills); a conforming independent implementation interoperates with the same skills, projects, and registries (Section 17).

---

## 2. Terminology

| Term | Definition |
|------|-----------|
| **Skill** | A reusable instruction package for an AI coding agent: a `SKILL.md` file with optional context directories, commands, and dependencies (Section 4). |
| **Context skill** | A skill without commands; it installs agent-facing content only. |
| **csk-skill.json** | The machine manifest of a skill: commands, runtime layout, capabilities, dependencies. Schema versions 1 through 5 (Section 5). |
| **Skillfile** | `Skillfile.json`: the committed project manifest declaring skills at exact git references (Section 6). |
| **Dev substitution** | A non-committed local override of a provider through `Skillfile.dev.json` (Section 6.2). |
| **Closure** | The set of declared skills plus every transitive skill requirement, unified by name to one commit and one source, ordered providers first (Section 8.3). |
| **Activation mode** | How a requirement consumes its provider: `full`, `runtime`, or `context` (Section 5.7). |
| **Install marker** | `.csk-install.json`: the per-skill record of what was installed, including the content hash and attestations (Section 8.5). |
| **Content hash** | A deterministic SHA-256 over an installed tree, `sha256:<hex>` (Section 8.5). |
| **Source identity** | The canonical `host/path` form of a git source; SSH and HTTPS URLs of one repository share one identity (Section 8.2). |
| **Runtime store** | `~/.cocoaskills/runtime/<skill>/<commit>/`: machine-level storage of command runtimes, shared across projects (Section 8.6). |
| **Shim** | A per-project (or global) entry in `.agents/bin/` pointing at a runtime store file (Section 8.6). |
| **Adapter** | A managed mirror of installed context into the directory a specific agent reads (Section 10). |
| **Scope** | Where a skill is declared and activated: project, global, or hybrid (Section 9). |
| **Audit registry** | A service serving Ed25519-signed audit records about skill artifacts; machines pin registry keys out of band (Section 13). |
| **Attestation** | The verified registry record that authorized an install, recorded in the marker (Section 13.3). |
| **Snapshot (registry)** | A signed commitment to the registry log head, used for rollback and freeze detection (Section 13.4). |
| **csk** | The reference implementation CLI. |

---

## 3. Architecture

### 3.1 Machine Layout

```text
~/.cocoaskills/
├── config.json              # machine configuration (Section 7.1)
├── consumers.json           # registry of project checkouts for GC (Section 8.7)
├── cache/
│   ├── <source>/<commit>/snapshot/   # immutable source snapshots (git archive)
│   └── registry/            # audit registry record cache and snapshot state (Section 13.5)
├── runtime/<skill>/<commit>/         # command runtimes shared across projects (Section 8.6)
├── audit/<hash-prefix>/...           # audit verdict cache and trust pins (Section 12)
├── dev/<skill>/             # clones for git dev substitutions (Section 6.2)
├── global/
│   ├── Skillfile.json       # global scope manifest (Section 9.2)
│   ├── skills/              # installed global context
│   ├── bin/                 # global command shims
│   └── env.sh, env.ps1
└── hybrid/
    ├── Skillfile.json       # hybrid scope manifest with per-skill targets (Section 9.3)
    └── skills/              # hybrid store, rendered once per machine
```

Skill source repositories live separately under the configured `skills_root`.

### 3.2 Project Layout

```text
project/
├── Skillfile.json           # committed
├── Skillfile.dev.json       # never committed (managed .gitignore)
├── .agents/                 # generated, never committed
│   ├── skills/<name>/       # installed context + .csk-install.json markers
│   ├── bin/                 # command shims
│   ├── env.sh, env.ps1      # PATH helpers
├── .claude/skills/          # adapter mirrors (per selected agent)
├── .codex/skills/
├── .cursor/rules/
└── .gemini/skills/
```

### 3.3 Data Flow

```text
Skillfile.json + Skillfile.dev.json + hybrid manifest
  -> closure resolution (fetch, allowlist, snapshots, manifests)   Section 8.2-8.3
  -> gates: skill validation, collisions, dependencies, MCP,
            source audit, audit registries, moved tags             Sections 8.1, 11, 12, 13
  -> materialization: runtime store + shims, context + markers,
            cleanup, env files, adapters                           Sections 8.5-8.6, 10
  -> garbage collection over consumers                             Section 8.7
```

The full phase order is normative and specified in Section 8.1.

---

## 4. Skill Package Format

A skill is a git repository (or a directory inside one) whose root contains a `SKILL.md` file. Everything else is optional. CocoaSkills consumes skills in this format and installs a filtered view of them into consuming projects.

### 4.1 Package Layout

```text
skill-example/
├── SKILL.md              # required: agent-facing instructions with YAML frontmatter
├── csk-skill.json        # optional: machine manifest (Section 5)
├── agents/               # context: agent-specific material (also: agents/openai.yaml interface hints)
├── references/           # context: supporting documents for the model
├── .skill_triggers/      # context: per-locale activation trigger catalogs
├── assets/               # context: static resources
├── templates/            # context: reusable templates
├── examples/             # context: usage examples
├── data/                 # context: data files
├── locales/
│   └── metadata.json     # localization metadata (Section 4.3)
├── scripts/              # runtime: command sources (Section 5.3)
└── tests/, README.md, …  # developer-facing, never installed
```

`SKILL.md` MUST exist at the package root. An installer MUST fail the installation of a skill whose snapshot has no `SKILL.md`.

### 4.2 Context Whitelist

Installation separates model-facing context from everything else. Only the following root entries are copied into the installed context directory (`.agents/skills/<name>/` in a project):

```text
SKILL.md  agents/  references/  .skill_triggers/  assets/  templates/  examples/  data/
```

Additionally, `scripts/` is copied into context only when the skill declares no commands in its manifest and a `scripts/` directory exists. A skill that exports commands keeps its `scripts/` out of the model context; command sources are delivered through the runtime store instead (Section 8).

Within the copied roots, entries matching any of the following patterns MUST be excluded at any depth:

```text
.git  .github  .gitlab-ci.yml  .venv  __pycache__  *.pyc  node_modules
tests  test  __tests__  README*  CHANGELOG*  LICENSE*  Makefile
setup.py  pyproject.toml  requirements*.txt  .DS_Store  .gitignore
```

Directories listed in `runtime_roots` (Section 5.3) MUST also be excluded from context, even when they fall under a whitelisted root. Context installation MUST be atomic: implementations stage into a temporary directory and replace the previous installation only on success.

This whitelist is the mechanism behind the context and runtime separation: the model sees short, relevant instructions, while executable material lives in a managed runtime outside the agent context.

### 4.3 Localization

Localization is optional. A skill that ships no `locales/metadata.json` and no `.skill_triggers/` installs identically under any project locale.

When localization metadata is present, the following rules apply:

- `locales/metadata.json` MUST contain an object field `locales` mapping locale codes to objects. Per-locale objects MAY carry `description`, `display_name`, `short_description`, and `default_prompt`.
- `.skill_triggers/` MUST be a directory; it contains one `<locale>.md` catalog per locale. Trigger phrases are list items (`- phrase`) outside fenced code blocks.
- A locale is **consistent** when it appears both as a key in `locales` and as a `.skill_triggers/<locale>.md` file. At least one consistent locale MUST exist when localization metadata is present; otherwise installation fails.
- If the selected project locale is consistent, the installer renders it: the `description` from metadata replaces the `description` field in the installed `SKILL.md` frontmatter (preserving `name`), trigger phrases are written as a `triggers` list in the frontmatter, and `agents/openai.yaml`, when present, is rewritten from `display_name`, `short_description`, and `default_prompt`.
- If the selected locale is not consistent but another consistent locale exists, the installer MUST install the source `SKILL.md` unchanged and emit a warning naming the available catalogs. Locale warnings MUST be emitted even when the installation is otherwise up to date.

### 4.4 Relationship to the Common SKILL.md Convention

The package format is a constrained profile of the SKILL.md convention used across the agent ecosystem: a markdown instruction file with YAML frontmatter (`name`, `description`, optional `triggers`) plus supporting directories. Any CocoaSkills skill is readable by tools that understand plain SKILL.md packages. The profile adds three constraints: the context whitelist (Section 4.2), the optional machine manifest `csk-skill.json` (Section 5), and the localization contract (Section 4.3). It deliberately excludes arbitrary top-level content from the agent context.

---

## 5. The csk-skill.json Manifest

`csk-skill.json` at the package root declares the machine-facing contract of a skill: exported commands, runtime file layout, declared capabilities, and dependencies. Skills without commands or dependencies do not need one.

### 5.1 Schema Versions

The manifest MUST contain an integer field `schema_version`. Implementations targeting this specification MUST accept versions 1 through 5 and MUST reject any other value with an error that tells the user to upgrade the tool.

| Version | Adds |
|---------|------|
| 1 | `commands` (single-file scripts and system checks) |
| 2 | `runtime_roots`, `dependencies.commands`, strict field validation |
| 3 | `capabilities` (required from this version on) |
| 4 | `dependencies.skills` (skill-to-skill requirements) |
| 5 | `dependencies.mcp_servers` (MCP server requirements) |

Each version is additive over the previous one. For `schema_version` 2 and newer, implementations MUST reject unknown top-level fields; the allowed set is `schema_version`, `runtime_roots`, `commands`, `dependencies`, plus `capabilities` for version 3 and newer. For version 3 and newer, `capabilities` MUST be present. Gating MUST be enforced downward as well: `dependencies` requires version 2, `dependencies.skills` requires version 4, `dependencies.mcp_servers` requires version 5.

### 5.2 Identifiers

Skill names, command names, and MCP server names become filesystem path components (shim filenames, runtime directories). They MUST match:

```text
^[A-Za-z0-9][A-Za-z0-9._-]*$
```

This rules out path separators, leading dashes, and anything that could escape a designated directory.

### 5.3 runtime_roots

`runtime_roots` (schema 2+) lists the directories that skill commands need at execution time:

```json
"runtime_roots": ["scripts"]
```

Each entry MUST be a POSIX-style relative path (no backslashes, no `..`, no empty or `.` segments, no doubled slashes) that exists in the package and is a directory. Entries MUST be unique and pairwise disjoint: no root may contain another. Runtime roots are copied to the machine-level runtime store keyed by skill and commit (Section 8.6) and are excluded from the model context (Section 4.2).

### 5.4 commands

`commands` maps exported command names to command objects. Two types exist.

**Script commands** point at files inside the package:

```json
"commands": {
  "ytx": { "type": "script", "unix_path": "scripts/ytx", "win_path": "scripts/ytx.cmd" }
}
```

Paths MUST be relative paths inside the package. For schema 2 and newer: at least one of `unix_path` or `win_path` MUST be present, the referenced file MUST exist, no fields other than `type`, `unix_path`, `win_path` are allowed, and when `runtime_roots` is non-empty every command path MUST fall inside one of the roots.

**System commands** assert that an externally installed binary is available:

```json
"commands": {
  "wiki": { "type": "system", "command": "wiki", "hint": "Install the wiki CLI through project bootstrap." }
}
```

`command` MUST be a non-empty string; `hint` is optional. A system command is resolved against `PATH` at install time; a missing binary MUST fail the installation of that skill with the hint. Implementations MUST NOT install a skill into a partially working state.

A skill MUST only export commands it owns. Declaring another skill's command creates a shim collision with the real owner.

### 5.5 capabilities

`capabilities` (required from schema 3) declares the boundaries within which the skill is expected to operate. It is an audit and review surface, not a runtime sandbox.

```json
"capabilities": {
  "network": ["youtrack.example.com"],
  "filesystem": "repo",
  "exec": ["python3"],
  "secrets": ["youtrack-cli"],
  "env_read": ["HOME"],
  "prompt_scope": "Read and update tracker issues within the selected project."
}
```

Field rules:

- `network`: `"none"` (default) or a list of host globs. Entries MUST NOT contain whitespace, `/`, or `\`.
- `filesystem`: `"repo"` (default), `"home-config"`, or a list of paths. Relative paths MUST NOT contain `..`; entries MUST NOT start with `-` or contain NUL.
- `exec`: `"none"` (default) or a list of bare executable names (no paths, no spaces, no leading `-`).
- `secrets`: `"none"` (default) or a list of secret or keyring entry names.
- `env_read`: a list (default empty) of environment variable names (`[A-Za-z_][A-Za-z0-9_]*`).
- `prompt_scope`: optional non-empty sentence describing the intended purpose.

List values MUST be unique. Unknown capability fields MUST be rejected. The audit pipeline compares observed behavior against these declarations (Section 12).

### 5.6 dependencies.commands

Command-level dependencies name tools the skill invokes but does not export.

```json
"dependencies": {
  "commands": {
    "glab": { "type": "system", "command": "glab", "hint": "Install the GitLab CLI through project bootstrap." }
  }
}
```

`type: "system"` follows the same resolution rule as system commands: present on `PATH` or the skill fails to install with the hint.

The legacy form `type: "skill"` (fields `skill`, `command`, optional `hint`) declares that another installed skill provides the command. It remains accepted for compatibility, MUST NOT create a shim, and implementations SHOULD print a migration warning pointing at `dependencies.skills`. New skills MUST use `dependencies.skills` instead.

### 5.7 dependencies.skills

Schema 4 introduces self-contained skill-to-skill requirements. Each entry carries everything needed to fetch the provider:

```json
"dependencies": {
  "skills": {
    "skill-wiki": {
      "git": "git@git.example.com:skills/skill-wiki.git",
      "ref": { "kind": "tag", "value": "v1.4.2" },
      "mode": "runtime",
      "commands": ["wk"]
    }
  }
}
```

Validation rules, all MUST:

- `git` is a non-empty source URL.
- `ref` is an object `{ "kind": "tag" | "revision", "value": <non-empty> }`. `kind: "branch"` is rejected with a dedicated error. A `version` field is rejected: version ranges are not part of the protocol. Values containing range markers (`^`, `~`, `>`, `<`, `*`, or whitespace) are rejected.
- `mode` is one of `full` (default), `runtime`, `context`. `full` activates the provider's context and commands for the consumer; `runtime` activates only its commands; `context` activates only its context.
- `commands` is allowed only with `mode: "runtime"` and, when present, is a non-empty list of command identifiers narrowing which provider commands are activated. Duplicates are dropped preserving order.

Requirement resolution across the project is specified in Section 8 (closure resolution).

### 5.8 dependencies.mcp_servers

Schema 5 introduces requirements on MCP servers configured in the consuming agent environments:

```json
"dependencies": {
  "mcp_servers": {
    "google-sheets": {
      "hint": "Connect the Google Sheets MCP server in your agent environment configuration.",
      "transport": "http",
      "required_in": "any"
    }
  }
}
```

- `hint` is REQUIRED and non-empty; it is shown when the requirement is not met.
- `transport` is optional documentation: `stdio` or `http`.
- `required_in` selects the check semantics: `any` (default) requires the server name to be configured in at least one target agent environment; `all` requires it in every target agent environment.

The server name MUST match the name under which the server is registered in agent configuration files. Verification behavior and the per-agent configuration surfaces are specified in Section 11. CocoaSkills never launches or installs MCP servers; it verifies their presence in configuration.

### 5.9 No Install Hooks

The manifest is declarative. Fields such as `install`, `post_install`, `check`, or any other executable hook are not part of any schema version and MUST be rejected through unknown-field validation (schema 2+). An implementation MUST NOT execute code from a skill package during installation. This is a load-bearing security property: installation reads and copies files, verifies declarations, and nothing else.

### 5.10 Legacy Runtime Manifest

When no `csk-skill.json` exists but the package contains `agents/runtime.json`, implementations MUST read it as a legacy command map: an object field `commands` mapping command identifiers to relative file paths. A path ending in `.cmd` doubles as the Windows entry point. New skills MUST NOT use this format. When neither file exists, the skill is a pure context skill: it installs context and exports nothing.

### 5.11 Complete Example

A schema 5 skill that exports one command, depends on a provider skill and an MCP server:

```json
{
  "schema_version": 5,
  "runtime_roots": ["scripts"],
  "capabilities": {
    "network": ["api.example.com"],
    "filesystem": "repo",
    "exec": ["python3"],
    "secrets": "none",
    "env_read": ["HOME"],
    "prompt_scope": "Prepare the team's weekly report from tracker and spreadsheet data."
  },
  "commands": {
    "report": { "type": "script", "unix_path": "scripts/report", "win_path": "scripts/report.cmd" }
  },
  "dependencies": {
    "commands": {
      "python3": { "type": "system", "command": "python3", "hint": "Install Python through project bootstrap." }
    },
    "skills": {
      "skill-tracker": {
        "git": "git@git.example.com:skills/skill-tracker.git",
        "ref": { "kind": "tag", "value": "v2.1.0" },
        "mode": "runtime",
        "commands": ["trk"]
      }
    },
    "mcp_servers": {
      "google-sheets": { "hint": "Connect the Google Sheets MCP server in your agent environment." }
    }
  }
}
```

---

## 6. Skillfile: Project Manifest

`Skillfile.json` at the project root declares which skills the project uses. It is committed to version control; generated directories are not.

### 6.1 Format (schema 1)

```json
{
  "schema_version": 1,
  "project": { "alias": "my-project" },
  "agents": ["claude_code", "codex_cli", "cursor"],
  "locale": "ru",
  "skills": [
    {
      "name": "skill-youtrack",
      "git": "git@git.example.com:skills/skill-youtrack.git",
      "tag": "v1.3.0"
    }
  ]
}
```

Rules, all MUST unless stated otherwise:

- `schema_version` is the integer 1. Unknown versions are rejected with an upgrade error.
- `project.alias` is an optional non-empty string naming the project for hybrid targeting (Section 9.3).
- `agents` is a list of agent identifiers (Section 10). It selects which adapter directories are produced. Unknown agents are ignored with a warning.
- `locale` is an optional locale code; it overrides the machine `preferred_locale` for this project.
- `skills` is a list of declaration objects. Each declares:
  - `name`: a skill identifier (Section 5.2), unique within the file.
  - `source`: optional path under the machine `skills_root` where the source repository lives; defaults to `name`. Each path segment MUST be a valid identifier, which excludes `..`, absolute paths, and option-like segments.
  - `git`: optional git URL used to clone the source repository when it is absent from `skills_root`.
  - Exactly one of `tag`, `branch`, or `revision` with a non-empty string value. Branch declarations are allowed here, at the project level; skill-to-skill requirements do not accept them (Section 5.7).

### 6.2 Development Substitutions: Skillfile.dev.json

`Skillfile.dev.json` sits next to `Skillfile.json`, is never committed, and belongs to the managed `.gitignore` block. It substitutes providers locally during development instead of hand-editing installed copies.

```json
{
  "substitutions": {
    "skill-wiki": { "path": "../skill-wiki" },
    "skill-tracker": { "git": "git@git.example.com:forks/skill-tracker.git",
                       "ref": { "kind": "branch", "value": "fix-pagination" } }
  }
}
```

Rules:

- The only top-level field is `substitutions`; unknown fields are rejected.
- Each entry declares exactly one of `path` (a local checkout, resolved against the project root when relative; it MUST be a git repository, and its `HEAD` is used) or `git` plus a `ref` object whose `kind` may be `tag`, `revision`, or `branch`. Branches are allowed here by design: substitutions are a development device.
- A substitution replaces every requirement of that name across the whole closure, and unification checks are skipped for the substituted name.
- Installations with active substitutions MUST print one `SUBSTITUTION <name> -> <target>` line per entry, and the install marker records the substitution. When strict audit mode is enabled, an install with active substitutions MUST fail.
- Git substitutions clone outside `skills_root` (the reference implementation uses `~/.cocoaskills/dev/<name>`) so a substitution never shadows the declared source repository.

### 6.3 Managed .gitignore Block

Generated paths MUST be ignored by git before installation proceeds. The required entries are `.agents/` plus the adapter directory of every selected agent (Section 10.1). The installer verifies this with `git check-ignore` probes; a project that does not ignore the paths is skipped with a message. `csk init` writes the block, appending only missing entries under a `# CocoaSkill` comment; `csk install --fix-gitignore` repairs it. When `Skillfile.dev.json` is present it MUST be ignored as well.

---

## 7. Machine and System Configuration

### 7.1 User Configuration

The machine configuration lives at `~/.cocoaskills/config.json` (overridable through the `CSK_CONFIG` environment variable). Schema version 1. Fields:

| Field | Type | Meaning |
|-------|------|---------|
| `schema_version` | int, required | 1 |
| `skills_root` | string, required | Directory holding source skill repositories |
| `default_agents` | list of strings | Agents used when a project declares none; default `["codex_cli"]` |
| `preferred_locale` | string, optional | Locale used when the Skillfile declares none |
| `adapter_mode` | `auto` \| `symlink` \| `copy` | How adapter entries materialize; default `auto` (symlink with copy fallback) |
| `worktree_alias_pattern` | regex string | Pattern extracting checkout aliases for worktrees; default `[A-Z]+-[0-9]+` |
| `projects` | object, required | Registered projects: alias to `{path, agents, project_alias, checkout_alias}` |
| `allowed_sources` | list of strings | Canonical `host/path` prefixes the resolver may fetch from (Section 8.2) |
| `audit` | object | Source audit and registry policy configuration (Sections 12 and 13) |
| `audit_registries` | list | Trusted audit registries: `{name, url, public_keys, enabled}` (Section 13) |
| `disable_builtin_registries` | bool | Drop built-in default registries; default false |

Registry entries require a non-empty `name`, an `http(s)` `url` unique across the list, and string `public_keys`.

### 7.2 Enforced System Configuration

An organization distributes an enforced configuration file read before the user config: `/etc/cocoaskills/config.json` on Unix, `%ProgramData%\cocoaskills\config.json` on Windows (overridable through `CSK_SYSTEM_CONFIG`).

Merge semantics, all MUST:

- Keys listed in the system config field `locked` take their value from the system config. A conflicting user value is ignored with a warning naming the system config path.
- A key that is locked but not set in the system config is a configuration error.
- System keys not listed in `locked` act as defaults; the user config may override them.
- Lockable keys are `audit_registries`, `disable_builtin_registries`, `allowed_sources`, and `audit`.

This is the mechanism for centrally distributing registry trust and source policy through device management.

---

## 8. Resolution and Installation

Installation is driven by `csk install`. For each selected project the phases below run in order. Any failure marks the project failed; nothing about a failing skill is left half-installed.

### 8.1 Phase Order

1. Load `Skillfile.json`; absent means the project is skipped.
2. Determine effective agents: the Skillfile `agents`, else the project entry in the machine config, else `default_agents`.
3. Enforce the managed `.gitignore` block (Section 6.3).
4. Load dev substitutions; fail under strict audit; report each substitution.
5. Load hybrid declarations and extend the manifest (Section 9.3).
6. Determine the effective locale: Skillfile `locale`, else `preferred_locale`.
7. Build the dependency closure (Section 8.3), which fetches sources, applies the source allowlist, takes snapshots, and parses manifests.
8. Validate every skill (`csk skill check` rules); collect warnings, fail on errors.
9. Detect active command collisions across the closure (Section 8.4).
10. Check declared dependencies: system commands on `PATH`, legacy skill-command dependencies satisfied.
11. Verify MCP server requirements (Section 11); emit static availability warnings.
12. Emit migration warnings for legacy `dependencies.commands` entries of type `skill`.
13. Run the source audit gate (Section 12); a blocked result fails the install.
14. Resolve skills against trusted audit registries (Section 13); a verified revocation fails, strict registry policy fails unknown artifacts, attestations are collected for markers.
15. Detect moved tags: a tag whose recorded commit in the previous install marker differs from the newly resolved commit produces a warning, or an error under `--strict-tags`.
16. In dry-run mode, print the plan and stop before any file changes.
17. Record the project as a runtime consumer (Section 8.7).
18. For every closure node in provider-before-consumer order: install runtime commands (Section 8.6) for the active command set, then install context plus marker, or a marker only for nodes without active context (Section 8.5).
19. Remove installed skills that are no longer expected, remove stale command shims, write the environment files `.agents/env.sh` and `.agents/env.ps1`, and refresh agent adapters (Section 10).
20. After all projects, garbage-collect unreferenced runtime store entries.

### 8.2 Source Fetching and the Allowlist

Source repositories live under `skills_root/<source>`. A missing repository is cloned from the declared `git` URL. Cloning MUST restrict git transports to `file`, `git`, `http`, `https`, and `ssh` (the reference implementation sets `GIT_ALLOW_PROTOCOL`), MUST refuse empty or dash-prefixed URLs, and MUST pass the URL positionally after `--`. Submodules are unsupported; a snapshot containing `.gitmodules` fails. Symbolic and hard links inside git archives are rejected, and archive extraction MUST prevent path escapes.

Every artifact carries a canonical source identity: `host/path` with the transport removed, the host lowercased, a trailing `.git` stripped, and the path kept case-sensitive. SSH and HTTPS URLs of one repository yield one identity. Local filesystem sources have no identity.

`allowed_sources` gates network fetches: before cloning a declared git source, its identity MUST match one of the configured prefixes. Matching is segment-aware: `host/skills` matches `host/skills/x` and never `host/skills-evil`. An empty allowlist allows everything; local sources always pass.

Refs resolve as follows: `tag` resolves `refs/tags/<value>` to a commit; `revision` resolves `<value>^{commit}`; `branch` prefers `refs/remotes/origin/<value>` and falls back to a local head. Snapshots are produced with `git archive` at the resolved commit and cached per source and commit under the csk home (`cache/<source>/<commit>/snapshot`).

### 8.3 Closure Resolution

Direct Skillfile declarations enter the closure as full-mode requirements rooted in the synthetic consumer `<project>`. Processing a node adds its `dependencies.skills` entries to the queue with the node as consumer. Rules, all MUST:

- Within one closure, a skill name resolves to exactly one commit and one canonical source identity.
- When two requirements name the same skill from different repositories (different identities), resolution fails with a source conflict naming both requirement chains.
- When two requirements pin refs that resolve to different commits, resolution fails with a version conflict naming both chains and both commits. Different refs resolving to the same commit unify.
- A requirement whose `commands` narrowing names a command the provider does not export as a script command is an error.
- Dependency cycles are an error naming the cycle members.
- The result is ordered providers before consumers, deterministically.

Activation is edge-based. A node's context is active when any incoming edge has mode `full` or `context`. Its active command set is: all exported script commands when any edge is `full`; otherwise the union over `runtime` edges of their command narrowing (an unnarrowed runtime edge activates all exported commands).

### 8.4 Command Collisions

Across the closure, one active command name MUST have exactly one owner. Collision detection runs over active commands only: two skills may export the same name as long as at most one activation makes it live.

### 8.5 Install Markers

Every installed node carries a marker file `.csk-install.json` in its installed directory (context installs) or in a marker-only directory (runtime-only nodes; adapters never mirror those). Marker fields:

```json
{
  "schema_version": 1,
  "name": "...", "source": "...",
  "ref_kind": "tag", "ref": "v1.2.0", "commit": "<full sha>",
  "content_sha256": "sha256:<hex>",
  "locale": "ru", "agents": ["claude_code"],
  "commands": ["exported script commands"],
  "dependencies": ["declared dependency names"],
  "skill_schema_version": 5,
  "runtime_roots": ["scripts"],
  "installed_at": "<UTC ISO-8601, Z suffix>",
  "files": ["installed context files"],
  "git": "<declared url, when present>",
  "requirements": ["dependencies.skills names, when present"],
  "mcp_servers": {"server": ["agents where found"]},
  "attestation": {"registry": "...", "status": "audited", "key_id": "..."},
  "activation": {"context": true, "commands": ["active commands"]},
  "requirers": ["consumers"],
  "substituted": "<description, when substituted>"
}
```

An installation is up to date only when ref kind, ref, commit, locale, agents, activation, substitution, MCP findings, and attestation all match the marker, and the content hash recomputed from the installed directory equals `content_sha256`. The recomputation makes local tampering visible on the next install. Directory replacement MUST be atomic (stage, back up, rename, roll back on failure).

The content hash is computed over the installed files exclusive of the marker itself: files sorted by POSIX-style relative path, each contributing `relpath NUL content`, records joined with `NUL`, hashed with SHA-256 and prefixed `sha256:`.

### 8.6 Runtime Store and Command Shims

Command runtimes live once per machine in `~/.cocoaskills/runtime/<skill>/<commit>/`. When a skill declares `runtime_roots`, those directories are copied there (atomically, keyed by commit; an existing entry is reused). Without runtime roots, a single command file is copied to `runtime/<skill>/<commit>/bin/<command>`.

For every active command the installer writes a shim into the project `.agents/bin/`: on Unix a relative symlink to the runtime file (made executable), on Windows a `<command>.cmd` wrapper invoking the runtime path. Command paths MUST NOT escape the snapshot. Stale shims for commands no longer active are removed.

`.agents/env.sh` and `.agents/env.ps1` are generated helpers that prepend `.agents/bin` to `PATH` and export `CSK_PROJECT_ROOT`; shell integration is specified in Section 14.

### 8.7 Consumers and Garbage Collection

Every successful project install records the project path in a machine-level consumer registry (`~/.cocoaskills/consumers.json`). Runtime garbage collection scans registered projects and consumers for markers referencing `runtime/<skill>/<commit>` entries and deletes unreferenced entries; consumer entries whose checkout disappeared or holds no markers are pruned.

---

## 9. Install Scopes

### 9.1 Project Scope

The default. Skills declared in the project Skillfile install into the project checkout (`.agents/skills`, `.agents/bin`, adapter directories). Different projects hold different versions independently.

### 9.2 Global Scope

Machine-wide skills live under `~/.cocoaskills/global/`: a global `Skillfile.json` of the same schema, installed context in `global/skills/`, command shims in `global/bin/`, and generated `env.sh`/`env.ps1`. Managed through `csk global init|add|remove|install|update|status|upgrade`. Global adapters mirror into the home-level agent directories (`~/.claude/skills`, `~/.codex/skills`, `~/.cursor/rules`, `~/.gemini/skills`), and for native-discovery agents into `~/.agents/skills` (Section 10.2).

### 9.3 Hybrid Scope

Hybrid skills are stored once per machine and activated only for targeted projects, leaving nothing in the target repository. The declaration lives in `~/.cocoaskills/hybrid/Skillfile.json`: standard schema 1 plus a required per-skill `targets` list. A target matches a project by declared alias (config alias, config `project_alias`, or Skillfile `project.alias`), by exact resolved path, or by path glob.

During a project install, applicable hybrid declarations join the effective manifest. Shadowing order is project, then hybrid, then global: a project declaration of the same name shadows the hybrid entry (reported as a message). Hybrid nodes and the parts of their closures unreachable from project declarations materialize in the machine-level hybrid store (`~/.cocoaskills/hybrid/skills/`), rendered once per machine with the machine locale; project adapters then mirror both the project store and the hybrid store. Closure resolution, audit, and registry gates apply to hybrid skills unchanged.

---

## 10. Multi-Agent Delivery

### 10.1 Adapters

The canonical installed context lives in `.agents/skills/`. Adapters mirror it into the directories each agent reads:

| Agent id | Project directory | Home directory (global scope) |
|----------|-------------------|-------------------------------|
| `claude_code` | `.claude/skills` | `~/.claude/skills` |
| `codex_cli` | `.codex/skills` | `~/.codex/skills` |
| `cursor` | `.cursor/rules` | `~/.cursor/rules` |
| `gemini` | `.gemini/skills` | `~/.gemini/skills` |

Adapter entries are symlinks, or full copies where symlinks are unavailable (`adapter_mode`: `auto`, `symlink`, `copy`). Each adapter directory carries a ledger `.csk-managed.json` (schema 1, sorted `entries`) recording which entries the tool manages. Managed entries that fall out of the expected set are removed; an existing unmanaged entry with the same name MUST fail the refresh rather than be overwritten. Unknown agent identifiers are ignored with a warning listing known agents.

### 10.2 Native-Discovery Agents

`opencode` and `windsurf` discover the canonical `.agents/skills/` directory natively and receive no project-level mirror. For global installs, their entries mirror into `~/.agents/skills` so the skills are visible outside any project checkout.

---

## 11. MCP Server Requirements

Skills declare MCP server requirements in `dependencies.mcp_servers` (Section 5.8). Verification is read-only: implementations MUST NOT launch or install MCP servers.

### 11.1 Configuration Surfaces

A server counts as configured for an agent when its name appears in one of that agent's configuration files:

| Agent | Project-level | User-level |
|-------|---------------|------------|
| `claude_code` | `.mcp.json` | `~/.claude.json` |
| `cursor` | `.cursor/mcp.json` | `~/.cursor/mcp.json` |
| `codex_cli` | `.codex/config.toml` | `~/.codex/config.toml` |
| `gemini` | `.gemini/settings.json` | `~/.gemini/settings.json` |
| `opencode` | `opencode.json`, `opencode.jsonc` | `~/.config/opencode/opencode.json(c)` |
| `windsurf` | none | `~/.codeium/windsurf/mcp_config.json` |

JSON files declare servers under `mcpServers`; Codex TOML under `mcp_servers`; OpenCode under `mcp`, where an entry with `"enabled": false` does not count. For Claude Code, a server listed in `disabledMcpjsonServers` of `.claude/settings.json` or `.claude/settings.local.json` does not count: the agent will not activate a rejected server. Missing or malformed configuration files count as configuring no servers.

### 11.2 Verification Semantics

For each requirement, each target agent resolves to configured or not. Agents without a known configuration surface resolve to not configured. With `required_in: "any"` the requirement fails when no target agent has the server; with `"all"` it fails naming every agent that lacks it. Failure messages MUST include the declared `hint`. The install marker records, per server, the agents where it was found.

### 11.3 Static Availability Warnings

Two conditions produce warnings without failing the install:

- Every entry for a configured server is positively a stdio server whose command does not resolve on `PATH` (a string `command`, or an argv list for OpenCode). Entries that may be remote produce no warning.
- A server is declared only in project-level configuration for an agent: agents gate project-level config behind checkout trust, so the server may sit pending in a fresh clone.

---

## 12. Source Audit

The source audit is a machine-local gate that inspects skill snapshots before installation. It is off by default (`audit.enabled: false`) and configured under the `audit` key (Section 7.1).

### 12.1 Pipeline

For each skill in the closure:

1. Compute the snapshot content hash (Section 8.5 algorithm, over the raw snapshot).
2. Look up a cached verdict keyed by content hash, backend name, model, prompt version, and ruleset version. A hit skips analysis; the decision is recomputed from the cached findings under the current policy.
3. Run the static canary: a self-test that plants known-bad fixtures and checks that detectors fire. A failing canary blocks the audit entirely.
4. Run static detectors over the snapshot, comparing observed behavior against the declared capabilities (Section 5.5). Findings carry an id, a surface (`code`, `prompt`, `manifest`), a category, a severity (`info`, `low`, `medium`, `high`, `critical`), evidence, a detector name, a confidence, a verifiability flag, an optional file location, and an optional capability violation (capability, declared, observed).
5. Optionally run a backend for deeper analysis: `null` (no-op, default), `command` (an operator-supplied local command), or `codex` (an LLM backend). Backends have their own canary. A backend request larger than `audit.max_request_bytes` is skipped and replaced by a high-severity `audit.request.too-large` finding.
6. Cloud egress control: a backend marked cloud MAY only receive skills whose source classifies as `public` under `audit.source_policy` (pattern rules over source and git URL; default class `internal`). Otherwise the audit fails with an egress error. File contents sent to a cloud backend are redacted (secret scrubbing) and the redaction is recorded as a finding.
7. Store the verdict in the machine trust store and decide.

### 12.2 Decisions and Policy

The decision for a skill is one of `allow`, `warn`, `block`, `require_pin`:

- A local revocation match blocks unconditionally. Local revocations (`audit.revocations`) are content hashes (`sha256:<hex>` or bare hex) or `source:<glob>` patterns matched against the declared source, the git URL, and its normalized form.
- Under `audit.mode: "strict"`, a skill with manifest schema older than 3 (no capability declaration) and no operator pin resolves to `require_pin`. The operator pins with `csk audit --allow <content-hash> --reason <text>`; the pin is recorded with the user name.
- Otherwise, with no findings the decision is `allow`. With findings: in advisory mode, or with `fail_on: "off"`, the decision is `warn`; in strict mode the decision is `block` when any verifiable finding meets the `fail_on` severity threshold, else `warn`.

Gate behavior: `block` and `require_pin` fail the install; `warn` produces messages. A backend failure blocks in strict mode and degrades to a warning in advisory mode. Canary and egress failures always block.

---

## 13. Audit Registry Protocol

The audit registry is a shared, cryptographically verifiable layer over the same artifact coordinates the installer already computes: canonical source identity, commit, and content hash. Machines pin trusted registries; registries serve signed audit records. The client behavior is advisory by default: a verified revocation always denies, a strict policy additionally requires a positive audit.

### 13.1 Records

An audit record is a JSON object with required non-empty string fields `name`, `source_identity`, `commit`, `content_sha256`, `status`, an optional object `audit` (free-form audit metadata: auditor, report, scope), optional `endorsements`, and a signature envelope `sig`:

```json
{
  "name": "skill-youtrack",
  "source_identity": "git.example.com/skills/skill-youtrack",
  "commit": "<full sha>",
  "content_sha256": "sha256:<hex>",
  "status": "audited",
  "audit": { "auditor": "security-team", "report": "https://..." },
  "endorsements": [ { "endorser": "auditor-id", "sig": { "...": "..." } } ],
  "sig": { "key_id": "<sha256(pubkey)[:16]>", "algorithm": "ed25519", "signature": "<base64>" }
}
```

`status` is one of `audited`, `revoked`, `deprecated`, `pending`. Records with other statuses MUST be rejected as malformed.

### 13.2 Canonical Bytes and Signatures

The signed form of any registry object (record or snapshot) is the compact sorted JSON of every field except `sig`: keys sorted, separators `,` and `:`, non-ASCII preserved (no escaping), encoded as UTF-8. Signatures are Ed25519 over these bytes, transported base64 in `sig.signature`. `sig.key_id` is the first 16 hex characters of SHA-256 over the raw 32-byte public key.

Pinned public keys are strings of the form `ed25519:<base64>` (the prefix MAY be omitted) decoding to exactly 32 bytes. A record verifies when its signature checks against any pinned key of its registry. Implementations need no third-party cryptography for the client side: Ed25519 verification is implementable from the standard library (the reference implementation vendors a pure-Python verifier).

### 13.3 Client Resolution: Deny-Wins Federation

For each installed artifact the client queries every trusted registry with `source_identity`, `commit`, and `content_sha256`. A returned record matches the artifact when its `content_sha256` equals the computed one, or when its `source_identity` and `commit` both match. Then:

- A registry with no pinned keys contributes nothing; its records are not trusted (warning).
- An unreachable registry contributes nothing (warning).
- Records that fail parsing or signature verification are ignored (warning).
- A verified `revoked` record from any registry immediately resolves the artifact as revoked: deny wins across the federation.
- Otherwise a verified `audited` record resolves as audited (the first one becomes the attestation); failing that, a verified `deprecated` record resolves as deprecated; failing that, the artifact is unknown.

Install semantics (Section 8.1, phase 14): revoked fails the install naming the registry; deprecated produces a message; unknown fails only under `audit.registry_policy: "strict"`. The authorizing attestation (registry name, status, key id) is recorded in the install marker. `csk status --attest` re-resolves installed artifacts from their markers on demand, so a revocation issued after install surfaces without reinstalling; markers without a canonical source identity report as unattestable.

### 13.4 Snapshot Verification

Before resolving records, the client fetches each registry's signed snapshot: a commitment to the log head with fields `schema_version`, `merkle_root`, `log_size`, `head`, `version`, `created_at`, signed like a record. A registry is excluded from the resolution (treated as tampered) when:

- the snapshot signature does not verify against its pinned keys, or
- `version` is not an integer or moved backward relative to the highest version previously accepted from that registry (rollback detection; the highest accepted version persists across runs), or
- `created_at` is missing, unparsable, or older than the staleness bound (default 7 days), defending against a frozen view that hides newer revocations.

An unreachable snapshot produces a warning but does not exclude the registry: per-record signatures and deny-wins still protect the install. When every trusted registry is excluded as tampered, the install MUST fail.

### 13.5 Caching and Offline Grace

Record lookups cache on disk keyed by the full query URL. A cache entry younger than the TTL (default 1 hour) is served without network access. On refresh failure a stale entry remains usable within the offline grace window (default 7 days); past it, the registry counts as unreachable.

### 13.6 Registry Service HTTP API

A registry service implements:

| Endpoint | Method | Behavior |
|----------|--------|----------|
| `/health` | GET | Liveness: `{"status": "ok"}` |
| `/v1/meta` | GET | Registry name, version, pinned public keys, supported record schema versions, policy statement |
| `/v1/records?source_identity&commit&content_sha256` | GET | `{"records": [...]}`: the latest record per artifact matching identity plus commit, or content hash |
| `/v1/snapshot` | GET | The signed snapshot of the current log head; `version` advances with every append |
| `/v1/log?since=N` | GET | Transparency log entries after sequence N: `{seq, entry_hash, prev_hash, record}` |
| `/v1/records` | POST | Auditor submission (below) |

### 13.7 Submission, Tokens, and Countersigning

Submission requires a bearer token bound to a registered auditor. The service stores only the SHA-256 of each token and compares in constant time; the auditor registration carries the auditor id and pinned public key. The submitted record MUST verify against the submitting auditor's public key; a valid token alone cannot forge a record.

The service then countersigns: the auditor signature moves into `endorsements` (as `{endorser, sig}`), and the service signs the resulting body with the registry key. Clients therefore verify served records against the registry key alone, while auditor endorsements remain as provenance.

### 13.8 Transparency Log

Every accepted record appends to a hash-chained log: `entry_hash = SHA-256(prev_entry_hash_ascii || canonical_bytes(record))`, with a genesis previous hash of 64 zeros. The log is append-only; the current record for an artifact is the latest entry naming it, so a revocation supersedes an earlier audit of the same artifact. The snapshot's `merkle_root` is an ordered Merkle tree over all entry hashes (odd nodes pair with themselves). Chain verification recomputes every entry hash from the genesis.

### 13.9 Air-Gapped Federation: Bundles

A registry exports a signed bundle: `{schema_version: 1, records, snapshot, public_key}`. An offline registry imports it by verifying the snapshot and every record against the upstream pinned key, then countersigning each record with its own key (adding an `upstream-import` endorsement) and appending to its own log. Clients of the offline registry keep verifying against their own registry's pinned key.

### 13.10 Publishing from the Client

`csk audit --publish <record.json> --registry <url> --token <token>` submits a signed record file to `POST /v1/records`. The token MAY come from the `CSK_REGISTRY_TOKEN` environment variable. The client validates that the file is JSON and reports the registry's acceptance (`{seq, entry_hash}`) or its rejection reason.

---

## 14. Shell Integration

### 14.1 Shell Hook

```bash
# ~/.zshrc or ~/.bashrc:
eval "$(csk shell-init zsh)"    # or bash
```

```powershell
csk shell-init powershell   # prints the hook; add it to the PowerShell profile
```

Hook behavior:

- On every prompt (and on `chpwd` under zsh), the hook searches upward from the current directory for `.agents/env.sh` and sources the first one found, saving the previous `PATH`.
- Leaving the project restores the saved `PATH` and clears the activation state (`CSK_ACTIVE_ENV`, `CSK_OLD_PATH`).
- Unless `--no-global` is passed to `shell-init`, the hook also sources the global environment file (`<csk home>/global/env.sh`) once, honoring a `CSK_CONFIG` override.

### 14.2 Environment Files

`.agents/env.sh` and `.agents/env.ps1` are generated during installation. They locate themselves (bash `BASH_SOURCE`, zsh prompt expansion, `$0` fallback), export `CSK_PROJECT_ROOT`, and prepend `.agents/bin` to `PATH`. The global counterparts export `CSK_GLOBAL_ROOT` and prepend `global/bin`.

Effective command precedence:

```text
project .agents/bin  >  global ~/.cocoaskills/global/bin  >  system PATH
```

For CI and scripts, sourcing `.agents/env.sh` directly is equivalent to hook activation.

---

## 15. CLI Reference

This section is informative: it documents the reference implementation surface an interoperable tool SHOULD mirror in behavior, not necessarily in flags.

| Command | Behavior |
|---------|----------|
| `csk bootstrap` | Create the machine config interactively or from flags. |
| `csk init [path]` | Create `Skillfile.json` and the managed `.gitignore` block. |
| `csk add <name> --tag\|--branch\|--revision <ref> [--git <url>] [--source <dir>]` | Add or replace a declaration, then install. |
| `csk remove <name>` | Remove a declaration. |
| `csk install [target] [--all] [--dry-run] [--verbose] [--strict-tags] [--audit [advisory\|strict]]` | Apply the manifest (Section 8.1). |
| `csk update` | Fetch all source repositories under `skills_root`. |
| `csk upgrade [target]` | `update`, then `install`. |
| `csk status [target] [--all] [--check] [--json] [--attest]` | Manifest vs installed state; `--attest` re-checks installed artifacts against trusted registries; `--check` makes drift a non-zero exit. |
| `csk list` | Configured projects and declared skills. |
| `csk project add\|resolve` | Manage registered projects; resolve which project a path belongs to. |
| `csk config show` | Print the effective configuration. |
| `csk skill check <dir> [--locale <code>] [--json]` | Validate one skill package: strict format errors and advisory warnings. |
| `csk global init\|add\|remove\|list\|status\|install\|update\|upgrade` | Global scope management (Section 9.2). |
| `csk hybrid add\|remove\|list\|status` | Hybrid scope management (Section 9.3). |
| `csk audit [target] [--all] [--global] [--json]` | Run the audit standalone. |
| `csk audit --allow <content-hash> --reason <text>` | Pin trust for an artifact (Section 12.2). |
| `csk audit --publish <record.json> --registry <url> [--token <token>]` | Submit a signed record to a registry (Section 13.10). |
| `csk gc` | Remove unreferenced runtime entries, snapshot cache entries, and dead consumer entries. |
| `csk shell-init <zsh\|bash\|powershell> [--no-global]` | Print the shell hook. |

Exit codes distinguish success, partial failure, and blocked results (audit block, registry revocation, failed checks).

---

## 16. CI/CD Integration

CI uses the same commands as developers. A typical pipeline:

```yaml
steps:
  - uses: actions/checkout@v4
  - name: Install csk
    run: pipx install cocoaskills
  - name: Install skills
    run: csk install .
  - name: Check state
    run: csk status . --check
```

Reproducibility in CI comes from exact references in the committed `Skillfile.json` and marker verification, with `--strict-tags` available to fail on a tag that moved since the last recorded install. Registry gates (Section 13) apply in CI exactly as on developer machines; an organization pins registries and policy through the enforced system config (Section 7.2).

---

## 17. Conformance and Compatibility

### 17.1 Conformance for Independent Implementations

An implementation conforms to this specification when:

1. It consumes the skill package format of Section 4 (including the context whitelist and localization) and the `csk-skill.json` schemas 1 through 5 of Section 5 with all validation rules, and rejects what the reference rejects (unknown fields, ranges, branch requirements, install hooks).
2. It reads and writes `Skillfile.json` schema 1 and honors `Skillfile.dev.json` semantics (Section 6).
3. It resolves closures with the unification, conflict, cycle, ordering, and activation semantics of Section 8.3, gated by the source allowlist over canonical identities (Section 8.2).
4. It produces the installation layout of Sections 8.5, 8.6, and 10: whitelisted context, install markers with the exact content hash algorithm, a commit-keyed runtime store, shims, managed adapters. Markers written by one conforming implementation MUST be readable by another; up-to-date detection and tamper detection then work across tools.
5. It never executes skill-provided code at install time.
6. It verifies MCP requirements read-only per Section 11.
7. It implements the audit registry client of Section 13: canonical bytes, Ed25519 verification against pinned keys, artifact matching, deny-wins federation, snapshot verification with persisted monotonic versions, cache TTL and offline grace, and the install semantics of revoked, deprecated, and unknown results, including the enforced system configuration (Section 7.2).
8. Its registry service, when it provides one, implements the API, countersigning, transparency log, and bundle semantics of Sections 13.6 through 13.9.

The source audit (Section 12) is a machine-local policy layer; implementations MAY differ in detectors and backends, but MUST honor the decision semantics of Section 12.2 when audit is enabled, and MUST treat canary failure as a blocking condition.

### 17.2 SKILL.md Compatibility

The package format is a constrained profile of the SKILL.md convention (Section 4.4). CocoaSkills does not transform skill content beyond localization rendering (Section 4.3); any tool that reads plain SKILL.md packages can read installed CocoaSkills context.

### 17.3 Coexisting Tools

Skills remain consumable from any git host by URL. Adapter directories carry a managed-entries ledger so CocoaSkills never deletes or overwrites entries it does not manage (Section 10.1); manually placed skills coexist with managed ones.

---

## 18. Reference Implementation Notes

This section is informative.

- The reference implementation is Python 3.11+, distributed as `cocoaskills` on PyPI (`pipx install cocoaskills`), through a Homebrew tap, and as a source repository. The installed runtime keeps zero third-party dependencies; Ed25519 verification is vendored in pure Python. The only system prerequisite is `git`.
- The reference registry service (`csk-registry`) is a separate Python package (FastAPI, SQLite WAL) with a CLI: `genkey`, `issue-token`, `sign-record`, `export-snapshot`, `export-bundle`, `import-bundle`, `verify-chain`, `serve`. Server-side signing uses the `cryptography` package; that dependency never enters the client.
- Windows is a first-class target: `win_path` command entries, `.cmd` shims, PowerShell hooks, and `%ProgramData%` system config.

---

## Appendix A: Future Work (Non-Normative)

Ideas from the original 0.1.0 draft that are not part of the implemented protocol. They may return in future revisions; nothing in this appendix is normative.

- **Lockfile (`Skillfile.lock`) and frozen installs.** The implemented protocol reaches reproducibility through exact references, closure unification, and markers; a generated lockfile with `--frozen` semantics remains attractive for branch declarations and audit metadata pinning.
- **Version ranges and constraint resolution.** Requirements accept exact tags or revisions only. Ranges (`^`, `~`, comparison operators) would need a resolver and a lockfile first.
- **SSH certificate signing, CA hierarchies, trust providers, revocation lists.** The original design placed a per-publisher PKI (SSH certificates, root and intermediate CAs, DNS and GitHub identity verification, revocation list discovery) on skill artifacts. The implemented protocol covers revocation and attestation through registry-side Ed25519 signing (Section 13); publisher-side artifact signing remains future work.
- **Skillspec.yml author manifest.** Superseded by `csk-skill.json`. A richer author manifest (descriptions, format translation hints, build targets) could layer on top without breaking the current schemas.
- **Build phase for executables.** The implemented protocol copies runtime files as-is and never builds. Audited build recipes (for example whitelisted Makefile operations) were designed but not implemented.
- **Format translation.** Automatic conversion between SKILL.md, `.cursorrules`, `.mdc`, and similar formats.
- **Registry-based skill sources.** Installing skills by registry coordinates instead of git URLs.

---

## Appendix B: Field Reference: csk-skill.json

| Field | Since | Required | Description |
|-------|-------|----------|-------------|
| `schema_version` | 1 | yes | Integer 1 through 5 |
| `commands` | 1 | no | Exported commands: `script` (`unix_path`, `win_path`) or `system` (`command`, `hint`) |
| `runtime_roots` | 2 | no | Disjoint POSIX-relative directories copied to the runtime store |
| `dependencies.commands` | 2 | no | `system` requirements; legacy `skill` form |
| `capabilities` | 3 | yes (3+) | `network`, `filesystem`, `exec`, `secrets`, `env_read`, `prompt_scope` |
| `dependencies.skills` | 4 | no | Requirements: `git`, `ref {kind: tag\|revision, value}`, `mode`, `commands` |
| `dependencies.mcp_servers` | 5 | no | MCP requirements: `hint` (required), `transport`, `required_in` |

## Appendix C: Field Reference: Skillfile.json

| Field | Required | Description |
|-------|----------|-------------|
| `schema_version` | yes | Integer 1 |
| `project.alias` | no | Project alias for hybrid targeting |
| `agents` | no | Target agents (Section 10) |
| `locale` | no | Project locale |
| `skills[].name` | yes | Skill identifier, unique |
| `skills[].source` | no | Path under `skills_root`; defaults to name |
| `skills[].git` | no | Clone URL for a missing source |
| `skills[].tag` / `branch` / `revision` | exactly one | Exact reference |

Hybrid manifests add a required per-skill `targets` list (Section 9.3).

---

## References

### Key Articles and Research

**SSH certificates: the better SSH experience**  
Jan-Piet Mens, April 2026  
https://jpmens.net/2026/04/03/ssh-certificates-the-better-ssh-experience/  
Primary inspiration for the publisher signing model explored in the original draft (now Appendix A). Demonstrates that SSH Certificate Authorities provide a stronger trust model than TOFU (Trust On First Use) with comparable implementation complexity. The article's key insight (trust established once via configuration, eliminating interactive prompts and non-deterministic trust state) also shaped the implemented registry key pinning model (Section 13).

**Snyk ToxicSkills: Malicious AI Agent Skills on ClawHub**  
Snyk Security Research, February 2026  
https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/  
Scanned 3,984 agent skills. Found 36.82% with at least one security flaw, 13.4% at critical severity, and 76 confirmed malicious payloads. The ClawHavoc campaign (January 2026) poisoned 341 skills on ClawHub. This research validates the necessity of the CocoaSkills source audit (Section 12) and registry revocation (Section 13). Specific attack patterns from this study informed the audit detectors.

**OWASP Agentic Skills Top 10 (AST10)**  
OWASP Foundation, 2026  
https://owasp.org/www-project-agentic-skills-top-10/  
Catalogues the ten most critical security risks in agentic skill ecosystems: prompt injection, data exfiltration, privilege escalation, supply chain compromise, and others. The CocoaSkills audit detectors use AST10 categories as a primary taxonomy for detection patterns (Section 12).

**SKILL.md Specification**  
Anthropic, December 2025  
https://agentskills.io/specification  
De facto standard skill format adopted by 44+ agents. CocoaSkills preserves compatibility with this format (Section 17.2): csk-skill.json is a metadata companion to SKILL.md, adding dependency management and capability declarations without modifying the skill content format itself.

**SSH Certificate Format (Internet-Draft)**  
draft-miller-ssh-cert-06  
Technical specification of the SSH certificate format used by OpenSSH. The publisher certificate design of the original draft (Appendix A) mapped directly to this format.

### Existing Alternatives

**npx skills (Vercel Labs)**  
https://github.com/vercel-labs/skills; registry: https://skills.sh  
Largest ecosystem (87K+ indexed skills, 44 agent support). Project-local installation by default. Clean UX for adding individual skills (`npx skills add <owner/repo>`).  
**Strengths adopted by CocoaSkills:** project-local scope, git-based installation, multi-agent support.  
**Gaps CocoaSkills addresses:** no declarative manifest (skills are added imperatively, one at a time), no reproducible lockfile (partial `skills-lock.json` exists but is output-only, not used for restore), no version pinning beyond git tree SHA, no dependency resolution, no security gating.

**pixi-skills (pavelzw)**  
https://github.com/pavelzw/pixi-skills  
The only existing tool with a full manifest (`pixi.toml`), deterministic lockfile (`pixi.lock` with SAT-solved resolution), and frozen lockfile mode for CI. Resolves skill dependencies alongside runtime dependencies (Python, Node.js, CLI tools) via conda-forge and PyPI.  
**Strengths recognized by CocoaSkills:** deterministic lockfile model, frozen install for CI, dependency resolution.  
**Gaps that prevent adoption:** requires conda ecosystem (recipe.yaml + rattler-build publishing ceremony), two-step install process (pixi install + pixi-skills manage), heavy `.pixi/` directory, small skill catalog (~100 vs 87K on skills.sh), npm/cargo/gem dependencies still require manual task steps. CocoaSkills takes a purpose-built approach that avoids the conda packaging overhead while reaching reproducibility through exact references and install markers.

**vskill (verified-skill.com)**  
https://verified-skill.com  
Security-first skill verification tool (111K indexed skills). Three-tier trust model (Scanned / Verified / Certified). 38 deterministic security rules plus LLM-based intent analysis. Lockfile with SHA-256 and trust tier metadata.  
**Strengths recognized by CocoaSkills:** security scanning as a first-class concern, trust tiering concept, deterministic rule-based analysis.  
**Gaps that prevent adoption:** not a dependency manager (no manifest, no install-from-manifest, no dependency resolution). Complementary tool, not a replacement. CocoaSkills integrates scanning (Section 12) alongside dependency management and adds registry-backed attestation and revocation (Section 13), which vskill does not provide.

**skillman (pi0/unjs)**  
https://github.com/pi0/skillman  
Closest existing tool to a declarative manifest (`skills.json`). Reads a manifest and calls `npx skills add` for each entry.  
**Strengths:** simple declarative model.  
**Gaps:** thin wrapper over npx skills, no lockfile, no version pinning, no security. May become redundant if Vercel adds native manifest support.

**agent-skill-manager / asm (luongnv89)**  
https://github.com/luongnv89/agent-skill-manager  
Best security features among imperative tools: `asm audit security`, TUI dashboard, 17 agent providers, duplicate detection. Global-first installation with optional `--scope project`.  
**Strengths:** security auditing, broad agent support.  
**Gaps:** imperative workflow (no declarative manifest), global-first default, lockfile is global-only.

**SkillKit (rohitg00)**  
https://github.com/rohitg00/skillkit  
Format auto-translation (SKILL.md ↔ .cursorrules ↔ .mdc), memory persistence, multi-machine mesh (P2P skill distribution).  
**Strengths:** format translation is valuable for multi-agent delivery.  
**Gaps:** breadth over depth, not a dependency manager. Format translation is a feature CocoaSkills may adopt in a future version (Appendix A).

### Adjacent Infrastructure Projects

The following projects are out of scope for the current protocol. They address problems adjacent to skill dependency management and may be integrated or referenced in future versions.

**Sigstore (sigstore.dev)**  
https://www.sigstore.dev/  
Keyless code signing and transparency logging. The Rekor transparency log provides a public, immutable audit trail of all signing events. A future trust provider layer (Appendix A) could support Sigstore. The implemented registry already keeps a hash-chained transparency log (Section 13.8); Rekor would add a public, external one.

**mise (jdx/mise)**  
https://github.com/jdx/mise  
Polyglot runtime version manager (successor to asdf). Manages Node.js, Python, Go, Ruby, and other runtime installations per-project via `.mise.toml`. CocoaSkills delegates system tool installation to tools like mise: a skill declares system commands (Section 5.6), csk verifies their presence on PATH, and `hint` fields can reference mise installation commands. CocoaSkills complements mise rather than replacing it.

**direnv (direnv/direnv)**  
https://github.com/direnv/direnv  
Per-directory environment variable management. The implemented shell hook (Section 14) covers the same activation need; direnv users can source `.agents/env.sh` from `.envrc` themselves. Generated direnv files were part of the original draft only.

**tree-sitter (tree-sitter/tree-sitter)**  
https://github.com/tree-sitter/tree-sitter  
Incremental parsing framework supporting 100+ languages. The original draft planned tree-sitter based AST audit; the implemented audit uses deterministic detectors plus optional backends (Section 12). Tree-sitter remains a candidate for deeper static analysis.

**go-git (go-git/go-git)**  
https://github.com/go-git/go-git  
Pure Go git implementation. Relevant to the original Go implementation plan; the reference implementation shells out to system git with a restricted transport allowlist (Section 8.2).

**Rekor (sigstore/rekor)**  
https://github.com/sigstore/rekor  
Transparency log for software supply chain. Records signed metadata about software artifacts in a tamper-evident, append-only log. A future integration could anchor registry log heads (Section 13.8) in Rekor for public auditability.

**Namecoin**  
https://www.namecoin.org/  
Decentralized naming system based on blockchain technology. `id/` namespace records can associate human-readable identities with cryptographic public keys without relying on any central authority. A candidate for a future trust provider (Appendix A) for use cases requiring maximum decentralization and censorship resistance.

**AAIF (AI Agent Interoperability Framework)**  
https://aaif.io/  
Linux Foundation-hosted vendor-neutral governance initiative for AI agent standards. Members include Anthropic, OpenAI, Google, Microsoft, and AWS. Relevant to the CocoaSkills multi-agent delivery model (Section 10): future AAIF standards for skill format interoperability could simplify or replace the agent adapter layer.

### Standards and Governance

| Standard | URL | Relevance to CocoaSkills |
|----------|-----|------------------------|
| SKILL.md Specification | https://agentskills.io/specification | Skill content format. CocoaSkills preserves compatibility (Section 17.2). |
| AGENTS.md | https://agents.md | Project-level agent instructions (OpenAI convention). Not generated by the implemented protocol. |
| AAIF | https://aaif.io | Vendor-neutral agent governance. Future interoperability target. |
| OWASP AST10 | https://owasp.org/www-project-agentic-skills-top-10/ | Security risk taxonomy. Primary source for audit detectors (Section 12). |
| SSH Certificate Format | draft-miller-ssh-cert-06 | Certificate wire format of the original draft signing design (Appendix A). |
| DKIM (RFC 6376) | https://tools.ietf.org/html/rfc6376 | Inspiration for the DNS TXT key discovery of the original draft (Appendix A). |

### Skill Registries

| Registry | URL | Skills | Security Audit | Notes |
|----------|-----|--------|---------------|-------|
| skills.sh (Vercel) | https://skills.sh | 87K+ | None | Largest discovery index. Backend for `npx skills`. |
| SkillsMP | https://skillsmp.com | 700K+ | None | GitHub crawler. Largest by raw count. No vetting. |
| ClawHub (OpenClaw) | https://clawhub.ai | 13.7K | None (post-incident scanning added) | npm-style publish. Subject of ClawHavoc malware incident (January 2026, 341 poisoned skills). |
| SkillShield | https://skillshield.dev | 33.5K scanned | Mandatory scanning before listing | Security-first registry. All listed skills pass automated scanning. |
| verified-skill.com | https://verified-skill.com | 111K | Three-tier: Scanned (automated rules), Verified (deterministic + LLM analysis), Certified (manual review) | Most rigorous public audit pipeline. 38 deterministic rules + LLM-based intent analysis. |
| cursor.directory | https://cursor.directory | none | None | 63K community. Cursor rules + MCP configurations. Predates SKILL.md. |
| skill-forge (prefix.dev) | https://prefix.dev/skill-forge | ~100 | Conda package signing | Conda-packaged skills for pixi-skills. Inherits conda signing infrastructure. |

CocoaSkills consumes skills from any git repository regardless of registry listing. These registries serve as discovery tools; CocoaSkills references repositories directly through git URLs in the Skillfile (Section 6).

<!-- relux-ecosystem:start -->

## About Relux Works

This project is part of the open-source ecosystem of
[Relux Works](https://relux.works), an AI-native software development studio.
We build fixed-price MVPs, rescue vibe-coded apps, run local AI inference, and
train teams to work with coding agents. Much of the infrastructure behind that
work is open source.

- Full catalog: [relux.works/en/open-source](https://relux.works/en/open-source/)
- Agentic enablement: [agent harnesses & team training](https://relux.works/en/agentic-enablement/)
- Hire us the agent-native way: point your assistant at `https://api.relux.works/mcp`
- Contact: ivan@relux.works

<!-- relux-ecosystem:end -->
