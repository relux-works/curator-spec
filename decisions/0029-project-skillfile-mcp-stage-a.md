# Decision 0029: project Skillfile MCP declarations, package-first stage A

## Status

Status: accepted

The operator accepted CIP-0022 on 2026-10-22 with its recommended staged
boundary; this record publishes implementation-plan leaf 2. Decision 0028 is
allocated separately to CIP-0002. The CIP's acceptance/status record is owned
by a separate task and is not edited here.

## Context

Skillfile schema 2 already binds skills, source aliases and immutable package
snapshots. Project MCP declarations need explicit version dispatch, package
trust, distinct normalized identities and per-record native ownership rather
than implicit authority from project bytes. Inline admission requires
CIP-0002's protected project contributions and cannot ship by parsing alone.

## Decision

1. Adopt [project Skillfile MCP stage A revision 1](../protocol/skillfile-mcp.md)
   and its [closed runtime-pin sheet](../protocol/mcp-runtime-pins.md).
   Schema 3 inherits schema 2 and adds optional `mcp_servers`, project scope
   only. Unsupported/global readers fail with the existing upgrade error;
   writers never implicitly upgrade a manifest.
2. Publish Git `agent-mcp.json` declaration packages first, using existing
   source safety/allowlist, MCP package allowlist, signer/revocation and strict
   audit gates. Every inline arm refuses `mcp_inline_approval_unsupported`,
   even if a project supplies a purported approval. There is no Skillfile
   audit waiver.
3. Reserve stage-B authority for a protected approval bound to the
   manager-registered project identity, NAME and normalized server digest,
   approver and current fleet/manager ceiling. Syntax-only edits with equal
   normalized identity do not authorize changed endpoints, arguments or env
   names. No accepted stage-A inline approval instance exists. Future
   effective auth/header options require their own approval binding.
4. `install` has no standardized nested grammar; stage A ignores every option
   and names it in the plan without values. Audit still covers all of it.
   A separately accepted supported-option contract is required before a
   writer can honor it or emit `mcp_install_option_invalid`.
5. Publish separate complete schema-3, stage-A lock, protected package
   ownership-action authorization and plan carriers, plus a separate vector
   namespace. Never extend a closed released carrier or alter core/source
   release pins. Preserve distinct manifest/server/declaration/plan identities.
6. Native writes use per-record protected ownership and a complete no-follow
   transaction. Foreign same-name entries are conflicts. Requirement checks
   remain read-only. The first adoption wave is Claude, Codex and Muse, each
   requiring actual writer/platform qualification before advertising support.
   Native configuration success is not managed-launch qualification.

## Alternatives

- Inline first or plain-URL implicit approval: rejected because project bytes
  cannot grant executable/control authority or bypass package allowlisting.
- Standardize auth/headers/scope now: rejected; their effective-control and
  secret authority need a separate typed contract.
- Rewrite schema-2 locks or accepted conformance pins: rejected to preserve
  partial-client independence and released byte identity.
- Treat runtime pins as transitive locks or executable attestations: rejected;
  the closed lexical sheet limits direct requests and claims no such proof.

## Compatibility and security

Schema 1/2, released MCP packages and source/profile locks retain their bytes
and meanings. Only the new schema-3 lane adds lexical/pin restrictions to its
resolved packages. Known unwritable environments report a skip, unknown ids
refuse. No server/runtime, endpoint connection or authentication is started
by parsing, planning, audit, status or requirement checking. Secret findings
remain blocking; no ordinary pin clears them. Store protection, race handling,
rollback, protected approvals and managed isolation require real consumer
qualification; structural and synthetic vector success cannot establish them.
