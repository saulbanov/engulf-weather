"""The daily reading: for each festival day, what the model runs show against what the same week has
done in 30 past years, then what to wear and eat; for the weekend, what to pack.

Every line comes from a number in data/. Words like "safe" or "dangerous" are never used (data
rule 8); the burn crew decides.
"""
from __future__ import annotations
import json
from datetime import date, datetime
from zoneinfo import ZoneInfo
from . import ROOT, event, astro, kit, rules

ABOUT = {0: "arrival and setup; gates 10 am to 10 pm",
         1: "the full day on site",
         2: "burn night: temple around 8 pm, effigy around 10 pm",
         3: "exodus: off the land by 5 pm"}


def pooled(models: dict, day: str, key: str) -> tuple[float | None, int]:
    """Share of all runs (every ensemble that reaches the day) showing `key`, and the run count."""
    yes = runs = 0
    for m in models.values():
        d = m.get("days", {}).get(day, {})
        if d.get("runs"):
            yes += d[key] * d["runs"]; runs += d["runs"]
    return (round(yes / runs, 2) if runs else None), runs


def pooled_burn(models: dict, key: str) -> tuple[float | None, int]:
    yes = runs = 0
    for m in models.values():
        b = m.get("burn", {})
        if b.get("runs"):
            yes += b[key] * b["runs"]; runs += b["runs"]
    return (round(yes / runs, 2) if runs else None), runs


def median_of(models: dict, day: str, key: str, stat: str = "median") -> int | None:
    """Across the models that reach the day: the mean of their medians, the lowest p10 or the highest p90."""
    vals = [(m["days"][day].get(key) or {}).get(stat) for m in models.values() if m.get("days", {}).get(day, {}).get("runs")]
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {"median": round(sum(vals) / len(vals)), "p10": min(vals), "p90": max(vals)}[stat]


def wear_eat(i: int, day: str, models: dict, clim: dict, ev: dict) -> dict:
    """Clothes for three parts of the day and a meal plan; the climatology stands in where no run reaches."""
    sd, bh = clim["site_daily"], clim["burn_hours"]
    reached = bool(reach(models, day))
    k = {"high_f": median_of(models, day, "high_f") if reached else sd["high_f"]["median"],
         "morning_f": median_of(models, day, "low_f") if reached else sd["low_f"]["median"],
         "evening_feels_f": median_of(models, day, "evening_feels_f") if reached else bh["evening_feels_f"]["median"],
         "overnight_f": median_of(models, day, "overnight_low_f") if reached else bh["overnight_low_f"]["median"],
         "high_p90_f": median_of(models, day, "high_f", "p90") if reached else sd["high_f"]["p90"],
         "evening_p10_f": median_of(models, day, "evening_feels_f", "p10") if reached else bh["evening_feels_f"]["p10"],
         "overnight_p10_f": median_of(models, day, "overnight_low_f", "p10") if reached else bh["overnight_low_f"]["p10"],
         "from": "the model runs" if reached else "past years (no run reaches this day yet)"}
    last = i == len(ev["days"]) - 1
    if last:
        k["overnight_f"] = k["overnight_p10_f"] = k["evening_p10_f"] = None
    wear = [f"Afternoon (near {k['high_f']}°F): {kit.dress(k['high_f'])}."]
    if not last:
        wear.append(f"After dark (feels near {k['evening_feels_f']}°F): {kit.dress(k['evening_feels_f'])}.")
        if k["overnight_f"] is not None:
            wear.append(f"Overnight (low near {k['overnight_f']}°F): sleep in {kit.sleepwear(k['overnight_f'])}.")
    k["wear"] = wear
    sunset = astro.sun(date.fromisoformat(day), ev["site"]["lat"], ev["site"]["lon"], ev["timezone"])[1].strftime("%-I:%M pm")
    k["eat"] = kit.meals(k, day == ev["burn_window"]["date"], last, i == 0, sunset)
    return k


def reach(models: dict, day: str) -> list[str]:
    return [name for name, m in models.items() if m.get("days", {}).get(day, {}).get("runs")]


