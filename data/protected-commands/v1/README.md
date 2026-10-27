# Protected command inventory data v1

This is the release-owned dataset for the [inventory contract](../../../protocol/protected-command-inventory.md).
`inventory.json`, `artifact.json` and `sources.lock.json` are UTF-8 CCJ-1 bytes,
including the absence of a final newline. `artifact.json` supplies the whole-file
SHA-256; it is not embedded in the payload it hashes. The portable lock takes only
its `command_inventory` object, under L1's successor lock contract.

The initial version is `2026-10-27.1`: **4,192 keys**, **480,176 bytes**. The
research's mixed-license 4,412-key specimen is deliberately not published.
Inventory versions compare by date and then numeric revision counter, never
lexicographically (`.10` follows `.9`). Every published byte change needs a new
version and review, even when it only changes provenance/parser metadata.

## Sources and permission status

| Source | Status in this release | Extraction / notice |
| --- | --- | --- |
| aqua registry | Included, MIT | Effective literal files/build files, defaults and override union; [intact MIT notice](licenses/aqua-registry-MIT.txt). |
| aqua implementation | Reference-only semantic adapter pin, MIT | Naming/reset behavior from the pinned `package_info.go`; no implementation code copied. |
| mise | Included, MIT | Registry short names, aliases and bins; [intact MIT notice](licenses/mise-MIT.txt). |
| Curator seeds | Included identifier facts | Independently curated system, shell/grammar, VCS, package-manager, platform and manager identifiers in `seeds/`. No foreign implementation or prose copied. |
| GNU coreutils | Reference-only | GPL code / GFDL manual: pin and literal-variable recipe, including `ginstall` mapping and library exclusion; no bulk derived list. |
| Bash | Reference-only | GPL source / separately licensed manual: pin and `$BUILTIN` + `$FUNCTION` recipe; no bulk derived list. |
| Zsh | Reference-only | Permissive core, per-file exceptions: literal declarations including modules require further per-file review before bulk inclusion. |
| Apple shell/file/text/system command sources | Reference-only, each independently pinned | Mixed per-file licenses; Xcode tool-target product recipe only, no bulk derived list. |
| POSIX Issue 8 (2024) | Reference-only | Rights reserved: publication/content pins and utility/builtin extraction method; no HTML, prose, table or bulk derived list. |
| Host macOS observation | Excluded, reference-only | Coverage context only; no machine-specific executable inventory or proprietary content included. |

Every pin, input/seed digest, disposition, method and coverage count is in
[sources.lock.json](sources.lock.json). Reference-only pins cannot appear in entry
provenance. A source's MIT notice licenses its included registry material, not
the named programs. No additional source has been cleared by implication.

## Offline reproduction

Use Ruby **4.0.7**, Psych **5.3.1**, JSON **2.18.0**, and Python **3.15.1** with
stdlib `tomllib` as pinned in the manifest. Python conformance additionally uses
the repository's existing `jsonschema` dependency. No package/plugin/upstream
code is executed. Generation enumerates the pinned mise source directory;
publication and launch do not enumerate directories or parse registry sources.

Acquire the two source trees at the exact commits below into private scratch
storage, then disconnect network access for generation. This acquisition is a
maintainer action, never a runtime prerequisite. Run from the repository root:

```sh
(
  # Select your approved Git transport before acquisition.
  unset GIT_DIR GIT_WORK_TREE
  mkdir -p .temp/protected-inventory/inputs/aqua .temp/protected-inventory/inputs/mise
  git clone --no-checkout https://github.com/aquaproj/aqua-registry.git .temp/protected-inventory/aqua-source
  git -C .temp/protected-inventory/aqua-source checkout --detach 2db5a70b0c3e770bc9f61515cbefca7b13c405a8
  git clone --no-checkout https://github.com/jdx/mise.git .temp/protected-inventory/mise-source
  git -C .temp/protected-inventory/mise-source checkout --detach 59ae1b179162c89aa717accc1d090a08c6a7a9f8
)
cp .temp/protected-inventory/aqua-source/registry.yaml .temp/protected-inventory/inputs/aqua/
cp .temp/protected-inventory/aqua-source/LICENSE .temp/protected-inventory/inputs/aqua/
cp .temp/protected-inventory/mise-source/LICENSE .temp/protected-inventory/inputs/mise/
cp -R .temp/protected-inventory/mise-source/registry .temp/protected-inventory/inputs/mise/
ruby tools/protected_inventory_prepare.rb .temp/protected-inventory/inputs/aqua/registry.yaml > .temp/protected-inventory/inputs/aqua/registry.json
python3 tools/protected_inventory_generator.py --inputs .temp/protected-inventory/inputs --check
```

Use approved Git credentials for acquisition. Generation itself needs none. Source bundle identities are SHA-256 of CCJ-1 maps
`relative-path -> sha256:<whole-file hash>`; the prepared JSON is included alongside
raw YAML so parser behavior is bound too. The extractor digest uses the same map
form over the three `protected_inventory.py`, `protected_inventory_generator.py`
and `protected_inventory_prepare.rb` files under `tools/`. Notice bytes must match
pinned upstream licenses exactly. Source/seed drift, missing files, altered
extractor or coverage counts refuse; no quiet manifest rewrite.

For a reviewed update, edit pins/seeds/parser identity and independent coverage
witnesses, recompute their bundle digests and extractor digest, increment the
version, then run the generator without `--check` to write both the artifact and
metadata. Review complete additions/removals and source permissions. Generation
must not automatically bless its own changed coverage counts. Registry removals
require explicit policy review; consumers still enforce locked/current union.

## Tools and checks

| Tool / entry point | Purpose | Outputs |
| --- | --- | --- |
| `ruby tools/protected_inventory_prepare.rb INPUT.yaml` | Bounded data-only YAML, duplicate/tag/coercion controls; exact parser versions | Prepared JSON on stdout; private inputs under `.temp/`. |
| `python3 tools/protected_inventory_generator.py --inputs DIR [--check]` | Offline pinned extraction, coverage and CCJ-1 generation/comparison | `inventory.json` + `artifact.json`, or comparison only. |
| `python3 tools/check_protected_inventory_sources.py --inputs DIR` | Real YAML negative controls, prepared-source comparison, two full offline regenerations, coverage control plant | PASS/refusal on stdout; capture under `.temp/`. |
| `python3 -m unittest discover -s tools -p test_protected_inventory.py -v` | 24 pairs, schemas, identity/bounds, immediate preimages and normalization control plant | Test report; capture under `.temp/`. |
| `go run ./tools/protected_inventory_bench/main.go` | Cold + warm native lookup, identity validation and collision/preimage controls | JSON benchmark on stdout; [witnesses](../../../conformance/protected-command-inventory-v1/README.md). |

Run all checks with `env -u GIT_DIR -u GIT_WORK_TREE -u SSH_AUTH_SOCK -u GOFLAGS`
prefixed. The Python checker is a synthetic specification oracle, not admission
or manager ownership authority. Source checks require the pinned offline input
bundle; ordinary conformance uses only the committed artifact and synthetic data.
