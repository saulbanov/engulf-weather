"""This week's forecasts for the event's hours, from three places, kept side by side.

* ECMWF's ensemble (51 runs, 0.25°) and NOAA's GEFS ensemble (31 runs, 0.5°), hourly, through
  Open-Meteo's ensemble API. Ensembles are the honest form past about a week: the readings report
  how many runs show a thing, not one run's guess. ECMWF's open runs reach 15 days; GEFS reaches 35.
* The National Weather Service's hourly forecast for the site's grid cell: forecasters' adjusted
  numbers, 7 days out, one value per hour.
* If Open-Meteo refuses (its free quota counts calls per internet address, and a shared cloud
  machine can find it spent), ECMWF's own open data through tools/ecmwf_point.py, daily only, when its
  decoder is installed (requirements-ecmwf.txt). This is the fallback built in austin-heat on
  2026-10-30 when exactly that happened.

All hours are local (America/Chicago). Missing is never zero: an hour a run does not reach is absent.
"""
from __future__ import annotations
import json, statistics, subprocess, sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from . import ROOT, event, kit, rules
from .fetch import Refused, get_json

ENSEMBLE = "https://ensemble-api.open-meteo.com/v1/ensemble"
MODELS = {"ecmwf_ifs025": "ECMWF ENS", "gfs05": "NOAA GEFS"}
VARS = ["temperature_2m", "dew_point_2m", "wind_speed_10m", "wind_gusts_10m", "precipitation"]


def ensemble(ev: dict, model: str) -> dict:
    s = ev["site"]
    url = (f"{ENSEMBLE}?latitude={s['lat']}&longitude={s['lon']}&hourly={','.join(VARS)}&models={model}"
           f"&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch"
           f"&timezone={ev['timezone'].replace('/', '%2F')}&start_date={ev['days'][0]}&end_date={ev['days'][-1]}")
    return get_json(url, "open-meteo-ensemble", model)


def members(raw: dict) -> dict[str, dict[str, list]]:
    """{member: {var: [hourly values]}} from Open-Meteo's flat `var_memberNN` layout; the control is member 00."""
    h = raw["hourly"]
    out: dict[str, dict[str, list]] = {}
    for k, v in h.items():
        if k == "time":
            continue
        var, _, m = k.partition("_member")
        out.setdefault(m or "00", {})[var] = v
    return out


def hours_of(times: list[str], day: str, h0: int = 0, h1: int = 23) -> list[int]:
    return [i for i, t in enumerate(times) if t[:10] == day and h0 <= int(t[11:13]) <= h1]


def summarise(times: list[str], mem: dict, ev: dict) -> dict:
    """Per day and for the burn window: how many runs reach it, and what share show each thing."""
    days = {}
    for d in ev["days"]:
        idx = hours_of(times, d)
        per = []
        for m in mem.values():
            t = [m["temperature_2m"][i] for i in idx if m["temperature_2m"][i] is not None]
            if len(t) < 24:
                continue                  # this run does not cover the whole day
            r = [m["precipitation"][i] or 0.0 for i in idx]
            night = [m["temperature_2m"][i] for i in hours_of(times, d, 0, 8)]
            eve = [kit.feels(m["temperature_2m"][i], m["wind_speed_10m"][i] or 0.0) for i in hours_of(times, d, 18, 23)]
            nxt = (date.fromisoformat(d) + timedelta(days=1)).isoformat()
            over = [m["temperature_2m"][i] for i in hours_of(times, d, 22, 23) + hours_of(times, nxt, 0, 8)]
            over = None if None in over or len(over) < 11 else min(over)   # the night into the next morning
            per.append({"high": max(t), "low": min(night), "rain": sum(r), "evening": min(eve), "overnight": over})
        days[d] = day_row(per) if per else {"runs": 0, "note": "beyond this model's reach today"}
    bw = ev["burn_window"]
    idx = hours_of(times, bw["date"], int(bw["start"][:2]), int(bw["end"][:2]))
    per = []
    for m in mem.values():
        w = [m["wind_speed_10m"][i] for i in idx]
        if None in w or not w:
            continue
        g = [m.get("wind_gusts_10m", [None] * len(times))[i] for i in idx]
        per.append({"wind": max(w), "gust": max([x for x in g if x is not None], default=None),
                    "rain": sum(m["precipitation"][i] or 0.0 for i in idx),
                    "temp": min(m["temperature_2m"][i] for i in idx)})
    burn = {"runs": 0, "note": "the burn hours are beyond this model's reach today"} if not per else {
        "runs": len(per),
        "max_wind_mph": spread([p["wind"] for p in per]),
        "share_wind_at_least_15": shr([p["wind"] >= rules.WINDY_MPH for p in per]),
        "share_gust_at_least_25": shr([(p["gust"] or 0) >= rules.GUSTY_MPH for p in per]),
        "share_rain_at_least_0.1": shr([p["rain"] >= rules.WET_IN for p in per]),
        "coldest_f": spread([p["temp"] for p in per])}
    return {"days": days, "burn": burn}


