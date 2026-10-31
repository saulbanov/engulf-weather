"""Engulf weather: the arithmetic behind the readings. No network."""
import sys, unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engulf import astro, climatology, event, forecast, ground, reading, kit, site

EV = event()
TZ = ZoneInfo(EV["timezone"])


class Event(unittest.TestCase):
    def test_burns_fall_inside_the_burn_window(self):
        bw = EV["burn_window"]
        for b in EV["burns"]:
            self.assertEqual(b["date"], bw["date"])
            self.assertTrue(bw["start"] <= b["time"] <= bw["end"])

    def test_window_pads_both_sides(self):
        md = climatology.window(EV, 3)
        self.assertEqual((md[0], md[-1], len(md)), ((11, 9), (11, 18), 10))


class Sky(unittest.TestCase):
    def test_sun_matches_the_naval_observatory_within_two_minutes(self):
        # USNO for 2026-11-14 at the site: rise 06:28, set 17:04 (CST), read 2026-10-31
        rise, set_ = astro.sun(date(2026, 11, 14), EV["site"]["lat"], EV["site"]["lon"], EV["timezone"])
        self.assertLess(abs((rise.hour * 60 + rise.minute) - (6 * 60 + 28)), 2)
        self.assertLess(abs((set_.hour * 60 + set_.minute) - (17 * 60 + 4)), 2)

    def test_moon_matches_the_naval_observatory(self):
        # USNO: waxing crescent, 25% lit at local midnight beginning 2026-11-14; first quarter 11-17
        m = astro.moon(datetime(2026, 11, 14, 22, tzinfo=TZ))
        self.assertEqual(m["phase"], "waxing crescent")
        self.assertLess(abs(m["illuminated"] - 0.28), 0.06)


class Outlook(unittest.TestCase):
    def test_point_in_polygon_with_a_hole(self):
        from engulf import outlook
        square = [(0, 0), (10, 0), (10, 10), (0, 10)]
        self.assertTrue(outlook.inside(5, 5, square))
        self.assertFalse(outlook.inside(15, 5, square))
        kml = b"""<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>8-14 Day Temperature Outlook - Created: 10/30/2026 - Valid: 11/07/2026 - 11/13/2026</name>
        <Placemark><name>33.0% Chance of Above Normal Temperature</name><Polygon><outerBoundaryIs><LinearRing><coordinates>0,0 10,0 10,10 0,10 0,0</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
        <Placemark><name>50.0% Chance of Above Normal Temperature</name><Polygon><outerBoundaryIs><LinearRing><coordinates>2,2 4,2 4,4 2,4 2,2</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
        </Document></kml>"""
        self.assertEqual(outlook.read_kml(kml, 3, 3)["chance"], 50.0)
        self.assertEqual(outlook.read_kml(kml, 8, 8)["chance"], 33.0)
        self.assertEqual(outlook.read_kml(kml, 20, 20)["lean"], "equal chances")
        self.assertEqual(outlook.read_kml(kml, 8, 8)["period"], ["2026-11-07", "2026-11-13"])


class Blend(unittest.TestCase):
    def test_forecast_weight_by_lead(self):
        from engulf import blend
        self.assertEqual(blend.forecast_weight(3), 1.0)
        self.assertEqual(blend.forecast_weight(7), 1.0)
        self.assertEqual(blend.forecast_weight(11), 0.75)
        self.assertEqual(blend.forecast_weight(15), 0.5)
        self.assertEqual(blend.forecast_weight(20), 0.5)

    def test_estimate_blends_and_nudges(self):
        from engulf import blend
        normal = {"high_f": 72, "morning_f": 45, "evening_feels_f": 52, "overnight_f": 49, "wet": 0.14}
        fc = {"high_f": 68, "morning_f": 50, "evening_feels_f": 56, "overnight_f": 50, "wet": 0.1}
        outlook = {"outlooks": {"8-14 day": {"temperature": {"period": ["2026-11-07", "2026-11-13"], "lean": "above", "chance": 33.0},
                                             "rain": {"period": ["2026-11-07", "2026-11-13"], "lean": "near", "chance": 36.0}}}}
        e = blend.estimate("2026-11-12", date(2026, 11, 1), fc, normal, outlook)   # 11 days out: 75% forecast
        self.assertEqual(e["high_f"], round(0.75 * 68 + 0.25 * 73.5))               # normal nudged +1.5° for a slight warm lean
        self.assertEqual(e["inputs"]["normal_rain_factor"], 1.0)                     # "near normal" rain: no nudge
        none = blend.estimate("2026-11-15", date(2026, 10, 20), None, normal, outlook)
        self.assertEqual((none["high_f"], none["inputs"]["forecast_weight"]), (72, 0.0))   # outside the outlook's dates
        close = blend.estimate("2026-11-14", date(2026, 11, 10), fc, normal, outlook)
        self.assertEqual(close["high_f"], 68)


