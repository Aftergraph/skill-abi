"""Schema-file tests (hostile H-003 closure).

The validator references skill-md.schema.json + abi.schema.json; these
files now exist, so the branches are live. Tests pin accept/reject
behavior directly against sabi.schema.validate.
"""
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi import schema as js

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "telegram-live-status"


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def test_schema_files_exist():
    assert (SCHEMAS / "skill-md.schema.json").is_file()
    assert (SCHEMAS / "abi.schema.json").is_file()


def test_frontmatter_accepts_example():
    fm, _ = open(EXAMPLE / "SKILL.md", encoding="utf-8").read().split("---")[1:3]
    assert js.validate(yaml.safe_load(fm), load("skill-md.schema.json")) == []


def test_frontmatter_rejects_missing_name():
    assert js.validate({"description": "x"}, load("skill-md.schema.json")) != []


def test_frontmatter_rejects_missing_description():
    assert js.validate({"name": "x"}, load("skill-md.schema.json")) != []


def test_abi_accepts_example():
    abi = yaml.safe_load((EXAMPLE / "skill.abi.yaml").read_text(encoding="utf-8"))
    assert js.validate(abi, load("abi.schema.json")) == []


def test_abi_rejects_bad_spec():
    doc = {"spec": "other/1", "skill": "x", "capabilities": {"required": []}}
    assert js.validate(doc, load("abi.schema.json")) != []


def test_abi_rejects_missing_capabilities():
    assert js.validate({"spec": "sabi/v0.1", "skill": "x"}, load("abi.schema.json")) != []


# ── canonical schema family (Team D consolidation) ──────────────────
#
# One normative family, one $id namespace (aftergraph.org/sabi).
# schemas/skill-abi.schema.json was the obsolete unreferenced duplicate
# and is retired; abi.schema.json is canonical. See spec/schema-family.md.

CANONICAL_NS = "https://aftergraph.org/sabi/"


def test_all_schemas_share_canonical_namespace():
    schema_files = sorted(SCHEMAS.glob("*.schema.json"))
    assert schema_files, "no schema files found"
    for path in schema_files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["$id"].startswith(CANONICAL_NS), (
            f"{path.name} uses non-canonical $id {doc['$id']!r}")


def test_obsolete_skill_abi_schema_removed():
    assert not (SCHEMAS / "skill-abi.schema.json").exists(), (
        "obsolete duplicate skill-abi.schema.json must stay deleted")


def test_abi_schema_accepts_conformance_block():
    doc = {
        "spec": "sabi/v0.1",
        "skill": "x",
        "capabilities": {"required": []},
        "conformance": {"level": "P3", "spec_version": "sabi/v0.1"},
    }
    assert js.validate(doc, load("abi.schema.json")) == []


def test_abi_schema_rejects_bad_conformance_level():
    doc = {
        "spec": "sabi/v0.1",
        "skill": "x",
        "capabilities": {"required": []},
        "conformance": {"level": "P9"},
    }
    assert js.validate(doc, load("abi.schema.json")) != []
