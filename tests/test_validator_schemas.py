"""H-003: schema validation tests for skill-md and abi schemas.

Each schema rejects bad docs, accepts the telegram-live-status example,
and missing schema files degrade gracefully (no crash).
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi import schema as json_schema
from sabi.validator import validate_skill, _load_schema

REPO = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = REPO / "schemas"
FIXTURE = REPO / "examples" / "telegram-live-status"


def _load_fixture_frontmatter():
    text = (FIXTURE / "SKILL.md").read_text(encoding="utf-8")
    # Extract between first --- and second ---
    start = text.index("---", 0) + 3
    end = text.index("---", start)
    fm_text = text[start:end].strip()
    import yaml
    return yaml.safe_load(fm_text)


def _load_fixture_abi():
    import yaml
    return yaml.safe_load((FIXTURE / "skill.abi.yaml").read_text(encoding="utf-8"))


# ── skill-md.schema.json ────────────────────────────────────────────


def test_skill_md_schema_accepts_fixture():
    schema = _load_schema(SCHEMAS_DIR / "skill-md.schema.json")
    assert schema is not None, "skill-md.schema.json must exist"
    fm = _load_fixture_frontmatter()
    errors = json_schema.validate(fm, schema)
    assert errors == [], f"fixture frontmatter rejected: {errors}"


def test_skill_md_schema_rejects_missing_name():
    schema = _load_schema(SCHEMAS_DIR / "skill-md.schema.json")
    errors = json_schema.validate({"description": "x"}, schema)
    assert any("name" in e for e in errors)


def test_skill_md_schema_rejects_missing_description():
    schema = _load_schema(SCHEMAS_DIR / "skill-md.schema.json")
    errors = json_schema.validate({"name": "x"}, schema)
    assert any("description" in e for e in errors)


def test_skill_md_schema_rejects_wrong_type():
    schema = _load_schema(SCHEMAS_DIR / "skill-md.schema.json")
    errors = json_schema.validate({"name": 123, "description": "x"}, schema)
    assert errors, "integer name should be rejected"


# ── abi.schema.json ─────────────────────────────────────────────────


def test_abi_schema_accepts_fixture():
    schema = _load_schema(SCHEMAS_DIR / "abi.schema.json")
    assert schema is not None, "abi.schema.json must exist"
    abi = _load_fixture_abi()
    errors = json_schema.validate(abi, schema)
    assert errors == [], f"fixture ABI rejected: {errors}"


def test_abi_schema_rejects_missing_spec():
    schema = _load_schema(SCHEMAS_DIR / "abi.schema.json")
    abi = {"skill": "x", "capabilities": {"required": [], "optional": []}}
    errors = json_schema.validate(abi, schema)
    assert any("spec" in e for e in errors)


def test_abi_schema_rejects_missing_capabilities():
    schema = _load_schema(SCHEMAS_DIR / "abi.schema.json")
    abi = {"spec": "sabi/v0.1", "skill": "x"}
    errors = json_schema.validate(abi, schema)
    assert any("capabilities" in e for e in errors)


def test_abi_schema_rejects_bad_spec_pattern():
    schema = _load_schema(SCHEMAS_DIR / "abi.schema.json")
    abi = {
        "spec": "wrong-format",
        "skill": "x",
        "capabilities": {"required": [], "optional": []},
    }
    errors = json_schema.validate(abi, schema)
    assert any("pattern" in e or "spec" in e for e in errors)


# ── graceful degradation ────────────────────────────────────────────


def test_missing_skill_md_schema_degrades_gracefully(tmp_path):
    empty_schemas = tmp_path / "empty_schemas"
    empty_schemas.mkdir()
    dest = tmp_path / "telegram-live-status"
    shutil.copytree(FIXTURE, dest)
    level, errors = validate_skill(dest, schemas_dir=empty_schemas)
    # Should still reach P3 without crashing; no schema errors
    schema_errors = [e for e in errors if "frontmatter schema" in e]
    assert schema_errors == [], f"unexpected schema errors: {schema_errors}"
    assert level == "P3", f"expected P3, got {level}: {errors}"


def test_missing_abi_schema_degrades_gracefully(tmp_path):
    empty_schemas = tmp_path / "empty_schemas"
    empty_schemas.mkdir()
    dest = tmp_path / "telegram-live-status"
    shutil.copytree(FIXTURE, dest)
    level, errors = validate_skill(dest, schemas_dir=empty_schemas)
    schema_errors = [e for e in errors if "abi schema" in e]
    assert schema_errors == [], f"unexpected schema errors: {schema_errors}"
    assert level == "P3", f"expected P3, got {level}: {errors}"
