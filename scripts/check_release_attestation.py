#!/usr/bin/env python3
"""Fail closed if the release provenance workflow loses its required controls."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / ".github" / "workflows" / "release.yml"
README = ROOT / "README.md"

ATTEST_ACTION = "actions/attest"
ATTEST_SHA = "1e69f48acb82d1966a394da916b4c1698aa569d6"
SUBJECT_PATH = "release-artifacts/source.tar.gz"
VERIFY_COMMAND = "gh attestation verify source.tar.gz --repo Aftergraph/skill-abi"


def _job_block(text: str, job: str) -> str:
    match = re.search(rf"(?ms)^  {re.escape(job)}:\n(?P<body>.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", text)
    return match.group("body") if match else ""


def check_release_policy(workflow: str, readme: str) -> list[str]:
    errors: list[str] = []
    artifacts = _job_block(workflow, "artifacts")
    verify = _job_block(workflow, "verify")

    if not artifacts:
        errors.append("release workflow missing artifacts job")
        return errors

    required_permissions = ("contents: read", "id-token: write", "attestations: write")
    for permission in required_permissions:
        if permission not in artifacts:
            errors.append(f"artifacts job missing permission: {permission}")

    for forbidden in ("id-token: write", "attestations: write"):
        if forbidden in verify:
            errors.append(f"verify job must not have release write permission: {forbidden}")

    expected_use = f"uses: {ATTEST_ACTION}@{ATTEST_SHA}"
    if expected_use not in artifacts:
        errors.append(f"release provenance action missing or not pinned to {ATTEST_SHA}")

    if f"subject-path: {SUBJECT_PATH}" not in artifacts:
        errors.append(f"attestation subject must be {SUBJECT_PATH}")

    build_at = artifacts.find("git archive --format=tar.gz")
    attest_at = artifacts.find(expected_use)
    upload_at = artifacts.find("uses: actions/upload-artifact@")
    if min(build_at, attest_at, upload_at) < 0 or not build_at < attest_at < upload_at:
        errors.append("release ordering must be build archive -> attest archive -> upload artifacts")

    if "sha256sum release-artifacts/source.tar.gz" not in artifacts:
        errors.append("release must preserve SHA-256 sidecar")
    if VERIFY_COMMAND not in readme:
        errors.append("README missing consumer attestation verification command")
    if "not, by itself" not in readme or "SLSA level" not in readme:
        errors.append("README missing bounded SLSA claim language")

    return errors


def main() -> int:
    errors = check_release_policy(
        RELEASE.read_text(encoding="utf-8"),
        README.read_text(encoding="utf-8"),
    )
    for error in errors:
        print(f"::error::{error}")
    if not errors:
        print("release attestation policy: PASS")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
