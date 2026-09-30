import json
from pathlib import Path

from sabi import schema as json_schema


ROOT = Path(__file__).resolve().parents[1]


def _schema():
    return json.loads((ROOT / "schemas" / "abi.schema.json").read_text(encoding="utf-8"))


def _base():
    return {
        "spec": "sabi/v0.1",
        "skill": "demo-skill",
        "capabilities": {"required": ["shell.execute"], "optional": []},
    }


def test_tool_binding_schema_accepts_non_authoritative_constraints():
    abi = _base()
    abi["tool_bindings"] = [{
        "capability": "shell.execute",
        "acceptable_kinds": ["cli"],
        "acceptable_runtimes": ["runtime", "relay"],
        "selector": "lowest-risk",
        "credential_exposure": False,
    }]
    assert json_schema.validate(abi, _schema()) == []


def test_tool_binding_schema_rejects_credential_exposure():
    abi = _base()
    abi["tool_bindings"] = [{
        "capability": "shell.execute",
        "credential_exposure": True,
    }]
    errors = json_schema.validate(abi, _schema())
    assert any("expected const False" in error for error in errors)
