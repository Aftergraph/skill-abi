"""Tests driven by conformance/ vectors (no network)."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi.resolver import resolve_tier
from sabi.effects import check_observed, envelope_contains, validate_envelope

VECTORS = Path(__file__).resolve().parent / ".." / "conformance"

WORKSPACE = "/ws"


def _run_vector(v):
    check = v.get("check", "observed")
    if check == "observed":
        return check_observed(v["envelope"], v["observed"], workspace=WORKSPACE)
    if check == "contains":
        return envelope_contains(v["outer"], v["inner"], workspace=WORKSPACE)
    if check == "envelope":
        return validate_envelope(v["envelope"])
    raise AssertionError(f"unknown vector check {check!r}")


def test_tier_vectors():
    vecs = yaml.safe_load((VECTORS / "tier-vectors.yaml").read_text(encoding="utf-8"))["vectors"]
    assert len(vecs) >= 4
    for v in vecs:
        assert resolve_tier(v["degradation"], v["capabilities"]) == v["expect_tier"], v["id"]


def test_effect_vectors():
    vecs = yaml.safe_load((VECTORS / "effect-vectors.yaml").read_text(encoding="utf-8"))["vectors"]
    assert len(vecs) >= 5
    for v in vecs:
        got = _run_vector(v)
        for want in v["expect_violations"]:
            assert any(want in g for g in got), (v["id"], got)
        if not v["expect_violations"]:
            assert got == [], (v["id"], got)


def test_effect_vectors_cover_every_check_kind():
    vecs = yaml.safe_load((VECTORS / "effect-vectors.yaml").read_text(encoding="utf-8"))["vectors"]
    kinds = {v.get("check", "observed") for v in vecs}
    assert kinds == {"observed", "contains", "envelope"}, kinds
