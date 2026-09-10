"""Tests for sabi.resolver (no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi.resolver import resolve_tier

LATTICE = {
    "full": {"requires": ["a", "b", "c"]},
    "partial": {"requires": ["a", "b"]},
    "review": {"requires": ["a"]},
    "advisory": {"requires": []},
    "reject": {"terminal": True},
}


def test_full_when_all_present():
    assert resolve_tier(LATTICE, ["a", "b", "c", "extra"]) == "full"


def test_degrades_one_step():
    assert resolve_tier(LATTICE, ["a", "b"]) == "partial"


def test_degrades_to_advisory():
    assert resolve_tier(LATTICE, ["zzz"]) == "advisory"


def test_terminal_floor_on_empty():
    assert resolve_tier(LATTICE, []) == "advisory"


def test_empty_mapping_returns_none():
    assert resolve_tier({}, ["a"]) is None


def test_terminal_tier_returned():
    lattice = {"only": {"terminal": True}}
    assert resolve_tier(lattice, []) == "only"
