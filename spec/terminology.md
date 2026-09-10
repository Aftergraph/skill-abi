# SABI v0.1 — Terminology

**Version:** 0.1.0
**Status:** Draft
**Date:** 2026-09-10

This document defines normative terms used across the SABI specification.
All other SABI documents depend on this glossary.

## 1. RFC 2119 Keywords

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**,
**SHOULD**, **SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in SABI
documents are to be interpreted as described in RFC 2119.

- **MUST / MUST NOT**: Absolute requirement or prohibition. A skill violating
  a MUST clause is P0/INVALID.
- **SHOULD / SHOULD NOT**: Strong recommendation. Deviation is permitted only
  when documented with rationale; conformance level may be capped.
- **MAY / OPTIONAL**: Truly optional behavior. Implementations that do not
  support an OPTIONAL feature MUST still interoperate with those that do.

## 2. Core Terms

### Skill
A self-describing unit of agent capability conforming to the SABI tuple
S = <I, O, C, E, D, V>. A skill is defined by its contract artifacts (YAML
or JSON files), not by its implementation code. A directory containing
prose instructions without a `skill.abi.yaml` is not a SABI skill.

### Runtime
An execution environment capable of invoking a skill. A runtime provides
a concrete set of capabilities and enforces effect bounds. Examples include
Hermes Agent, Muse Code, or any harness that satisfies the binding model.

### Binding
A mapping from abstract capability identifiers to concrete implementations
within a specific runtime. A binding record declares which runtime it targets,
which capabilities are available, and how each capability is implemented.
See `runtime-binding.md`.

### Capability
An abstract, versioned primitive representing a class of operations a skill
may require. Capabilities are not tools: a tool is a concrete function or
command, while a capability is the semantic category it belongs to.
See `capability-model.md`.

### Effect
A quantified bound on observable state changes produced by a skill invocation.
Effects cover filesystem mutations, network egress, message delivery, financial
operations, and credential exposure. See `effect-model.md`.

### Degradation
Deterministic reduction in skill behavior when one or more required
capabilities are unavailable. Degradation tiers form a partial order.
See `degradation-model.md`.

### Attestation
A cryptographically signed record proving that a skill was executed under
specific conditions and produced verified results. Attestation elevates
conformance to P5. See `verification-model.md`.

### Portability vs Parseability
Parseability means a skill document can be read and structurally validated
by a parser. Portability means the skill executes correctly, degrades
deterministically, and respects effect bounds across runtimes. The core
invariant of SABI is that portable != parseable: parseability is necessary
but never sufficient for portability.

### Conformance Level
A discrete classification (P0 through P5) indicating how thoroughly a skill's
claims have been verified. See `conformance.md` for exact requirements.

### Verification Stage
A phase of evidence collection: static analysis, single-runtime execution,
multi-runtime execution, or attestation. Each stage proves different
properties. See `verification-model.md`.

### Harness
A test or execution framework that drives a skill through its lifecycle.
A harness is distinct from a runtime: the runtime provides capabilities;
the harness orchestrates invocation and observation.

### Tuple Component
One of the six elements I, O, C, E, D, V that compose a SABI skill.
Each component has its own governing document within this specification.
