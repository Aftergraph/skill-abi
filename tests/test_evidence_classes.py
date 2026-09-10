"""Evidence-class tests for sabi.certify.

Static success must yield STATIC_CONFORMANT, never wording equivalent to
full runtime certification. Runtime classes require run receipts; ATTESTED
requires multi-runtime evidence plus a signature.
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi.certify import (  # noqa: E402
    EVIDENCE_CLASSES,
    build_certificate,
    classify_evidence,
)


def make_skill(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_bytes(b"---\nname: t\ndescription: t\n---\nbody\n")
    abi = {"spec": "sabi/v0.1", "skill": "t", "version": "1.0.0",
           "inputs": {"schema": "schemas/in.json"},
           "outputs": {"schema": "schemas/out.json"},
           "capabilities": {"required": ["filesystem.read"], "optional": []}}
    (root / "skill.abi.yaml").write_bytes(yaml.safe_dump(abi).encode())
    (root / "effects.yaml").write_bytes(yaml.safe_dump(
        {"effects": {"credentials": {"expose_to_model": False}}}).encode())
    (root / "degradation.yaml").write_bytes(yaml.safe_dump({"degradation": {
        "full": {"requires": ["filesystem.read"]}, "reject": {"terminal": True}}}).encode())
    (root / "schemas").mkdir(exist_ok=True)
    (root / "schemas" / "in.json").write_bytes(b'{"type":"object"}')
    (root / "schemas" / "out.json").write_bytes(b'{"type":"object"}')
    (root / "skill.lock").write_bytes(b'{"lock_version":1,"skill":"t","files":{}}\n')
    return root


def test_evidence_classes_enum():
    assert EVIDENCE_CLASSES == (
        "SPEC_VALID", "STATIC_CONFORMANT", "RUNTIME_TESTED",
        "MULTI_RUNTIME_TESTED", "ATTESTED")


def test_static_success_is_static_conformant(tmp_path):
    skill = make_skill(tmp_path / "s")
    cert = build_certificate(skill, [("rt", "full", [("a", True)])])
    assert cert["evidence_class"] == "STATIC_CONFORMANT"
    # never wording equivalent to full runtime certification
    assert cert["evidence_class"] not in (
        "RUNTIME_TESTED", "MULTI_RUNTIME_TESTED", "ATTESTED")
    assert "full" not in cert["evidence_class"].lower()
    assert "static" in cert["note"]
    assert "not" in cert["note"]  # explicit non-claim disclaimer


def test_static_failure_is_spec_valid(tmp_path):
    skill = make_skill(tmp_path / "s")
    cert = build_certificate(skill, [("rt", "full", [("a", False)])])
    assert cert["evidence_class"] == "SPEC_VALID"


def test_one_receipt_is_runtime_tested(tmp_path):
    skill = make_skill(tmp_path / "s")
    cert = build_certificate(
        skill, [("rt", "full", [("a", True)])],
        run_receipts=[{"runtime": "rt", "harness": "h", "evidence": "e.json"}])
    assert cert["evidence_class"] == "RUNTIME_TESTED"


def test_two_receipts_is_multi_runtime(tmp_path):
    skill = make_skill(tmp_path / "s")
    cert = build_certificate(
        skill, [("rt", "full", [("a", True)])],
        run_receipts=[{"runtime": "rt1", "harness": "h", "evidence": "e.json"},
                      {"runtime": "rt2", "harness": "h", "evidence": "e.json"}])
    assert cert["evidence_class"] == "MULTI_RUNTIME_TESTED"


def test_two_receipts_signed_is_attested(tmp_path):
    skill = make_skill(tmp_path / "s")
    cert = build_certificate(
        skill, [("rt", "full", [("a", True)])],
        run_receipts=[{"runtime": "rt1", "harness": "h", "evidence": "e.json"},
                      {"runtime": "rt2", "harness": "h", "evidence": "e.json"}],
        signed=True)
    assert cert["evidence_class"] == "ATTESTED"


def test_signed_single_receipt_not_attested():
    assert classify_evidence(
        [{"runtime": "rt"}], signed=True, static_ok=True) == "RUNTIME_TESTED"


def test_signed_static_not_attested():
    assert classify_evidence([], signed=True, static_ok=True) == "STATIC_CONFORMANT"


def test_certificate_never_emits_full(tmp_path):
    skill = make_skill(tmp_path / "s")
    cert = build_certificate(skill, [("rt", "full", [("a", True)])])
    assert "certificate" not in cert
    assert "full" not in cert["note"].lower()