def any_rain(models: dict, ev: dict) -> float | None:
    """The highest pooled share of runs showing 0.1 in or more on any one festival day."""
    vals = [pooled(models, d, "share_rain_at_least_0.1")[0] for d in ev["days"]]
    vals = [v for v in vals if v is not None]
    return max(vals) if vals else None


def odds(p: float | None) -> str:
    if p is None:
        return "not yet in any model's reach"
    if p == 0:
        return "no run shows it"
    n = round(p * 10)
    if n == 0:
        return "fewer than 1 run in 10"
    return "nearly every run" if n >= 10 else f"about {n} run{'s' if n > 1 else ''} in 10"


def lead(today: date, first: date) -> str:
    n = (first - today).days
    if n > 15:
        return f"{n} days out: past every forecast's reach, so this is the climatology alone."
    if n > 7:
        return f"{n} days out: ensembles only. Read the shares as leanings, not plans."
    return f"{n} days out: ensembles plus the National Weather Service's hourly forecast."


def day_reading(i: int, day: str, f: dict, clim: dict, ground: dict, ev: dict) -> dict:
    models = f["models"]
    about = ABOUT[i]
    wet, runs = pooled(models, day, "share_rain_at_least_0.1")
    soak, _ = pooled(models, day, "share_rain_at_least_0.5")
    cold, _ = pooled(models, day, "share_low_at_or_below_40")
    frost, _ = pooled(models, day, "share_low_at_or_below_32")
    hi, lo = median_of(models, day, "high_f"), median_of(models, day, "low_f")
    sd, bh = clim["site_daily"], clim["burn_hours"]
    lines = []
    if runs == 0:
        lines.append(f"The models have not reached this day yet. In past years it has rained 0.1 in or more on "
                     f"{round(sd['share_days_rain_at_least_0.1'] * 100)}% of these days, and "
                     f"{round(sd['share_nights_at_or_below_40'] * 100)}% of nights have dropped to 40°F or below.")
    else:
        lines.append(f"{runs} runs from {', '.join(reach(models, day))}. Afternoon near {hi}°F (the week's usual is {sd['high_f']['median']}°F); "
                     f"morning low near {lo}°F (usual {sd['low_f']['median']}°F).")
        lines.append(f"Rain of 0.1 in or more: {odds(wet)} (in past years, {round(sd['share_days_rain_at_least_0.1'] * 100)}% of these days).")
        if cold:
            lines.append(f"A night at 40°F or colder: {odds(cold)}." + (f" Frost: {odds(frost)}." if frost else ""))
    burn = None
    if day == ev["burn_window"]["date"]:
        w, br = pooled_burn(models, "share_wind_at_least_15")
        g, _ = pooled_burn(models, "share_gust_at_least_25")
        r, _ = pooled_burn(models, "share_rain_at_least_0.1")
        m = astro.moon(datetime.fromisoformat(f"{day}T22:00").replace(tzinfo=ZoneInfo(ev["timezone"])))
        burn = {"runs": br, "share_wind_at_least_15": w, "share_gust_at_least_25": g, "share_rain_at_least_0.1": r, "moon": m}
        if br:
            lines.append(f"Burn hours (7 pm to midnight), {br} runs: wind of 15 mph or more, {odds(w)}; gusts of 25 mph or more, "
                         f"{odds(g)}; rain, {odds(r)}.")
        lines.append(f"Thirty years at McComb: burn-hour wind reached 15 mph on {round(bh['share_nights_wind_at_least_15'] * 100)}% "
                     f"of mid-November nights; the usual peak is {bh['median_max_wind_mph_burn_hours']} mph.")
        lines.append(f"Moon: {m['phase']}, {round(m['illuminated'] * 100)}% lit, so a dark sky around the burns.")
    if i == 3:
        rv = ground.get("river", {})
        if rv.get("flow_cfs") is not None:
            lines.append(f"The Tangipahoa at Osyka runs {rv['flow_cfs']:g} cfs, at or above "
                         f"{round(rv['share_of_same_weeks_at_or_below'] * 100)}% of past readings for these weeks.")
    rise, set_ = astro.sun(date.fromisoformat(day), ev["site"]["lat"], ev["site"]["lon"], ev["timezone"])
    return {"kit": wear_eat(i, day, models, clim, ev), "date": day, "about": about, "runs": runs, "lines": lines,
            "sunrise": rise.strftime("%-I:%M am"), "sunset": set_.strftime("%-I:%M pm"),
            "high_f": hi, "low_f": lo, "share_rain_at_least_0.1": wet, "share_low_at_or_below_40": cold, "burn": burn}


