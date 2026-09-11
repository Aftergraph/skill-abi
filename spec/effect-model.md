# SABI v0.1 — Effect Model (E)

**Version:** 0.1.1
**Status:** Draft
**Date:** 2026-09-10

This document defines the normative effect bounds, authority separation,
bound dimensions, typed constraint semantics, and enforcement
responsibilities for the Effects component (E) of the SABI skill tuple
S = <I, O, C, E, D, V>.

Prerequisites: `SABI-v0.1.md` (scope, invariant), `terminology.md` (terms).

## 1. Purpose

Effects quantify what a skill invocation may change in the world. Unlike
capabilities, which describe abstract operation classes, effects describe
concrete, bounded state changes. Every skill MUST declare its effects so that
runtimes and verifiers can reason about safety without executing the skill.

## 2. Declared Authority vs Permitted Authority

A foundational principle of the SABI effect model:

> **Declared authority ≠ permitted authority.**

- **Declared authority** is the set of effect bounds a skill's author claims
  the skill will not exceed. It is expressed in the skill's `effects.yaml`
  or equivalent artifact.
- **Permitted authority** is the set of effect bounds a runtime actually
  allows during execution, determined by policy, binding configuration, and
  environment constraints.

A skill MAY declare broad authority but be executed under narrow permissions.
A skill MUST NOT exceed its declared authority. A runtime MUST NOT grant
permissions beyond what the skill declares. The effective authority at
execution time is the intersection of declared and permitted authority.

If a skill attempts an effect outside its declared bounds, the runtime MUST
block the operation or halt the skill, depending on the binding's failure
semantics. If a runtime cannot enforce a declared bound, it MUST refuse to
execute the skill rather than execute it unbounded.

### 2.1 The semantic-bound boundary

SABI defines the **semantic bound only**. This document, the effects schema,
and the reference effect checker specify:

1. what a declaration *means* (typed, quantified constraint semantics), and
2. when one declaration is *contained in* another (no widening).

They do **not** specify how the bound is enforced. Provider-specific
enforcement — sandboxing, syscall filtering, egress proxies, secret
injection, approval gates, spend limits — belongs to runtime and trust
systems and MUST NOT be encoded in this ABI. A binding record MAY map an
abstract category to a concrete enforcement mechanism, but the mapping is
not part of the semantic bound.

## 3. Bound Dimensions

Every effect declaration MUST specify values across five dimensions:

### 3.1 Reversibility

Whether the effect can be undone without residual state.

| Value | Meaning |
|-------|---------|
| `reversible` | The effect can be fully undone (e.g., writing a temp file then deleting it) |
| `partially-reversible` | Some state can be restored but traces remain (e.g., sending then deleting a message) |
| `irreversible` | The effect cannot be undone (e.g., publishing a package, transferring funds) |

Skills SHOULD prefer reversible effects where possible. Irreversible effects
MUST be explicitly declared and require higher verification evidence.

### 3.2 Scope

The set of resources an effect may touch. Scope MUST be enumerated or
bounded by a pattern. An undeclared scope dimension defaults to empty
(no access), never to unlimited.

### 3.3 External Visibility

Whether the effect produces observable changes outside the local execution
environment.

| Value | Meaning |
|-------|---------|
| `local-only` | No external observer can detect the effect |
| `external` | The effect is visible to external systems or users |

Message sends, network requests, and deployments are `external`. Local file
writes within a sandboxed workspace are `local-only`.

### 3.4 Quantity Bounds

Numeric limits on how many times an effect may occur per invocation.

- `max_operations`: maximum number of discrete operations (e.g., messages sent,
  files written). MUST be a non-negative integer. A value of `0` means the
  effect category is declared but must not occur.
- `amount`: for monetary effects, the maximum value per invocation. MUST be a
  non-negative number. A value of `0` means no financial operations are
  permitted. `amount` greater than `0` REQUIRES an explicit `currency`.
- `currency`: ISO 4217 three-letter uppercase code (pattern `^[A-Z]{3}$`).
  A monetary declaration with no currency is unbounded in unit and therefore
  INVALID when `amount > 0`.

`max_amount` is accepted as a v0.1 compatibility alias for `amount`.

### 3.5 Credential Exposure

Whether credentials (API keys, tokens, passwords) are exposed to the model
or agent context during execution.

- `expose_to_model`: boolean, and in v0.1 MUST be `false`. Credentials MUST
  be injected at the runtime/tool layer without appearing in the model's
  context window. A declaration that sets `true` is INVALID.

## 4. Typed Effect Categories

SABI recognizes nine effect categories. Each category accepts only the
constraint keys listed for it; any other key is a typing error. This is what
makes an envelope *typed* rather than a free-form mapping.

| Category | `allowed` | `scope` | `paths` | `branches` | `destinations` | `domains` | `environment` | `max_operations` | `amount` / `currency` |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `filesystem` | ✓ | ✓ | ✓ | – | – | – | – | ✓ | – |
| `repository` | ✓ | ✓ | – | ✓ | – | – | – | ✓ | – |
| `process` | ✓ | ✓ | – | – | – | – | ✓ | ✓ | – |
| `network` | ✓ | – | – | – | ✓ | ✓ | – | ✓ | – |
| `message` | ✓ | – | – | – | ✓ | – | – | ✓ | – |
| `artifact` | ✓ | ✓ | ✓ | – | – | – | – | ✓ | – |
| `deployment` | ✓ | ✓ | – | – | ✓ | ✓* | ✓ | ✓ | – |
| `credential` | ✓ | ✓ | – | – | – | – | ✓ | ✓ | – |
| `money` | ✓ | – | – | – | – | – | – | ✓ | ✓ |

