#!/usr/bin/env python3
"""Daily highs, lows and rain for any point from ECMWF's own open data, for when Open-Meteo refuses.

Open-Meteo's free tier counts calls per internet address, so a shared cloud machine can find the day's
quota spent before it asks (2026-10-30: "Daily API request limit exceeded" from a Claude cloud session).
ECMWF publishes the same IFS model's forecasts itself, free and without a key, at data.ecmwf.int:
the 00 and 12 UTC runs out to 15 days (360 h), on a 0.25° grid, under CC BY 4.0. This tool takes the
newest of those runs that reaches 360 h and reads one model cell, the one nearest the point.

The numbers are a model forecast for a cell about 25 km across, not a station's, and past about a
week a single run is one guess among many. `--ensemble` reads ECMWF's 50 perturbed runs instead and
reports their middle and spread, which is the honest form for days 8 to 15. Highs and lows are the
model's 6-hour maximum and minimum 2 m temperature (`mx2t6`, `mn2t6`); rain is total precipitation
(`tp`) differenced over the same windows. A 6-hour window counts toward the local day its midpoint
falls in, so in time zones not six hours from UTC a window can straddle midnight.

It is a lookup, not a collector: nothing here is scheduled, and nothing it prints is published from
this repo. It needs ECMWF's GRIB decoder, which the standard library does not have, so it runs in its
own environment (`requirements-ecmwf.txt`); `collect.py` and the planner never import it.

    python3 -m venv ~/.venvs/ecmwf && ~/.venvs/ecmwf/bin/pip install -r requirements-ecmwf.txt
    ~/.venvs/ecmwf/bin/python tools/ecmwf_point.py --lat 30.938 --lon -90.508 \\
        --tz America/Chicago --start 2026-11-11 --days 3 --ensemble
    ... --json             # the same, with the run, model cell and file hashes, as JSON
"""
from __future__ import annotations
import argparse, hashlib, json, statistics, sys, tempfile
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LAST_STEP = 360      # hours; the 00 and 12 UTC runs reach 15 days, the 06 and 18 UTC runs do not
WINDOW = 6           # hours covered by each mx2t6, mn2t6 and tp difference
RAIN_SOME_IN = 0.1   # the shares reported: members with at least this much rain in the day
RAIN_HEAVY_IN = 0.5
SOURCE = "ECMWF IFS open data (data.ecmwf.int), CC BY 4.0"


def k_to_f(k: float) -> float:
    return (k - 273.15) * 9 / 5 + 32


def m_to_in(m: float) -> float:
    return m * 39.3701


def local_span(start: date, days: int, tz: ZoneInfo) -> tuple[datetime, datetime]:
    """UTC instants of local midnight at the start and after the last day."""
    a = datetime.combine(start, time(0), tz).astimezone(timezone.utc)
    b = datetime.combine(start + timedelta(days=days), time(0), tz).astimezone(timezone.utc)
    return a, b


def window_steps(run: datetime, start_utc: datetime, end_utc: datetime) -> list[int]:
    """Steps whose 6-hour window ends at run+step and has its midpoint inside [start_utc, end_utc)."""
    out = []
    for step in range(WINDOW, LAST_STEP + 1, WINDOW):
        mid = run + timedelta(hours=step - WINDOW / 2)
        if start_utc <= mid < end_utc:
            out.append(step)
    return out


def day_of(run: datetime, step: int, tz: ZoneInfo) -> date:
    return (run + timedelta(hours=step - WINDOW / 2)).astimezone(tz).date()


