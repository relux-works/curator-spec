# Effective posture v1

[`record.schema.json`](record.schema.json) is the closed Curator carrier for
[unattended posture admission](../../protocol/effective-posture.md).
Schema validation is necessary, not permission to start: EPA01–EPA06 and
**EPA-C1** additionally bind current authority, inspection, qualification,
intent and provenance. Wire refusal codes belong to curator-run.

The complete record is CCJ-1, at most 64 KiB, depth at most 12. The SHA-256
of those exact bytes is carried by the negotiated protected launch plan;
there is no digest member inside the record. `binding.plan_sha256` identifies
the admitted Curator plan, not that outer launcher plan. Native suffix order
is significant and independently digest-bound. No legacy schema is extended.

Run the executable [paired corpus](../../conformance/effective-posture-v1/README.md)
with `python -B -m unittest discover -s tools -p 'test_effective_posture.py'`.
