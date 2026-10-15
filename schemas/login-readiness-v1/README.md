# Login readiness revision 1 schemas

Accepted [CIP-0015 leaf 1](../../protocol/login-readiness.md) uses a separate
namespace; released core schemas remain unchanged.

| Schema | Scope |
|---|---|
| `login-row-v1` | Standalone versioned profile × environment presence row |
| `credential-store-config-v1` | User-owned `environments.credential_store` subtree |
| `store-projection-v1` | Environment/policy plus backend-literal-only env projection |

The projection omits home-path variables and is **not** a full fragment.
Containing status/config/fragment revision publication remains open. No schema
here licenses adding fields to released closed objects or qualifies a native
backend. Semantic refusal, metadata-only access, source policy and isolation
remain [normative prose](../../protocol/login-readiness.md) obligations.
Run `python3 tools/validate.py` and the [corpus checks](../../conformance/login-readiness-v1/README.md).
