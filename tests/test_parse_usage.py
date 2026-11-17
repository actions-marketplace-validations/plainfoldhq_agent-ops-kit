"""Run: python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PARSE = os.path.join(HERE, "..", "scripts", "parse_usage.py")
OUTPUTS = os.path.join(HERE, "..", "scripts", "action_outputs.py")

# Shape of a real rate_limit_event from the Claude Code CLI (stream-json), values changed.
EVENT = {"type": "rate_limit_event", "rate_limit_info": {
    "status": "allowed", "rateLimitType": "five_hour", "utilization": None, "resetsAt": 1794904800,
    "unifiedWindows": {"five_hour": {"utilization": 0.09, "resetsAt": 1794904800, "status": "allowed"},
                       "seven_day": {"utilization": 0.06, "resetsAt": 1795374000, "status": "allowed"}},
    "isUsingOverage": False, "someOtherField": "must not be copied"}}


def run(script, path, env=None):
    e = dict(os.environ, **(env or {}))
    return subprocess.run([sys.executable, script, path], capture_output=True, text=True, env=e).stdout


def tmp(text):
    f = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
    f.write(text)
    f.close()
    return f.name


class ParseUsage(unittest.TestCase):
    def parse(self, lines):
        p = tmp("\n".join(lines))
        try:
            return json.loads(run(PARSE, p))
        finally:
            os.unlink(p)

    def test_unified_windows(self):
        u = self.parse(['{"type":"system"}', json.dumps(EVENT), '{"type":"result","is_error":false}'])
        self.assertEqual(u["five_hour_pct"], 9.0)
        self.assertEqual(u["weekly_pct"], 6.0)
        self.assertEqual(u["weekly_resets"], "2026-11-22T19:00:00+00:00")
        self.assertEqual(u["status"], "allowed")
        self.assertIsNone(u["error"])
        self.assertNotIn("someOtherField", json.dumps(u))

    def test_old_shape_and_ms_timestamps(self):
        ev = {"type": "rate_limit_event", "rate_limit_info": {
            "status": "allowed", "rateLimitType": "seven_day", "utilization": 0.42, "resetsAt": 1795374000000}}
        u = self.parse([json.dumps(ev)])
        self.assertEqual(u["weekly_pct"], 42.0)
        self.assertEqual(u["weekly_resets"], "2026-11-22T19:00:00+00:00")
        self.assertIsNone(u["five_hour_pct"])

    def test_no_event_and_garbage(self):
        u = self.parse(["not json", '{"type":"assistant"}'])
        self.assertIsNone(u["weekly_pct"])
        self.assertEqual(u["error"], "no rate_limit_event in output")

    def test_result_error(self):
        u = self.parse(['{"type":"result","is_error":true,"subtype":"error_during_execution"}'])
        self.assertIn("error_during_execution", u["error"])

    def test_missing_file(self):
        u = json.loads(run(PARSE, "/nonexistent/out.jsonl"))
        self.assertTrue(u["error"].startswith("no output file"))


class ActionOutputs(unittest.TestCase):
    def outputs(self, usage, **env):
        p = tmp(json.dumps(usage))
        try:
            return dict(l.split("=", 1) for l in run(OUTPUTS, p, env).splitlines())
        finally:
            os.unlink(p)

    def test_no_thresholds(self):
        o = self.outputs({"five_hour_pct": 9.0, "weekly_pct": None, "status": "allowed"})
        self.assertEqual(o, {"five_hour_pct": "9.0", "weekly_pct": "", "weekly_resets": "", "status": "allowed", "ok": "true"})

    def test_thresholds(self):
        u = {"five_hour_pct": 79.0, "weekly_pct": 50.0}
        self.assertEqual(self.outputs(u, AOK_MAX_WEEKLY="60", AOK_MAX_5H="80")["ok"], "true")
        self.assertEqual(self.outputs(u, AOK_MAX_WEEKLY="50")["ok"], "false")
        self.assertEqual(self.outputs({"weekly_pct": None}, AOK_MAX_WEEKLY="90")["ok"], "false")


if __name__ == "__main__":
    unittest.main()
