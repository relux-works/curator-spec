# Profile generations: N-only conformance draft

The [semantic chapter](../../protocol/profile-generations.md) owns the rules.
All three closed draft meta-schemas live in this corpus directory, as in the
startup corpus. [Schema notes](SCHEMAS.md) describe their scope; no production
family is reserved under `schemas/`.

`pairs.json` retains **48 paired rows: 7 package/render, 9 edge-selection,
12 evidence/negative and 20 authority/binding/recovery**. The original
`paired_requirement` texts are unchanged. `paired_extensions` adds paired
subcases for the agreed startup, authority, replay, verified-native and
compatibility semantics without allocating a 49th row. All rows remain `stub`
and `not-run`; references are planned coverage, not executed witnesses.

Each pair names its N/P `clause_refs` and `pending_gates`. Six publication/meta
clauses are separately classified with reasons in `meta_clauses`; every other
N clause and every P gate is referenced. `input_files` lists applicable baseline
files or the new textual A1 trace. `input_note` explains their limited role and
why missing successor/native instances are deferred. A referenced baseline
control does not become a new successor witness. No empty input list silently
claims a native or instantiated test result.

`a1.json` preserves the ten agreed bind-replay branches as a Q4-V12 expansion.
The parent names PG-HOLDER-01, PG-REPLAY-01/02 and PG-P-071. Exact original-
revision retrieval precedes a new-mutation CAS; current terminal bind refuses
non-admitting. The fixed fixture isolation gate applies to this qualification
trace, not every production replay. No trace branch has been executed.

`reuse.json` enumerates 96 unchanged files at baseline
`ab6b1b0960473b359c84d96e7c7749b9be6011e0`: hash-framing, complete carrier
publication, selected-directory, startup-verification and registry families.
Each entry binds Git blob and SHA-256. The closure includes referenced
instances, canonical bytes and old/new controls. Symbolic commit substitutions
require separate future materialization receipts; baseline bytes stay intact.

## Validation boundary

The draft's **external authoring checks are not checked into this publication**.
There is no versioned semantic checker or mutant-control runner for this family,
and the repository's normal conformance dispatcher does not invoke it. External
authoring receipts do not constitute a passing release or native conformance
result. The authoring procedure checks clause/vector correspondence, meta-clause
classification, gate coverage, exact A1 expectations and baseline blob/hash
identity, with valid neighbors and malformed-metadata controls. Those semantic
checks are separate from JSON Schema validation. For each baseline clause, the
union of its split trace rows must retain every vector assigned by the pinned
joint skeleton; a clause-to-catalog match alone is insufficient. The external
checker includes a dropped-coverage control for that independent requirement.

The following repository-root command validates shape only, using the existing
development dependency. It performs no native execution:

```sh
python3 -B - <<'PY_SHAPE'
import json
from pathlib import Path
from jsonschema import Draft202012Validator
root = Path("conformance/profile-generations-v1")
for name in ("pairs", "a1", "reuse"):
    schema = json.loads((root / (name + ".schema.json")).read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads((root / (name + ".json")).read_text()))
PY_SHAPE
```

Before conformance can be claimed: allocate the production carriers, instantiate
the paired inputs with independent expected outcomes and preservation checks,
publish canonical/signature bytes, supply a versioned checker/control entry
point and separately authorized native plus actual consumer-adoption receipts.
Unsupported observations and missing custody remain blocked. No account,
login, credential-store, runtime or probe result is present.
