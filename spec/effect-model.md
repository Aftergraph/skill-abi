# SABI v0.1 — Effect Model (E)

**Version:** 0.1.0
**Status:** Draft
**Date:** 2026-09-10

This document defines the normative effect bounds, authority separation,
bound dimensions, and enforcement responsibilities for the Effects component
(E) of the SABI skill tuple S = <I, O, C, E, D, V>.

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
bounded by a pattern.

Examples:
- `filesystem.write.scope`: list of path globs the skill may write to.
  An empty list (`[]`) means no filesystem writes are declared.
- `network.egress.domains`: list of domains the skill may contact.
  An empty list means no network egress is declared.

An undeclared scope dimension defaults to empty (no access), not unlimited.

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
- `max_amount`: for financial effects, the maximum monetary value per
  invocation. MUST be a non-negative number with currency unit. A value of `0`
  means no financial operations are permitted.

### 3.5 Credential Exposure

Whether credentials (API keys, tokens, passwords) are exposed to the model
or agent context during execution.

- `expose_to_model`: boolean. When `false`, credentials MUST be injected at
  the runtime/tool layer without appearing in the model's context window.
  When `true`, the skill acknowledges that credential material enters the
  model context, which carries elevated risk.

Skills SHOULD set `expose_to_model: false` unless the capability inherently
requires the model to read secret material.

## 4. Effect Categories

SABI v0.1 recognizes the following effect categories. Each category maps to
one or more capability families but is evaluated independently:

| Category | Description | Key Dimensions |
|----------|-------------|----------------|
| `filesystem.write` | Local file creation or mutation | scope, max_operations, reversibility |
| `filesystem.read` | Local file access | scope |
| `network.egress` | Outbound network connections | domains, max_operations, visibility |
| `message.send` | Delivery of messages to platforms | destinations, max_operations, visibility |
| `money` | Financial transactions or commitments | max_amount, reversibility |
| `credentials` | Access to or exposure of secrets | expose_to_model |
| `process.spawn` | Child process creation | scope, max_operations |

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

## 6. Enforcement Responsibility

| Actor | Responsibility |
|-------|---------------|
| Skill author | Declare accurate, complete effect bounds |
| Runtime | Enforce declared bounds at execution time; block or halt on violation |
| Binding record | Map abstract effect categories to concrete enforcement mechanisms |
| Verification stage | Prove that enforcement was exercised (P4+) |
| Attestor | Sign evidence that bounds were respected during verified runs (P5) |

No single actor bears sole responsibility. The effect model distributes
enforcement across authoring, binding, execution, and verification layers.

## 7. Relationship to Capabilities

Capabilities (C) describe what a skill needs; effects (E) describe what a
skill does. A skill may require `shell.execute` (capability) but declare
zero `process.spawn` effects if it only runs read-only commands. Conversely,
a skill with `message.send` effects MUST require the corresponding `message.*`
capability.

Verification MUST check that every declared effect category has a
corresponding required or optional capability. Undeclared capabilities with
declared effects indicate incomplete contracts.

## 8. Grounding Note

The reference skill `telegram-live-status` demonstrates minimal effects:
one message send to a fixture destination, zero filesystem writes, zero
network egress, zero financial operations, and no credential exposure to
the model. This represents a tightly bounded effect profile suitable for
high-conformance attestation.
