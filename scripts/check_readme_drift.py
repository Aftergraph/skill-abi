#!/usr/bin/env python3
"""Check README.md status section against canonical sources.

Verifies mechanically derivable values in the Status table. Exits 1 on
drift. Designed for CI (untrusted job, stdlib only, no secrets).

Checks:
1. __version__ from src/sabi/__init__.py appears in README as `0.1.0`
2. Latest non-Unreleased CHANGELOG heading appears in README
3. README contains "unsigned" and "P3"
4. No forbidden overclaims present
5. CONDITIONAL: when sibling ../skillport exists, verify PINNING.md
   references match
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
README = REPO / "README.md"
SRC_INIT = REPO / "src" / "sabi" / "__init__.py"
CHANGELOG = REPO / "CHANGELOG.md"
SKILLPORT_PINNING = REPO.parent / "skillport" / "results" / "runset-2026-09-10-conf1" / "PINNING.md"

FORBIDDEN_OVERCLAIMS = [
    "p4 conformance proven",
    "p4m certified",
    "p5 attested",
    "statistically significant",
    "production ready",
    "portability across all runtimes",
]


def main():
    errors = []

    # 1. Version check
    if not SRC_INIT.is_file():
        errors.append(f"source not found: {SRC_INIT}")
    else:
        version_match = re.search(r'__version__\s*=\s*"([^"]+)"', SRC_INIT.read_text(encoding="utf-8"))
        if not version_match:
            errors.append("__version__ not found in src/sabi/__init__.py")
        else:
            version = version_match.group(1)
            if f"`{version}`" not in README.read_text(encoding="utf-8"):
                errors.append(f"README missing version backtick reference: `{version}`")

    # 2. CHANGELOG latest release check
    if not CHANGELOG.is_file():
        errors.append(f"CHANGELOG not found: {CHANGELOG}")
    else:
        changelog_text = CHANGELOG.read_text(encoding="utf-8")
        # Find the first ## heading that isn't "Unreleased"
        for line in changelog_text.splitlines():
            m = re.match(r"^## (v\d+\.\d+\.\d+[-a-zA-Z0-9.]+)", line)
            if m:
                latest_tag = m.group(1)
                if latest_tag not in README.read_text(encoding="utf-8"):
                    errors.append(f"README missing latest release reference: {latest_tag}")
                break
        else:
            errors.append("no release heading found in CHANGELOG.md")

    # 3. Required keywords
    readme_text = README.read_text(encoding="utf-8") if README.is_file() else ""
    if "unsigned" not in readme_text.lower():
        errors.append("README must mention 'unsigned' (certificate status)")
    if "P3" not in readme_text:
        errors.append("README must mention 'P3' (conformance level)")

    # 4. Forbidden overclaims
    for phrase in FORBIDDEN_OVERCLAIMS:
        if phrase in readme_text.lower():
            errors.append(f"forbidden overclaim found in README: '{phrase}'")

    # 5. Conditional skillport cross-check
    if SKILLPORT_PINNING.is_file():
        pinning_text = SKILLPORT_PINNING.read_text(encoding="utf-8")
        # Check that skill-abi SHA is mentioned
        sha_match = re.search(r"skill-abi:\s*([0-9a-f]{40})", pinning_text)
        if sha_match:
            short_sha = sha_match.group(1)[:8]
            if short_sha not in readme_text:
                errors.append(f"README runset SHA ({short_sha}) doesn't match PINNING.md")
        else:
            errors.append("skill-abi SHA not found in PINNING.md")
        # Check runset name
        if "runset-2026-09-10-conf1" not in readme_text:
            errors.append("README missing runset name 'runset-2026-09-10-conf1'")

    if errors:
        print("README DRIFT DETECTED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    print("README drift check: OK")
    return 0


if __name__ == "__main__":
    main()
