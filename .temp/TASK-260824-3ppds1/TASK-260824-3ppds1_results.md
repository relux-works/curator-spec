# TASK-260824-3ppds1 — publish curator-spec 1.0.0-rc.9

Release published. All gates run as standalone processes; exit codes below are real.

## Release identity

| Item | Value |
| --- | --- |
| Repository | `github.com/relux-works/curator-spec` |
| Tag | `v1.0.0-rc.9` (repo convention `v<version>`, matching `v1.0.0-rc.8`, `v1.0.0-rc.7`, …) |
| Tag object | `b67966449220d42218bd50420e74dac673431464` |
| Target commit | `0ed5c691e9208eea52f21db2fc05e226ce3516fd` — "Land schema 8 with the implementation pins that consume it (#29)" |
| Tag type | annotated + SSH-signed, message `Curator Protocol v1.0.0-rc.9` |
| Signing key | `/Users/iv/.ssh/ivanopcode`, ECDSA `SHA256:V6JiKG7J29mjsvikcLoSVp0bLa77VTsFy12gnLO81cM`, `oparin@me.com` — byte-identical to the sole entry in `maintainers.allowed_signers` |
| Release run | https://github.com/relux-works/curator-spec/actions/runs/32764992277 (success, 53s) |
| Release | https://github.com/relux-works/curator-spec/releases/tag/v1.0.0-rc.9 (prerelease, published 2026-08-24T18:54:36Z) |

The local checkout was fast-forwarded from `517a130` to `origin/main` `0ed5c69`
first: `release/1.0.0-rc.9.json`, the schema-8 surface, and the rc.9 CHANGELOG
entry had landed in PR #29 and were not yet in the local tree.

## GOVERNANCE.md release process

1. **Version metadata, schemas, vector manifest updated** — already in tree from
   the landing. `CHANGELOG.md` carries the `1.0.0-rc.9 - 2026-08-23` section;
   `release/1.0.0-rc.9.json` is the live candidate pin; rc.5–rc.8 metadata stays
   byte-frozen. rc.9 is referenced from `README.md`, `COMPATIBILITY.md`,
   `protocol/assurance.md`, `tools/validate.py`, `tools/release_gate.py`, and
   `tools/generate-vectors/main.go`.
2. **Regenerate twice, prove a clean second run** — see below.
3. **Required checks green on the protected default branch** — see below.
4. **Annotated signed `v<version>` tag** — created and verified before push.
5. **GitHub release with normative schemas + conformance archive and SHA-256
   checksums** — verified by independent download.

## Regeneration determinism (governance step 2)

Run in a task-scoped worktree at `0ed5c69`
(`curator-spec/.temp/TASK-260824-3ppds1/worktree`), Python 3.14 venv with
`jsonschema==4.25.1` from `requirements-dev.txt`.

| Command | Exit | Result |
| --- | ---: | --- |
| `go run ./tools/generate-vectors -root .` (run 1) | 0 | — |
| `git diff --exit-code -- conformance/v1 release/1.0.0-rc.{5,6,7,8,9}.json` | 0 | no drift |
| `go run ./tools/generate-vectors -root .` (run 2) | 0 | — |
| `git diff --exit-code -- conformance/v1 release/1.0.0-rc.{5,6,7,8,9}.json` | 0 | no drift |

Byte-identity proven independently of git: recursive SHA-256 over every file in
`conformance/v1`, sorted, hashed —

```
after run 1: 54d8e7e149e9b3acb9f42f90420b59772bbbc15eb056db46c2a761d27cf025df
after run 2: 54d8e7e149e9b3acb9f42f90420b59772bbbc15eb056db46c2a761d27cf025df
```

Suite manifest digest matches the pin exactly:

```
conformance/v1/manifest.json  sha256 803918bf8672f76cf990985e51db213b826674cd5bb54fbf47731b8404b44403
release/1.0.0-rc.9.json       candidate_protocol_pin.manifest_sha256
                              sha256:803918bf8672f76cf990985e51db213b826674cd5bb54fbf47731b8404b44403
```

## Local gates before signing

