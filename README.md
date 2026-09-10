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

## Status

Experimental v0.1.0-alpha. Example skills carry sanitized fixture data
(`FIXTURE_CHAT_ID`); no live credentials anywhere in this repo.
