# SABI v0.1 — Skill ABI Specification

**Version:** 0.1.0
**Status:** Draft
**Date:** 2026-09-10

## 1. Scope

The Skill ABI (SABI) defines a normative contract format for portable agent skills.
A SABI skill is a self-describing unit of agent capability whose portability can be
verified independently of any single runtime, harness, or model.

This specification covers:

- The skill tuple and its six components
- Normative terminology and conformance keywords
- Capability vocabulary and versioning
- Effect bounds and authority separation
- Degradation tiers
- Runtime binding resolution
- Verification stages and evidence requirements
- Conformance levels P0 through P5
- Spec versioning semantics

This specification does NOT cover:

- Skill implementation language or framework
- Model training, fine-tuning, or inference protocols
- Network transport or wire formats for skill invocation
- Trust root provisioning or key management beyond attestation payload shape
- UI rendering or user-facing presentation of skill metadata

## 2. Core Invariant

> **Portable ≠ Parseable.**

Parseability is necessary but never sufficient for portability. A skill document that
parses without error may still fail to execute, degrade incorrectly, or violate declared
effect bounds on a target runtime. Portability requires verified behavior under the
Effect model (E), Degradation model (D), and Verification model (V).

Conformance levels in this spec enforce this invariant: static validation caps at P1;
runtime evidence begins at P4; multi-runtime evidence at P4M; signed attestation at P5.

## 3. Skill Tuple

A SABI skill S is defined as the ordered tuple:

```
S = <I, O, C, E, D, V>
```

| Component | Name | Governing Document |
|-----------|------|--------------------|
| I | Inputs | This document (§4) |
| O | Outputs | This document (§4) |
| C | Capabilities | `capability-model.md` |
| E | Effects | `effect-model.md` |
| D | Degradation | `degradation-model.md` |
| V | Verification | `verification-model.md` |

### 3.1 Inputs (I)

Inputs define the typed data a skill consumes per invocation. Inputs MUST be described
by a schema reference (JSON Schema, OpenAPI fragment, or equivalent). Input schemas
MUST be deterministic: identical input documents produce identical parsed structures.

### 3.2 Outputs (O)

Outputs define the typed data a skill produces per invocation. Like inputs, outputs
MUST be described by a schema reference. Output schemas MUST distinguish success and
failure shapes so callers can discriminate outcomes without parsing prose.

### 3.3 Capabilities (C)

Capabilities are abstract, versioned primitives a skill requires or optionally uses.
See `capability-model.md` for the normative vocabulary, identifier syntax, overlap
rules, and canonicalization.

### 3.4 Effects (E)

Effects are quantified bounds on what a skill invocation may change in the world.
Declared authority is distinct from permitted authority. See `effect-model.md`.

### 3.5 Degradation (D)

Degradation defines deterministic tiers of reduced behavior when capabilities are
unavailable. See `degradation-model.md`.

### 3.6 Verification (V)

Verification defines what must be proven, and how, before a skill claim is accepted.
See `verification-model.md`.

## 4. Non-Goals

The following are explicitly out of scope for SABI v0.1:

1. **Runtime implementation.** SABI specifies contracts, not engines.
2. **Model selection or routing.** Which model executes a skill is orthogonal.
3. **Secret storage.** SABI references credentials abstractly; vaults are external.
4. **Backward compatibility with pre-SABI formats.** Migration is a tooling concern.
5. **Performance benchmarks.** Latency and throughput are runtime metrics, not ABI.
6. **Human-readable documentation generation.** Tooling may derive docs from SABI
   artifacts, but the spec does not prescribe output format.

## 5. Document Map

| Document | Purpose |
|----------|---------|
| `SABI-v0.1.md` (this) | Root: scope, invariant, tuple, non-goals |
| `terminology.md` | Normative terms and RFC 2119 keywords |
| `capability-model.md` | C: vocabulary, identifiers, overlap, versioning |
| `effect-model.md` | E: bounds, authority vs permission, dimensions |
| `degradation-model.md` | D: tiers, determinism, partial order |
| `runtime-binding.md` | B: binding records, resolution, failure |
| `verification-model.md` | V: stages, evidence, non-conflation |
| `conformance.md` | Levels P0–P5, requirements per level |
| `versioning.md` | Spec versioning: PATCH/MINOR/MAJOR |

Each document is self-contained given `terminology.md` and this root document as
prerequisites. No circular dependencies exist.

## 6. Conformance Level Overview

Full requirements appear in `conformance.md`. Summary:

| Level | Name | Requirement |
|-------|------|-------------|
| P0 | INVALID | Fails parse or structural check |
| P1 | SPEC_VALID | Parses and satisfies all MUST clauses |
| P2 | EFFECT_AWARE | Static conformance of E declarations |
| P3 | DEGRADATION_CONFORMANT | Static conformance of D declarations |
| P4 | RUNTIME_TESTED | Verified via real execution on ≥1 runtime |
| P4M | MULTI_RUNTIME_TESTED | Verified on ≥2 independent runtimes |
| P5 | ATTESTED | Signed attestation over P4M evidence |

Static checks cap at P1 for structural validity; P2 and P3 add static conformance
of effect and degradation declarations respectively. Runtime evidence begins at P4.
