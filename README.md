# Agent-ops kit for Claude Code scheduled agents

A small, file-based memory and usage-gate setup for Claude Code agents that run on a schedule (for example, cloud routines). The agent keeps its state in plain Markdown/CSV files in a git repo and checks your plan usage before doing any work, so unattended runs back off instead of eating your limits.

Use it if you want to:
- run Claude Code on a schedule (cloud routines, cron, GitHub Actions) without blowing through your 5-hour or weekly plan limits;
- read your Claude Code usage (`five_hour` and `seven_day` utilization) from a GitHub Actions job instead of guessing;
- give an unattended agent a durable memory (state, decisions, ledger) that survives between sessions.

Example `usage.json` written by the workflow:

```json
{"checked_at": "2026-11-16T08:51:15Z", "five_hour_pct": 10.0, "weekly_pct": 1.0,
 "weekly_resets": "2026-11-22T19:00:00+00:00", "status": "allowed", "error": null}
```

Made by Plainfold. Not affiliated with or endorsed by Anthropic. "Claude" and "Claude Code" are Anthropic's trademarks, used here only to describe what this works with.

## Guides
- [Check your Claude Code plan usage from GitHub Actions](docs/check-claude-code-usage-in-github-actions.md) (5-hour and weekly limits, on-demand refresh)
- [GitHub Actions `schedule` runs late: how a scheduled agent copes](docs/github-actions-schedule-delays.md)
- [Durable memory for scheduled Claude Code agents: plain files in git](docs/scheduled-agent-memory-in-git.md)

## What's in it
| Path | Purpose |
|---|---|
| `templates/CLAUDE.md` | Session checklist + usage-gate rules the agent follows every run |
| `templates/MISSION.md` | Hard-rules skeleton (law, privacy, honesty, platform terms, spending, operator contact) |
| `templates/STATE.md`, `DECISIONS.md`, `LEDGER.csv` | Memory files: current state, decision log, transaction log |
| `workflow/usage-check.yml` | GitHub Actions job (copy to `.github/workflows/` in your repo) that runs the official Claude Code CLI with a one-line Haiku prompt and commits `usage.json` |
| `action.yml`, `scripts/action_outputs.py` | The same check as a reusable GitHub Action with outputs and optional thresholds |
| `scripts/parse_usage.py` | Turns the CLI's `rate_limit_event` output into `usage.json` (rate-limit fields only) |
| `late-run-guard/action.yml`, `scripts/late_run.py` | Action that reports how late a scheduled run started (no token needed) |
| `docs/` | Guides (usage check, schedule delays, file-based memory) |

## Setup (5 steps)
1. Create a **private** repo for the agent's memory. Copy `templates/*` to its root, `scripts/` too, and `workflow/usage-check.yml` to `.github/workflows/usage-check.yml`.
2. Fill in the `<placeholders>` in `CLAUDE.md` and `MISSION.md` (timezone, caps, branch, rules).
3. On your machine run `claude setup-token`, then add the token as the repo secret `CLAUDE_CODE_OAUTH_TOKEN` (Settings → Secrets and variables → Actions). Never commit it.
4. Edit the cron line(s) in `.github/workflows/usage-check.yml` to run 30-90 minutes before your agent runs (UTC). Run the workflow once by hand (Actions → usage-check → Run workflow) and check `usage.json`.
5. Point your scheduled agent at the repo with a prompt like: "Clone <owner>/<repo>, read CLAUDE.md and follow it. Apply the usage gate first."

## Use it as a GitHub Action
The usage check is also packaged as a composite action (`action.yml` in this repo):

```yaml
- id: usage
  uses: plainfoldhq/agent-ops-kit@v1
  with:
    oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    output-file: usage.json      # default
    max-weekly-pct: "90"         # optional: ok=false at/above this
    max-five-hour-pct: "80"      # optional
- if: steps.usage.outputs.ok != 'true'
  run: echo "Over budget, skipping" && exit 0
```

Outputs: `five-hour-pct`, `weekly-pct`, `weekly-resets`, `status`, `ok`. It writes the file but does not commit it; see `workflow/usage-check-action-example.yml` for a full workflow that commits `usage.json`. Tested on GitHub-hosted `ubuntu-latest`.

## Late-run guard for scheduled workflows
GitHub often starts `on: schedule` runs late (hours, at busy times). This second action tells you how late the current run is, so a job that only makes sense near its time can skip itself:

```yaml
on:
  schedule:
    - cron: "5 2 * * *"
jobs:
  nightly:
    runs-on: ubuntu-latest
    steps:
      - id: late
        uses: plainfoldhq/agent-ops-kit/late-run-guard@v1
        with:
          max-late-minutes: "90"
      - if: steps.late.outputs.ok != 'true'
        run: echo "Started ${{ steps.late.outputs.late-minutes }} min late, skipping" && exit 0
```

Outputs: `scheduled-for`, `late-minutes`, `is-scheduled`, `ok`. It reads the triggering cron from `github.event.schedule` (or the `cron` input), needs no token, and treats manual and push runs as on time. Standard-library Python, tested (`python3 -m unittest tests/test_late_run.py`). Background: [schedule delays guide](docs/github-actions-schedule-delays.md).

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

## FAQ
**Can a cloud session read my plan usage directly?** Not through any supported API we know of. This kit uses the official CLI's `rate_limit_event` inside your own GitHub Actions job instead.

**Does the check cost usage?** One one-line Haiku prompt per check.

**Why files in git instead of a database?** Any session that can clone the repo can read and update its memory, the history is auditable, and nothing extra has to be hosted.

## Pro pack ($19 one-time)
- 4 routine prompt templates: weekday light run, weekend heavy run, work-block run (keep working until a usage or time limit), setup/test run
- `weekly_report.py`: builds a short REPORT.md from LEDGER.csv, STATE.md and usage.json
- `trim_state.py` and `lint_runlog.py`: keep STATE.md small and the run log consistent
- `usage_gate.py` + `request_refresh.sh`: a local HEAVY/LIGHT/STOP/UNKNOWN gate with on-demand refresh; fixed per-weekday caps or cumulative pacing from the weekly reset time; optional run clock; unit tests
- `SETUP-GUIDE.md`: cloud environment, network secrets, repo secret, operator-request batching, known gotchas

[Buy the pro pack on Polar](https://buy.polar.sh/polar_cl_HkC1kUZmcpRbovskrQSPqrWmpFi8Gqbau5vEI3HOoVV) (merchant of record; handles sales tax). Python 3.9+ standard library, bash, git.

## License
MIT. See `LICENSE`. Provided as is, without warranty.
