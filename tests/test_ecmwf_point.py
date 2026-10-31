"""The ECMWF point tool's step choice, day assignment and summaries; no network, no GRIB decoder."""
import sys, unittest
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import ecmwf_point as ep

CHI = ZoneInfo("America/Chicago")
RUN = datetime(2026, 10, 30, 12, tzinfo=timezone.utc)


def fake(members, steps, hi_k=295.0, lo_k=283.0, rain_m_per_window=0.0):
    """Every member the same, except member n is n kelvin warmer."""
    v = {}
    for n in members:
        acc = 0.0
        for s in range(ep.WINDOW, max(steps) + 1, ep.WINDOW):
            acc += rain_m_per_window
            v[("tp", n, s)] = acc
            v[("mx2t6", n, s)] = hi_k + n
            v[("mn2t6", n, s)] = lo_k + n
    return v


class Steps(unittest.TestCase):
    def test_one_central_day_is_four_windows(self):
        steps = ep.window_steps(RUN, *ep.local_span(date(2026, 11, 11), 1, CHI))
        self.assertEqual(steps, [288, 294, 300, 306])

    def test_days_past_the_run_are_dropped(self):
        steps = ep.window_steps(RUN, *ep.local_span(date(2026, 11, 13), 3, CHI))
        self.assertEqual(max(steps), ep.LAST_STEP)
        self.assertEqual({ep.day_of(RUN, s, CHI) for s in steps}, {date(2026, 11, 13), date(2026, 11, 14)})

    def test_rain_asks_for_the_step_before_each_window(self):
        self.assertEqual(ep.tp_steps([6, 12, 18]), [6, 12, 18])
        self.assertEqual(ep.tp_steps([288, 294]), [282, 288, 294])


class Summaries(unittest.TestCase):
    def test_single_run(self):
        steps = ep.window_steps(RUN, *ep.local_span(date(2026, 11, 11), 1, CHI))
        day = ep.summarise(fake([0], steps, rain_m_per_window=0.001), RUN, steps, CHI)[0]
        self.assertEqual(day["date"], "2026-11-11")
        self.assertTrue(day["complete"])
        self.assertEqual((day["high_f"], day["low_f"]), (71, 50))
        self.assertAlmostEqual(day["rain_in"], 0.16, places=2)

    def test_ensemble_spread_and_rain_shares(self):
        steps = ep.window_steps(RUN, *ep.local_span(date(2026, 11, 11), 1, CHI))
        day = ep.summarise(fake(range(1, 11), steps), RUN, steps, CHI)[0]
        self.assertEqual(day["members"], 10)
        self.assertLessEqual(day["high_f"]["p10"], day["high_f"]["median"])
        self.assertLessEqual(day["high_f"]["median"], day["high_f"]["p90"])
        self.assertEqual(day["rain_in"]["share_at_least_0.1"], 0.0)

    def test_partial_day_is_marked(self):
        steps = ep.window_steps(RUN, *ep.local_span(date(2026, 11, 14), 1, CHI))
        day = ep.summarise(fake([0], steps), RUN, steps, CHI)[0]
        self.assertFalse(day["complete"])


if __name__ == "__main__":
    unittest.main()
