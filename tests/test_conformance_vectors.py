"""Tests driven by conformance/ vectors (no network)."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi.resolver import resolve_tier
from sabi.effects import check_observed

VECTORS = Path(__file__).resolve().parent / ".." / "conformance"


def test_tier_vectors():
    vecs = yaml.safe_load((VECTORS / "tier-vectors.yaml").read_text(encoding="utf-8"))["vectors"]
    assert len(vecs) >= 4
    for v in vecs:
        assert resolve_tier(v["degradation"], v["capabilities"]) == v["expect_tier"], v["id"]


def test_effect_vectors():
    vecs = yaml.safe_load((VECTORS / "effect-vectors.yaml").read_text(encoding="utf-8"))["vectors"]
    assert len(vecs) >= 5
    for v in vecs:
        got = check_observed(v["envelope"], v["observed"], workspace="/ws")
        for want in v["expect_violations"]:
            assert any(want in g for g in got), (v["id"], got)
        if not v["expect_violations"]:
            assert got == [], (v["id"], got)
