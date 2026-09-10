"""Deterministic degradation-tier resolver (SABI D module).

Rule: T* = max{Ti | requires(Ti) ⊆ R}, evaluated in declaration order
(full → … → reject). No model inference involved.
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional


def resolve_tier(degradation: Dict, capabilities: Iterable[str]) -> Optional[str]:
    """Return the first tier whose requirements are satisfied.

    Tiers are evaluated in mapping order; a tier with
    ``terminal: true`` always matches (it is the floor). Returns None
    only when the mapping is empty.
    """
    R = set(capabilities or [])
    for name, spec in (degradation or {}).items():
        spec = spec or {}
        if spec.get("terminal") is True:
            return name
        if set(spec.get("requires", []) or []) <= R:
            return name
    return None
