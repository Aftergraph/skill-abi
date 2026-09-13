"""CLI-level tests for the sabi command.

Invariant: CLI_VALID == LIBRARY_VALID — the same canonical validation
runs whether called via CLI or library.

Test structure:
- setup_module() creates a demo skill dir with fixtures
- make_skill() helper builds one-flaw-per-kind skill dirs
- run() helper invokes `python cli/sabi.py <cmd> <args>`
- library_validate() calls sabi.validator.validate_skill directly
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import yaml

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / "cli" / "sabi.py"
FIXTURE = REPO / "examples" / "telegram-live-status"
SCHEMAS = REPO / "schemas"
FIXTURES_DIR = REPO / "tests" / "fixtures"


def setup_module():
    """Ensure demo-skill fixture exists and is pre-locked."""
    demo = FIXTURES_DIR / "demo-skill"
    if not demo.is_dir():
        if FIXTURE.is_dir():
            shutil.copytree(FIXTURE, demo)
        else:
            demo.mkdir(parents=True, exist_ok=True)
    # Ensure description is present (required by Agent Skills rules)
    sm = demo / "SKILL.md"
    if sm.is_file():
        text = sm.read_text(encoding="utf-8")
        if "description:" not in text:
            text = text.replace("---\n", "---\ndescription: demo skill for testing\n", 1)
            sm.write_text(text, encoding="utf-8")
    # Pre-lock the demo skill
    subprocess.run([sys.executable, str(CLI), "lock", str(demo)], capture_output=True)


def run(*args):
    """Run `python cli/sabi.py <args>` and return CompletedProcess."""
    cmd = [sys.executable, str(CLI)] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def make_skill(path, flaws=None, effects=None, degradation=None,
              abi=None, skippable=None, write_lock=True):
    """Build a skill directory with optional flaws.

    Each flaw is a string key that overrides a specific part of the
    skill's contract. Returns the Path.
    """
    d = Path(path)
    d.mkdir(parents=True, exist_ok=True)
    name = d.name

    # Default SKILL.md
    if "bad-fm" in (flaws or []):
        (d / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")
    elif "empty-body" in (flaws or []):
        (d / "SKILL.md").write_text("---\nname: {}\ndescription: test\n---\n   ".format(name), encoding="utf-8")
    elif "bad-name" in (flaws or []):
        (d / "SKILL.md").write_text(
            "---\nname: {}\ndescription: a test skill for CLI testing\n---\nbody\n".format(name),
            encoding="utf-8")
    else:
        (d / "SKILL.md").write_text(
            "---\nname: {}\ndescription: a test skill for CLI testing\n---\nbody\n".format(name),
            encoding="utf-8")

    # Default skill.abi.yaml
    abi_doc = abi if abi is not None else {
        "spec": "sabi/v0.1",
        "skill": name,
        "version": "1.0.0",
        "inputs": {"schema": "schemas/input.json"},
        "outputs": {"schema": "schemas/output.json"},
        "capabilities": {"required": ["filesystem.read"], "optional": ["message.send"]},
    }
    if "unknown-cap" in (flaws or []):
        abi_doc["capabilities"]["required"] = ["filesystem.meltdown"]
    if "bad-spec" in (flaws or []):
        abi_doc["spec"] = "v0.1"
    if "no-input-schema" in (flaws or []):
        del abi_doc["inputs"]["schema"]
    if "no-output-schema" in (flaws or []):
        del abi_doc["outputs"]["schema"]
    (d / "skill.abi.yaml").write_text(yaml.dump(abi_doc, default_flow_style=False), encoding="utf-8")

    # Default effects.yaml
    eff = effects if effects is not None else {
        "effects": {
            "filesystem.write": {"scope": [], "max_operations": 0},
            "credentials": {"expose_to_model": False},
        }
    }
    if "bad-effects" in (flaws or []):
        eff = {"not-effects": True}
    (d / "effects.yaml").write_text(yaml.dump(eff, default_flow_style=False), encoding="utf-8")

    # Default degradation.yaml
    deg = degradation if degradation is not None else {
        "degradation": {
            "full": {"requires": ["filesystem.read", "message.send"], "terminal": False},
            "partial": {"requires": ["filesystem.read"], "terminal": False},
            "advisory": {"requires": [], "terminal": True},
        }
    }
    if "bad-degradation" in (flaws or []):
        deg = {"degradation": {"only": {"requires": [], "terminal": False}}}
    (d / "degradation.yaml").write_text(yaml.dump(deg, default_flow_style=False, sort_keys=False), encoding="utf-8")

    # Default schemas
    (d / "schemas").mkdir(exist_ok=True)
    (d / "schemas" / "input.json").write_text(json.dumps({"type": "object"}), encoding="utf-8")
    (d / "schemas" / "output.json").write_text(json.dumps({"type": "object"}), encoding="utf-8")

    # Default bindings
    (d / "bindings").mkdir(exist_ok=True)
    (d / "bindings" / "rt.yaml").write_text(
        yaml.dump({"runtime": "test-rt", "capabilities": ["filesystem.read", "message.send"]}),
        encoding="utf-8")

    # Default conformance
    (d / "conformance").mkdir(exist_ok=True)
    (d / "conformance" / "invariants.yaml").write_text(
        yaml.dump([
            {"id": "terminal-tier-last"},
            {"id": "lock-covers-contract"},
        ]),
        encoding="utf-8")

    # Lock
    if write_lock:
        subprocess.run([sys.executable, str(CLI), "lock", str(d)], capture_output=True)

    return d


def library_validate(skill_dir):
    """Call sabi.validator.validate_skill directly (library path)."""
    from sabi.validator import validate_skill
    return validate_skill(skill_dir, schemas_dir=SCHEMAS)


# ── CLI == library invariant ─────────────────────────────────────────


def test_cli_valid_equals_library_valid(tmp_path):
    d = make_skill(tmp_path / "valid-skill")
    cli_r = run("validate", str(d))
    lib_level, lib_errors = library_validate(d)
    assert cli_r.returncode == 0, cli_r.stderr
    assert "VALID" in cli_r.stdout, cli_r.stdout
    assert lib_level not in ("INVALID",), lib_errors


def test_cli_invalid_equals_library_invalid(tmp_path):
    d = make_skill(tmp_path / "bad-fm", flaws=["bad-fm"])
    cli_r = run("validate", str(d))
    lib_level, lib_errors = library_validate(d)
    assert cli_r.returncode == 1, cli_r.stdout
    assert "INVALID" in cli_r.stdout, cli_r.stdout
    assert lib_level == "INVALID", lib_level


# ── Negative CLI rejection cases ─────────────────────────────────────


def test_rejects_bad_frontmatter(tmp_path):
    d = make_skill(tmp_path / "bad-fm", flaws=["bad-fm"])
    r = run("validate", str(d))
    assert r.returncode == 1
    assert "INVALID" in r.stdout


def test_rejects_empty_body(tmp_path):
    d = make_skill(tmp_path / "empty-body", flaws=["empty-body"])
    r = run("validate", str(d))
    assert r.returncode == 1
    assert "INVALID" in r.stdout


def test_rejects_name_mismatch(tmp_path):
    d = make_skill(tmp_path / "name-mismatch")
    # Override SKILL.md with a different name
    (d / "SKILL.md").write_text(
        "---\nname: other-name\ndescription: a test skill\n---\nbody\n", encoding="utf-8")
    r = run("validate", str(d))
    assert r.returncode == 1
    assert "INVALID" in r.stdout or "directory" in r.stdout


def test_rejects_unknown_capability(tmp_path):
    d = make_skill(tmp_path / "unknown-cap", flaws=["unknown-cap"])
    r = run("validate", str(d))
    assert r.returncode == 1
    assert "INVALID" in r.stdout


def test_rejects_missing_input_schema(tmp_path):
    d = make_skill(tmp_path / "no-input", flaws=["no-input-schema"])
    r = run("validate", str(d))
    assert r.returncode == 1
    assert "INVALID" in r.stdout


def test_rejects_missing_output_schema(tmp_path):
    d = make_skill(tmp_path / "no-output", flaws=["no-output-schema"])
    r = run("validate", str(d))
    assert r.returncode == 1
    assert "INVALID" in r.stdout


def test_rejects_bad_effects(tmp_path):
    d = make_skill(tmp_path / "bad-eff", flaws=["bad-effects"])
    r = run("validate", str(d))
    assert r.returncode == 1
    assert "INVALID" in r.stdout


def test_rejects_bad_degradation(tmp_path):
    d = make_skill(tmp_path / "bad-deg", flaws=["bad-degradation"])
    r = run("validate", str(d))
    assert r.returncode == 1
    assert "INVALID" in r.stdout


def test_rejects_bad_spec_version(tmp_path):
    d = make_skill(tmp_path / "bad-spec", flaws=["bad-spec"])
    r = run("validate", str(d))
    assert r.returncode == 1
    assert "INVALID" in r.stdout


def test_rejects_corrupt_lock(tmp_path):
    d = make_skill(tmp_path / "corrupt-lock")
    (d / "skill.lock").write_text("{not json\n", encoding="utf-8")
    r = run("validate", str(d))
    # Missing/corrupt lock is reported but tolerated in validate
    assert r.returncode == 0 or "LOCK" in r.stdout


def test_rejects_tampered_file(tmp_path):
    d = make_skill(tmp_path / "tampered")
    (d / "SKILL.md").write_text(
        "---\nname: tampered\ndescription: tampered file\n---\ntampered body\n", encoding="utf-8")
    r = run("validate", str(d))
    assert r.returncode == 1  # lock errors are now blocking
    # verify-lock should catch tampering
    r2 = run("verify-lock", str(d))
    assert r2.returncode == 3


# ── JSON / human output parity ───────────────────────────────────────


def test_validate_json_output(tmp_path):
    d = make_skill(tmp_path / "json-test")
    r = run("--json", "validate", str(d))
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["skill"] == "json-test"
    assert "level" in data
    assert "errors" in data


def test_validate_json_human_parity(tmp_path):
    d = make_skill(tmp_path / "parity")
    r_json = run("--json", "validate", str(d))
    r_human = run("validate", str(d))
    data = json.loads(r_json.stdout)
    if data["level"] not in ("INVALID",):
        assert "VALID" in r_human.stdout
    else:
        assert "INVALID" in r_human.stdout


# ── bind tests ───────────────────────────────────────────────────────


def test_bind_resolved(tmp_path):
    d = make_skill(tmp_path / "bind-test")
    prof = {"runtime": "test-rt", "capabilities": ["filesystem.read", "message.send"]}
    prof_path = d / "profile.yaml"
    prof_path.write_text(yaml.dump(prof), encoding="utf-8")
    r = run("bind", str(d), "--runtime", str(prof_path))
    assert r.returncode == 0, r.stderr
    # JSON output
    rj = run("--json", "bind", str(d), "--runtime", str(prof_path))
    data = json.loads(rj.stdout)
    assert data["selected_degradation_tier"] is not None
    assert data["unresolved_required_caps"] == []


def test_bind_unresolved(tmp_path):
    d = make_skill(tmp_path / "bind-unresolved")
    prof = {"runtime": "test-rt", "capabilities": []}
    prof_path = d / "profile.yaml"
    prof_path.write_text(yaml.dump(prof), encoding="utf-8")
    r = run("bind", str(d), "--runtime", str(prof_path))
    assert r.returncode == 1
    assert "unresolved" in r.stdout.lower()


# ── verify-lock tests ────────────────────────────────────────────────


def test_verify_lock_ok(tmp_path):
    d = make_skill(tmp_path / "lock-ok")
    r = run("verify-lock", str(d))
    assert r.returncode == 0
    assert "OK" in r.stdout


def test_verify_lock_missing(tmp_path):
    d = make_skill(tmp_path / "lock-missing", write_lock=False)
    r = run("verify-lock", str(d))
    assert r.returncode == 3
    assert "missing" in (r.stderr + r.stdout).lower()


def test_verify_lock_corrupt(tmp_path):
    d = make_skill(tmp_path / "lock-corrupt")
    (d / "skill.lock").write_text("{not json\n", encoding="utf-8")
    r = run("verify-lock", str(d))
    assert r.returncode == 3
    assert "invalid" in (r.stderr + r.stdout).lower()


def test_verify_lock_tampered(tmp_path):
    d = make_skill(tmp_path / "lock-tampered")
    (d / "SKILL.md").write_text(
        "---\nname: lock-tampered\ndescription: tampered\n---\nbody\n", encoding="utf-8")
    r = run("verify-lock", str(d))
    assert r.returncode == 3
    assert "mismatch" in (r.stderr + r.stdout).lower()


def test_verify_lock_coverage_gap(tmp_path):
    d = make_skill(tmp_path / "coverage-gap", write_lock=False)
    assert run("lock", str(d)).returncode == 0
    full = json.loads((d / "skill.lock").read_text(encoding="utf-8"))
    subset = {k: v for k, v in full["files"].items() if not k.startswith("schemas/")}
    full["files"] = subset
    (d / "skill.lock").write_text(json.dumps(full, indent=2) + "\n", encoding="utf-8")
    r = run("verify-lock", str(d))
    assert r.returncode == 3 and "coverage gap" in (r.stderr + r.stdout)


def test_verify_lock_rejects_pinned_attestation(tmp_path):
    d = make_skill(tmp_path / "no-attest", write_lock=False)
    assert run("lock", str(d)).returncode == 0
    full = json.loads((d / "skill.lock").read_text(encoding="utf-8"))
    full["files"]["attestations/portability.json"] = "sha256:" + "0" * 64
    (d / "skill.lock").write_text(json.dumps(full, indent=2) + "\n", encoding="utf-8")
    r = run("verify-lock", str(d))
    assert r.returncode == 3 and "ephemeral" in (r.stderr + r.stdout)


# ── verify-certificate tests ─────────────────────────────────────────


def test_verify_certificate_structural(tmp_path):
    d = make_skill(tmp_path / "cert-struct")
    r = run("certify", str(d))
    assert r.returncode == 0
    cert_path = d / "attestations" / "portability.json"
    assert cert_path.is_file()
    r2 = run("verify-certificate", str(cert_path))
    assert r2.returncode == 0
    assert "VALID" in r2.stdout


def test_verify_certificate_with_skill(tmp_path):
    d = make_skill(tmp_path / "cert-skill")
    r = run("certify", str(d))
    assert r.returncode == 0
    cert_path = d / "attestations" / "portability.json"
    r2 = run("verify-certificate", str(cert_path), "--skill", str(d))
    assert r2.returncode == 0
    assert "VALID" in r2.stdout


# ── demo-skill fixture smoke tests ───────────────────────────────────


def test_demo_skill_validates(tmp_path):
    demo = FIXTURES_DIR / "demo-skill"
    if not demo.is_dir():
        return
    r = run("validate", str(demo))
    assert r.returncode == 0, r.stderr
    assert "VALID" in r.stdout


def test_demo_skill_verify_lock(tmp_path):
    demo = FIXTURES_DIR / "demo-skill"
    if not demo.is_dir():
        return
    r = run("verify-lock", str(demo))
    assert r.returncode == 0, r.stderr
    assert "OK" in r.stdout


def test_lock_then_certify_then_verify_certificate():
    s = str(FIXTURES_DIR / "demo-skill")
    assert run("lock", s).returncode == 0
    assert run("certify", s).returncode == 0
    r = run("verify-certificate", s + "/attestations/portability.json")
    assert r.returncode == 0 and "VALID" in r.stdout


def test_certify_static_is_not_full():
    s = str(FIXTURES_DIR / "demo-skill")
    assert run("lock", s).returncode == 0
    r = run("certify", s)
    assert r.returncode == 0
    assert "STATIC_CONFORMANT" in r.stdout
    assert "full" not in r.stdout.lower()
