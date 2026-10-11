# CIP figure sources

These are source views of the current CIP text, not runtime qualification. Phase, process identity, persistent-state authority and refusal/recovery appear in each view. Unknown formats, UIDs and retention rules are marked where the defining specification is silent. B activation stays disabled. PlantUML uses local basic syntax without themes, includes or a renderer dependency. The existing C4 source is retained and extended alongside the PlantUML component view.

| Figure | Source | Defining specification | Audit row |
|---|---|---|---|
| Donor components (C4 retained) | [donor-side.dsl](donor-side.dsl) | [D0–D3, D5, D12](../CIP-0009-donor-side-deployment-and-bridge.md#recommendation) | M-CIP1 |
| Donor components (PlantUML) | [donor-side.puml](donor-side.puml) | [D0–D3, D5, D9, D12](../CIP-0009-donor-side-deployment-and-bridge.md#recommendation) | M-CIP1 |
| First deployment | [donor-first-deployment.puml](donor-first-deployment.puml) | [D0–D4, D9–D10, D12](../CIP-0009-donor-side-deployment-and-bridge.md#recommendation) | M-CIP1 |
| Join handshake | [join-handshake.puml](join-handshake.puml) | [D4, D6, D9, D12](../CIP-0009-donor-side-deployment-and-bridge.md#recommendation) | M-CIP1 |
| Remote-worker turn | [remote-worker-turn.puml](remote-worker-turn.puml) | [D0–D5, D12; CIP-0008 R3/R5/R9](../CIP-0009-donor-side-deployment-and-bridge.md#recommendation) | M-CIP1 |
| Retirement sequence | [remote-worker-retire.puml](remote-worker-retire.puml) | [D7, D12](../CIP-0009-donor-side-deployment-and-bridge.md#recommendation) | M-CIP1 |
| Deployment variants | [donor-variants.puml](donor-variants.puml) | [D0–D3; CIP-0008 R9](../CIP-0009-donor-side-deployment-and-bridge.md#recommendation) | M-CIP1 |
| Independent lifecycle axes | [donor-lifecycle.puml](donor-lifecycle.puml) | [D7, D12](../CIP-0009-donor-side-deployment-and-bridge.md#recommendation) | M-CIP1 |
| State layout | [donor-layout.puml](donor-layout.puml) | [D0–D3, D5, D7, D12](../CIP-0009-donor-side-deployment-and-bridge.md#recommendation) | M-CIP1 |
| Credential source lifecycle | [credential-source-lifecycle.puml](credential-source-lifecycle.puml) | [C1–C6, Revision 2.2; CIP-0003 migration; CIP-0011 §2/§3](../CIP-0010-credentials-setup-token-and-inherited-auth.md#recommendation) | M-CIP2 |
| Configuration publication | [configuration-publication.puml](configuration-publication.puml) | [CIP-0002 admission/leases/PATH; CIP-0004 recommendation/migration; CIP-0006 design/migration](../CIP-0002-project-context-in-managed-launches.md#recommendation) | M-CIP2 |
| Tool admission | [tool-admission.puml](tool-admission.puml) | [Operator decision, option B, recommendation/security; shared D-PATH](../CIP-0007-manager-provisioned-cli-tools.md#recommendation) | M-CIP2 |
| Audit transport | [audit-transport.puml](audit-transport.puml) | [Recommendation §§1–7](../CIP-0005-audit-backends-and-cli-secret-transport.md#recommendation) | M-CIP2 |

Audit: [B4 M-CIP1/M-CIP2](https://github.com/relux-works/curator/blob/48789217/.research/261010_platform-docs-audit.md#b4-missing-or-insufficient-module-diagrams--exact-proposed-files). The current CIPs and [shared disposition](../platform-contract-disposition.md) include later owner decisions; the pinned [contract table](https://github.com/relux-works/curator/blob/177cb554/.research/261010_platform-contract-table.md) supplies the baseline. No render, test, build or native qualification was run by this documentation author; handoff owns configured CR validation.
