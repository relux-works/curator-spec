# Manager-Provisioned CLI Tools (v1)

This document specifies the v1 concrete surface for
[CIP-0007](../cips/CIP-0007-manager-provisioned-cli-tools.md): declarative
external CLI tool dependencies in `agent-skill.json` schema 10, built-in
trusted catalog resolution (Aqua Registry + curated PyPI via manager-provisioned
`uv`), sealed store layout, and exposure through profile command roots.

## 1. Skill manifest surface (`schema_version: 10`)

Schema 10 (`schemas/tool-provisioning-v1/agent-skill-v10.schema.json` and its
legacy alias `csk-skill-v10.schema.json`) extends schema 9 with exactly one
new member under `dependencies`: `dependencies.tools`.

Schemas 1 through 9 MUST reject `dependencies.tools`.

`dependencies.tools` is a JSON object mapping each exported alias name (a
portable command identifier) to a tool requirement object:

```json
{
  "dependencies": {
    "tools": {
      "colab": {
        "id": "pypi/google-colab-cli",
        "version": ">=0.8.0"
      },
      "uv": {
        "id": "aqua/astral-sh/uv",
        "version": ">=0.10.0"
      }
    }
  }
}
```

Rules:

1. **No package-supplied fetch URLs:** `id` MUST match one of the closed
   catalog namespaces:
   - `aqua/<owner>/<repo>` (Aqua Registry package identifier);
   - `pypi/<package>` (curated PyPI package identifier).
   URLs, paths, checksums, and install commands are rejected at parse time.
2. **Version constraint:** `version` is a non-empty version or range constraint
   (e.g. `0.8.0`, `>=0.8.0`, `^0.8.0`, `latest`) with no whitespace-injected
   flags or URL characters.
3. **Alias uniqueness:** an alias declared under `dependencies.tools` MUST NOT
   collide with a protected command name (`curator-*`, Windows device names) or
   with another active exported command or tool alias in the same profile
   command root.

## 2. Trusted catalog backends

The v1 manager ships a built-in trusted catalog supporting `darwin-arm64`,
`darwin-amd64`, `linux-amd64`, and `linux-arm64` with two closed backends:

### 2.1 Aqua backend (`aqua/<owner>/<repo>`)

- Resolves pinned built-in records (including `aqua/astral-sh/uv` with exact
  per-platform SHA-256 digests) directly from the manager's built-in catalog.
- For other `aqua/<owner>/<repo>` identities not pre-pinned in the binary, the
  manager MAY consult the official Aqua Registry definition
  (`https://raw.githubusercontent.com/aquaproj/aqua-registry/main/pkgs/<owner>/<repo>/registry.yaml`)
  for `type: github_release` packages ONLY when the release provides a
  verifiable SHA-256 checksum asset; packages without verifiable SHA-256
  checksums MUST refuse closed.
- Every downloaded archive MUST match its verified SHA-256 digest before
  extraction and MUST be extracted with strict archive-containment checks into:
  `<manager-home>/tools/store/aqua/<owner>/<repo>/<version>/<os>-<arch>/`.

### 2.2 Curated PyPI backend (`pypi/<package>`)

- Only packages explicitly admitted in the manager's curated PyPI allowlist
  (starting with `pypi/google-colab-cli`, executable `colab`, Python `>=3.12`)
  are eligible. Unknown PyPI packages MUST refuse with
  `tool_catalog_unknown`.
- The manager first ensures `aqua/astral-sh/uv` is provisioned in the sealed
  Aqua store, then invokes that sealed `uv` executable with explicit isolated
  environment variables (`UV_PYTHON_INSTALL_DIR`, `UV_CACHE_DIR`,
  `UV_PYTHON_DOWNLOADS=automatic`) — independent of host Python and immune to
  ambient `XDG_*` overrides — to materialize an isolated virtual environment at:
  `<manager-home>/tools/store/pypi/<package>/<version>/<os>-<arch>/venv`.
- Publication is atomic (staging directory renamed into final sealed store path
  with mode `0700`) and writes `.curator-tool-receipt.json` conforming to
  [`tool-receipt-v1.schema.json`](../schemas/tool-provisioning-v1/tool-receipt-v1.schema.json).

## 3. Exposure through profile command roots

Provisioned tools are never installed system-wide. For an installed profile
whose active skill closure declares `dependencies.tools`, the manager publishes
a fixed private executable entry `<alias>` inside the profile's generation
command root:

```text
<manager-home>/environments/<profile>/commands/<generation>/<platform>/bin/<alias>
```

covered by `.curator-profile-command-root.json` and delivered at launch via
`launch-env-fragment-v9` (`command_root` + `path_prepend`) or interactive
operator execution via `curator profile exec <profile> -- <command> [args...]`.
