"""Offline deterministic extraction from pinned source inputs. No network or upstream execution."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import tomllib
from pathlib import Path

import protected_inventory as policy

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/protected-commands/v1"


def strings(values, label):
    if not isinstance(values, list) or any(not isinstance(x, str) for x in values):
        raise policy.Refusal("invalid_source_" + label)
    for value in values:
        policy.normalize(value)
    return values


def aqua(document):
    if not isinstance(document, dict) or not isinstance(document.get("packages"), list):
        raise policy.Refusal("invalid_aqua")
    names = set()
    nodes = 0

    def walk(node, parent, depth):
        nonlocal nodes
        nodes += 1
        if depth > 32 or nodes > 200_000 or not isinstance(node, dict):
            raise policy.Refusal("aqua_bounds")
        effective = copy.deepcopy(parent)
        # Only command-bearing fields are interpreted. Version/platform conditions are unioned, never evaluated.
        for key in ("type", "name", "repo_owner", "repo_name", "path"):
            if key in node and not isinstance(node[key], str):
                raise policy.Refusal("invalid_aqua_field")
        typ = node.get("type", effective.get("type", ""))
        if typ not in {"github_release", "github_content", "github_archive", "http", "go_install", "go_build", "cargo", "gitlab_release", "forgejo_release"}:
            raise policy.Refusal("unsupported_aqua_type")
        # Relevant default-name reset from the pinned semantic adapter; repo/name persist.
        if node.get("type") and typ in {"github_release", "github_archive", "http", "cargo", "gitlab_release", "forgejo_release"}:
            effective.pop("path", None)
        for key in ("type", "name", "repo_owner", "repo_name", "path"):
            if node.get(key):
                effective[key] = node[key]
        for key in ("files", "build"):
            if key in node and node[key] is not None:
                effective[key] = node[key]
        lists = [effective.get("files", [])]
        build = effective.get("build")
        if build is not None:
            if not isinstance(build, dict):
                raise policy.Refusal("invalid_aqua_build")
            if "files" in build:
                lists.append(build["files"])
        for files in lists:
            if files is None:
                files = []
            if not isinstance(files, list):
                raise policy.Refusal("invalid_aqua_files")
            if files:
                for file in files:
                    if not isinstance(file, dict) or "name" not in file:
                        raise policy.Refusal("invalid_aqua_file")
                    names.update(strings([file["name"]], "aqua_name"))
            else:
                if effective.get("repo_owner") and effective.get("repo_name"):
                    value = effective.get("name") or effective["repo_name"]
                elif typ == "go_install":
                    value = effective.get("path", "")
                else:
                    value = effective.get("name", "")
                if "{{" in value or "}}" in value:
                    raise policy.Refusal("unresolved_name")
                default = value.rstrip("/").rsplit("/", 1)[-1]
                names.update(strings([default], "aqua_default"))
        for key in ("overrides", "version_overrides"):
            children = node.get(key, [])
            if children is None:
                children = []
            if not isinstance(children, list):
                raise policy.Refusal("invalid_aqua_overrides")
            for child in children:
                walk(child, effective, depth + 1)
    for package in document["packages"]:
        walk(package, {}, 0)
    return names, nodes


def mise(files):
    result = {"mise-short": set(), "mise-alias": set(), "mise-bin": set()}
    for name, raw in sorted(files.items()):
        if not re.fullmatch(r"[A-Za-z0-9_.+-]+\.toml", name):
            raise policy.Refusal("invalid_mise_filename")
        try:
            document = tomllib.loads(raw.decode("utf-8", "strict"))
        except (tomllib.TOMLDecodeError, UnicodeError) as exc:
            raise policy.Refusal("invalid_toml") from exc
        result["mise-short"].update(strings([name[:-5]], "mise_short"))
        for key, source in (("aliases", "mise-alias"), ("bins", "mise-bin")):
            result[source].update(strings(document.get(key, []), key))
    return result


def recipe_facts(kind, raw):
    """Synthetic witnesses for reference-only recipes; never contributes bulk GPL/Apple/standard exports."""
    if kind == "coreutils":
        values = raw.split()
        return {"install" if n == "ginstall" else n for n in values if n != "libstdbuf.so"}
    if kind == "bash":
        blocks = re.split(r"(?m)^\$BUILTIN ", raw)[1:]
        return {block.splitlines()[0] for block in blocks if re.search(r"(?m)^\$FUNCTION ", block)}
    if kind == "zsh":
        return set(re.findall(r'BUILTIN\("([^"\\]+)"', raw))
    raise policy.Refusal("reference_only_source")


def read(path, limit=64 * 1024 * 1024):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise policy.Refusal("source_file_bounds")
    return path.read_bytes()


def input_digest(files):
    return policy.sha256(policy.ccj1({name: policy.sha256(raw) for name, raw in sorted(files.items())}))


def extractor_digest():
    return input_digest({name: (ROOT / "tools" / name).read_bytes() for name in
                         ("protected_inventory.py", "protected_inventory_generator.py", "protected_inventory_prepare.rb")})


def generate(inputs: Path, manifest=None):
    manifest = manifest or policy.decode((DATA / "sources.lock.json").read_bytes())
    if manifest["extractor_version"] != policy.EXTRACTOR or manifest["extractor_sha256"] != extractor_digest():
        raise policy.Refusal("extractor_identity")
    aq = {name: read(inputs / "aqua" / name) for name in ("registry.yaml", "registry.json", "LICENSE")}
    mi = {"LICENSE": read(inputs / "mise/LICENSE")}
    for path in sorted((inputs / "mise/registry").glob("*.toml")):
        mi["registry/" + path.name] = read(path, 1024 * 1024)
    pins = manifest["source_pins"]
    for sid, files in (("aqua", aq), ("mise", mi)):
        pin = next(x for x in pins if x["id"] == sid)
        if input_digest(files) != pin["inputs_sha256"]:
            raise policy.Refusal("source_digest")
        if files["LICENSE"] != (DATA / pin["notice"]).read_bytes():
            raise policy.Refusal("source_notice")
    names, nodes = aqua(policy.decode(aq["registry.json"], 64 * 1024 * 1024))
    exports = {"aqua": names, **mise({name.removeprefix("registry/"): raw for name, raw in mi.items() if name.startswith("registry/")})}
    for pin in pins:
        if pin["status"] == "curated-identifiers":
            raw = read(DATA / pin["extraction"])
            if policy.sha256(raw) != pin["inputs_sha256"]:
                raise policy.Refusal("seed_digest")
            lines = raw.decode("ascii").splitlines()
            if lines != sorted(set(lines)) or not raw.endswith(b"\n"):
                raise policy.Refusal("seed_order")
            exports[pin["id"]] = strings(lines, "seed")
    expected = manifest["coverage"]
    counts = {key: len(value) for key, value in exports.items()}
    if counts != expected["counts"] or nodes != expected["aqua_nodes"]:
        raise policy.Refusal("coverage_witness")
    entries = {}
    by_id = {pin["id"]: pin for pin in pins}
    for source, values in exports.items():
        for spelling in values:
            key = policy.normalize(spelling)
            entry = entries.setdefault(key, {"name": key, "spellings": set(), "provenance": set()})
            entry["spellings"].add(spelling)
            entry["provenance"].add((source, by_id[source]["class"]))
    if len(entries) > policy.MAX_KEYS:
        raise policy.Refusal("inventory_bounds")
    artifact = {"schema_version": 1, "inventory_version": manifest["inventory_version"],
                "normalization": policy.NORMALIZATION, "extractor_version": policy.EXTRACTOR,
                "extractor_sha256": manifest["extractor_sha256"], "source_pins": pins,
                "patterns": [{"kind": "prefix", "value": "curator-", "class": "manager"}],
                "entries": [{"name": key, "spellings": sorted(e["spellings"]),
                             "provenance": [{"source": s, "class": c} for s, c in sorted(e["provenance"])]}
                            for key, e in sorted(entries.items())]}
    raw = policy.ccj1(artifact)
    if len(raw) > policy.MAX_BYTES:
        raise policy.Refusal("artifact_too_large")
    for name in expected["required_names"]:
        if policy.normalize(name) not in entries:
            raise policy.Refusal("coverage_witness")
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    raw = generate(args.inputs)
    artifact = policy.decode(raw)
    metadata = policy.ccj1({"schema_version": 1, "command_inventory": {
        "version": artifact["inventory_version"], "sha256": policy.sha256(raw),
        "normalization": policy.NORMALIZATION}, "entry_count": len(artifact["entries"]), "bytes": len(raw)})
    for name, content in (("inventory.json", raw), ("artifact.json", metadata)):
        path = DATA / name
        if args.check:
            if path.read_bytes() != content:
                raise policy.Refusal("regeneration_mismatch")
        else:
            path.write_bytes(content)
    print(json.dumps({"entries": len(policy.decode(raw)["entries"]), "bytes": len(raw), "sha256": policy.sha256(raw)}))


if __name__ == "__main__":
    main()
