"""Keep the draft Skillfile source extension independent of post-rc.10 core clauses."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

BASELINE_TAG = "v1.0.0-rc.10"
SCHEMA_ROOT = "schemas/skillfile-sources-v1"
PROTOCOL_PATHS = (
    "protocol/skillfile-sources.md",
    "protocol/repository-transport.md",
)
CLAUSE_DOCUMENTS = {
    "core": "protocol/core.md",
    "registry": "protocol/registry.md",
    "manager": "profiles/manager.md",
    "environments": "protocol/environments.md",
}

_NUMBER = r"\d+(?:\.\d+)*"
_RANGE = rf"{_NUMBER}(?:\s*(?:[–—-]|\bto\b)\s*{_NUMBER})?"
_CITATION = re.compile(
    rf"\b(?P<document>core|registry|manager|environments)\s+"
    rf"(?:(?:sections?|§§?)\s*)?(?P<sections>{_RANGE}"
    rf"(?:\s*(?:,|\band\b)\s*{_RANGE})*)",
    re.IGNORECASE,
)
_HEADING = re.compile(r"^\s*#{1,6}\s+(\d+(?:\.\d+)*)(?=\b|\.)", re.MULTILINE)

CONDITIONAL_CITATION_ALLOWLIST = {
    (
        "protocol/skillfile-sources.md",
        (
            "Machine-global Skillfiles follow [environments §9.4 profile locks]"
            "(environments.md#94-profile-scoped-skills-and-migration) when the manager "
            "implements that capability."
        ),
    ): (
        "This sentence describes the optional machine-global profile-lock capability. "
        "Partial clients implementing the rc.10 core baseline do not acquire that capability."
    ),
}


class GateError(Exception):
    """An input could not be checked with the required baseline evidence."""


def _run_git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        check=False,
    )


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise GateError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def _load_json(source: bytes) -> object:
    try:
        return json.loads(source.decode("utf-8"), object_pairs_hook=_unique_object)
    except UnicodeDecodeError as exc:
        raise GateError(f"invalid UTF-8 JSON: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise GateError(f"invalid JSON: {exc}") from exc


def _baseline_file(root: Path, relative_path: str, *, allow_missing: bool = False) -> bytes | None:
    result = _run_git(root, "show", f"{BASELINE_TAG}:{relative_path}")
    if result.returncode == 0:
        return result.stdout
    if allow_missing:
        listed = _run_git(root, "ls-tree", "-r", "--name-only", BASELINE_TAG, "--", relative_path)
        if listed.returncode == 0 and not listed.stdout.strip():
            return None
    detail = result.stderr.decode("utf-8", errors="replace").strip()
    raise GateError(f"cannot read {relative_path} at {BASELINE_TAG}: {detail}")


def _skip_space(source: bytes, index: int) -> int:
    while index < len(source) and source[index] in b" \t\r\n":
        index += 1
    return index


def _string_end(source: bytes, index: int) -> int:
    if source[index] != ord('"'):
        raise GateError("invalid JSON string while extracting a raw definition")
    index += 1
    while index < len(source):
        byte = source[index]
        if byte == ord("\\"):
            index += 2
        elif byte == ord('"'):
            return index + 1
        else:
            index += 1
    raise GateError("unterminated JSON string while extracting a raw definition")


def _value_end(source: bytes, index: int) -> int:
    index = _skip_space(source, index)
    if index >= len(source):
        raise GateError("missing JSON value while extracting a raw definition")
    start = source[index]
    if start == ord('"'):
        return _string_end(source, index)
    if start == ord("{"):
        index = _skip_space(source, index + 1)
        if source[index] == ord("}"):
            return index + 1
        while True:
            index = _string_end(source, index)
            index = _skip_space(source, index)
            if source[index] != ord(":"):
                raise GateError("invalid JSON object while extracting a raw definition")
            index = _value_end(source, index + 1)
            index = _skip_space(source, index)
            if source[index] == ord("}"):
                return index + 1
            if source[index] != ord(","):
                raise GateError("invalid JSON object while extracting a raw definition")
            index = _skip_space(source, index + 1)
    if start == ord("["):
        index = _skip_space(source, index + 1)
        if source[index] == ord("]"):
            return index + 1
        while True:
            index = _value_end(source, index)
            index = _skip_space(source, index)
            if source[index] == ord("]"):
                return index + 1
            if source[index] != ord(","):
                raise GateError("invalid JSON array while extracting a raw definition")
            index = _skip_space(source, index + 1)
    while index < len(source) and source[index] not in b",]} \t\r\n":
        index += 1
    return index


def _object_member_span(source: bytes, start: int, wanted: str) -> tuple[int, int] | None:
    index = _skip_space(source, start)
    if source[index] != ord("{"):
        return None
    index = _skip_space(source, index + 1)
    if source[index] == ord("}"):
        return None
    while True:
        key_start = index
        key_end = _string_end(source, key_start)
        try:
            key = json.loads(source[key_start:key_end].decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GateError(f"invalid JSON object key while extracting a raw definition: {exc}") from exc
        index = _skip_space(source, key_end)
        if source[index] != ord(":"):
            raise GateError("invalid JSON object while extracting a raw definition")
        value_start = _skip_space(source, index + 1)
        value_end = _value_end(source, value_start)
        if key == wanted:
            return value_start, value_end
        index = _skip_space(source, value_end)
        if source[index] == ord("}"):
            return None
        if source[index] != ord(","):
            raise GateError("invalid JSON object while extracting a raw definition")
        index = _skip_space(source, index + 1)


def _array_item_span(source: bytes, start: int, wanted: int) -> tuple[int, int] | None:
    index = _skip_space(source, start)
    if source[index] != ord("["):
        return None
    index = _skip_space(source, index + 1)
    item_index = 0
    if source[index] == ord("]"):
        return None
    while True:
        value_start = index
        value_end = _value_end(source, value_start)
        if item_index == wanted:
            return value_start, value_end
        item_index += 1
        index = _skip_space(source, value_end)
        if source[index] == ord("]"):
            return None
        if source[index] != ord(","):
            raise GateError("invalid JSON array while extracting a raw definition")
        index = _skip_space(source, index + 1)


def _pointer_tokens(fragment: str) -> list[str]:
    decoded = unquote(fragment)
    if not decoded:
        return []
    if not decoded.startswith("/"):
        raise GateError(f"unsupported non-JSON-Pointer fragment #{fragment}")
    tokens = []
    for token in decoded[1:].split("/"):
        if re.search(r"~(?![01])", token):
            raise GateError(f"invalid JSON Pointer escape in #{fragment}")
        tokens.append(token.replace("~1", "/").replace("~0", "~"))
    return tokens


def _raw_pointer_span(source: bytes, fragment: str) -> tuple[int, int] | None:
    _load_json(source)
    tokens = _pointer_tokens(fragment)
    if not tokens:
        return 0, len(source)
    span = (0, _value_end(source, 0))
    for token in tokens:
        start, _ = span
        if source[_skip_space(source, start)] == ord("{"):
            span = _object_member_span(source, start, token)
        elif source[_skip_space(source, start)] == ord("["):
            if not re.fullmatch(r"0|[1-9]\d*", token):
                return None
            span = _array_item_span(source, start, int(token))
        else:
            return None
        if span is None:
            return None
    return span


def _resolved_schema_target(schema_path: str, reference: str) -> tuple[str, str] | None:
    try:
        parts = urlsplit(reference)
    except ValueError as exc:
        raise GateError(f"invalid schema reference {reference!r}: {exc}") from exc
    if not parts.path:
        return None
    path = unquote(parts.path)
    if parts.scheme or parts.netloc:
        marker = "/schemas/v1/"
        marker_index = path.find(marker)
        if marker_index < 0:
            return None
        target = posixpath.normpath("schemas/v1/" + path[marker_index + len(marker) :])
    elif path.startswith("/"):
        target = posixpath.normpath(path.lstrip("/"))
    elif path == "schemas/v1" or path.startswith("schemas/v1/"):
        target = posixpath.normpath(path)
    else:
        target = posixpath.normpath(posixpath.join(posixpath.dirname(schema_path), path))
    if target != "schemas/v1" and not target.startswith("schemas/v1/"):
        return None
    if parts.query:
        raise GateError(f"unsupported query in local schema reference {reference!r}")
    return target, parts.fragment


def _walk_refs(value: object, location: str):
    if isinstance(value, dict):
        for key, child in value.items():
            child_location = f"{location}/{key}"
            if key == "$ref":
                yield child_location, child
            else:
                yield from _walk_refs(child, child_location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_refs(child, f"{location}/{index}")


def _section_ids(markdown: bytes) -> set[str]:
    content = markdown.decode("utf-8")
    return set(_HEADING.findall(content))


def _expand_sections(expression: str) -> list[str]:
    pieces = re.split(r"\s*(?:,|\band\b)\s*", expression, flags=re.IGNORECASE)
    expanded: list[str] = []
    for piece in pieces:
        parts = re.split(r"\s*(?:[–—-]|\bto\b)\s*", piece, flags=re.IGNORECASE)
        if len(parts) == 1:
            expanded.append(parts[0])
            continue
        if len(parts) != 2:
            raise GateError(f"unsupported section range {piece!r}")
        start, end = parts
        start_parts = [int(part) for part in start.split(".")]
        end_parts = [int(part) for part in end.split(".")]
        if len(start_parts) == len(end_parts) and start_parts[:-1] == end_parts[:-1]:
            first, last = start_parts[-1], end_parts[-1]
            prefix = ".".join(str(part) for part in start_parts[:-1])
        elif len(start_parts) == len(end_parts) == 1:
            first, last = start_parts[0], end_parts[0]
            prefix = ""
        else:
            expanded.extend((start, end))
            continue
        if last < first or last - first > 100:
            raise GateError(f"unsupported section range {piece!r}")
        expanded.extend(f"{prefix + '.' if prefix else ''}{number}" for number in range(first, last + 1))
    return expanded


def _conditional_allowlist_spans(relative_path: str, text: str) -> tuple[dict[tuple[int, int], str], list[str]]:
    allowed: dict[tuple[int, int], str] = {}
    failures: list[str] = []
    for (allowed_path, clause), reason in CONDITIONAL_CITATION_ALLOWLIST.items():
        if allowed_path != relative_path:
            continue
        pattern = r"\s+".join(re.escape(part) for part in clause.split())
        matches = list(re.finditer(pattern, text))
        if len(matches) > 1:
            failures.append(f"{relative_path}: allowlisted conditional clause occurs more than once")
            continue
        if not matches:
            continue
        clause_match = matches[0]
        citations = list(_CITATION.finditer(text, clause_match.start(), clause_match.end()))
        if len(citations) != 1 or not reason.strip():
            failures.append(f"{relative_path}: conditional citation allowlist entry is malformed")
            continue
        allowed[citations[0].span()] = reason
    return allowed, failures


def _check_schema_refs(root: Path) -> tuple[int, int, list[str]]:
    failures: list[str] = []
    checked = 0
    passed = 0
    schema_root = root / SCHEMA_ROOT
    schema_files = sorted(schema_root.rglob("*.json")) if schema_root.is_dir() else []
    if not schema_files:
        return 0, 0, [f"no JSON schemas found under {SCHEMA_ROOT}"]

    baseline_cache: dict[str, bytes] = {}
    for current_schema in schema_files:
        schema_rel = current_schema.relative_to(root).as_posix()
        try:
            current_bytes = current_schema.read_bytes()
            current_json = _load_json(current_bytes)
        except (OSError, GateError) as exc:
            failures.append(f"{schema_rel}: cannot read valid UTF-8 JSON: {exc}")
            continue
        for location, reference in _walk_refs(current_json, "$"):
            if not isinstance(reference, str):
                failures.append(f"{schema_rel}{location}: $ref must be a string")
                continue
            try:
                target = _resolved_schema_target(schema_rel, reference)
            except GateError as exc:
                failures.append(f"{schema_rel}{location}: {exc}")
                continue
            if target is None:
                continue
            checked += 1
            target_path, fragment = target
            try:
                current_target = root.joinpath(*PurePosixPath(target_path).parts).read_bytes()
            except OSError as exc:
                failures.append(f"{schema_rel} $ref {reference!r}: current target {target_path} is unreadable: {exc}")
                continue
            try:
                if target_path not in baseline_cache:
                    baseline = _baseline_file(root, target_path)
                    assert baseline is not None
                    baseline_cache[target_path] = baseline
                baseline_target = baseline_cache[target_path]
                current_span = _raw_pointer_span(current_target, fragment)
                baseline_span = _raw_pointer_span(baseline_target, fragment)
            except (GateError, AssertionError) as exc:
                failures.append(f"{schema_rel} $ref {reference!r}: {exc}")
                continue
            if current_span is None:
                failures.append(f"{schema_rel} $ref {reference!r}: target is absent from current {target_path}")
                continue
            if baseline_span is None:
                failures.append(f"{schema_rel} $ref {reference!r}: target is absent from {BASELINE_TAG}:{target_path}")
                continue
            current_definition = current_target[current_span[0] : current_span[1]]
            baseline_definition = baseline_target[baseline_span[0] : baseline_span[1]]
            if current_definition != baseline_definition:
                current_hash = hashlib.sha256(current_definition).hexdigest()
                baseline_hash = hashlib.sha256(baseline_definition).hexdigest()
                failures.append(
                    f"{schema_rel} $ref {reference!r}: definition differs from {BASELINE_TAG} "
                    f"(candidate sha256 {current_hash}, baseline sha256 {baseline_hash})"
                )
                continue
            passed += 1
    if checked == 0:
        failures.append(f"no $ref from {SCHEMA_ROOT} into schemas/v1 was found")
    return passed, checked, failures


def _check_protocol_citations(root: Path) -> tuple[int, int, int, int, list[str], list[str]]:
    failures: list[str] = []
    citations = 0
    checked_clauses = 0
    passed_clauses = 0
    conditional_exceptions = 0
    exception_reasons: set[tuple[str, str]] = set()
    clause_cache: dict[str, set[str]] = {}
    for relative_path in PROTOCOL_PATHS:
        try:
            text = (root / relative_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(f"{relative_path}: cannot read UTF-8 protocol text: {exc}")
            continue
        allowlisted_spans, allowlist_failures = _conditional_allowlist_spans(relative_path, text)
        failures.extend(allowlist_failures)
        for match in _CITATION.finditer(text):
            citations += 1
            document = match.group("document").lower()
            try:
                sections = _expand_sections(match.group("sections"))
            except GateError as exc:
                failures.append(f"{relative_path}:{text.count(chr(10), 0, match.start()) + 1}: {exc}")
                continue
            exception_reason = allowlisted_spans.get(match.span())
            if exception_reason is not None:
                conditional_exceptions += len(sections)
                exception_reasons.add((relative_path, exception_reason))
                continue
            checked_clauses += len(sections)
            if document not in clause_cache:
                baseline_path = CLAUSE_DOCUMENTS[document]
                try:
                    baseline_doc = _baseline_file(root, baseline_path, allow_missing=True)
                except GateError as exc:
                    failures.append(str(exc))
                    clause_cache[document] = set()
                else:
                    try:
                        clause_cache[document] = _section_ids(baseline_doc) if baseline_doc is not None else set()
                    except UnicodeDecodeError as exc:
                        failures.append(f"{baseline_path} at {BASELINE_TAG} is not UTF-8: {exc}")
                        clause_cache[document] = set()
            baseline_sections = clause_cache[document]
            line = text.count("\n", 0, match.start()) + 1
            for section in sections:
                if section not in baseline_sections:
                    failures.append(
                        f"{relative_path}:{line}: {document} section {section} is not present at {BASELINE_TAG}; "
                        "only the exact conditional-capability citation allowlist can exempt a post-baseline clause"
                    )
                else:
                    passed_clauses += 1
    if citations == 0:
        failures.append(f"no numbered core/registry/manager/environments citations found in {', '.join(PROTOCOL_PATHS)}")
    exception_notes = [
        f"Conditional citation exception at {path}: {reason}"
        for path, reason in sorted(exception_reasons)
    ]
    return citations, checked_clauses, passed_clauses, conditional_exceptions, failures, exception_notes


def check_repository(root: Path) -> tuple[list[str], list[str]]:
    root = root.resolve()
    if not root.is_dir():
        return [], [f"repository root is not a directory: {root}"]
    tag_check = _run_git(root, "rev-parse", "--verify", f"{BASELINE_TAG}^{{commit}}")
    if tag_check.returncode != 0:
        detail = tag_check.stderr.decode("utf-8", errors="replace").strip()
        return [], [f"required baseline tag {BASELINE_TAG} is unavailable: {detail}"]

    ref_passed, ref_checked, ref_failures = _check_schema_refs(root)
    citations, clause_count, clause_passed, conditional_exceptions, prose_failures, exception_notes = (
        _check_protocol_citations(root)
    )
    summary = [
        f"Skillfile source schema references: {ref_passed}/{ref_checked} byte-identical to {BASELINE_TAG}",
        (
            f"Protocol cited clauses: {clause_passed}/{clause_count} present at {BASELINE_TAG}; "
            f"{citations} citations found, {conditional_exceptions} exact conditional exception(s) allowlisted"
        ),
        *exception_notes,
    ]
    return summary, ref_failures + prose_failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="repository checkout to check (defaults to this script's repository)",
    )
    args = parser.parse_args(argv)
    try:
        summary, failures = check_repository(args.root)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"independence gate could not complete: {exc}", file=sys.stderr)
        return 1
    for line in summary:
        print(line)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("Skillfile source independence gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
