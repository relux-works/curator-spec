# Decision 0014: tool-configuration surfaces

## Status

Status: proposed — not adopted

Proposed 2026-09-15. DRAFT for review under TASK-260908-1e55lp,
EPIC-260908-2wp8wn, migration workstream B7. No option is selected.
Filing this proposal authorizes no implementation, workaround, normative
amendment, or landing of the draft.

Numbering: the existing decision series ends at 0013; 0011 remains
reserved as recorded there. This B7 filing uses the next three unused
numbers, 0014–0016.

## Context

[Environments 1.1](../protocol/environments.md) §1 admits root context,
skills, and MCP declarations only; settings are explicitly outside revision
1. Section 7.4 declares a minimal written Claude `.claude.json` seed,
not a `settings.json` seed. Codex `config.toml` is copied whole once at
provisioning; later native changes are not propagated and seeds are not
hashed managed surfaces. Neither mechanism declares Codex `rules/*.rules`.
Sections 8.2–8.4 govern managed ownership and drift; §§12.1–12.2 enumerate
machine knobs and lockable policy.

The migration input is the 2026-09-07
`agents-infra-to-curator-mapping.md` precondition resource on
EPIC-260908-2wp8wn,
under “What agents-infra installs today.” It is a historical migration
inventory, not evidence of current runtime behavior. The epic's
`goal-launcher-and-infra-migration.md` precondition on the same epic,
workstream B7, asks for this gap to be filed without a workaround.

The mapping's Claude settings row carries `permissions.allow`,
`defaultMode`, `model`, and `enabledPlugins`; its Codex rules row carries
the prefix-rule allowlist. Its Codex configuration row explicitly
distinguishes the one-time seed from agents-infra's authority merge.

## Gap statement

There is no declared profile or machine surface for distributing these
settings or rules into managed homes. Reusing a seed, a context module,
or an arbitrary copied file would not establish ownership or policy.
Model defaults also overlap the launcher's responsibility recorded in
[Decision 0013](0013-execution-ownership-and-launch-plans.md), Decision 6.

## Options and trade-offs

1. **Machine-only typed configuration.** A future closed adapter-specific
   machine declaration could supply selected settings and rules. This
   keeps permission authority with the operator and permits system locks,
   but makes organization distribution a bootstrap concern and needs
   separate handling for every adapter and supported tool version.
2. **Profile declarations constrained by machine policy.** A future
   package surface could declare reviewed values or rule files, with
   machine admission and lock limits. This makes profile intent portable
   and potentially reproducible through a lock, but lets package content
   influence tool permissions and plugins; it needs a new trust boundary,
   schema, audit scope, and conflict rules.
3. **Explicit operator provisioning only.** Retain the current boundary;
   consider a separately consented seed class in a later revision. This
   minimizes continuous ownership conflicts, but later source updates do
   not propagate and configuration is not reproducible from the profile
   lock. Existing external management remains a migration residual.

## Open questions

1. Which actor owns each field: package author, system administrator,
   operator, launcher, or tool? Does launcher model selection override a
   stored model, and how is that conflict reported?
2. Are outputs whole files, typed key merges, or tool-supported layers?
   How are unknown keys, tool writes, deletion, takeover, repair, and
   rollback handled without overwriting user state?
3. Which permission and plugin fields may be locked, and can a profile
   ever weaken a machine restriction? Is plugin enablement merely a
   reference, or would it imply installation (outside this proposal)?
4. Does a profile lock bind source declarations, rendered bytes, or both?
   Where are machine overrides and adapter versions recorded? How do
   marker hashing and drift differ from one-time seeds?
5. What pinned-tool evidence establishes settings/rule precedence and
   safe update behavior before a normative amendment is considered?

## Compatibility and security impact

No schema, seed, adapter, or runtime behavior changes. Adoption would
require separately reviewed contracts and conformance for ownership,
conflicts, rejected permission escalation, and tool mutation. Generalized
plugin imports remain deferred.
