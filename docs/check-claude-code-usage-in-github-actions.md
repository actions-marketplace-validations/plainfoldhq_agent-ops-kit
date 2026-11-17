# How to check your Claude Code plan usage from GitHub Actions

You run Claude Code on a schedule (cloud routines, cron, CI) and want each run to know how much of your **5-hour** and **weekly** plan limits are already used, so it can back off before it hits them. This guide shows the approach the free kit uses: run the official Claude Code CLI once with a tiny prompt inside your own GitHub Actions job and read the rate-limit event it prints.

Not affiliated with or endorsed by Anthropic. "Claude" and "Claude Code" are Anthropic's trademarks.

## What you get

A `usage.json` file in your repo, plus step outputs if you use the action:

```json
{"checked_at": "2026-11-17T03:41:02Z", "five_hour_pct": 1.0, "weekly_pct": 5.0,
 "weekly_resets": "2026-11-22T19:00:00+00:00", "status": "allowed", "error": null}
```

## How it works

1. `claude -p "Reply with OK" --model haiku --max-turns 1 --output-format stream-json --verbose` runs with your token from a repo secret.
2. In stream-json mode the CLI emits a `rate_limit_event` line. Its `unifiedWindows` object carries `five_hour` and `seven_day` utilization (0-1) and reset times.
3. `scripts/parse_usage.py` keeps only those rate-limit fields and writes `usage.json`. If the event is missing or its shape changed, it writes nulls instead of guessing.

The check costs one one-line Haiku prompt from your own plan.

## Setup (about 5 minutes)

1. On your machine: `claude setup-token`. Add the token as the repo secret `CLAUDE_CODE_OAUTH_TOKEN` (Settings → Secrets and variables → Actions). Never commit it.
2. Either copy [`workflow/usage-check.yml`](../workflow/usage-check.yml) and [`scripts/parse_usage.py`](../scripts/parse_usage.py) into your repo, or use the action:

```yaml
name: usage-check
on:
  workflow_dispatch:
  push:
    branches: [main]
    paths: [".github/usage-request"]
permissions:
  contents: write
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - id: usage
        uses: plainfoldhq/agent-ops-kit@v1
        with:
          oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          max-weekly-pct: "90"
          max-five-hour-pct: "80"
      - run: echo "weekly=${{ steps.usage.outputs.weekly-pct }} ok=${{ steps.usage.outputs.ok }}"
```

The full version that commits `usage.json` is [`workflow/usage-check-action-example.yml`](../workflow/usage-check-action-example.yml).

3. Run it once by hand (Actions → usage-check → Run workflow) and look at `usage.json`.

## Reading it from your agent

Tell the agent (in `CLAUDE.md`) to treat the numbers as fresh only if `checked_at` is recent and `weekly_pct` is not null, and to stop at fixed lines, for example:

- stop when `five_hour_pct >= 80`;
- stop when `weekly_pct` reaches the day's cumulative cap (spread the week: about 14 points per day);
- if the data is stale and a refresh fails twice, do a few more steps, save, and stop.

[`templates/CLAUDE.md`](../templates/CLAUDE.md) has these rules as fill-in-the-blanks.

## On-demand refresh

GitHub's scheduled workflows often start late (see [cron delays](github-actions-schedule-delays.md)), so the agent asks for fresh numbers itself: it writes the current UTC time to `.github/usage-request`, commits and pushes. The `push` trigger with that `paths` filter runs the check, which commits `usage.json` back, typically within a minute or two. The agent then `git pull`s and reads it.

## What not to do

Do not call usage endpoints directly with your OAuth token or browser cookies. Anthropic's consumer terms do not allow that; this method only uses the official CLI with your own token in your own job.

## Related

- [Durable memory for scheduled Claude Code agents](scheduled-agent-memory-in-git.md)
- Pro pack ($19): local HEAVY/LIGHT/STOP gate script, refresh helper, routine prompt templates and a full setup guide. [Details in the README](../README.md#pro-pack-19-one-time).
