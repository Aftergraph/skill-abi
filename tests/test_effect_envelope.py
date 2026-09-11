"""Effect-envelope semantics: typing, quantification, and widening rejection.

These tests pin the SEMANTIC BOUND only. SABI decides whether an envelope is
well-formed and whether one envelope stays inside another; runtime and trust
systems enforce the bound. No test here exercises a provider or a runtime.

Widening MUST be rejected: any inner envelope that declares authority beyond
the outer (declared) envelope produces violations.
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi import schema as json_schema
from sabi.effects import (
    CATEGORIES,
    canonical_category,
    envelope_contains,
    validate_envelope,
)

REPO = Path(__file__).resolve().parents[1]
SCHEMAS = REPO / "schemas"
EXAMPLE = REPO / "examples" / "telegram-live-status"
WORKSPACE = "/ws"


def effects_schema():
    return json.loads((SCHEMAS / "effects.schema.json").read_text(encoding="utf-8"))


# ── positive: well-formed envelopes ─────────────────────────────────

FULL_ENVELOPE = {
    "filesystem": {"allowed": True, "scope": ["${workspace}/reports/**"], "max_operations": 5},
    "repository": {"branches": ["feature/**"], "max_operations": 2},
    "process": {"scope": ["git *"], "environment": ["PATH"], "max_operations": 3},
    "network": {"domains": ["api.example.org"], "destinations": ["api.example.org:443"], "max_operations": 4},
    "message": {"destinations": ["chat-1"], "max_operations": 1},
    "artifact": {"paths": ["dist/app.tar.gz"], "max_operations": 1},
    "deployment": {"environment": ["staging"], "destinations": ["staging-cluster"], "max_operations": 1},
    "credential": {"expose_to_model": False, "scope": ["API_TOKEN"], "environment": ["CI"]},
    "money": {"amount": 10, "currency": "USD", "max_operations": 1},
}


def test_all_categories_are_the_expected_nine():
    assert set(CATEGORIES) == {
        "filesystem", "repository", "process", "network", "message",
        "artifact", "deployment", "credential", "money",
    }


def test_full_envelope_is_well_formed():
    assert validate_envelope(FULL_ENVELOPE) == []


def test_full_envelope_passes_json_schema():
    doc = {"effects": FULL_ENVELOPE}
    assert json_schema.validate(doc, effects_schema()) == []


def test_legacy_dotted_aliases_still_validate():
    legacy = {
        "message.send": {"destinations": ["telegram:FIXTURE_CHAT_ID"], "max_operations": 1, "note": "one card update"},
        "filesystem.write": {"scope": [], "max_operations": 0},
        "network.egress": {"domains": [], "max_operations": 0},
        "money": {"max_amount": 0},
        "credentials": {"expose_to_model": False},
    }
    assert validate_envelope(legacy) == []
    assert json_schema.validate({"effects": legacy}, effects_schema()) == []


def test_reference_example_effects_yaml_is_accepted_by_schema():
    doc = yaml.safe_load((EXAMPLE / "effects.yaml").read_text(encoding="utf-8"))
    assert json_schema.validate(doc, effects_schema()) == []


def test_aliases_map_to_canonical_categories():
    assert canonical_category("filesystem.write") == "filesystem"
    assert canonical_category("repository.push") == "repository"
    assert canonical_category("network.egress") == "network"
    assert canonical_category("message.send") == "message"
    assert canonical_category("credentials") == "credential"
    assert canonical_category("money") == "money"
    assert canonical_category("teleportation") is None


def test_containment_of_identical_envelope_is_clean():
    assert envelope_contains(FULL_ENVELOPE, FULL_ENVELOPE, workspace=WORKSPACE) == []


def test_containment_of_narrowed_envelope_is_clean():
    inner = {
        "filesystem": {"scope": ["${workspace}/reports/daily/**"], "max_operations": 1},
        "repository": {"branches": ["feature/x"], "max_operations": 1},
        "message": {"destinations": ["chat-1"], "max_operations": 1},
        "money": {"amount": 5, "currency": "USD", "max_operations": 1},
    }
    assert envelope_contains(FULL_ENVELOPE, inner, workspace=WORKSPACE) == []


def test_containment_ignores_vacuous_inner_declarations():
    outer = {"message": {"destinations": ["chat-1"], "max_operations": 1}}
    inner = {"message": {"destinations": ["chat-1"], "max_operations": 1},
             "network": {"domains": [], "max_operations": 0}}
    assert envelope_contains(outer, inner, workspace=WORKSPACE) == []


# ── negative: widening is rejected (one per constraint dimension) ───

def _widens(outer, inner, workspace=WORKSPACE):
    violations = envelope_contains(outer, inner, workspace=workspace)
    assert violations, (outer, inner)
    assert any("widening" in v for v in violations), violations
    return violations


def test_widening_max_operations_is_rejected():
    _widens({"message": {"destinations": ["chat-1"], "max_operations": 1}},
            {"message": {"destinations": ["chat-1"], "max_operations": 5}})


def test_widening_filesystem_scope_glob_is_rejected():
    _widens({"filesystem": {"scope": ["${workspace}/reports/**"], "max_operations": 5}},
            {"filesystem": {"scope": ["${workspace}/**"], "max_operations": 5}})


def test_widening_filesystem_scope_with_new_path_is_rejected():
    _widens({"filesystem": {"scope": ["${workspace}/reports/**"], "max_operations": 5}},
            {"filesystem": {"scope": ["${workspace}/reports/**", "/etc/passwd"], "max_operations": 5}})


def test_widening_artifact_paths_is_rejected():
    _widens({"artifact": {"paths": ["dist/app.tar.gz"], "max_operations": 1}},
            {"artifact": {"paths": ["dist/app.tar.gz", "/etc/passwd"], "max_operations": 1}})


def test_widening_repository_branch_is_rejected():
    _widens({"repository": {"branches": ["feature/**"], "max_operations": 2}},
            {"repository": {"branches": ["main"], "max_operations": 2}})


def test_widening_message_destination_is_rejected():
    _widens({"message": {"destinations": ["chat-1"], "max_operations": 1}},
            {"message": {"destinations": ["chat-1", "chat-9"], "max_operations": 1}})


def test_widening_network_domain_is_rejected():
    _widens({"network": {"domains": ["api.example.org"], "max_operations": 1}},
            {"network": {"domains": ["api.example.org", "exfil.example.net"], "max_operations": 1}})


def test_widening_network_destination_is_rejected():
    _widens({"network": {"destinations": ["api.example.org:443"], "max_operations": 1}},
            {"network": {"destinations": ["api.example.org:443", "exfil.example.net:443"], "max_operations": 1}})


def test_widening_process_scope_is_rejected():
    _widens({"process": {"scope": ["git *"], "environment": ["PATH"], "max_operations": 3}},
            {"process": {"scope": ["git *", "curl *"], "environment": ["PATH"], "max_operations": 3}})


def test_widening_process_environment_is_rejected():
    _widens({"process": {"scope": ["git *"], "environment": ["PATH"], "max_operations": 3}},
            {"process": {"scope": ["git *"], "environment": ["PATH", "AWS_SECRET_ACCESS_KEY"], "max_operations": 3}})


def test_widening_deployment_environment_is_rejected():
    _widens({"deployment": {"environment": ["staging"], "max_operations": 1}},
            {"deployment": {"environment": ["staging", "production"], "max_operations": 1}})


def test_widening_credential_scope_is_rejected():
    _widens({"credential": {"expose_to_model": False, "scope": ["API_TOKEN"]}},
            {"credential": {"expose_to_model": False, "scope": ["API_TOKEN", "AWS_SECRET_ACCESS_KEY"]}})


def test_widening_credential_exposure_is_rejected():
    _widens({"credential": {"expose_to_model": False, "scope": ["API_TOKEN"], "max_operations": 1}},
            {"credential": {"expose_to_model": True, "scope": ["API_TOKEN"], "max_operations": 1}})


def test_widening_money_amount_is_rejected():
    _widens({"money": {"amount": 10, "currency": "USD", "max_operations": 1}},
            {"money": {"amount": 100, "currency": "USD", "max_operations": 1}})


def test_widening_money_currency_is_rejected():
    _widens({"money": {"amount": 10, "currency": "USD", "max_operations": 1}},
            {"money": {"amount": 10, "currency": "EUR", "max_operations": 1}})


def test_widening_money_without_currency_is_rejected():
    _widens({"money": {"amount": 10, "currency": "USD", "max_operations": 1}},
            {"money": {"amount": 10, "max_operations": 1}})


def test_widening_allowed_flag_is_rejected():
    _widens({"process": {"allowed": False}},
            {"process": {"allowed": True, "max_operations": 1}})


def test_widening_by_adding_an_undeclared_category_is_rejected():
    _widens({"filesystem": {"scope": ["${workspace}/**"], "max_operations": 1}},
            {"filesystem": {"scope": ["${workspace}/**"], "max_operations": 1},
             "network": {"domains": ["api.example.org"], "max_operations": 1}})


def test_widening_undeclared_max_operations_is_rejected():
    # Undeclared outer dimension defaults to empty (0), never unlimited.
    _widens({"repository": {"branches": ["feature/**"]}},
            {"repository": {"branches": ["feature/**"], "max_operations": 1}})


# ── negative: malformed / unquantified envelopes ────────────────────

@pytest.mark.parametrize("envelope,needle", [
    ({"teleportation": {"max_operations": 1}}, "unknown effect category"),
    ({"filesystem": {"branches": ["main"], "max_operations": 1}}, "not applicable"),
    ({"message": {"destinations": ["chat-1"], "max_operations": -1}}, "non-negative integer"),
    ({"message": {"destinations": ["chat-1"], "max_operations": "many"}}, "non-negative integer"),
    ({"message": {"destinations": "chat-1", "max_operations": 1}}, "must be a list"),
    ({"money": {"amount": 10, "max_operations": 1}}, "currency"),
    ({"money": {"amount": 10, "currency": "usd"}}, "ISO 4217"),
    ({"money": {"amount": -1, "currency": "USD"}}, "non-negative number"),
    ({"network": {"allowed": False, "domains": ["api.example.org"], "max_operations": 3}}, "allowed is false"),
    ({"process": {"allowed": True}}, "no quantified bound"),
    ({"credential": {"scope": ["API_TOKEN"]}}, None),  # valid: expose_to_model optional here
    ({"filesystem": {}}, "non-empty quantified mapping"),
    ({"filesystem": {"max_operations": 1}, "filesystem.write": {"max_operations": 1}}, "duplicate effect category"),
])
def test_malformed_envelopes_are_rejected(envelope, needle):
    errors = validate_envelope(envelope)
    if needle is None:
        assert errors == [], errors
    else:
        assert any(needle in e for e in errors), (envelope, errors)


# ── negative: schema-level typing ───────────────────────────────────

def test_schema_rejects_unknown_category():
    doc = {"effects": {"teleportation": {"max_operations": 1}}}
    assert json_schema.validate(doc, effects_schema()) != []


def test_schema_rejects_non_applicable_constraint():
    doc = {"effects": {"filesystem": {"branches": ["main"], "max_operations": 1}}}
    assert json_schema.validate(doc, effects_schema()) != []


def test_schema_rejects_wrong_max_operations_type():
    doc = {"effects": {"message": {"destinations": ["chat-1"], "max_operations": "many"}}}
    assert json_schema.validate(doc, effects_schema()) != []


def test_schema_rejects_negative_max_operations():
    doc = {"effects": {"message": {"destinations": ["chat-1"], "max_operations": -1}}}
    assert json_schema.validate(doc, effects_schema()) != []


def test_schema_rejects_bad_currency_pattern():
    doc = {"effects": {"money": {"amount": 10, "currency": "usd"}}}
    assert json_schema.validate(doc, effects_schema()) != []


def test_schema_rejects_credential_model_exposure():
    doc = {"effects": {"credential": {"expose_to_model": True}}}
    assert json_schema.validate(doc, effects_schema()) != []


def test_schema_requires_effects_mapping():
    assert json_schema.validate({}, effects_schema()) != []
    assert json_schema.validate({"effects": {}}, effects_schema()) != []
