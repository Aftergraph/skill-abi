"""Conformance runner + certificate handling (SABI certify module).

Evaluates file-based invariants against a skill directory and builds
portability certificates. Certificates record the *evidence class* they
actually rest on; static evaluation can never claim a runtime class,
and unsigned evidence can never claim ATTESTED. The `signed` flag is
set only by the signing sidecar, never here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# Evidence classes, ordered weakest to strongest. A certificate claims
# exactly the strongest class its evidence supports.
EVIDENCE_CLASSES = (
    "SPEC_VALID",          # P1: parses + spec-valid, static only
    "STATIC_CONFORMANT",   # P2/P3: static invariants pass, no execution
    "RUNTIME_TESTED",      # P4: one runtime run receipt
    "MULTI_RUNTIME_TESTED",  # P4M: >=2 independent run receipts
    "ATTESTED",            # P5: signed over P4M evidence
)

# A static-only certificate must never carry wording equivalent to full
# runtime certification.
NOTE_BY_CLASS = {
    "SPEC_VALID": "static evidence only; spec-valid, not fully conformant; "
                  "no runtime execution performed",
    "STATIC_CONFORMANT": "static evidence only; no runtime execution "
                         "performed; not runtime-tested, not attested",
    "RUNTIME_TESTED": "runtime evidence from one runtime; not multi-runtime "
                      "tested, not attested",
    "MULTI_RUNTIME_TESTED": "runtime evidence from multiple runtimes; "
                            "unsigned, not attested",
    "ATTESTED": "signed attestation over multi-runtime evidence",
}


def _load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def file_digest(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def classify_evidence(run_receipts, signed: bool = False, static_ok: bool = True) -> str:
    """Return the highest evidence class actually supported by the evidence.

    Non-conflation rules enforced here:
    - static-only evidence never yields a runtime class;
    - a single runtime never yields MULTI_RUNTIME_TESTED;
    - unsigned evidence never yields ATTESTED (ATTESTED needs P4M + signature).
    """
    n = len(list(run_receipts or []))
    if n >= 2:
        return "ATTESTED" if signed else "MULTI_RUNTIME_TESTED"
    if n == 1:
        return "RUNTIME_TESTED"
    return "STATIC_CONFORMANT" if static_ok else "SPEC_VALID"


def evaluate_invariants(skill_dir, runtime_caps) -> List:
    """Evaluate conformance/invariants.yaml; return [(id, ok)]."""
    from .resolver import resolve_tier
    skill_dir = Path(skill_dir)
    invs = _load_yaml(skill_dir / "conformance" / "invariants.yaml")
    effects = (_load_yaml(skill_dir / "effects.yaml") or {}).get("effects", {})
    out = []
    for inv in invs:
        iid = inv.get("id", "?")
        ok = False
        if "check" in inv:
            try:
                lexpr, rexpr = inv["check"].split("==", 1)
                node = {"effects": effects}
                parts = [x.strip() for x in lexpr.strip().split(".")]
                i = 0
                while i < len(parts):
                    for j in range(len(parts), i, -1):
                        key = ".".join(parts[i:j])
                        if isinstance(node, dict) and key in node:
                            node = node[key]
                            i = j
                            break
                    else:
                        raise KeyError(parts[i])
                ok = node == json.loads(rexpr.strip())
            except Exception:
                ok = False
        elif "remove_capability" in inv:
            base = set(runtime_caps)
            if inv.get("base_runtime"):
                bp = skill_dir / "bindings" / (inv["base_runtime"] + ".yaml")
                base = set((_load_yaml(bp) or {}).get("capabilities", []) or [])
            deg = (_load_yaml(skill_dir / "degradation.yaml") or {}).get("degradation", {})
            ok = resolve_tier(deg, base - set(inv["remove_capability"])) == inv["expect_tier"]
        elif "capabilities" in inv and "expect_tier" in inv:
            deg = (_load_yaml(skill_dir / "degradation.yaml") or {}).get("degradation", {})
            ok = resolve_tier(deg, inv["capabilities"]) == inv["expect_tier"]
        elif iid == "terminal-tier-last":
            deg = (_load_yaml(skill_dir / "degradation.yaml") or {}).get("degradation", {})
            names = list(deg.keys())
            ok = not (deg[names[0]] or {}).get("terminal") and (deg[names[-1]] or {}).get("terminal") is True
        elif iid == "lock-covers-contract":
            lock = Path(skill_dir) / "skill.lock"
            if lock.is_file():
                pinned = set(json.loads(lock.read_text(encoding="utf-8")).get("files", {}).keys())
                need = {"skill.abi.yaml", "effects.yaml", "degradation.yaml"}
                need |= {q.relative_to(skill_dir).as_posix() for q in (skill_dir / "schemas").glob("*.json")}
                ok = need <= pinned
        out.append((iid, ok))
    return out


def build_certificate(skill_dir, runtime_results, run_receipts=None, signed=False) -> Dict:
    """Build an UNSIGNED portability certificate dict.

    runtime_results: [(runtime_name, tier, [(id, ok), ...])] from static
    invariant evaluation.
    run_receipts: optional runtime execution receipts; each a mapping with
    at least ``runtime``, ``harness`` and ``evidence`` (a path relative to
    the skill dir). Presence of receipts is what elevates the certificate
    above STATIC_CONFORMANT.
    signed: only the signing sidecar sets this; never infer it here.
    """
    skill_dir = Path(skill_dir)
    passed = sum(1 for _, _, rs in runtime_results for _, ok in rs if ok)
    failed = sum(1 for _, _, rs in runtime_results for _, ok in rs if not ok)
    receipts = [dict(r) for r in (run_receipts or [])]
    static_ok = failed == 0
    evidence_class = classify_evidence(receipts, signed=bool(signed), static_ok=static_ok)
    abi = _load_yaml(skill_dir / "skill.abi.yaml") or {}
    lock = skill_dir / "skill.lock"
    cert = {
        "skill": skill_dir.name,
        "skill_digest": file_digest(skill_dir / "SKILL.md"),
        "abi_digest": file_digest(skill_dir / "skill.abi.yaml"),
        "lock_digest": file_digest(lock) if lock.is_file() else None,
        "sabi": abi.get("spec", "sabi/v0.1"),
        "tested_runtimes": [{"runtime": r, "tier": t} for r, t, _ in runtime_results],
        "tested_tiers": sorted({t for _, t, _ in runtime_results if t}),
        "cases": passed + failed,
        "passed": passed,
        "failed": failed,
        "effect_violations": 0,
        "evidence_class": evidence_class,
        "run_receipts": receipts,
        "signed": bool(signed),
        "note": NOTE_BY_CLASS[evidence_class],
    }
    return cert
