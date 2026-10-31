"""The public page: site/index.html and site/data.json, rendered from the saved data and nothing else.

Deterministic by design: the page is a pure function of data/forecast-latest.json,
data/ground-latest.json, data/climatology.json and readings/latest.json. The same files give the same
bytes; there is no clock in here, and the "updated" time on the page is the time the forecast was
read. No JavaScript, no web fonts, no external requests: one HTML file with its CSS inline.
"""
from __future__ import annotations
import json
from datetime import datetime
from html import escape
from . import ROOT, event, reading, rules

OUT = ROOT / "site"
REPO = "https://github.com/saulbanov/engulf-weather"


def e(x) -> str:
    return escape("" if x is None else str(x))


def pct(p: float | None) -> str:
    return "—" if p is None else f"{round(p * 100)}%"


def rng(s: dict | None, unit: str = "°F") -> str:
    """A middle value with its likely range, e.g. '72°F (60–76)'."""
    if not s:
        return "—"
    if "p10" not in s:
        return f"{s['median']}{unit}"
    return f"{s['median']}{unit} <span class=band>({s['p10']}–{s['p90']})</span>"


def chance(p: float | None) -> str:
    """A chance in words a reader can use: '1 in 10', 'unlikely'."""
    if p is None:
        return "—"
    if p == 0:
        return "very unlikely"
    n = round(p * 10)
    if n == 0:
        return "under 1 in 10"
    return "almost certain" if n >= 10 else f"{n} in 10"


def pooled_spread(parts: list[dict]) -> dict | None:
    """Several forecasts' middle-and-range blocks as one: average middle, widest range."""
    parts = [x for x in parts if x]
    if not parts:
        return None
    out = {"median": round(sum(x["median"] for x in parts) / len(parts))}
    if all("p10" in x for x in parts):
        out.update(p10=min(x["p10"] for x in parts), p90=max(x["p90"] for x in parts))
    return out


def pooled_share(parts: list[tuple[float, int]]) -> float | None:
    parts = [(v, n) for v, n in parts if n]
    total = sum(n for _, n in parts)
    return round(sum(v * n for v, n in parts) / total, 2) if total else None


def day_name(d: str) -> str:
    return datetime.fromisoformat(d).strftime("%a %b %-d")


