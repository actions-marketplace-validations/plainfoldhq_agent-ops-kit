import sys, unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import late_run as lr

U = timezone.utc


class T(unittest.TestCase):
    def prev(self, expr, now):
        return lr.previous_fire(expr, datetime.fromisoformat(now).replace(tzinfo=U))

    def test_daily(self):
        self.assertEqual(self.prev("5 2 * * *", "2026-11-17T09:00:00"),
                         datetime(2026, 11, 17, 2, 5, tzinfo=U))
        self.assertEqual(self.prev("5 2 * * *", "2026-11-17T02:04:59"),
                         datetime(2026, 11, 16, 2, 5, tzinfo=U))

    def test_exact_minute(self):
        self.assertEqual(self.prev("5 2 * * *", "2026-11-17T02:05:30"),
                         datetime(2026, 11, 17, 2, 5, tzinfo=U))

    def test_steps_lists_ranges(self):
        self.assertEqual(self.prev("*/15 * * * *", "2026-11-17T10:44:00"),
                         datetime(2026, 11, 17, 10, 30, tzinfo=U))
        self.assertEqual(self.prev("0 9,17 * * 1-5", "2026-11-17T12:00:00"),
                         datetime(2026, 11, 17, 9, 0, tzinfo=U))

    def test_weekday_names_and_7(self):
        # 2026-11-17 is a Tuesday; previous Sunday is 11-15
        self.assertEqual(self.prev("0 0 * * SUN", "2026-11-17T12:00:00"),
                         datetime(2026, 11, 15, 0, 0, tzinfo=U))
        self.assertEqual(self.prev("0 0 * * 7", "2026-11-17T12:00:00"),
                         datetime(2026, 11, 15, 0, 0, tzinfo=U))
        self.assertEqual(self.prev("30 6 * * MON-FRI", "2026-11-16T06:00:00"),
                         datetime(2026, 11, 13, 6, 30, tzinfo=U))

    def test_dom_or_dow(self):
        # 1st of month OR Friday: previous is Fri 2026-11-13
        self.assertEqual(self.prev("0 0 1 * 5", "2026-11-17T00:00:00"),
                         datetime(2026, 11, 13, 0, 0, tzinfo=U))

    def test_month_names(self):
        self.assertEqual(self.prev("0 0 1 JAN *", "2026-11-17T00:00:00"),
                         datetime(2026, 1, 1, 0, 0, tzinfo=U))

    def test_bad(self):
        for bad in ["* * * *", "60 * * * *", "*/0 * * * *", "5-1 * * * *"]:
            with self.assertRaises(ValueError):
                lr.parse_cron(bad)

    def run_main(self, *args):
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            lr.main(["x", *args])
        return dict(l.split("=", 1) for l in buf.getvalue().split())

    def test_main_late(self):
        o = self.run_main("5 2 * * *", "2026-11-17T09:05:00Z", "60", "schedule")
        self.assertEqual(o["late-minutes"], "420")
        self.assertEqual(o["ok"], "false")
        self.assertEqual(o["scheduled-for"], "2026-11-17T02:05:00Z")

    def test_main_on_time(self):
        o = self.run_main("5 2 * * *", "2026-11-17T02:20:00Z", "60", "schedule")
        self.assertEqual(o["ok"], "true")

    def test_main_not_schedule(self):
        o = self.run_main("", "", "60", "workflow_dispatch")
        self.assertEqual(o["ok"], "true")
        self.assertEqual(o["is-scheduled"], "false")


if __name__ == "__main__":
    unittest.main()