def day_row(per: list[dict]) -> dict:
    over = [p["overnight"] for p in per if p.get("overnight") is not None]
    return {"runs": len(per), "high_f": spread([p["high"] for p in per]), "low_f": spread([p["low"] for p in per]),
            "evening_feels_f": spread([p["evening"] for p in per]),
            "overnight_low_f": spread(over) if over else None,
            "share_rain_at_least_0.1": shr([p["rain"] >= rules.WET_IN for p in per]),
            "share_rain_at_least_0.5": shr([p["rain"] >= rules.SOAKING_IN for p in per]),
            "share_low_at_or_below_40": shr([p["low"] <= rules.COLD_NIGHT_F for p in per]),
            "share_low_at_or_below_32": shr([p["low"] <= rules.FROST_F for p in per])}


def spread(xs: list[float]) -> dict:
    if len(xs) == 1:
        return {"median": round(xs[0])}
    dec = statistics.quantiles(xs, n=10, method="inclusive")
    return {"median": round(statistics.median(xs)), "p10": round(dec[0]), "p90": round(dec[-1])}


def shr(xs: list[bool]) -> float:
    return round(sum(xs) / len(xs), 2)


def nws(ev: dict) -> dict:
    """The NWS hourly forecast for the site's grid cell, reduced to the event's hours it reaches."""
    s = ev["site"]
    point = get_json(f"https://api.weather.gov/points/{s['lat']},{s['lon']}", "nws", "points", accept="application/geo+json")
    hourly = get_json(point["properties"]["forecastHourly"], "nws", "forecast-hourly", accept="application/geo+json")
    rows = []
    for p in hourly["properties"]["periods"]:
        t = p["startTime"][:16].replace("T", " ")
        if t[:10] in ev["days"]:
            rows.append({"time": t, "temp_f": p["temperature"], "wind": p["windSpeed"],
                         "rain_chance": (p.get("probabilityOfPrecipitation") or {}).get("value"),
                         "dew_c": (p.get("dewpoint") or {}).get("value"), "sky": p["shortForecast"]})
    return {"source": "National Weather Service hourly forecast, " + point["properties"]["gridId"]
            + f" grid {point['properties']['gridX']},{point['properties']['gridY']}",
            "issued": hourly["properties"].get("updateTime") or hourly["properties"].get("generatedAt"),
            "hours_in_event": len(rows), "hours": rows}


def ecmwf_direct(ev: dict) -> dict:
    """The fallback: ECMWF's own open data, daily, via tools/ecmwf_point.py, if its decoder is installed."""
    s = ev["site"]
    cmd = [sys.executable, str(ROOT / "tools" / "ecmwf_point.py"), "--lat", str(s["lat"]), "--lon", str(s["lon"]),
           "--tz", ev["timezone"], "--start", ev["days"][0], "--days", str(len(ev["days"])), "--ensemble", "--json"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if p.returncode:
        return {"error": (p.stderr or p.stdout).strip().splitlines()[-1:]}
    return json.loads(p.stdout)


def build(now: datetime | None = None) -> dict:
    ev = event()
    out = {"meaning": "Forecasts for Engulf's days and burn hours, as read on the date below; shares are of model runs.",
           "read_at": (now or datetime.now(ZoneInfo(ev["timezone"]))).isoformat(timespec="minutes"), "models": {}, "nws": None, "refused": []}
    for model, label in MODELS.items():
        try:
            raw = ensemble(ev, model)
            out["models"][label] = summarise(raw["hourly"]["time"], members(raw), ev)
        except Refused as e:
            out["refused"].append(str(e)[:300])
    if not out["models"]:
        out["models"]["ECMWF ENS (direct)"] = {"direct": ecmwf_direct(ev)}
    try:
        out["nws"] = nws(ev)
    except Refused as e:
        out["refused"].append(str(e)[:300])
    (ROOT / "data" / "forecast-latest.json").write_text(json.dumps(out, indent=1) + "\n")
    return out
