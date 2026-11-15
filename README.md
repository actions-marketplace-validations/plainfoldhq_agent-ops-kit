# Agent-ops kit for Claude Code scheduled agents

A small, file-based memory and usage-gate setup for Claude Code agents that run on a schedule (for example, cloud routines). The agent keeps its state in plain Markdown/CSV files in a git repo and checks your plan usage before doing any work, so unattended runs back off instead of eating your limits.

Made by Plainfold. Not affiliated with or endorsed by Anthropic. "Claude" and "Claude Code" are Anthropic's trademarks, used here only to describe what this works with.

## What's in it
| Path | Purpose |
|---|---|
| `templates/CLAUDE.md` | Session checklist + usage-gate rules the agent follows every run |
| `templates/MISSION.md` | Hard-rules skeleton (law, privacy, honesty, platform terms, spending, operator contact) |
| `templates/STATE.md`, `DECISIONS.md`, `LEDGER.csv` | Memory files: current state, decision log, transaction log |
| `workflow/usage-check.yml` | GitHub Actions job (copy to `.github/workflows/` in your repo) that runs the official Claude Code CLI with a one-line Haiku prompt and commits `usage.json` |
| `scripts/parse_usage.py` | Turns the CLI's `rate_limit_event` output into `usage.json` (rate-limit fields only) |

## Setup (5 steps)
1. Create a **private** repo for the agent's memory. Copy `templates/*` to its root, `scripts/` too, and `workflow/usage-check.yml` to `.github/workflows/usage-check.yml`.
2. Fill in the `<placeholders>` in `CLAUDE.md` and `MISSION.md` (timezone, caps, branch, rules).
3. On your machine run `claude setup-token`, then add the token as the repo secret `CLAUDE_CODE_OAUTH_TOKEN` (Settings → Secrets and variables → Actions). Never commit it.
4. Edit the cron line(s) in `.github/workflows/usage-check.yml` to run 30-90 minutes before your agent runs (UTC). Run the workflow once by hand (Actions → usage-check → Run workflow) and check `usage.json`.
5. Point your scheduled agent at the repo with a prompt like: "Clone <owner>/<repo>, read CLAUDE.md and follow it. Apply the usage gate first."

## How the usage gate works
- The workflow writes `usage.json`: `checked_at`, `five_hour_pct`, `weekly_pct`, `weekly_resets`, `status`, `error`.
- The agent treats data as fresh only if `checked_at` is under ~2 hours old and `weekly_pct` is not null. Otherwise it does only the smallest next step.
- **On-demand refresh:** the agent writes the current UTC time to `.github/usage-request` and pushes; the workflow runs on that push and commits fresh numbers in about 15-60 seconds.
- Hard stops and per-day caps live in `CLAUDE.md`, so a week's budget is spread out.

## Limits (read these)
- GitHub's scheduled crons are often late (we have seen 7+ hours) or skipped. Treat the on-demand refresh as the normal path.
- Each check spends one tiny Haiku prompt from your own plan.
- Usage numbers come from the CLI's rate-limit event. Its shape may change between CLI versions; the parser writes nulls (→ "unknown") rather than guessing.
- This kit only reads usage through the official CLI. Do not call usage endpoints directly with OAuth tokens or browser cookies; that is against Anthropic's consumer terms.
- Your own interactive Claude use counts toward the same limits.

## Pro pack
Routine prompt templates, a weekly report generator, a state-file trimmer and run-log linter, a local usage-gate script with on-demand refresh, and a setup guide: https://polar.sh/plainfold

## License
MIT. See `LICENSE`. Provided as is, without warranty.
