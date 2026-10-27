# Protected command inventory v1 conformance

[vectors.json](vectors.json) has exactly 24 negative/positive pairs, retaining the
research's order. [The executable driver](../../tools/test_protected_inventory.py)
uses the committed release artifact and isolated synthetic directories. It checks
the precise refusal and the complete synthetic preimage immediately after every
checker invocation, including both checks around drift. Its checker is a
specification witness, not Curator's actual installer, transaction publisher,
shell adapter, destination-admission authority or lock-carrier implementation.

| Pair | Negative obligation exercised | Positive control |
| --- | --- | --- |
| PCI-01 | Check exported `git`, not harmless package name | Unique export |
| PCI-02 | Built-binary alias `ssh` is reserved | Unique alias |
| PCI-03 | Exact manager names and case/suffix/prefix variants refuse | Unique non-manager name |
| PCI-04 | ASCII case and repeated executable/wrapper suffixes normalize | Distinct dotted name |
| PCI-05 | Shell builtins/keywords refuse | Context-only package exports nothing |
| PCI-06 | Selected/retained normalized names cannot be ambiguous | Distinct exports |
| PCI-07 | Static `jq` refuses, no grant authority in v1 | Rename export |
| PCI-08 | Purported approval reuse after source/commit/directory/output/alias/inventory/scope changes confers no authority | Rename export |
| PCI-09 | Actual base collision refuses regardless of any static approval claim | Unique export absent from base |
| PCI-10 | Uncatalogued custom base executable still collides | Unadmitted unrelated executable excluded |
| PCI-11 | Base arrival after valid preflight blocks launch check | Unrelated arrival preserves valid check |
| PCI-12 | Destination witness wins over caller PATH | Caller collision alone is irrelevant |
| PCI-13 | Missing/excluded witness, relative/workspace path, stale directory identity, unreadable directory refuse | Explicit absolute fixture witness |
| PCI-14 | One owned forwarder cannot exempt mixed-bin real commands | Exact owned wrapper tuple excluded |
| PCI-15 | Fake/foreign ownership and same-inode wrapper-content drift refuse | Captured inode/digest/owner/generation |
| PCI-16 | Allowed link still collides; unsafe/dangling link fails admission | Unrelated link and Unix non-executable file |
| PCI-17 | Directory replacement or owner change fails second check | Stable two-check witness |
| PCI-18 | Missing/wrong identity, unknown normalization/schema, duplicate JSON/name, extra field, truncation refuse | Known bytes + identity |
| PCI-19 | Old lock list cannot override new machine baseline | Old/current union with clean exports |
| PCI-20 | Control plants omit aqua defaults/Go basename/platform/version or mise alias/multiple bins; independent expected union catches each | Complete synthetic extraction |
| PCI-21 | Template, unsafe name coercion, malformed TOML/duplicate keys refuse | Literal extraction |
| PCI-22 | Wrong GNU installed-name/library, Bash help-only, Zsh module classifications fail independent expected facts | Correct synthetic recipe facts |
| PCI-23 | Undeclared RC/function/alias surface refuses | Declared alias needs no shell execution |
| PCI-24 | Wrong entry enumeration is rejected even with recomputed digest | Canonical key order; real seed/version change changes digest |

PCI-07–09 intentionally replace research grant-positive controls: this version
has **no operator approval protocol**. The named follow-up is
`command-static-overlap-approval-v1`; there are no grants to validate or reuse.
The fixture checker takes no approval argument. Publication atomicity, complete
successor-lock schema, real shell/admission/ownership authority and race exclusion
remain L1/Curator consumer tests, not results inferred from this driver. Windows
non-executable-file behavior intentionally differs from Unix.

Additional controls in `tools/check_protected_inventory_sources.py` execute the
pinned Ruby adapter on positive data-only anchors and negative syntax, multiple
documents, duplicate keys, object tags, cycles, unsafe coercion and templates.
They compare raw pinned YAML preparation and two complete offline regenerations
under changed locale, then plant an incorrect independent source count and
require `coverage_witness`. The unit driver also plants disabled ASCII folding:
the mutant admits `Git`, and the real policy rejects it. Coverage is grounded in
explicit expected names rather than agreement between two generators.

## Benchmark witnesses

[Native darwin/arm64 witness](benchmark-darwin-arm64.json) and
[six-spelling stress witness](benchmark-portable-stress-darwin-arm64.json) retain
all 31 warm samples, cold initialization and independent collision/preimage
controls. Both identify the exact committed artifact. The native run uses the
actual Unix lookup rule: a bare command has one candidate per directory; wrapper
names are explicit exports and count toward the 64-name limit. Static suffix
normalization remains platform-independent.

| Local fixture, Go 1.25.5, 64 exports / 12 directories | Cold | Warm p95 | Warm max | ≤20 ms |
| --- | ---: | ---: | ---: | --- |
| Native Unix, 768 candidate misses | 10.02 ms | 1.72 ms | 2.33 ms | Pass in this recorded run |
| Portable stress, 4,608 candidate misses | 46.53 ms | 58.72 ms | 72.97 ms | **Fail; unqualified** |

The stress run was recorded while maintainer source-validation work was active;
all observed delays remain included. Neither the budget nor the workload is
silently relaxed. Consumers must qualify their real admitted D/S/platform/load
envelope, including cold work when done per launch. These are reference-check
measurements, not end-to-end launcher, forwarder, arbitrary writable PATH,
network-filesystem, Windows or Linux qualification. The failed stress envelope
cannot be advertised as budget-compliant.

Run from the repository root (see [data/tool instructions](../../data/protected-commands/v1/README.md)):

```sh
env -u GIT_DIR -u GIT_WORK_TREE -u SSH_AUTH_SOCK -u GOFLAGS python3 -m unittest discover -s tools -p test_protected_inventory.py -v
env -u GIT_DIR -u GIT_WORK_TREE -u SSH_AUTH_SOCK -u GOFLAGS python3 tools/check_protected_inventory_sources.py --inputs .temp/protected-inventory/inputs
env -u GIT_DIR -u GIT_WORK_TREE -u SSH_AUTH_SOCK -u GOFLAGS go run ./tools/protected_inventory_bench/main.go > .temp/inventory-native-benchmark.json
env -u GIT_DIR -u GIT_WORK_TREE -u SSH_AUTH_SOCK -u GOFLAGS go run ./tools/protected_inventory_bench/main.go --suffix-mode portable-stress > .temp/inventory-stress-benchmark.json
```

A benchmark exits nonzero when cold or any warm sample exceeds 20 ms; a failed
sample is evidence of an unqualified envelope, not a passing performance check.
No network/process/directory enumeration occurs inside the timed check. Fixture
creation and Go compilation occur before its timer; artifact reading, hashing,
decoding and index construction occur inside the cold timer. Warm checks reuse
an immutable index and repeat admitted-directory identity/probe work. The only
contents read by a dynamic fixture check are explicitly captured manager wrappers.
