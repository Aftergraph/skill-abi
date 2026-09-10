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
