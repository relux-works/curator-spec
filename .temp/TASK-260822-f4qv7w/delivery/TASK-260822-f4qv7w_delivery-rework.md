# TASK-260822-f4qv7w delivery rework

## Delivered scope

- Signed commit: `dd9c9fc079470f03f247b71efb52d4de6b204e78` (`G`, signer `oparin@me.com`).
- Branch: `spec/script-worker-v1-normative`.
- Remote branch head matches the local commit.
- Committed only the reviewed conformance/vector/tooling scope.
- Excluded `.temp/`, `tools/__pycache__/`, and the generated rewrite of immutable `release/1.0.0-rc.8.json` as required by the review verdict.

## Standalone validation evidence

| Command | Exit | Result |
| --- | ---: | --- |
| `.temp/TASK-260822-f4qv7w/venv/bin/python tools/validate.py` | 1 | `rc.8 downstream candidate pin does not match the suite manifest` |
| `.temp/TASK-260822-f4qv7w/venv/bin/python -B -m unittest discover -s tools -p 'test_*.py'` | 1 | 95 tests; 4 failures and 1 error, all caused by the same rc.8 live-pin invariant |
| `go test ./tools/...` | 1 | `TestRC8ReleaseMetadataPinsSuiteWithoutClaimFabrication` rejects the new manifest because immutable rc.8 was intentionally not rewritten |
| `gofmt -l tools` | 0 | No output |
| `git diff --check` | 0 | No output |

The earlier direct system-Python attempts also exited 1 because that interpreter lacks `jsonschema`; the venv reruns above are the authoritative local Python evidence.

## Remote CI

- Workflow: `Specification CI`
- Run: https://github.com/relux-works/curator-spec/actions/runs/32632173590
- Event: `workflow_dispatch`
- Head SHA: `dd9c9fc079470f03f247b71efb52d4de6b204e78`
- Overall conclusion: failure (`gh run watch --exit-status` exit 1).
- Green jobs: Formatting, Links, Release target provenance.
- Failing jobs: Specification on Ubuntu, macOS, and Windows. Every lane fails at `python tools/validate.py` with `rc.8 downstream candidate pin does not match the suite manifest`; later test/regeneration steps are skipped.

## Stop-the-line constraint

The reviewed vector bytes change `conformance/v1/manifest.json`. Current validator, generator, Go tests, Python tests, and CI require `release/1.0.0-rc.8.json` to pin the live manifest. rc.8 is already tagged/published and is declared immutable, so making this branch green by committing the generated rc.8 rewrite would falsify historical release evidence.

The board has already assigned the clean resolution to `TASK-260822-c0rxj7`: create the shared Schema 8 rc.9 candidate, migrate release tooling/metadata to rc.9, combine decision 0008 and 0009 bytes, regenerate twice, and qualify that immutable candidate. That task is currently backlog and unassigned.

Attempts and rejected forced fits:

1. Keep the rc.8 rewrite: would make current validation green but mutate published historical evidence; rejected.
2. Exclude the rc.8 rewrite: preserves history and matches the reviewer instruction, but current CI necessarily fails; this is the committed state.
3. Change validator/tests to ignore the live pin while still calling the protocol rc.8: would weaken the release invariant and create a special case; rejected.

Recommended resolution: route and execute `TASK-260822-c0rxj7`'s rc.9 candidate migration, then re-run Specification CI against the candidate head and return this task to review using that green evidence. Exact external input needed is an rc.9 candidate commit owned by `TASK-260822-c0rxj7`; expanding this task to author that cross-story candidate would violate the recorded ownership boundary.
