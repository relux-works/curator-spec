# Repository transport revisions 1 and 2 (unreleased)

This normative opt-in `repository-transport-v1` amendment is separate from
[local source acquisition](skillfile-sources.md). It specifies machine endpoint
selection for new Skillfile sources and for existing Git acquisition lanes only
when the manager explicitly supports this amendment. It does not change legacy
wire schemas or broaden a lane's admitted endpoint grammar. It is not a
published release or an implementation claim.

Revision 1 is specified in sections 1–3 below and is unchanged by revision 2.
Revision 2 (sections 4–7) is a separately scoped normative opt-in
`repository-transport-v2` amendment deciding the advanced endpoint mappings
that revision 1 left undecided. A reader MUST explicitly support each revision
it accepts; revision 1 support alone MUST NOT accept revision 2 policy.

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
new Skillfile source objects. The advanced endpoint mappings (non-default
ports, mirrors, host aliases) are decided by revision 2 below; the remaining
open items are tracked in
[UNRESOLVED_QUESTIONS.md](../UNRESOLVED_QUESTIONS.md).

## 4. Revision 2 scope and schema versioning

Revision 2 decides the advanced endpoint mappings that revision 1 left
undecided: explicit non-default ports on listed endpoints, operator-declared
mirrors, and operator-declared host aliases. It specifies machine endpoint
properties only; like revision 1 it applies to new Skillfile sources and to
existing Git acquisition lanes only when the manager explicitly supports this
amendment. For the strict external-build lane (manager section 11) only the
port-free, alias-free subset applies: endpoints with an explicit port (URL
port or alias port) or an `alias` field are refused there with the lane's
grammar diagnostic (section 7) and are admitted only for Skillfile source
acquisition, while mirror endpoints without ports or aliases are ordinary
section 11.2 URLs and remain admissible with identical verification. It is
not a published release or an implementation claim.

Source-policy schema 2 (`source-policy-v2.schema.json`,
`schema_version: 2`) is a new file and an additive superset of schema 1: every
schema-1 `repositories`/`root_inputs` shape is valid under schema 2 with
`schema_version: 2`, extended with optional per-endpoint `mirror_of` and
`alias` fields, an optional top-level `aliases` table, and an endpoint/`pin`
URL grammar admitting explicit ports. A new `schema_version` value is used
instead of optional fields under schema 1 because the version is a const
discriminator: forking the shape under one value would split the meaning of
"schema 1", while a revision 1 reader already fails a schema-2 document closed
(`additionalProperties: false` and the const reject unknown members and the
unknown version) instead of silently ignoring endpoint properties it cannot
enforce. Schema 1 is byte-unchanged. A revision 2 reader MUST also accept
schema-1 documents with revision 1 semantics; a revision 1 reader MUST reject
a schema-2 document as `repository_policy_invalid` before any network I/O.

No other schema changes: Skillfile schema 2, lock schema 1, marker schema 5,
receipt schema 3, audit schema 1, every published manifest and every lane
declaration grammar are unchanged. Core sections 6.1 and 6.3 are unchanged:
ports, mirrors and aliases do not widen any acquisition lane's admitted
declaration grammar. For a lane used under revision 2, the lane grammar still
governs package declarations while the endpoint grammar of section 5 governs
listed policy endpoints. A listed endpoint whose transport form or path
characters fall outside the lane's grammar remains an error per revision 1,
not a skipped candidate.

## 5. Revision 2 identity, ports, mirrors and host aliases

Canonical `host/path` (lowercase host, no port, no username, no terminal
`.git`) remains the only portable repository identity. Ports, mirrors and
aliases are machine-policy endpoint properties and MUST NOT enter package
manifests, the portable Skillfile lock, receipts' portable identity, marker
package identity, or allowlist matching; allowlists match canonical identity
only. A port MUST NOT change receipt or cache identity beyond the existing
declared/effective `https`/`ssh` transport enum: it is a connection property
of the same endpoint transport, and the verified content (locked commit) is
identical.

An `endpoints[]` URL or `pin` MAY carry an explicit port only in URI form:
`https://host[:port]/path` and `ssh://[user@]host[:port]/path`, where the port
is decimal `1`–`65535` with no leading zeros. All other revision 1 URL rules
are unchanged: no userinfo on HTTPS, optional ASCII SSH username, no dot
components, no query/fragment/escapes. Scp-like `git@host:path` carries no
port; the segment after `:` is always the path, so `git@host:2222/repo.git`
names path `2222/repo.git`, never port 2222. Canonicalization strips an
explicit port first and then applies the core 6.1 rules; the stripped endpoint
still MUST satisfy the section 6 checks against the exact entry key. `pin`
comparison is exact listed-URL string equality with the port included, so a
pin that differs only by port fails before network I/O. An endpoint with an
explicit port MUST NOT be selected for the strict external-build lane
(manager section 11); section 7 states the refusal.

