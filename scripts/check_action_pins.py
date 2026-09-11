#!/usr/bin/env python3
"""Fail CI if any third-party GitHub Action is not pinned to a commit SHA.

Supply-chain control: `uses: action@v4` style tags are mutable and can be
repointed after review. Every third-party action reference must be pinned
to a full 40-hex commit SHA. Local (repo-relative) actions (`uses: ./...`)
are exempt; first-party actions under this org are NOT exempt by default
(they are mutable repos too) - extend THIRD_PARTY_EXCEPTIONS explicitly if
a first-party action ever needs an exemption.

Exit 0 = all pinned, 1 = violation (CI fails closed).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

USES_RE = re.compile(r"uses:\s*(\S+)@(\S+)")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# Action references that are exempt from SHA pinning. Local actions start
# with "./" and never appear here.
THIRD_PARTY_EXCEPTIONS = set()

# Known first-party org prefixes, treated as third-party (mutable) unless
# listed above. Adjust if the org adopts immutable action tags.
FIRST_PARTY_ORGS = set()


def main() -> int:
    violations = []
    files = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    if not files:
        print(f"::notice::no workflow files found in {WORKFLOWS}")
        return 0

    for wf in files:
        text = wf.read_text()
        for m in USES_RE.finditer(text):
            action, ref = m.group(1), m.group(2)
            # Local (repo-relative) actions are always exempt.
            if action.startswith("./"):
                continue
            # Explicitly listed third-party exceptions.
            if f"{action}@{ref}" in THIRD_PARTY_EXCEPTIONS:
                continue
            if not SHA_RE.match(ref):
                violations.append(f"{wf.name}: uses {action}@{ref} — NOT SHA-pinned")

    for v in violations:
        print(f"::error::{v}")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