def build(today: date | None = None) -> dict:
    ev = event()
    today = today or datetime.now(ZoneInfo(ev["timezone"])).date()
    clim = json.loads((ROOT / "data" / "climatology.json").read_text())
    f = json.loads((ROOT / "data" / "forecast-latest.json").read_text())
    ground = json.loads((ROOT / "data" / "ground-latest.json").read_text())
    days = [day_reading(i, d, f, clim, ground, ev) for i, d in enumerate(ev["days"])]
    out = {"meaning": "Engulf weather reading: each day's forecast against past years, and what to wear, pack and eat.",
           "written_on": today.isoformat(), "forecast_read_at": f["read_at"], "lead": lead(today, date.fromisoformat(ev["days"][0])),
           "days": days, "drought": ground.get("drought"), "refused": f.get("refused", []),
           "packing": kit.packing([d["kit"] for d in days], any_rain(f["models"], ev), clim["burn_hours"].get("share_predawn_hours_dewy"),
                                 clim["burn_hours"]["overnight_low_f"]["p10"], clim["burn_hours"]["evening_feels_f"]["p10"])}
    (ROOT / "readings").mkdir(exist_ok=True)
    (ROOT / "readings" / "latest.json").write_text(json.dumps(out, indent=1) + "\n")
    md = render(out, clim)
    (ROOT / "readings" / f"{today.isoformat()}.md").write_text(md)
    (ROOT / "readings" / "latest.md").write_text(md)
    return out


def render(r: dict, clim: dict) -> str:
    L = [f"# Engulf weather, read {r['written_on']}", "",
         f"_{r['lead']}_ Forecast read {r['forecast_read_at']}.", ""]
    dr = r.get("drought") or {}
    if dr.get("share_of_parish"):
        s = dr["share_of_parish"]
        L += [f"**The ground:** on the US Drought Monitor's {dr['map_date']} map, {round(s['D1'] * 100)}% of Tangipahoa Parish is in "
              f"moderate drought or worse and {round(s['D2'] * 100)}% in severe. Dry parishes issue burn bans; Engulf's "
              f"flame-effect policy says a ban can restrict fire at the event. Burn ban status: {dr['burn_ban']}.", ""]
    L += ["## Pack for the weekend", "", "_Planned for the cold end of the runs: a layer you didn't need costs less than one you didn't bring._", ""]
    L += [f"- {x}" for x in r["packing"]] + [""]
    for d in r["days"]:
        L += [f"## {datetime.fromisoformat(d['date']).strftime('%A %b %-d')}: {d['about']}",
              f"_Sunrise {d['sunrise']}, sunset {d['sunset']}._", ""] + [f"- {x}" for x in d["lines"]] + [""]
        L += [f"**Wear** (from {d['kit']['from']}):", ""] + [f"- {x}" for x in d["kit"]["wear"]] + [""]
        L += ["**Eat:**", ""] + [f"- {x}" for x in d["kit"]["eat"]] + [""]
    L += ["## How to read this", "",
          "- Shares are of model runs: ECMWF's 51-run ensemble and NOAA's 31-run GEFS, pooled where both reach the day. "
          "They are leanings, not promises; past about a week no single forecast is better than the spread.",
          f"- \"Usual\" and \"past years\" mean {clim['window']}, {clim['site_daily']['years'][0]}–{clim['site_daily']['years'][1]}: "
          "highs, lows and rain from PRISM's 4 km grid (modelled); burn-hour wind from McComb's airport station 26 km north (measured).",
          "- The thresholds are in `engulf/rules.py`; they are planning lines, not Engulf policy. The Fire Art Response Team and burn leads decide what burns.",
          "- Data: `data/forecast-latest.json`, `data/climatology.json`, `data/ground-latest.json`; every download is kept in `data/captures/` and listed in `data/manifest.jsonl`.", ""]
    if r.get("refused"):
        L += ["**Sources that refused today:** " + "; ".join(r["refused"]), ""]
    return "\n".join(L)
