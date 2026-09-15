# Decision 0015: per-project policy and profile selection

## Status

Status: proposed — not adopted

Proposed 2026-09-15. DRAFT for review under TASK-260908-1e55lp,
EPIC-260908-2wp8wn, migration workstream B7. No option is selected.
Filing this proposal authorizes no implementation, workaround, normative
amendment, or landing of the draft.

## Context

[Environments 1.1](../protocol/environments.md) §§1 and 1.3 bind context,
skills, and MCP declarations to a profile lock. Section 1.4 preserves
the core project `Skillfile.json` contract; §9.4 defines profile skills,
and §9.3 scopes switching by adapter or target, not by project.
Sections 7.8 and 10.3 bound MCP channels and package influence;
§§12.1–12.2 place policy knobs on the machine.
[Decision 0013](0013-execution-ownership-and-launch-plans.md), Decisions
1, 5, and 6, keeps launch composition and model/effort defaults with the
launcher and permission bypass out of interactive plans.

The migration input is the 2026-09-07
`agents-infra-to-curator-mapping.md` precondition resource on
EPIC-260908-2wp8wn,
under “What agents-infra installs today.” It is a historical migration
inventory, not evidence of current runtime behavior. The epic's
`goal-launcher-and-infra-migration.md` precondition on the same epic,
workstream B7, asks for this gap to be filed without a workaround.

The mapping's project configuration and launcher rows describe ancestor
composition of `.agents/.configs/project-config.toml`: MCP opt-in,
model/effort, and yolo. Those rows have no equivalent Curator project
policy layer. The Skillfile remains a skills declaration; opt-in Skillfile
source extensions do not themselves grant MCP or launch-policy authority.

## Gap statement

A repository cannot currently express the old project policy as Curator
configuration. Selecting a profile selects its MCP set, while model and
effort remain launcher policy. Treating a Skillfile as an implicit launch
policy would cross both boundaries.

## Options and trade-offs

1. **Separate profiles per project kind now.** Operators explicitly select
   a profile with the appropriate MCP set and use existing launcher
   model/effort controls. This uses established contracts, but multiplies
   profiles and does not reproduce automatic ancestor composition or
   per-project defaults. It is an available operating choice, not a new
   automatic project selector.
2. **A project lock and separately specified policy scope.**
   [Decision 0012](0012-context-packages-and-semver-locks.md), Open
   question 6, first requires a project lock identifier, location, install
   marker relationship, and interaction with `Skillfile.dev.json`.
   That foundation could support a later project package/policy design,
   but OQ6 concerns skill ranges: a lock alone does not authorize MCP,
   model, or yolo policy. Extending scope needs another explicit decision.
3. **A launcher project layer.** A future launcher-owned declaration
   could select an installed profile and supply bounded model/effort
   preferences. This keeps process composition in one place and avoids
   widening Skillfile, but adds project discovery, trust, inheritance,
   precedence, and replay obligations. MCP selection would still need to
   resolve through the declared profile/channel contract.

## Open questions

1. Is the desired unit a repository, worktree, ancestor directory, or
   project kind? How are nested projects and symlinked launch directories
   identified without silently inheriting an unrelated policy?
2. What is the ordering among machine locks, operator defaults, project
   preferences, explicit profile selection, and CLI arguments? How does
   the launcher explain the winning source for each value?
3. Can untrusted checkout content request MCP servers or only select an
   already admitted profile? What explicit trust action admits a project
   layer, and how are unreadable or malformed files distinguished from
   absence?
4. Which identity and effective policy are recorded for reproducible
   launches and resume? How do project and profile locks interact?
5. Should project policy be allowed to request a tracked execution
   profile at all? Yolo remains unavailable in the current untracked
   scope; any future request must preserve ax ownership and must not
   synthesize bypass flags or reinterpret repository content as consent.

## Compatibility and security impact

No Skillfile, lock identifier, launcher defaults, or MCP channel changes.
Pi still has no MCP channel under environments §7.8. A future project
layer would require independent review of discovery, locked precedence,
untrusted input, and explicit execution-profile authorization.
