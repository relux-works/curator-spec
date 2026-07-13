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
| `curator bootstrap [--if-missing]` | Create machine configuration interactively or from flags; keep an existing file unchanged with `--if-missing` |
| `curator init [path]` | Create `Skillfile.json` and ignore generated paths |
| `curator add <name> --tag\|--branch\|--revision <ref>` | Add or replace a direct declaration and install |
| `curator remove <name>` | Remove a declaration |
| `curator install [target] [--all] [--dry-run] [--strict-tags] [--audit [advisory\|strict]]` | Apply the manager lifecycle |
| `curator update` | Fetch configured source repositories |
| `curator upgrade [target] [--all] [--dry-run]` | Fetch only the selected dependency closure, then install |
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
| `curator shell-init [auto\|zsh\|bash\|powershell] [--install] [--no-global]` | Print or cache optional shell integration |

Exit code 0 is success. Curator distinguishes usage errors, partial multi-
project failure, drift checks, and security-policy blocks with non-zero codes;
scripts should use `status --json` when they need structured details.

`bootstrap --if-missing` is intended for repository bootstrap commands. It
returns success without parsing or rewriting an existing configuration and is
mutually exclusive with `--force`.

`upgrade` differs from `update`: upgrade fetches only direct and transitive
sources required by the selected project or global manifest, while update
fetches every repository below `skills_root`. `upgrade --all` deduplicates
repositories shared by project closures. Any install or upgrade `--dry-run`
uses temporary planning state and leaves source checkouts, caches,
configuration, runtime state, and project artifacts unchanged.

## Developer shell

Shell profile setup is optional. Agent instructions can invoke project
commands directly through `.agents/bin/<command>` on Unix or
`.agents\bin\<command>.cmd` on Windows. Global installation publishes
forwarding shims to a safe existing user-bin directory when possible.
Set `CURATOR_GLOBAL_USER_BIN` to a writable directory already on `PATH` when
automatic selection is unavailable.

For interactive bare command names, cache the hook once:

```bash
curator shell-init --install
# Add the source command printed above to .zshrc or .bashrc.
```

On Windows, automatic detection selects PowerShell unless `SHELL` identifies
Git Bash. Add the printed dot-source command to the PowerShell profile only if
interactive activation is wanted:

```powershell
curator shell-init --install
```

The cached hook is sourced without starting Curator on each shell launch.
`CURATOR_AUTO_ENV=0` disables project-directory scanning while retaining
global activation. Curator never edits a shell profile automatically.

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
