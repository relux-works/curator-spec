# CIP-0005: Audit backends and CLI secret transport

- **Status:** Draft
- **Owner:** ivan-curator (orchestrator); decision: operator
- **Created:** 2026-10-04
- **Related:** TASK-261004-hy8zmn — audit-token-argv-and-backend-env-allowlist-design; STORY-261004-2b8pnx — design-audit-backends-and-secret-transport; K24; public cocoaskills PR #142, commit 0da153a54e7f8b446e63a6a177a9b5392e30da11; adopted Decisions 0019 and 0021
- **Affects:** curator-spec manager profile §§1, 7, 12.6; registry protocol §9.1; CLI audit reference; manager configuration, local verdict and backend schemas; curator; shared agents-management launch layer. No proposed curator-run headless mode or launch-fragment wire change.

## Summary

Refuse literal registry tokens in CLI arguments and support CURATOR_REGISTRY_TOKEN or a bounded, private, no-follow token file. Implement explicitly selected audit backends through a shared process runner, with Codex and Claude launch plans constructed by the existing owner of harness flags and a direct command adapter. Every manager-launched backend process receives the same allowlist policy, with unconditional secret-variable exclusions; Git transport retains its separate authentication policy. Make egress, canary results, incomplete backend coverage, cache identity, and strict/advisory failures explicit. This draft recommends a design for operator review; it authorizes no implementation, scheduling, or producer runs.

## Motivation and user stories

- An auditor publishes a signed record without placing a bearer value in the command line. An explicit token-file error must stop the operation instead of falling back to an ambient credential.
- An operator selects Codex, Claude, or a trusted local command and sees which analyzer actually ran. A misspelled or unsupported selection must never become a static-only clean report.
- A workstation carrying registry credentials, provider keys and Git authentication can audit an untrusted snapshot without forwarding those ambient credentials to an analyzer.
- An organization permits cloud analysis of explicitly public source, while internal source remains local. Neither advisory mode nor a content pin may authorize prohibited egress.
- Profile installation must use the configured analyzer while retaining its mandatory strict mode. Dry-run, external build-source and cached paths need the same policy.

## Current state

