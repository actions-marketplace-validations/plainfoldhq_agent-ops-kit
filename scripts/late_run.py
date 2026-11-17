#!/usr/bin/env python3
"""Late-run guard: how late is this GitHub Actions scheduled run?

Finds the most recent time at or before NOW that matches a 5-field cron
expression (UTC, as GitHub uses) and reports how many minutes ago it was.
Standard library only. Supports *, numbers, lists (1,2), ranges (1-5),
steps (*/15, 0-30/5) and month/day names (JAN, MON). If both day-of-month
and day-of-week are restricted, a day matches if EITHER matches (cron rule).

Usage: late_run.py "<cron>" [now-iso] [max-late-minutes] [event-name]
Prints key=value lines for $GITHUB_OUTPUT.
"""
import sys
from datetime import datetime, timedelta, timezone

MONTHS = {m: i + 1 for i, m in enumerate(
    "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}
DAYS = {d: i for i, d in enumerate("SUN MON TUE WED THU FRI SAT".split())}
LIMITS = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
MAX_LOOKBACK_MIN = 366 * 24 * 60


def _num(tok, names):
    tok = tok.upper()
    return names[tok] if tok in names else int(tok)


def parse_field(text, idx):
    lo, hi = LIMITS[idx]
    names = MONTHS if idx == 3 else DAYS if idx == 4 else {}
    out = set()
    for part in text.split(","):
        step = 1
        if "/" in part:
            part, s = part.split("/", 1)
            step = int(s)
            if step < 1:
                raise ValueError("step must be >= 1")
        if part == "*":
            a, b = lo, hi
        elif "-" in part:
            x, y = part.split("-", 1)
            a, b = _num(x, names), _num(y, names)
        else:
            a = _num(part, names)
            b = hi if step > 1 else a
        if not (lo <= a <= hi and lo <= b <= hi and a <= b):
            raise ValueError(f"value out of range in field {idx + 1}: {text}")
        out.update(range(a, b + 1, step))
    if idx == 4 and 7 in out:
        out.discard(7)
        out.add(0)
    return out


def parse_cron(expr):
    fields = expr.split()
    if len(fields) != 5:
        raise ValueError("cron needs 5 fields")
    sets = [parse_field(f, i) for i, f in enumerate(fields)]
    dom_star = fields[2] == "*"
    dow_star = fields[4] == "*"
    return sets, dom_star, dow_star


def matches(t, cron):
    (mins, hours, doms, months, dows), dom_star, dow_star = cron
    if t.minute not in mins or t.hour not in hours or t.month not in months:
        return False
    dom_ok = t.day in doms
    dow_ok = (t.isoweekday() % 7) in dows
    if dom_star or dow_star:
        return dom_ok and dow_ok
    return dom_ok or dow_ok


def previous_fire(expr, now):
    cron = parse_cron(expr)
    t = now.replace(second=0, microsecond=0)
    for _ in range(MAX_LOOKBACK_MIN):
        if matches(t, cron):
            return t
        t -= timedelta(minutes=1)
    raise ValueError("no matching time in the last year")


def main(argv):
    expr = argv[1] if len(argv) > 1 else ""
    now = (datetime.fromisoformat(argv[2].replace("Z", "+00:00"))
           if len(argv) > 2 and argv[2] else datetime.now(timezone.utc))
    max_late = float(argv[3]) if len(argv) > 3 and argv[3] else 60.0
    event = argv[4] if len(argv) > 4 else "schedule"
    if event != "schedule" or not expr.strip():
        print("scheduled-for=")
        print("late-minutes=0")
        print("is-scheduled=false")
        print("ok=true")
        return 0
    fire = previous_fire(expr, now)
    late = int((now - fire).total_seconds() // 60)
    print(f"scheduled-for={fire.strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"late-minutes={late}")
    print("is-scheduled=true")
    print(f"ok={'true' if late <= max_late else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
