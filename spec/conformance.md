# SABI v0.1 — Conformance Levels

**Version:** 0.1.0
**Status:** Draft
**Date:** 2026-09-10

This document defines the normative conformance levels P0 through P5 for
SABI skills. Each level specifies exact requirements a skill MUST satisfy
to claim that level.

Prerequisites: `SABI-v0.1.md` (scope, invariant), `terminology.md` (terms).

## 1. Level Definitions

### 1.1 P0 / INVALID

A skill is P0/INVALID when it fails any of the following:

- Contract artifacts do not parse as valid YAML or JSON.
- Required fields in the skill tuple S = <I, O, C, E, D, V> are missing.
- Capability identifiers violate the syntax rules in `capability-model.md`.
- Effect declarations lack quantified bounds (vague declarations).
- Degradation model lacks exactly one terminal tier.
- Any MUST clause from `SABI-v0.1.md` or its sub-documents is violated.

P0 is the default state. A skill remains P0 until evidence elevates it.

### 1.2 P1 / SPEC_VALID

A skill is P1/SPEC_VALID when it satisfies all P0 structural checks and:

- All input (I) and output (O) schemas reference valid schema documents.
- All capability identifiers belong to one of the nine families defined in
  `capability-model.md` and use canonical form (aliases resolved).
- The degradation model's tiers form a valid partial order under the
  subset relation.
- Cross-references are consistent: capabilities in D exist in C; effects
  referenced in D exist in E.

P1 is achieved through static analysis alone. It proves parseability and
structural validity, NOT portability.

### 1.3 P2 / EFFECT_AWARE

A skill is P2/EFFECT_AWARE when it satisfies P1 and:

- Every effect category declared in E has quantified bounds across all five
  dimensions (reversibility, scope, external visibility, quantity bounds,
  credential exposure) as defined in `effect-model.md`.
- No effect declaration uses vague terms such as "may write files" without
  numeric limits or scoped patterns.
- Declared authority does not contradict capability declarations (every
  effect category with non-zero bounds has a corresponding capability in C).

P2 is achieved through static analysis of effect declarations. It does NOT
prove that effects are respected at runtime.

### 1.4 P3 / DEGRADATION_CONFORMANT

A skill is P3/DEGRADATION_CONFORMANT when it satisfies P2 and:

- The degradation model contains at least one non-terminal tier and exactly
  one terminal tier.
- Tier selection follows the deterministic max-tier rule: T* = max{Ti |
  requires(Ti) ⊆ R_caps}.
- Incomparable tiers have an explicit priority tiebreaker.
- Effect loss mapping is documented and monotonic across the tier lattice.
- The terminal tier performs no effects declared in E.

P3 is achieved through static analysis of the degradation model. It does NOT
prove that degradation behaves correctly at runtime.

### 1.5 P4 / RUNTIME_TESTED

A skill is P4/RUNTIME_TESTED when it satisfies P3 and:

- The skill has been executed on at least one named runtime with a concrete
  binding file.
- Execution evidence demonstrates that observed effects did not exceed
  declared bounds in E.
- Degradation tier selection matched the deterministic rule when tested
  with reduced capability sets.
- Evidence includes execution traces, observed-vs-declared comparison
  reports, and identification of the runtime, binding, and harness used.

P4 requires real runtime execution. Static analysis alone cannot achieve P4.

### 1.6 P4M / MULTI_RUNTIME_TESTED

A skill is P4M/MULTI_RUNTIME_TESTED when it satisfies P4 and:

- P4-level evidence exists for at least two independent runtimes.
- The runtimes use distinct binding implementations (not merely different
  configuration values for the same binding).
- Cross-runtime comparison demonstrates output equivalence or documents
  acceptable divergence per the degradation model.
- Deterministic degradation produces identical tier selections for identical
  capability subsets across all tested runtimes.

P4M proves portability. Single-runtime evidence (P4) is insufficient.

### 1.7 P5 / ATTESTED

A skill is P5/ATTESTED when it satisfies P4M and:

- The complete P4M evidence bundle is cryptographically signed by a
  recognized attestor.
- The signature covers all evidence artifacts including execution traces,
  comparison reports, and binding file hashes.
- The attestor's identity and public key are referenced in the attestation
  record.
- The attestation includes a timestamp.

P5 adds provenance and non-repudiation to P4M evidence. Unsigned P4M
evidence remains P4M regardless of thoroughness.

## 2. Separation Principle

The conformance levels enforce a strict separation between evidence types:

| Boundary | Rule |
|----------|------|
| Static ≠ Runtime | P1–P3 are static. P4+ requires execution. Never label static results as runtime-tested. |
| Runtime ≠ Multi-Runtime | P4 tests one runtime. P4M tests ≥2. Never label single-runtime results as multi-runtime. |
| Multi-Runtime ≠ Signed | P4M is unsigned. P5 requires cryptographic signature. Never label unsigned evidence as attested. |

These boundaries are absolute. Tooling, documentation, and human reviewers
MUST NOT conflate them.

## 3. Level Migration Rule for Historical Artifacts

Skills verified under earlier versions of this specification MAY carry
conformance claims that do not map directly to current levels. The following
migration rules apply:

1. **Upward migration is not automatic.** A skill claiming P4 under a prior
   spec version MUST be re-evaluated against current P4 requirements before
   claiming P4 under this version. Prior evidence MAY be reused if it
   satisfies current criteria, but the claim itself must be re-issued.

2. **Downward migration on spec change.** If a spec version introduces new
   MUST clauses at a given level, previously conformant skills are
   provisionally downgraded to the highest level whose requirements they
   still satisfy. They remain at the lower level until re-verified.

3. **Evidence preservation.** Historical verification evidence MUST be
   retained even after migration. Evidence produced under a prior spec
   version SHOULD be annotated with the spec version it was produced against.

4. **No grandfathering of conflation.** Historical artifacts that conflated
   static and runtime evidence (e.g., labeling static analysis as P4) MUST
   be corrected during migration. The separation principle in Section 2
   applies retroactively to all migrated claims.

5. **Attestation invalidation.** If a MAJOR spec version changes the
   verification model or effect categories, existing P5 attestations become
   advisory. The skill retains its P4M evidence but MUST obtain a new
   attestation against the current spec to claim P5.

## 4. Claiming Conformance

A skill claims a conformance level by including a `conformance` field in its
`skill.abi.yaml`:

```yaml
conformance:
  level: P4M
  spec_version: sabi/v0.1
  evidence_ref: ./conformance/evidence-bundle.yaml
```

The `evidence_ref` MUST point to a machine-readable evidence bundle or a
document describing where evidence is stored. Claims without evidence
references are treated as P0/INVALID regardless of the stated level.
