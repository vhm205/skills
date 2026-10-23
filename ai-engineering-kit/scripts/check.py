"""Static kit contracts. No optional validation or network access here."""
import json
import os
import pathlib
import re
import sys

import yaml

kit = pathlib.Path(sys.argv[1]).resolve()
errors = []


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError(f"duplicate YAML key: {key}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def parse_yaml(text, path):
    try:
        data = yaml.load(text, Loader=UniqueLoader)
        if not isinstance(data, dict):
            raise ValueError("expected a YAML mapping")
        return data
    except (yaml.YAMLError, ValueError, TypeError) as exc:
        errors.append(f"{path.relative_to(kit)}: {exc}")
        return {}


def exists(source, target):
    if not target.exists():
        errors.append(f"{source.relative_to(kit)}: missing {target}")


IGNORED = {'.git', '.worktrees', 'node_modules', 'dist', 'coverage', 'test-results', 'playwright-report', '__pycache__', '.cache'}


def source_files(suffix):
    for root, dirs, files in os.walk(kit, followlinks=False):
        dirs[:] = [d for d in dirs if d not in IGNORED]
        for name in files:
            if name.endswith(suffix):
                yield pathlib.Path(root) / name


known = {p.parent.name for p in kit.glob("skills/*/SKILL.md")}
for path in sorted(source_files(".md")):
    text = path.read_text()
    if text.startswith("---\n"):
        match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.S)
        if not match:
            errors.append(f"{path.relative_to(kit)}: unterminated frontmatter")
            continue
        fields = parse_yaml(match[1], path)
        if path.name == "SKILL.md":
            name, desc = fields.get("name"), fields.get("description")
            if set(fields) != {"name", "description"}:
                errors.append(f"{path}: frontmatter must contain only name and description")
            if name != path.parent.name or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(name)):
                errors.append(f"{path}: invalid or mismatched skill name")
            if not isinstance(desc, str) or not desc.strip() or len(desc) > 1024:
                errors.append(f"{path}: description must be a nonempty string <= 1024 characters")
    elif path.name == "SKILL.md":
        errors.append(f"{path}: missing frontmatter")
    for ref in re.findall(r"`(references/[^`]+)`", text):
        exists(path, path.parent / ref)
    for name in re.findall(r"\.aiek/core/([A-Za-z0-9_.-]+\.md)", text):
        exists(path, kit / "core" / name)
    for ref in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        if not re.match(r"(?:[a-z]+:|#|/)", ref) and "<" not in ref:
            exists(path, path.parent / ref.split("#", 1)[0])

try:
    manifest = json.loads((kit / "manifest.json").read_text())
    entries = manifest["skills"]
    names = [item["name"] for item in entries]
    if set(names) != known or len(names) != len(known):
        errors.append("manifest.json: skill inventory differs from skills/")
    installer = (kit / "scripts/install.sh").read_text()
    installed = re.search(r"SKILLS=\((.*?)\)", installer, re.S).group(1).split()
    if set(installed) != known or len(installed) != len(known):
        errors.append("scripts/install.sh: skill inventory differs from skills/")
    package = json.loads((kit / "package.json").read_text())
    if manifest.get("version") != package.get("version"):
        errors.append(
            "manifest.json: version differs from package.json "
            f"({manifest.get('version')} != {package.get('version')})")
    profiles = manifest.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        errors.append("manifest.json: profiles must be a non-empty mapping")
    else:
        roles = {item["name"]: item.get("role") for item in entries}
        discovery = {name for name, role in roles.items() if role == "discovery"}
        expected = {
            "core": known - discovery,
            "discovery": discovery,
            "full": set(known),
        }
        for profile_name, members in profiles.items():
            if not isinstance(members, list) or not members:
                errors.append(
                    f"manifest.json: profile '{profile_name}' must be a non-empty list")
                continue
            if len(members) != len(set(members)):
                errors.append(f"manifest.json: profile '{profile_name}' has duplicate entries")
            unknown = set(members) - known
            if unknown:
                errors.append(
                    f"manifest.json: profile '{profile_name}' has unknown skills: {sorted(unknown)}")
            if profile_name in expected and set(members) != expected[profile_name]:
                errors.append(
                    f"manifest.json: profile '{profile_name}' must be exactly "
                    f"{len(expected[profile_name])} skills "
                    f"({', '.join(sorted(expected[profile_name]))})")
        for required_profile in ("core", "discovery", "full"):
            if required_profile not in profiles:
                errors.append(f"manifest.json: missing profile '{required_profile}'")
    for script in manifest.get("scripts", []):
        exists(kit / "manifest.json", kit / script)
    for entry in entries:
        exists(kit / "manifest.json", kit / entry["path"] / "SKILL.md")
    for group in ("extensions", "presets", "workflows"):
        for ref in manifest["speckit"][group]:
            exists(kit / "manifest.json", kit / ref)
except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
    errors.append(f"manifest.json: {exc}")
    manifest = {}

for path in sorted(source_files(".yml")):
    data = parse_yaml(path.read_text(), path)
    if path.name not in ("extension.yml", "preset.yml", "workflow.yml"):
        continue
    if data.get("schema_version") != "1.0":
        errors.append(f"{path}: schema_version must be '1.0'")
    if data.get("requires", {}).get("speckit_version") != manifest.get("speckit", {}).get("requires"):
        errors.append(f"{path}: Spec Kit version requirement differs from manifest.json")
    for kind in ("commands", "templates"):
        for entry in data.get("provides", {}).get(kind, []):
            target = path.parent / entry["file"]
            exists(path, target)
            if entry.get("strategy") == "wrap" and target.exists():
                if target.read_text().count("{CORE_TEMPLATE}") != 1:
                    errors.append(f"{target}: wrap must contain exactly one CORE_TEMPLATE")
    if path.name == "extension.yml":
        commands = {c["name"] for c in data.get("provides", {}).get("commands", [])}
        for hooks in data.get("hooks", {}).values():
            for hook in hooks if isinstance(hooks, list) else [hooks]:
                if hook.get("command") not in commands:
                    errors.append(f"{path}: hook references unknown command {hook.get('command')}")

if errors:
    print("\n".join("FAIL " + e for e in errors))
    sys.exit(1)
print(f"OK: {len(known)} skills; YAML, references, inventories and wrappers consistent")
