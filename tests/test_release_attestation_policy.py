from pathlib import Path

from scripts.check_release_attestation import ATTEST_SHA, check_release_policy

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / ".github" / "workflows" / "release.yml"
README = ROOT / "README.md"


def current():
    return RELEASE.read_text(encoding="utf-8"), README.read_text(encoding="utf-8")


def test_current_release_attestation_policy_passes():
    workflow, readme = current()
    assert check_release_policy(workflow, readme) == []


def test_removing_attestation_fails_closed():
    workflow, readme = current()
    workflow = workflow.replace(f"uses: actions/attest@{ATTEST_SHA}", "uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1")
    errors = check_release_policy(workflow, readme)
    assert any("release provenance action missing" in e for e in errors)


def test_mutable_attestation_tag_is_rejected():
    workflow, readme = current()
    workflow = workflow.replace(f"actions/attest@{ATTEST_SHA}", "actions/attest@v4")
    errors = check_release_policy(workflow, readme)
    assert any("not pinned" in e for e in errors)


def test_attestation_write_permission_is_required():
    workflow, readme = current()
    artifacts_marker = "  artifacts:"
    prefix, artifacts = workflow.split(artifacts_marker, 1)
    artifacts = artifacts.replace("      attestations: write\n", "", 1)
    errors = check_release_policy(prefix + artifacts_marker + artifacts, readme)
    assert any("attestations: write" in e for e in errors)


def test_subject_path_is_exact():
    workflow, readme = current()
    workflow = workflow.replace(
        "subject-path: release-artifacts/source.tar.gz",
        "subject-path: release-artifacts/",
    )
    errors = check_release_policy(workflow, readme)
    assert any("attestation subject" in e for e in errors)
