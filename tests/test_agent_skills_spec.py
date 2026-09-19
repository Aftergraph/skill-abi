"""Agent Skills specification compatibility tests for SABI.

SABI is an extension of the Agent Skills spec
(https://agentskills.io/specification). These tests assert that the SABI
validator accepts/rejects SKILL.md frontmatter exactly as the base spec
requires, and that the bundled example stays spec-conformant.

Oracle: the published spec at https://agentskills.io/specification
(accessed 2026-09-10) and the reference validator ``skills-ref`` 0.1.1.
See ``spec/agent-skills-compat.md``.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sabi.validator import validate_skill

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "telegram-live-status"

VALID_DESC = "Do a thing well. Use when a thing must be done."
BODY = "\n# Body\n\nInstructions for the agent.\n"


def build(tmp_path, dirname, frontmatter, body=BODY):
    """Create a skill directory containing a SKILL.md with *frontmatter*."""
    d = tmp_path / dirname
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        "---\n" + frontmatter + "\n---\n" + body, encoding="utf-8"
    )
    return d


def check(tmp_path, dirname, frontmatter, body=BODY):
    d = build(tmp_path, dirname, frontmatter, body)
    return validate_skill(d)


def findings(errors):
    return [e for e in errors if "Agent Skills" in e]


def fm(name="demo-skill", desc=VALID_DESC, extra=""):
    text = f"name: {name}\ndescription: {desc}\n"
    if extra:
        text += extra if extra.endswith("\n") else extra + "\n"
    return text


# ── SKILL.md presence and YAML frontmatter ──────────────────────────


def test_accepts_valid_minimal_skill(tmp_path):
    level, errors = check(tmp_path, "demo-skill", fm())
    assert findings(errors) == [], errors
    assert level == "P0", errors


def test_rejects_missing_skill_md(tmp_path):
    d = tmp_path / "demo-skill"
    d.mkdir()
    level, errors = validate_skill(d)
    assert level == "INVALID"
    assert any("SKILL.md missing" in e for e in errors)


def test_rejects_missing_frontmatter(tmp_path):
    d = tmp_path / "demo-skill"
    d.mkdir()
    (d / "SKILL.md").write_text("no frontmatter here\n", encoding="utf-8")
    level, errors = validate_skill(d)
    assert level == "INVALID"
    assert errors


def test_rejects_unclosed_frontmatter(tmp_path):
    d = tmp_path / "demo-skill"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: demo-skill\n", encoding="utf-8")
    level, errors = validate_skill(d)
    assert level == "INVALID"


# ── name field ──────────────────────────────────────────────────────


def test_name_max_64_accepted(tmp_path):
    name = "a" * 64
    level, errors = check(tmp_path, name, fm(name=name))
    assert findings(errors) == [], errors


def test_name_over_64_rejected(tmp_path):
    name = "a" * 65
    _, errors = check(tmp_path, name, fm(name=name))
    assert any("exceeds 64" in e for e in findings(errors)), errors


def test_name_must_be_lowercase(tmp_path):
    _, errors = check(tmp_path, "PDF-Processing", fm(name="PDF-Processing"))
    assert any("must be lowercase" in e for e in findings(errors)), errors


def test_name_no_leading_hyphen(tmp_path):
    _, errors = check(tmp_path, "-pdf", fm(name="-pdf"))
    assert any("start or end with a hyphen" in e for e in findings(errors)), errors


def test_name_no_trailing_hyphen(tmp_path):
    _, errors = check(tmp_path, "pdf-", fm(name="pdf-"))
    assert any("start or end with a hyphen" in e for e in findings(errors)), errors


def test_name_no_consecutive_hyphens(tmp_path):
    _, errors = check(tmp_path, "pdf--processing", fm(name="pdf--processing"))
    assert any("consecutive hyphens" in e for e in findings(errors)), errors


def test_name_charset_letters_numbers_hyphens(tmp_path):
    _, errors = check(tmp_path, "pdf_processing", fm(name="pdf_processing"))
    assert any("letters, numbers, and hyphens" in e for e in findings(errors)), errors


def test_name_must_match_directory(tmp_path):
    _, errors = check(tmp_path, "wrong-name", fm(name="pdf-processing"))
    assert any("must match skill name" in e for e in findings(errors)), errors


def test_valid_hyphenated_name_accepted(tmp_path):
    level, errors = check(tmp_path, "pdf-processing", fm(name="pdf-processing"))
    assert findings(errors) == [], errors


# ── description field ───────────────────────────────────────────────


def test_description_max_1024_accepted(tmp_path):
    desc = "x" * 1024
    level, errors = check(tmp_path, "demo-skill", fm(desc=desc))
    assert findings(errors) == [], errors


def test_description_over_1024_rejected(tmp_path):
    desc = "x" * 1025
    _, errors = check(tmp_path, "demo-skill", fm(desc=desc))
    assert any("exceeds 1024" in e for e in findings(errors)), errors


def test_description_empty_rejected(tmp_path):
    level, errors = check(tmp_path, "demo-skill", 'name: demo-skill\ndescription: ""\n')
    assert level == "INVALID"
    assert any("description" in e for e in errors)


def test_description_missing_rejected(tmp_path):
    level, errors = check(tmp_path, "demo-skill", "name: demo-skill\n")
    assert level == "INVALID"
    assert any("description" in e for e in errors)


# ── optional fields ─────────────────────────────────────────────────


def test_optional_license_accepted(tmp_path):
    level, errors = check(
        tmp_path, "demo-skill", fm(extra="license: Apache-2.0")
    )
    assert findings(errors) == [], errors


def test_optional_license_wrong_type_rejected(tmp_path):
    _, errors = check(tmp_path, "demo-skill", fm(extra="license: 42"))
    assert any("license" in e for e in findings(errors)), errors


def test_optional_compatibility_accepted(tmp_path):
    level, errors = check(
        tmp_path, "demo-skill", fm(extra="compatibility: Requires python3")
    )
    assert findings(errors) == [], errors


def test_optional_compatibility_max_500(tmp_path):
    comp = "y" * 500
    _, errors = check(tmp_path, "demo-skill", fm(extra=f'compatibility: "{comp}"'))
    assert findings(errors) == [], errors


def test_optional_compatibility_over_500_rejected(tmp_path):
    comp = "y" * 501
    _, errors = check(tmp_path, "demo-skill", fm(extra=f'compatibility: "{comp}"'))
    assert any("exceeds 500" in e for e in findings(errors)), errors


def test_optional_compatibility_empty_rejected(tmp_path):
    _, errors = check(tmp_path, "demo-skill", fm(extra='compatibility: ""'))
    assert any("1-500 characters" in e for e in findings(errors)), errors


def test_optional_compatibility_wrong_type_rejected(tmp_path):
    _, errors = check(tmp_path, "demo-skill", fm(extra="compatibility: [a, b]"))
    assert any("compatibility" in e for e in findings(errors)), errors


def test_metadata_string_map_accepted(tmp_path):
    extra = 'metadata:\n  author: example-org\n  version: "1.0"'
    level, errors = check(tmp_path, "demo-skill", fm(extra=extra))
    assert findings(errors) == [], errors


def test_metadata_non_mapping_rejected(tmp_path):
    _, errors = check(tmp_path, "demo-skill", fm(extra="metadata: [a, b]"))
    assert any("metadata" in e for e in findings(errors)), errors


def test_metadata_non_string_value_rejected(tmp_path):
    extra = "metadata:\n  version: 1.0"
    _, errors = check(tmp_path, "demo-skill", fm(extra=extra))
    assert any("metadata" in e for e in findings(errors)), errors


def test_allowed_tools_string_accepted(tmp_path):
    extra = 'allowed-tools: "Bash(git:*) Read"'
    level, errors = check(tmp_path, "demo-skill", fm(extra=extra))
    assert findings(errors) == [], errors


def test_allowed_tools_wrong_type_rejected(tmp_path):
    extra = "allowed-tools:\n  - Bash\n  - Read"
    _, errors = check(tmp_path, "demo-skill", fm(extra=extra))
    assert any("allowed-tools" in e for e in findings(errors)), errors


# ── optional directories ────────────────────────────────────────────


def test_optional_dirs_accepted(tmp_path):
    d = build(tmp_path, "demo-skill", fm())
    for name in ("scripts", "references", "assets"):
        (d / name).mkdir()
    level, errors = validate_skill(d)
    assert findings(errors) == [], errors


def test_optional_dir_as_file_rejected(tmp_path):
    d = build(tmp_path, "demo-skill", fm())
    (d / "scripts").write_text("not a directory\n", encoding="utf-8")
    _, errors = validate_skill(d)
    assert any("scripts/ must be a directory" in e for e in findings(errors)), errors


# ── the bundled example stays spec-conformant ───────────────────────


def test_example_fixture_is_spec_conformant():
    level, errors = validate_skill(EXAMPLE)
    assert findings(errors) == [], errors
    assert level == "P3", errors
