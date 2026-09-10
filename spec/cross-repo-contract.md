# Cross-repo contract — SABI requirement-object export

## Invariant

**SABI says WHAT must remain true. Runtime decides WHERE/HOW. Trust
decides WHETHER.**

A requirement object answers what must remain true about a skill. It
never decides how a runtime binds to the skill (the runtime's job) or
whether the runtime is trusted (the trust plane's job). This invariant
is normative: any consumer that conflates these planes produces an
invalid portability claim.

## Requirement object (`sabi/requirement-object/v0.1`)

Exported by `src/sabi/api.py::export_requirement_object(skill_dir)`.

| Field | Type | Source |
|---|---|---|
| `schema` | string | `sabi/requirement-object/v0.1` |
| `skill` | string | `SKILL.md` frontmatter `name` |
| `version` | string | `SKILL.md` frontmatter `metadata.version` |
| `spec` | string | `skill.abi.yaml` `spec` |
| `digests.skill_md` | string | sha256 hex of `SKILL.md` |
| `digests.abi` | string | sha256 hex of `skill.abi.yaml` |
| `required_capabilities` | string[] | `skill.abi.yaml` `capabilities.required` |
| `optional_capabilities` | string[] | `skill.abi.yaml` `capabilities.optional` |
| `effect_envelope` | object | `effects.yaml` `effects` block |
| `degradation_tiers` | string[] | `degradation.yaml` tier keys, declaration order |
| `verification_obligations` | string[] | `skill.abi.yaml` `verification.required` |

## Consumer rules

1. **Requirement objects are DERIVED data.** The skill-abi repository is
   the only source of truth. A vault, registry, or benchmark may cache
   or distribute a requirement object but MUST re-export from the skill
   directory before acting on it. No consumer may author, edit, or
   substitute a requirement object and present it as SABI truth.
2. **Digests pin `SKILL.md` + `skill.abi.yaml`.** The requirement object
   carries sha256 digests of these two files. A consumer MUST verify
   that the digests match the stored skill bytes before relying on the
   requirement object. Other files (effects, degradation, verification)
   are contractually present but their digests are not in the
   requirement object — the lockfile covers the full set.
3. **`degradation_tiers` order is normative.** The declaration order in
   `degradation.yaml` defines the resolution order. The requirement
   object preserves this order.
4. **Additive-only evolution until `sabi/v0.2`.** No field may be
   removed or have its type changed. New fields may be added with a
   new schema id. Consumers MUST ignore unknown fields.
5. **Canonical JSON (sorted keys, compact) is the digest form.**
   `requirement_object_bytes()` produces the byte-exact form that is
   stable across exports. Pretty-printed JSON is for human inspection
   only and must not be digested.
