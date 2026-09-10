# Skill ABI (SABI) — reference implementation

Semantic compatibility for portable AI agent skills: what must remain
true when a skill is bound to different models, tools, runtimes, and
capability environments. Core invariant: **Portable != Parseable**.

## Quickstart

```bash
pip install pyyaml cryptography   # only dependencies
python cli/sabi.py validate examples/telegram-live-status
python cli/sabi.py resolve examples/telegram-live-status --runtime examples/telegram-live-status/bindings/minimal.yaml
python cli/sabi.py test examples/telegram-live-status --matrix
python -m pytest tests/ -q
```

## Layout

- `spec/` — normative SABI v0.1 specification (9 documents)
- `src/sabi/` — reference library (parser, validator, resolver, effects,
  diff, lockfile, certify)
- `cli/sabi.py` — command surface (validate, inspect, resolve, diff,
  test, certify, verify-certificate, lock)
- `schemas/` — JSON Schemas (draft 2020-12)
- `conformance/` — positive/negative/adversarial vectors
- `examples/` — migrated example skills (sanitized fixtures only)
- `tests/` — pytest suite, stdlib, no network

## Conformance levels

P0/INVALID, P1/SPEC_VALID, P2/EFFECT_AWARE, P3/DEGRADATION_CONFORMANT,
P4/RUNTIME_TESTED, P4M/MULTI_RUNTIME_TESTED, P5/ATTESTED.
Static validation != runtime test != multi-runtime test != signed
attestation. See `spec/conformance.md`.

## Certificate evidence classes

Certificates carry an explicit `evidence_class`, never an ambiguous
"full" label. The class is the strongest evidence actually present:

| Evidence class | Requires |
|----------------|----------|
| `SPEC_VALID` | parses + spec-valid; static evaluation did not fully pass |
| `STATIC_CONFORMANT` | static invariants pass; no runtime execution |
| `RUNTIME_TESTED` | >=1 runtime run receipt with evidence |
| `MULTI_RUNTIME_TESTED` | >=2 independent runtime run receipts |
| `ATTESTED` | >=2 run receipts plus a signature |

A static-only result can never claim a runtime class, a single runtime can
never claim multi-runtime, and unsigned evidence can never claim
`ATTESTED`. `verify-certificate` checks the certificate schema, skill/ABI/
lock digests against actual bytes, run-receipt references, runtime and
harness identifiers, evidence existence, and the signature bundle when
signed — structural JSON validity alone does not pass.

## Single validation path

`cli/sabi.py validate` calls the canonical semantic validator
`src/sabi/validator.py:validate_skill`. There is exactly one validation
path: Agent Skills frontmatter rules, name/description bounds, name ==
directory, ABI schema conformance, capability resolvability, input/output
schema references, effect and degradation declarations, and lockfile
integrity. `VALID` means the canonical validator returned no findings.


## Status

Experimental v0.1.0-alpha. Example skills carry sanitized fixture data
(`FIXTURE_CHAT_ID`); no live credentials anywhere in this repo.
