---
name: notify-dont-poll
description: >-
  Wait for a long job (a nornir-build chain, an image build, a re-import) without polling: start a host-side
  watcher that messages your Claude session once on the first failure or when the job is done, then stop. Use
  whenever you start a job that runs longer than a few minutes, instead of Monitor keepalives, ScheduleWakeup
  loops or periodic checks.
---

# Long jobs notify; sessions don't poll

Every session wake re-reads the whole conversation. A Monitor keepalive (30-minute cap) or a 2-hour poll costs dozens
of wakes a day. A watcher costs one small headless run per event: once on failure, once on completion (James, 2026-11-10).

## Procedure

1. Start the job so it writes a log (host-visible) and, ideally, prints a final marker line (`EXIT`, `LANE-DONE`).
2. Start ONE watcher on the **host** (it calls `claude` and reads host logs; it cannot run inside the build container):
   - Linux / macOS: `nornir-docker/agent/host-scripts/watch_job.sh` in tmux.
     `watch_job.sh [-m MARKER -n COUNT] [-s] [-t NOTE] "<session>" "<label>" "<done-check>"|- <log or 'glob'>...`
   - Windows: `nornir-docker/agent/host-scripts/Watch-Job.ps1` in its own console (PowerShell 7).
     `Watch-Job.ps1 -Session <name> -Label <label> -DoneCheck <command>|- [-Marker M -Count N] [-FromStart] [-Note text] -Logs <log or glob>...`
3. Stop. Do not keep a Monitor or ScheduleWakeup loop running for progress (at most one rare fallback).

## What the watcher does

- Checks every 60 s. Sends ONE message and exits:
  - on the first failure lines (`Traceback`, `FAILED`, `STOPPED`, `OCI runtime`, `Error response`, `No such container`,
    `Killed`, `MemoryError`) in any log: up to 3 lines, with file names;
  - when done: the done-check command succeeds, or MARKER lines across all logs reach COUNT (parallel lanes each print
    the marker when they finish; pass `-` as the done-check), with each log's last line and the `-Note`/`-t` next step.
- Logs may be files or quoted globs, re-expanded each pass, so lane logs created later are picked up.
- By default only lines written after the watcher starts count. `-s` / `-FromStart` scans whole files (fresh logs only;
  not for logs appended across runs).
- It sends through `notify_session.sh` / `Notify-Session.ps1`: a one-shot headless `claude -p` limited to
  SendMessage, ListAgents and ToolSearch. Calls are logged to `$NORNIR_NOTIFY_LOG`, else
  `<NORNIR_DOCKER_USER_ROOT>/Logs/nornir-build/notify.log`.
- Your session name is the one `ListAgents` shows for you.

## After starting

- When you next start work, check the watcher is alive (`tmux has-session -t watch-<label>`, or the console is open). If it
  died, failures go unnoticed.
- For a short wait inside a turn, an until-loop on a condition is fine. To wait for another session's job, ask that session
  to message you when it ends.
- The watcher reports failures only if they reach the log. A crash with no log line is not detected.

## Later (not built)

The pipelines could emit the completion or failure event themselves (MQTT run meta `status` going to completed or
failed), and one host watcher could turn those into notifications, so no per-job watcher is needed.
