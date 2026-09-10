# SABI v0.1 Spec — Writing Plan

Goal: normative, self-contained spec for the Skill ABI (SABI) under `spec/` only.
No code, schemas, tests, or CLI in this pass. LF endings, no TODOs.

## Deliverables (in write order)

1. `spec/SABI-v0.1.md` — root document: scope, core invariant
   (Portable != Parseable), skill tuple S=<I,O,C,E,D,V>, non-goals,
   document map, conformance-level overview.
2. `spec/terminology.md` — normative terms (MUST/SHOULD/MAY, skill,
   runtime, binding, capability, effect, degradation, attestation,
   portability vs parseability).
3. `spec/capability-model.md` — C: versioned capability vocabulary
   (the nine families), capability identifiers, versioning of
   capabilities themselves, overlap and alias rules, canonicalization.
4. `spec/effect-model.md` — E: quantified effect bounds; declared
   authority != permitted authority; bound dimensions (reversibility,
   scope, external visibility); enforcement responsibility.
5. `spec/degradation-model.md` — D: deterministic degradation tiers,
   max-tier selection, partial order over capability/effect loss,
   determinism requirement (same input, same environment ⇒ same tier).
6. `spec/runtime-binding.md` — B: how a skill binds capabilities and
   effects to a concrete runtime; binding record shape (normative
   fields, prose-level), binding resolution order, failure semantics.
7. `spec/verification-model.md` — V: what each verification stage
   proves (static, runtime, multi-runtime, attestation), evidence
   requirements, what must NOT be conflated.
8. `spec/conformance.md` — exact level names and requirements:
   P0/INVALID, P1/SPEC_VALID, P2/EFFECT_AWARE,
   P3/DEGRADATION_CONFORMANT, P4/RUNTIME_TESTED,
   P4M/MULTI_RUNTIME_TESTED, P5/ATTESTED.
9. `spec/versioning.md` — SABI spec versioning rules: PATCH/MINOR/MAJOR
   semantics, compatibility direction, deprecation.

## Fixed decisions (from task context, non-negotiable)

- Core invariant: **Portable != Parseable.** Parseability is necessary
  but never sufficient for portability; portability requires verified
  behavior under E, D, and V.
- Level name fix: the old "P4-static" ambiguity is removed. Static
  checks cap at P1 (+P2/P3 static conformance of E/D declarations);
  P4 requires real runtime tests; P4M requires ≥2 runtimes; P5
  requires signed attestation. static != runtime != multi != signed.
- Capability vocabulary families: filesystem, process/shell,
  web/network, git/repository, database, test/ci,
  artifact/deployment, message, user/agent.
- Reference implementations for grounding (read-only):
  `~/.agents/skills/telegram-live-status`, `~/.agents/skills/release-draft`.

## Grounding step before writing prose

Read the two reference skill directories to align field names and
structure with existing practice (skill.abi.yaml, effects.yaml,
degradation.yaml, bindings/, conformance/, attestations/).

## Constraints

- Only write under `C:/Users/empir/workspace/skill-abi/spec/`.
- Do not touch src/, cli/, schemas/, tests/, or any other repo.
- Every doc self-contained enough to be read with only terminology.md
  + SABI-v0.1.md as prerequisites. No TODOs, no dangling placeholders.
