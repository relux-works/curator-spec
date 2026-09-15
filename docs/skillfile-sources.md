# Authoring local, Git and collection sources

These examples target the unreleased Skillfile schema 2 contract, not the
current CLI. No local v2 installation is claimed. The normative rules are in
[Skillfile sources](../protocol/skillfile-sources.md) and the separate
[transport amendment](../protocol/repository-transport.md).

## Keep authored inputs separate

```text
project/
  Skillfile.json
  Skillfile.lock.json          frozen selection and package identities
  agents/skills/review/        authored package, no leading dot
    SKILL.md
    agent-skill.json
    scripts/
    build/
  .agents/skills/review/       managed context
  .agents/bin/                 managed command shims
  .codex/skills/review/        managed adapter entry
  .claude/skills/review/       managed adapter entry
<manager-state>/              protected snapshots, runtime store and build cache
```

Local packages retain their runtime, commands, builds and dependencies. They
are not a SKILL.md-only copy. Script edits require explicit refresh; launches
consume the frozen runtime. Do not point authored packages into managed output.

## Mixed sources

```json
{
  "schema_version": 2,
  "sources": {
    "project": {"path": "./agents"},
    "team": {"git": "https://example.org/kit.git", "tag": "v1.2.0"}
  },
  "skills": [
    {"name": "security-check", "git": "https://example.org/security-check.git", "tag": "v3.0.0"},
    {"from": "project", "directory": "skills", "include": ["docs", "release"]},
    {"name": "review", "from": "team", "directory": "skills/review"}
  ]
}
```

Legacy entries still work without `sources`; their `source` field keeps its
manager-source-root meaning. The example selects four distinct skills, each
with its own validated metadata, audit and dependency closure. URLs and refs
are illustrative, not fetched evidence.

Use any one of these acquisition objects as the value of `sources.team`:

```json
{"path": "../shared-agents"}
```
```json
{"path": "/work/shared-agents"}
```
```json
{"git": "git@example.org:kit.git", "tag": "v1.2.0"}
```
```json
{"git": "https://example.org/kit.git", "revision": "0123456789abcdef0123456789abcdef01234567"}
```
```json
{"repository": "example.org/kit", "branch": "main"}
```

Relative paths resolve against Skillfile.json. A local Git checkout supplies
its admitted dirty/untracked bytes, not committed HEAD. Branches are root-only.
To select a root package, use `{ "name": "review", "from": "team",
"directory": "." }`. To select nested authored skills, use
`directory: "agents/skills/review"` for one or `directory: "agents/skills"`
for a collection. `path: "."` with `directory: "agents/skills/review"` is legal.

Collection alternatives (choose one; overlapping installed names fail):

```json
{"from": "team", "directory": "skills", "include": ["review", "docs"]}
```
```json
{"from": "team", "directory": "skills", "include": ["*"]}
```
```json
{"from": "team", "directory": "skills", "include": ["*"], "exclude": ["release"]}
```

Only immediate directories participate. Missing named members and malformed
selected packages fail. For different refs, declare `stable` and `next` aliases
for the same repository and select distinct skill names from each. This does
not permit two installed versions of `review`.

## Machine transport policy

A workstation can use this operator-owned machine policy:

```json
{
  "schema_version": 1,
  "repositories": {
    "example.org/kit": {
      "endpoints": [
        {"url": "git@example.org:kit.git", "authentication": "team-ssh"},
        {"url": "https://example.org/kit.git", "authentication": "team-https"}
      ],
      "fallback": "availability-auth"
    }
  }
}
```

CI can reverse that list or pin the HTTPS URL with `pin`; the shared declaration
and locked commit stay identical. Configure the named authentication providers
through the manager's existing operator mechanism. Never put secrets in these
objects. TLS, host-key, integrity, ref and audit failures forbid fallback.

For a package at the project root, explicitly admit its disjoint inputs through
`root_inputs`, for example `{"project":["SKILL.md","agent-skill.json",
"references","scripts","build"]}` in source-policy.json. Listed files and
directories must exist and cover every required input; remove nonexistent
optional roots. Normal nested packages need no root input list.

Resolve/install and refresh here describe protocol operations; they are not
new CLI spellings. Use only a manager that explicitly implements both the
schema-2 contract and the required runtime/security lane.
