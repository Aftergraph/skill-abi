"""Skills Vault seam test — offline, self-contained, skips without sibling repo.

Tests that:
1. vault.discover_candidates finds the SABI skill
2. vault.ingest_skill_source stores it byte-intact
3. Vault treats SABI as opaque (no SABI fields in vault records)
4. Vault's own integrity layer covers distribution
5. SABI truth remains in skill-abi (requirement object + lockfile)
"""
import json
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
VAULT_SCRIPT = REPO.parent / "skills-vault" / "scripts" / "vault.py"
EXAMPLE = REPO / "examples" / "telegram-live-status"

pytestmark = pytest.mark.skipif(
    not VAULT_SCRIPT.is_file(),
    reason="skills-vault sibling repo not checked out",
)


@pytest.fixture
def vault():
    """Import vault module from sibling repo.

    Skips gracefully if vault.py uses Python 3.12+ syntax unavailable in
    the current runtime (e.g. KW_ONLY dataclass fields).
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("vault", VAULT_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except (AttributeError, TypeError, SyntaxError) as exc:
        pytest.skip(f"vault.py import failed (Python version mismatch?): {exc}")
    return mod


@pytest.fixture
def tmp_vault_root(tmp_path):
    """Bootstrap a TEMP vault root — never touches real skills-vault."""
    root = Path(tmp_path) / "vault-root"
    root.mkdir()
    (root / "registry").mkdir()
    (root / "registry" / "policy.json").write_text(
        json.dumps({"lifecycles": {"experimental": {}}, "default_lifecycle": "experimental"}),
        encoding="utf-8",
    )
    (root / "registry" / "overrides.json").write_text("{}", encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps({"name": "skills-vault", "sources": {}, "total_skills": 0}),
        encoding="utf-8",
    )
    return root


@pytest.fixture
def src_skill(tmp_path):
    """Copy the telegram-live-status example to a temp location."""
    dst = Path(tmp_path) / "telegram-live-status"
    shutil.copytree(EXAMPLE, dst)
    return dst


class TestSkillsVaultSeam:
    def test_discover_candidates(self, vault, src_skill):
        candidates = vault.discover_candidates(src_skill)
        assert len(candidates) == 1
        name, lifecycle, trust = candidates[0]
        assert name == "telegram-live-status"
        assert lifecycle == "experimental"
        assert trust == "untrusted"

    def test_ingest_byte_intact(self, vault, tmp_vault_root, src_skill):
        ingested, errors = vault.ingest_skill_source(
            tmp_vault_root, src_skill, "sabi-seam-2026-09-10"
        )
        assert ingested == 1
        assert errors == []

        # Verify every source file sha256 matches stored
        stored = tmp_vault_root / "skills" / "imported" / "telegram-live-status"
        assert stored.is_dir()
        for f in src_skill.rglob("*"):
            if f.is_file():
                rel = f.relative_to(src_skill)
                stored_f = stored / rel
                assert stored_f.is_file(), f"missing stored file: {rel}"
                assert f.read_bytes() == stored_f.read_bytes(), f"byte mismatch: {rel}"

    def test_vault_treats_sabi_as_opaque(self, vault, tmp_vault_root, src_skill):
        vault.ingest_skill_source(tmp_vault_root, src_skill, "sabi-seam-2026-09-10")
        records = vault.build_records(tmp_vault_root)
        # Find the imported skill record
        record = None
        for r in records:
            if r.get("name") == "telegram-live-status":
                record = r
                break
        assert record is not None, "skill not found in vault records"

        record_str = json.dumps(record).lower()
        sabi_fields = [
            "required_capabilities", "optional_capabilities",
            "effect_envelope", "degradation_tiers",
            "verification_obligations", "sabi/",
        ]
        for field in sabi_fields:
            assert field not in record_str, f"vault record contains SABI field: {field}"

        assert record.get("lifecycle") == "experimental"
        assert record.get("trust") == "untrusted"

    def test_vault_integrity_layer(self, vault, tmp_vault_root, src_skill):
        vault.ingest_skill_source(tmp_vault_root, src_skill, "sabi-seam-2026-09-10")
        records = vault.build_records(tmp_vault_root)
        lock = vault.build_lock(tmp_vault_root, records)
        findings = vault.verify_lock(tmp_vault_root, lock)
        assert not findings, f"vault lock verification found issues: {findings}"

    def test_sabi_truth_remains_in_skill_abi(self, tmp_path):
        """SABI truth (requirement object + lock) works from stored copy."""
        from sabi.api import requirement_object_bytes, export_requirement_object
        from sabi.lockfile import check_lock

        # Copy example to temp
        stored = Path(tmp_path) / "telegram-live-status"
        shutil.copytree(EXAMPLE, stored)

        # Requirement object
        obj = export_requirement_object(stored)
        assert obj["skill"] == "telegram-live-status"
        assert "sabi" in obj["schema"]
        assert requirement_object_bytes(stored) == requirement_object_bytes(stored)

        # Lockfile
        valid, issues = check_lock(stored)
        assert valid, f"lockfile check failed: {issues}"
