"""The daily reading: for each festival day, what the model runs show against what the same week has
done in 30 past years, then what to wear and eat; for the weekend, what to pack.

Every line comes from a number in data/. Words like "safe" or "dangerous" are never used (data
rule 8); the burn crew decides.
"""
from __future__ import annotations
import json
from datetime import date, datetime, timedelta
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
         "from": "the forecast" if reached else "a normal year (forecasts don't reach this day yet)"}
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


ABOUT_PAGE = [
    "Forecasts: the European (ECMWF) and US (NOAA) weather services, plus the National Weather Service once burn night is within a week. "
    "Each service runs its forecast dozens of times with small changes; the chances here are how often those versions agree.",
    "Normal year: the same week of November over the past 30 years, at the site and at McComb, Mississippi, the nearest airport weather station.",
    "The advice follows fixed rules of thumb, the same every time. It isn't Engulf's official word: the fire safety team decides what burns.",
    "Not checked: burn bans, flooding on the site itself, and wind under the trees at camp.",
]


def river_words(share: float | None) -> str:
    """The river's level against the same weeks of past years, in words."""
    if share is None:
        return "at an unknown level"
    if share < 0.1:
        return "very low"
    if share < 0.3:
        return "lower than normal"
    if share <= 0.7:
        return "about normal"
    return "higher than normal" if share <= 0.9 else "very high"


def drought_words(dr: dict) -> str:
    s = dr["share_of_parish"]
    when = datetime.fromisoformat(dr["map_date"]).strftime("%b %-d")
    severe = round(s["D2"] * 100)
    share = "all" if s["D1"] >= 0.995 else f"{round(s['D1'] * 100)}%"
    return (f"**The ground is dry.** As of {when}, {share} of Tangipahoa Parish "
            f"is in drought{f', and about {severe}% is in severe drought' if severe else ''} (US Drought Monitor). Dry spells are when "
            "parishes ban burning, and Engulf's rules say a ban can limit fire at the event. This page doesn't check for bans; "
            "the parish posts them at tangipahoa.org.")


def odds(p: float | None) -> str:
    if p is None:
        return "too far out to say"
    if p == 0:
        return "very unlikely"
    n = round(p * 10)
    if n == 0:
        return "unlikely (under 1 in 10)"
    return "almost certain" if n >= 10 else f"about {n} in 10"


def banner(today: date, burn: date) -> str:
    """The one line at the top: preliminary until the hour-by-hour forecast reaches burn night, a week out."""
    firm = burn - timedelta(days=7)
    if today < firm:
        return (f"This is preliminary until about {firm.strftime('%b %-d')}, when the hour-by-hour forecast for burn night comes in. "
                "It gets more accurate the closer we get to the burn.")
    return "Burn night is within a week, so this forecast is firming up. It gets more accurate every update until the burn."


def lead(today: date, first: date) -> str:
    n = (first - today).days
    if n > 15:
        return f"{n} days away. That's too far ahead for forecasts, so this shows a normal year."
    if n > 7:
        return f"{n} days away. Forecasts this far ahead are rough, so treat these as best guesses. This page updates twice a day."
    return f"{n} days away. Forecasts are getting firmer, and the hour-by-hour forecast for burn night is now in."


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
        lines.append(f"Forecasts don't reach this day yet. In a normal year it rains on about "
                     f"{round(sd['share_days_rain_at_least_0.1'] * 10)} of these days in 10, and about "
                     f"{round(sd['share_nights_at_or_below_40'] * 10)} nights in 10 drop to 40°F or below.")
    else:
        lines.append(f"Afternoon around {hi}°F (normal: {sd['high_f']['median']}°F). Early morning around {lo}°F (normal: {sd['low_f']['median']}°F).")
        lines.append(f"Chance of rain: {odds(wet)}. In a normal year it rains on about {round(sd['share_days_rain_at_least_0.1'] * 10)} of these days in 10.")
        if cold:
            lines.append(f"Chance of a night at 40°F or colder: {odds(cold)}." + (f" Chance of frost: {odds(frost)}." if frost else ""))
    burn = None
    if day == ev["burn_window"]["date"]:
        w, br = pooled_burn(models, "share_wind_at_least_15")
        g, _ = pooled_burn(models, "share_gust_at_least_25")
        r, _ = pooled_burn(models, "share_rain_at_least_0.1")
        m = astro.moon(datetime.fromisoformat(f"{day}T22:00").replace(tzinfo=ZoneInfo(ev["timezone"])))
        burn = {"runs": br, "share_wind_at_least_15": w, "share_gust_at_least_25": g, "share_rain_at_least_0.1": r, "moon": m}
        if br:
            lines.append(f"Burn night, 7 pm to midnight. Chance of wind 15 mph or stronger: {odds(w)}. "
                         f"Gusts 25 mph or stronger: {odds(g)}. Rain: {odds(r)}.")
        else:
            lines.append("Forecasts don't reach burn night yet.")
        lines.append(f"Over the past 30 years, wind on mid-November nights here usually tops out around "
                     f"{bh['median_max_wind_mph_burn_hours']} mph; it reached 15 mph on about 1 night in 25.")
        lines.append(f"Moon: a thin crescent, {round(m['illuminated'] * 100)}% lit. A dark sky for the burns.")
    if i == 3:
        rv = ground.get("river", {})
        if rv.get("flow_cfs") is not None:
            lines.append(f"The nearby Tangipahoa River is {river_words(rv['share_of_same_weeks_at_or_below'])} for this time of year.")
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
           "banner": banner(today, date.fromisoformat(ev["burn_window"]["date"])),
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
    L = [f"# Engulf weather, read {r['written_on']}", "", f"**{r['banner']}**", "",
         f"_{r['lead']}_ Forecast read {r['forecast_read_at']}.", ""]
    dr = r.get("drought") or {}
    if dr.get("share_of_parish"):
        s = dr["share_of_parish"]
        L += [drought_words(dr), ""]
    L += ["## Pack for the weekend", "", "_Packed for a colder-than-expected weekend. A layer you didn't need beats one you didn't bring._", ""]
    L += [f"- {x}" for x in r["packing"]] + [""]
    for d in r["days"]:
        L += [f"## {datetime.fromisoformat(d['date']).strftime('%A %b %-d')}: {d['about']}",
              f"_Sunrise {d['sunrise']}, sunset {d['sunset']}._", ""] + [f"- {x}" for x in d["lines"]] + [""]
        L += ["**Wear:**", ""] + [f"- {x}" for x in d["kit"]["wear"]] + [""]
        L += ["**Eat:**", ""] + [f"- {x}" for x in d["kit"]["eat"]] + [""]
    L += ["## Where this comes from", "", *[f"- {x}" for x in ABOUT_PAGE], ""]
    if r.get("refused"):
        L += ["**Some sources didn't answer this time:** " + "; ".join(r["refused"]), ""]
    return "\n".join(L)
