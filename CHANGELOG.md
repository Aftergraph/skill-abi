# Changelog — skill-abi

## v0.1.0-alpha.2 (2026-09-10)
- H-003 closed: skill-md + abi schemas live, validator branches active, schema tests

## v0.1.0-alpha.1 (2026-09-10)
- Frozen initial schemas (skill-abi, effects, degradation, certificate)
- Reference CLI: validate, inspect, resolve, diff, test, certify,
  verify-certificate, lock
- Conformance runner with 9-document normative spec
- First example: telegram-live-status (sanitized fixtures)
- Demo-grade ed25519 signing sidecar mechanics documented

## Unreleased
- Cross-repo requirement-object export: src/sabi/api.py, `sabi export` CLI, spec/cross-repo-contract.md
- Skills Vault seam test (tests/test_skills_vault_seam.py, skips without sibling checkout)
