"""SABI lockfile: create and verify sha256 digests for skill contract files.

The lockfile pins the exact content of every file that forms the
machine-readable contract. Any mutation invalidates the lock.
"""
import json
from pathlib import Path

from sabi.canon import sha256_file

LOCKED_GLOBS = [
    "SKILL.md",
    "skill.abi.yaml",
    "effects.yaml",
    "degradation.yaml",
    "schemas/*.json",
    "scripts/*.py",
    "references/*",
    "bindings/*.yaml",
    "conformance/*.yaml",
]


def locked_files(skill_dir):
    """Return sorted list of files covered by the lock."""
    skill_dir = Path(skill_dir)
    out = []
    for pat in LOCKED_GLOBS:
        out.extend(sorted(skill_dir.glob(pat)))
    return [p for p in out if p.is_file() and p.name != "skill.lock"]


def compute_digests(skill_dir):
    """Compute sha256 digest URIs for all locked files."""
    skill_dir = Path(skill_dir)
    digests = {}
    for p in locked_files(skill_dir):
        rel = p.relative_to(skill_dir).as_posix()
        digests[rel] = "sha256:" + sha256_file(p)
    return digests


def write_lock(skill_dir):
    """Write a fresh skill.lock. Returns the number of files locked."""
    skill_dir = Path(skill_dir)
    digests = compute_digests(skill_dir)
    doc = {
        "lock_version": 1,
        "skill": skill_dir.name,
        "files": digests,
    }
    lock_path = skill_dir / "skill.lock"
    lock_path.write_text(
        json.dumps(doc, indent=2) + "\n", encoding="utf-8"
    )
    return len(digests)


def check_lock(skill_dir, write_lock=False):
    """Verify or write the skill.lock. Returns (ok, errors).

    When write_lock is True, writes a fresh lock and returns (True, []).
    Otherwise verifies existing lock against current files.
    """
    skill_dir = Path(skill_dir)
    if write_lock:
        count = globals()["write_lock"](skill_dir)
        return True, [f"lock written: {count} files"]

    lock_path = skill_dir / "skill.lock"
    errors = []
    if not lock_path.is_file():
        errors.append("LOCK: skill.lock missing (run with --write-lock)")
        return False, errors

    try:
        doc = json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"LOCK: skill.lock invalid JSON: {exc}")
        return False, errors

    current = compute_digests(skill_dir)
    pinned = doc.get("files", {})

    for rel, digest in current.items():
        if pinned.get(rel) != digest:
            errors.append(f"LOCK: {rel} digest mismatch (skill changed, re-lock)")
    for rel in pinned:
        if rel not in current:
            errors.append(f"LOCK: {rel} pinned but file gone")

    return (len(errors) == 0), errors
