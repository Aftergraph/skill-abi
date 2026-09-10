# SABI v0.1 — Capability Model (C)

**Version:** 0.1.0
**Status:** Draft
**Date:** 2026-09-10

This document defines the normative capability vocabulary, identifier syntax,
versioning rules, overlap semantics, and canonicalization for the Capabilities
component (C) of the SABI skill tuple S = <I, O, C, E, D, V>.

Prerequisites: `SABI-v0.1.md` (scope, invariant), `terminology.md` (terms).

## 1. Capability ≠ Tool

A **capability** is an abstract, versioned semantic category representing a
class of operations. A **tool** is a concrete function, command, or API endpoint
within a specific runtime that implements one or more capabilities.

Example: `shell.execute` is a capability. The `terminal()` function in Hermes
Agent and the `exec()` primitive in Muse Code are both tools that implement
`shell.execute`. A skill declares required capabilities; a binding maps them to
available tools.

This distinction is foundational: skills MUST declare capabilities, never tool
names. Binding records (see `runtime-binding.md`) resolve capabilities to tools.

## 2. Capability Identifier Syntax

Capability identifiers MUST follow the pattern:

```
<family>.<action>[.<qualifier>]
```

- `family`: one of the nine families defined in §3.
- `action`: a verb or verb-noun pair describing the operation class.
- `qualifier`: optional dot-separated refinement.

All segments MUST be lowercase ASCII alphanumeric with hyphens permitted.
Identifiers MUST NOT contain spaces, underscores, or uppercase characters.

Examples:
- `filesystem.read`
- `message.send`
- `git.repository.clone`
- `network.egress.http`

## 3. Capability Families

SABI v0.1 defines exactly nine capability families. Every capability identifier
MUST belong to one of these families. New families require a MAJOR spec bump
(see `versioning.md`).

| # | Family | Prefix | Scope |
|---|--------|--------|-------|
| 1 | Filesystem | `filesystem.*` | Read, write, delete, stat of local files and directories |
| 2 | Process/Shell | `shell.*` | Command execution, process management, environment access |
| 3 | Web/Network | `network.*` | HTTP egress/ingress, DNS, socket-level operations |
| 4 | Git/Repository | `git.*` | Clone, commit, push, pull, branch, tag operations |
| 5 | Database | `database.*` | Query, mutate, migrate persistent data stores |
| 6 | Test/CI | `ci.*` | Test execution, coverage collection, pipeline orchestration |
| 7 | Artifact/Deployment | `artifact.*` | Build, package, publish, deploy operations |
| 8 | Message | `message.*` | Send, receive, update messages on communication platforms |
| 9 | User/Agent | `agent.*` | Identity assertion, delegation, sub-agent spawning |

## 4. Versioning of Capabilities

Each capability identifier carries an implicit version tied to the SABI spec
version. When a capability's semantics change incompatibly, the identifier
MUST be replaced (not version-suffixed). Minor refinements to a capability's
scope are handled via MINOR spec bumps.

A skill MAY declare a minimum spec version in its `skill.abi.yaml` under
`spec: sabi/v0.1`. Runtimes MUST reject skills requiring a newer spec version
than they support.

## 5. Overlap and Alias Rules

### 5.1 No Semantic Overlap Within a Family

Two capability identifiers within the same family MUST NOT describe the same
operation class. If overlap is discovered, it is a specification defect
requiring resolution via alias canonicalization.

### 5.2 Cross-Family Boundaries

Some operations span families. For example, pushing a git commit over HTTPS
involves both `git.repository.push` and `network.egress.http`. Skills MUST
declare all involved capabilities. A runtime providing only `git.repository.push`
without `network.egress.http` MUST trigger degradation (see `degradation-model.md`),
not silently fail the network portion.

### 5.3 Aliases

An alias is a deprecated identifier that maps to a canonical identifier. Aliases
MUST be listed in a normative alias table maintained by the spec. Parsers MUST
resolve aliases to canonical form before validation. Skills SHOULD use canonical
identifiers; skills using aliases remain valid but conformance tooling SHOULD
emit a warning.

## 6. Canonicalization

Before any comparison, matching, or verification, capability sets MUST be
canonicalized:

1. Resolve all aliases to canonical identifiers.
2. Normalize to lowercase.
3. Sort lexicographically.
4. Deduplicate.

Two capability sets are equal if and only if their canonical forms are identical.

## 7. Required vs Optional Capabilities

A skill's `capabilities` block contains two lists:

- `required`: capabilities the skill MUST have to execute at full fidelity.
  Absence of any required capability triggers degradation tier selection.
- `optional`: capabilities the skill MAY use if available but can operate
  without. Absence of optional capabilities does not trigger degradation;
  the skill simply omits the enhanced behavior.

Runtimes MUST evaluate required capabilities before invocation. Evaluation of
optional capabilities is RECOMMENDED but not REQUIRED.

## 8. Grounding Example

The reference skill `telegram-live-status` declares:

```yaml
capabilities:
  required:
    - shell.execute
  optional: []
```

This means the skill requires the `shell.execute` capability (Process/Shell
family) to invoke a CLI command. It has no optional capabilities. On a runtime
lacking `shell.execute`, the skill degrades per its degradation model (to
`report-only` or `reject`).
