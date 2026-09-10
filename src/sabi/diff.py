"""Semantic diff between two skill contract versions (SABI diff module).

Compares inputs, outputs, capabilities, effects, degradation,
verification obligations. Classifies MAJOR / MINOR / PATCH.
Never infers compatibility from Markdown text-diff size.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Tuple


def _read(p: Path):
    import yaml
    import json
    if p.suffix in (".yaml", ".yml"):
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    if p.suffix == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _deep_diff(old, new, path=""):
    out = []
    if isinstance(old, dict) and isinstance(new, dict):
        for k in sorted(set(old) | set(new)):
            if k not in old:
                out.append(("added", f"{path}{k}", None, new[k]))
            elif k not in new:
                out.append(("removed", f"{path}{k}", old[k], None))
            else:
                out.extend(_deep_diff(old[k], new[k], f"{path}{k}."))
    elif isinstance(old, list) and isinstance(new, list):
        if old != new:
            out.append(("changed", path.rstrip("."), old, new))
    elif old != new:
        out.append(("changed", path.rstrip("."), old, new))
    return out


def semantic_diff(old_dir, new_dir) -> Tuple[str, List[str], List[str], List[str]]:
    """Return (bump, breaking, minor, notes) comparing two skill dirs."""
    old_dir, new_dir = Path(old_dir), Path(new_dir)
    old_abi = _read(old_dir / "skill.abi.yaml") or {}
    new_abi = _read(new_dir / "skill.abi.yaml") or {}
    breaking, minor, notes = [], [], []

    old_req = set(((old_abi.get("capabilities", {}) or {}).get("required", [])) or [])
    new_req = set(((new_abi.get("capabilities", {}) or {}).get("required", [])) or [])
    for c in sorted(new_req - old_req):
        breaking.append(f"New required capability: + {c}")
    for c in sorted(old_req - new_req):
        breaking.append(f"Removed required capability: - {c}")
    old_opt = set(((old_abi.get("capabilities", {}) or {}).get("optional", [])) or [])
    new_opt = set(((new_abi.get("capabilities", {}) or {}).get("optional", [])) or [])
    for c in sorted(new_opt - old_opt):
        minor.append(f"New optional capability: + {c}")

    old_eff = ((_read(old_dir / "effects.yaml") or {}).get("effects", {}))
    new_eff = ((_read(new_dir / "effects.yaml") or {}).get("effects", {}))
    for kind, where, o, n in _deep_diff(old_eff, new_eff):
        if where.endswith(".note"):
            notes.append(f"Note text changed: {where}")
        elif kind == "added":
            breaking.append(f"New effect: + {where} = {n}")
        else:
            breaking.append(f"Effect change ({kind}): {where}: {o} -> {n}")

    old_deg = list(((_read(old_dir / "degradation.yaml") or {}).get("degradation", {}).keys()))
    new_deg = list(((_read(new_dir / "degradation.yaml") or {}).get("degradation", {}).keys()))
    for t in new_deg:
        if t not in old_deg:
            minor.append(f"New degradation tier: + {t}")
    for t in old_deg:
        if t not in new_deg:
            breaking.append(f"Removed degradation tier: - {t}")

    for ref in ("inputs", "outputs"):
        o_rel = ((old_abi.get(ref, {}) or {}).get("schema"))
        n_rel = ((new_abi.get(ref, {}) or {}).get("schema"))
        if o_rel and n_rel:
            oh = hashlib.sha256((old_dir / o_rel).read_bytes()).hexdigest()[:12]
            nh = hashlib.sha256((new_dir / n_rel).read_bytes()).hexdigest()[:12]
            if oh != nh:
                minor.append(f"Schema changed ({ref}); reviewer must confirm compatibility")

    old_ver = set(((old_abi.get("verification", {}) or {}).get("required", [])) or [])
    new_ver = set(((new_abi.get("verification", {}) or {}).get("required", [])) or [])
    for v in sorted(new_ver - old_ver):
        minor.append(f"New verification obligation: + {v}")
    for v in sorted(old_ver - new_ver):
        breaking.append(f"Weakened verification: - {v}")

    bump = "MAJOR" if breaking else ("MINOR" if minor else "PATCH")
    return bump, breaking, minor, notes
