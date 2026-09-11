"""The two structural invariants this change must guarantee.

1. CLI VALID == canonical validator success.
2. StructurallyValid != EvidenceVerified.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from sabi import schema as json_schema  # noqa: E402
from sabi.lockfile import write_lock  # noqa: E402
from sabi.validator import validate_skill  # noqa: E402

CLI = REPO / "cli" / "sabi.py"
EXAMPLE = REPO / "examples" / "telegram-live-status"
CERT_SCHEMA = json.loads(
    (REPO / "schemas" / "certificate.schema.json").read_text(encoding="utf-8"))


def _run(*argv):
    return subprocess.run([sys.executable, str(CLI), *argv],
                          capture_output=True, text=True, timeout=60)


def _copy(tmp_path, name="telegram-live-status"):
    dest = tmp_path / name
    shutil.copytree(EXAMPLE, dest)
    return dest


def _cli_valid(skill) -> bool:
    return _run("validate", str(skill)).returncode == 0


def _canonical_valid(skill) -> bool:
    level, errors = validate_skill(skill)
    return (not errors) and level != "INVALID"


def test_cli_valid_equals_canonical_validator(tmp_path):
    cases = []

    good = _copy(tmp_path, "good")
    cases.append(good)

    tampered = _copy(tmp_path, "tampered")
    write_lock(tampered)
    (tampered / "SKILL.md").write_text(
        (tampered / "SKILL.md").read_text(encoding="utf-8") + "x\n",
        encoding="utf-8")
    cases.append(tampered)

    bad_name = _copy(tmp_path, "BadName")
    fm, body = (bad_name / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1:]
    fm_doc = yaml.safe_load(fm)
    fm_doc["name"] = "BadName"
    (bad_name / "SKILL.md").write_text(
        "---\n" + yaml.safe_dump(fm_doc, sort_keys=False) + "---" + body,
        encoding="utf-8")
    write_lock(bad_name)
    cases.append(bad_name)

    no_effects = _copy(tmp_path, "no-effects")
    (no_effects / "effects.yaml").unlink()
    write_lock(no_effects)
    cases.append(no_effects)

    for skill in cases:
        assert _cli_valid(skill) == _canonical_valid(skill), skill


def test_structural_valid_is_not_evidence_verified(tmp_path):
    skill = tmp_path / "ghost-skill"
    skill.mkdir()
    fake = "sha256:" + "0" * 64
    cert = {
        "skill": "ghost-skill",
        "skill_digest": fake,
        "abi_digest": fake,
        "lock_digest": fake,
        "sabi": "sabi/v0.1",
        "cases": 0,
        "passed": 0,
        "failed": 0,
        "evidence_class": "STATIC_CONFORMANT",
        "run_receipts": [],
        "signed": False,
    }
    out = skill / "attestations" / "portability.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cert, indent=2) + "\n", encoding="utf-8")

    # structurally valid: parses and satisfies the certificate schema
    assert json_schema.validate(cert, CERT_SCHEMA) == []
    # but it is not evidence-verified
    assert _run("verify-certificate", str(out)).returncode == 1
