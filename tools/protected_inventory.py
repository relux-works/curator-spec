"""Protected-inventory byte/matching oracle and bounded fixture resolver, not Curator admission."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_BYTES = 16 * 1024 * 1024
MAX_KEYS = 100_000
MAX_NAME = 128
NORMALIZATION = "ascii-fold-wrapper-suffix-v1"
SUFFIXES = (".exe", ".com", ".bat", ".cmd", ".ps1")
EXTRACTOR = "protected-command-inventory/1"


class Refusal(ValueError):
    """Stable specification refusal class; the enclosing CLI is owned by L1."""


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out = {}
    for key, value in pairs:
        if key in out:
            raise Refusal("duplicate_json_key")
        out[key] = value
    return out


def _integer(token: str) -> int:
    number = int(token)
    if token == "-0" or abs(number) > 9_007_199_254_740_991:
        raise Refusal("unsafe_number")
    return number


def _noninteger(_: str) -> Any:
    raise Refusal("noninteger_number")


def decode(raw: bytes, limit: int = MAX_BYTES) -> Any:
    if len(raw) > limit:
        raise Refusal("artifact_too_large")
    try:
        value = json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_pairs,
                           parse_int=_integer, parse_float=_noninteger, parse_constant=_noninteger)
        json.dumps(value, ensure_ascii=False).encode("utf-8", "strict")
        return value
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise Refusal("invalid_json") from exc


def ccj1(value: Any) -> bytes:
    # No signature elision: this artifact has no sig field and its WHOLE bytes are hashed.
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                     allow_nan=False).encode("utf-8", "strict")
    decode(raw)
    return raw


def sha256(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def normalize(name: str) -> str:
    if not isinstance(name, str) or not 1 <= len(name) <= MAX_NAME or not re.fullmatch(r"[!-~]+", name):
        raise Refusal("invalid_name")
    if "/" in name or "\\" in name or "{{" in name or "}}" in name:
        raise Refusal("unresolved_name")
    key = name.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))
    while any(key.endswith(suffix) for suffix in SUFFIXES):
        key = key.rsplit(".", 1)[0]
    if not key:
        raise Refusal("invalid_name")
    return key


def export_key(name: str) -> str:
    # Inventory punctuation does not broaden the existing portable export grammar.
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9_-])?", name):
        raise Refusal("invalid_export")
    key = normalize(name)
    if key.split(".", 1)[0] in {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}:
        raise Refusal("invalid_export")
    return key


def load_artifact(raw: bytes, identity: dict[str, Any]) -> dict[str, Any]:
    try:
        return _load_artifact(raw, identity)
    except (TypeError, KeyError, AttributeError) as exc:
        raise Refusal("inventory_shape") from exc


def _load_artifact(raw: bytes, identity: dict[str, Any]) -> dict[str, Any]:
    if set(identity) != {"version", "sha256", "normalization"} or identity["normalization"] != NORMALIZATION:
        raise Refusal("inventory_identity")
    if not isinstance(identity["version"], str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\.[1-9][0-9]*", identity["version"]):
        raise Refusal("inventory_identity")
    artifact = decode(raw)
    if raw != ccj1(artifact) or sha256(raw) != identity["sha256"]:
        raise Refusal("inventory_digest")
    if not isinstance(artifact, dict) or set(artifact) != {"schema_version", "inventory_version", "normalization", "extractor_version", "extractor_sha256", "source_pins", "patterns", "entries"}:
        raise Refusal("inventory_shape")
    if artifact["extractor_version"] != EXTRACTOR:
        raise Refusal("extractor_identity")
    if type(artifact["schema_version"]) is not int or artifact["schema_version"] != 1 or artifact["inventory_version"] != identity["version"] or artifact["normalization"] != NORMALIZATION:
        raise Refusal("inventory_identity")
    entries = artifact["entries"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_KEYS:
        raise Refusal("inventory_bounds")
    names = []
    pins = artifact["source_pins"]
    if not isinstance(pins, list) or not 1 <= len(pins) <= 64:
        raise Refusal("inventory_bounds")
    classes = {"catalogue", "system", "shell", "vcs", "package-manager", "platform", "manager"}
    source_fields = {"id", "repository", "revision", "status", "class", "extraction", "license", "notice", "inputs_sha256"}
    for pin in pins:
        if set(pin) != source_fields or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", pin["id"]) or pin["class"] not in classes:
            raise Refusal("source_shape")
        if pin["status"] not in {"included-mit", "curated-identifiers", "reference-only"}:
            raise Refusal("source_shape")
        for field, bound in (("repository", 512), ("revision", 128), ("extraction", 1024), ("license", 512)):
            if not isinstance(pin[field], str) or not 1 <= len(pin[field]) <= bound or re.search(r"[\x00-\x1f\x7f]", pin[field]):
                raise Refusal("source_shape")
        digest = pin["inputs_sha256"]
        notice = pin["notice"]
        if digest is not None and not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise Refusal("source_shape")
        if notice is not None and not re.fullmatch(r"licenses/[A-Za-z0-9-]+\.txt", notice):
            raise Refusal("source_shape")
        if pin["status"] == "included-mit" and (digest is None or notice is None):
            raise Refusal("source_shape")
        if pin["status"] == "curated-identifiers" and (digest is None or notice is not None):
            raise Refusal("source_shape")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", artifact["extractor_sha256"]):
        raise Refusal("extractor_identity")
    sources = [s["id"] for s in pins]
    if sources != sorted(set(sources)):
        raise Refusal("source_order")
    statuses = {s["id"]: s["status"] for s in pins}
    source_classes = {s["id"]: s["class"] for s in pins}
    for entry in entries:
        if set(entry) != {"name", "spellings", "provenance"} or normalize(entry["name"]) != entry["name"]:
            raise Refusal("entry_shape")
        if not isinstance(entry["spellings"], list) or not 1 <= len(entry["spellings"]) <= 32:
            raise Refusal("inventory_bounds")
        if not entry["spellings"] or entry["spellings"] != sorted(set(entry["spellings"])) or any(normalize(s) != entry["name"] for s in entry["spellings"]):
            raise Refusal("entry_spellings")
        prov = entry["provenance"]
        if not isinstance(prov, list) or not 1 <= len(prov) <= 32:
            raise Refusal("inventory_bounds")
        if any(set(p) != {"source", "class"} or p["class"] not in classes or source_classes.get(p["source"]) != p["class"] for p in prov):
            raise Refusal("entry_provenance")
        if not prov or prov != sorted(prov, key=lambda x: (x["source"], x["class"])) or len({(p["source"], p["class"]) for p in prov}) != len(prov):
            raise Refusal("entry_provenance")
        if any(statuses.get(p["source"]) not in ("included-mit", "curated-identifiers") for p in prov):
            raise Refusal("uncleared_source")
        names.append(entry["name"])
    if names != sorted(set(names)):
        raise Refusal("entry_order")
    if artifact["patterns"] != [{"kind": "prefix", "value": "curator-", "class": "manager"}]:
        raise Refusal("manager_prefix")
    return artifact


@dataclass(frozen=True)
class Directory:
    path: Path
    device: int
    inode: int


@dataclass(frozen=True)
class Forwarder:
    path: str
    device: int
    inode: int
    digest: str
    owner: str
    generation: str


@dataclass(frozen=True)
class Admission:
    # Constructed only by synthetic tests here. Production must consume L1's authority/witness.
    directories: tuple[Directory, ...]
    suffixes: tuple[str, ...] = ("",)
    allowed_link_roots: tuple[Path, ...] = ()
    owned_forwarders: tuple[Forwarder, ...] = ()
    owners: tuple[tuple[str, str, str], ...] = ()


def check_exports(exports: list[str], artifacts: list[dict[str, Any]], admission: Admission | None,
                  shell_names: tuple[str, ...] = (), manager_names: tuple[str, ...] = (),
                  undeclared_surface: bool = False) -> None:
    if undeclared_surface:
        raise Refusal("undeclared_command_surface")
    if not exports:
        return
    if not artifacts:
        raise Refusal("inventory_unavailable")
    keys = [export_key(name) for name in exports]
    if len(keys) != len(set(keys)):
        raise Refusal("ambiguous_export")
    classes: dict[str, set[str]] = {}
    for artifact in artifacts:  # Union locked + current required, never replace locked protection.
        for entry in artifact["entries"]:
            classes.setdefault(entry["name"], set()).update(p["class"] for p in entry["provenance"])
    permanent = {normalize(x) for x in (*shell_names, *manager_names, "curator", "curator-run")}
    for key in keys:
        if key.startswith("curator-") or key in permanent or classes.get(key, set()) & {"shell", "manager"}:
            raise Refusal("reserved_namespace")
    if admission is None or not admission.directories or not 1 <= len(admission.suffixes) <= 6:
        raise Refusal("admission_unavailable")
    if len(admission.directories) > 64 or any(s not in ("", *SUFFIXES) for s in admission.suffixes):
        raise Refusal("admission_unavailable")
    for directory in admission.directories:
        if not directory.path.is_absolute() or ".." in directory.path.parts:
            raise Refusal("admission_unavailable")
        try:
            info = directory.path.lstat()
        except OSError as exc:
            raise Refusal("admission_unavailable") from exc
        if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != (directory.device, directory.inode):
            raise Refusal("admission_changed")
    for name in exports:
        for directory in admission.directories:
            for suffix in admission.suffixes:
                path = directory.path / (name + suffix)
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    continue
                except OSError as exc:
                    raise Refusal("admission_unreadable") from exc
                identity = (str(path), info.st_dev, info.st_ino)
                if stat.S_ISLNK(info.st_mode):
                    try:
                        target = path.resolve(strict=False)
                    except (OSError, RuntimeError) as exc:
                        raise Refusal("admission_unsafe_link") from exc
                    if not any(target.is_relative_to(root) for root in admission.allowed_link_roots):
                        raise Refusal("admission_unsafe_link")
                    try:
                        info = path.stat()
                    except OSError as exc:
                        raise Refusal("admission_unreadable") from exc
                forwarder = next((f for f in admission.owned_forwarders
                                  if (f.path, f.device, f.inode) == identity), None)
                if forwarder is not None:
                    if (forwarder.path, forwarder.owner, forwarder.generation) not in admission.owners:
                        raise Refusal("forwarder_owner_changed")
                    # Only a captured manager wrapper is content-checked, never arbitrary PATH programs.
                    try:
                        with path.open("rb") as stream:
                            raw = stream.read(65537)
                    except OSError as exc:
                        raise Refusal("admission_unreadable") from exc
                    if len(raw) > 65536 or sha256(raw) != forwarder.digest:
                        raise Refusal("forwarder_content_changed")
                    continue
                if stat.S_ISREG(info.st_mode) and (os.name == "nt" or os.access(path, os.X_OK)):
                    raise Refusal("base_path_collision")
    if any(key in classes for key in keys):
        raise Refusal("static_overlap")
