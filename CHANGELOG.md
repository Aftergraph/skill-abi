# Changelog — skill-abi

## Unreleased
- Schema consolidation: `schemas/abi.schema.json` is the single canonical
  ABI-descriptor schema; the unreferenced duplicate
  `schemas/skill-abi.schema.json` is removed (its `conformance.level`
  enum folded into the canonical schema).
- All schema `$id`s normalized to one namespace,
  `https://aftergraph.org/sabi/` (legacy `sabi.dev/schemas` retired).
  Decision documented in `spec/schema-family.md` and in the schema.

## v0.1.0-alpha.1 (2026-09-10)
- Frozen initial schemas (skill-abi, effects, degradation, certificate)
- Reference CLI: validate, inspect, resolve, diff, test, certify,
  verify-certificate, lock
- Conformance runner with 9-document normative spec
- First example: telegram-live-status (sanitized fixtures)
- Demo-grade ed25519 signing sidecar mechanics documented
