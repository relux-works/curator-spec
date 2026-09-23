# TASK-260906-1xbrz6 — global takeover recovery ordering decision packet

## Constraint

Keep the orchestrator's five-operation takeover carrier set. `global add` and
`global install` remain outside it and receive no new flag. The current
§9.4/§9.5 wording points operators to `profile sync --takeover` or
`profile use --takeover`, then a retry.

## Evidence

- Environments §9.4 says direct global skill declarations are written into
the profile lock through the same resolution, and resolved skills
materialize into managed homes and the in-place surfaces of current scopes.
It does not specify whether the new lock is published before the attempted
surface writes or what lock survives a surface conflict.
- Environments §9.2 says `profile sync` reads installed profile locks and
`profile use <name>` materializes from the named profile's lock. Those
operations can replay the new declaration only if the lock containing it is
available after the failed global operation.
- Environments §9.2 does specify publish-before-rematerialize order for
`profile update` (steps 4–5), but §9.4 does not state that direct global
operations share this ordering or failure behavior.
- Environments §8.3 reports `environment_surface_unmanaged_conflict` when a
write would touch an unrecorded surface. No existing conformance family
specifies global lock publication ordering for that conflict.

No runtime failure has been observed. The gap is that the normative text
does not establish the recovery precondition: whether sync/use will see the
extended lock after the global operation reports the conflict.

## Alternatives

1. Keep the five-member set and specify that `global add`/`global install`
   publish the extended lock before in-place materialization; if a surface
   conflicts, preserve that lock so `profile sync --takeover` or
   `profile use --takeover` can materialize it before retry.
2. Keep the five-member set but specify rollback or another recovery path
   when the extended lock is unavailable; revise the blanket sync/use retry
   sentence to match that path.
3. Add a takeover flag to global operations. This widens the closed set and
   conflicts with the binding orchestrator decision, so it is not recommended
   for this task.

## Recommendation

Choose alternative 1 if it matches the intended transaction model: the five
carriers stay fixed and the already-named recovery can consume the changed
lock. State the lock publication and conflict behavior explicitly in §9.4
and the manager transaction rules. If that ordering is not intended, choose
alternative 2 and replace the unconditional recovery claim with the supported
recovery sequence; do not silently widen the carrier set.

## Exact decision requested

For `global add` and `global install`, does the specification guarantee that
the updated profile lock is published and remains available before an
in-place surface conflict is reported, so that `profile sync --takeover` or
`profile use --takeover` can materialize the updated skill set? If not, what
recovery sequence should §9.4 prescribe while retaining the five-operation
carrier set?
