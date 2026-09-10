# SABI v0.1 — Verification Model (V)

**Version:** 0.1.0
**Status:** Draft
**Date:** 2026-09-10

This document defines the verification stages, evidence requirements, and
ground-truth obligations for the Verification component (V) of the SABI skill
tuple S = <I, O, C, E, D, V>.

Prerequisites: `SABI-v0.1.md` (scope, invariant), `terminology.md` (terms).

## 1. Foundational Principle

> **DeclaredComplete ≠ VerifiedComplete.**

A skill author may declare that a skill satisfies all structural, capability,
effect, and degradation requirements. This declaration is a claim, not proof.
Verification is the process of producing evidence that independently confirms
or refutes each claim. A skill is never treated as verified solely because its
author declared it complete.

- **DeclaredComplete**: The skill's contract artifacts parse without error and
  the author asserts all MUST clauses are satisfied. This caps at P1/SPEC_VALID.
- **VerifiedComplete**: Independent evidence (static analysis, runtime execution,
  multi-runtime testing, or signed attestation) confirms the claims. This begins
  at P4/RUNTIME_TESTED.

No conformance level above P1 may be claimed without external evidence. Self-
declaration alone is insufficient for portability claims.

## 2. Verification Stages

Verification proceeds through four stages. Each stage proves properties the
prior stage cannot. Stages are cumulative: higher stages include all evidence
from lower stages.

### 2.1 Static Analysis (P1–P3)

Static analysis operates on contract artifacts without executing the skill.

**What it proves:**
- Structural validity: YAML/JSON parses correctly, required fields present.
- Schema conformance: inputs (I) and outputs (O) reference valid schemas.
- Capability vocabulary: all identifiers in C belong to the nine families and
  use correct syntax.
- Effect declaration completeness: all effect categories in E have quantified
  bounds (no vague declarations).
- Degradation model structure: tiers form a valid partial order with exactly
  one terminal tier.
- Cross-referential consistency: every capability referenced in D exists in C;
  every effect referenced in D exists in E.

**What it does NOT prove:**
- That the skill executes without error.
- That effect bounds are actually respected during execution.
- That degradation tiers produce correct behavior when capabilities are absent.
- That bindings resolve to working implementations.

Static analysis caps conformance at P3/DEGRADATION_CONFORMANT. Claims of P4 or
above based solely on static analysis are invalid.

### 2.2 Single-Runtime Testing (P4)

Runtime testing executes the skill under a specific binding on a named runtime
and observes actual behavior.

**What it proves:**
- The skill executes to completion (or degrades to the terminal tier) without
  unhandled errors.
- Observed effects do not exceed declared bounds in E.
- The resolved degradation tier matches the deterministic max-tier selection
  rule from `degradation-model.md`.
- Binding implementations satisfy the capabilities they claim.

**Evidence requirements:**
- Execution trace or log showing invocation inputs, observed effects, and
  outputs.
- Comparison report mapping observed effects against declared bounds.
- Identification of the runtime, binding file, and harness used.

### 2.3 Multi-Runtime Testing (P4M)

Multi-runtime testing repeats P4 verification on two or more independent
runtimes with distinct binding files.

**What it proves:**
- Portability: the skill produces consistent results across runtimes.
- Binding independence: no single runtime's quirks are baked into the skill.
- Degradation determinism: identical capability subsets produce identical tier
  selection across runtimes.

**Evidence requirements:**
- All P4 evidence for each runtime tested.
- Cross-runtime comparison report showing output equivalence or documented
  acceptable divergence.
- Minimum two runtimes with non-identical binding implementations.

### 2.4 Signed Attestation (P5)

Attestation wraps P4M evidence in a cryptographic signature from a recognized
attestor.

**What it proves:**
- All P4M properties, plus provenance: the evidence was produced by a specific
  attestor at a specific time and has not been tampered with.
- Non-repudiation: the attestor cannot deny having verified the skill.

**Evidence requirements:**
- Complete P4M evidence bundle.
- Cryptographic signature over the evidence bundle (e.g., ed25519, Sigstore).
- Attestor identity and public key reference.
- Timestamp of attestation.

## 3. Ground Truth Per Effect Class

Verification MUST evaluate effects against ground truth appropriate to each
effect category. Generic assertions without category-specific evidence are
insufficient.

| Effect Category | Ground-Truth Source |
|-----------------|---------------------|
| `filesystem.write` | Filesystem state diff before/after invocation; file existence, content hash, and path match declared scope |
| `filesystem.read` | Access logs or sandbox audit trail confirming only declared paths were read |
| `network.egress` | Network capture or proxy log showing destination domains and request counts within declared bounds |
| `message.send` | Platform delivery receipt or API response confirming destination matches declared targets (using fixture identifiers such as FIXTURE_CHAT_ID, never real identifiers) and count within max_operations |
| `money` | Transaction ledger entry or payment API response confirming amount within max_amount and currency matches declaration |
| `credentials` | Context inspection confirming credential material did not appear in model context when expose_to_model is false |
| `process.spawn` | Process table diff or sandbox audit confirming spawned processes fall within declared scope and count |

For each effect class, the verifier MUST record whether the observed behavior
was within bounds, exceeded bounds, or was not exercised. Unexercised effects
MUST be reported as "not verified" rather than "passed."

## 4. Non-Conflation Rules

The following conflations are explicitly prohibited:

1. **Static ≠ Runtime**: Passing static validation (P1–P3) MUST NOT be reported
   as runtime-tested (P4). The labels "static" and "runtime" describe distinct
   evidence types.
2. **Runtime ≠ Multi-Runtime**: Testing on one runtime (P4) MUST NOT be reported
   as multi-runtime tested (P4M). Portability requires evidence from at least
   two independent runtimes.
3. **Multi-Runtime ≠ Signed**: P4M evidence without a cryptographic signature
   MUST NOT be reported as P5/ATTESTED. Unsigned multi-runtime evidence remains
   P4M.
4. **Declared ≠ Verified**: An author's declaration that effects are bounded
   MUST NOT be treated as evidence of bounding. Only runtime observation or
   attestation constitutes verification.

## 5. Evidence Retention

Verification evidence MUST be retained alongside the skill artifact or
referenced by stable identifier. Evidence that cannot be re-examined by a
third party does not support conformance claims. Evidence bundles SHOULD
include sufficient context (runtime version, binding file hash, harness
version) to reproduce the verification result.