An endpoint is a mirror when its resolved connection host (lowercased)
differs from the entry-key host. The resolved connection host is the alias
target host when the endpoint names an `alias`, else the endpoint URL host.
Repository identity for the entry is always the entry key: a mirror host is
a connection address only and MUST NOT enter portable identity, the lock,
receipts, markers or allowlist matching. The port-stripped canonical path
of every endpoint, mirror or not, MUST equal the key path; only the host
may differ, and only when attested. A mirror is admitted only when the
entry lists its URL explicitly under that exact canonical key with
`mirror_of` equal to the key exactly. `mirror_of` MUST be present if and
only if the resolved connection host differs from the key host: a
differing resolved host without it fails
`repository_mirror_undeclared`; a value not equal to the key, or a
spurious attestation when the resolved host equals the key host, fails
`repository_policy_invalid`. In particular: a canonical-URL endpoint
routed by alias to another host requires `mirror_of`; a same-host alias
(alias target host equals the key host) forbids it; and a mirror URL (URL
host differs from the key host) MUST NOT be combined with an `alias` at
all — such an endpoint fails `repository_policy_invalid`, since its URL
host would be neither identity nor connection address. Mirrors are
ordinary endpoints once declared: a mirror MAY be first in list order,
and `pin`/`fallback` semantics are unchanged from revision 1. The manager
MUST verify the locked commit and exact tag objects for a mirror
identically to revision 1, and MUST NOT infer, generate, or discover
mirrors: no generated URLs, no probing, no redirect-following to an
unlisted host. A mirror attestation authorizes the resolved connection
host only.

Host aliases are declared only in the operator-owned `aliases` table mapping
an alias name to `{host, port?, authentication}`: a concrete target host, an
optional port `1`–`65535`, and the authentication provider for connections via
this alias. Alias names and target hosts MUST be lowercase
`[a-z0-9][a-z0-9.-]*` and match case-sensitively and exactly. An endpoint
names an alias only through its `alias` field; a URL host that equals an alias
key fails `repository_policy_invalid` and is never substituted implicitly. At
most one substitution applies: the connection goes to the alias host with the
alias port when present, else the URL port when present, else the transport
default. The alias target MUST be concrete: a target that is itself an alias
key (chaining) fails `repository_policy_invalid`. A URL port and an alias
port MUST NOT both be present. The alias `authentication` MUST equal the
endpoint `authentication`: one provider per attempt, with no precedence rule
to misimplement. An `alias` that names no table entry fails
`repository_alias_unknown`. Repository identity is always the entry key,
never the URL host or the alias target; the URL path MUST equal the key
path and, when an `alias` is named, the URL host MUST equal the key host
(a mirror URL combined with an `alias` is refused as stated above).
Whether `mirror_of` is required follows the single resolved-host
predicate above and MUST NOT be re-derived from the URL host alone. An
endpoint naming an `alias` MUST NOT be selected for the strict
external-build lane (manager section 11); section 7 states the refusal.
Package declarations stay canonical and
logical: Skillfile `git`/`repository` fields and legacy lane declarations
MUST NOT name aliases. User `~/.ssh/config` Host aliases, `insteadOf`,
`ProxyCommand`, `core.sshCommand`, helpers, include files and environment
overrides remain NOT imported.

An endpoint written in SCP-like form (`[user@]host:path`) has no URI port
position. If its named alias supplies a port, the manager MUST fail with
`repository_policy_invalid` before network I/O. Converting it to an SSH URI
would require a `~/` remote-path convention that some SSH front ends do not
accept, so the manager MUST NOT guess that rendering or risk changing the
target path. An SSH URI endpoint MAY use an alias port; its connection target
is the SSH URI with the resolved alias host and port, while the repository
identity remains the entry key.

## 6. Revision 2 resolution, failure classes and attempt bounds

Resolution for a schema-2 entry runs in this order, with every structural
check failing before any network I/O for the entry: validate the policy
document (invalid or unreadable fails `repository_policy_invalid`, never
treated as absent); select the entry by exact canonical identity (absent
entry keeps revision 1 behavior); per endpoint in list order, validate the
section 5 URL grammar, reject an embedded alias host, resolve the `alias`
field, refuse a mirror URL combined with an `alias`, canonicalize the URL
with the port stripped and require the path to equal the key path, derive
the resolved connection host, and apply the single `mirror_of` predicate;
then apply `pin` selection. `pin` selects exactly one
listed endpoint by exact string equality and forbids fallback irrespective of
the `fallback` value. A URL hint never reorders an explicit machine list.

