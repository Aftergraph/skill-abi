"""Quantified effect-envelope checker (SABI E module).

Compares observed effects against the declared envelope and returns a
list of violation strings (empty means contained). Never invents
effects: undeclared-but-zero observations are clean; undeclared
non-zero observations are violations.
"""
from __future__ import annotations

import fnmatch
from typing import Dict, List


def _scope_ok(patterns, value: str, workspace: str) -> bool:
    for pat in patterns or []:
        pat = pat.replace("${workspace}", workspace or "")
        if fnmatch.fnmatch(value, pat):
            return True
    return False


def check_observed(envelope: Dict, observed: Dict, workspace: str = "") -> List[str]:
    """Check one observed-effects mapping against the envelope."""
    errors: List[str] = []
    env = envelope or {}
    obs = observed or {}

    ms, mobs = env.get("message.send", {}), obs.get("message.send", {})
    if mobs.get("count", 0) > ms.get("max_operations", 0):
        errors.append("message.send count exceeds envelope")
    for d in mobs.get("destinations", []):
        if d not in (ms.get("destinations") or []):
            errors.append(f"message.send destination {d} outside envelope")

    if "filesystem.write" in env:
        fw, fobs = env["filesystem.write"], obs.get("filesystem.write", {})
        if fobs.get("count", 0) > fw.get("max_operations", 0):
            errors.append("filesystem.write count exceeds envelope")
        for p in fobs.get("paths", []):
            if not _scope_ok(fw.get("scope"), p, workspace):
                errors.append(f"write path {p} outside envelope scope")
    elif obs.get("filesystem.write", {}).get("count", 0):
        errors.append("filesystem.write observed but no envelope entry")

    if "repository.push" in env:
        rp, robs = env["repository.push"], obs.get("repository.push", {})
        if robs.get("count", 0) > rp.get("max_operations", 0):
            errors.append("repository.push count exceeds envelope")
        for b in robs.get("branches", []):
            if not any(fnmatch.fnmatch(b, pat) for pat in (rp.get("branches") or [])):
                errors.append(f"push branch {b} outside envelope")
    elif obs.get("repository.push", {}).get("count", 0):
        errors.append("repository.push observed but no envelope entry")

    ne, neobs = env.get("network.egress", {}), obs.get("network.egress", {})
    if neobs.get("count", 0) > ne.get("max_operations", 0):
        errors.append("network.egress count exceeds envelope")
    for d in neobs.get("domains", []):
        if d not in (ne.get("domains") or []):
            errors.append(f"egress domain {d} outside envelope")

    if (obs.get("money", {}) or {}).get("amount", 0) > (env.get("money", {}) or {}).get("max_amount", 0):
        errors.append("money exceeds envelope")
    if obs.get("credentials_exposed", False):
        errors.append("credential exposure violates envelope")
    return errors
