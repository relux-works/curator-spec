# Machine-scoped Claude environment, revision 1 (proposal)

Status: proposed, unreleased. [CIP-0029](../cips/CIP-0029-machine-claude-output-limit.md)
and [draft Decision 0035](../decisions/0035-machine-claude-output-limit.md)
describe this bounded addition. The keywords below specify the proposed
contract; they do not claim implementation, runtime qualification or allocation
of a containing carrier. The shell extension is outside this proposal.

## 1. Authority and containing versions

The existing per-OS-account machine configuration is the sole source of
`extensions.claude_env`. It applies across that account's profiles. It MUST NOT
be read from a context package, profile, lock, overlay, project configuration,
system configuration, `launcher.json`, or an alternate environment variable.
It grants no cross-account authority. No profile or lock bytes change.

Propose manager configuration **9**, after the notification carrier **8** in
[Core PR #216](https://github.com/relux-works/curator/pull/216). Version 7's
`proxy` and `claude_auth`, and version 8's `notification`, retain their exact
admitted semantics. This proposal MUST NOT land as an accepted carrier before
that dependency is accepted and its final containing shape is fixed. The
maintainer allocates the number at review; **9 is a proposal, not a reservation**.
If the allocation changes, all witnesses change together before acceptance.
Schema 6's separate node-source family MUST NOT be repurposed.

A containing typed projection also needs a successor: propose
`curator.launcher-config/3`, after #216's `/2`. Old `/1` and `/2` readers MUST NOT
silently drop the new selection. The complete successor configuration and
projection schemas must retain all admitted predecessor fields and strict
unknown-member rejection before any producer emits them. The standalone
[member schemas](../schemas/machine-claude-env-v1/README.md) here allocate
neither whole carrier. Earlier carrier bytes and frozen release pins are unchanged.

Ordinary configuration edits MUST preserve unrelated admitted fields and the
selected configuration version; they MUST NOT downgrade a configuration to
discard this member. Older readers reject the unsupported version before
publishing a projection or starting a child. No fallback to an older file is
permitted after an explicit selection fails.

## 2. Closed declaration

Illustrative subtree (not a complete configuration):

```json
{"extensions":{"claude_env":{"BASH_MAX_OUTPUT_LENGTH":"8000"}}}
```

`claude_env` is OPTIONAL. Absence and `{}` select no override. If present, it
MUST be an object with at most the single exact, case-sensitive name
`BASH_MAX_OUTPUT_LENGTH`. Null, duplicate members, malformed JSON, unknown
names and unknown containing extension members MUST be rejected. No generic
environment map, credential, proxy selector, permission setting or hook is added.

The value MUST be a **JSON string containing a canonical ASCII decimal integer
in the inclusive range 1 through 65536**. There is no sign, leading zero,
whitespace, fraction, exponent or coercion from a JSON number/boolean/null.
The string representation follows environment-variable transport and the
existing proposed declaration, rather than introducing a second numeric type.

65536 is a proposed manager policy cap: a finite 2^16-unit budget that admits
the requested 8000 while bounding an explicit configuration. It is not a vendor
maximum, a measured output size, a disk quota or a guarantee about token use.
Changing the cap requires reviewed schema, prose and vector changes together.
The real-runtime witness must establish the native release's actual units and
spill behavior; these fixtures do not establish them.

## 3. Child-only projection and compatibility

After complete configuration validation, the manager applies the selected
string only to the **Claude Code child's environment**, at its normal launch
or resume boundary. The selection overrides an inherited value for that child.
It MUST NOT mutate the manager's parent environment, persist `settings.json`,
rewrite a managed home, change hooks or permissions, copy credentials, restart
a live session, or cause a second launch. Existing nonselected environment
entries and security settings retain their own policy and values.

The selection and its source identity MUST be re-evaluated for each launch or
resume. An already running process is unaffected. Status MUST distinguish
absent, configured and runtime-ineligible selection and identify its machine
source without dumping an environment or native settings. Status must not
claim runtime effect without the evidence in section 5.

| Input / target | Required result |
| --- | --- |
| Absent member or `{}` / any admitted runtime | Existing launch behavior; no contribution from this extension |
| Valid selection / `claude_code` | Exact string in that child's extension contribution only |
| Same valid machine selection / another admitted runtime | Launch retains its existing behavior; extension contribution is empty |
| An extension contribution containing the name / non-Claude child | Reject with `claude_env_runtime_ineligible`; no child starts from that invalid plan |
| Invalid explicit declaration / any target | Reject before any child, write or fallback |
| Existing unrelated proxy/auth/notification or environment settings | Preserve their accepted validation, delivery and security semantics |

The non-Claude negative is an attempted **injection**, not the presence of a
valid Claude selection in a shared machine file. Rejecting every non-Claude
launch would violate the third row. Independently admitted ambient variables
retain their existing provenance; they MUST NOT be mislabeled as contributions
from this extension. The projection schema models only this extension's
contribution, never a full child environment or credentials.

## 4. Refusals and observable effects

Diagnostics MUST contain no supplied values, unknown member names, raw input,
native settings, authentication material or child environment. Use a stable
code and the fixed path `extensions.claude_env` only. Reader/schema errors must
be normalized before reaching user-visible diagnostics; parser errors must not
be passed through verbatim. The conformance codes are:

| Condition | Code |
| --- | --- |
| Invalid object, duplicate/malformed JSON or projection shape | `claude_env_invalid` |
| Unknown declaration name | `claude_env_name_not_allowed` |
| Wrong JSON type or noncanonical integer spelling | `claude_env_value_not_integer` |
| Zero or negative integer | `claude_env_value_nonpositive` |
| Integer above 65536, including overflow | `claude_env_value_over_bound` |
| Non-Claude extension contribution contains the variable | `claude_env_runtime_ineligible` |

A refusal publishes no usable launch plan, starts no child, performs no native
or machine-file write, and leaves the previous accepted state intact. Invalid
explicit input MUST NOT silently become absence or native-default behavior.
The standalone validator proves input/refusal properties, not these production
side effects; real-entrypoint validation must check the latter independently.

## 5. Required implementation and real-runtime evidence

Implementation is a separate step after accepted spec landing. Before claiming
usable support, the implementation must provide:

1. Positive and negative checks through the actual selected machine-config
   parser, ordinary editor, status, typed projection and launcher/resume path;
   unchanged profile/lock/native-file witnesses; old-reader rejection; and
   preservation of every legitimate predecessor extension form.
2. Child-bound observations for a configured Claude launch and resume, paired
   with a non-Claude launch with no extension contribution. A conflicting
   inherited value is a positive override control. Unrelated environment,
   hooks, permissions, authentication and session custody remain intact. Do not
   capture a full environment, credential value or raw native configuration.
3. A real supported Claude runtime, through its admitted launch route, with a
   finite synthetic command producing output above and below the selected
   budget. Observe the preview, full-output disposition, native interpretation
   of the limit and command exit status. Compare against an unconfigured
   control on the same release; test an effective native-settings precedence
   conflict rather than assuming that child-env presence proves effect.
4. Exact runtime/build/platform, selected configuration identity, command and
   sanitized observation evidence. Capture only the allowlisted setting and
   finite synthetic output; no auth copies, home hotfix, private config export,
   prompt injection, permission weakening or service mutation is a test route.

No real runtime is exercised by this spec PR. No launch, spill behavior,
credential compatibility, per-platform support or existing-session update is
claimed by a passing schema or corpus check.

## 6. Acceptance data

The [corpus](../conformance/machine-claude-env-v1/README.md) contains nearby
valid controls and the six required single-defect plants: unknown name,
non-integer, zero, negative, over-bound and non-Claude injection. Each must fail
for its named reason; an unrelated setup error is not a detected plant. The Go
checker runs every case, reports each mismatch and returns nonzero if any case
fails. It validates real JSON Schemas as well as semantic refusal codes, and
tests its own rejection of a wrong expected verdict. None of these results is
an implementation or runtime conformance claim.
