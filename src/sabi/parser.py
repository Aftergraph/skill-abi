"""Parse SKILL.md frontmatter and skill.abi.yaml into Manifest dataclasses."""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from sabi.errors import ValidationError


@dataclass
class Manifest:
    name: str
    description: str
    spec: str = ""
    version: str = ""
    capabilities_required: List[str] = field(default_factory=list)
    capabilities_optional: List[str] = field(default_factory=list)
    inputs_schema: Optional[str] = None
    outputs_schema: Optional[str] = None
    verification_required: List[str] = field(default_factory=list)
    raw_frontmatter: Dict[str, Any] = field(default_factory=dict)
    raw_abi: Dict[str, Any] = field(default_factory=dict)


def parse_frontmatter(text: str) -> tuple:
    """Extract YAML frontmatter from SKILL.md text.

    Returns (frontmatter_dict, body_text).
    Raises ValidationError on malformed frontmatter.
    """
    if not text.startswith("---"):
        raise ValidationError("SKILL.md must start with ---")
    m = re.search(r"\n---\s*\n", text[3:])
    if not m:
        raise ValidationError("Frontmatter must close with newline---newline")
    fm_text = text[3:m.start() + 3]
    try:
        fm = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        raise ValidationError(f"Frontmatter YAML error: {exc}")
    if not isinstance(fm, dict):
        raise ValidationError("Frontmatter must be a YAML mapping")
    body = text[m.start() + 3:]
    return fm, body


def parse_skill_md(path: Path) -> tuple:
    """Parse SKILL.md file. Returns (frontmatter_dict, body_text)."""
    text = path.read_text(encoding="utf-8")
    return parse_frontmatter(text)


def parse_abi_yaml(path: Path) -> Dict[str, Any]:
    """Parse skill.abi.yaml. Returns the parsed dict."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValidationError(f"skill.abi.yaml YAML error: {exc}")
    if not isinstance(data, dict):
        raise ValidationError("skill.abi.yaml must be a YAML mapping")
    return data


def load_manifest(skill_dir: Path) -> Manifest:
    """Load a complete Manifest from a skill directory."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise ValidationError("SKILL.md missing")
    fm, body = parse_skill_md(skill_md)
    if not fm.get("name"):
        raise ValidationError("Frontmatter missing 'name'")
    if not str(fm.get("description", "")).strip():
        raise ValidationError("Frontmatter missing or empty 'description'")

    abi_path = skill_dir / "skill.abi.yaml"
    abi = {}
    if abi_path.is_file():
        abi = parse_abi_yaml(abi_path)

    caps = abi.get("capabilities", {}) or {}
    inputs = abi.get("inputs", {}) or {}
    outputs = abi.get("outputs", {}) or {}
    verification = abi.get("verification", {}) or {}

    return Manifest(
        name=fm["name"],
        description=fm["description"],
        spec=str(abi.get("spec", "")),
        version=str(abi.get("version", "")),
        capabilities_required=caps.get("required", []) or [],
        capabilities_optional=caps.get("optional", []) or [],
        inputs_schema=inputs.get("schema"),
        outputs_schema=outputs.get("schema"),
        verification_required=verification.get("required", []) or [],
        raw_frontmatter=fm,
        raw_abi=abi,
    )
