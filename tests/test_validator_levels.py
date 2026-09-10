"""Validator level-ladder regression tests (hostile H-001/H-002).

Full fixture -> P3. Removing degradation -> P2 (was mislabeled P1).
Removing effects -> P1 (was unreachable). Removing ABI -> P0.
Garbage dir -> INVALID. Duplicate ABI-schema errors must not appear.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
