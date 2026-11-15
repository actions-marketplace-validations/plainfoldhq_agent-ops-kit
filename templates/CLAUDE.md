# <Project name> ops

This repo is the memory of a scheduled Claude Code agent. Read MISSION.md for the rules; they override everything else.

## Every session
1. Read STATE.md, DECISIONS.md, and the tail of LEDGER.csv.
2. Apply the usage gate below before any work.
3. Do the next actions in STATE.md.
4. Before stopping: update STATE.md (and LEDGER.csv / DECISIONS.md if anything changed), commit, push to <branch>.

## Usage gate (apply before any work)
The GitHub Actions workflow `.github/workflows/usage-check.yml` runs the official Claude Code CLI (your own OAuth token in the repo secret CLAUDE_CODE_OAUTH_TOKEN) with a one-line prompt and commits `usage.json`: `{checked_at, five_hour_pct, weekly_pct, weekly_resets, status, error}`.
- To refresh on demand: write the current UTC time to `.github/usage-request`, commit, push, wait ~1-2 min, `git pull`, read usage.json. At most once per run.
- Fresh = checked_at under <2> hours old AND weekly_pct is not null. Otherwise unknown: do only the single smallest next action, no subagents, then stop.
- Never call model-provider usage endpoints directly with any token or cookie. Only the official CLI in the workflow reads usage.
- Hard stop (log one line in STATE.md, push, end): weekly_pct >= <90>, or five_hour_pct >= <70>.
- Weekly cap by day (<timezone>, week resets <day time>): <Sun N, Mon N, Tue N, Wed N, Thu N, Fri N, Sat N>. If weekly_pct >= cap: hard stop. If within 5 points of cap: light only.
- Your own interactive Claude use counts toward the same numbers. Back off when you are busy.
- Models: <main model> for main runs; a smaller model for routine subagent work (drafting, formatting, file checks).

## Facts
- <Brand / project name>. <Business contact address, not personal>.
- <Services and API bases the agent uses. Say where credentials live, e.g. "network secret injected by the proxy; never in the repo".>

## Never
- Commit secrets. Store personal data. Move money.
- <Project-specific prohibitions.>
