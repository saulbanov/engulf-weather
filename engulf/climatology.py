"""What the festival week has done in the past: the baseline every forecast is read against.

Two records, kept apart because they are different instruments (data rule 1 and 3):

* Daily highs, lows and rain at the site, 1991 to last year, from PRISM's 4 km gridded analysis
  served by the Regional Climate Centers' ACIS (grid 21). Modelled from stations, not a station.
* Hourly wind, gusts, temperature, dew point and rain at McComb/Lewis Field, MS (MCB), 26 km north,
  from the Iowa Environmental Mesonet's ASOS archive. Measured, at an airport, not at the site.

Both are read for a window of days around the event (default the event's days ±3, so 10 calendar
days a year), because four days a year is too few to say "how often". A year is one sample of a
mid-November week; the shares below are counts of those days or nights over the years read.
"""
from __future__ import annotations
import csv, gzip, io, json, statistics, time
from datetime import date, timedelta
from . import ROOT, event, kit, rules
from .fetch import get, get_json

ACIS = "https://data.rcc-acis.org/GridData"
IEM = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
OUT = ROOT / "data" / "climatology.json"


def window(ev: dict, pad: int) -> list[tuple[int, int]]:
    """(month, day) pairs for the event's days, padded either side."""
    first, last = date.fromisoformat(ev["days"][0]), date.fromisoformat(ev["days"][-1])
    d, out = first - timedelta(days=pad), []
    while d <= last + timedelta(days=pad):
        out.append((d.month, d.day)); d += timedelta(days=1)
    return out


def share(xs: list[bool]) -> float | None:
    return round(sum(xs) / len(xs), 2) if xs else None


def daily(ev: dict, years: range, md: list[tuple[int, int]]) -> dict:
    site = ev["site"]
    body = {"loc": f"{site['lon']},{site['lat']}", "grid": "21", "elems": "maxt,mint,pcpn",
            "sdate": f"{years.start}-01-01", "edate": f"{years.stop - 1}-12-31"}
    url = ACIS + "?params=" + json.dumps(body, separators=(",", ":"))
    data = get_json(url.replace(" ", ""), "acis-prism", "site-daily")["data"]
    keep = {(m, d) for m, d in md}
    rows = [r for r in data if (int(r[0][5:7]), int(r[0][8:10])) in keep and r[1] > -900 and r[2] > -900]
    hi, lo, rain = [r[1] for r in rows], [r[2] for r in rows], [max(r[3], 0.0) for r in rows if r[3] > -900]
    return {"source": "PRISM 4 km daily via ACIS GridData grid 21 (modelled from stations)",
            "years": [years.start, years.stop - 1], "days_read": len(rows),
            "high_f": {"median": round(statistics.median(hi)), "p10": pct(hi, 10), "p90": pct(hi, 90), "max": round(max(hi))},
            "low_f": {"median": round(statistics.median(lo)), "p10": pct(lo, 10), "p90": pct(lo, 90), "min": round(min(lo))},
            "share_days_rain_at_least_0.1": share([x >= rules.WET_IN for x in rain]),
            "share_days_rain_at_least_0.5": share([x >= rules.SOAKING_IN for x in rain]),
            "share_nights_at_or_below_40": share([x <= rules.COLD_NIGHT_F for x in lo]),
            "share_nights_at_or_below_32": share([x <= rules.FROST_F for x in lo]),
            "share_days_at_least_82": share([x >= rules.WARM_DAY_F for x in hi]),
            "share_days_at_most_58": share([x <= rules.CHILLY_DAY_F for x in hi])}


def pct(xs: list[float], p: int) -> int:
    return round(statistics.quantiles(xs, n=100, method="inclusive")[p - 1])


def asos_year(station: str, y: int, md: list[tuple[int, int]], tz: str, pause: float = 0.0) -> list[dict]:
    (m1, d1), (m2, d2) = md[0], md[-1]
    end = date(y, m2, d2) + timedelta(days=1)
    q = (f"{IEM}?station={station}&data=tmpf&data=dwpf&data=sknt&data=gust&data=p01i"
         f"&year1={y}&month1={m1}&day1={d1}&year2={end.year}&month2={end.month}&day2={end.day}"
         f"&tz={tz.replace('/', '%2F')}&format=onlycomma&latlon=no&missing=M&trace=T&report_type=3")
    kept = sorted((ROOT / "data" / "captures" / "iem-asos").glob(f"*-{station}-{y}.gz"))
    if kept:                              # a past year does not change: reread the kept bytes
        text = gzip.decompress(kept[-1].read_bytes()).decode()
    else:
        text = get(q, "iem-asos", f"{station}-{y}", accept="text/csv").decode()
        time.sleep(pause)
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        v = r["valid"]
        out.append({"date": v[:10], "hour": int(v[11:13]),
                    "temp_f": num(r["tmpf"]), "dew_f": num(r["dwpf"]),
                    "wind_mph": None if num(r["sknt"]) is None else num(r["sknt"]) * 1.15078,
                    "gust_mph": None if num(r["gust"]) is None else num(r["gust"]) * 1.15078,
                    "rain_in": 0.0 if r["p01i"] == "T" else num(r["p01i"])})
    return out


