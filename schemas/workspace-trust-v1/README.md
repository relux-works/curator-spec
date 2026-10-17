# Private workspace trust record v1

Unreleased [environments A1](../../protocol/environments.md#710-workspace-trust-ledger)
record; not a profile member, wire fragment, marker or export extension.
The closed [record schema](workspace-trust-record-v1.schema.json) describes
one operator event and, for a bind, one environment-specific reference.
`state_history` retains previous states in order; `state` is the latest state.
Initial history is empty. Event fields and historical transitions are immutable.
The containing private journal enforces unique grant IDs and one effective
reference per binding/environment/root; it is not a portable carrier.

JSON Schema admission requires a date-time format checker. Structural path
and URL shapes alone cannot prove exact admission, absence of secrets or
filesystem identity. The accompanying semantic checker rejects broad and
noncanonical path spellings, credential-bearing remotes, source paths outside
the repository and contradictory transition history. Implementations additionally
validate actual directory kind, every component without following links, private
ownership/permissions, metadata discovery, journal recovery and race safety.
Known explicit non-repository events omit `repository`; unknown discovery is
never represented by omission. No-remote repositories use JSON `null`.
Root object IDs admit SHA-1 and SHA-256; timestamps are UTC `Z`.

Schema and executable-vector checks run through `make validate` and
`python3 tools/workspace_trust.py`. Fixtures live in
[`conformance/workspace-trust-v1`](../../conformance/workspace-trust-v1/README.md).
Logs go under `.temp/`; these checks qualify no Curator or vendor runtime.
