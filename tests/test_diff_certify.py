"""Tests for sabi.diff + sabi.certify (no network)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml

from sabi.diff import semantic_diff
from sabi.certify import evaluate_invariants, build_certificate


def make_skill(root: Path, version="1.0.0", caps=("a",), effects=None, tiers=None):
    root.mkdir(parents=True, exist_ok=True)
    (root / "SKILL.md").write_bytes(b"---\nname: t\n---\nbody\n")
    abi = {"spec": "sabi/v0.1", "skill": "t", "version": version,
           "inputs": {"schema": "schemas/in.json"},
           "outputs": {"schema": "schemas/out.json"},
           "capabilities": {"required": list(caps), "optional": []},
           "verification": {"required": ["artifact.exists"]}}
    (root / "skill.abi.yaml").write_bytes(yaml.safe_dump(abi).encode())
    eff = effects if effects is not None else {"message.send": {"destinations": ["x"], "max_operations": 1}}
    (root / "effects.yaml").write_bytes(yaml.safe_dump({"effects": eff}).encode())
    deg = tiers if tiers is not None else {"full": {"requires": list(caps)}, "reject": {"terminal": True}}
    (root / "degradation.yaml").write_bytes(yaml.safe_dump({"degradation": deg}).encode())
    (root / "schemas").mkdir(exist_ok=True)
    (root / "schemas" / "in.json").write_bytes(b'{"type":"object"}')
    (root / "schemas" / "out.json").write_bytes(b'{"type":"object"}')
    (root / "conformance").mkdir(exist_ok=True)
    (root / "conformance" / "invariants.yaml").write_bytes(yaml.safe_dump([
        {"id": "terminal-tier-last"},
        {"id": "lock-covers-contract"},
    ]).encode())
    lock = {"lock_version": 1, "skill": "t", "files": {
        "skill.abi.yaml": "sha256:x", "effects.yaml": "sha256:x",
        "degradation.yaml": "sha256:x",
        "schemas/in.json": "sha256:x", "schemas/out.json": "sha256:x"}}
    (root / "skill.lock").write_bytes((json.dumps(lock) + "\n").encode())
    return root


def test_diff_identical_is_patch(tmp_path):
    make_skill(tmp_path / "v1")
    make_skill(tmp_path / "v2")
    bump, breaking, minor, notes = semantic_diff(tmp_path / "v1", tmp_path / "v2")
    assert bump == "PATCH" and not breaking


def test_diff_added_required_cap_is_major(tmp_path):
    make_skill(tmp_path / "v1", caps=("a",))
    make_skill(tmp_path / "v2", caps=("a", "b"))
    bump, breaking, minor, notes = semantic_diff(tmp_path / "v1", tmp_path / "v2")
    assert bump == "MAJOR"
    assert any("required capability" in b for b in breaking)


def test_diff_widened_effect_is_major(tmp_path):
    make_skill(tmp_path / "v1")
    make_skill(tmp_path / "v2", effects={"message.send": {"destinations": ["x", "y"], "max_operations": 5}})
    bump, breaking, minor, notes = semantic_diff(tmp_path / "v1", tmp_path / "v2")
    assert bump == "MAJOR"


def test_evaluate_terminal_and_lock(tmp_path):
    skill = make_skill(tmp_path / "s")
    res = evaluate_invariants(skill, ["a"])
    by_id = dict(res)
    assert by_id["terminal-tier-last"] is True
    assert by_id["lock-covers-contract"] is True


def test_certificate_counts(tmp_path):
    skill = make_skill(tmp_path / "s")
    res = evaluate_invariants(skill, ["a"])
    cert = build_certificate(skill, [("rt", "full", res)])
    assert cert["cases"] == 2 and cert["passed"] == 2
    assert cert["signed"] is False
    assert cert["certificate"] == "full"
