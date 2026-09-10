"""SABI parser: manifest loading, ABI YAML parsing, Agent Skills validation.

Agent Skills name rules:
  - 1..64 characters
  - ^[a-z0-9]+(-[a-z0-9]+)*$  (lowercase alphanumeric + hyphens)
  - No leading or trailing hyphen
  - No consecutive hyphens
  - Must equal directory name (enforced in validator.py)

Agent Skills description rules:
  - 1..1024 characters
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sabi.errors import ValidationError

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class Manifest:
    """Parsed SKILL.md frontmatter."""
    name: str
    description: str
    raw_frontmatter: Dict[str, Any] = field(default_factory=dict)


def parse_frontmatter(text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from SKILL.md text. Returns dict or raises."""
    if not text.startswith("---"):
        raise ValidationError("SKILL.md must start with ---")
    idx = text.find("---", 3)
    if idx < 0:
        raise ValidationError("SKILL.md missing closing ---")
    fm_text = text[3:idx].strip()
    if not fm_text:
        raise ValidationError("SKILL.md frontmatter is empty")
    import yaml
    try:
        fm = yaml.safe_load(fm_text)
    except Exception as exc:
        raise ValidationError(f"SKILL.md frontmatter YAML error: {exc}") from exc
    if not isinstance(fm, dict):
        raise ValidationError("SKILL.md frontmatter must be a YAML mapping")
    return fm


def parse_abi_yaml(path: Path) -> Dict[str, Any]:
    """Load and return the skill.abi.yaml as a dict."""
    import yaml
    try:
        abi = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValidationError(f"skill.abi.yaml YAML error: {exc}") from exc
    if not isinstance(abi, dict):
        raise ValidationError("skill.abi.yaml must be a YAML mapping")
    return abi


def load_manifest(skill_dir: Path) -> Manifest:
    """Load and parse SKILL.md into a Manifest."""
    skill_dir = Path(skill_dir)
    sm = skill_dir / "SKILL.md"
    if not sm.is_file():
        raise ValidationError("SKILL.md missing")
    text = sm.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    name = fm.get("name", "")
    description = fm.get("description", "")
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("SKILL.md frontmatter missing 'name'")
    if not isinstance(description, str) or not description.strip():
        raise ValidationError("SKILL.md frontmatter missing 'description'")
    return Manifest(name=name.strip(), description=description.strip(), raw_frontmatter=fm)


# ── Agent Skills validation -------------------------------------------------


def validate_name(name: str) -> bool:
    """Return True if name violates Agent Skills rules."""
    if not name or len(name) > 64:
        return True
    if not NAME_RE.match(name):
        return True
    return False


def validate_description(description: str) -> List[str]:
    """Return list of description violations."""
    errors = []
    if not description:
        errors.append("description is required")
    elif len(description) > 1024:
        errors.append("description exceeds 1024 characters")
    return errors


def validate_agent_skills_frontmatter(fm: Dict[str, Any]) -> List[str]:
    """Validate frontmatter dict against Agent Skills rules.

    Returns list of violation strings (empty means valid).
    Enforced at P0 by the validator (name/description only).
    """
    errors: List[str] = []
    name = fm.get("name", "")
    if validate_name(name):
        errors.append(
            f"name {name!r} must be 1-64 lowercase alphanumerics with hyphens "
            "(no leading/trailing, no consecutive)"
        )
    errors.extend(validate_description(fm.get("description", "")))
    # Lenient on optional fields — only type-check metadata if present
    metadata = fm.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        errors.append("metadata must be a mapping (dict)")
    return errors
