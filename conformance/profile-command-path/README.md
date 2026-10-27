# Managed-session profile command PATH witnesses

This normative, unreleased corpus accompanies
[environments §9.4](../../protocol/environments.md#94-profile-scoped-skills-and-migration),
[§10.2](../../protocol/environments.md#102-the-launch-environment-fragment)
and the [hosted delivery contract](../../protocol/local-hosted-launches.md#4-exact-process-and-runtime-writers).
It implements the managed-session companion requirement identified in
[profile skill-plan carrier PR #189, section 5](https://github.com/relux-works/curator-spec/pull/189).
Its placement follows the accepted
[D-PATH recommendation](https://github.com/relux-works/curator/blob/05102ddb4f4911f25c49fee5ba55221a5dd16a3e/docs/design/profile-skill-runtime.md#slice-b-command-roots-bound-to-profile-locks).
The owner requirement of 2026-10-27 adopts that placement for every managed
launch with a profile, including managed one-shot launches. This does not
change unmanaged one-shot selection or lift project-command execution gates.

`cases.json` contains **abstract evidence records, not wire payloads**.
The base models a selected `alpha` profile in Slice A's proven isolated
machine-current domain. Root paths are fixture paths, and repeated hex digits
are synthetic digest identities, not verified artifacts. `receipt` stands for
protected admission evidence supplied by the runtime authority, not a
caller-authored bypass. A real implementation must derive the lock digest
from the complete CCJ-1 lock under environments §1.3, verify plan and source
pins, and verify the executable bytes against protected runtime receipts.
Executable digests remain outside the portable lock.

Each case deep-merges `changes` into `base`; arrays replace rather than append.
Cross each `routes` entry with all three `launch_forms`: interactive, managed
one-shot and a resume/restart creating a new child. The examples use POSIX path
spelling. Real qualification must also exercise each claimed platform's
lookup, case, extension, filesystem-alias and separator rules. No claim about
Windows lookup is established by these strings.

## Required observations

For each successful route/form, collect all three witnesses from the **final
agent child**, through the real launch path, and correlate them with protected
Curator/launcher/hosted admission records:

1. `child.path`: its actual PATH, in order, with protected tools before exactly
   one verified profile root and the admitted base after it. Record the native
   serialized PATH as well as its platform-parsed components. Keep an already
   admitted protected dispatcher at its admitted position, otherwise append it
   once, under the existing D-PATH rules. No inherited foreign profile root is
   admitted, even if the selected root would shadow it.
2. `child.command`: the ordinary skill CLI actually reached, with its resolved
   artifact path and SHA-256 digest. Verify the shim/target chain and active
   export against the lock-bound receipt. A shell's printed lookup alone is
   insufficient; the observed executed artifact must match. Real fixture
   commands should report their identity to an independent harness.
3. `child.binding`: selected profile, complete lock digest, plan identity and
   runtime generation, correlated with the verified fragment/root receipt.
   Hosted evidence additionally binds the delivered process to that same
   tuple and effective PATH; exact-plan execution covers them in its complete
   process digest, delegated execution uses its negotiated contract.

The `candidate` is the environment/binding at the process-start boundary.
The specification checker compares its claims with the admitted baseline;
it neither authenticates that baseline nor launches anything. On a refusal
the expected `child` is null, provider starts and fallbacks are zero, and
the live preimage is unchanged. Rejection telemetry is permitted. A negative
row is never satisfied by a successful child that merely reports wrong PATH.
`violations` are corpus assertion labels, **not allocated CLI diagnostics**.
This corpus isolates one fault per row and assigns no combined-failure order.

| Vector | Required result and responsible boundary |
| --- | --- |
| `verified-root` | Native and hosted succeed with all three exact witnesses; Curator publishes, curator-run applies and host preserves. |
| `empty-command-set` | Both routes deliver the verified empty root and binding, with no command witness; no inactive exports are inferred. |
| `missing-root` / `tampered-root` / `unreadable-root` | Curator refuses successful fragment publication; launcher verification also rejects substituted root evidence. No repair or foreign fallback. |
| `stale-lock` / `wrong-plan` / `wrong-generation` | Root receipt fails the selected lock/plan/generation binding; no child, including at hosted start. |
| `foreign-inherited-root` | Base admission rejects an inherited foreign root even when it comes after the correct selected root. |
| `hosted-drops-root` | Hosted start refuses a delivery missing the root; no native fallback. |
| `inert-path-prepend` | Parsing the fragment without applying it fails on both routes. |
| `root-before-protected-tools` | Refuse ordering that can shadow protected tools. |
| `ambient-path-recomputed` | Refuse a late ambient PATH substitution on either route. |
| `wrong-reached-path` / `wrong-reached-digest` | Candidate artifact disagrees with the receipt; a forged successful-child witness is also nonconforming. |
| `missing-lock-binding` | Correct PATH and bytes alone do not authorize an unbound child. |
| `unsupported-transport` | Refuse rather than omit/ignore required-understanding semantics. |
| `other-current-profile` / `routing-unproven` | Slice A cannot serve another profile or admit unknown consumers. |

Every refusal has `verified-root` as its nearby valid control. The empty-root
case is a separate positive control. The checker also plants wrong final-child
PATH, reached path, reached digest and lock binding in an otherwise valid
witness; each must fail its intended assertion. Passing abstract records prove
only this corpus's consistency and bounded detection, not product behavior.

## Ownership, qualification and publication gates

Curator must qualify publication and invalid-root preservation. curator-run
must qualify verification, actual `path_prepend` application and child
provenance. The hosted manager must qualify transport and final execution of
the same environment/binding. Native success never qualifies hosting, nor does
one runtime/form/platform qualify another. For a Slice A claim the independent
harness must demonstrate supervisor-issued exclusive routing admission and
unchanged unrelated consumers. Slice B additionally needs two profiles with
different versions of the same CLI running concurrently, update preservation,
and live-generation/receipt retention through GC; this corpus does not claim
those future grammar or runtime gates are delivered.

The full successor fragment/hosted carrier, capability negotiation, exact root
grammar and start-boundary refusal diagnostic mapping require joint publication
before implementation. Historical closed carriers stay unchanged; reserved
`path_prepend` syntax alone proves no consumer capability. The existing
`command_environment`/`path_prepend` exclusion remains; a launch needing both
requires a jointly accepted combined carrier or refuses. None of these gates
permits an accepted companion to be reported as qualified. Broader completion
or adoption retains `profile_skill_companion_required` until its required
accepted allocations and applicable real-runtime witnesses exist, including
the separate protected-command inventory companion.

Run `python3 -B -m unittest discover -s tools -p 'test_profile_command_path.py' -v`.
`make validate` discovers the same tests. Logs belong in `.temp/`. No Curator,
curator-run, hosted daemon or provider executes in these specification checks.
Released schemas, manifests and qualification records are unchanged.
