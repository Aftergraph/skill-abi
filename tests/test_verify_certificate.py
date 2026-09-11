"""verify-certificate: structural JSON validity alone must NOT pass.

The verifier checks the certificate schema, skill/ABI/lock digests against
actual bytes, run-receipt references, runtime/test-suite identifiers,
evidence existence, and signature/bundle when signed.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "cli" / "sabi.py"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "telegram-live-status"


def run(*argv):
    return subprocess.run([sys.executable, str(CLI), *argv],
                          capture_output=True, text=True, timeout=60)


def _digest(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def _prepared_skill(tmp_path) -> Path:
    skill = tmp_path / "telegram-live-status"
    shutil.copytree(EXAMPLE, skill)
    assert run("lock", str(skill)).returncode == 0
    assert run("certify", str(skill)).returncode == 0
    return skill


def _base_cert(skill: Path, **over):
    def d(name):
        p = skill / name
        return _digest(p) if p.is_file() else "sha256:" + "0" * 64
    cert = {
        "skill": skill.name,
        "skill_digest": d("SKILL.md"),
        "abi_digest": d("skill.abi.yaml"),
        "lock_digest": d("skill.lock"),
        "sabi": "sabi/v0.1",
        "tested_runtimes": [],
        "tested_tiers": [],
        "cases": 2,
        "passed": 2,
        "failed": 0,
        "effect_violations": 0,
        "evidence_class": "STATIC_CONFORMANT",
        "run_receipts": [],
        "signed": False,
        "note": "static evidence only",
    }
    cert.update(over)
    return cert


def _write_cert(skill: Path, cert) -> Path:
    out = skill / "attestations" / "crafted.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(cert, indent=2) + "\n", encoding="utf-8")
    return out


def _verify(cert_path: Path, *extra):
    return run("verify-certificate", str(cert_path), *extra)


def test_valid_static_certificate_verifies(tmp_path):
    skill = _prepared_skill(tmp_path)
    cert_path = skill / "attestations" / "portability.json"
    r = _verify(cert_path)
    assert r.returncode == 0 and "VALID" in r.stdout, r.stdout


def test_structural_json_only_rejected(tmp_path):
    # schema-valid JSON with no real skill behind it must not pass
    skill = tmp_path / "ghost-skill"
    skill.mkdir()
    fake = "sha256:" + "0" * 64
    cert = _base_cert(
        skill, skill_digest=fake, abi_digest=fake, lock_digest=fake)
    cert_path = _write_cert(skill, cert)
    r = _verify(cert_path)
    assert r.returncode == 1
    assert "skill directory not found" in r.stdout


def test_skill_digest_mismatch_rejected(tmp_path):
    skill = _prepared_skill(tmp_path)
    cert_path = skill / "attestations" / "portability.json"
    (skill / "SKILL.md").write_text(
        (skill / "SKILL.md").read_text(encoding="utf-8") + "\ntamper\n",
        encoding="utf-8")
    r = _verify(cert_path)
    assert r.returncode == 1
    assert "skill_digest does not match SKILL.md bytes" in r.stdout


def test_abi_digest_mismatch_rejected(tmp_path):
    skill = _prepared_skill(tmp_path)
    cert_path = skill / "attestations" / "portability.json"
    (skill / "skill.abi.yaml").write_text(
        (skill / "skill.abi.yaml").read_text(encoding="utf-8") + "\n# x\n",
        encoding="utf-8")
    r = _verify(cert_path)
    assert r.returncode == 1
    assert "abi_digest does not match skill.abi.yaml bytes" in r.stdout


def test_lock_digest_mismatch_rejected(tmp_path):
    skill = _prepared_skill(tmp_path)
    cert_path = skill / "attestations" / "portability.json"
    (skill / "skill.lock").write_text(
        (skill / "skill.lock").read_text(encoding="utf-8") + "\n",
        encoding="utf-8")
    r = _verify(cert_path)
    assert r.returncode == 1
    assert "lock_digest does not match skill.lock bytes" in r.stdout


def test_runtime_class_without_receipts_rejected(tmp_path):
    skill = _prepared_skill(tmp_path)
    cert_path = _write_cert(skill, _base_cert(
        skill, evidence_class="RUNTIME_TESTED"))
    r = _verify(cert_path)
    assert r.returncode == 1
    assert "RUNTIME_TESTED requires >=1 run receipt" in r.stdout


def test_attested_unsigned_rejected(tmp_path):
    skill = _prepared_skill(tmp_path)
    cert_path = _write_cert(skill, _base_cert(skill, evidence_class="ATTESTED"))
    r = _verify(cert_path)
    assert r.returncode == 1
    assert "ATTESTED requires signed=true" in r.stdout


def test_signed_without_signature_block_rejected(tmp_path):
    skill = _prepared_skill(tmp_path)
    receipts = [{"runtime": "rt1", "harness": "h", "evidence": "e.json"},
                {"runtime": "rt2", "harness": "h", "evidence": "e.json"}]
    cert_path = _write_cert(skill, _base_cert(
        skill, evidence_class="ATTESTED", signed=True, run_receipts=receipts))
    r = _verify(cert_path)
    assert r.returncode == 1
    assert "signed=true requires a signature block" in r.stdout


def test_missing_evidence_file_rejected(tmp_path):
    skill = _prepared_skill(tmp_path)
    receipts = [{"runtime": "rt1", "harness": "h",
                 "evidence": "attestations/nope.json"}]
    cert_path = _write_cert(skill, _base_cert(
        skill, evidence_class="RUNTIME_TESTED", run_receipts=receipts))
    r = _verify(cert_path)
    assert r.returncode == 1
    assert "evidence not found" in r.stdout


def test_missing_runtime_identifier_rejected(tmp_path):
    skill = _prepared_skill(tmp_path)
    ev = skill / "attestations" / "run.json"
    ev.write_text("{}\n", encoding="utf-8")
    receipts = [{"harness": "h", "evidence": "attestations/run.json"}]
    cert_path = _write_cert(skill, _base_cert(
        skill, evidence_class="RUNTIME_TESTED", run_receipts=receipts))
    r = _verify(cert_path)
    assert r.returncode == 1
    assert "missing runtime identifier" in r.stdout


def test_bad_evidence_class_rejected(tmp_path):
    skill = _prepared_skill(tmp_path)
    cert_path = _write_cert(skill, _base_cert(skill, evidence_class="full"))
    r = _verify(cert_path)
    assert r.returncode == 1
    assert "evidence_class" in r.stdout


def test_historical_example_certificate_rejected(tmp_path):
    # the preserved example certificate predates evidence classes
    cert_path = EXAMPLE / "attestations" / "portability.json"
    r = _verify(cert_path)
    assert r.returncode == 1