def summarise(values: dict, run: datetime, steps: list[int], tz: ZoneInfo) -> list[dict]:
    """Per local day: high, low and rain, as one value or as the members' middle and spread.

    `values` maps (shortName, member, endStep) to the cell's value in GRIB units (K, m). Rain at a
    step is the accumulation since the run began; the window's rain is that minus the value at
    step - 6, or minus zero at the run's start.
    """
    members = sorted({n for (_, n, _) in values})
    days: dict[date, list[int]] = {}
    for s in steps:
        days.setdefault(day_of(run, s, tz), []).append(s)
    out = []
    for d, ss in sorted(days.items()):
        his, los, rains = [], [], []
        for n in members:
            his.append(k_to_f(max(values[("mx2t6", n, s)] for s in ss)))
            los.append(k_to_f(min(values[("mn2t6", n, s)] for s in ss)))
            rains.append(m_to_in(sum(values[("tp", n, s)] - (values[("tp", n, s - WINDOW)] if s > WINDOW else 0.0)
                                     for s in ss)))
        row = {"date": d.isoformat(), "windows": len(ss), "complete": len(ss) == 24 // WINDOW}
        if len(members) == 1:
            row.update(high_f=round(his[0]), low_f=round(los[0]), rain_in=round(max(rains[0], 0.0), 2))
        else:
            row.update(high_f=spread(his), low_f=spread(los),
                       rain_in={"median": round(max(statistics.median(rains), 0.0), 2),
                                "share_at_least_0.1": round(sum(r >= RAIN_SOME_IN for r in rains) / len(rains), 2),
                                "share_at_least_0.5": round(sum(r >= RAIN_HEAVY_IN for r in rains) / len(rains), 2),
                                "max": round(max(rains), 2)},
                       members=len(members))
        out.append(row)
    return out


def spread(xs: list[float]) -> dict:
    """Middle, the band holding 8 runs in 10, and the extremes, in whole degrees."""
    dec = statistics.quantiles(xs, n=10, method="inclusive")
    return {"median": round(statistics.median(xs)), "p10": round(dec[0]), "p90": round(dec[-1]),
            "min": round(min(xs)), "max": round(max(xs))}


def tp_steps(steps: list[int]) -> list[int]:
    """The tp steps needed: each window's end and the step before it, never step 0."""
    return sorted({s for s in steps} | {s - WINDOW for s in steps if s > WINDOW})


def read_point(path: Path, lat: float, lon: float, values: dict) -> tuple[float, float]:
    """Add the nearest cell's value from every GRIB message in `path`; return the cell centre."""
    import eccodes
    cell = (float("nan"), float("nan"))
    with open(path, "rb") as f:
        while (h := eccodes.codes_grib_new_from_file(f)) is not None:
            try:
                name = eccodes.codes_get(h, "shortName")
                step = int(eccodes.codes_get(h, "endStep"))
                member = eccodes.codes_get(h, "number") if eccodes.codes_is_defined(h, "number") else 0
                near = eccodes.codes_grib_find_nearest(h, lat, lon)[0]
                values[(name, member, step)] = near["value"]
                cell = (near["lat"], near["lon"])
            finally:
                eccodes.codes_release(h)
    return cell


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fetch(args: argparse.Namespace, raw: Path) -> dict:
    from ecmwf.opendata import Client
    tz = ZoneInfo(args.tz)
    client = Client(source="ecmwf")
    run = client.latest(type="fc", step=LAST_STEP, param="2t").replace(tzinfo=timezone.utc)
    start = date.fromisoformat(args.start)
    steps = window_steps(run, *local_span(start, args.days, tz))
    if not steps:
        raise SystemExit(f"the {run:%Y-%m-%d %H} UTC run does not reach {start} (it ends {run + timedelta(hours=LAST_STEP):%Y-%m-%d %H} UTC)")
    kind = "pf" if args.ensemble else "fc"
    base = dict(date=run.strftime("%Y%m%d"), time=run.hour, type=kind)
    files = {"temperature": raw / f"{kind}-mx2t6-mn2t6.grib2", "rain": raw / f"{kind}-tp.grib2"}
    client.retrieve(**base, param=["mx2t6", "mn2t6"], step=steps, target=str(files["temperature"]))
    client.retrieve(**base, param=["tp"], step=tp_steps(steps), target=str(files["rain"]))
    values: dict = {}
    cell = read_point(files["temperature"], args.lat, args.lon, values)
    read_point(files["rain"], args.lat, args.lon, values)
    return {"source": SOURCE, "run_utc": run.strftime("%Y-%m-%dT%H:%MZ"), "kind": "ensemble, 50 perturbed runs" if args.ensemble else "single run (HRES)",
            "point": {"lat": args.lat, "lon": args.lon}, "model_cell": {"lat": cell[0], "lon": cell[1], "grid": "0.25°"},
            "timezone": args.tz, "files": {k: {"name": p.name, "sha256": sha256(p), "bytes": p.stat().st_size} for k, p in files.items()},
            "days": summarise(values, run, steps, tz),
            "caveat": "Model forecast for one 0.25° cell, not a station. Highs and lows are 6-hour model extremes; rain is the model's total precipitation."}


def show(r: dict) -> str:
    lines = [f"{r['source']}, run {r['run_utc']}, {r['kind']}",
             f"cell nearest {r['point']['lat']}, {r['point']['lon']}: {r['model_cell']['lat']}, {r['model_cell']['lon']} ({r['model_cell']['grid']})", ""]
    for d in r["days"]:
        if not d["complete"]:
            lines.append(f"{d['date']}  not shown: the run covers only {d['windows'] * WINDOW} of its 24 hours")
            continue
        tag = ""
        if "members" in d:
            h, l, p = d["high_f"], d["low_f"], d["rain_in"]
            lines.append(f"{d['date']}  high {h['median']}°F (8 in 10 runs {h['p10']}–{h['p90']})  "
                         f"low {l['median']}°F ({l['p10']}–{l['p90']}, coldest {l['min']})  "
                         f"rain: {round(p['share_at_least_0.1'] * 100)}% of runs ≥0.1 in{tag}")
        else:
            lines.append(f"{d['date']}  high {d['high_f']}°F  low {d['low_f']}°F  rain {d['rain_in']:.2f} in{tag}")
    lines += ["", r["caveat"]]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--tz", default="America/Chicago", help="IANA zone the days are counted in")
    ap.add_argument("--start", default=date.today().isoformat(), help="first local day, YYYY-MM-DD")
    ap.add_argument("--days", type=int, default=3)
    ap.add_argument("--ensemble", action="store_true", help="the 50 perturbed runs (about 170 MB for 3 days) instead of one")
    ap.add_argument("--raw", help="keep the GRIB files here (default: a temporary folder, deleted after)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.raw:
        raw = Path(args.raw); raw.mkdir(parents=True, exist_ok=True)
        result = fetch(args, raw)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            result = fetch(args, Path(tmp))
    print(json.dumps(result, indent=1, ensure_ascii=False) if args.json else show(result))


if __name__ == "__main__":
    sys.exit(main())
