# Pace a scheduled Claude Code agent across the weekly limit

Claude subscription plans have a rolling 5-hour limit and a weekly limit that resets at a fixed time each week. If an unattended agent shares the plan with you, two things go wrong without pacing:

- it spends most of the week's allowance in the first night or two, and you hit the weekly limit on Thursday;
- or it is so cautious that most of the allowance is never used.

A cumulative daily cap fixes both. This guide shows the rule and how to compute it from the `usage.json` that this kit's workflow writes (it includes `weekly_pct`, `five_hour_pct` and `weekly_resets`).

## The rule

Allow about 1/7 of the week per day, counted from the reset, and keep a margin under the true limit:

| Day since reset (local calendar days) | Cap (weekly %) |
|---|---|
| reset day, after the reset | 14 |
| day 2 | 28 |
| day 3 | 42 |
| ... | +14 per day |
| last full day and the reset day before the reset | 93 |

- Caps are cumulative: a slow day leaves room for later days.
- Stop below your real hard line (here 93, so that usage added between two checks cannot push it past 95).
- Also stop when the 5-hour window is high (for example at 80%). Your own interactive use counts toward the same numbers, so the agent backs off when you are busy.
- If your runs are scheduled back to back (for example every 5 hours), add a run clock: stop after 4.5 hours.

The tricky part is the reset day. If the week resets Sunday at 1 PM, Sunday morning belongs to the old week (cap 93) and Sunday afternoon to the new one (cap 14). A fixed per-weekday table gets one of the two wrong. Counting days from `weekly_resets` gets both right.

## Compute it (stdlib Python)

```python
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

def today_cap(usage, now=None, per_day=14, final=93, tz="America/Chicago"):
    now = now or datetime.now(timezone.utc)
    resets = datetime.fromisoformat(usage["weekly_resets"].replace("Z", "+00:00"))
    while resets <= now:          # usage.json may predate the last reset
        resets += timedelta(days=7)
    last = resets - timedelta(days=7)
    z = ZoneInfo(tz)
    days = (now.astimezone(z).date() - last.astimezone(z).date()).days
    return min(per_day * (days + 1), final)

u = json.load(open("usage.json"))
cap = today_cap(u)
stop = u["weekly_pct"] is None or u["weekly_pct"] >= cap or (u["five_hour_pct"] or 0) >= 80
print("STOP" if stop else "GO", "weekly", u["weekly_pct"], "cap", cap)
```

Treat a stale file (for example `checked_at` older than an hour) as unknown, and refresh it on demand rather than trusting the GitHub `schedule` trigger (see [schedule delays](github-actions-schedule-delays.md)).

## How often to check

Usage moves while the agent works, so check during the run, not only at the start. What has worked for us: at the start, then about every 40 tool calls or 45 minutes, and about every 15 tool calls once within 5 points of a stop line. Never refresh more than every 10 minutes; each refresh costs one tiny prompt.

## In the agent's instructions

Put the rule in the agent's `CLAUDE.md` (the template in `templates/` has a usage-gate section) so every run applies it the same way. "Keep working until the gate says stop" is safe only if the instructions also say that each block must leave a committed result, and that finished work must not be redone to fill time.

The pro pack's `usage_gate.py` implements this rule (`--pace 14:93`, plus staleness, hard limits, a run clock and unit tests) together with a work-block prompt template; see the README. The snippet above is enough to do it yourself.
