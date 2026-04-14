"""
compile_registry.py
Scans skills/installable-skills/<USER>/*.skill and
       skills/in-progress-skills/<USER>/*.skill,
then writes registry.json.

Version rules:
  - New skill:     starts at 1.0.0
  - Existing skill that changed: patch bump (1.0.0 -> 1.0.1, 1.2.9 -> 1.2.10)
  - Existing skill unchanged:    version left as-is
  - User-bumped version (major or minor changed): preserved as-is, no patch bump on top
"""

import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT       = Path(__file__).resolve().parents[2]
SKILLS_ROOT     = REPO_ROOT / "skills"
STABLE_DIR      = SKILLS_ROOT / "installable-skills"
BETA_DIR        = SKILLS_ROOT / "in-progress-skills"
REGISTRY_PATH   = REPO_ROOT / "registry.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def bump_patch(version: str) -> str:
    """Increment the patch segment of a semver string."""
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version.strip())
    if not match:
        return version  # don't touch non-semver strings
    major, minor, patch = match.groups()
    return f"{major}.{minor}.{int(patch) + 1}"


def get_changed_files() -> set[str]:
    """
    Return the set of .skill file paths (relative to repo root) that differ
    between HEAD~1 and HEAD.  Falls back to all .skill files if git history
    is unavailable (e.g. first commit / shallow clone with depth 1).
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, check=True, cwd=REPO_ROOT,
        )
        changed = {p.strip() for p in result.stdout.splitlines() if p.strip().endswith(".skill")}
        if changed:
            return changed
    except subprocess.CalledProcessError:
        pass

    # Fallback: treat every .skill file as changed
    return {
        str(p.relative_to(REPO_ROOT))
        for p in SKILLS_ROOT.rglob("*.skill")
    }


def extract_skill_metadata(skill_path: Path) -> dict | None:
    """
    Read a .skill file (zip archive) and pull the YAML frontmatter from
    SKILL.md inside it.  Returns a dict with at least 'name' and
    'description', or None if parsing fails.
    """
    try:
        with zipfile.ZipFile(skill_path, "r") as zf:
            # Find SKILL.md anywhere inside the zip
            skill_md_names = [n for n in zf.namelist() if n.endswith("SKILL.md")]
            if not skill_md_names:
                print(f"  [warn] No SKILL.md found in {skill_path.name}", file=sys.stderr)
                return None
            content = zf.read(skill_md_names[0]).decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, KeyError, OSError) as exc:
        print(f"  [warn] Could not read {skill_path.name}: {exc}", file=sys.stderr)
        return None

    # Parse YAML frontmatter between --- delimiters
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        print(f"  [warn] No frontmatter in {skill_path.name}", file=sys.stderr)
        return None

    fm_text = fm_match.group(1)
    meta: dict = {}

    # Minimal YAML key:value parser (handles multiline `>` blocks too)
    current_key = None
    multiline_value: list[str] = []

    def flush_multiline():
        if current_key and multiline_value:
            meta[current_key] = " ".join(multiline_value).strip()

    for line in fm_text.splitlines():
        kv = re.match(r"^(\w[\w-]*):\s*(.*)", line)
        if kv:
            flush_multiline()
            multiline_value = []
            current_key = kv.group(1)
            val = kv.group(2).strip()
            if val and val != ">":
                meta[current_key] = val
            # if val == ">" or val == "", we'll accumulate lines below
        elif current_key and line.startswith("  "):
            multiline_value.append(line.strip())

    flush_multiline()

    if "name" not in meta or "description" not in meta:
        print(f"  [warn] Missing name/description in frontmatter of {skill_path.name}", file=sys.stderr)
        return None

    return meta


def scan_skills() -> list[dict]:
    """
    Walk both skill dirs and return one raw entry per .skill file.
    Structure: skills/<stable|beta>/<USERNAME>/<skill-name>.skill
    """
    entries = []

    for base_dir, status in [(STABLE_DIR, "stable"), (BETA_DIR, "beta")]:
        if not base_dir.exists():
            continue
        for user_dir in sorted(base_dir.iterdir()):
            if not user_dir.is_dir():
                continue
            author = user_dir.name
            for skill_file in sorted(user_dir.glob("*.skill")):
                entries.append({
                    "_path": skill_file,
                    "_rel":  str(skill_file.relative_to(REPO_ROOT)),
                    "author": author,
                    "status": status,
                })

    return entries


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    changed_files = get_changed_files()
    print(f"Changed .skill files detected: {changed_files or '(none — using full scan)'}")

    # Load existing registry keyed by skill name for fast lookup
    existing: dict[str, dict] = {}
    if REGISTRY_PATH.exists():
        try:
            for entry in json.loads(REGISTRY_PATH.read_text()):
                existing[entry["name"]] = entry
        except (json.JSONDecodeError, KeyError):
            print("[warn] Existing registry.json is malformed — starting fresh.", file=sys.stderr)

    raw_skills = scan_skills()
    registry: list[dict] = []

    for raw in raw_skills:
        skill_path: Path = raw["_path"]
        rel_path:   str  = raw["_rel"]

        print(f"Processing: {rel_path}")
        meta = extract_skill_metadata(skill_path)
        if meta is None:
            print(f"  Skipping (could not extract metadata).")
            continue

        name        = meta["name"]
        description = meta["description"]
        author      = raw["author"]
        status      = raw["status"]

        # Version logic
        prev = existing.get(name)
        if prev is None:
            # Brand-new skill
            version = meta.get("version", "1.0.0")
            print(f"  New skill — version {version}")
        else:
            prev_version = prev.get("version", "1.0.0")
            fm_version   = meta.get("version", prev_version)

            # If the frontmatter carries a higher major/minor, the author bumped it manually
            def parse(v):
                m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v.strip())
                return tuple(int(x) for x in m.groups()) if m else (1, 0, 0)

            prev_t = parse(prev_version)
            fm_t   = parse(fm_version)

            if fm_t[:2] > prev_t[:2]:
                # Author bumped major or minor — respect it as-is
                version = fm_version
                print(f"  Author-bumped version: {prev_version} -> {version}")
            elif rel_path in changed_files:
                # File changed, auto patch-bump from the registry version
                version = bump_patch(prev_version)
                print(f"  File changed — patch bump: {prev_version} -> {version}")
            else:
                # No change detected — preserve existing version
                version = prev_version
                print(f"  Unchanged — keeping version {version}")

        registry.append({
            "name":        name,
            "description": description,
            "author":      author,
            "version":     version,
            "status":      status,
        })

    # Stable first, then beta; alphabetical within each group
    registry.sort(key=lambda e: (0 if e["status"] == "stable" else 1, e["name"]))

    REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n")
    print(f"\nWrote {len(registry)} entries to registry.json")


if __name__ == "__main__":
    main()
