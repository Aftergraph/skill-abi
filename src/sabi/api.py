"""SABI cross-repo requirement-object export (public API seam).

Freezes the minimal machine-readable surface other repositories may
consume. A requirement object answers WHAT must remain true about a
skill; it never decides WHERE/HOW a runtime binds (runtime's job) or
WHETHER the runtime is trusted (trust plane's job).

Invariant (normative, see spec/cross-repo-contract.md):
  SABI says WHAT must remain true. Runtime decides WHERE/HOW.
  Trust decides WHETHER.

Consumers (registries, vaults, benchmarks) MUST treat the exported
object as derived data from the skill directory; the skill-abi
repository remains the only source of truth.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml

from sabi.canon import canonical_json, digest_file_uri
from sabi.parser import load_manifest

REQUIREMENT_OBJECT_SCHEMA = "sabi/requirement-object/v0.1"


def export_requirement_object(skill_dir) -> Dict[str, Any]:
    """Build the frozen requirement object for one skill directory."""
    skill_dir = Path(skill_dir)
    manifest = load_manifest(skill_dir)
    eff = skill_dir / "effects.yaml"
    effect_envelope = {}
    if eff.is_file():
        effect_envelope = (yaml.safe_load(eff.read_text(encoding="utf-8")) or {}).get("effects", {}) or {}
    deg = skill_dir / "degradation.yaml"
    degradation_tiers = []
    if deg.is_file():
        degradation_tiers = list(((yaml.safe_load(deg.read_text(encoding="utf-8")) or {}).get("degradation", {}) or {}).keys())
    return {
        "schema": REQUIREMENT_OBJECT_SCHEMA,
        "skill": manifest.name,
        "version": manifest.version,
        "spec": manifest.spec or "sabi/v0.1",
        "digests": {
            "skill_md": digest_file_uri(skill_dir / "SKILL.md"),
            "abi": digest_file_uri(skill_dir / "skill.abi.yaml"),
        },
        "required_capabilities": list(manifest.capabilities_required),
        "optional_capabilities": list(manifest.capabilities_optional),
        "effect_envelope": effect_envelope,
        "degradation_tiers": degradation_tiers,
        "verification_obligations": list(manifest.verification_required),
    }


def requirement_object_bytes(skill_dir) -> bytes:
    """Canonical JSON bytes of the requirement object (stable digest)."""
    return canonical_json(export_requirement_object(skill_dir))


def write_requirement_object(skill_dir, out_path=None) -> Path:
    """Write requirement-object JSON (pretty, sorted keys)."""
    out = Path(out_path) if out_path else Path(skill_dir) / "requirement-object.json"
    out.write_text(json.dumps(export_requirement_object(skill_dir), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out
