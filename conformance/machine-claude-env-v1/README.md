# Machine Claude environment proposal corpus

This corpus is outside the frozen release manifest. It checks the
[proposed contract](../../protocol/machine-claude-env-proposal.md), not an
implementation or real runtime. Inputs are synthetic and contain no native
settings, environment dump or authentication material.

Run from the repository root:

```bash
go run ./tools/validate-claude-env -root .
go test ./tools/validate-claude-env
```

`cases.json` binds an independently stated claim, a real JSON Schema verdict
and a specific semantic verdict to each input. `plants.json` starts from a
valid declaration or contribution and introduces one defect per required
vector: unknown name, non-integer, zero, negative, over-bound and non-Claude
injection. Each plant must reach its intended refusal; its adjacent valid
control must pass. Tests also plant wrong corpus expectations to establish
that the checker detects a false acceptance and a false rejection, runs later
cases, and returns an aggregate failure.

The schema checks and semantic checks intentionally differ for duplicate JSON
members: JSON Schema sees a decoded object, while the strict byte decoder must
reject duplicates. Other refusal-class mismatches or setup failures are not
successful controls. The command prints only fixture IDs and stable codes,
never input values or raw parser/schema errors. This does not prove production
diagnostic redaction, no-write/no-child invariants or actual output spilling.

The future implementation must run the actual selected parser/editor/status,
projection, child launch/resume and real-runtime witnesses in contract section
5. No such runtime case is measured by this corpus.
