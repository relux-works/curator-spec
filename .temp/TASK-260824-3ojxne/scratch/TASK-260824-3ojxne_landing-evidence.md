# TASK-260824-3ojxne — atomic schema-8 landing with implementation pins

Repository: `relux-works/curator-spec`
PR: [#29](https://github.com/relux-works/curator-spec/pull/29) — squash merged
Merge commit on `main`: `0ed5c691e9208eea52f21db2fc05e226ce3516fd`
Branch HEAD before merge: `daa1cf38f049ca2f2f67f4845dcda88f1778e9f9`

## Identity

| Fact | Value |
| --- | --- |
| Base | `origin/main` at `09f0423a` (#28) |
| Candidate merged in | `candidate/schema-8-rc.9` at `6001dc33281b94a4ec7442ab15278550dd0f51d9` |
| Merge conflicts | none; every line #28 added to `profiles/manager.md` and `protocol/core.md` verified present after the merge |
| Landing suite manifest | `sha256:803918bf8672f76cf990985e51db213b826674cd5bb54fbf47731b8404b44403` |
| Candidate suite manifest | identical — #28 is prose only and touches no suite file |
| Squash tree on `main` | `ee1ac91de4c3472630c07d4d9def4042a89ec9b6`, identical to the branch tree |

Because the landing suite manifest is byte-identical to the qualified
candidate, both implementations were qualified against exactly the bytes that
landed, not against an approximation of them.

## Pins advanced in the same commit as the bytes

| implementation | from | to | qualification |
| --- | --- | --- | --- |
| Go manager (`relux-works/curator`) | `bd6ba08a` | `a3abcf3468b4854904313295672eef6f7d8826fd` (main, PR 37) | dispatch 32689488293, SUCCESS, 3 OSes |
| Python manager (`ivanopcode/cocoaskills`) | `6fc2fd97` | `3ecca1dba9f8831e1617b7466c17ecc8a2957d3f` (main, PR 43) | run 32756144649, SUCCESS, 3 OSes |
| Registry (`relux-works/curator-skill-registry`) | `d690bea6` | unchanged | schema 8 adds no registry surface |

## Coverage contract added

New in this landing:

- `.github/ci/implementation-coverage.tsv` — 18 rows naming what each pin must
  be observed doing against this suite (7 Go cases, 11 manager cases) and the
  root artefacts each of them reads.
- `tools/implementation_coverage.py` — three subcommands: `families` (the suite
  still publishes every declared artefact), `go` (every Go row observed passing
  in that runner's real `go test -json` stream), `pytest` (every manager row
  observed passing in that runner's real `--junitxml` stream). Each fails by
  name; a skip of a declared case, or of any subtest of one, is fatal.
- `tools/test_implementation_coverage.py` — 36 unit tests over ledger shape,
  family resolution, both stream parsers, and the command-line exit codes.

The ledger is owned by the specification rather than deferred to each
implementation's own consumption ledger: an implementation that renames or
drops a schema-8 consumer fails this repository's gate, not only its own.

### Negative proofs (run locally against the merged tree)

| probe | implementation command | coverage gate |
| --- | ---: | --- |
| Go invocation without `./internal/scriptpolicy` | `go test` exit 0 | exit 1, names all 4 `internal/scriptpolicy` cases |
| manager suite with `-k "not module_root"` | pytest exit 0, 172 passed / 11 deselected | exit 1, names both module-root rows |
| `families` against the pre-schema-8 rc.8 root from `origin/main` (`sha256:d14e3a16`) | — | exit 1, names all 17 rows reading an unpublished family |

## Python manager released-suite module

`tests/test_protocol_conformance.py` was removed from this job. At pin
`3ecca1db` it authenticates one immutable suite — protocol `1.0.0-rc.6`,
manifest `sha256:12e58b82...` — and fails collection against any other root by
design (`assert digest == EXPECTED_CANDIDATE_MANIFEST_SHA256`). It could be
pointed at this repository's moving root only while the previous pin
`6fc2fd97` performed no authentication at all, which is the same false green
this landing removes. It keeps running against the suite it names in
cocoaskills' own CI (`RELEASED_SUITE_PIN: 0c81c1f8`), and returns to this job
when that pin advances to rc.9 — step 9 of the landing order, after rc.9 is
published. Its root-independent lifecycle selection is unchanged and still runs
here. This is recorded in a block comment in the workflow at the point where
the step used to be.

## rc.8 immutability

`git diff origin/main -- release/1.0.0-rc.8.json` is empty on the landing
branch, and the file on `main` after the merge hashes to
`sha256:293f101d10665061aa049efa72141f9e3c5d608bbde300e882f6e3e095e31ede`,
unchanged. `release/1.0.0-rc.9.json` records that digest as its historical
predecessor rather than replacing it.

## Double regeneration

`go run ./tools/generate-vectors -root .` run twice, each followed by
`git diff --exit-code -- conformance/v1 release/1.0.0-rc.{5,6,7,8,9}.json`.

| pass | generator exit | diff exit | worktree tree digest |
| --- | ---: | ---: | --- |
| 1 | 0 | 0 | `effb543a9e076ecba5aa39673875263735afe3a5` |
| 2 | 0 | 0 | `effb543a9e076ecba5aa39673875263735afe3a5` (unchanged) |

Repeated after every subsequent edit; both passes stayed at exit 0 with an
empty diff, and CI's own `Prove deterministic regeneration` step passed on all
three runners.

## Local gate results (merged tree, before push)

| command | exit |
| --- | ---: |
| `python tools/validate.py` | 0 (53 schemas, 691 vector files) |
| `python -B -m unittest discover -s tools -p 'test_*.py'` | 0 (134 tests, was 98 before this change) |
| `go test ./tools/...` | 0 |
| `gofmt -l tools` | 0, no output |
| `git diff --check` | 0 |
| full `implementations.yml` job simulation (all 3 OS-independent steps + lifecycle + registry) | 0 |

## Required checks, verified green pre-merge

| check | result | duration |
| --- | --- | ---: |
| Specification (ubuntu-latest) | pass | 36s |
| Specification (macos-latest) | pass | 44s |
| Specification (windows-latest) | pass | 1m37s |
| Implementations (ubuntu-latest) | pass | 1m2s |
| Implementations (macos-latest) | pass | 1m40s |
| Implementations (windows-latest) | pass | 2m51s |
| Formatting | pass | 6s |
| Links | pass | 7s |

Coverage-gate output observed on every runner: `18 declared claim(s) upheld`
(families), `7 declared claim(s) upheld` (Go), `11 declared claim(s) upheld`
(manager), plus cocoaskills' own `candidate-consumption: every declared
artifact is published`.

## Post-merge `main`

Runs on `0ed5c691`: `Specification CI` SUCCESS and `Implementation
conformance` SUCCESS. `Release target provenance`, which runs only off pull
requests, also passed — the squash commit verifies as a signed main-branch
release target, so the rc.9 publication step is not blocked on provenance.

## Documentation

- `CHANGELOG.md` — rc.9 gains the coverage contract under Added and the pin
  advance under Changed.
- `COMPATIBILITY.md` — adds the two rules the prose left implicit: an absent
  `execution_policy` means declared-only on every schema and is co-required
  with `interpreter` rather than defaulted, so no existing manifest acquires
  enforcement by omission; and an absent or empty `modules` list must have an
  empty effective replace set, the schema-6/7 rule unchanged. Also states
  marker v1–v3 byte stability (verified: `common.schema.json` only adds
  `$defs`; no marker v1–v3 schema or schema-case byte moved) and that rc.9
  supersedes rc.8 without changing rc.8.
- `README.md` — states that a pin must demonstrably consume what this
  repository publishes, and points at the ledger.

## Follow-ups this landing hands to later tasks

1. rc.9 publication per `RELEASE.md` with a signed `v1.0.0-rc.9` tag.
2. Advance cocoaskills' `RELEASED_SUITE_PIN` to rc.9, then restore
   `tests/test_protocol_conformance.py` to this repository's Implementations
   job.
3. Advance curator's `SPEC_PIN` to the rc.9 release commit.
