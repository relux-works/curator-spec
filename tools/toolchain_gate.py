"""Toolchain requirement, registry and guidance gates.

Decision 0007 fixes the closed toolchain requirement, the two-stage preflight,
the twelve-code taxonomy and the manager-owned guidance catalog. This module
carries the checks that are properties of the whole surface rather than of one
document, so ``tools/validate.py`` can call them as one gate:

* the **wire-surface** gate — an enumeration of the build-command and
  descriptor-target property names of every published schema version, failing on
  a field that names an executable path, toolchain root, URL, mirror, channel or
  track, version manager, install command, environment override, credential,
  keyring, checksum, or trust root. A runtime diagnostic cannot carry this rule,
  because a field that does not exist produces no value to diagnose;
* the **registry** gate — section 6.3 resolution and reachability applied to
  each complete entry's per-operating-system ``primary_relpath`` and ``probe``,
  plus the section 3.1.1 ordering rules for every value classifier;
* the **guidance catalog** gate — coverage, selection, revision monotonicity and
  the section 6.2.1 lifecycle rules;
* the **inventory** gate — the section 8 vector inventory is present in the
  generated corpus, by case identifier.

Every function raises the caller's failure type, which is passed in so this
module stays importable without a cycle.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Iterable

# The closed toolchain identifiers of section 1. ``jdk`` is companion-only and a
# package may never name it, which is why the wire enum omits it.
TOOLCHAIN_REGISTRY_IDS = ("go", "jdk", "kotlin", "rust", "swift")
TOOLCHAIN_WIRE_IDS = ("go", "kotlin", "rust", "swift")
# The registry is the only mapping from a driver to a toolchain, and it is never
# derived from a driver name, a language name, a file extension, or package
# data. Protocol 1.0 admits exactly the two Go identifiers, so the shipped
# registry declares exactly this mapping; ``check_registry`` proves the two
# agree, which is what keeps the ``id_not_primary`` check from drifting into a
# second, unreviewed mapping.
DRIVER_PRIMARY_TOOLCHAIN: dict[str, str] = {
    "go-repository-v1": "go",
    "go-v1": "go",
}

# Section 6.1 is the identity mapping on the ``build_toolchain_`` suffix, so the
# reason set is the code set and cannot drift as codes are added.
TOOLCHAIN_REASONS: dict[str, str] = {
    "changed": "configuration",
    "incompatible": "host",
    "metadata_mismatch": "host",
    "package_influence_forbidden": "authoring",
    "platform_unsupported": "host",
    "prerelease_unsupported": "host",
    "requirement_invalid": "authoring",
    "requirement_unsatisfiable": "authoring",
    "untested_release": "host",
    "untrusted": "configuration",
    "unavailable": "host",
    "version_undetermined": "host",
}
TOOLCHAIN_CODES = tuple(sorted("build_toolchain_" + reason for reason in TOOLCHAIN_REASONS))
GUIDANCE_CLASSES = ("authoring", "configuration", "host")
GUIDANCE_ID = re.compile(
    r"\Atoolchain\.(?P<toolchain>[a-z]+)\.(?P<reason>[a-z_]+)\.(?P<platform>any|linux|macos|windows)\.r(?P<revision>[1-9][0-9]*)\Z",
    re.ASCII,
)

# The wire surfaces whose property names the release gate enumerates, with the
# published version each belongs to. A definition added here without being added
# to the shared closed member-set table is already a failure of the decision 0008
# boundary; this gate is the second, name-kind reading of the same surface.
WIRE_SURFACE_DEFINITIONS: dict[str, tuple[str, ...]] = {
    "buildCommandV6": ("manifest 6", "manifest 7"),
    "buildCommandV8": ("manifest 8",),
    "repositoryBuildCommandV1": ("manifest 7",),
    "repositoryBuildCommandV2": ("manifest 8",),
    "skillBuildTargetV1": ("descriptor 1",),
    "skillBuildTargetV2": ("descriptor 2",),
    "toolchainRequirementV1": ("manifest 8", "descriptor 2"),
    "toolchainVersionConstraintV1": ("manifest 8", "descriptor 2"),
}
# Name fragments that would make a wire field a resolution input rather than a
# version-domain assertion. Matching is on word-ish fragments of the property
# name, so ``toolchain_root`` and ``rootDir`` are both caught.
FORBIDDEN_WIRE_NAME_FRAGMENTS = (
    "argv",
    "channel",
    "checksum",
    "command",
    "credential",
    "digest",
    "download",
    "env",
    "exec",
    "flag",
    "hook",
    "install",
    "keyring",
    "manager",
    "mirror",
    "path",
    "plugin",
    "root",
    "secret",
    "shim",
    "signing",
    "sysroot",
    "token",
    "track",
    "trust",
    "uri",
    "url",
)
# The single exemption, with its reason. ``build_root`` is a relative path
# *inside* the already-validated source snapshot, constrained by the portable
# path grammar and by the containment rule; it never names a toolchain root, and
# it predates this contract on descriptor schema 1.
WIRE_NAME_EXEMPTIONS: dict[str, str] = {
    "build_root": "a snapshot-relative source root, never a toolchain root",
}

# The section 8 inventory, by case identifier. Presence is checked against the
# generated corpus, so a case that is dropped from the generator is caught even
# though nothing else references its number.
REQUIRED_INVENTORY_CASES: tuple[str, ...] = (
    tuple(str(number) for number in range(1, 70))
    + ("70", "71")
    + tuple(str(number) for number in range(72, 85))
    + ("84a", "84b")
    + tuple(str(number) for number in range(85, 123))
    + ("122a", "122b", "122c", "122d", "122e", "122f", "122g")
    + ("123", "124", "124a", "125", "126")
    + ("126a", "126b", "126c", "126d")
    + ("127", "127a", "127b", "127c", "127d", "127e")
)

# The landed section 4.2.1.2 boundary probe. Its own case tables are the
# observed upstream column the fixture's authored one is checked against.
BOUNDARY_PROBE = Path("tools") / "toolchain-boundary-probe" / "main.go"
PROBE_CASE = re.compile(
    r'\{"(?P<value>(?:[^"\\]|\\.)*)",\s*(?P<class>\d+),\s*"[^"]*",\s*'
    r"(?P<disposition>compared|mismatch|forbidden),",
    re.ASCII,
)
# The probe names three dispositions; the contract names two, because its
# `mismatch` is a `compared` class whose outcome is the unclassifiable token.
PROBE_DISPOSITIONS = {
    "compared": ("compared", False),
    "mismatch": ("compared", True),
    "forbidden": ("forbidden", False),
}

TOOLCHAIN_VECTOR_FILES = (
    "toolchain-preflight.json",
    "toolchain-registry.json",
    "toolchain-guidance-catalog.json",
    "toolchain-go-metadata.json",
    "toolchain-diagnostics.json",
)


def _fragments(name: str) -> set[str]:
    """Split a property name into lowercase word fragments."""
    return {part for part in re.split(r"[^a-z]+", name.lower()) if part}


def _property_names(node: Any, found: set[str]) -> None:
    """Collect every property name reachable inside one definition."""
    if isinstance(node, dict):
        properties = node.get("properties")
        if isinstance(properties, dict):
            found.update(properties)
        for key, value in node.items():
            if key == "properties" and isinstance(value, dict):
                for nested in value.values():
                    _property_names(nested, found)
                continue
            _property_names(value, found)
    elif isinstance(node, list):
        for item in node:
            _property_names(item, found)


def check_wire_surface(common: Any, fail: Callable[[str], Exception]) -> dict[str, list[str]]:
    """Enumerate the published wire property names and reject resolution inputs.

    The closed-field-set constraint is an authoring obligation on this
    specification rather than a runtime code, which is exactly what makes it
    enforceable here: the gate reads the shipped schemas, not a package.
    """
    definitions = common["$defs"]
    enumerated: dict[str, list[str]] = {}
    for name, versions in sorted(WIRE_SURFACE_DEFINITIONS.items()):
        definition = definitions.get(name)
        if definition is None:
            raise fail(f"wire surface definition {name} is missing, but {', '.join(versions)} publish it")
        found: set[str] = set()
        _property_names(definition, found)
        if not found:
            raise fail(f"wire surface definition {name} declares no property at all")
        enumerated[name] = sorted(found)
        for property_name in sorted(found):
            if property_name in WIRE_NAME_EXEMPTIONS:
                continue
            hit = sorted(_fragments(property_name).intersection(FORBIDDEN_WIRE_NAME_FRAGMENTS))
            if hit:
                raise fail(
                    f"{name} ({', '.join(versions)}) publishes property {property_name!r}, "
                    f"which names a resolution input: {', '.join(hit)}"
                )
    return enumerated


def _operating_systems(entry: Any) -> list[str]:
    return sorted({pair["operating_system"] for pair in entry.get("platforms", [])})


def complete_registry_entries(registry: Any) -> dict[str, Any]:
    return {
        entry["toolchain_id"]: entry
        for entry in registry.get("entries", [])
        if entry.get("status") == "complete"
    }


def check_registry(registry: Any, fail: Callable[[str], Exception]) -> None:
    """Section 6.3 resolution and reachability, applied to the registry itself.

    This is what makes the Stage A step 2 host-pair check total: every host the
    manager reaches past step 2 has a relpath and a probe by construction, and no
    host outside ``platforms`` has one to resolve.
    """
    seen: set[str] = set()
    for entry in registry.get("entries", []):
        identifier = entry["toolchain_id"]
        if identifier in seen:
            raise fail(f"toolchain registry declares {identifier!r} twice")
        seen.add(identifier)
        if identifier not in TOOLCHAIN_REGISTRY_IDS:
            raise fail(f"toolchain registry declares the unclosed identifier {identifier!r}")
        if entry.get("status") != "complete":
            continue
        systems = _operating_systems(entry)
        if not systems:
            raise fail(f"complete registry entry {identifier!r} declares no platform")
        for table in ("primary_relpath", "probe"):
            declared = sorted(entry.get(table, {}))
            missing = sorted(set(systems) - set(declared))
            if missing:
                raise fail(
                    f"complete registry entry {identifier!r} declares no {table} for {missing}, "
                    "so a host inside its platforms set has nothing to resolve"
                )
            unreachable = sorted(set(declared) - set(systems))
            if unreachable:
                raise fail(
                    f"complete registry entry {identifier!r} declares a {table} for {unreachable}, "
                    "which is outside its platforms set and therefore unreachable"
                )
        expected_algorithm = f"curator-{identifier}-toolchain-v1"
        if entry.get("fingerprint_algorithm") != expected_algorithm:
            raise fail(
                f"complete registry entry {identifier!r} does not carry {expected_algorithm}"
            )
        normalization = entry.get("normalization", {})
        probe_names = {
            vector["name"]
            for vectors in entry.get("probe", {}).values()
            for vector in vectors
        }
        if normalization.get("probe") not in probe_names:
            raise fail(
                f"complete registry entry {identifier!r} normalizes output of a probe it does not declare"
            )
        check_classifiers(identifier, entry.get("metadata_sources", []), fail)
        for driver in entry.get("drivers", []):
            if DRIVER_PRIMARY_TOOLCHAIN.get(driver) != identifier:
                raise fail(
                    f"complete registry entry {identifier!r} claims driver {driver!r}, "
                    "which the closed driver-to-primary mapping does not assign to it"
                )
    declared_drivers = {
        driver
        for entry in registry.get("entries", [])
        for driver in entry.get("drivers", [])
    }
    if declared_drivers != set(DRIVER_PRIMARY_TOOLCHAIN):
        raise fail(
            "the registry driver mapping is not the closed admitted driver set: "
            f"declared {sorted(declared_drivers)}, expected {sorted(DRIVER_PRIMARY_TOOLCHAIN)}"
        )
    if "go" not in seen:
        raise fail("toolchain registry declares no go entry")


def check_requirement(requirement: Any, driver: Any) -> str | None:
    """The two requirement rules JSON Schema cannot express.

    Both are ``build_toolchain_requirement_invalid`` at the validation stage, so
    neither is a schema rejection: the schema admits the closed identifier set
    and the three closed kinds, and the manager decides equality with the
    driver's registry primary and the ordering of a range's own bounds.
    """
    if requirement is None:
        return None
    if not isinstance(requirement, dict):
        return "toolchain requirement is not an object"
    primary = DRIVER_PRIMARY_TOOLCHAIN.get(driver) if isinstance(driver, str) else None
    if primary is not None and requirement.get("id") != primary:
        return (
            f"toolchain id {requirement.get('id')!r} is not the registry primary {primary!r} "
            f"of driver {driver!r}"
        )
    version = requirement.get("version")
    if isinstance(version, dict) and version.get("kind") == "range":
        minimum, below = version.get("min"), version.get("below")
        if isinstance(minimum, str) and isinstance(below, str):
            if _triple(minimum) >= _triple(below):
                return "range min must be strictly below its below bound"
    return None


def _triple(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def check_classifiers(identifier: str, sources: Iterable[Any], fail: Callable[[str], Exception]) -> None:
    """Section 3.1.1: classifiers are ordered, total and forbidden-first."""
    for source in sources:
        for field in source.get("fields", []):
            if field.get("disposition") != "classified":
                continue
            classes = field.get("classes", [])
            label = f"{identifier} {source['path']}#{field['field_path']}"
            names = [item["name"] for item in classes]
            if len(names) != len(set(names)):
                raise fail(f"{label} declares a duplicate value class")
            catch_all = [index for index, item in enumerate(classes) if item.get("catch_all")]
            if catch_all != [len(classes) - 1]:
                raise fail(
                    f"{label} does not end with exactly one catch-all class, so classification is not total"
                )
            if classes[-1]["matches"] != "value":
                raise fail(f"{label} ends with a catch-all that matches no value")
            absence = [index for index, item in enumerate(classes) if item["matches"] == "absence"]
            if absence not in ([], [0]):
                raise fail(
                    f"{label} declares its absence class at {absence}; a field is either absent or "
                    "carries a value, so at most one class matches absence and it is first"
                )
            # The precedence rule is stated over value classes: a class that
            # matches the field not being present classifies no byte string, so
            # it cannot shadow a forbidden one.
            value_classes = [item for item in classes if item["matches"] == "value"]
            seen_other = False
            for item in value_classes:
                if item["disposition"] == "forbidden":
                    if seen_other:
                        raise fail(
                            f"{label} declares the forbidden class {item['name']!r} after a compared or "
                            "ignored one, so the forbidden-before-compared precedence is not true at the "
                            "value level"
                        )
                else:
                    seen_other = True


def _tuple_of(entry: Any) -> tuple[str, str, str]:
    return entry["toolchain_id"], entry["reason"], entry["platform"]


def check_guidance_catalog(
    catalog: Any, registry: Any, fail: Callable[[str], Exception]
) -> None:
    """Sections 6.1 through 6.3: mapping, lifecycle, coverage and reachability."""
    check_guidance_lifecycle(catalog, fail)
    check_guidance_coverage(catalog, registry, fail)


def check_guidance_lifecycle(catalog: Any, fail: Callable[[str], Exception]) -> None:
    """Sections 6.1 and 6.2: mapping, identifier grammar and supersession.

    These are properties of the catalog alone, so they hold for a catalog
    document read on its own, before any registry is in hand.
    """
    entries = catalog.get("entries", [])
    by_identifier: dict[str, Any] = {}
    revisions: dict[tuple[str, str, str], list[int]] = {}
    active: dict[tuple[str, str, str], list[Any]] = {}
    for entry in entries:
        match = GUIDANCE_ID.match(entry["guidance_id"])
        if match is None:
            raise fail(f"guidance identifier {entry['guidance_id']!r} is malformed")
        if entry["guidance_id"] in by_identifier:
            raise fail(f"guidance identifier {entry['guidance_id']!r} is declared twice")
        by_identifier[entry["guidance_id"]] = entry
        if (
            match.group("toolchain") != entry["toolchain_id"]
            or match.group("reason") != entry["reason"]
            or match.group("platform") != entry["platform"]
        ):
            raise fail(
                f"guidance identifier {entry['guidance_id']!r} disagrees with its own tuple"
            )
        expected_class = TOOLCHAIN_REASONS.get(entry["reason"])
        if expected_class is None:
            raise fail(f"guidance entry names the unmapped reason {entry['reason']!r}")
        if entry["guidance_class"] != expected_class:
            raise fail(
                f"{entry['guidance_id']}: guidance_class {entry['guidance_class']!r} is not the "
                f"section 6.1 class {expected_class!r} of its reason"
            )
        key = _tuple_of(entry)
        revisions.setdefault(key, []).append(int(match.group("revision")))
        if entry["active"]:
            active.setdefault(key, []).append(entry)

    origins: dict[tuple[str, str], set[str]] = {}
    for entry in entries:
        origins.setdefault((entry["guidance_class"], entry["reason"]), set()).add(entry["primary_source"])
    for (guidance_class, reason), sources in sorted(origins.items()):
        if len(sources) != 1:
            raise fail(
                f"reason {reason!r} in class {guidance_class!r} draws guidance from more than one origin: {sorted(sources)}"
            )

    for key, found in sorted(revisions.items()):
        if len(found) != len(set(found)):
            raise fail(f"tuple {key} declares a revision twice")
    for key, found in sorted(active.items()):
        if len(found) > 1:
            raise fail(
                f"tuple {key} carries {len(found)} active entries; at most one entry per tuple is active"
            )

    for entry in entries:
        successor = entry.get("superseded_by")
        if successor is None:
            continue
        if entry["active"]:
            raise fail(f"{entry['guidance_id']}: an active entry carries superseded_by")
        target = by_identifier.get(successor)
        if target is None:
            raise fail(f"{entry['guidance_id']}: superseded_by names the absent entry {successor!r}")
        if _tuple_of(target) != _tuple_of(entry):
            raise fail(f"{entry['guidance_id']}: superseded_by names a different tuple")
        this_revision = int(GUIDANCE_ID.match(entry["guidance_id"]).group("revision"))
        that_revision = int(GUIDANCE_ID.match(successor).group("revision"))
        if that_revision <= this_revision:
            raise fail(
                f"{entry['guidance_id']}: superseded_by names revision {that_revision}, "
                "which is not strictly greater"
            )


def check_guidance_coverage(
    catalog: Any, registry: Any, fail: Callable[[str], Exception]
) -> None:
    """Section 6.3: the catalog is total over supported toolchains and reachable.

    Coverage is defined by the selection function rather than alongside it, so
    all three shapes are valid: one ``any`` entry, one exact entry per operating
    system, and a hybrid of a fallback plus overrides.
    """
    entries = catalog.get("entries", [])
    active: dict[tuple[str, str, str], list[Any]] = {}
    for entry in entries:
        if entry["active"]:
            active.setdefault(_tuple_of(entry), []).append(entry)
    complete = complete_registry_entries(registry)
    for identifier, entry in sorted(complete.items()):
        systems = _operating_systems(entry)
        for reason in sorted(TOOLCHAIN_REASONS):
            fallback = active.get((identifier, reason, "any"))
            covered_exactly: list[str] = []
            for operating_system in systems:
                exact = active.get((identifier, reason, operating_system))
                if exact:
                    covered_exactly.append(operating_system)
                elif not fallback:
                    raise fail(
                        f"({identifier}, {reason}) does not resolve for {operating_system}: "
                        "no active exact entry and no active any entry"
                    )
            if fallback and len(covered_exactly) == len(systems):
                raise fail(
                    f"({identifier}, {reason}) carries an active any entry shadowed by active exact "
                    "entries for every registry operating system, so the fallback is unreachable"
                )

    for entry in entries:
        if not entry["active"] or entry["platform"] == "any":
            continue
        registry_entry = complete.get(entry["toolchain_id"])
        if registry_entry is None:
            raise fail(
                f"{entry['guidance_id']}: active exact entry for a toolchain with no complete registry entry"
            )
        if entry["platform"] not in _operating_systems(registry_entry):
            raise fail(
                f"{entry['guidance_id']}: active exact entry for an operating system outside the "
                "toolchain's registry platforms set, so it is unreachable"
            )


def resolve_guidance(catalog: Any, toolchain: str, reason: str, operating_system: str) -> str | None:
    """Section 6.2 selection: exact tuple first, then the ``any`` fallback."""
    for wanted in (operating_system, "any"):
        for entry in catalog.get("entries", []):
            if (
                entry["active"]
                and entry["toolchain_id"] == toolchain
                and entry["reason"] == reason
                and entry["platform"] == wanted
            ):
                return entry["guidance_id"]
    return None


def check_diagnostic_payloads(
    payloads: Iterable[Any], catalog: Any, fail: Callable[[str], Exception]
) -> None:
    """Every emitted diagnostic resolves to an active, revisioned guidance entry."""
    for payload in payloads:
        code = payload["code"]
        if code not in TOOLCHAIN_CODES:
            raise fail(f"diagnostic payload names the unmapped code {code!r}")
        reason = code[len("build_toolchain_") :]
        match = GUIDANCE_ID.match(payload["guidance_id"])
        if match is None:
            raise fail(f"diagnostic payload carries the malformed guidance identifier {payload['guidance_id']!r}")
        if match.group("reason") != reason:
            raise fail(
                f"diagnostic {code} carries guidance for reason {match.group('reason')!r}; "
                "the code-to-reason mapping is the identity"
            )
        if match.group("toolchain") != payload["toolchain_id"]:
            raise fail(f"diagnostic {code} carries guidance for another toolchain")
        entry = next(
            (item for item in catalog["entries"] if item["guidance_id"] == payload["guidance_id"]),
            None,
        )
        if entry is None:
            raise fail(f"diagnostic {code} carries the unpublished identifier {payload['guidance_id']!r}")
        if not entry["active"]:
            raise fail(f"diagnostic {code} carries the retired identifier {payload['guidance_id']!r}")
        for forbidden in ("guidance", "url", "hint", "message"):
            if forbidden in payload:
                raise fail(
                    f"diagnostic {code} carries {forbidden!r}; a code carries a guidance_id and no prose or URL"
                )


def collect_case_identifiers(suite: Path) -> set[str]:
    """Every ``case`` identifier the generated toolchain corpus carries."""
    import json

    found: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            identifier = node.get("case")
            if isinstance(identifier, str):
                found.add(identifier)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for name in TOOLCHAIN_VECTOR_FILES:
        walk(json.loads((suite / "vectors" / name).read_text(encoding="utf-8")))
    return found


def check_inventory(suite: Path, fail: Callable[[str], Exception]) -> None:
    found = collect_case_identifiers(suite)
    missing = [case for case in REQUIRED_INVENTORY_CASES if case not in found]
    if missing:
        raise fail(
            f"the section 8 vector inventory is incomplete: {len(missing)} missing, first {missing[:12]}"
        )


def parse_probe_cases(root: Path, fail: Callable[[str], Exception]) -> dict[tuple[str, str], tuple[int, str, bool]]:
    """The boundary probe's own case tables, by position and value.

    Reading the probe's source rather than its output is deliberate. The probe
    needs a real Go toolchain of a particular family and this check must run on
    any runner, so what is compared here is the two tables' agreement on class
    and disposition. The measurement itself stays the probe's job, and its five
    regression controls stay the guard on the measurement.
    """
    source = root / BOUNDARY_PROBE
    if not source.is_file():
        raise fail(f"the section 4.2.1.2 boundary probe is missing at {BOUNDARY_PROBE}")
    text = source.read_text(encoding="utf-8")
    cases: dict[tuple[str, str], tuple[int, str, bool]] = {}
    for name, position in (("goCases", "go"), ("tcCases", "toolchain")):
        start = text.find(f"var {name} = []probeCase{{")
        if start < 0:
            raise fail(f"the boundary probe declares no {name} table")
        end = text.find("\n}\n", start)
        if end < 0:
            raise fail(f"the boundary probe's {name} table is unterminated")
        block = text[start:end]
        found = list(PROBE_CASE.finditer(block))
        if not found:
            raise fail(f"the boundary probe's {name} table declares no case")
        for match in found:
            value = match.group("value").replace(chr(92) + chr(92), chr(92))
            disposition, unclassifiable = PROBE_DISPOSITIONS[match.group("disposition")]
            cases[(position, value)] = (int(match.group("class")), disposition, unclassifiable)
    return cases


def check_probe_agreement(rows: Iterable[Any], root: Path, fail: Callable[[str], Exception]) -> None:
    """The fixture table agrees with the probe's table on every measured value.

    A fixture table that disagrees with a probe run is a defect in the fixture,
    not in the probe, so the direction of this check matters: the probe's class
    and disposition are authoritative and the fixture is held to them.
    """
    probe = parse_probe_cases(root, fail)
    by_value = {(row["position"], row["value"]): row for row in rows}
    for key, row in sorted(by_value.items()):
        measured = row.get("probe_measured")
        if measured is None:
            raise fail(f"alignment row {key} does not say whether the probe measures it")
        if measured and key not in probe:
            raise fail(
                f"alignment row {key} claims the boundary probe measures it, but the probe's "
                "table does not carry that value"
            )
    for key, (class_number, disposition, unclassifiable) in sorted(probe.items()):
        row = by_value.get(key)
        if row is None:
            raise fail(
                f"the boundary probe measures {key} and the alignment table does not carry it"
            )
        if not row["probe_measured"]:
            raise fail(f"alignment row {key} is marked unmeasured, but the probe measures it")
        if row["class"] != class_number:
            raise fail(
                f"alignment row {key} says class {row['class']}, the probe says {class_number}"
            )
        if row["disposition"] != disposition:
            raise fail(
                f"alignment row {key} says disposition {row['disposition']!r}, "
                f"the probe says {disposition!r}"
            )
        if unclassifiable and row["outcome"] != "unclassifiable":
            raise fail(
                f"alignment row {key} says outcome {row['outcome']!r}, the probe classifies it as "
                "a metadata mismatch"
            )
        if not unclassifiable and disposition == "compared" and row["outcome"] == "unclassifiable":
            raise fail(
                f"alignment row {key} says unclassifiable, the probe classifies it as a comparison"
            )
