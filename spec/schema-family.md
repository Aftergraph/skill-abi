# SABI schema family — canonicalization decision

**Status:** Normative (v0.1.0-alpha.1)
**Date:** 2026-09-10

## Decision

There is exactly **one** canonical normative schema family, identified by the
single `$id` namespace:

```
https://aftergraph.org/sabi/
```

The legacy `https://sabi.dev/schemas/` namespace is **retired**. Every schema in
`schemas/` MUST carry an `$id` rooted at `https://aftergraph.org/sabi/`.

## The duplicate

`schemas/abi.schema.json` and `schemas/skill-abi.schema.json` both described a
`skill.abi.yaml` ABI descriptor. They disagreed in four ways:

| Aspect | `abi.schema.json` (kept) | `skill-abi.schema.json` (removed) |
|---|---|---|
| `$id` namespace | `aftergraph.org/sabi/` | `sabi.dev/schemas/` |
| `required` | `spec`, `skill`, `capabilities` | `spec`, `skill`, `version`, `inputs`, `outputs`, `capabilities` |
| `capabilities.required` sub-key | required | not required |
| `spec` pattern | `^sabi/v` | `^sabi/` |
| `conformance.level` enum | absent | `P0`–`P5` |

Only `abi.schema.json` was ever wired into the implementation:
`src/sabi/validator.py` (P1 branch) and `tests/test_schemas.py` /
`tests/test_validator_schemas.py` load it by filename. `skill-abi.schema.json`
was referenced by **nothing** (no code, test, spec, CI, or example). It was a
dead duplicate introduced in the initial SABI commit and never adopted.

## Resolution

1. `schemas/abi.schema.json` is the canonical ABI-descriptor schema.
2. `schemas/skill-abi.schema.json` is **deleted** as the obsolete duplicate.
3. Its unique normative constraint — the `conformance.level` enum `P0`–`P5` —
   is folded into the canonical schema so no constraint is lost. The fold is
   additive (`conformance` is an optional property), so existing valid
   descriptors remain valid.
4. All remaining schema `$id` values are normalized to `aftergraph.org/sabi/`.

Deterministic equivalence is therefore preserved for every document that the
implementation actually validates: the canonical schema accepts the same
`skill.abi.yaml` documents as before, plus an optional `conformance` block.

## Enforcement

`tests/test_schemas.py` pins the invariant: every schema file shares the
`aftergraph.org/sabi/` namespace prefix, the canonical `abi.schema.json` exists,
and the retired `skill-abi.schema.json` does not.
