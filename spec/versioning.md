# SABI v0.1 — Specification Versioning

**Version:** 0.1.0
**Status:** Draft
**Date:** 2026-09-10

This document defines the semantic versioning rules for the SABI specification
itself and for individual skill contracts that declare conformance to it.

Prerequisites: `SABI-v0.1.md` (scope, invariant), `terminology.md` (terms).

## 1. Version Format

SABI uses Semantic Versioning 2.0.0 with the format:

```
MAJOR.MINOR.PATCH
```

The current specification version is `0.1.0`. While MAJOR is `0`, the
specification is considered pre-release; MINOR bumps MAY introduce breaking
changes until `1.0.0` is reached. After `1.0.0`, the rules below are
normative and binding.

## 2. PATCH Semantics

A PATCH increment (e.g., `0.1.0` → `0.1.1`) indicates backward-compatible
defect corrections. PATCH changes MUST NOT alter the normative requirements
of any conformance level.

### 2.1 Permitted PATCH Changes

- Correcting typographical errors in prose that do not change normative meaning.
- Fixing malformed YAML/JSON examples so they parse correctly.
- Clarifying ambiguous wording where only one interpretation was intended.
- Adding missing cross-references between documents.
- Correcting alias table entries without removing canonical identifiers.

### 2.2 Prohibited PATCH Changes

- Adding new MUST clauses to any conformance level.
- Changing the semantics of an existing capability identifier.
- Altering effect bound dimensions or their valid values.
- Modifying the degradation tier selection algorithm.
- Adding or removing fields from the binding record shape.

### 2.3 Breaking Examples That Are NOT Patches

These changes require at least a MINOR bump:

- Fixing a typo that changes "MUST" to "SHOULD" or vice versa.
- Correcting a capability identifier syntax rule that invalidates previously
  valid identifiers.
- Adding a required field to `skill.abi.yaml` that existing skills lack.

## 3. MINOR Semantics

A MINOR increment (e.g., `0.1.0` → `0.2.0`) introduces backward-compatible
additions. Existing skills conformant under the prior version remain
conformant under the new version without modification.

### 3.1 Permitted MINOR Changes

- Adding new capability families beyond the initial nine.
- Adding new effect categories with defined ground-truth verification methods.
- Introducing OPTIONAL fields to contract artifacts.
- Adding new degradation tiers as examples without changing the selection
  algorithm.
- Defining new aliases that map to existing canonical identifiers.
- Extending the verification model with additional evidence types that do not
  invalidate existing evidence.
- Adding new conformance levels above P5 (if needed) without altering P0–P5.

### 3.2 Compatibility Direction

MINOR bumps preserve forward compatibility for consumers and backward
compatibility for producers:

- A runtime supporting spec `0.2.0` MUST accept skills written for `0.1.x`.
- A skill written for `0.2.0` MAY be rejected by a runtime supporting only
  `0.1.x` if it uses features introduced in `0.2.0`.

### 3.3 Breaking Examples That Require MAJOR Instead

These changes are NOT permitted under MINOR:

- Removing a capability family (skills using it become P0/INVALID).
- Changing the degradation max-tier selection formula.
- Renaming an existing conformance level or changing its requirements such
  that previously conformant skills no longer qualify.
- Replacing the tuple structure S = <I, O, C, E, D, V> with a different
  arity or component set.
- Changing the cryptographic signature scheme for P5 attestation in a way
  that invalidates existing signatures.

## 4. MAJOR Semantics

A MAJOR increment (e.g., `0.1.0` → `1.0.0`, or `1.0.0` → `2.0.0`) introduces
incompatible changes. Skills conformant under the prior MAJOR version are not
guaranteed to be conformant under the new version.

### 4.1 Changes Requiring MAJOR Bump

- Removing or renaming any of the nine capability families.
- Changing the core invariant (Portable ≠ Parseable) or the skill tuple
  structure.
- Modifying the conformance level definitions such that a skill's level
  changes without re-verification.
- Altering the verification stage boundaries (e.g., allowing static analysis
  to satisfy P4 requirements).
- Changing the binding resolution order or failure semantics in a way that
  alters which tier is selected for a given capability set.
- Removing support for an effect category that existing skills declare.
- Any change that violates the separation principle (static ≠ runtime ≠
  multi ≠ signed).

### 4.2 Breaking Examples

1. **Capability family removal**: If `shell.*` is removed from the vocabulary,
   every skill requiring `shell.execute` becomes P0/INVALID under the new
   spec. This is a MAJOR change.

2. **Tuple restructuring**: Adding a seventh component to S = <I, O, C, E, D, V>
   means all existing skill contracts lack the new component and fail
   structural validation. MAJOR bump required.

3. **Conformance level redefinition**: If P4/RUNTIME_TESTED is redefined to
   require three runtimes instead of one, all existing P4 skills lose their
   conformance claim. MAJOR bump required.

4. **Effect dimension removal**: Removing the `credential_exposure` dimension
   from the effect model means existing effect declarations reference a
   nonexistent dimension. MAJOR bump required.

5. **Degradation algorithm change**: Replacing the deterministic max-tier
   selection with a weighted scoring system changes which tier is selected
   for identical inputs. All degradation models become invalid. MAJOR bump
   required.

## 5. Deprecation Policy

### 5.1 Capability Deprecation

A capability identifier MAY be deprecated via a MINOR bump by adding it to
the alias table with a pointer to its replacement. The deprecated identifier
remains valid for parsing but tooling SHOULD emit warnings. Removal of the
alias requires a MAJOR bump.

### 5.2 Effect Category Deprecation

An effect category MAY be deprecated via a MINOR bump. Deprecated categories
remain recognized for two MINOR versions before removal. Removal requires a
MAJOR bump.

### 5.3 Conformance Level Deprecation

Conformance levels MUST NOT be deprecated. They may be superseded (e.g., P4M
introduced after P4) but never removed within a MAJOR version.

## 6. Skill Contract Versioning

Individual skills declare the minimum spec version they require:

```yaml
spec: sabi/v0.1
```

When a skill's contract changes (capabilities added, effects modified,
degradation tiers altered), the skill author MUST update the skill's own
version. Skill-level versioning follows the same PATCH/MINOR/MAJOR semantics:

- **PATCH**: Prose clarifications, metadata updates that do not affect
  execution behavior.
- **MINOR**: Adding optional capabilities, widening effect bounds within
  declared limits, adding non-terminal degradation tiers.
- **MAJOR**: Removing required capabilities, narrowing effect bounds in ways
  that break callers, removing degradation tiers, changing input/output
  schemas incompatibly.

Runtimes MUST reject skills whose declared minimum spec version exceeds the
runtime's supported spec version.

## 7. Version Negotiation

When a runtime loads a skill, it performs version negotiation:

1. Read the skill's `spec` field.
2. Compare against the runtime's supported spec version.
3. If the skill requires a newer MAJOR version than the runtime supports,
   refuse to load and report a version mismatch error.
4. If the skill requires a newer MINOR or PATCH version, the runtime MAY
   attempt to load it but MUST treat unrecognized fields as absent and
   resolve to the terminal degradation tier if required capabilities cannot
   be mapped.
5. If the skill's spec version is older than the runtime's, apply the
   migration rules from `conformance.md` Section 3 to determine the skill's
   effective conformance level.
