# Durable memory for scheduled Claude Code agents: plain files in git

A scheduled Claude Code run (cloud routine, cron job, CI job) usually starts in a fresh container with no memory of earlier runs. The simplest memory that works across sessions, machines and models is a private git repo with a few plain-text files the agent reads at the start and updates before it stops.

## The files

| File | What goes in it | Rule of thumb |
|---|---|---|
| `CLAUDE.md` | The session checklist: what to read, the usage gate, when to stop | Short and stable; Claude Code loads it automatically |
| `MISSION.md` | Goal and hard rules (law, privacy, honesty, platform terms, spending, when to contact you) | Rules in priority order; they override the prompt |
| `STATE.md` | Current projects, metrics, next actions, blockers, a one-line run log | The agent rewrites it every run; keep it small |
| `DECISIONS.md` | Every launch, pivot, kill or rule change, with the reason | Append-only, dated |
| `LEDGER.csv` | Every money movement: `date,amount,account,venture,description` | Append-only; never secrets or buyer data |

Templates for all five are in [`templates/`](../templates/).

## The loop each run follows

1. Clone or pull the repo. Read `CLAUDE.md`, `MISSION.md`, `STATE.md`, `DECISIONS.md`, and the tail of `LEDGER.csv`.
2. Apply the usage gate (see [usage check](check-claude-code-usage-in-github-actions.md)). If it says stop, write one run-log line, push, end.
3. Do the next actions in `STATE.md`, committing and pushing after each finished piece, not only at the end. A run can be cut off at any time.
4. Before stopping, update `STATE.md` (next actions, blockers, run-log line with usage at start and end) and push.

## Why this works better than a long prompt

- **The prompt stays fixed.** The scheduled task's prompt only says "read CLAUDE.md and follow it". You change behavior by editing files, with history.
- **Auditable.** `git log` shows what each run did and why. You can revert a bad run.
- **Model- and machine-independent.** Any session that can clone the repo picks up where the last one stopped.
- **No extra hosting.** No database, no vector store, no server.

## Practical tips

- Put secrets in your platform's secret store (repo secrets, environment network secrets), never in these files. Scan before pushing anything public.
- Write "Operator requests" into `STATE.md` and have the agent batch them, so you get one clear message a week instead of many pings.
- Cap the run log: keep the last few weeks in `STATE.md`, move older lines elsewhere.
- Add a "never redo finished work" rule, and have the agent check `DECISIONS.md` and a `research/` folder before researching anything again.

The pro pack ($19) adds routine prompt templates, a weekly report generator, state-trimming and run-log lint scripts. [See the README](../README.md#pro-pack-19-one-time).
