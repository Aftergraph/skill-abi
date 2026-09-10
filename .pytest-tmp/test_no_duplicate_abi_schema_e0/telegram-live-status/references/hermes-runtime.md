# Hermes runtime binding for telegram-live-status

Canonical sender. The Hermes `telegram_status_cards` plugin owns card
rendering, edit-in-place state, duplicate suppression, and control buttons.
This file only records how to invoke it from each shell.

## WSL (Muse's shell on this host)

The `hermes` shim does NOT work in WSL (MSYS shebang). Call the Windows
venv binary with a Windows-style profile home:

```bash
export HERMES_HOME='C:\Users\empir\AppData\Local\hermes\profiles\avc'
HERMES_EXE=${HOME}/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe
"$HERMES_EXE" statuscard --to telegram:FIXTURE_USER_NAME --task <task> --event '{"task_id":"<task>","status":"running","producer":"Muse","phase":"<phase>","message":"what changed"}'
```

Muse sends always set `"producer":"Muse"` (identity line + card state key).
Task ids for Muse sends use the `muse-<session>/<task>` namespace.

## Native Hermes shell (Git Bash, Windows Terminal)

```bash
hermes statuscard --to telegram:FIXTURE_USER_NAME --task <task> --event '{"task_id":"<task>","status":"running","producer":"Muse","phase":"<phase>","message":"what changed"}'
```

The helper `tg-status.sh -t <task> -p 1/4 "message"` in the Hermes skill
does the same through the same plugin.

## Hermes-side internals (Hermes agents only)

Full card contract, V5 controls, gateway adapter, and state files live in
the Hermes `telegram-live-status` skill (avc profile). That skill is the
Hermes runtime adapter; this canonical skill stays runtime-neutral.
Change Hermes-side behavior there, never here.
