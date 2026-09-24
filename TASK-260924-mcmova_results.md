# TASK-260924-mcmova — results

## Change

`protocol/core.md` now defines hard-link substitution as a link that makes
resolution select an identity other than the platform-owned executable the
manager intended. The only multiply-linked target exception is a platform-owned
Windows executable named by `exec`, resolved through the manager's default
Windows executable search list, below canonical `%SystemRoot%\System32` derived
from the manager's captured `SystemRoot`, with every additional hard-link name
in that root's `WinSxS` component store. The exception fails closed if any bound
cannot be established. All other multiply-linked targets remain rejected.

The exception does not apply to the interpreter identity rules for `python3-v1`
or `node-v1`. Symlink and reparse-point rejection remains unchanged. The
manager's own worker executable also remains subject to its existing strict
identity rule.

`profiles/manager.md` repeats the rule. The generated script execution vector
has one positive System32/component-store case and negatives for an outside
System32 target, non-component-store links, non-default search, uncaptured
SystemRoot, an unowned file, and hard-linked Python and Node interpreters.
`tools/validate.py` closes the case set and rejects mutations that widen any
bound; generator and validator tests cover those negatives. `CHANGELOG.md`
records the erratum under Unreleased.

## Before / after

**Before — Core interpreter identity:**

> The resolved target MUST be a canonical regular executable file. Symlink,
> reparse-point, and hard-link substitution MUST be rejected, strong file
> identity MUST be recorded, and the executable's bytes MUST be hashed.

**After — Core identity and `exec` rule:**

> For this policy, a hard-link substitution is a hard link that causes
> resolution to select a file identity other than the platform-owned executable
> the manager intended. A multiply-linked executable target MUST be rejected
> except for the narrow Windows `exec` case below.

The new Windows case limits the exception to the manager's default Windows
executable search list, its captured `SystemRoot`, a target physically below
canonical `%SystemRoot%\System32`, and extra hard links belonging to that
SystemRoot's `WinSxS` component store. It explicitly excludes `python3-v1` and
`node-v1` interpreter files.

**Before — Manager interpreter control:**

> per-invocation identity verification of the resolved interpreter executable
> file, with symlink, reparse-point, and hard-link substitution rejected and
> identity re-checked at the launch boundary;

**After:** the control remains intact. The manager profile now defines the same
bounded Windows `exec` case separately and states that the interpreter
hard-link rejection is unchanged.

## Validation

| Check | Result |
| --- | --- |
| `python3 tools/validate.py` with the declared dev dependency available | Exit 0; validated 64 schemas and 1,169 vector files |
| `SchemaRegistryCacheTests` through `BuildDriverGoldenSuiteTests` | 45 tests, exit 0 |
| `SharedFixtureMarkerTests`, `WorkflowRegenerationScopeTests`, `EnvironmentVectorTests`, `EnvPassthroughVectorTests` | 66 tests, exit 0 |
| `StoreBoundaryVectorTests`, `PathKindAdmissionVectorTests` | 61 tests, exit 0 |
| `SourceSignersVectorTests`, `CodexSeedVectorTests` | 79 tests, exit 0 |
| `ContextVersionVectorTests`, `ContextDetectorVectorTests`, `SnapshotAcquisitionVectorTests`, `ShellHookTrustVectorTests`, `SecurityPostureVectorTests` | 61 tests, exit 0 |
| `WriteNofollowVectorTests` | 12 tests, exit 0 |
| `DotfileManagersVectorTests` | 20 tests, exit 0 |
| `ReadFailureVectorTests` excluding the scenario replay | 17 tests, exit 0 |
| `ReadFailureVectorTests.test_substituted_scenario_rejected_through_main` | 1 test covering 39 cases, 510.363 seconds, exit 0 |
| `UmbrellaProviderVectorTests`, `ManagerConfigVectorTests` | 45 tests, exit 0 |
| `SystemConfigV2SchemaTests`, `RegistryPageBoundaryVectorTests`, `RegistryCheckpointVectorTests` | 57 tests, exit 0 |
| `RegistryBootstrapVectorTests`, `TakeoverClosedSetTextTests` | 69 tests, exit 0 |
| `test_script_execution_vector_rejects_contract_drift` | 1 test, exit 0 |
| `test_verify_release_merge_policy.py` | 5 tests, exit 0 |
| `test_verify_release_commit.py` | 5 tests, exit 0 |
| `test_release_gate.py` isolated rerun | 32 tests, exit 0 |
| `test_implementation_coverage.py` | 36 tests, exit 0 |
| `go test ./tools/...` | Exit 0 |
| `go vet ./tools/...` | Exit 0 |
| `gofmt -d tools/generate-vectors/main.go tools/generate-vectors/main_test.go` | Exit 0; no formatting diff |
| `git diff --check` | Exit 0 |
| `make regenerate-check` | Exit 0; generator output and the generated-file diff check were clean |

All 533 `test_validate.py` tests passed in bounded class/method chunks. Two
attempts at full-file discovery were stopped near the ten-minute shell-call
bound with exit 130. An initial class-selection typo exited 1 and was corrected.
An initial concurrent `test_release_gate.py` run exited 1 because the other test
process temporarily repinned shared files; its isolated rerun passed.

The first system-Python validator attempt exited 1 because `jsonschema` was not
installed. The exact `requirements-dev.txt` dependency was installed into an
ignored, worktree-local virtual environment; the validator and subsequent tests
then passed. No repository lint target or Ruff installation is available;
Go vet, Go formatting, and whitespace checks passed.

`make regenerate-check` used a temporary alternate Git index containing the
intended generated vector, manifest, and `rc.9` pin updates. The real worktree
index remains unchanged and all repository edits remain uncommitted. Generator
refreshes were limited to the script vector, its manifest digest, and the
corresponding `rc.9` manifest pin; release schemas and qualification rules did
not change.

No Windows runtime lane was run; this is a specification and conformance-vector
change, not runtime implementation evidence.
