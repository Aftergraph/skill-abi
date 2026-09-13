"""Self-contained tests for the cross-repo requirement-object export API."""
import json
from pathlib import Path

from sabi.api import (
    export_requirement_object,
    requirement_object_bytes,
    REQUIREMENT_OBJECT_SCHEMA,
)


class TestRequirementObjectShape:
    def test_schema_id_present(self, tmp_path):
        skill = _make_skill(tmp_path)
        obj = export_requirement_object(skill)
        assert obj["schema"] == REQUIREMENT_OBJECT_SCHEMA

    def test_all_ten_fields_present(self, tmp_path):
        skill = _make_skill(tmp_path)
        obj = export_requirement_object(skill)
        assert set(obj.keys()) == {
            "schema", "skill", "version", "spec",
            "digests", "required_capabilities", "optional_capabilities",
            "effect_envelope", "degradation_tiers", "verification_obligations",
        }

    def test_degradation_tiers_ordered(self, tmp_path):
        skill = _make_skill(tmp_path, degradation_tiers=["full", "reject"])
        obj = export_requirement_object(skill)
        assert obj["degradation_tiers"] == ["full", "reject"]

    def test_digests_are_sha256_uris(self, tmp_path):
        skill = _make_skill(tmp_path)
        obj = export_requirement_object(skill)
        for key in ("skill_md", "abi"):
            val = obj["digests"][key]
            assert val.startswith("sha256:"), f"{key} digest should be sha256 URI"
            assert len(val) == 7 + 64, f"{key} digest wrong length"

    def test_effect_envelope_present(self, tmp_path):
        skill = _make_skill(tmp_path)
        obj = export_requirement_object(skill)
        assert isinstance(obj["effect_envelope"], dict)

    def test_requirement_object_bytes_deterministic(self, tmp_path):
        skill = _make_skill(tmp_path)
        b1 = requirement_object_bytes(skill)
        b2 = requirement_object_bytes(skill)
        assert b1 == b2

    def test_requirement_object_bytes_is_compact_json(self, tmp_path):
        skill = _make_skill(tmp_path)
        raw = requirement_object_bytes(skill)
        parsed = json.loads(raw)
        assert json.dumps(parsed, separators=(",", ":")) == raw.decode("utf-8")


def _make_skill(tmp_path, degradation_tiers=None):
    """Create a minimal skill directory with all required files."""
    skill = Path(tmp_path) / "test-skill"
    skill.mkdir()

    # SKILL.md
    (skill / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: test\nmetadata:\n  version: 1.0.0\n---\n# Test\n",
        encoding="utf-8",
    )

    # skill.abi.yaml
    import yaml
    abi = {
        "spec": "sabi/v0.1",
        "version": "1.0.0",
        "capabilities": {"required": ["skill.read"], "optional": []},
        "verification": {"required": ["verify.noop"]},
    }
    with open(skill / "skill.abi.yaml", "w") as f:
        yaml.dump(abi, f)

    # effects.yaml
    effects = {"effects": {"filesystem": {"write": {"allowed": False}}}}
    with open(skill / "effects.yaml", "w") as f:
        yaml.dump(effects, f)

    # degradation.yaml
    deg = {"degradation": {}}
    if degradation_tiers:
        deg["degradation"] = {t: {"mode": "skip"} for t in degradation_tiers}
    else:
        deg["degradation"] = {"full": {"mode": "proceed"}}
    with open(skill / "degradation.yaml", "w") as f:
        yaml.dump(deg, f)

    return skill