| Command | Exit | Output |
| --- | ---: | --- |
| `python tools/validate.py` | 0 | `validated 53 schemas and 691 vector files` |
| `python -B -m unittest discover -s tools -p 'test_*.py'` | 0 | `Ran 134 tests … OK` |
| `go test ./tools/...` | 0 | `ok github.com/relux-works/curator-spec/tools/generate-vectors 0.409s` |
| `python tools/verify_release_merge_policy.py` | 0 | `repository relux-works/curator-spec permits only GitHub-verified squash release targets` |
| `python tools/verify_release_commit.py --commit 0ed5c69…` | 0 | `release target 0ed5c691… is a GitHub-verified commit on origin/main` |
| `python -B tools/release_gate.py --version 1.0.0-rc.9 --commit HEAD` | 0 | `release gate passed for 1.0.0-rc.9 at 0ed5c691…` |
| `git -c gpg.format=ssh -c gpg.ssh.allowedSignersFile=… verify-tag v1.0.0-rc.9` | 0 | `Good "git" signature for oparin@me.com with ECDSA key SHA256:V6JiKG7J…` |

Together these are `make validate` + `make regenerate-check` + the
`release-check` gate that `RELEASE.md` requires before signing.

Note: `release_gate.py` requires a clean checkout and its own import of
`tools/assurance.py` writes `tools/__pycache__`, which trips that check on a
first bare run. The release workflow sets `PYTHONDONTWRITEBYTECODE: "1"` at the
job level; reproducing locally needs the same env (or `-B`). Not a defect —
recorded so the next release run does not misread it as a dirty tree.

## Required checks on `main` at the release target

All check-runs on `0ed5c691…` report `success`:

```
Formatting                    Release target provenance
Links                         Specification (ubuntu-latest)
Implementations (ubuntu-latest)   Specification (macos-latest)
Implementations (macos-latest)    Specification (windows-latest)
Implementations (windows-latest)
```

This satisfies the `RELEASE.md` candidate item "`make validate` passes on Linux,
macOS, and Windows" and the release-target-provenance item.

## Release workflow

Run 32764992277, job "Publish signed specification artifacts", 53s, every step
green. `Validate release input` is the step that runs `git verify-tag
v1.0.0-rc.9` with `gpg.ssh.allowedSignersFile` pointed at
`maintainers.allowed_signers` — so the tag signature was verified against the
maintainer allowlist by CI, not only locally. That same step re-ran
`verify_release_commit.py`, `validate.py`, the Python and Go test suites,
regeneration with `git diff --exit-code`, and `release_gate.py`.

## Published artifacts (verified by independent download)

| Asset | Size | State | SHA-256 |
| --- | ---: | --- | --- |
| `curator-protocol-1.0.0-rc.9.tar.gz` | 291597 | uploaded | `524f505c5f9170f15730485888db27dfa8ad48ee2939176e35a225daf3a01bd7` |
| `curator-protocol-1.0.0-rc.9.zip` | 738498 | uploaded | `dc8df7112418d636be86fc089eb7162409136d60ccc472bf41849e6e908b33cf` |
| `checksums.txt` | 199 | uploaded | — |

- `shasum -a 256 -c checksums.txt` → exit 0, both `OK`.
- Archive carries the normative schemas (53 files under `schemas/v1/`) and the
  conformance suite. `conformance/v1/manifest.json` inside the tarball hashes to
  `803918bf…`, identical to the rc.9 pin — the published archive is the pinned
  suite, not a rebuild.
- Top level also contains `protocol/`, `profiles/`, `cli/`, `decisions/`,
  `docs/`, `release/`, `reviews/`, `maintainers.allowed_signers`, and the
  governance/policy docs.
- SLSA build-provenance attestation verifies for both archives
  (`gh attestation verify … --repo relux-works/curator-spec` → exit 0),
  predicate `https://slsa.dev/provenance/v1`, subjects
  `[checksums.txt, curator-protocol-1.0.0-rc.9.tar.gz, curator-protocol-1.0.0-rc.9.zip]`,
  built by `.github/workflows/release.yml` at `refs/tags/v1.0.0-rc.9`.
  Negative control (an unattested file) fails with exit 1, so the verification
  is real and not a silent pass.

## Acceptance criteria

- Tag `v1.0.0-rc.9` — convention verified against existing tags — signed and
  pushed. ✅
- Release workflow green. ✅
- Release artifacts published with SHA-256 checksums. ✅

## Scope note

No repository source changed for this task; publishing rc.9 is a release
operation over already-landed bytes. Nothing was committed to `curator-spec`.
The only new immutable object is the signed tag. No new tests were written:
the behavior under test is the existing release tooling, and its suites
(134 Python tests + the Go generator tests) were run green against the exact
release target.
