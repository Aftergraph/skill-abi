"""Negative regression tests for the canonical semantic validator.

One test per failure mode. Each asserts the specific error the
canonical validator (sabi.validator.validate_skill) must emit, proving
that `cli/sabi.py validate` rejects the same class of defect.
"""
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi.lockfile import write_lock
from sabi.validator import validate_skill

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "telegram-live-status"


def _copy(tmp_path, name="telegram-live-status"):
    dest = tmp_path / name
    shutil.copytree(EXAMPLE, dest)
    return dest


def _frontmatter(dest):
    parts = (dest / "SKILL.md").read_text(encoding="utf-8").split("---", 2)
    return yaml.safe_load(parts[1]) or {}, parts[2]


def _write_frontmatter(dest, fm, body):
    (dest / "SKILL.md").write_text(
        "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---" + body,
        encoding="utf-8")


def _mutate_frontmatter(dest, **changes):
    fm, body = _frontmatter(dest)
    for k, v in changes.items():
        if v is None:
            fm.pop(k, None)
        else:
            fm[k] = v
    _write_frontmatter(dest, fm, body)


def _mutate_abi(dest, fn):
    abi = yaml.safe_load((dest / "skill.abi.yaml").read_text(encoding="utf-8"))
    fn(abi)
    (dest / "skill.abi.yaml").write_text(
        yaml.safe_dump(abi, sort_keys=False), encoding="utf-8")


def _relock(dest):
    write_lock(dest)


def _assert_error(errors, needle):
    joined = "\n".join(errors)
    assert any(needle in e for e in errors), f"expected {needle!r} in: {joined}"


# ── frontmatter presence ────────────────────────────────────────────

def test_missing_frontmatter_rejected(tmp_path):
    dest = _copy(tmp_path)
    (dest / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")
    level, errors = validate_skill(dest)
    assert level == "INVALID"
    _assert_error(errors, "must start with ---")


def test_missing_description_rejected(tmp_path):
    dest = _copy(tmp_path)
    _mutate_frontmatter(dest, description=None)
    _relock(dest)
    level, errors = validate_skill(dest)
    _assert_error(errors, "description")


# ── name rules ──────────────────────────────────────────────────────

def test_name_uppercase_rejected(tmp_path):
    dest = _copy(tmp_path, name="Telegram-live-status")
    _mutate_frontmatter(dest, name="Telegram-live-status")
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "lowercase alnum/hyphen")


def test_name_too_long_rejected(tmp_path):
    long_name = "a" * 65
    dest = _copy(tmp_path, name=long_name)
    _mutate_frontmatter(dest, name=long_name)
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "name length 65 not in 1..64")


def test_name_leading_hyphen_rejected(tmp_path):
    dest = _copy(tmp_path, name="-telegram")
    _mutate_frontmatter(dest, name="-telegram")
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "no leading/trailing hyphen")


def test_name_trailing_hyphen_rejected(tmp_path):
    dest = _copy(tmp_path, name="telegram-")
    _mutate_frontmatter(dest, name="telegram-")
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "no leading/trailing hyphen")


def test_name_consecutive_hyphens_rejected(tmp_path):
    dest = _copy(tmp_path, name="tele--gram")
    _mutate_frontmatter(dest, name="tele--gram")
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "no consecutive '--'")


def test_name_directory_mismatch_rejected(tmp_path):
    dest = _copy(tmp_path)
    _mutate_frontmatter(dest, name="other-skill")
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "must match skill name")


# ── description bound ───────────────────────────────────────────────

def test_description_too_long_rejected(tmp_path):
    dest = _copy(tmp_path)
    _mutate_frontmatter(dest, description="x" * 1025)
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "description length 1025 exceeds 1024")


# ── ABI schema + references ─────────────────────────────────────────

def test_abi_schema_violation_rejected(tmp_path):
    dest = _copy(tmp_path)
    _mutate_abi(dest, lambda a: a.__setitem__("spec", "wrong/1"))
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "abi schema")


def test_unresolvable_capability_rejected(tmp_path):
    dest = _copy(tmp_path)
    _mutate_abi(dest, lambda a: a["capabilities"].__setitem__(
        "required", ["bogus.cap"]))
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "capability 'bogus.cap' not in SABI vocabulary")


def test_input_schema_reference_missing_rejected(tmp_path):
    dest = _copy(tmp_path)
    _mutate_abi(dest, lambda a: a["inputs"].__setitem__(
        "schema", "schemas/nope.json"))
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "schema file schemas/nope.json missing")


def test_output_schema_reference_missing_rejected(tmp_path):
    dest = _copy(tmp_path)
    _mutate_abi(dest, lambda a: a["outputs"].__setitem__(
        "schema", "schemas/nope.json"))
    _relock(dest)
    _, errors = validate_skill(dest)
    _assert_error(errors, "schema file schemas/nope.json missing")


# ── effects / degradation declared ──────────────────────────────────

def test_effects_missing_rejected(tmp_path):
    dest = _copy(tmp_path)
    (dest / "effects.yaml").unlink()
    _relock(dest)
    level, errors = validate_skill(dest)
    _assert_error(errors, "P2: effects.yaml missing")
    assert level == "P1"


def test_degradation_missing_rejected(tmp_path):
    dest = _copy(tmp_path)
    (dest / "degradation.yaml").unlink()
    _relock(dest)
    level, errors = validate_skill(dest)
    _assert_error(errors, "P3: degradation.yaml missing")
    assert level == "P2"


# ── lockfile integrity ──────────────────────────────────────────────

def test_lockfile_integrity_rejected(tmp_path):
    dest = _copy(tmp_path)
    _relock(dest)
    text = (dest / "SKILL.md").read_text(encoding="utf-8")
    (dest / "SKILL.md").write_text(text + "\ntampered\n", encoding="utf-8")
    _, errors = validate_skill(dest)
    _assert_error(errors, "LOCK: SKILL.md digest mismatch")


def test_lockfile_missing_rejected(tmp_path):
    dest = _copy(tmp_path)
    (dest / "skill.lock").unlink()
    _, errors = validate_skill(dest)
    _assert_error(errors, "skill.lock missing")
