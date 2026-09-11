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
- `schemas/` — JSON Schemas (draft 2020-12), one canonical family under
  the `https://aftergraph.org/sabi/` `$id` namespace (see
  `spec/schema-family.md`)
- `conformance/` — positive/negative/adversarial vectors
- `examples/` — migrated example skills (sanitized fixtures only)
- `tests/` — pytest suite, stdlib, no network

## Conformance levels

P0/INVALID, P1/SPEC_VALID, P2/EFFECT_AWARE, P3/DEGRADATION_CONFORMANT,
P4/RUNTIME_TESTED, P4M/MULTI_RUNTIME_TESTED, P5/ATTESTED.
Static validation != runtime test != multi-runtime test != signed
attestation. See `spec/conformance.md`.

## Status

> Mechanically checkable: `python scripts/check_readme_drift.py` verifies every
> value below against canonical sources. CI fails on drift.

| Dimension | Value | Source of truth |
|---|---|---|
| Implementation maturity | P3 static conformance proven (example). P4/P4M/P5 unclaimed. Certificates are UNSIGNED static evidence only. | `spec/conformance.md`, `src/sabi/certify.py` (`"signed": False`) |
| Latest release | `v0.1.0-alpha.2` (commit `9bd3b61eab35d2c3088035b5439abfc923ffc751`) | git tags / GitHub releases |
| Implementation version | `0.1.0` | `src/sabi/__init__.py` |
| Latest frozen evidence runset | `runset-2026-09-10-conf1` pinning this repo at `9bd3b61e` (pilot-level power) | skillport `results/runset-2026-09-10-conf1/PINNING.md` |
| Research evidence maturity | Exploratory pilots + confirmatory conf1 at pilot-level power (3 runs/cell < 10 minimum); no 95% significance anywhere (C-010 REFUTED) | skillport `analysis/claim-ledger.md` |
| Unsupported claims | Signing (C-007) NOT_TESTED; portability beyond Omega-tested (C-008) NOT_TESTED; P4M unclaimed; one receiver (Telegram FIXTURE only); Codex NOT_TESTED / Muse blocked; single host | skillport `analysis/claims.json` |

Example skills carry sanitized fixture data (`FIXTURE_CHAT_ID`); no live
credentials anywhere in this repo.
