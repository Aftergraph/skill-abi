"""Public SABI API surface.

Canonical operations exposed to CLI and library consumers. Every
function here is a thin wrapper over the internal modules; the CLI
imports from here, not from internal modules directly.

Invariant: CLI_VALID == LIBRARY_VALID — the same validation code runs
regardless of entry point.

Binding != Authorization (normative). Binding maps capabilities to
concrete implementations; no authority is granted by the bind step.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sabi.canon import canonical_json, digest_file_uri, sha256_file
from sabi.certify import build_certificate
from sabi.errors import IntegrityError, SabiError, ValidationError
from sabi.lockfile import check_lock, compute_digests, locked_files, write_lock as _write_lock
from sabi.parser import load_manifest, parse_abi_yaml
from sabi.resolver import resolve_tier
from sabi import schema as json_schema


# ── requirement-object export seam (Team G, preserved) ──────────────

REQUIREMENT_OBJECT_SCHEMA = "https://sabi.dev/schemas/requirement-object.json"


def export_requirement_object(skill_dir: Path) -> Dict[str, Any]:
    """Produce a requirement-object dict from a skill directory.

    Returns dict with keys: schema, skill, version, spec, digests,
    required_capabilities, optional_capabilities, effect_envelope,
    degradation_tiers, verification_obligations.
    """
    skill_dir = Path(skill_dir)
    manifest = load_manifest(skill_dir)
    abi = parse_abi_yaml(skill_dir / "skill.abi.yaml")
    caps = abi.get("capabilities", {}) or {}
    required = caps.get("required", []) or []
    optional = caps.get("optional", []) or []

    # Digests
    digests = {}
    sm = skill_dir / "SKILL.md"
    if sm.is_file():
        digests["skill_md"] = digest_file_uri(sm)
    ap = skill_dir / "skill.abi.yaml"
    if ap.is_file():
        digests["abi"] = digest_file_uri(ap)

    # Effect envelope
    import yaml
    effect_envelope = {}
    ep = skill_dir / "effects.yaml"
    if ep.is_file():
        doc = yaml.safe_load(ep.read_text(encoding="utf-8")) or {}
        effect_envelope = doc.get("effects", {})

    # Degradation tiers
    import yaml
    degradation_tiers = []
    dp = skill_dir / "degradation.yaml"
    if dp.is_file():
        doc = yaml.safe_load(dp.read_text(encoding="utf-8")) or {}
        tiers = doc.get("degradation", {})
        degradation_tiers = list(tiers.keys())

    # Verification obligations
    verification_obligations = abi.get("verification", {})

    return {
        "schema": REQUIREMENT_OBJECT_SCHEMA,
        "skill": manifest.name,
        "version": abi.get("version", ""),
        "spec": abi.get("spec", ""),
        "digests": digests,
        "required_capabilities": required,
        "optional_capabilities": optional,
        "effect_envelope": effect_envelope,
        "degradation_tiers": degradation_tiers,
        "verification_obligations": verification_obligations,
    }


def requirement_object_bytes(skill_dir: Path) -> bytes:
    """Return canonical JSON bytes of the requirement object."""
    return canonical_json(export_requirement_object(skill_dir))


def write_requirement_object(skill_dir: Path) -> Path:
    """Write requirement-object.json and return its path."""
    obj = export_requirement_object(skill_dir)
    out = skill_dir / "requirement-object.json"
    out.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


# ── canonical operations ─────────────────────────────────────────────


def validate_canonical(skill_dir: Path, schemas_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Validate one skill directory. Returns dict with 'level' and 'errors'.

    This is the single canonical validation path. The CLI calls this;
    tests call this. CLI_VALID == LIBRARY_VALID.
    """
    from sabi.validator import validate_skill
    level, errors = validate_skill(skill_dir, schemas_dir=schemas_dir)
    return {"skill": skill_dir.name, "level": level, "errors": errors}


def resolve(degradation: Dict, capabilities) -> Optional[str]:
    """Resolve the maximal degradation tier. Thin wrapper."""
    return resolve_tier(degradation, capabilities)


def diff(old: str, new: str) -> Tuple[str, List[str], List[str], List[str]]:
    """Semantic diff between two SABI versions."""
    from sabi.diff import semantic_diff
    return semantic_diff(old, new)


def bind(skill_dir: Path, runtime_profile: Dict) -> Dict[str, Any]:
    """Produce a deterministic binding result.

    Input: skill directory + runtime profile (with declared capabilities).
    Output: binding record with resolved tier, concrete implementations,
    unresolved caps, effect envelope reference.

    Invariant: Binding != Authorization — no authority is granted here.
    """
    skill_dir = Path(skill_dir)
    abi = parse_abi_yaml(skill_dir / "skill.abi.yaml")
    deg_path = skill_dir / "degradation.yaml"
    try:
        import yaml
        deg = (yaml.safe_load(deg_path.read_text(encoding="utf-8")) or {}).get("degradation", {})
    except Exception:
        deg = {}
    eff_path = skill_dir / "effects.yaml"
    try:
        import yaml
        eff_doc = yaml.safe_load(eff_path.read_text(encoding="utf-8")) or {}
    except Exception:
        eff_doc = {}

    caps = abi.get("capabilities", {}) or {}
    required = caps.get("required", []) or []
    optional = caps.get("optional", []) or []
    r_caps = set(runtime_profile.get("capabilities", []) or [])
    tier = resolve_tier(deg, r_caps)

    # Map required caps to implementations from profile
    implementations = runtime_profile.get("implementations", {}) or {}
    resolved = {cap: implementations.get(cap, "?") for cap in required if cap in r_caps}
    unresolved = [cap for cap in required if cap not in r_caps]

    return {
        "skill": abi.get("skill", skill_dir.name),
        "sabi": abi.get("spec", "sabi/v0.1"),
        "runtime_profile": {
            "runtime": runtime_profile.get("runtime", "?"),
            "capabilities": sorted(r_caps),
        },
        "required_capabilities": required,
        "resolved_required_caps": resolved,
        "unresolved_required_caps": unresolved,
        "optional_capabilities": optional,
        "selected_degradation_tier": tier,
        "effect_envelope_ref": str(eff_path.relative_to(skill_dir) if eff_path.is_file() else ""),
        "note": "Binding != Authorization. This record maps capabilities to implementations; no authority is granted.",
    }