class Station(unittest.TestCase):
    def hour(self, d, h, wind, gust=None, rain=0.0):
        return {"date": d, "hour": h, "temp_f": 50.0, "dew_f": 45.0, "wind_mph": wind, "gust_mph": gust, "rain_in": rain}

    def test_burn_night_takes_the_worst_hour(self):
        hs = [self.hour("2020-11-14", h, w) for h, w in zip(range(19, 24), [3, 5, 16, 4, 2])]
        n = climatology.burn_nights(hs, 19, 23)[0]
        self.assertEqual(n["max_wind_mph"], 16)
        self.assertIsNone(n["max_gust_mph"])

    def test_night_with_too_few_reports_is_dropped(self):
        hs = [self.hour("2020-11-14", 19, 3)]
        self.assertEqual(climatology.burn_nights(hs, 19, 23), [])


def fake_ensemble(n_members, wind=5.0, rain=0.0, temp=60.0, hours_cover=None):
    times = [f"{d}T{h:02d}:00" for d in EV["days"] for h in range(24)]
    cover = hours_cover or len(times)
    mem = {}
    for m in range(n_members):
        mem[f"{m:02d}"] = {"temperature_2m": [temp + m if i < cover else None for i in range(len(times))],
                           "wind_speed_10m": [wind if i < cover else None for i in range(len(times))],
                           "wind_gusts_10m": [wind * 1.5 if i < cover else None for i in range(len(times))],
                           "precipitation": [rain if i < cover else None for i in range(len(times))]}
    return times, mem


class Forecast(unittest.TestCase):
    def test_members_unflatten_open_meteo_layout(self):
        raw = {"hourly": {"time": ["t"], "wind_speed_10m": [1], "wind_speed_10m_member01": [2], "precipitation_member01": [0]}}
        m = forecast.members(raw)
        self.assertEqual(m["00"]["wind_speed_10m"], [1])
        self.assertEqual(m["01"], {"wind_speed_10m": [2], "precipitation": [0]})

    def test_days_a_run_does_not_reach_are_absent_not_zero(self):
        times, mem = fake_ensemble(3, hours_cover=48)          # covers Thursday and Friday only
        s = forecast.summarise(times, mem, EV)
        self.assertEqual(s["days"]["2026-11-13"]["runs"], 3)
        self.assertEqual(s["days"]["2026-11-14"]["runs"], 0)
        self.assertEqual(s["burn"]["runs"], 0)

    def test_burn_shares(self):
        times, mem = fake_ensemble(4, wind=18.0, rain=0.05)
        b = forecast.summarise(times, mem, EV)["burn"]
        self.assertEqual(b["share_wind_at_least_15"], 1.0)
        self.assertEqual(b["share_gust_at_least_25"], 1.0)     # 27 mph gusts
        self.assertEqual(b["share_rain_at_least_0.1"], 1.0)    # 5 hours × 0.05 in


class Ground(unittest.TestCase):
    def test_same_weeks_skip_this_year_and_far_days(self):
        rows = [("2020-10-30", 1.0), ("2020-12-30", 9.0), ("2026-10-30", 5.0), ("2010-11-05", 2.0)]
        self.assertEqual(sorted(ground.same_weeks(rows, date(2026, 10, 31))), [1.0, 2.0])

    def test_percentile_is_share_at_or_below(self):
        self.assertEqual(ground.percentile_of(2, [1, 2, 3, 4]), 0.5)


