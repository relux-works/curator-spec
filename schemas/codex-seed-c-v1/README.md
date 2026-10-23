# Codex seed-C marker schema

The [normative amendment](../../protocol/codex-seed-c.md) allocates the complete,
unreleased Draft 2020-12 `agent-environment-marker-v7.schema.json`, extending
marker 6 only with discriminator 7 and seed revision C. All prior schemas
remain unchanged. The relocated node-source reference explicitly targets
`../local-setup-token-v1/node-source-v1.schema.json`; its inherited semantics
are unchanged. A/B records remain representable; their presence does not
authorize seed refresh or project-trust migration. Package settings remain
empty-only. The schema cannot prove adapter identity, path privacy, mutation
discipline or filesystem preservation; those are normative semantic rules.

Run the [corpus checks](../../conformance/codex-seed-c-v1/README.md). Inputs and
expected outcomes are public synthetic data; no native home is inspected.
