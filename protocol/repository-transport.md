# Repository transport revision 1 (unreleased)

This normative opt-in `repository-transport-v1` amendment is separate from
[local source acquisition](skillfile-sources.md). It specifies machine endpoint
selection for new Skillfile sources and for existing Git acquisition lanes only
when the manager explicitly supports this amendment. It does not change legacy
wire schemas or broaden a lane's admitted endpoint grammar. It is not a
published release or an implementation claim.

## 1. Identity and declarations

Canonical repository identity remains core 6.1 `host/path`: lowercase host,
case-sensitive repository path, one terminal `.git` removed, no transport or
SSH username. A canonical identity MUST already be normalized, non-empty and
valid under that grammar. Dot/parent components, ports, mirrors and aliases do
not become valid through this amendment. URL declarations are checked against
their lane's existing grammar before canonicalization.

In a new source object, `repository: "github.com/acme/kit"` is the explicit
logical form. It cannot be confused with `path: "github.com/acme/kit"`, which
is filesystem acquisition. `git` and `repository` are mutually exclusive.
A supported `git` URL supplies identity and a default connection hint, not a
transport pin. Exact ref and lock requirements remain independent of transport.
No shared field may contain a password, token or credential-provider reference.
SSH usernames allowed by the existing grammar are connection labels, not
repository identity or authorization grants.

## 2. Machine policy and bounded resolution

The operator-owned `source-policy.json`, stored with machine configuration
outside package-controlled trees, conforms to source-policy schema 1. It is
optional for URL declarations; absent an entry, attempt the declared endpoint
once with existing lane policy and no fallback. A logical declaration without
an entry fails `repository_endpoint_unavailable`. Invalid or unreadable policy
fails `repository_policy_invalid`; it is never treated as absent.

A `repositories` entry is keyed by exact canonical identity. `endpoints` is an
ordered list of one or two distinct HTTPS/SSH endpoints, each with an opaque
`authentication` provider identifier referring to an already configured,
operator-owned provider (including an explicitly configured anonymous provider).
Each endpoint MUST independently canonicalize to the exact key. Repeated URLs,
identity mismatch, unsafe grammar or a pin not equal to a listed URL fails
before network I/O. Provider identifiers resolve only through operator
configuration; they are neither commands nor package-supplied executable paths.

Without `pin`, use list order. `pin` selects exactly one listed endpoint and
forbids fallback irrespective of the `fallback` value. A URL hint never reorders
an explicit machine list. No policy entry permits generating alternative URLs,
probing other accounts, following redirects or inferring a mirror from a matching
commit. A listed endpoint outside a stricter acquisition lane's grammar is an
error, not a skipped candidate.

There is at most one attempt per listed endpoint (maximum two total), no
implicit retry, and the existing lane's total deadline includes both attempts.
`fallback: "none"` permits only the first; `availability-auth` permits the next
only after a positively classified availability/authentication failure:

| Failure | Alternate endpoint |
|---|---|
| DNS failure, connection refused/timeout, endpoint unavailable (HTTP 502/503/504) | Allowed by `availability-auth` only |
| Operator authentication method unavailable or explicit authentication rejection (HTTP 401/403, SSH authentication rejection) | Allowed by `availability-auth` only |
| TLS certificate or SSH host-key validation failure | Forbidden |
| Wrong identity, redirects/remapping, malformed/unreadable policy | Forbidden |
| Missing/moved ref, missing commit, object/hash/integrity mismatch | Forbidden |
| Audit denial, revocation, canary, assurance or capability failure | Forbidden |
| Unclassified failure, ambiguous HTTP 404, partial/malformed response | Forbidden |

An authentication fallback grants no additional rights; the alternate must
independently authenticate and prove the same identity and locked content.
No interactive credential discovery occurs in a headless run. Exhaustion returns
`repository_endpoint_unavailable` with sanitized attempt classifications and
operator remediation. Fail-closed classes retain the lane's specific diagnostic
and terminate acquisition without alternate network traffic or a cache shortcut.

## 3. Security and external builds

Allowlist/trust checks use stable identity before acquisition. Successful
acquisition still must verify the full locked object-format/commit, exact tag
when declared, objects, snapshot and audit evidence. Same commit bytes alone
never establish repository equivalence. Transport choice is not part of the
portable Skillfile lock or package identity. Store sanitized endpoint provenance
in machine-private operation diagnostics, separately from portable identity.

User Git/SSH configuration is usable only through explicit operator admission.
This revision supports endpoint URLs and authentication-provider selection only;
it does not import `insteadOf`, `ProxyCommand`, `core.sshCommand`, helpers,
include files, environment overrides, host aliases or arbitrary remapping.
Credentials remain in the existing trusted broker. Do not export or persist
secrets in manifests, locks, receipts, logs, command arguments or compiler
worker environments. No fallback disables certificate or host-key validation.

Manager section 11 remains stricter: the trusted Git distribution, clean
configuration/environment, closed process graph, SSH wrapper, per-host broker,
exact-ref fetch, raw-object parser and no-package-execution boundaries remain
mandatory for every endpoint attempt. Auth-provider admission feeds that broker,
not Git helper execution or compiler inheritance. In external build receipt
inputs, existing declared/effective transport fields still record the actual
permitted endpoint transport and can change a receipt/cache key across machines;
this does not change repository identity or pinned content. Do not remove those
fields to force cross-transport cache reuse. Existing committed-HEAD development
substitutions keep their own rules and strict-audit rejection.

This revision adds no new fields to published skill build repositories or other
package manifests. Such lanes can use their existing URL declaration and an
admitted machine policy; the logical `repository` spelling is admitted only in
new Skillfile source objects. Advanced mappings remain explicitly undecided in
[UNRESOLVED_QUESTIONS.md](../UNRESOLVED_QUESTIONS.md).