class Reading(unittest.TestCase):
    def test_river_words(self):
        self.assertEqual(reading.river_words(0.05), "very low")
        self.assertEqual(reading.river_words(0.36), "about normal")
        self.assertEqual(reading.river_words(0.95), "very high")

    def test_no_jargon_in_reader_text(self):
        import json
        from engulf import ROOT
        f, g, c = (json.loads((ROOT / p).read_text()) for p in ("data/forecast-latest.json", "data/ground-latest.json", "data/climatology.json"))
        days = [reading.day_reading(i, d, f, c, g, EV) for i, d in enumerate(EV["days"])]
        text = " ".join(x for d in days for x in d["lines"] + d["kit"]["means"]).lower()
        for word in ("ensemble", "runs", "median", "percentile", "climatology", "cfs", "model", "leaning", "p10", "share"):
            self.assertNotIn(word, text, word)

    def test_odds_words(self):
        self.assertEqual(reading.odds(None), "too far out to say")
        self.assertEqual(reading.odds(0), "very unlikely")
        self.assertEqual(reading.odds(0.04), "unlikely (under 1 in 10)")
        self.assertEqual(reading.odds(0.1), "about 1 in 10")
        self.assertEqual(reading.odds(0.33), "about 3 in 10")
        self.assertEqual(reading.odds(0.97), "almost certain")

    def test_pooling_weights_by_run_count(self):
        models = {"A": {"days": {"d": {"runs": 50, "x": 0.0}}}, "B": {"days": {"d": {"runs": 30, "x": 1.0}}},
                  "C": {"days": {"d": {"runs": 0}}}}
        self.assertEqual(reading.pooled(models, "d", "x"), (0.38, 80))

    def test_banner_names_the_date_then_changes(self):
        burn = date(2026, 11, 14)
        self.assertIn("preliminary until about Nov 7", reading.banner(date(2026, 10, 31), burn))
        self.assertIn("firming up", reading.banner(date(2026, 11, 8), burn))

    def test_why_explains_the_blend(self):
        days = [{"date": "2026-11-12", "kit": {"inputs": {"forecast_weight": 0.69, "outlook": {"temperature": "above (33%)"}}}},
                {"date": "2026-11-14", "kit": {"inputs": {"forecast_weight": 0.56, "outlook": {}}}}]
        outlook = {"outlooks": {"8-14 day": {"temperature": {"period": ["2026-11-07", "2026-11-13"], "lean": "above", "chance": 33.0}}}}
        ground = {"recent": {"highs_vs_normal_f": 3.8, "rain_in": 1.9, "normal_rain_in": 3.5}}
        text = " ".join(reading.why(days, ground, outlook, date(2026, 10, 31)))
        for bit in ("56% to 69%", "normal Engulf week", "slightly warmer", "Thursday", "warm and dry", "isn't in the numbers"):
            self.assertIn(bit, text)
        close = [{"date": "2026-11-14", "kit": {"inputs": {"forecast_weight": 1.0, "outlook": {}}}}]
        self.assertIn("within a week", reading.why(close, {}, {}, date(2026, 11, 10))[0])

    def test_lean_words(self):
        self.assertEqual(reading.lean_words({"lean": "above", "chance": 33}, "temperature"), "slightly warmer than normal")
        self.assertEqual(reading.lean_words({"lean": "below", "chance": 55}, "rain"), "likely drier than normal")
        self.assertEqual(reading.lean_words({"lean": "near", "chance": 36}, "rain"), "rain about normal")
        self.assertEqual(reading.lean_words({"lean": "equal chances", "chance": None}, "rain"), "no clear lean on rain")

    def test_one_in(self):
        self.assertEqual(reading.one_in(0.14), "1 in 7")
        self.assertEqual(reading.one_in(0.1), "1 in 10")

    def test_lead_wording(self):
        first = date(2026, 11, 12)
        self.assertIn("normal year", reading.lead(date(2026, 10, 20), first))
        self.assertIn("best guesses", reading.lead(date(2026, 10, 31), first))
        self.assertIn("burn night is now in", reading.lead(date(2026, 11, 8), first))


class Kit(unittest.TestCase):
    def test_wind_chill_only_where_it_applies(self):
        self.assertEqual(kit.feels(60, 20), 60)
        self.assertEqual(kit.feels(40, 2), 40)
        self.assertEqual(round(kit.feels(40, 10)), 34)          # NWS chart: 40°F at 10 mph feels 34°F

    def test_wear_phrases(self):
        self.assertEqual(kit.wear(80), "t-shirt weather")
        self.assertEqual(kit.wear(50), "a fleece or light jacket")
        self.assertEqual(kit.wear(33), "winter layers")

    def test_meaning_lines(self):
        cold = kit.meaning({"high_f": 72, "evening_feels_f": 50, "overnight_f": 38, "overnight_p10_f": 30}, 0.4,
                           first=True, last=False, daylight_after_gates=7.1, dewy=0.34)
        text = " ".join(cold)
        for bit in ("A big swing", "cold night", "Frost", "7 hours of daylight", "dew", "mud"):
            self.assertIn(bit, text)
        mild = kit.meaning({"high_f": 70, "evening_feels_f": 60, "overnight_f": 55, "overnight_p10_f": 50}, 0.1,
                           first=False, last=False, daylight_after_gates=7, dewy=0.34)
        self.assertEqual(len(mild), 1)
        last = kit.meaning({"high_f": 66, "evening_feels_f": 52, "overnight_f": None}, 0.5,
                           first=False, last=True, daylight_after_gates=7, dewy=None)
        self.assertTrue(any("off the land by 5 pm" in x for x in last) and any("muddy" in x for x in last))

class Site(unittest.TestCase):
    def load(self):
        import json
        from engulf import ROOT
        return [json.loads((ROOT / p).read_text()) for p in
                ("data/forecast-latest.json", "data/ground-latest.json", "data/climatology.json", "readings/latest.json")]

    def test_same_data_gives_the_same_page(self):
        f, g, c, r = self.load()
        self.assertEqual(site.render(EV, f, g, c, r), site.render(EV, f, g, c, r))

    def test_page_is_self_contained(self):
        html = site.render(EV, *self.load())
        self.assertNotIn("<script", html)
        self.assertNotIn("src=\"http", html)
        self.assertIn("Burn night", html)
        self.assertIn("Not an official Engulf page", html)

    def test_page_has_no_jargon(self):
        import re
        html = re.sub(r"<[^>]+>", " ", site.render(EV, *self.load())).lower()
        for word in ("ensemble", "model runs", "median", "climatology", "cfs", "leaning", "p10"):
            self.assertNotIn(word, html, word)

    def test_band_formatting(self):
        self.assertEqual(site.rng({"median": 5}), "5°F")
        self.assertEqual(site.rng(None), "—")
        self.assertIn("(3–8)", site.rng({"median": 5, "p10": 3, "p90": 8}, " mph"))


if __name__ == "__main__":
    unittest.main()
