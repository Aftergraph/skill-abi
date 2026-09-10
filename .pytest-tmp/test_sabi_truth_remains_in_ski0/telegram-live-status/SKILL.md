---
name: telegram-live-status
description: Use when long-running work needs live Telegram status updates for FIXTURE_USER_NAME.
metadata:
  protocol: "universal-skill/1"
  version: "1.0.0"
---

# Telegram Live Status

## Purpose

Keep FIXTURE_USER_NAME informed during long-running work with one editable Telegram
status card per task, updated at meaningful transitions.

## When to use

Use this skill when:

- implementation, migration, or verification work runs long enough that FIXTURE_USER_NAME expects live progress
- a milestone is reached, a warning or failure occurs, or the work completes

Do not use it for:

- conversational replies
- long logs or arbitrary announcements

## Inputs

Required:

- task id, stable for the full lifecycle of one task
- message text describing the latest outcome

Optional (all render on the card — use them; thin cards help no one):

- progress as `current`/`total` (renders N/M plus a progress bar)
- `phase` label (one short line under the status)
- `detail` (evidence: what was verified, IDs, counts)
- `next_step` (what happens next, or what FIXTURE_USER_NAME must decide)
- status: INFO, RUNNING, WAITING, WARN, FAIL, COMPLETE

## Required capabilities

Required:

- shell.execute

Use the runtime's equivalent shell capability when the preferred name differs.
Do not depend on proprietary tool names.

## Procedure

1. Pick one stable task id per task and reuse it for every update of that
   task. Format: lowercase `muse-<session>/<task>` (letters, digits,
   hyphen) so Muse cards are recognizable; never reuse one id for two
   tasks. Every event sets `"producer":"Muse"`, which renders a Muse
   identity line on the card and keys card state — use it on all sends
   for the task, never mix producers on one task.
2. Send the initial card when the task starts, with `phase` and a message
   stating what is starting and why.
3. Update the same card only at transitions: start, milestone reached,
   warning or failure, completion. Never per log line; at most one update
   per milestone.
4. Make every update informative: outcome first, then evidence. Milestones
   carry `current`/`total` and `phase`; completion carries proof in
   `detail` and the next move in `next_step`. A card with only a status
   word is a failed card.
5. Keep the card scannable. Never put secrets in card text.
6. Verify delivery (sender exit zero AND a returned message id) before
   reporting the outcome.

## Runtime bindings

The agent MUST use whichever binding works in the current runtime:

- WSL on FIXTURE_USER_NAME's Windows host (verified): call the Windows Hermes binary
  with a Windows-style profile home. See `references/hermes-runtime.md`.
- Native Hermes shell (Git Bash, Windows): `hermes statuscard --to telegram:FIXTURE_USER_NAME`.
  See `references/hermes-runtime.md`.

Do not invent another send mechanism. If no binding works in the current
runtime, report BLOCKED and name the missing capability.

## Verification

The task is complete only when:

- the sender command exits successfully
- a message id is returned for the card

Do not send live test cards unless the task explicitly asks for a Telegram message.

## Failure handling

- SUCCESS: card created or updated, delivery verified.
- PARTIAL: useful updates sent, but later updates remain.
- BLOCKED: no working runtime binding; report the missing capability.

Never report SUCCESS merely because commands ran without checking delivery.

## Red flags — STOP and do not claim delivery

- Sender exited zero but no message id was returned.
- "The command ran, so FIXTURE_USER_NAME was informed."
- One task id reused for two different tasks.
- Card updated per log line instead of per transition.
- Any secret (token, key, password) in card text.

All of these mean: no SUCCESS. Fix the gap, re-verify, then report.

## Output

Return:

- result (SUCCESS, PARTIAL, or BLOCKED)
- evidence (message id when available)
- deviations
- blockers

## References

Read only when relevant:

- `references/receiver.json` — receiver record for FIXTURE_USER_NAME (secret-free).
- `references/hermes-runtime.md` — exact Hermes invocations and where the
  Hermes-side card internals live. Read when a binding fails or when
  Hermes-side behavior must change.

## Machine contract (SABI P3)

`skill.abi.yaml`, `effects.yaml`, `degradation.yaml`, `schemas/`, and
`skill.lock` form the machine-readable semantic contract. Read them when
binding this skill to a new runtime or auditing what authority it may
consume. Validate with `scripts/sabi-validate.py` (`test --matrix` runs
all runtime bindings; `test --certify` writes `attestations/portability.json`;
`bench <skills-root>` runs the cross-skill fallback battery).
