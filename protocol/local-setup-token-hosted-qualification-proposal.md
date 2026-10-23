# Hosted-station setup-token qualification proposal

**Status: proposed contract, not activation.** The accepted
[local-source revision 1](local-setup-token-source.md) remains unchanged. This
standalone amendment proposes the additional qualification
requirements for a long-lived Claude station on the same host and UID as its
enrolled source. It does not publish a hosted carrier, implement the source
store/API, qualify a provider, or lift the hosted/Terminal refusals in
[revision 1 section 7](local-setup-token-source.md#7-entry-point-and-qualification-l7).
The requirements below apply to a future jointly adopted hosted route; until
its publication and behavioral qualification, node-source hosting MUST remain
unavailable, with no manager contact or native/per-home fallback.

## 1. Dependency and ownership boundary

The proposal relies on the following source snapshots, not on inferred runtime
support. Re-pin the owning contracts when admitting an implementation or
qualification tuple; do not treat a branch name or a newer draft as authority.

| Dependency | Inspected revision and boundary |
|---|---|
| CIP-0010 and local source | [Spec a77686c8](https://github.com/relux-works/curator-spec/tree/a77686c8112d60841236f2107d7e085e48361f6e): CIP-0010 Draft revision 4 and local-source revision 1. Revision 1 sections 2, 6 and 8 retain custody, protected binding and the in-process final boundary. |
| Station account, keys, paths and lifecycle | [CIP-0024 Draft fb4e16ab](https://github.com/relux-works/curator-spec/blob/fb4e16abe1cf4aa2c87e01a87203134b4f06b6b9/cips/CIP-0024-agent-stations.md): one OS account per station; separate account/key and home/composition owners; protected assignment, fenced lifecycle and unknown-state retention. This draft publishes no station wire or live capability. |
| Hosted lifecycle and exact process | [Local hosting](local-hosted-launches.md) and [CIP-0023](../cips/CIP-0023-exact-plan-hosted-launches.md) at a77686c8: preserve their selection, preparation, exact-process, original-home/session-lease, resume and recovery gates. |
| Launcher companion | [FRONT-DOOR section 9 and Appendix B at 60143fec](https://github.com/relux-works/curator-agent-launcher/blob/60143fec205e21a7b7ec98674f6e48cd646db22a/FRONT-DOOR.md): hosted node source is refused; the per-session final-owner amendment is proposed, not qualified. |

The station owner must publish the relied-on account/UID, platform-owned versus
station-writable path, protected trust/key and lifecycle bindings before their
use in a live tuple. CIP-0024's inspected key-custody interim is not a grant to
choose a successor signer, key backend or writable trust path here. This
amendment allocates none of those interfaces, nor station-record, role,
raise-by-card, a2a/profile-link or product-card fields. An unresolved normative
choice stays an explicit owning dependency; it cannot become a local workaround.

Before implementation, identify the writers and published pins for T1/T2
custody/policy, T3a `pkg/localcredential`, and launcher/manager consumption.
The specification of `AuthorizeAndStart` is not an available module pin.
Acceptance of this text does not assign those implementations or silently
include them in an injection-only change.

## 2. Account-local source and profile continuity

A station has a distinct OS account from the outset. The source and final
executor MUST use that station's admitted UID and local host binding. The
human's separately authorized enrollment occurs in the destination account;
neither a raising orchestrator nor a manager copies an operator's source,
`source_ref`, HOME, native login, token, private key or trust state into it.
No cross-UID broker, account allocator, privilege-escalation helper or token
transport is admitted by this local-source amendment.

Preserve the admitted role-profile source, dependency closure and lock unless
a separately reviewed pin/closure change is intentional. Matching profile or
lock bytes are configuration identity, never credential or OS-account
authority. Reject unexpected profile drift without silent repair, repinning,
old-HOME reuse or account creation. Source selection remains user-owned machine
configuration; a profile, product card or package cannot select credentials.

Before a later native migration admission, its owning private task records
old and target host/account, profile source/revision/closure/lock, managed
HOME, lifecycle owner and current execution generation. It also records the
destination's supported cache/root layout, protected source/binding metadata
and approved enrollment route, without material or material digests. Explain
legitimate account-dependent rendered-path/context differences: neither copied
root hashes nor unexplained new hashes prove the destination boundary.
Do not populate real continuity rows in this shared specification or corpus.

Cache access and private Git administration require their owning supported
cross-account contracts. A writable shared cache or operator Git back-link is
not assumed. Unsupported destination cache/HOME/root layout refuses before
start without changing either account's existing state. Same-UID workers and
copied roots MUST NOT be reported as account-isolated stations.

## 3. Proposed hosted final boundary

Only the per-session final-process owner executing as the enrolled station UID
may call the Curator in-process `AuthorizeAndStart` boundary. The shared daemon
does not retrieve, retain or distribute material; no callback into a daemon,
token getter, caller-sealed secret, wrapper or per-home fallback substitutes
for that boundary. The trusted Claude process intentionally sees its token;
this does not claim secrecy from the harness or a compromised same-UID process.

Launcher and receiver owners must jointly publish the full hosted carrier and
its canonical digest coverage before emission. It binds the requested source
projection, admitted profile/lock, station/execution identity and generation,
non-secret invocation, route/mode and IO to the owning preparation/lifecycle
contract. These are required semantic bindings, not new JSON field names or
permission to extend `local-final-exec-v1` or another closed carrier. A plan's
source or capability declaration remains requested intent, not authority.

The final owner compares the requested source projection with its own Curator
resolve; source/reference/generation drift refuses `credential_source_stale`.
It then uses the independent protected binding, policy and executable checks in
[revision 1 section 6](local-setup-token-source.md#6-local-binding-and-final-boundary-l6), with its
endpoint, competing-input and node-lock checks. Qualification must cover both
the lifecycle's one-start boundary and the node's revoke/material-release
boundary; neither lock is assumed to replace the other's ordering.

The only proposed exception to hosted exact-process execution is the final
Curator-controlled addition of `CLAUDE_CODE_OAUTH_TOKEN` to that one approved
child's private environment. All other admitted argv, environment, cwd, binary,
policy and IO stay exact. No secret enters a plan, generic environment map,
daemon environment, snapshot, journal, restart recipe, temporary file outside
the protected source store, log, diagnostic or child-environment dump.
Revision 1 section 6's conflicting names are rejected by presence, including
empty/equal values. A pre-start refusal starts no child and leaves source, home, environment
and preparation state without forbidden partial writes; permitted durable
refusal/recovery telemetry follows the owning lifecycle contract.

PTY and noninteractive hosting are separate qualification tuples. A non-nil
`Terminal` remains refused until its actual mode is qualified; a headless test
cannot qualify PTY, attach or resume. Unsupported modes preserve their typed
refusal rather than dropping IO. Current local-final-exec schemas retain only
their published headless route and acquire no hosted authority from this text.

## 4. Long-lived execution, cutover and recovery

Preserve existing legacy sessions, homes, profile locks and live bindings while
specifying or testing this contract. A later identity cutover needs a separate
authorized operation: its lifecycle owner establishes authoritative quiescence
and release of the old execution generation before starting one target.
An unacknowledged start, missing PID, quiet inbox, expired TTL or disconnected
client does not establish absence. Unknown execution retains its claims and
must be reconciled against the same operation/manager/generation, never retried
as a second provider or resolved by stealing a lease.

Every newly started process, including a typed restart/resume, re-enters the
qualified final boundary and re-resolves current source and policy. Do not
persist material for restart or imply that a token delivered to an existing
Claude process can be recalled. Local revoke disables future delivery; it is
not vendor revocation or proof of process termination. Source replacement or
post-revoke recovery cannot reuse stale authorization. Unknown expiry remains
unknown, and transcript resume under changed authentication needs its separate
qualification under [revision 1 section 2](local-setup-token-source.md#2-custody-input-and-atomicity-l2-l8).

Recovery distinguishes a provably unstarted target, uncertain start, completed
authority transition and revoked source. A filesystem rollback restores neither
revoked authority nor a released execution generation. Preserve recovery records,
leases and source-state distinctions instead of recreating old credentials or
deleting an account/home to obtain a clean retry.

## 5. Qualification evidence and counterexamples

The [hosted qualification witnesses](../conformance/local-setup-token-v1/hosted-qualification-cases.json)
define neutral positive controls and forbidden neighboring outcomes. They are
contract/test-plan data, not a hosted wire, executable runtime harness or test
results. The existing metadata corpus separately exercises current binding,
source and unsupported-route diagnostics; it cannot establish no-read/no-write,
one-start, isolation, real OAuth or leak containment.

Keep the following evidence claims distinct:

| Claim | Evidence required before that claim is made |
|---|---|
| Specification/fixture consistency | Schema, metadata/refusal, link and paired contract-counterexample checks. Every hosted runtime remains unqualified. |
| Synthetic final-executor behavior | Isolated disposable fixtures show one final injection, exact refusals, no fallback, residue or duplicate child, including interrupted start/cutover/revoke and valid neighboring controls. |
| Real-harness containment | Separately authorized pinned real Claude release, disposable sentinels and child probes, including MCP interpolation/settings reload, hooks, tools, plugin helpers, telemetry and debug/transcript sinks; a known-leaking detector control fails for the intended leak. A guessed scrub flag or mock exec is insufficient. |
| Actual OAuth authentication | Separate owner-run destination-account enrollment and authorized provider check; structural token acceptance and a present readiness row do not prove it. |
| Live station/pilot | Qualified account/key/path, source/API, carrier/final-owner, IO/lifecycle and real-harness tuple; owning Curator-lane pilot first, later-host activation separately admitted after its evidence. |

Record exact reviewed source/API/carrier pins, host platform, harness release,
mode, configuration, commands, exits and intended control failures for each
claimed tuple. macOS/Linux results cannot admit another OS, account, host,
harness release or mode implicitly. Unknown or failed prerequisites leave
`credential-injection/1` unavailable for that tuple. All destructive fault and
revoke cases use isolated fixtures or explicitly authorized test accounts;
qualification requirements never authorize damage to a live operator session.

## 6. Compatibility and security impact

This proposal changes no released or closed schema, frozen readiness
row, default `per-home` behavior, source-policy selector, custody backend,
snapshot exclusion, diagnostic or execution capability. It adds no Keychain,
broker, refresh-token, Remote Control, archive relocation or cross-UID route.
Joint adoption and later route-specific qualification remain separate gates.

The intended security change is to qualify hosted final-owner delivery without
turning metadata/profile equality into authority or teaching a shared daemon to
read credentials. Reuse revision 1 sections 2–9's exact protections and typed
refusals;
do not claim account isolation from ordinary same-UID precautions. If the real
harness cannot contain delivery to the required sinks or an owning interface
cannot express these bindings, keep the tuple unavailable and return the exact
constraint to its owner instead of weakening the contract or hiding it in mocks.