There is at most one attempt per listed endpoint (maximum two total), no
implicit retry, and the existing lane's total deadline includes both attempts.
The two-endpoint cap is unchanged from revision 1: ports, mirrors and aliases
are properties of an endpoint, not new failure classes needing more attempts,
so raising the cap would widen the network blast radius and invalidate
revision 1 deadline accounting without authorizing any new identity. The
revision 1 failure-classification table applies unchanged, extended only by
these fail-closed rows (zero attempts, no fallback, no cache shortcut):

| Failure | Result |
|---|---|
| Resolved connection host differs from the key host without `mirror_of` | `repository_mirror_undeclared`, forbidden |
| `alias` names no entry in the policy alias table | `repository_alias_unknown`, forbidden |
| `mirror_of` or alias misuse (`mirror_of` mismatch, spurious attestation, mirror URL combined with an alias, embedded alias host, chained alias, double port, authentication mismatch, pin mismatch, SCP-like endpoint with alias port) | `repository_policy_invalid`, forbidden |

Mirror, port and alias properties add no fallback-allowed class: a declared
mirror or aliased endpoint that fails with an availability/authentication
error follows the ordinary revision 1 `availability-auth` rule, and every
fail-closed class terminates acquisition without alternate network traffic.

## 7. Revision 2 secrets, provenance, compatibility and external builds

Secret handling is unchanged from revision 1: no passwords, tokens, or
credential references in shared or policy objects; credentials stay in the
existing trusted broker; nothing is exported or persisted in manifests,
locks, receipts, logs, command arguments or worker environments; no fallback
disables certificate or host-key validation.

Sanitized endpoint provenance, including the listed URL with its port, the
resolved connection host and port, the alias name when used and the
`mirror_of` attestation when used, is recorded in machine-private operation
diagnostics only, separately from portable identity. It MUST NOT enter the
lock, receipts, markers, manifests or any portable artifact.

Compatibility: revision 1 readers reject schema-2 documents closed; revision
2 readers accept schema-1 documents with revision 1 semantics; schema 1,
locks, manifests and receipts are unchanged, so portable artifacts stay
identical across machines regardless of endpoint properties. No acquisition
lane declaration grammar is widened.

In external build receipt inputs the existing declared/effective transport
fields keep recording the actual permitted endpoint transport (`https`/`ssh`)
with no port field added. Manager section 11 remains stricter: the trusted
Git distribution, clean configuration/environment, closed process graph, SSH
wrapper, per-host broker, exact-ref fetch, raw-object parser and
no-package-execution boundaries remain mandatory for every revision 2
endpoint attempt. Revision 2 does not extend the section 11.2 URL grammar
or the section 11.3 SSH wrapper: when the target lane is the strict
external-build lane, a selected endpoint with an explicit port (URL port
or alias port) or an `alias` field fails
`build_repository_identity_invalid` before network I/O — a port violates
section 11.2's no-explicit-port rule, and alias rewriting has no
resolved-host input in the lane's closed validated-URL/host tuple. The
manager MUST NOT strip the port or ignore the alias to force admission.
A mirror endpoint without ports or aliases is an ordinary section 11.2
URL and remains admissible with verification identical to revision 1.
Auth-provider admission feeds that broker, not Git helper execution or
compiler inheritance. Existing committed-HEAD development substitutions
keep their own rules and strict-audit rejection.

Conformance vectors live under
[the draft source namespace](../conformance/draft-sources-v1/README.md):
schema cases in `schema-cases/source-policy-v2/` (four positives: port,
declared mirror, alias resolution, revision-1 shape under schema 2; nine
negatives: unknown top-level member, out-of-range port, SSH upper-bound
port, leading-zero port, malformed `mirror_of`, malformed alias name,
alias missing authentication, string alias port, extra endpoint member)
indexed in `index.json`, and `semantic-cases.json` cases
`v2-port-endpoint`, `v2-declared-mirror`, `v2-mirror-first`,
`v2-alias-resolution`, `v2-reader-accepts-v1-policy` and
`v2-external-build-mirror-admitted` (positive) and
`v2-undeclared-mirror`, `v2-pin-port-mismatch`, `v2-alias-unknown`,
`v2-alias-mirror-undeclared`, `v2-user-ssh-alias-ignored`,
`v2-user-insteadof-ignored`, `v2-embedded-alias-host`,
`v2-alias-auth-mismatch`, `v2-alias-chain`, `v2-double-port`,
`v2-spurious-mirror-of`, `v2-mirror-of-mismatch`,
`v2-v1-reader-rejects-v2-policy`, `v2-external-build-port-refused` and
`v2-external-build-alias-refused` (refusal). No manager implementation or
release qualification is claimed.
