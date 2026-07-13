# Curator CLI guide

This document is informative. It describes the Go reference implementation,
not a conformance requirement. Other managers may use different command names,
flags, output, machine-home paths, and distribution channels.

Curator uses `curator`, defaults its machine home to `~/.curator`, reads user
configuration from `~/.curator/config.json`, and supports overrides through
`CURATOR_CONFIG` and `CURATOR_SYSTEM_CONFIG`. Those names are not protocol wire
identifiers.

## Commands

| Command | Behavior |
|---|---|
| `curator bootstrap` | Create machine configuration interactively or from flags |
| `curator init [path]` | Create `Skillfile.json` and ignore generated paths |
| `curator add <name> --tag\|--branch\|--revision <ref>` | Add or replace a direct declaration and install |
| `curator remove <name>` | Remove a declaration |
| `curator install [target] [--all] [--dry-run] [--strict-tags] [--audit [advisory\|strict]]` | Apply the manager lifecycle |
| `curator update` | Fetch configured source repositories |
| `curator upgrade [target]` | Update then install |
| `curator status [target] [--all] [--check] [--json] [--attest]` | Report drift and optionally refresh attestations |
| `curator list` | List configured projects and declarations |
| `curator project add\|resolve` | Register projects and resolve ownership of a path |
| `curator config show` | Print effective configuration |
| `curator skill check <dir> [--locale <code>] [--json]` | Validate one package |
| `curator global init\|add\|remove\|list\|status\|install\|update\|upgrade` | Manage global scope |
| `curator hybrid add\|remove\|list\|status` | Manage hybrid scope |
| `curator audit [target] [--all] [--global] [--json]` | Run source audit |
| `curator audit --allow <hash> --reason <text>` | Create an operator pin |
| `curator audit --publish <record> --registry <url>` | Publish an auditor-signed record |
| `curator gc` | Collect unreferenced machine state |
| `curator shell-init <zsh\|bash\|powershell> [--no-global]` | Print shell integration |

Exit code 0 is success. Curator distinguishes usage errors, partial multi-
project failure, drift checks, and security-policy blocks with non-zero codes;
scripts should use `status --json` when they need structured details.

## Developer shell

```bash
eval "$(curator shell-init zsh)"    # or bash
```

For PowerShell, add the emitted hook to the profile:

```powershell
curator shell-init powershell | Out-String | Invoke-Expression
```

## CI example

Pin a released Curator version using the platform package or verified release
artifact, then run the same protocol gates as local development:

```yaml
steps:
  - uses: actions/checkout@v4
  - name: Install Curator v0.1.1
    run: go install github.com/relux-works/curator/cmd/curator@v0.1.1
  - name: Materialize skills
    run: curator install . --strict-tags
  - name: Verify installed state
    run: curator status . --check
```

Organizations normally install enforced source, audit, and registry policy
before this job. CI MUST NOT disable a policy required on developer machines.
