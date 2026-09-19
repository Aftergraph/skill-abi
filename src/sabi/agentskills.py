"""Agent Skills specification compatibility layer for SABI.

SABI is an *extension* of the Agent Skills specification
(https://agentskills.io/specification), not a fork. This module encodes
the base spec's ``SKILL.md`` requirements so the SABI validator accepts
exactly what a spec-compliant skill declares and rejects what the spec
rejects. Where SABI and the spec disagree, the spec wins.

The checks mirror the official reference validator (``skills-ref``,
https://github.com/agentskills/agentskills) so SABI agrees with the
external oracle on the base format. SABI-specific semantics (the ABI,
effects, degradation, locks) live in the sibling modules and are layered
on top of this baseline.

Extension policy: the spec enumerates the frontmatter fields it defines
(``SPEC_FIELDS``); SABI may add its own extension keys, so unknown keys
are *not* rejected here. The spec-defined fields, however, are validated
strictly.
"""
import unicodedata
from pathlib import Path

# Limits defined by the Agent Skills specification.
MAX_SKILL_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500

# Frontmatter fields defined by the Agent Skills spec. SABI is an
# extension, so additional keys are permitted (SABI extension namespace).
SPEC_FIELDS = frozenset(
    {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
)

# Optional directories named by the spec.
OPTIONAL_DIRS = ("scripts", "references", "assets")


def check_name(name, skill_dir_name=None):
    """Validate the required ``name`` field against the spec.

    Returns a list of finding strings (empty means conformant).
    """
    errors = []
    if not isinstance(name, str) or not name.strip():
        return ["'name' must be a non-empty string"]

    name = unicodedata.normalize("NFKC", name.strip())

    if len(name) > MAX_SKILL_NAME_LENGTH:
        errors.append(
            f"name exceeds {MAX_SKILL_NAME_LENGTH} characters ({len(name)})"
        )
    if name != name.lower():
        errors.append(f"name {name!r} must be lowercase")
    if name.startswith("-") or name.endswith("-"):
        errors.append("name must not start or end with a hyphen")
    if "--" in name:
        errors.append("name must not contain consecutive hyphens")
    if not all(c.isalnum() or c == "-" for c in name):
        errors.append(
            f"name {name!r} may only contain lowercase letters, numbers, and hyphens"
        )

    if skill_dir_name is not None:
        dir_name = unicodedata.normalize("NFKC", skill_dir_name)
        if dir_name != name:
            errors.append(
                f"directory name {skill_dir_name!r} must match skill name {name!r}"
            )
    return errors


def check_description(description):
    """Validate the required ``description`` field against the spec."""
    errors = []
    if not isinstance(description, str) or not description.strip():
        return ["'description' must be a non-empty string"]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        errors.append(
            f"description exceeds {MAX_DESCRIPTION_LENGTH} characters "
            f"({len(description)})"
        )
    return errors


def check_optional_fields(frontmatter):
    """Validate the optional spec fields when present."""
    errors = []

    if "license" in frontmatter:
        lic = frontmatter["license"]
        if not isinstance(lic, str) or not lic.strip():
            errors.append("'license' must be a non-empty string")

    if "compatibility" in frontmatter:
        comp = frontmatter["compatibility"]
        if not isinstance(comp, str):
            errors.append("'compatibility' must be a string")
        elif not comp:
            errors.append("'compatibility' must be 1-500 characters when provided")
        elif len(comp) > MAX_COMPATIBILITY_LENGTH:
            errors.append(
                f"compatibility exceeds {MAX_COMPATIBILITY_LENGTH} characters "
                f"({len(comp)})"
            )

    if "metadata" in frontmatter:
        meta = frontmatter["metadata"]
        if not isinstance(meta, dict):
            errors.append("'metadata' must be a map of string keys to string values")
        else:
            for key, value in meta.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    errors.append(
                        "'metadata' must be a map of string keys to string values"
                    )
                    break

    # allowed-tools is experimental; the spec fixes the format (a
    # space-separated string) but support varies between implementations.
    if "allowed-tools" in frontmatter:
        tools = frontmatter["allowed-tools"]
        if not isinstance(tools, str):
            errors.append(
                "'allowed-tools' must be a space-separated string (experimental)"
            )

    return errors


def check_frontmatter(frontmatter, skill_dir=None):
    """Validate a parsed SKILL.md frontmatter mapping against the spec.

    ``skill_dir``, when given, enables the directory-name equality check.
    Returns a list of finding strings (empty means conformant).
    """
    if not isinstance(frontmatter, dict):
        return ["SKILL.md frontmatter must be a YAML mapping"]

    errors = []
    if "name" not in frontmatter:
        errors.append("missing required field 'name'")
    else:
        dir_name = skill_dir.name if skill_dir is not None else None
        errors.extend(check_name(frontmatter["name"], dir_name))

    if "description" not in frontmatter:
        errors.append("missing required field 'description'")
    else:
        errors.extend(check_description(frontmatter["description"]))

    errors.extend(check_optional_fields(frontmatter))
    return errors


def check_directories(skill_dir):
    """Validate that optional spec directories, when present, are directories."""
    skill_dir = Path(skill_dir)
    errors = []
    for name in OPTIONAL_DIRS:
        p = skill_dir / name
        if p.exists() and not p.is_dir():
            errors.append(f"{name}/ must be a directory")
    return errors
