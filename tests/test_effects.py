"""Tests for sabi.effects (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi.effects import check_observed

ENVELOPE = {
    "message.send": {"destinations": ["chat-1"], "max_operations": 1},
    "filesystem.write": {"scope": ["${workspace}/reports/**"], "max_operations": 5},
    "repository.push": {"branches": ["feature/**"], "max_operations": 1},
    "network.egress": {"domains": [], "max_operations": 0},
    "money": {"max_amount": 0},
    "credentials": {"expose_to_model": False},
}

CLEAN = {
    "message.send": {"count": 1, "destinations": ["chat-1"]},
    "filesystem.write": {"count": 2, "paths": ["/ws/reports/a.md"]},
    "repository.push": {"count": 0},
    "network.egress": {"count": 0, "domains": []},
    "money": {"amount": 0},
    "credentials_exposed": False,
}


def test_clean_run_has_no_violations():
    assert check_observed(ENVELOPE, CLEAN, workspace="/ws") == []


def test_extra_destination_is_violation():
    obs = {"message.send": {"count": 1, "destinations": ["chat-1", "chat-9"]}}
    assert any("destination" in v for v in check_observed(ENVELOPE, obs))


def test_count_overflow_is_violation():
    obs = {"message.send": {"count": 3, "destinations": ["chat-1"]}}
    assert any("count exceeds" in v for v in check_observed(ENVELOPE, obs))


def test_out_of_scope_write_is_violation():
    obs = {"filesystem.write": {"count": 1, "paths": ["/etc/passwd"]}}
    assert any("outside envelope scope" in v for v in check_observed(ENVELOPE, obs))


def test_undeclared_effect_is_violation():
    env = {"money": {"max_amount": 0}}
    obs = {"repository.push": {"count": 1, "branches": ["main"]}}
    assert any("no envelope entry" in v for v in check_observed(env, obs))


def test_wrong_branch_is_violation():
    obs = {"repository.push": {"count": 1, "branches": ["main"]}}
    assert any("outside envelope" in v for v in check_observed(ENVELOPE, obs))


def test_credential_exposure_is_violation():
    obs = {"credentials_exposed": True}
    assert any("credential" in v for v in check_observed(ENVELOPE, obs))
