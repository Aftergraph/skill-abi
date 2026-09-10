# SABI Reference Implementation — Plan

Repo: C:/Users/empir/workspace/skill-abi — build ONLY under src/, cli/, schemas/, tests/. Do not touch spec/ or other repos. Prototype scripts at ~/.agents/skills/telegram-live-status/scripts/ (sabi-validate.py, sabi-sign.py) are read-only reference; port semantics, do not copy blindly.

## Scope
Reference implementation of the Skill ABI (SABI): a machine-verifiable contract for portable agent skills. A skill bundle declares its tools, effects, degradation behavior, and tests. SABI parses/validates manifests in escalating profiles, locks file digests, computes semantic diffs between versions, and issues ed25519-signed certificates — only after dynamic test execution passes, never from static validation alone.

## Layout
- src/sabi/ (package)
  - __init__.py        version + public API
  - errors.py          exception types mapped to exit codes
  - canon.py           canonical JSON serialization + sha256 digests
  - schema.py          minimal JSON Schema draft 2020-12 validator (stdlib; subset: type/required/properties/items/additionalProperties/enum/pattern/minimum/$ref-local/anyOf)
  - parser.py          skill.yaml + SKILL.md YAML frontmatter -> Manifest dataclasses
  - validator.py       profiles: P0 schema, P1 structural refs (files/tools declared), P2 effects complete+policy, P3 degradation+portability+tests; `validate --lock` gates on lockfile digest match
  - resolver.py        resolve tool refs against host capability map (aliases); `bind` emits binding plan
  - effects.py         effect checker: declared effect classes vs policy, undeclared/forbidden classes, path/host scoping
  - degradation.py     degradation coverage: every optional tool needs declared behavior; no silent-fail of required deps
  - diff.py            semantic diff of two manifests; classify breaking vs non-breaking
  - lock.py            lockfile create/verify: sha256 per bundle file + manifest digest
  - tests_runner.py    run declared test matrix (subprocess), emit results JSON with evidence digests
  - certify.py         certificate generation + verification (ed25519 via cryptography)
  - attest.py          signed attestation of test-run results + verification
- cli/sabi.py          argparse entry: validate inspect resolve bind diff test certify verify-certificate lock verify-lock attest verify-attestation; --json where useful
- schemas/             skill.manifest.schema.json, lock.schema.json, certificate.schema.json, attestation.schema.json (draft 2020-12)
- tests/               pytest, stdlib-only fixtures, no network; conftest.py adds src/ to sys.path

## Exit codes
0 ok · 1 semantic validation/check failure · 2 usage error · 3 integrity failure (digest mismatch / tamper) · 4 invalid signature or certificate · 5 certification precondition unmet · 6 required dependency unresolvable

## Certification rule (hard)
`certify` requires ALL of: validate P3 pass against the current lock, `verify-lock` pass, and a recorded `sabi test` run with every matrix entry passed. Static `validate` output is always labeled "static" and can never produce a certificate.

## Pytest coverage targets
test_parser, test_schema_validator, test_validator_profiles, test_resolver_bind, test_effects, test_degradation, test_semantic_diff, test_lock_digests, test_tamper_refusal (file mutation, digest mutation, signature mutation), test_certificate (generate AND verify), test_attestation, test_cli_end_to_end.

## Constraints
- Deps: Python stdlib + pyyaml + cryptography only.
- All files LF line endings.
- Tests run offline; no network access.
- Port from prototype: P0–P3+lock validation, resolve, diff, test matrix, attest (sabi-validate.py); ed25519 keygen/sign/verify (sabi-sign.py).
