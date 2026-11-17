# GitHub Actions `schedule` runs late: how to make a scheduled agent cope

If your workflow uses `on: schedule` and you expected it at 02:05 UTC but it ran hours later (or not at all), that is normal GitHub behavior, not a bug in your cron line. GitHub documents that scheduled runs can be delayed during high load, and that the top of the hour is busiest. Many users report delays of several hours.

What we saw while running a scheduled agent for a week (one repo, `ubuntu-latest`):

| Cron (UTC) | Observed |
|---|---|
| `5 2 * * *` | fired about 7 hours late once; on other nights had not fired 90+ minutes after its time |
| a second cron at `47 2 * * *` | also had not fired by the time the agent needed it |
| `push` trigger on a path | ran within about 15-60 seconds every time |

## The fix: don't depend on the schedule

1. Keep the cron if you like, but treat it as a bonus.
2. Add a `push` trigger with a `paths` filter on a small request file:

```yaml
on:
  schedule:
    - cron: "5 2 * * *"
  workflow_dispatch:
  push:
    branches: [main]
    paths: [".github/usage-request"]
```

3. The consumer (your agent, a script, another job) writes a timestamp to `.github/usage-request`, commits, pushes, waits a minute or two, pulls, and reads the result.
4. Always store a `checked_at` timestamp in the output, and make consumers check its age instead of assuming the cron ran.

Tips:
- Pick odd minutes (`:05`, `:47`), not `:00`.
- Scheduled workflows run only on the default branch, and GitHub disables them in public repos after 60 days without repository activity.
- Use `concurrency:` so a manual run and a push run don't commit over each other.

If a job only makes sense close to its time, skip late runs with the kit's late-run guard:

```yaml
- id: late
  uses: plainfoldhq/agent-ops-kit/late-run-guard@v1
  with:
    max-late-minutes: "90"
- if: steps.late.outputs.ok != 'true'
  run: echo "Too late (${{ steps.late.outputs.late-minutes }} min), skipping" && exit 0
```

The usage check in this kit uses the same push-trigger pattern; see [checking Claude Code usage from GitHub Actions](check-claude-code-usage-in-github-actions.md).