def num(s: str) -> float | None:
    try:
        return float(s)
    except ValueError:
        return None


def burn_nights(hours: list[dict], start_h: int, end_h: int) -> list[dict]:
    """One row per night: the worst wind, gust and the rain in the burn hours, and the next morning's low."""
    nights: dict[str, list[dict]] = {}
    for h in hours:
        if start_h <= h["hour"] <= end_h:
            nights.setdefault(h["date"], []).append(h)
    out = []
    for d, hs in sorted(nights.items()):
        w = [h["wind_mph"] for h in hs if h["wind_mph"] is not None]
        g = [h["gust_mph"] for h in hs if h["gust_mph"] is not None]
        r = [h["rain_in"] for h in hs if h["rain_in"] is not None]
        if len(w) < (end_h - start_h + 1) // 2:
            continue                      # too few reports to say what the night did
        out.append({"date": d, "max_wind_mph": max(w), "max_gust_mph": max(g) if g else None,
                    "rain_in": sum(r) if r else None, "reports": len(hs)})
    return out


def evenings(hours: list[dict]) -> list[dict]:
    """Per date: the coldest it felt 6 pm to midnight (wind chill applied) and the low into the next morning."""
    by: dict[str, dict[int, dict]] = {}
    for h in hours:
        if h["temp_f"] is not None:
            by.setdefault(h["date"], {})[h["hour"]] = h
    out = []
    for d in sorted(by):
        nxt = (date.fromisoformat(d) + timedelta(days=1)).isoformat()
        eve = [kit.feels(h["temp_f"], h["wind_mph"] or 0.0) for k, h in by[d].items() if 18 <= k <= 23]
        night = [h["temp_f"] for k, h in by[d].items() if k >= 22] + [h["temp_f"] for k, h in by.get(nxt, {}).items() if k <= 8]
        if len(eve) >= 4 and len(night) >= 8:
            out.append({"date": d, "evening_feels_f": min(eve), "overnight_low_f": min(night)})
    return out


def hourly(ev: dict, years: range, md: list[tuple[int, int]], pause: float = 1.0) -> dict:
    st = ev["neighbours"]["station"]["id"]
    hours = []
    for y in years:
        hours += asos_year(st, y, md, ev["timezone"], pause)
    keep = {f"{m:02d}-{d:02d}" for m, d in md}
    hours = [h for h in hours if h["date"][5:] in keep]
    bw = ev["burn_window"]
    nights = burn_nights(hours, int(bw["start"][:2]), int(bw["end"][:2]))
    evs = evenings(hours)
    calm_wet = [h for h in hours if h["hour"] in (2, 3, 4, 5, 6) and None not in (h["temp_f"], h["dew_f"], h["wind_mph"])]
    return {"source": f"{ev['neighbours']['station']['name']}, hourly ASOS via Iowa Environmental Mesonet (measured, 26 km from the site)",
            "years": [years.start, years.stop - 1], "hours_read": len(hours), "nights_read": len(nights),
            "burn_hours_local": [bw["start"], bw["end"]],
            "share_nights_wind_at_least_15": share([n["max_wind_mph"] >= rules.WINDY_MPH for n in nights]),
            "share_nights_gust_at_least_25": share([(n["max_gust_mph"] or 0) >= rules.GUSTY_MPH for n in nights]),
            "share_nights_rain_at_least_0.1": share([(n["rain_in"] or 0) >= rules.WET_IN for n in nights]),
            "median_max_wind_mph_burn_hours": round(statistics.median([n["max_wind_mph"] for n in nights])),
            "evening_feels_f": {"median": round(statistics.median([e["evening_feels_f"] for e in evs])),
                                "p10": pct([e["evening_feels_f"] for e in evs], 10)},
            "overnight_low_f": {"median": round(statistics.median([e["overnight_low_f"] for e in evs])),
                                "p10": pct([e["overnight_low_f"] for e in evs], 10)},
            "share_predawn_hours_dewy": share([(h["temp_f"] - h["dew_f"]) <= rules.DEW_SPREAD_F and h["wind_mph"] <= rules.CALM_MPH for h in calm_wet]),
            "caveat": ("Gusts are reported only when they occur, so a night with no gust report counts as under 25 mph. "
                       "The station's wind sensor is in open airport ground; a camp among trees usually feels less wind. "
                       "Reports are hourly (routine METARs), so a short squall between reports can be missed.")}


def build(first: int = 1996, last: int = 2025, pad: int = 3) -> dict:
    ev = event()
    md = window(ev, pad)
    out = {"meaning": "Mid-November at Engulf's site in past years: the baseline the readings compare forecasts with.",
           "window": f"{md[0][0]:02d}-{md[0][1]:02d} to {md[-1][0]:02d}-{md[-1][1]:02d} each year (the event's days ±{pad})",
           "site_daily": daily(ev, range(first, last + 1), md),
           "burn_hours": hourly(ev, range(first, last + 1), md),
           "thresholds": {k: getattr(rules, k) for k in dir(rules) if k.isupper()}}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    return out
