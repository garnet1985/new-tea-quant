#!/usr/bin/env python3
"""
Sync README version badge with core/system.json version.

Usage (from repository root):
  python3 devtools/automation/badge_updating/update_readme_version_badge.py
"""
from __future__ import annotations

import json
import pathlib
import sys

# devtools/automation/badge_updating/this_file -> parents[3] = repo root
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SYSTEM_JSON = REPO_ROOT / "core" / "system.json"
README_MD = REPO_ROOT / "README.md"


def read_core_version() -> str:
    raw = json.loads(SYSTEM_JSON.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("version"), str):
        raise RuntimeError("Cannot read version from core/system.json")
    return raw["version"].strip()


def update_badge(version: str) -> bool:
    content = README_MD.read_text(encoding="utf-8")
    old = content
    found_badge = False

    # Keep existing color suffix, only replace version payload.
    badge_anchor = "https://img.shields.io/badge/version-"
    idx = content.find(badge_anchor)
    if idx >= 0:
        found_badge = True
        start = idx + len(badge_anchor)
        end = content.find("-", start)
        if end > start:
            content = content[:start] + version + content[end:]

    if not found_badge:
        raise RuntimeError("Version badge not found in README.md")

    README_MD.write_text(content, encoding="utf-8")
    return content != old


def main() -> int:
    version = read_core_version()
    changed = update_badge(version)
    print(f"README version badge synced to: {version}")
    return 0 if changed else 0


if __name__ == "__main__":
    sys.exit(main())