def table(head: list[str], rows: list[list[str]], cls: str = "") -> str:
    h = "".join(f"<th scope=col>{x}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" if i else f"<th scope=row>{c}</th>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class=scroll><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def days_table(ev: dict, f: dict, clim: dict) -> str:
    sd, bh = clim["site_daily"], clim["burn_hours"]
    rows = []
    for d in ev["days"]:
        xs = [m["days"][d] for m in f["models"].values() if m.get("days", {}).get(d, {}).get("runs")]
        if not xs:
            rows.append([day_name(d), "too far out", "", "", "", "", ""])
            continue
        g = lambda k: pooled_spread([x.get(k) for x in xs])
        c = lambda k: chance(pooled_share([(x[k], x["runs"]) for x in xs if k in x]))
        rows.append([day_name(d), rng(g("high_f")), rng(g("low_f")), rng(g("evening_feels_f")), rng(g("overnight_low_f")),
                     c("share_rain_at_least_0.1"), c("share_low_at_or_below_40")])
    rows.append(["Normal year", rng(sd["high_f"]), rng(sd["low_f"]), rng(bh["evening_feels_f"]), rng(bh["overnight_low_f"]),
                 chance(sd["share_days_rain_at_least_0.1"]), chance(sd["share_nights_at_or_below_40"])])
    return table(["Day", "Afternoon", "Early morning", "Evening, with wind", "Overnight low", "Chance of rain",
                  f"Chance of a night {rules.COLD_NIGHT_F}°F or colder"], rows, "days")


def burn_table(ev: dict, f: dict, clim: dict) -> str:
    bh = clim["burn_hours"]
    bs = [m["burn"] for m in f["models"].values() if m.get("burn", {}).get("runs")]
    rows = []
    if bs:
        share = lambda k: chance(pooled_share([(b[k], b["runs"]) for b in bs]))
        rows.append(["Forecast", rng(pooled_spread([b["max_wind_mph"] for b in bs]), " mph"), share("share_wind_at_least_15"),
                     share("share_gust_at_least_25"), share("share_rain_at_least_0.1"), rng(pooled_spread([b["coldest_f"] for b in bs]))])
    else:
        rows.append(["Forecast", "too far out", "", "", "", ""])
    rows.append(["Normal year", f"{bh['median_max_wind_mph_burn_hours']} mph", chance(bh["share_nights_wind_at_least_15"]),
                 chance(bh["share_nights_gust_at_least_25"]), chance(bh["share_nights_rain_at_least_0.1"]), rng(bh["evening_feels_f"])])
    return table(["", "Strongest wind", f"Chance of wind {rules.WINDY_MPH}+ mph", f"Chance of gusts {rules.GUSTY_MPH}+ mph",
                  "Chance of rain", "Coldest, with wind"], rows)


def nws_table(ev: dict, f: dict) -> str:
    n = f.get("nws") or {}
    bw = ev["burn_window"]
    hours = [h for h in n.get("hours", []) if h["time"][:10] == bw["date"] and bw["start"][:2] <= h["time"][11:13]]
    if not hours:
        return "<p class=note>An hour-by-hour forecast for burn night appears here about a week before, around Nov 7.</p>"
    rows = [[datetime.fromisoformat(h["time"].replace(" ", "T")).strftime("%-I %p"), f"{h['temp_f']}°F", e(h["wind"]),
             "—" if h["rain_chance"] is None else f"{h['rain_chance']}%", e(h["sky"])] for h in hours]
    return "<h3>Hour by hour (National Weather Service)</h3>" + table(["Time", "Temperature", "Wind", "Chance of rain", "Sky"], rows)


def bullets(xs: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{e(x)}</li>" for x in xs) + "</ul>"


def md_bold(x: str) -> str:
    """The reading's one markdown mark (**bold**) as HTML, after escaping."""
    parts = e(x).split("**")
    return "".join(f"<b>{t}</b>" if i % 2 else t for i, t in enumerate(parts))


def feel_word(high: int | None) -> str:
    if high is None:
        return ""
    for floor, w in ((80, "Hot"), (70, "Warm"), (60, "Mild"), (50, "Cool"), (-99, "Cold")):
        if high >= floor:
            return w


def rain_word(p: float | None) -> str:
    if p is None:
        return ""
    return "mostly dry" if p < 0.2 else ("some chance of rain" if p < 0.5 else "rain likely")


def glance(ev: dict, f: dict, clim: dict, r: dict) -> str:
    """One swipeable card per day: summary, high and low, rain, dark-by time, then what it means."""
    sd = clim["site_daily"]
    cards, n = "", len(ev["days"])
    for i, (d, rd) in enumerate(zip(ev["days"], r["days"]), 1):
        xs = [m["days"][d] for m in f["models"].values() if m.get("days", {}).get(d, {}).get("runs")]
        if xs:
            hi = pooled_spread([x["high_f"] for x in xs])["median"]
            lo = pooled_spread([x["low_f"] for x in xs])["median"]
            wet = pooled_share([(x["share_rain_at_least_0.1"], x["runs"]) for x in xs])
            src = ""
        else:
            hi, lo, wet = sd["high_f"]["median"], sd["low_f"]["median"], sd["share_days_rain_at_least_0.1"]
            src = "<p class=small>Too far out to forecast; this is a normal year.</p>"
        k = rd["kit"]
        cards += (f"<article class=card id=day{i}><div class=top><span class=dname>{e(datetime.fromisoformat(d).strftime('%A %b %-d'))}</span>"
                  f"<span class=small>{i} of {n}</span></div><div class=about>{e(rd['about'])}</div>"
                  f"<div class=sum>{e(feel_word(hi))}, {e(rain_word(wet))}</div>"
                  f"<div class=temps><b>{hi}°</b> / {lo}°</div>"
                  f"<div class=small>Rain: {e(chance(wet))} · dark by {e(rd['sunset'])}</div>{src}"
                  f"<h4>What it means</h4>{bullets(k['means'])}</article>")
    jump = " ".join(f"<a href='#day{i}'>{e(datetime.fromisoformat(d).strftime('%a'))}</a>" for i, d in enumerate(ev["days"], 1))
    return f"<p class=small>Swipe through the days → &nbsp; {jump}</p><div class=deck>{cards}</div>"


def burn_sentence(f: dict, clim: dict, r: dict) -> str:
    bs = [m["burn"] for m in f["models"].values() if m.get("burn", {}).get("runs")]
    moon = next((d["burn"]["moon"] for d in r["days"] if d.get("burn")), None)
    sky = f" A thin crescent moon ({pct(moon['illuminated'])} lit), so a dark sky." if moon else ""
    if not bs:
        bh = clim["burn_hours"]
        return (f"Too far out for a forecast yet. In a normal year, wind on these nights tops out around "
                f"{bh['median_max_wind_mph_burn_hours']} mph and it rarely rains.{sky}")
    wind = pooled_spread([b["max_wind_mph"] for b in bs])["median"]
    rain = pooled_share([(b["share_rain_at_least_0.1"], b["runs"]) for b in bs])
    cold = pooled_spread([b["coldest_f"] for b in bs])["median"]
    w = "Light wind" if wind < 10 else ("Breezy" if wind < rules.WINDY_MPH else "Windy")
    return (f"<b>{w}</b> (around {wind} mph), <b>{e(rain_word(rain))}</b> ({e(chance(rain))} chance of rain), "
            f"and about <b>{cold}°F</b> by midnight, colder when you're standing still.{sky}")


def render(ev: dict, f: dict, ground: dict, clim: dict, r: dict) -> str:
    dr, rv = ground.get("drought") or {}, ground.get("river") or {}
    updated = datetime.fromisoformat(f["read_at"]).strftime("%a %b %-d, %-I:%M %p Central")
    fire = ""
    if dr.get("share_of_parish"):
        fire = ("<p class=small><b>Fire note:</b> the parish is in drought. Dry spells are when parishes ban burning, and Engulf's rules "
                "say a ban can limit fire at the event. This page doesn't track bans; check tangipahoa.org.</p>")
    river = ""
    if rv.get("share_of_same_weeks_at_or_below") is not None:
        river = (f"<p>The Tangipahoa River near the site is {e(reading.river_words(rv['share_of_same_weeks_at_or_below']))} for this "
                 "time of year. The event warns heavy rain can flood the site's roads.</p>")
    refused = f"<p class=note>Some sources didn't answer this update: {e('; '.join(f['refused']))}</p>" if f.get("refused") else ""
    return f"""<!doctype html>
<html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Engulf 2026 weather</title>
<meta name=description content="Forecast for Engulf 2026, and what it means,, Kentwood LA, Nov 12–15.">
<style>{CSS}</style></head><body><main>
<p class=banner>{e(r.get('banner', ''))}</p>
<header><h1>Engulf 2026 weather</h1>
<p class=small>Kentwood, Louisiana · Thu Nov 12 to Sun Nov 15 · updated {e(updated)}, twice a day</p></header>
{glance(ev, f, clim, r)}
<section><h2>Burn night</h2><p class=small>Saturday: temple around 8 pm, effigy around 10 pm.</p><p>{burn_sentence(f, clim, r)}</p>{fire}{nws_table(ev, f)}</section>
<section class=method><h2>The details</h2>
<details><summary>Burn night, by the numbers</summary>{burn_table(ev, f, clim)}<p class=note>Numbers in brackets are the likely range. "Normal year" is the same week over the past 30 years.</p></details>
<details><summary>Every day, by the numbers</summary>{days_table(ev, f, clim)}<p class=note>Numbers in brackets are the likely range.</p></details>
<details><summary>Drought and river</summary>{"<p>" + md_bold(reading.drought_words(dr)) + "</p>" if dr.get("share_of_parish") else ""}{river}</details>
<details><summary>Where this comes from</summary>{bullets(reading.ABOUT_PAGE)}<p class=note>Numbers and code: <a href="{REPO}">github.com/saulbanov/engulf-weather</a>.</p></details>
{refused}</section>
<footer>Not an official Engulf page. Data: ECMWF, NOAA and the National Weather Service, PRISM, Iowa Environmental Mesonet, US Geological Survey, US Drought Monitor. Event details: engulfburn.org.</footer>
</main></body></html>
"""


CSS = """
:root{--bg:#fbfaf7;--fg:#1d1b18;--mute:#6b665e;--line:#e3ded5;--card:#fff;--accent:#b4441c;--alert:#fff3e8}
@media (prefers-color-scheme:dark){:root{--bg:#141210;--fg:#eee9e1;--mute:#a49d92;--line:#33302b;--card:#1c1a17;--accent:#f08a5d;--alert:#2a1c13}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}h1{margin:.2em 0;font-size:1.8rem}h2{font-size:1.25rem;margin:1.6em 0 .5em}
h3{font-size:1.05rem;margin:0 0 .2em}h4{margin:.6em 0 .2em;font-size:.95rem;color:var(--accent)}
a{color:var(--accent)}.updated,.note,.band{color:var(--mute)}.note{font-size:.9rem}.band{font-size:.85em;white-space:nowrap}
section.alert{background:var(--alert);border-left:4px solid var(--accent);padding:4px 14px;border-radius:6px}
.day{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:10px 0}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:0 24px}@media (max-width:640px){.cols{grid-template-columns:1fr}}
ul{padding-left:1.2em;margin:.3em 0}li{margin:.2em 0}
.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.92rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}thead th{font-weight:600;color:var(--mute)}
tbody th{font-weight:600;white-space:nowrap}footer{margin:2em 0 1em;color:var(--mute);font-size:.85rem}
details{margin:.5em 0;border-top:1px solid var(--line);padding-top:.5em}details summary{cursor:pointer;font-weight:600}
.small{font-size:.9rem;color:var(--mute)}.deck{display:flex;align-items:flex-start;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;padding:4px 2px 12px;margin:0 -2px;-webkit-overflow-scrolling:touch}
.card{flex:0 0 min(86%,420px);scroll-snap-align:start;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;scroll-margin:16px}
.top{display:flex;justify-content:space-between;align-items:baseline}.dname{font-weight:700;font-size:1.1rem}.about{color:var(--mute);font-size:.9rem;margin-bottom:6px}
.sum{color:var(--accent);font-weight:600;margin:2px 0}.temps{font-size:1.5rem}.check{list-style:none;padding:0}
.check li{padding:8px 0 8px 30px;border-bottom:1px solid var(--line);position:relative}
.check li:before{content:"";position:absolute;left:2px;top:11px;width:16px;height:16px;border:2px solid var(--mute);border-radius:3px}
.banner{margin:0 0 12px;padding:10px 14px;border-radius:6px;background:var(--fg);color:var(--bg);font-weight:600}
"""


def build() -> None:
    ev = event()
    load = lambda p: json.loads((ROOT / p).read_text())
    f, ground, clim, r = load("data/forecast-latest.json"), load("data/ground-latest.json"), load("data/climatology.json"), load("readings/latest.json")
    OUT.mkdir(exist_ok=True)
    (OUT / "index.html").write_text(render(ev, f, ground, clim, r))
    data = {"event": {k: ev[k] for k in ("name", "year", "days", "burns", "burn_window", "site")},
            "reading": r, "forecast": f, "ground": ground, "climatology": clim}
    (OUT / "data.json").write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")
