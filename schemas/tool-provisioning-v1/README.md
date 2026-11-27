# Tool provisioning schemas (v1)

This directory defines the additive v1 schemas for
[manager-provisioned CLI tools](../../protocol/tool-provisioning.md)
([CIP-0007](../../cips/CIP-0007-manager-provisioned-cli-tools.md)) and
[manager-provisioned Go toolchains](../../protocol/go-toolchain-provisioning.md)
([CIP-0040](../../cips/CIP-0040-manager-provisioned-go-toolchain.md)):

- `agent-skill-v10.schema.json`: skill manifest schema 10 adding
  `dependencies.tools` while keeping schemas 1 through 9 byte-unchanged.
- `csk-skill-v10.schema.json`: legacy filename alias for schema 10.
- `tool-receipt-v1.schema.json`: sealed store receipt written alongside every
  manager-provisioned tool or Go toolchain under `<manager-home>/tools/store/`.
