# Agent Skills specification compatibility

SABI is an **extension** of the Agent Skills specification, not a fork.
This document records the external oracle SABI is checked against and
every place the base spec and SABI's implementation interact. **Where the
spec and SABI disagree, the spec wins.**

## External oracle

| Item | Value |
| --- | --- |
| Specification | Agent Skills — Specification |
| URL | https://agentskills.io/specification |
| Accessed | 2026-09-10 (UTC) |
| Reference validator | `skills-ref` (PyPI package `skills-ref`), version **0.1.1** |
| Validator source | https://github.com/agentskills/agentskills (`skills-ref`) |
| Validator command | `agentskills validate <skill-dir>` (console script from `skills_ref.cli:main`) |

The published spec was fetched live (not recalled from memory); the
requirements below are transcribed from that fetch and cross-checked
against the reference validator's source (`skills_ref/validator.py`).

## Base spec requirements (SKILL.md)

- A skill is a directory containing, at minimum, `SKILL.md`.
- `SKILL.md` must contain YAML frontmatter followed by Markdown content.
- `name` (required): 1–64 characters, lowercase letters/numbers/hyphens
  only, must not start or end with a hyphen, no consecutive hyphens, and
  must match the parent directory name.
- `description` (required): 1–1024 characters, non-empty.
- `license` (optional): license name or reference to a bundled license file.
- `compatibility` (optional): max 500 characters.
- `metadata` (optional): a map from string keys to string values.
- `allowed-tools` (optional, experimental): space-separated string of
  pre-approved tools.
- Optional directories: `scripts/`, `references/`, `assets/`.

## Divergences found and fixed

SABI previously validated only "non-empty `name`", "non-empty
`description`", and name == directory. It accepted frontmatter the spec
rejects. The spec wins, so the following are now enforced in
`src/sabi/agentskills.py` and wired into the P0 gate in
`src/sabi/validator.py`:

| # | Spec rule | Before (SABI) | After (spec wins) |
| --- | --- | --- | --- |
| 1 | `name` ≤ 64 chars | unchecked | rejected |
| 2 | `name` lowercase only | unchecked | rejected |
| 3 | `name` no leading/trailing hyphen | unchecked | rejected |
| 4 | `name` no consecutive hyphens | unchecked | rejected |
| 5 | `name` letters/numbers/hyphens only | unchecked | rejected |
| 6 | `description` ≤ 1024 chars | unchecked | rejected |
| 7 | `compatibility` ≤ 500 chars, string | unchecked | rejected |
| 8 | `metadata` string→string map | unchecked | rejected |
| 9 | `allowed-tools` is a string (experimental) | unchecked | rejected on wrong type |
| 10 | `scripts/`, `references/`, `assets/` are directories | unchecked | rejected when present as a non-directory |
| 11 | `license` is a non-empty string | unchecked | rejected |

Supporting changes:

- `src/sabi/schema.py` gained `maxLength` support (it already handled
  `minLength`/`pattern`), so the JSON schema can express the spec limits.
- `schemas/skill-md.schema.json` now encodes the spec constraints
  (`name` ≤ 64 with the no-leading/trailing/consecutive-hyphen pattern,
  `description` ≤ 1024, `compatibility` ≤ 500, string `metadata` values).

## Intentional, documented differences from the reference validator

These are deliberate; they do **not** loosen any rule the spec states.

1. **Extra frontmatter keys are permitted.** SABI is an extension, so it
   accepts additional keys (its own extension namespace) where the
   reference validator rejects any key outside
   `{name, description, license, compatibility, metadata, allowed-tools}`.
   The spec-defined fields are still validated strictly. Example:
   `examples/telegram-live-status/SKILL.md` carries a `metadata.protocol`
   key; SABI accepts it.
2. **Stricter on a stated spec rule.** For `metadata` the reference
   validator coerces non-string values to strings, whereas the spec says
   "a map from string keys to string values"; SABI enforces the spec text.

## Reference-validator run (external oracle)

```
$ agentskills validate examples/telegram-live-status
Valid skill: examples/telegram-live-status
```

- `skills-ref` **0.1.1**, run 2026-09-10.
- Result: **PASS** — the SABI example is accepted by the official validator.