The inspected curator main revision is **ca1b776fb580ec0cee0173bf150daf063023aeaa**, equal to the public main ref observed during research. The specification baseline is **v1.0.0-rc.14**, peeled commit **43bf0a2506d5c354a73bbc3ea4623d4653db10c7**, also pinned by curator CI. Source references below are relative to those repositories at those revisions; curator package paths such as audit/audit.go are under internal/. This CIP is filed from the research draft in [.research/261004_CIP-0005-audit-backends-and-cli-secret-transport.md](https://github.com/relux-works/curator/blob/fae2ff9cab17a031c26a2b4c776afd8dc5e8b4f6/.research/261004_CIP-0005-audit-backends-and-cli-secret-transport.md) on `relux-works/curator` `main` @ `fae2ff9c`. Links, probe procedures, real exit codes and verification bounds remain in the companion [.research/261004_CIP-0005-audit-backends-and-cli-secret-transport_evidence.md](https://github.com/relux-works/curator/blob/fae2ff9cab17a031c26a2b4c776afd8dc5e8b4f6/.research/261004_CIP-0005-audit-backends-and-cli-secret-transport_evidence.md) at the same commit; they are cited, not copied. The operator has made no acceptance decision on this proposal.

| Finding | Evidence and consequence |
| --- | --- |
| Literal secret accepted | curator cmd/curator/main.go:2120, 2150–2157 accepts token argv, then falls back to CURATOR_REGISTRY_TOKEN. registry/http.go:451–461 uses a Bearer header. Probe P2 reached record validation with a synthetic argv token; P3 did likewise with the environment. |
| Backend parsing is not backend execution | config/config.go:129–145, 963–985, 1007–1011 retains backend settings. audit/audit.go:307–325 runs deterministic detection and caches its output, without dispatching an analyzer. Backend/model strings currently label the cache at :413–415 and :470–480. P1 returned exit 0 in strict mode for an unsupported selection, with no child marker and zero cached findings. |
| Size and egress controls have no analyzer consumer | Default request cap is 1,048,576 bytes; maximum is 10,485,760 (config/config.go:42–43). AllowCloud, Backends and MaxRequestBytes are parsed, but the audit pipeline does not use them to dispatch or constrain a child. P1's one-byte cap did not change the static-only outcome. This is not a measurement of a constructed backend request. |
| Existing policy must remain authoritative | manager.md:1106–1120 requires static canary, optional configured analysis, public-only cloud egress, redaction, and mode-dependent backend failures. Canary failure always blocks. Pins cannot override revocation (:1122–1129). |
| Profile propagation is a separate integration seam | envprofile/envprofile.go:1716–1732 creates a new audit configuration with Backend null. manager.md:2977–3004 requires strict audit of every profile closure member, including unpinnable context-secret findings. Changing cmdAudit alone cannot satisfy that path. |
| Persisted identity needs migration discipline | audit/audit.go:281, 384–390, 470–480 uses the legacy hash call and writes no hash_version in these local records. rc.14 manager.md:1122–1129 requires versioned identities. Existing hashing helpers support version 2 (hashing/hashing.go:126–165); historical records must not be relabeled. |
| Native adapter flags have an existing owner | adopted Decision 0019:64–106 puts every harness argv element/channel in agents-management; Decision 0021:64–68 concerns interactive entry. This proposal must extend the shared launch plane, not create a second flag builder or a headless curator-run path. |

The configuration schemas leave audit.backends open and audit.backend as a string; v2/v3 reference the v1 audit object (schemas/v1/manager-config-v1.schema.json:71–112; v3:37–38). This allows an implementation contract to be added without silently changing frozen schemas, but does not establish any currently supported backend kinds.

## Design

### Options considered

| Option | Mechanism | Benefits | Costs and security tradeoffs |
| --- | --- | --- | --- |
| A. Token fix and explicit static-only audit | Refuse token argv, add secure file input, retain null and diagnose every other backend as unsupported. | Smallest release; honest behavior; no new analysis egress. | Does not deliver the requested agent backends. A useful separately prioritized first slice, not the full recommendation. |
| B. Shared audit runner plus typed native launch plans **(recommended)** | One runner owns env filtering, request/response bounds and lifetime. The shared launch plane constructs Codex/Claude plans; command runs a trusted executable directly. | Supports all three environments; central security boundary; respects Decision 0019; real child observation can cover every adapter. | Requires a shared launch-contract extension and version qualification. Provider authentication from environment keys is intentionally unavailable. Saved CLI state remains a trusted resource. |
| C. Command protocol only; operator supplies native wrappers | Curator speaks a bounded JSON protocol to an executable; externally maintained wrappers integrate agent CLIs. | Small Curator integration; flexible local analyzers; no native CLI flags in Curator. | Operator must maintain and review wrappers, credential sourcing and provider updates. Cannot advertise built-in Codex/Claude support or automatically attest wrapper confinement. |

A blacklist-only environment, arbitrary inherited environment, and a native adapter bypassing the shared runner are rejected within every option that launches analysis.

### Recommendation

Adopt B, with independently reviewable leaves after operator acceptance. Preserve current defaults: audit.enabled false for optional skill gates, backend null, advisory mode, fail_on high, allow_cloud false, and internal source classification. Explicit CLI audit continues to enable its audit, and profiles remain always strict.

#### 1. Registry token sources

The publishing syntax becomes:

    curator audit --publish <record.json> --registry <url> [--token-file <path>]

With no file option, use CURATOR_REGISTRY_TOKEN. An explicit file takes precedence even if the environment is populated; a missing, empty, unreadable or invalid file is an error, never absence. Reject repeated file options and file input outside the publish operation. Do not add token values to configuration, fragments, child environments, cache identities or command diagnostics.

Refuse the legacy --token and -token options, including separate-value and equals forms, before configuration loading, record reads, backend launch or network access. Refusal must not repeat the value. Test wrong-subcommand and malformed forms too; parser errors must not dump raw argv. Preserve the distinct Git-credential --token-env NAME interface: it carries a variable name, not this literal-secret flag.

Token-file contract:

1. Open read-only, non-inheritable and atomically no-follow at the final component. Reject links/reparse points, directories, FIFOs, sockets and devices before reading. Use a nonblocking open on POSIX so a racing FIFO substitution cannot hang.
2. Validate the opened handle with fstat or its native equivalent. If a pre-open identity check was used, require matching device/file identity and type; do not reopen the path to read. Validate privacy on that handle. POSIX minimum: neither group nor other read bit may be set; recommend current-owner files with no group/other write permission as well. Report extra ACL access as unsupported or unsafe rather than claiming mode bits establish ACL privacy.
3. Windows must use a non-inheritable OPEN_EXISTING handle with reparse-point opening and handle-based type/identity checks, plus a DACL privacy check. Permit the current user and OS administration principals; reject read access for other users/groups, a null DACL, or indeterminate access. Unix mode-bit emulation is insufficient. If the implementation/platform cannot establish these properties, refuse --token-file with a safe diagnostic; environment input remains available.
4. Refuse a reported file size above **65,536 bytes** and independently read at most **65,537 bytes** to detect growth. The cap applies to raw file bytes, including a trailing line ending. Do not trust stat size alone.
5. Accept one nonempty ASCII bearer value, using the [RFC 6750 §2.1 b64token alphabet and terminal padding grammar](https://www.rfc-editor.org/rfc/rfc6750#section-2.1). Remove at most one terminal LF or CRLF from file input only. Reject embedded whitespace, CR/LF, NUL, non-ASCII, leading whitespace and invalid padding; do not broadly trim. Apply the same 65,536-byte ceiling and token grammar to environment input, without newline removal.
6. Close the handle before publication. Sanitized failures name the source and error category, never file contents, bearer value, HTTP headers or raw decoding exceptions.

The file check guarantees the final opened object, not confinement of every ancestor directory or protection against the same user altering their own file. Use an operator-controlled parent directory. The design removes a future credential from argv; it cannot erase history or process observations from a legacy invocation the user already made.

#### 2. Selection and typed backend configuration

audit.backend selects exactly one name. The reserved name null means deterministic-only audit and launches no child; it must be reported as static-only coverage. A non-null name must resolve in audit.backends to a versioned descriptor. There is no implicit fallback, automatic analyzer selection, chained fallback or automatic installation/login.

Proposed descriptor version 1:

| Field | Contract |
| --- | --- |
| schema_version | Required integer 1 in a selected non-null descriptor. |
| kind | codex, claude, or command. These are audit adapter kinds, distinct from environment profile agent IDs. |
| model | Optional nonempty identifier; descriptor value overrides audit.model. No implicit named model chosen by Curator. Record the effective requested model and any provider-reported resolved model separately. |
| timeout_seconds | Integer 1–600, default 120; wall-clock deadline for each canary/extraction, including startup and output collection. No automatic retry in version 1. |
| env | Optional string-to-string map. Only the shared base/per-kind allowlist may survive; no field can expand it or exempt a denied name. |
| cloud | Required true for native codex/claude version 1. For command, defaults true; explicit false is a trusted operator assertion that the executable and any service it contacts are local. |
| command | Required nonempty argv array for command only. First entry is an operator-configured absolute executable; no shell command string, expansion, source interpolation or token. |

Native command paths/model selectors are supplied through the shared launch-layer tool bindings; arbitrary extra_args, cwd, provider URLs and raw native config overrides are not part of this first contract. Unknown fields in a recognized descriptor are invalid configuration. Unselected extension descriptors may be retained opaquely for another implementation, but must never execute.

Select after machine policy/locks are applied. A skill manifest, repository file, response or profile package cannot define the executable, backend configuration, environment exceptions, auth source or egress classification. Resolve a native executable from trusted bindings or an admitted absolute PATH candidate, never the audited checkout, a relative PATH entry, or the current directory.

Missing selected descriptor, unsupported kind/descriptor version or unavailable adapter is a typed backend-unavailable result: strict blocks, advisory warns and records incomplete coverage. A structurally malformed recognized descriptor is a configuration error in both modes. An inactive optional audit does not launch or claim backend coverage; explicit audit and mandatory profile gates activate selection checks even if the project has no eligible subjects.

#### 3. One child environment policy

All manager-owned analyzer launches use a single environment constructor at the real exec boundary. It applies to extraction, canaries, version/capability probes and any manager-launched adapter helper. It is not a new global subprocess policy.

| Scope | Allowed names |
| --- | --- |
| All backends | PATH, HOME, USER, LOGNAME, LANG, LC_*, TMPDIR, TEMP, TMP |
| Windows additionally | SYSTEMROOT, COMSPEC |
| Codex additionally | CODEX_HOME |
| Claude additionally | CLAUDE_CONFIG_DIR |
| Command additionally | None in descriptor version 1 |

Construct a fresh non-nil environment, taking only allowed entries from inherited values and explicit overrides. Windows matching, deny checks and duplicate-key normalization are case-insensitive; reject conflicting canonical duplicates within a single input layer. An explicit permitted override wins over its inherited value. POSIX allow-name matching is case-sensitive; perform security deny matching with ASCII case folding on every platform.

After merging, always remove names ending in _TOKEN or _KEY, SSH_AUTH_SOCK, and names beginning GIT_. Denial wins even for LC_* names, per-backend requirements and explicit overrides. Variables such as provider API keys, registry tokens, loader controls, language startup controls, proxy settings and arbitrary unrelated values do not inherit. Do not append os.Environ or plan-supplied variables after filtering. Curator checks the launch plan's required environment names; if a required name is forbidden, launch is unsupported rather than widening the policy.

PATH/HOME values and the configured executable remain operator trust inputs. This is a direct-child inheritance guarantee, not an OS sandbox or a promise that a trusted child cannot read its own credential store. Provider-created descendants are not manager-owned launches; disabling tools, hooks and integrations is a separate native-adapter requirement. Direct child tests must report this scope plainly.

Git clone/fetch/credential-helper children retain their existing transport environment policy. In particular, do not apply the audit filter to internal/gitops.run or the Git authentication acquisition path. A positive transport control must demonstrate synthetic auth survives where allowed while the analyzer child does not receive it.

#### 4. Native adapters and command protocol

Curator owns the process, request, input/output pipes, deadline, termination, decision and cache. The shared agents-management launch layer owns the native executable/argv and any harness-specific setting names, in accordance with adopted Decision 0019. Extend its typed exec contract with an audit purpose: noninteractive, no resume, isolated working directory, no tools/hooks/MCP/plugins, no ambient instruction or memory discovery, no history, schema-constrained result, and stdin input. This is a proposed extension; support by today's module is **not established** by this research.

Every launch uses a fresh private working directory unrelated to the source checkout. Pass source only as bounded stdin data; do not put prompts, source bytes or auth in argv or execute source files. Use a manager-owned schema/output path where a CLI requires one. Read result files without following links and with the same output byte bound as stdout. Only stdin/stdout/stderr and explicitly necessary handles survive; never inherit a token-file handle.

| Adapter | Intended behavior and support boundary |
| --- | --- |
| codex | Typed plan for codex exec, stdin sentinel, schema output, ephemeral session, read-only permissions and no prompts. Suppress user config/rules and disable tools, hooks, MCP, apps, remote plugins and subsidiary agents through the shared owner. Official docs distinguish ignoring user config from authentication: CODEX_HOME can still locate saved CLI auth. Do not call read-only mode a host filesystem sandbox or assume --ignore-rules disables all instructions. |
| claude | Typed print-mode plan, stdin prompt, structured JSON result, no persistence, empty built-in tools, no MCP tools, no project/local settings, disabled hooks/plugins and no permission interaction. Parse the CLI envelope before validating the audit response; successful process exit alone is insufficient. CLAUDE_CONFIG_DIR is the only additional inherited name. |
| command | Execute the configured argv directly with shell=false semantics, bounded JSON stdin and one JSON response on stdout. Curator does not know or claim tool confinement inside an arbitrary trusted command. No repository-selected executable or shell-wrapper convenience fallback. |

Official documentation supports the CLI building blocks, not the full proposed confinement profile: [Codex noninteractive operation](https://learn.chatgpt.com/docs/non-interactive-mode), [Codex exec options](https://learn.chatgpt.com/docs/developer-commands?surface=cli), [Codex feature controls](https://learn.chatgpt.com/docs/config-file/config-basic), [Claude CLI options](https://code.claude.com/docs/en/cli-reference), and [Claude environment variables](https://code.claude.com/docs/en/env-vars). The native implementation leaf must qualify exact CLI versions and refuse versions whose required controls cannot be applied. Windows plans must use a native executable or an explicitly admitted interpreter/script pair; do not fall back through COMSPEC just because a .cmd shim is found.

Authentication is the provider CLI's existing, explicitly provisioned saved-login mechanism. Curator never logs in/out, reads or copies a provider credential, or reintroduces API keys through another field. Environment-key-only provider setups will be unavailable under this contract. Curator can pass CODEX_HOME/CLAUDE_CONFIG_DIR, but cannot infer that a directory override relocates every OS credential store. Authentication, enterprise managed settings, ambient instruction discovery and exact tool-disable behavior require native qualification after acceptance; failure is visible, not grounds to relax the environment. If a CLI cannot separate required authentication from prohibited context discovery, its native adapter remains unsupported; do not manufacture a credential-copying workaround.

The neutral request protocol should have schema_version, request_id, subject identity including hash_version/content_sha256 and source policy class, prompt/ruleset versions, declared capabilities, deterministic findings, and an ordered file list. Each file has a safe relative path, encoding and content; binary bytes use base64. Do not include host-absolute snapshot paths, runtime secrets or the registry credential. The response repeats schema_version/request_id/subject identity and contains only findings, not a privileged policy verdict.

For backend findings, Curator validates severity, safe file paths and bounds against the exact frozen source. A backend's self-asserted verifiable=true is not authority. Findings remain advisory unless a manager-owned deterministic verifier establishes the claimed property; a valid byte span alone proves location, not malicious behavior. Preserve the existing fail_on rule for genuinely verifiable findings.

#### 5. Request bounds, egress and canaries

Build requests from the already frozen, raw-object-proved snapshot where applicable. Include the whole declared audit scope, with counts of included and expected files/bytes. An unreadable file, walk error, path escape, unsupported representation or incomplete enumeration is an error; never drop it and claim a clean audit. Do not grant backend access to the original checkout.

Enforce audit.max_request_bytes twice: bound the canonical serialized source envelope during collection and bound the exact bytes written to stdin after redaction and adapter prompt wrapping. Both use the existing default 1 MiB / maximum 10 MiB range. A payload at the configured byte boundary is allowed; one byte above is not. Base64 and JSON escaping count as transmitted bytes. Never truncate or split into unaudited partial success. Oversize is backend-incomplete: strict blocks; advisory warns without invocation or successful backend cache state.

Also bound final response/stdout to 1 MiB and diagnostic stderr to 64 KiB, stop a flooding process and drain/reap it within the deadline. Apply limits to success and error paths, including a Codex output file. Terminate the process tree on cancellation/timeout; use POSIX process groups or Windows job ownership. Do not issue a successful report while descendants owned by that launch remain running.

Egress classification is independent of executable location. Version-1 native Codex/Claude are cloud; command defaults cloud unless trusted machine configuration explicitly asserts local. A local binary that calls a remote service remains cloud. The local assertion does not provide packet filtering; source capabilities.network does not authorize auditor egress.

For cloud requests, require both allow_cloud=true and explicit public policy for **every** source contributing bytes. Default internal. Classify each subject's declared and effective network source identities after canonicalization under core §6.1; proposed matching is ordered first-match per identity, then default_class. The proposed source-policy pattern subset is a full-string match of literals plus * (zero or more Unicode scalars, including /) and ? (one scalar); brackets and escapes are rejected, and ** has no extra meaning. This is a new explicit audit-policy grammar, not the core network allowlist's segment-prefix rule. The most restrictive result across contributing identities wins. An explicit public default is a broad operator opt-in; path/dev snapshots remain internal in version 1, and failed identity reads block as indeterminate. No inference from a public-looking hostname, GitHub URL, cache hit or source declaration.

Before cloud launch, redact credential-shaped spans in all outbound fields, including source URLs, filenames, findings and prompt material, then recheck the exact encoded request. Failed/incomplete redaction or a residual supported secret shape blocks egress in every mode. Preserve redaction count, detector version, coverage bounds and source offsets without storing matched values. Prefer dropping the request over sending a secret-bearing metadata field. Known-pattern redaction does not establish absence of every possible secret, which is why public classification and explicit opt-in are separate gates.

The local static canary runs before any cache authorization. For a non-null backend, run a synthetic canary through the same adapter, runner, environment and response validation before the first uncached extraction in an audit operation. The canary has its own identity, public synthetic content and no user bytes or seeded credentials. Require expected fixture-specific network-transfer and policy-bypass findings at their known file/spans and a benign control without those findings; an arbitrary high-severity finding is insufficient. The spec leaf fixes their IDs and exact fixtures. The request cap applies to the canary too: a cap too small to encode it produces request-too-large before launch. A canary is a liveness/integrity check, not proof of analytical quality or absence of prompt injection.

Resolve selection and egress permission before even the synthetic cloud canary; disabled cloud must start no cloud process. Failure to locate/admit a backend before canary start is ordinary backend-unavailable. Once the canary starts, timeout, malformed output, process failure or a wrong/missing expected finding is canary failure and blocks both modes. Successful canary state is scoped to that operation and effective adapter identity, never accepted from a source or ordinary verdict cache.

#### 6. Failure and coverage semantics

Merge outcomes without losing deterministic findings or existing unconditional gates. The table applies to CLI audit, installation, repair, external-source audit and their dry-run paths. Profile operations always use the strict column.

| Event | Strict | Advisory | Child/cache effect |
| --- | --- | --- | --- |
| null selected; deterministic checks pass | Allow, static-only coverage | Allow, static-only coverage | No child; cannot claim backend analysis |
| Selected backend missing/unsupported/unavailable before canary | Block | Warn, incomplete backend coverage | No fallback; no successful backend cache |
| Invalid recognized configuration or unsafe launch plan | Configuration/policy error | Configuration/policy error | No child |
| Egress disallowed or redaction incomplete | Block | Block | No subject bytes sent |
| Static or started backend canary failure | Block | Block | No extraction; never cache a pass |
| Extraction timeout/nonzero exit, missing/malformed/oversize response, bad identity | Block | Warn, incomplete coverage | Reap child; retain static findings, not success |
| Request exceeds cap | Block | Warn, incomplete coverage | Do not launch; do not cache backend success |
| Snapshot/state read failed or content identity indeterminate | Block | Block | Do not treat failure as absence |
| Verifiable finding reaches fail_on | Block | Warn | Apply existing pin rules only to eligible findings |
| Unverified model finding | Warn | Warn | Cannot mint a manager verification claim |
| Local/registry revocation or unpinnable context secret | Block | Block where that gate applies | Pin cannot override |

fail_on=off suppresses finding-based refusal only; it does not disable canary, egress, invalid configuration or strict backend-availability checks. Pins cannot waive these operational controls. Preserve curator's exit convention: 0 for permitted/advisory outcomes, 1 for audit/publication/configuration-load failures, and 2 for usage errors such as a forbidden token option (cmd/curator/main.go:54–58, 352–361). Reporting must distinguish warnings from success coverage. Include a stable backend status, effective adapter/model identity, cache provenance and measured coverage (for example 1/1 selected analyzers, 8/8 required files), not just a clean message. Report unknown when enumeration failed.

Dry-run applies the same policy and can perform permitted analysis in private temporary state, but persists no verdict, pin, response, raw prompt or auth copy. No changes to already defined special diagnostic-only closure behavior.

#### 7. Cache identity and migration

Never reuse an existing static verdict labeled codex/claude/another backend as evidence of backend execution. Introduce a new local cache namespace/schema, containing hash_version, raw content digest, source/capability identity, backend kind/name, nonsecret effective-config digest, adapter/CLI contract identity, requested/resolved model identity when available, prompt/ruleset/redactor/environment-policy versions, request coverage and successful backend status. Hash the structured key into a filename rather than interpolating backend/model strings into a path.

An absent cache may be recomputed. An unreadable, partial or malformed present cache is a distinct state failure, not an absence-triggered authorization path. Old namespace entries are explicitly ineligible by version and may be recomputed without declaring corruption. Revocation, pins, current policy and the static canary run independently of cache hits; changed source classification or backend policy invalidates the relevant key. An eligible successful cache can avoid a new backend canary/extraction, but the report must say cached, not executed in this operation.

Cache failures/incomplete runs never become empty successful findings. Use private bounded records and atomic writes; a failed persistence attempt may report a valid in-memory result with a cache-write diagnostic, without claiming persistence. New version-2 identities must be computed with the version-2 helper; do not tag legacy digests as version 2. Coordinate with the existing rc.14 hash migration instead of inventing a second migration policy or widening pin authority.

## Security considerations

The hostile inputs are repository bytes, source metadata and analyzer responses. The trusted inputs are the installed manager, shared launch planner, operator-selected executable/tool bindings, machine policy, and the provider CLI's saved authentication facility. Prompt text is data; backend output cannot choose a command, change policy, mint a trusted pin or declare itself verified.

Environment protection limits accidental credential inheritance. It does not stop a malicious trusted executable from reading HOME, querying an OS credential store, or using network access. Passing HOME and provider state paths deliberately retains this boundary. Native tool/MCP/hook suppression reduces repository-driven access, but must be qualified separately from the allowlist. Arbitrary command backends are trusted operator code, with no implicit sandbox claim.

The token reader checks the opened object to resist path replacement, bounds growth after stat, refuses FIFO/device inputs, and does not leave a descriptor for children. Same-user process inspection, a compromised manager/provider, credential-manager access, and privileged users remain outside its confidentiality guarantee. Environment tokens avoid argv, but are not a promise of secrecy from privileged process inspection.

The public reference implementation is useful for the shared environment predicate, real subprocess fixtures and narrowing mutants. It is not a portable proof: its token reader skips the Unix permission-bit check on Windows; its no-follow fallback uses identity comparison; its native adapter is Codex, not Claude. Curator should adopt the tested invariants, strengthen platform refusal where necessary, and retain its own launch ownership. See the companion's source-specific comparison.

## Compatibility and migration

1. Immediately reject the old literal-token flag in the accepted implementation release; no warning period that continues using the secret. Keep the existing environment name and document safe credential injection without shell-history examples containing literal values. HTTP Bearer transport and signed registry records do not change.
2. Keep null as default and label static-only coverage. Existing non-null configurations now produce actual analysis or the explicit unsupported result. This behavior change needs a release note because the current implementation silently accepts them.
3. Retain manager-config-v1/v2/v3 and their frozen generic backend object shapes. Add a versioned selected-descriptor schema and capability contract; recognized malformed descriptors fail validation. Do not silently assign semantics to historical unversioned opaque descriptors. A migration diagnostic tells the operator to add/review version 1 or select null.
4. No new launch fragment schema, credential copying, profile credential mode, interactive permission mapping, headless curator-run command, or change to Git authentication policy is implied. The shared launch layer needs a typed audit plan extension and its own release pin before built-in adapters can ship.
5. Propagate effective backend policy through profile audit while keeping mode strict and preserving context-secret detector/waiver semantics. The subject being audited must never supply the profile or hooks used to audit itself.
6. Invalidate legacy backend verdicts by namespace/version. Keep historical files intact unless existing retention policy removes them. Document the rc.14 local identity migration gap and require version-correct new state.

## Specification changes

Normative sketch for the next accepted revision (these are proposed sentences, not current requirements):

1. **CLI credential transport:** “A manager MUST NOT accept a literal publication bearer credential in an argument. It MUST refuse the deprecated token option without echoing its value. A configured token-file MUST be read as one bounded private regular file through a non-inheritable no-follow handle. A failed explicit read MUST NOT fall back to the environment. The input byte limit is 65,536; a bounded limit-plus-one read MUST detect growth.”
2. **Descriptor selection:** “A selected non-null backend MUST resolve to a supported versioned descriptor or produce a typed backend-unavailable result. A manager MUST NOT replace an unsupported selected backend with null or report its analysis as successful. Unknown fields in a recognized descriptor MUST be rejected.”
3. **Environment:** “Every manager-owned backend process, including a canary or capability probe, MUST use the audit environment allowlist. Denial of *_TOKEN, *_KEY, SSH_AUTH_SOCK and GIT_* MUST take precedence over every allow entry and override. Windows matching MUST be case-insensitive. An unset/nil environment that inherits the parent MUST NOT satisfy this requirement. Git transport is outside this audit-child policy.”
4. **Ownership:** “Native audit harness plans MUST be constructed by the shared launch plane under Decision 0019. The manager MUST apply its audit environment and lifetime policy to the resulting plan and MUST refuse incompatible plan requirements; it MUST NOT append an unfiltered environment or re-spell native flags.”
5. **Bounds and egress:** “A backend MUST receive only the bounded declared request, not repository execution access. Cloud egress requires explicit cloud permission, public classification for every contributing source and successful secret redaction. Limits apply to the complete serialized request and adapter input; oversize MUST NOT be truncated into successful coverage.”
6. **Canary and failures:** “Static canary failure and failure of a started backend canary MUST block in all modes. A selected backend unavailable before canary start, or extraction failure, MUST block in strict mode and warn with incomplete coverage in advisory mode. Prohibited egress and indeterminate source reads MUST block regardless of mode or pins.”
7. **Results:** “A backend response MUST be schema-validated and bound to the request and subject identity. A backend's assertion of verifiability MUST NOT by itself make a finding verifiable. Incomplete analysis MUST NOT authorize a successful backend cache record.”
8. **Profiles/cache:** “All source-audit entry points, including profile audit and dry-run, MUST apply effective backend policy. Profiles MUST retain strict mode. Cache identity MUST include the versioned source identity and effective analysis/security contract; a static-only legacy entry MUST NOT attest backend execution.”

Publish schemas for backend-descriptor-v1, audit-request-v1, audit-response-v1 and a new **local** verdict format; do not confuse that verdict with registry audit-record-v1/v2. Use closed objects, explicit integer/string/array bounds and POSIX relative-path grammar. Freeze request canonicalization, response framing, file encoding, source-pattern semantics and named conformance vectors in the spec leaf before implementing their runtime consumers. Version-1 transport is one request per process and one response; no streaming partial verdict protocol.

Adopt a Decision record for CLI credential transport and one for audit backend execution/egress, cross-linking this CIP and clarifying the shared launch-plane extension under Decision 0019. The orchestrator assigns free Decision numbers and publishes the reviewed draft in curator-spec/cips. Adoption and prioritization remain operator actions.

## Implementation plan

The following leaves are a proposed sequence, **not scheduled tasks**. Sizes are relative review units: S = one narrow surface; M = one production path plus its platform/negative vectors.

| Order | Leaf / size | Consumes and produces |
| --- | --- | --- |
| 1 | Spec and Decision adoption, M | Approve the decisions below; freeze the smallest version-1 descriptor/request/response and refusal-vector contract. No runtime authorization before operator acceptance. |
| 2 | Publication token parsing and POSIX reader, M | CLI entry to registry.Publish, exact rejection forms, private/no-follow/size rules, redacted failures. This independently useful first production slice consumes the token contract. |
| 3 | Windows token reader, M | Native handle, reparse, file identity and DACL checks; explicit unsupported refusal until qualified. No mode-bit fallback. |
| 4 | Shared audit runner with command backend, M | Descriptor selection through real CLI audit to bounded stdin and an observed real child, one env policy, canary and failure table; spec-derived negatives. |
| 5 | Shared launch-plane audit purpose, M | Typed native requirements and supported-version qualification for both agent environments; sole ownership of argv/channel spelling. Version-pin this contract. |
| 6 | Codex adapter, M; then Claude adapter, M | Each wires one qualified launch plan into the same runner and protocol; isolated native fixtures and optional separately authorized provider smoke checks. No real credential use required for ordinary conformance. |
| 7 | Egress and redaction pipeline, M | Source classification, complete scope, encoded-byte caps, zero forbidden egress; required before enabling any cloud native/command backend. |
| 8 | Gate/profile/cache integration, M | All audited call paths, profile strictness, dry-run persistence, new cache namespace and correct hash identity; retain revocation and unpinnable findings. |

Dependency constraints: native/cloud activation waits for leaves 4, 5 and 7; no feature is advertised as available while its gates are unwired. Leaf 4 can initially qualify a local trusted command. Leaf 8 must land with any release exposing selected backend support at those entry points. These slices need implementation review, not another default serial research task.

## Test plan

Research measurements are documented separately. The following are **proposed implementation gates; none is claimed to have passed here**.

Drive the built curator executable with a scratch HOME and synthetic values. Use a real helper process that observes argv, stdin, cwd, environment names/selected synthetic markers and inherited handles, then emits protocol results. Do not replace exec with a mock and claim child observation. Existing Go testing is sufficient for manager entry-point tests; native planner tests stay with their owning repository.

| Surface | Required positive and negative vectors | Narrowing mutation that must fail |
| --- | --- | --- |
| Token CLI | Environment/file sources; all legacy option spellings, duplicates, wrong surface, no source, explicit file failure with populated env; no request/child on refusal; output contains no marker | Refuse only equals form; fallback only on ENOENT; disclose only HTTP-error branch |
| File object/privacy | 0400/0600; group-read and other-read independently; final symlink, directory, FIFO, socket/device; swap after precheck; opened-handle permissions; no-follow unavailable | Reject only directories; check path metadata only; deny only other-read; compare device but not file ID |
| Byte/grammar boundaries | 65,536 versus 65,537 raw bytes; growth after stat; exactly one LF/CRLF; bad padding, CR/LF, NUL, UTF-8/non-ASCII, empty value | Admit one extra byte; check stat only; strip all whitespace |
| Environment | Every native/command adapter × canary/extraction/probe; allowed locale/temp/platform names survive; suffix deny even inside LC_*; all Git_* and socket excluded; hostile overrides; unrelated variable absent | Filter extraction only; block _TOKEN but keep _KEY; exempt LC_*; append plan/override env after filtering; case-sensitive Windows deny |
| Git separation | Observed synthetic auth survives permitted Git transport while absent from audit child in one CLI flow | Apply audit filter to every subprocess or exempt one analyzer |
| Request/response | Exact cap and cap+1 after encoding/wrapping; base64/escaping expansion; malformed/trailing/duplicate-key JSON, absent/forged subject identity, bad severity/path/span, huge stderr/stdout/output-file, nonzero exit, timeout/cancel | Count file content only; bound stdout but not output file; accept one missing identity field; kill only direct child |
| Egress | All public/internal × allow_cloud × null/native/command combinations, mixed subjects, path/dev inputs, public default, conflicting identity rules, unreadable classification/redaction; fake cloud child sees redacted payload only | Check selected root but not dependency; classify executable as local; skip redaction on metadata or cache path |
| Canary | Known bad and benign controls, wrong finding, always-clean/always-high responses, unavailable-before-start versus failed-started-canary, no unsafe cloud canary | Accept any high finding; run static only; skip canary for Claude or warm cache policy checks |
| Failure modes/pins | Every row of the failure table in both modes, fail_on=off, pinned and unpinned; static findings retained after backend failure | Treat one failure as empty findings; allow pin to waive one operational gate |
| Call sites/cache | CLI audit; skill/global install; repair/upgrade/dry-run; external source; profile install/update/repair; null→native, model/config/source-policy/version change, old static cache; unreadable versus absent state | Propagate policy only in cmdAudit; leave profile's null literal; omit env-policy/source identity from cache key |

Derive expected adapter/phase/call-site members from the accepted spec and production surface inventory, not from the implementation's registry alone. Publish observed/expected ratios per platform and named killed/attempted narrowing-mutant ratios. No native Windows claim from GOOS compilation or simulated case folding; run actual Windows children and ACL/reparse fixtures. Run actual Linux and macOS file/lifetime fixtures too. Provider model quality and live saved-login compatibility remain separately labeled checks, not inferred from helper-process success.

## Open questions for the operator

1. **Accept option B and its launch ownership?** Recommend yes: Curator owns execution/policy; agents-management owns Codex/Claude flag spelling. If the shared typed audit purpose is not yet available, keep those kinds explicitly unsupported and ship only the accepted earlier slices.
2. **Release priority?** Recommend token transport first, then command runner/egress/profile integration, then native adapters. This is proposed ordering only; no producer or schedule starts from this draft.
3. **Windows file input and privacy strength?** Recommend native DACL/no-follow qualification before enabling --token-file there; otherwise a clear refusal with environment input available. On POSIX, require the brief's group/other read-bit check and document ACL limits; adopting owner-only/no-group-write and ACL checks as stronger mandatory rules needs an explicit conformance scope.
4. **Environment authentication exceptions?** Recommend none, including OPENAI_API_KEY, ANTHROPIC_API_KEY and subscription token variables. Use explicitly provisioned saved provider authentication. If environment-only providers are essential, choose a separately designed credential broker; do not weaken the deny rule.
5. **Local model scope?** Recommend native codex/claude version 1 classified cloud, with local analyzers through an explicitly trusted command descriptor. Add OSS/provider endpoint controls only with a later versioned contract that proves effective locality.
6. **Unsupported backend in advisory mode?** Recommend visible warning plus incomplete coverage, strict refusal in mandatory profile/strict mode, and no null fallback. Malformed recognized configuration remains an error in either mode.
7. **Canary and model findings?** Recommend started-canary failures always block, with fixture-specific verification; model findings block only after manager-owned deterministic verification. This preserves the spec's canary and verifiable-finding distinction without treating model assertions as evidence.
8. **Contract/migration direction?** Recommend versioned selected descriptors and new local cache state, preserving frozen manager/registry/fragment schemas. Spec adoption must settle the exact source-pattern and response-verification vectors before leaves 4–8 consume them.

Accepting these answers implies the spec/Decision leaves and bounded implementation leaves above. Until that acceptance, this packet is ready for review as research only.
