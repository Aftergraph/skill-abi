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



## Release provenance

Tagged/manual release builds create `release-artifacts/source.tar.gz`, retain its
SHA-256 sidecar as a convenience integrity check, and generate GitHub-native
signed build provenance for the archive with `actions/attest`.

After obtaining `source.tar.gz`, verify the attestation against this repository:

```bash
gh attestation verify source.tar.gz --repo Aftergraph/skill-abi
```

The `.sha256` sidecar is **not** provenance. A GitHub artifact attestation is
also not, by itself, an Aftergraph claim of any SLSA level; any such claim
requires an explicit mapping to the applicable SLSA specification and observed
release evidence.

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