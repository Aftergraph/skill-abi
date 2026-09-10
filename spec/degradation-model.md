# SABI v0.1 — Degradation Model (D)

## 1. Purpose

The degradation model D defines how a skill behaves when one or more
capabilities declared in C are unavailable at runtime. Degradation is
not optional error handling; it is a deterministic, pre-declared lattice
of fallback behaviors that a conformant runtime MUST resolve without
LLM decision-making.

## 2. Degradation Tiers

A skill declares an ordered set of tiers. Each tier specifies the
capabilities it requires and the behavior it produces.

### 2.1 Tier Structure

Each tier is a named entry containing:

- **name**: unique identifier within the skill's degradation model.
- **requires**: list of capability identifiers from C that must be
  available for this tier to be selected.
- **terminal** (optional, boolean): if true, this tier represents
  explicit refusal. A terminal tier produces no side effects and
  returns a structured rejection to the caller.
- **note** (optional, string): human-readable explanation of what
  the skill does at this tier.

### 2.2 Deterministic Max-Tier Selection

Given a runtime environment R providing a set of available capabilities
R_caps, the resolved tier T* is computed as:

    T* = max{ Ti | requires(Ti) ⊆ R_caps }

The `max` operator uses the partial order defined in Section 3. If
multiple tiers share the same maximal position (incomparable under the
partial order), the skill author MUST declare an explicit priority list
that breaks ties deterministically. The resolver MUST NOT use heuristic
or LLM-based selection.

**Determinism requirement**: identical inputs and identical available
capability sets MUST produce the identical tier on every invocation,
across all conformant runtimes.

### 2.3 Terminal Tier

Every degradation model MUST contain exactly one terminal tier. When
no non-terminal tier's requirements are satisfied by R_caps, the
resolver selects the terminal tier. The terminal tier MUST NOT perform
any effect declared in E.

## 3. Partial Order Over Capability and Effect Loss

Tiers form a partially ordered set (poset) under the subset relation
on their `requires` sets.

### 3.1 Ordering Rule

For two tiers Ta and Tb:

    Ta ≤ Tb  ⟺  requires(Ta) ⊆ requires(Tb)

This means Tb provides at least the functionality of Ta (it requires
more capabilities, so it can do more). The full tier (maximum element)
requires all capabilities. The minimal non-terminal tier requires the
fewest.

### 3.2 Incomparable Tiers

Two tiers are incomparable when neither's requirement set is a subset
of the other. This occurs when a skill offers alternative capability
paths (e.g., shell.execute vs. api.call for the same outcome). The
skill author MUST provide a deterministic tiebreaker via an explicit
priority list. Without a tiebreaker, the degradation model is invalid
and the skill cannot exceed P0/INVALID.

### 3.3 Effect Loss Mapping

When degrading from a higher tier to a lower tier, some effects in E
may become unreachable. The degradation model MUST document which
effects are lost at each non-full tier. An effect is "lost" at tier T
if no execution path at T can produce that effect.

Effect loss is monotonic: if Ta ≤ Tb, then every effect available at
Ta is also available at Tb. Non-monotonic effect availability indicates
a malformed degradation model.

## 4. Normative Requirements

1. Every skill declaring conformance ≥ P3/DEGRADATION_CONFORMANT MUST
   include a complete degradation model with at least one non-terminal
   tier and exactly one terminal tier.
2. The resolver MUST compute T* using only the set-inclusion rule in
   Section 2.2. No probabilistic, learned, or prompt-driven resolution
   is permitted.
3. The degradation model MUST be self-consistent: every capability in
   any tier's `requires` list MUST appear in the skill's capability
   declaration C.
4. A runtime encountering a capability set that satisfies no
   non-terminal tier MUST select the terminal tier and MUST NOT
   silently skip effects or fabricate outputs.
5. The degradation model is part of the machine-readable contract.
   Changes to tier structure, requirements, or priority ordering
   constitute a version change under versioning.md.