\* `deployment` accepts `destinations` (named targets) and `environment`
(named deployment environments such as `staging`); `domains` is not part of
the deployment category and MUST be expressed as `network`.

Per-category constraint semantics:

- **`allowed`** — boolean. Explicitly grants or withholds the category. When
  absent, `allowed` is implied: `true` if the declaration carries a quantified
  bound, `false` otherwise. `allowed: true` without any quantified bound is
  INVALID. `allowed: false` together with non-empty bounds is INVALID
  (contradictory).
- **`scope`** — list of path, command, credential-name, or target globs the
  effect may touch. Empty list means no access.
- **`paths`** — list of explicit path globs (filesystem/artifact). Where both
  `paths` and `scope` are declared, the effective path bound is their union.
- **`branches`** — list of branch globs a repository effect may push to.
- **`destinations`** — list of named targets (chat, endpoint, cluster).
- **`domains`** — list of network domains an effect may contact.
- **`environment`** — list of environment names (variables for `process` and
  `credential`; named deployment environments for `deployment`).
- **`max_operations`** — non-negative integer, per invocation.
- **`amount` / `currency`** — money only; see §3.4.
- **`expose_to_model`** — credential only; see §3.5.
- **`note`** — free-text documentation. Permitted on every category and never
  widens a bound.

The v0.1 dotted names (`filesystem.read`, `filesystem.write`,
`repository.push`, `process.spawn`, `network.egress`, `message.send`,
`artifact.create`, `deployment.create`, `credentials`) remain valid aliases
and map onto the canonical categories above. Exactly one entry per canonical
category is permitted; declaring an alias and its canonical name together is
a duplicate-category error.

Additional categories MAY be defined via spec extension (MINOR bump).

## 5. Quantification Requirements

Effect bounds MUST be quantified. Vague declarations such as "may write files"
or "sends messages" without numeric or scoped limits are P0/INVALID.

Valid example (sanitized from reference implementation):

```yaml
effects:
  message.send:
    destinations:
      - telegram:FIXTURE_CHAT_ID
    max_operations: 1
    note: one card update per invocation
  filesystem.write:
    scope: []
    max_operations: 0
  network.egress:
    domains: []
    max_operations: 0
  money:
    max_amount: 0
  credentials:
    expose_to_model: false
```

In this example:
- Exactly one message may be sent to a single fixture destination.
- No filesystem writes are permitted.
- No network egress is permitted.
- No financial operations are permitted.
- Credentials are not exposed to the model.

Note: Real chat identifiers, user identifiers, or personal data MUST NOT
appear in effect declarations. Use placeholder values such as
`FIXTURE_CHAT_ID` for specification examples and test fixtures.

## 6. Envelope Containment — Widening Is Rejected

A declared envelope may itself be constrained by an enclosing envelope
(policy, binding, or a narrower mission scope). The inner envelope MUST be
contained in the outer envelope:

> **inner ⊆ outer. Any widening is a violation.**

Containment is checked dimension by dimension, conservatively:

| Dimension | Containment rule |
|-----------|------------------|
| category | An inner category absent from the outer envelope is widening. |
| `allowed` | Inner `true` while outer is not `true` is widening. |
| `max_operations` | Inner greater than outer is widening. Undeclared outer defaults to `0`. |
| `scope`, `paths`, `branches`, `destinations`, `domains`, `environment` | Every inner entry MUST be glob-covered by an outer entry. A pattern the check cannot prove to be covered is rejected. |
| `amount` | Inner greater than outer is widening. |
| `currency` | Inner currency differing from the outer currency is widening. |
| `expose_to_model` | Inner `true` while outer is not `true` is widening. |

A vacuous inner declaration (all bounds empty, `allowed` not `true`) is
contained by anything: declaring that an effect will not occur never widens.

Symmetrically, an observed effect record MUST be contained in its declared
envelope. Undeclared-but-zero observations are clean; undeclared non-zero
observations are violations.

## 7. Enforcement Responsibility

| Actor | Responsibility |
|-------|---------------|
| Skill author | Declare accurate, complete effect bounds |
| SABI (this spec, schema, checker) | Define the semantic bound; decide typing, quantification, and containment |
| Runtime | Enforce declared bounds at execution time; block or halt on violation |
| Binding record | Map abstract effect categories to concrete enforcement mechanisms |
| Verification stage | Prove that enforcement was exercised (P4+) |
| Attestor | Sign evidence that bounds were respected during verified runs (P5) |

No single actor bears sole responsibility. The effect model distributes
enforcement across authoring, binding, execution, and verification layers.
Enforcement mechanisms are provider-specific and MUST NOT be encoded in the
SABI ABI.

## 8. Relationship to Capabilities

Capabilities (C) describe what a skill needs; effects (E) describe what a
skill does. A skill may require `shell.execute` (capability) but declare
zero `process` effects if it only runs read-only commands. Conversely,
a skill with `message` effects MUST require the corresponding `message.*`
capability.

Verification MUST check that every declared effect category has a
corresponding required or optional capability. Undeclared capabilities with
declared effects indicate incomplete contracts.

## 9. Grounding Note

The reference skill `telegram-live-status` demonstrates minimal effects:
one message send to a fixture destination, zero filesystem writes, zero
network egress, zero financial operations, and no credential exposure to
the model. This represents a tightly bounded effect profile suitable for
high-conformance attestation. `conformance/effect-vectors.yaml` carries the
normative accept/reject vectors, including the widening-rejection vectors.
