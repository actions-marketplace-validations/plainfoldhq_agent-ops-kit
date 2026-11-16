#!/usr/bin/env python3
"""Print GitHub Actions outputs (key=value lines) from a usage.json file.

Thresholds come from env AOK_MAX_WEEKLY / AOK_MAX_5H (empty = no limit).
ok=false when a threshold is set and the number is unknown or at/above it.
"""
import json
import os
import sys


def main(path):
    with open(path) as f:
        u = json.load(f)
    ok = True
    for key, env in (("weekly_pct", "AOK_MAX_WEEKLY"), ("five_hour_pct", "AOK_MAX_5H")):
        lim = os.environ.get(env, "").strip()
        if lim:
            v = u.get(key)
            if v is None or float(v) >= float(lim):
                ok = False
    for key in ("five_hour_pct", "weekly_pct", "weekly_resets", "status"):
        v = u.get(key)
        print("%s=%s" % (key, "" if v is None else str(v).replace("\n", " ")))
    print("ok=%s" % ("true" if ok else "false"))


if __name__ == "__main__":
    main(sys.argv[1])
