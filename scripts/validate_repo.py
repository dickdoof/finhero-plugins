#!/usr/bin/env python3
"""Release checks: manifests parse, catalogs point at real plugins, skills have front matter."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []


def load(path):
    try:
        return json.loads((ROOT / path).read_text())
    except Exception as e:
        errors.append(f"{path}: {e}")
        return {}


claude = load(".claude-plugin/marketplace.json")
codex = load(".agents/plugins/marketplace.json")
claude_names = {p["name"] for p in claude.get("plugins", [])}
codex_names = {p["name"] for p in codex.get("plugins", [])}
if claude_names != codex_names:
    errors.append(f"catalogs differ: claude={sorted(claude_names)} codex={sorted(codex_names)}")

for entry in claude.get("plugins", []):
    base = ROOT / entry["source"]
    for manifest in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        data = load(base.relative_to(ROOT) / manifest)
        if data.get("name") != entry["name"]:
            errors.append(f"{entry['name']}/{manifest}: name mismatch")
    codex_manifest = load(base.relative_to(ROOT) / ".codex-plugin/plugin.json")
    if not re.fullmatch(r"\d{4}\.\d{1,2}\.\d+", codex_manifest.get("version", "")):
        errors.append(f"{entry['name']}: codex version must be YEAR.MONTH.PATCH")
    skills = list((base / "skills").glob("*/SKILL.md"))
    if not skills:
        errors.append(f"{entry['name']}: no skills")
    for skill in skills:
        text = skill.read_text()
        match = re.match(r"---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n", text, re.S)
        if not match:
            errors.append(f"{skill.relative_to(ROOT)}: missing front matter")
        elif match.group(1) != skill.parent.name:
            errors.append(f"{skill.relative_to(ROOT)}: name must match folder")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print("ok")
