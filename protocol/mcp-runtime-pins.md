# Stage-A MCP runtime-pin grammar, revision 1

This is the closed lexical sheet for the new
[Skillfile MCP lane](skillfile-mcp.md#2-closed-declaration-grammar), including
its resolved Git packages. It does not rewrite legacy `agent-mcp.json`.

The reader MUST compare the bare command literally. Commands `npx` and `uvx`
use the productions below; case variants and suffix aliases (`NPX`, `npx.cmd`,
`uvx.exe`, etc.) are refused in this lane rather than bypassing the check.
Other bare commands retain §2.2 grammar and audit/allowlist gates. A version
pin limits the direct package request; it is not a transitive dependency lock,
registry attestation, binary identity or sandbox. Never invoke a runtime while
validating it. Writer/launch qualification must establish actual execution
policy; this sheet grants no install or launch permission.

## 1. npx

Arguments are exactly `[YES?, NPM_PIN, SERVER_ARG*]`, where YES is a single
`-y` or `--yes`, present at most once before NPM_PIN. No other leading option
or alternate package/command form is admitted. Each SERVER_ARG is one opaque
argument passed after the package operand; it cannot replace the first pin.
NPM_PIN is `NAME@VERSION` or `@SCOPE/NAME@VERSION`.
NAME and SCOPE match `[a-z0-9][a-z0-9._-]*`; each is at most 214 characters.
VERSION is exactly three decimal components (`0` or nonzero digit followed by
digits) separated by `.`, with no prefix, range, tag, prerelease or build
suffix in this revision. Reject missing versions, `latest`, ranges, npm aliases,
URLs, tarballs, Git/path specs, `--package`, `-p`, `-c`, `--call` and extra
pre-operand flags. Forwarded SERVER_ARG values remain subject to length and
secret auditing; they are not a second runtime invocation.

Valid inert examples: `["-y","example-mcp@1.2.3","--stdio"]`,
`["@example/tools@0.0.1"]`. Invalid neighbors include
`["example-mcp@latest"]` and `["--package=example-mcp@1.2.3","sh"]`.
The npm [npx documentation](https://docs.npmjs.com/cli/v11/commands/npx/)
explains the positional operand/forwarded-argument distinction; the closed
productions above, not npm's larger accepted language, are normative here.

## 2. uvx

Arguments are exactly one of `[UV_PIN, SERVER_ARG*]` or
`["--from", DIST_PIN, EXEC, SERVER_ARG*]`.
UV_PIN is `DIST@VERSION`. DIST_PIN is `DIST==VERSION`.
DIST is one lowercase ASCII letter/digit, or a string beginning and ending
with `[a-z0-9]` whose intervening characters match `[a-z0-9._-]*`; maximum
214 characters;
VERSION is the same three-component decimal form as §1. EXEC is an ordinary
bare command under environments §2.2 and MUST NOT start with `-`.
All operands are separate argv strings. No extras, markers, inequalities,
`latest`, URL/Git/path sources, editable mode, `--with`, interpreter selection,
index, config or other pre-operand flags are admitted. A direct
`DIST==VERSION` operand is refused; use the unambiguous documented `--from`
form. No normalization converts a refused spelling into a grant.

Valid inert examples: `["example-mcp@1.2.3"]`,
`["--from","example-tools==1.2.3","example-mcp","--stdio"]`.
Invalid neighbors: `["example-mcp"]`, `["--from","example-tools>=1","example-mcp"]`.
The uv [tool guide](https://docs.astral.sh/uv/guides/tools/)
and [command reference](https://docs.astral.sh/uv/reference/cli/#uv-tool-run)
describe these invocation forms. This sheet intentionally admits a subset;
examples in earlier proposals do not expand it. No runtime is installed,
updated or executed by these specification checks.
