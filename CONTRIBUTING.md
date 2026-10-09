# Contributing — skill-abi

- Python 3.11+, dependencies: pyyaml, pytest.
- `python -m pytest tests/ -q` must pass before any PR.
- LF-only line endings (verified by byte read, not grep).
- No live identifiers, credentials, or user paths anywhere in the
  tree (fixtures use `FIXTURE_*`; see SECURITY.md).
- Spec changes need conformance evidence, not just prose.
- One capability per lesson: keep modules small and tested.
