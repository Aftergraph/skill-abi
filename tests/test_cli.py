"""Tests for the sabi CLI (no network)."""
import json
import subprocess
import sys
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "cli" / "sabi.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures"


def run(*argv):
    r = subprocess.run([sys.executable, str(CLI), *argv],
                       capture_output=True, text=True, timeout=60)
    return r


def setup_module():
    import yaml
    skill = FIXTURE / "demo-skill"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "SKILL.md").write_bytes(b"---\nname: demo-skill\n---\nbody\n")
    abi = {"spec": "sabi/v0.1", "skill": "demo-skill", "version": "1.0.0",
           "inputs": {"schema": "schemas/in.json"},
           "outputs": {"schema": "schemas/out.json"},
           "capabilities": {"required": ["filesystem.read"], "optional": []},
           "verification": {"required": ["artifact.exists"]}}
    (skill / "skill.abi.yaml").write_bytes(yaml.safe_dump(abi).encode())
    (skill / "effects.yaml").write_bytes(yaml.safe_dump(
        {"effects": {"filesystem.write": {"scope": [], "max_operations": 0}}}).encode())
    (skill / "degradation.yaml").write_bytes(yaml.safe_dump({"degradation": {
        "full": {"requires": ["filesystem.read"]},
        "reject": {"terminal": True}}}).encode())
    (skill / "schemas").mkdir(exist_ok=True)
    (skill / "schemas" / "in.json").write_bytes(b'{"type":"object"}')
    (skill / "schemas" / "out.json").write_bytes(b'{"type":"object"}')
    (skill / "bindings").mkdir(exist_ok=True)
    (skill / "bindings" / "rt.yaml").write_bytes(yaml.safe_dump(
        {"runtime": "rt", "capabilities": ["filesystem.read"]}).encode())
    (skill / "conformance").mkdir(exist_ok=True)
    (skill / "conformance" / "invariants.yaml").write_bytes(yaml.safe_dump(
        [{"id": "terminal-tier-last"}, {"id": "lock-covers-contract"}]).encode())


def test_validate_ok():
    r = run("validate", str(FIXTURE / "demo-skill"))
    assert r.returncode == 0 and "VALID" in r.stdout


def test_resolve_full():
    r = run("resolve", str(FIXTURE / "demo-skill"), "--runtime",
            str(FIXTURE / "demo-skill" / "bindings" / "rt.yaml"))
    assert r.returncode == 0 and "FULL" in r.stdout


def test_diff_self_is_patch():
    s = str(FIXTURE / "demo-skill")
    r = run("diff", s, s)
    assert r.returncode == 0 and "PATCH" in r.stdout


def test_test_matrix_json():
    r = run("test", str(FIXTURE / "demo-skill"), "--matrix", "--json")
    assert r.returncode == 0
    assert json.loads(r.stdout)["results"][0]["tier"] == "full"


def test_lock_then_certify_then_verify_certificate():
    s = str(FIXTURE / "demo-skill")
    assert run("lock", s).returncode == 0
    assert run("certify", s).returncode == 0
    r = run("verify-certificate", s + "/attestations/portability.json")
    assert r.returncode == 0 and "OK" in r.stdout
