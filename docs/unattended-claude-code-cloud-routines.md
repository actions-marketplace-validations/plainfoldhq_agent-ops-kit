# Unattended Claude Code cloud routines: failure modes we hit and the fixes

A cloud routine (a scheduled Claude Code session in a cloud environment) behaves differently from a session you sit in front of. Nobody answers prompts, the container is thrown away afterwards, and the network is filtered. These are the problems we actually ran into during the first two weeks of running a scheduled agent every night, and what fixed each one. Your setup may differ; settings and product behavior change, so check the current Claude Code docs too.

## 1. "CONNECT tunnel failed, response 403" from curl or an SDK
**What it means:** the session's egress proxy refused the host. The request never left the container, so any network secret (API key) the environment holds for that host was never added.

**Fix:** add the exact host (for example `api.example.com`) to the network allowlist of the environment the routine runs in. A routine created from a different place may run in a different environment than the one you edited, so confirm which environment the scheduled task uses. After a change, start a fresh session to test; a task that re-fires into an old session may keep the old container.

## 2. Web fetches that need approval silently fail
In an interactive session a new domain triggers a permission prompt. In an unattended run nobody answers it, and the fetch fails (we saw "the user did not answer an earlier permission request in time"). Redirects to another host count as a new domain.

**Fix:** fetch the final URL directly (not a docs URL that redirects elsewhere), or have a person approve the domain once in an interactive session, or paste the page into the repo. Do not route around the prompt with mirrors.

## 3. Work lost when the container is reclaimed
The container is ephemeral. Anything not committed and pushed is gone.

**Fix:** commit and push after each finished piece of work, not only at the end, and keep all state in files in the repo (see the [memory guide](scheduled-agent-memory-in-git.md)). Make the first step of every run `git pull`, because a later firing can land in a session that already has an older clone.

## 4. The session cannot do some GitHub things
What we observed from cloud sessions (through the session's GitHub access):
- It could not create repositories. A person has to create an empty repo once; after that the session could push to it.
- Pushing tags and deleting branches were refused. For an action's stable ref we use a `v1` branch and fast-forward it, instead of a `v1` tag.
- Repos outside the ones attached to the session were refused until attached.

**Fix:** batch the one-minute human steps (create repo, publish a release) into one request, and design around branches instead of tags.

## 5. `on: schedule` workflows run late
If the routine depends on a GitHub Actions cron (for example a usage check), expect it to be hours late. Use a `push`-triggered refresh instead. Details: [schedule delays guide](github-actions-schedule-delays.md) and the [late-run guard action](../late-run-guard/action.yml).

## 6. The routine eats the limits you need yourself
Your own interactive Claude use and the routine share the same 5-hour and weekly limits.

**Fix:** have the routine read current usage before it works and back off when you are busy (for example, end the run if the 5-hour window is already above 70%). See [usage check from GitHub Actions](check-claude-code-usage-in-github-actions.md) and [weekly pacing](pace-claude-code-weekly-usage.md).

## 7. Some APIs reject the default Python User-Agent
One API behind Cloudflare answered `error code: 1010` to Python's default `urllib` User-Agent. A plain descriptive User-Agent (for example `my-agent/1.0`) fixed it. Do not put personal details in it.

## 8. Secrets in the repo
Never commit tokens. Put API keys in the environment's network secrets (the proxy adds them to requests) and the Claude Code OAuth token for the usage check in a GitHub Actions repo secret. The agent never needs to see either value.

## Checklist for a new routine
- [ ] The scheduled task runs in the environment that has the allowlist and secrets.
- [ ] Every host the run needs is on the allowlist; tested from a fresh session.
- [ ] First step: `git pull`; read the memory files.
- [ ] Usage gate before work; stop lines for the 5-hour and weekly limits.
- [ ] Commit and push after each piece of work.
- [ ] Human-only steps go into one batched request file, not into chat.

The free kit in this repo has the memory templates, the usage-check workflow and action, and the late-run guard. The [pro pack](https://buy.polar.sh/polar_cl_HkC1kUZmcpRbovskrQSPqrWmpFi8Gqbau5vEI3HOoVV?utm_source=github&utm_medium=readme&utm_campaign=A&utm_content=agent-ops-kit) ($19) adds routine prompt templates, a local usage gate with weekly pacing, report scripts and a longer setup guide.

Made by Plainfold. Not affiliated with or endorsed by Anthropic. Written with AI assistance.
