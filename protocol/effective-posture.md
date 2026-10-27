# Effective posture for unattended launch admission

Status: additive specification; no runtime implementation or provider certification.
Curator owns the typed carrier. **curator-run owns resolution, the admission
gate, launcher SPEC, model/bootstrap route graphs and wire refusal mapping.**
Existing fragments, exact/delegated plans and session-host schemas stay closed;
this document does not insert a field into an old carrier or activate a route.

Source: [unattended lane design §1.1 and Q1 at Curator main 05102ddb](https://github.com/relux-works/curator/blob/05102ddb4f4911f25c49fee5ba55221a5dd16a3e/docs/design/unattended-lane-launch.md#11-approval-and-sandbox-mode).
The owner's 2026-10-27 decision selects **yolo as the unattended default**;
`native-project` and `strict` are explicit isolation choices. That decision
supersedes the design's proposed launcher-global native default. A resolved
default is not operator approval. Packages never authorize their own posture.
The design's independently approved lane record and hook/project-trust gates
still apply; this carrier is not an operator grant or a sandbox boundary.

## 1. Closed carrier and bytes

**EPA01.** [`effective-posture/1`](../schemas/effective-posture-v1/record.schema.json)
is a required-understanding, closed, bounded record. Missing, duplicate,
unknown, unreadable or unsupported values MUST refuse before provider start.
No omitted field acquires a default. The complete received bytes MUST equal
CCJ-1 of the decoded record: strict UTF-8, safe shortest integers, no floats,
BOM, duplicate names, lone surrogates, trailing whitespace or newline.
CCJ-1 uses [registry §1](registry.md#1-curator-canonical-json-1); there is no `sig`
member or self-digest exception here. Maximum encoding is 64 KiB and depth 12.
SHA-256 over those complete bytes is `posture_sha256`; a negotiated protected
launch plan MUST cover the record and that digest. A digest proves byte
consistency, not source authority or qualification.

| Field | Meaning |
| --- | --- |
| `permission` | Resolved `native` or `yolo`, and actual source `default`, `profile`, `machine`, `lane-record` or `flag`. `flag` preserves the design's explicit-CLI provenance; it never supplies approval. `default` is `yolo` for this unattended contract. |
| `native_policy` | `policy_id`, `policy_sha256`, `source_set_sha256`, complete/incomplete/unsupported inspection, named `uninspected_sources` and `relaxations`. Policy and source-set digests name protected, retained inspection evidence for the exact home, checkout and provider bytes; not a selected config file alone. No credentials/config contents are put in this carrier. |
| `native_suffix` | Exact ordered arguments after `--`, with SHA-256 of CCJ-1 of that array. No splitting, cleanup, reordering or inferred removal. Arguments are private plan data and MUST NOT be logged indiscriminately. |
| `project` | Requested `strict`, `native_project`, `no_tools` selectors, effective `mode` (`none`, `native-project`, `strict`) and effective `no_tools`. These are resolved intent and observed posture, never permissions granted by a package. |
| `provider` | Canonical environment, exact version, binary SHA-256 and platform. A version string alone does not identify a provider. |
| `qualification` | Protected qualification `id`, CCJ-1 `sha256` and reported `state` (`qualified`, `unqualified`, `unknown`). A self-asserted qualified label cannot authorize admission. |
| `binding` | Profile name, CCJ-1 lock SHA-256, Curator admitted plan SHA-256 and protected generation identity. |
| `provenance` | Per-launch `launch_id`, digest/reference of the `launcher-path-state/1` record from spec #194, and native/hosted route with the home-lease relation from #193. Native has explicit null lease; hosted requires its exact prepared lease record identity/digest, holder request and manager incarnation. |

`binding.plan_sha256` is the **Curator plan** used by #194's binding, not the
outer launcher process-plan digest. The outer plan includes the posture and
has its own owning contract's digest. Neither hashes itself. Lock/plan hashes
MUST be recomputed from independently admitted complete records; a caller's
matching pair of strings cannot establish currentness. Qualification evidence
MUST be retained, digest-bound to the exact provider, inspector, suffix grammar,
mode and tool restrictions, and obtained from the protected authority boundary.

## 2. Resolution and refusal obligations

**EPA02.** Mode precedence is `strict` > `native-project` > the plain
`no-tools`/`none` route: if requested strict is true, mode MUST be strict;
otherwise requested native_project selects native-project; otherwise mode is
none. `no_tools` is an independent deny-all-tools constraint and MUST equal its
requested value in every mode, including strict. It never erases isolation,
changes permission approval or authorizes a weaker tool policy. Unsupported
strict plus requested native-project MUST refuse, never retry native-project;
unsupported no-tools MUST refuse, never ignore the selector.

**EPA03.** A missing/unknown/unqualified qualification or an unsupported
provider/version/bytes/platform/mode/tools/inspector/suffix-grammar combination
MUST refuse. Qualification is an external authority input, not capability
booleans supplied by the posture. Native-project and strict require the
mandatory permission, memory-off and source-control surfaces of
[project context](project-context.md); strict additionally requires native-source
exclusion. A narrow successful atom, adapter registration or an operator's
willingness to bypass cannot certify them. `yolo` MUST refuse for either
isolation mode, including an explicitly approved lane. No fallback is allowed.

At this revision **no provider is certified for native-project mandatory
surfaces**. [Curator #187](https://github.com/relux-works/curator/pull/187)
(head `01d86d8ab2e5851cb96c9c5bfc5e8784678e164e`) and
[#191](https://github.com/relux-works/curator/pull/191)
(head `db880fa6c058fb303297df5013b2df932c74b41b`) preserve admission false.
Codex 0.164.0 retains the observed resume memory-off failure and unknown cells;
Claude and Muse observations do not supply the missing complete proof.
Published positive isolation vectors use **synthetic future qualification**,
never a claim that one of these releases can launch today.

**EPA04.** curator-run MUST reconstruct the effective native policy and inspect
all settings sources read by the qualified provider release for the selected
home and checkout. For `native`, inspection MUST be complete, with no
uninspected source or relaxation. `yolo` explicitly admits bypass only against
the owner-approved unenrolled lane record; incomplete inspection remains
reported as incomplete, never upgraded to complete. Unsupported inspection
refuses. A `complete` claim with uninspected sources is internally inconsistent
and refuses. Policy/source-set identities MUST match current protected evidence.

The exact suffix MUST match the qualified parser's closed allowlist for this
provider and resolved posture. Policy selectors, an unparsed argument or a
suffix that conflicts with the stored policy/resolved mode MUST refuse; the
launcher MUST NOT strip an argument or silently edit the policy to proceed.
The corpus uses one synthetic grammar; it is not a vendor CLI allowlist.
`source` reports resolution only: every source, including default and flag,
requires the separate lane approval check. Machine locks retain their veto.
The permission precedence ladder is owned by curator-run, not redefined here.

**EPA05.** Compare `binding` with the current admitted lock, plan and generation,
and verify all native policy, suffix, qualification and provenance digests at
the actual start boundary. A moved lock or plan, different profile/generation,
changed suffix, policy or provider MUST refuse, not re-resolve, recompute a
baseline in place or borrow another profile's posture. Any changed input needs
a fresh fully admitted record and plan. Permission, mode and tools MUST match
the independently resolved authorized intent, not merely be internally valid;
changing native to yolo or strict to none cannot pass by recomputing digests.

## 3. Provenance and immutable plan consumer

**EPA06.** The per-launch state relation targets
[spec #194](https://github.com/relux-works/curator-spec/pull/194),
`launcher-path-state/1` and its profile/lock/Curator-plan/generation binding,
at proposed head `264275f35cd2a87aabb04952a1d48f5c27200224`. This is an explicit
publication dependency while #194 remains open, not a claim it is on main.
The state bytes, kind, launch ID and complete binding MUST match the posture;
the consumer MUST validate that state's own schema and publication/integrity
obligations. A state file is provenance, not launch authority. Missing or
substituted state refuses on this negotiated unattended route.

For hosted launches the relation is the merged
[#193 home-lease contract](home-leases.md): exact lease ID, revision,
manager-root/home identity, record digest, holder request and registered manager
incarnation. The current lease MUST still be prepared for this new start and
match the profile, canonical environment and lock. #193 stores bare lowercase
lock hex; here the same hash is `sha256:` plus those 64 unchanged hex digits.
Never reinterpret terminal acquire replay as admission. Native launches have
no home lease and MUST NOT acquire one for this carrier. Lease records progress
after start under #193; the immutable launch plan retains the admitted prepared
reference and later audit relates subsequent revisions rather than editing it.
Do not hash a later bound record as though it were the prepared preimage.

**EPA-C1 — curator-run effective-posture binding and start admission.** The
launcher MUST obtain the Curator-owned binding, policy and provenance inputs
through the protected manager boundary, assemble the typed carrier with its
own resolved permission, source, suffix and mode fields, and verify EPA01–EPA06
and its independently resolved lane approval, permission/source/intent, native
inspection and suffix parsing. It MUST bind the exact record plus digest into
its protected immutable launch plan.
It MUST persist the correlated per-launch state and preserve the home-lease
relation, then recheck current bindings at actual provider start. If a required
carrier, provenance, authoritative qualification, approval or verification is
unavailable, it MUST refuse before provider execution with a typed reason
identifying the failed input. It MUST NOT silently downgrade, repair, retry a
weaker mode, merge receiver defaults, discard a denied tool restriction or
reinterpret refusal as attended/native fallback. Refusal has zero provider
starts, no config/lock/policy rewrite and no new grant; allocated resources are
reconciled under their existing owning contracts, without breaking a lease.

curator-run's amendment may cite **EPA-C1** as one obligation. It owns public
refusal codes/exits and required-understanding route negotiation. Until that
amendment and any receiver carrier are jointly published and qualified, this
record alone does not make an old hosted/native route admission-capable.
The executable corpus checks typed bytes and specified relations only; it
neither implements the launcher gate nor validates an operating-system boundary.
