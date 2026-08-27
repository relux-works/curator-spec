# TASK-260822-1so0ym delivery evidence

## Delivery identity

- Branch: `spec/module-roots-prose`
- Commit: `bac193cadb7d26aabf006c92924b4a05f6574e31`
- Tree: `3dc7d6181db8321f9638e1333a670f229402eb38`
- Remote ref verified with `git ls-remote`: exact commit match, exit 0
- Suite manifest SHA-256: `88f7a81f4553fd8946a6f62407990a773f0f2f115b598b817dc9221a0467bb4a`
- Module-root vector SHA-256: `b13dcd6177bef7fcb4c96b4dc29a8435883d22624855ddfbfd2de6e760596dac`
- Immutable `release/1.0.0-rc.8.json` is unchanged from branch baseline.

## Implemented corpus

`conformance/v1/vectors/module-roots.json` contains ten cases:

1. valid declared module roots with reconciled directive and selection annotations;
2. replacement target escaping the snapshot;
3. module-to-module redirect;
4. undeclared directory replacement;
5. declared module without a replacement;
6. nested declared module roots;
7. module root contained by a build root;
8. module root contained by a runtime root;
9. versioned-left directory replacement;
10. Windows case-colliding declared module roots.

Every rejection binds the normative stable diagnostic and failure boundary and proves that `go build` does not start and persistent state does not change.

## Validation evidence

All commands below were run directly as standalone processes.

| Command | Exit | Result |
| --- | ---: | --- |
| `go test ./tools/generate-vectors -run '^TestGeneratedModuleRootConformanceVectors$'` before implementation | 1 | Expected red: generated vector absent |
| `go run ./tools/generate-vectors -root .` final pass 1 | 0 | Generated authoritative tree |
| `go run ./tools/generate-vectors -root .` final pass 2 | 0 | Regenerated authoritative tree |
| `cmp ...regeneration-pass1.sha256 ...regeneration-pass2.sha256` | 0 | Full generated inventories byte-identical |
| `PATH="$PWD/.temp/venv/bin:$PATH" make validate` on fully regenerated tree | 0 | 52 schemas, 687 vector files, 95 Python tests, Go tool tests |
| `go test ./tools/generate-vectors -run '^TestGeneratedModuleRootConformanceVectors$'` on committed bytes | 0 | Task regression green |
| `test -z "$(gofmt -l tools)"` | 0 | Formatting clean |
| `git diff --check` | 0 | Whitespace clean |
| `go test ./tools/...` after restoring immutable rc.8 | 1 | Expected integration red: rc.8 live pin mismatch only |
| `python3 tools/validate.py` after restoring immutable rc.8 | 1 | Expected integration red: rc.8 downstream candidate pin mismatch only |
| `git commit -m 'Add module root conformance vectors'` | 0 | Commit `bac193c...` |
| `git push origin spec/module-roots-prose` | 0 | Remote advanced `61ab801..bac193c` |

The first `make validate` attempt exited 2 because the checkout lacked `jsonschema`. The project-pinned `jsonschema==4.25.1` was installed into task-local `.temp/venv` via `.temp/venv/bin/python -m pip install -r requirements-dev.txt` (exit 0); the authoritative retry above exited 0.

## Remote CI

- Workflow: Specification CI
- Run: `32632733803`
- URL: https://github.com/relux-works/curator-spec/actions/runs/32632733803
- Event: `workflow_dispatch`
- Head SHA: exact `bac193cadb7d26aabf006c92924b4a05f6574e31`
- `gh run watch --exit-status`: exit 1
- Green jobs: Formatting, Links, Release target provenance
- Failed jobs: Specification on Ubuntu, macOS, and Windows
- Identical failure on all OSes: `validation failed: rc.8 downstream candidate pin does not match the suite manifest`

## Stop-the-line packet

Constraint: adding an authenticated conformance vector necessarily changes `conformance/v1/manifest.json`. Current generator, validator, Go tests, and CI require historical rc.8 metadata to pin that live manifest, while the task explicitly forbids changing tagged/published `release/1.0.0-rc.8.json`.

Rejected approaches:

- Commit the generated rc.8 rewrite: mutates immutable historical release evidence.
- Exclude the vector from the suite manifest: leaves normative conformance bytes unauthenticated.
- Suppress or special-case the validator: weakens the release-pin invariant and creates a forced fit.

Recommended path: `TASK-260822-c0rxj7` combines the script-worker and module-root branches into one immutable Schema 8 / rc.9 candidate, adds rc.9 release metadata and moves the live candidate validation there while retaining rc.8 byte-for-byte. That task's notes already name `spec/module-roots-prose` as the remaining input.

Exact external input required to resume: a green rc.9 candidate CI run from `TASK-260822-c0rxj7` containing commit `bac193c...` (or a descendant with identical task-owned bytes). Then this task can attach that gate evidence and return to review.
