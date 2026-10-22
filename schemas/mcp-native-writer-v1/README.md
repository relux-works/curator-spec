# Profile MCP native writer private carriers, revision 1

The [adaptation sheet](../../protocol/mcp-native-writer.md) defines this separate
`profile-mcp-native-writer-v1` namespace. It changes no released marker/lock,
project `mcp-approval-v1` or Skillfile parser dispatch.

- `ownership-v1.schema.json`: protected profile/environment/path record ledger;
  NAME-sorted unique records, each marked `owner: curator` and bound to exact
  native entry bytes plus server/content identities.
- `action-v1.schema.json`: protected explicit package ownership action bound to
  profile/environment/path/NAME, desired or previous identities as appropriate,
  operation, approver, current effective policy digest and active state.

Use strict CCJ-1 JSON with true-end scalar/path/digest checks. Ownership records
must be sorted and unique; consumers recompute installed-byte digests against
real native observations. Schema validity is not protected provenance or
permission. Require the current manager-store protections, source/policy/action
revalidation and no-follow transactional publication at real consumers.
The separate model checker validates semantic bindings and named refusal
controls; it never writes native files or qualifies a vendor runtime.
