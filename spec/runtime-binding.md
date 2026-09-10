# SABI v0.1 — Runtime Binding (B)

## 1. Purpose

The runtime binding model B defines how a skill's abstract capability
declarations (C) and effect bounds (E) map to concrete operations in a
specific runtime environment. A skill is portable across runtimes only
when each target runtime has an explicit binding that resolves every
required capability to a verifiable implementation.

## 2. Abstract-to-Concrete Binding

A capability identifier (e.g., `shell.execute`, `filesystem.read`) is
an abstract token defined in the capability vocabulary C. A binding
maps each such token to a concrete mechanism available in a named
runtime.

### 2.1 Binding Resolution Order

When a runtime loads a skill, it resolves capabilities in the following
order:

1. **Explicit binding file**: a YAML document under `bindings/` whose
   `runtime` field matches the current runtime identifier exactly.
2. **Minimal binding**: a fallback binding file that declares a subset
   of capabilities, enabling degraded operation via D.
3. **No binding**: if no binding file matches and no minimal binding
   covers the required capabilities for any non-terminal tier, the
   resolver MUST select the terminal degradation tier.

Resolution MUST be deterministic. The runtime MUST NOT guess
implementations from capability names or invoke LLM reasoning to infer
a mapping.

### 2.2 Partial Bindings

A binding MAY cover only a subset of the skill's declared capabilities.
When a partial binding is used, the resolver computes the available
capability set R_caps as the intersection of the binding's declared
implementations and the skill's required capabilities. This reduced
R_caps feeds into the degradation model's max-tier selection.

## 3. Binding Record Shape

Each binding is a YAML document with the following normative fields:

- **runtime** (string, required): unique identifier for the target
  runtime (e.g., `hermes-wsl`, `read-only-session`).
- **description** (string, required): human-readable summary of what
  this binding provides and any known limitations.
- **capabilities** (list of strings, required): the capability
  identifiers from C that this binding implements.
- **implementations** (map, required): key-value pairs where each key
  is a capability identifier present in `capabilities` and each value
  is a string describing the concrete mechanism (e.g., a binary name,
  an API endpoint, a function reference).

Additional fields MAY be present but MUST NOT alter the resolution
semantics defined here.

## 4. Failure Semantics

1. If a binding declares an implementation for a capability but the
   runtime cannot execute it (missing binary, denied permission), the
   capability is treated as unavailable. The resolver recomputes T*
   without that capability.
2. A binding MUST NOT declare a capability it does not actually provide.
   Declaring a false capability is a conformance violation detectable at
   P4/RUNTIME_TESTED.
3. If no binding exists for the current runtime, the skill MUST resolve
   to the terminal tier. Silent assumption of default behaviors is
   prohibited.
4. Binding files are part of the machine-readable contract. Changes to
   binding targets, capability coverage, or implementation mechanisms
   constitute a version change under versioning.md.
