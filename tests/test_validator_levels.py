"""Validator level-ladder regression tests (hostile H-001/H-002).

Full fixture -> P3. Removing degradation -> P2 (was mislabeled P1).
Removing effects -> P1 (was unreachable). Removing ABI -> P0.
Garbage dir -> INVALID. Duplicate ABI-schema errors must not appear.
Also: Agent Skills compatibility rules enforced at P0 (name/description).
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi.parser import validate_agent_skills_frontmatter, validate_name
from sabi.validator import validate_skill

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "telegram-live-status"


def make_copy(tmp_path, remove=()):
    dest = tmp_path / "telegram-live-status"
    shutil.copytree(FIXTURE, dest)
    for rel in remove:
        p = dest / rel
        if p.is_file():
            p.unlink()
    return dest


def test_full_fixture_is_p3(tmp_path):
    level, errors = validate_skill(make_copy(tmp_path))
    assert level == "P3", errors


def test_no_degradation_is_p2(tmp_path):
    level, errors = validate_skill(make_copy(tmp_path, ["degradation.yaml"]))
    assert level == "P2", errors
    assert any("P3:" in e for e in errors)


def test_no_effects_is_p1(tmp_path):
    level, errors = validate_skill(make_copy(tmp_path, ["effects.yaml"]))
    assert level == "P1", errors
    assert any("P2:" in e for e in errors)


def test_no_abi_is_p0(tmp_path):
    level, errors = validate_skill(
        make_copy(tmp_path, ["skill.abi.yaml", "effects.yaml", "degradation.yaml"])
    )
    assert level == "P0", errors


def test_garbage_is_invalid(tmp_path):
    d = tmp_path / "empty"
    d.mkdir()
    (d / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")
    level, errors = validate_skill(d)
    assert level == "INVALID"
    assert errors


def test_no_duplicate_abi_schema_errors(tmp_path):
    _, errors = validate_skill(make_copy(tmp_path))
    assert len(errors) == len(set(errors))


# ── Agent Skills compatibility (shared subset, enforced at P0) ──────


def test_agent_skills_valid_fixture_passes_both():
    """The shared compatibility fixture passes the AS validator AND is a
    valid SABI frontmatter document."""
    fm = {"name": "compat-skill", "description": "Agent Skills compatibility fixture",
          "license": "MIT", "metadata": {"version": "1.0.0"}}
    assert validate_agent_skills_frontmatter(fm) == []


def test_agent_skills_name_too_long():
    assert validate_name("a" * 65)  # 65 chars > 64
    assert not validate_name("a" * 64)


def test_agent_skills_name_uppercase_rejected():
    assert validate_name("Not-Lowercase")


def test_agent_skills_name_leading_trailing_hyphen_rejected():
    assert validate_name("-lead")
    assert validate_name("trail-")


def test_agent_skills_name_double_hyphen_rejected():
    assert validate_name("double--hyphen")


def test_agent_skills_description_too_long():
    fm = {"name": "ok-name", "description": "x" * 1025}
    errs = validate_agent_skills_frontmatter(fm)
    assert any("1024" in e for e in errs)


def test_agent_skills_optional_fields_typed_leniently():
    fm = {"name": "ok", "description": "d", "compatibility": [">=3.11"],
          "metadata": {"anything": True}, "version": "1.0.0", "license": "MIT"}
    assert validate_agent_skills_frontmatter(fm) == []
    bad = {"name": "ok", "description": "d", "metadata": ["not", "a", "map"]}
    assert any("metadata" in e for e in validate_agent_skills_frontmatter(bad))


def test_p0_rejects_agent_skills_violations_via_validator(tmp_path):
    """End-to-end: a name-rule violation surfaces as a P0 finding."""
    d = tmp_path / "Bad-Name"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: Bad-Name\ndescription: upper case name is invalid\n---\nbody\n",
        encoding="utf-8")
    level, errors = validate_skill(d)
    assert level == "INVALID"
    assert any("lowercase alphanumerics" in e for e in errors)
