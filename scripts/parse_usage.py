#!/usr/bin/env python3
"""Turn Claude Code stream-json output into usage.json.

Reads rate_limit_event lines only. Writes percentages (0-100) when the CLI
reports utilization; otherwise writes nulls so the usage gate treats the
numbers as unknown. Never copies anything except rate-limit fields.
"""
import json
import sys
from datetime import datetime, timezone


def iso(ts):
    if ts is None:
        return None
    try:
        ts = float(ts)
        if ts > 1e12:  # milliseconds
            ts /= 1000
        return datetime.fromtimestamp(ts, timezone.utc).isoformat()
    except (TypeError, ValueError):
        return str(ts)


def pct(u):
    if u is None:
        return None
    u = float(u)
    return round(u * 100, 1) if u <= 1.0 else round(u, 1)


def main(path):
    out = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "source": "github-actions: claude-code stream-json rate_limit_event",
        "five_hour_pct": None,
        "five_hour_resets": None,
        "weekly_pct": None,
        "weekly_resets": None,
        "status": None,
        "events": [],
        "error": None,
    }
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError as e:
        out["error"] = f"no output file: {e}"
        print(json.dumps(out, indent=2))
        return

    for line in lines:
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") == "result" and msg.get("is_error"):
            out["error"] = f"claude result error: {msg.get('terminal_reason') or msg.get('subtype')}"
        if msg.get("type") != "rate_limit_event":
            continue
        info = msg.get("rate_limit_info") or {}
        keep = {k: info.get(k) for k in (
            "status", "rateLimitType", "utilization", "resetsAt", "unifiedWindows", "isUsingOverage")}
        out["events"].append(keep)
        out["status"] = info.get("status") or out["status"]

        windows = info.get("unifiedWindows") or {}
        fh = windows.get("five_hour") or {}
        sd = windows.get("seven_day") or {}
        if fh.get("utilization") is not None:
            out["five_hour_pct"] = pct(fh["utilization"])
            out["five_hour_resets"] = iso(fh.get("resetsAt"))
        if sd.get("utilization") is not None:
            out["weekly_pct"] = pct(sd["utilization"])
            out["weekly_resets"] = iso(sd.get("resetsAt"))

        # Older event shape: one window per event.
        kind, util = info.get("rateLimitType"), info.get("utilization")
        if util is not None and kind == "five_hour" and out["five_hour_pct"] is None:
            out["five_hour_pct"], out["five_hour_resets"] = pct(util), iso(info.get("resetsAt"))
        if util is not None and kind == "seven_day" and out["weekly_pct"] is None:
            out["weekly_pct"], out["weekly_resets"] = pct(util), iso(info.get("resetsAt"))

    if not out["events"] and not out["error"]:
        out["error"] = "no rate_limit_event in output"
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/out.jsonl")
