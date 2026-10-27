# Proposed profile skill-plan carrier

The [allocation proposal](../../protocol/profile-skill-plan-proposal.md)
defines the complete closed [context-lock-v5](context-lock-v5.schema.json)
and its embedded [profile-skill-plan-v1](profile-skill-plan-v1.schema.json).
Both use JSON Schema Draft 2020-12. Graph completeness, pin agreement,
ordering, package-derived edges, command exports and digest relations require
the semantic checks in the [separate corpus](../../conformance/profile-skill-plan-v1/README.md).

This is a proposed allocation, not a release or implementation claim.
Version 5 retains the context/MCP and empty settings/precedence meanings of
the current unreleased schema 4. Preserving that shape is a compatibility
proposal. No schema 1, 2 or 4 bytes are changed. There is no runtime marker
or launcher-fragment allocation in this family.

Run `python3 tools/profile_skill_plan.py` for schema and semantic checks,
or `python3 -B -m unittest discover -s tools -p 'test_profile_skill_plan.py' -v`
for their bounded violation controls. Install `requirements-dev.txt` first.
Inputs live in this directory and `conformance/profile-skill-plan-v1/`;
local logs belong under `.temp/`. These tools execute no product lifecycle.