def certify(skill_dir: Path) -> Dict[str, Any]:
    """Build a portability certificate for a skill."""
    from sabi.certify import evaluate_invariants
    from sabi.resolver import resolve_tier
    skill_dir = Path(skill_dir)
    try:
        import yaml
        deg = (yaml.safe_load((skill_dir / "degradation.yaml").read_text(encoding="utf-8")) or {}).get("degradation", {})
    except Exception:
        deg = {}
    records = []
    for prof_p in sorted((skill_dir / "bindings").glob("*.yaml")):
        prof = yaml.safe_load(prof_p.read_text(encoding="utf-8")) if prof_p.is_file() else {}
        caps = prof.get("capabilities", []) or []
        records.append((
            prof.get("runtime", prof_p.stem),
            resolve_tier(deg, caps),
            evaluate_invariants(skill_dir, caps),
        ))
    return build_certificate(skill_dir, records)


def verify_certificate(cert_path: Path, skill_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Verify a portability certificate. Optionally re-verify digest against skill_dir."""
    from sabi.errors import IntegrityError
    cert = json.loads(cert_path.read_text(encoding="utf-8"))
    problems = []
    for k in ("skill", "skill_digest", "abi_digest", "cases", "passed", "failed"):
        if k not in cert:
            problems.append(f"missing field: {k}")
    if cert.get("passed", 0) + cert.get("failed", 0) != cert.get("cases", -1):
        problems.append("passed+failed != cases")
    if cert.get("signed"):
        problems.append("signed=true requires detached signature check (see sabi-sign)")

    # Optional digest re-verification against the skill directory
    if skill_dir is not None and not problems:
        skill_dir = Path(skill_dir)
        actual_skill_digest = digest_file_uri(skill_dir / "SKILL.md")
        if cert.get("skill_digest") and cert["skill_digest"] != actual_skill_digest:
            raise IntegrityError(
                f"skill_digest mismatch: {cert['skill_digest']} != {actual_skill_digest}"
            )
        abi_path = skill_dir / "skill.abi.yaml"
        if abi_path.is_file():
            actual_abi_digest = digest_file_uri(abi_path)
            if cert.get("abi_digest") and cert["abi_digest"] != actual_abi_digest:
                raise IntegrityError(
                    f"abi_digest mismatch: {cert['abi_digest']} != {actual_abi_digest}"
                )

    return {
        "valid": not problems,
        "certificate": cert.get("certificate"),
        "cases": cert.get("cases"),
        "passed": cert.get("passed"),
        "failed": cert.get("failed"),
        "problems": problems,
    }


def lock(skill_dir: Path) -> int:
    """Write a fresh skill.lock. Returns number of files locked."""
    return _write_lock(skill_dir)


def verify_lock(skill_dir: Path) -> Dict[str, Any]:
    """Verify lock integrity + coverage. Raises IntegrityError on tamper/corrupt/missing.

    Returns dict with 'ok' bool and 'errors' list.
    """
    skill_dir = Path(skill_dir)
    lock_path = skill_dir / "skill.lock"

    if not lock_path.is_file():
        raise IntegrityError("skill.lock missing (run `sabi lock` first)")

    try:
        doc = json.loads(lock_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise IntegrityError(f"skill.lock invalid JSON: {exc}") from exc

    current = compute_digests(skill_dir)
    pinned = doc.get("files", {})
    errors: List[str] = []

    # Integrity check: every current file must match pinned digest
    for rel, digest in current.items():
        if pinned.get(rel) != digest:
            errors.append(f"{rel} digest mismatch (skill changed, re-lock)")

    # Coverage check: every pinned file must still exist (forward)
    for rel in pinned:
        if rel not in current:
            errors.append(f"{rel} pinned but file gone (coverage gap)")

    # Forward coverage check: every current file must be pinned (reverse)
    for rel in current:
        if rel not in pinned:
            errors.append(f"{rel} not pinned (coverage gap — re-lock)")

    # Ephemeral rejection: lock must not pin attestations or ephemeral files
    EPHEMERAL_PREFIXES = ("attestations/", "evidence/", ".tmp/")
    for rel in pinned:
        if any(rel.startswith(prefix) for prefix in EPHEMERAL_PREFIXES):
            errors.append(f"{rel} is ephemeral (attestation/evidence) — must not be locked")

    if errors:
        raise IntegrityError("; ".join(errors))

    return {"ok": True, "files": len(pinned), "errors": errors}
