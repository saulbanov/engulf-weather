"""The ground under the weather: how dry the parish is, and how the river runs against its own past.

* Drought: the US Drought Monitor's weekly map for Tangipahoa Parish (FIPS 22105), as the share of
  the parish in each category or worse (D0 abnormally dry to D4 exceptional). It is an expert
  blend of indicators, published Thursdays for the week before. Dry ground is why parishes issue
  burn bans, and Engulf's flame-effect policy says a burn ban can restrict fire at the event.
  Whether a ban is in force is NOT read here: no machine-readable source was found; the parish
  posts them at tangipahoa.org.
* River: the Tangipahoa River at Osyka, MS (USGS 07375280), the nearest gauge with a long
  discharge record (daily means since 1996, live readings every 15 minutes), 9 km north-west of
  the site. Today's flow is placed among the daily means for the same two weeks of the year in
  every year of its record. The method is hill-country-hydro's: the gauge against its own past,
  no verdict. Whether the site drains to this river was not checked.
"""
from __future__ import annotations
import json
from datetime import date, datetime
from . import ROOT
from .fetch import get_json

USDM = ("https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"
        "?aoi=22105&startdate={a}&enddate={b}&statisticsType=1")
RIVER = "07375280"
RIVER_NAME = "Tangipahoa River at Osyka, MS (USGS 07375280)"
DAILY = ("https://api.waterdata.usgs.gov/ogcapi/v1/collections/daily/items?f=json&monitoring_location_id=USGS-{s}"
         "&parameter_code=00060&statistic_id=00003&limit=50000&skipGeometry=true&properties=time,value")
IV = "https://waterservices.usgs.gov/nwis/iv/?format=json&sites={s}&parameterCd=00060&period=P1D"


def drought(today: date) -> dict:
    a = date(today.year, today.month, 1) if today.day > 14 else date(today.year - (today.month == 1), (today.month - 2) % 12 + 1, 1)
    rows = get_json(USDM.format(a=a.strftime("%m/%d/%Y"), b=today.strftime("%m/%d/%Y")), "usdm", "tangipahoa")
    rows = sorted(rows, key=lambda r: r["mapDate"])
    if not rows:
        return {"error": "no Drought Monitor rows returned"}
    last = rows[-1]
    return {"source": "US Drought Monitor, county statistics (percent of area, category or worse)",
            "parish": last["county"], "map_date": last["mapDate"][:10],
            "share_of_parish": {k: round(float(last[k.lower()]) / 100, 2) for k in ("D0", "D1", "D2", "D3", "D4")},
            "weeks": [{"map_date": r["mapDate"][:10], "D1_or_worse": round(float(r["d1"]) / 100, 2),
                       "D2_or_worse": round(float(r["d2"]) / 100, 2)} for r in rows],
            "burn_ban": "not checked: see tangipahoa.org; bans are issued and lifted at short notice"}


def percentile_of(x: float, xs: list[float]) -> float:
    """Share of the record at or below x (a Weibull-free plain rank, enough for words like 'lowest tenth')."""
    return round(sum(v <= x for v in xs) / len(xs), 2)


def same_weeks(rows: list[tuple[str, float]], today: date, half: int = 7) -> list[float]:
    doy = today.timetuple().tm_yday
    out = []
    for t, v in rows:
        d = date.fromisoformat(t)
        if d.year == today.year:
            continue
        if abs(d.timetuple().tm_yday - doy) <= half:
            out.append(v)
    return out


def river(today: date, keep_history: bool = False) -> dict:
    # The 30-year daily record is ~330 KB gzipped and changes by a day at a time. The pulls of
    # 2026-10-31 are kept in data/captures/usgs/; the daily run records only its hash in the manifest.
    feats = get_json(DAILY.format(s=RIVER), "usgs", f"{RIVER}-daily", keep=keep_history)["features"]
    rows = [(f["properties"]["time"], float(f["properties"]["value"])) for f in feats
            if f["properties"].get("value") not in (None, "")]
    iv = get_json(IV.format(s=RIVER), "usgs", f"{RIVER}-iv")["value"]["timeSeries"]
    vals = iv[0]["values"][0]["value"] if iv else []
    now = (float(vals[-1]["value"]), vals[-1]["dateTime"]) if vals else (rows[-1][1], rows[-1][0])
    past = same_weeks(rows, today)
    years = sorted({t[:4] for t, _ in rows})
    return {"source": RIVER_NAME, "flow_cfs": now[0], "at": now[1],
            "record": f"daily means {years[0]}–{years[-1]}", "same_weeks_values": len(past),
            "share_of_same_weeks_at_or_below": percentile_of(now[0], past) if past else None,
            "median_same_weeks_cfs": sorted(past)[len(past) // 2] if past else None,
            "caveat": "Live readings are provisional. The record is daily means; today's value is one 15-minute reading."}


def recent(today: date, days: int = 30) -> dict:
    """The last `days` days at McComb against its 1991-2020 normals (ACIS): how warm and wet the fall has run."""
    import json as _json, urllib.parse
    from datetime import timedelta
    end, start = today - timedelta(days=1), today - timedelta(days=days)
    q = {"sid": "MCB", "sdate": start.isoformat(), "edate": end.isoformat(), "meta": "name",
         "elems": [{"name": "maxt", "normal": "departure"}, {"name": "mint", "normal": "departure"},
                   {"name": "pcpn"}, {"name": "pcpn", "normal": "1"}]}
    rows = get_json("https://data.rcc-acis.org/StnData?params=" + urllib.parse.quote(_json.dumps(q, separators=(",", ":"))),
                    "acis-station", "MCB-recent")["data"]
    num = lambda x: None if x in ("M", "", None) else (0.0 if x == "T" else float(x))
    hi = [num(r[1]) for r in rows if num(r[1]) is not None]
    lo = [num(r[2]) for r in rows if num(r[2]) is not None]
    wet = [(num(r[3]), num(r[4])) for r in rows if num(r[3]) is not None and num(r[4]) is not None]
    return {"source": "McComb, MS airport (ACIS), against its 1991-2020 normals", "from": start.isoformat(), "to": end.isoformat(),
            "days_reported": len(wet), "highs_vs_normal_f": round(sum(hi) / len(hi), 1) if hi else None,
            "lows_vs_normal_f": round(sum(lo) / len(lo), 1) if lo else None,
            "rain_in": round(sum(a for a, _ in wet), 2) if wet else None,          # no reports is unknown, not dry
            "normal_rain_in": round(sum(b for _, b in wet), 2) if wet else None}


def build(today: date | None = None) -> dict:
    today = today or date.today()
    out = {"meaning": "Drought and river state near Engulf's site, read on the date below.", "read_on": today.isoformat()}
    for k, f in (("drought", drought), ("river", river), ("recent", recent)):
        try:
            out[k] = f(today)
        except Exception as e:          # a refusal is reported, never filled in
            out[k] = {"error": str(e)[:300]}
    (ROOT / "data" / "ground-latest.json").write_text(json.dumps(out, indent=1) + "\n")
    return out
