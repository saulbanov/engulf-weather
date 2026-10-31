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
from . import ROOT, event, rules

OUT = ROOT / "site"
REPO = "https://github.com/saulbanov/engulf-weather"


def e(x) -> str:
    return escape("" if x is None else str(x))


def pct(p: float | None) -> str:
    return "—" if p is None else f"{round(p * 100)}%"


def rng(s: dict | None, unit: str = "°F") -> str:
    """Median with the band holding 8 runs in 10, e.g. '72°F (60–76)'."""
    if not s:
        return "—"
    if "p10" not in s:
        return f"{s['median']}{unit}"
    return f"{s['median']}{unit} <span class=band>({s['p10']}–{s['p90']})</span>"


def day_name(d: str) -> str:
    return datetime.fromisoformat(d).strftime("%a %b %-d")


def table(head: list[str], rows: list[list[str]], cls: str = "") -> str:
    h = "".join(f"<th scope=col>{x}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" if i else f"<th scope=row>{c}</th>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class=scroll><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def days_table(ev: dict, f: dict, clim: dict) -> str:
    sd, bh = clim["site_daily"], clim["burn_hours"]
    rows = []
    for name, m in f["models"].items():
        for d in ev["days"]:
            x = m.get("days", {}).get(d, {})
            if not x.get("runs"):
                rows.append([f"{day_name(d)}", e(name), "not in reach yet", "", "", "", "", ""])
                continue
            rows.append([day_name(d), f"{e(name)} <span class=band>{x['runs']} runs</span>", rng(x["high_f"]), rng(x["low_f"]),
                         rng(x.get("evening_feels_f")), rng(x.get("overnight_low_f")),
                         pct(x["share_rain_at_least_0.1"]), pct(x.get("share_low_at_or_below_40"))])
    rows.sort(key=lambda r: r[0][4:])
    rows.append(["Usual", "30 years, Nov 9–18", rng(sd["high_f"]), rng(sd["low_f"]), rng(bh["evening_feels_f"]),
                 rng(bh["overnight_low_f"]), pct(sd["share_days_rain_at_least_0.1"]), pct(sd["share_nights_at_or_below_40"])])
    return table(["Day", "Source", "High", "Morning low", "After dark, feels like", "Overnight low",
                  f"Rain ≥{rules.WET_IN} in", f"Night ≤{rules.COLD_NIGHT_F}°F"], rows, "days")


def burn_table(ev: dict, f: dict, clim: dict) -> str:
    bh = clim["burn_hours"]
    rows = []
    for name, m in f["models"].items():
        b = m.get("burn", {})
        if not b.get("runs"):
            rows.append([e(name), "not in reach yet", "", "", "", ""])
            continue
        rows.append([f"{e(name)} <span class=band>{b['runs']} runs</span>", rng(b["max_wind_mph"], " mph"),
                     pct(b["share_wind_at_least_15"]), pct(b["share_gust_at_least_25"]), pct(b["share_rain_at_least_0.1"]),
                     rng(b["coldest_f"])])
    rows.append(["McComb, 30 years", f"{bh['median_max_wind_mph_burn_hours']} mph", pct(bh["share_nights_wind_at_least_15"]),
                 pct(bh["share_nights_gust_at_least_25"]), pct(bh["share_nights_rain_at_least_0.1"]), rng(bh["evening_feels_f"])])
    return table(["Source", "Peak wind", f"Wind ≥{rules.WINDY_MPH} mph", f"Gusts ≥{rules.GUSTY_MPH} mph",
                  f"Rain ≥{rules.WET_IN} in", "Coldest"], rows)


def nws_table(ev: dict, f: dict) -> str:
    n = f.get("nws") or {}
    bw = ev["burn_window"]
    hours = [h for h in n.get("hours", []) if h["time"][:10] == bw["date"] and bw["start"][:2] <= h["time"][11:13]]
    if not hours:
        return ("<p class=note>The National Weather Service's hourly forecast reaches 7 days ahead; it will cover burn night from "
                "about Nov 7.</p>")
    rows = [[datetime.fromisoformat(h["time"].replace(" ", "T")).strftime("%-I %p"), f"{h['temp_f']}°F", e(h["wind"]),
             "—" if h["rain_chance"] is None else f"{h['rain_chance']}%", e(h["sky"])] for h in hours]
    return f"<p class=note>{e(n['source'])}, issued {e(n['issued'])}.</p>" + table(["Hour", "Temp", "Wind", "Rain chance", "Sky"], rows)


def bullets(xs: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{e(x)}</li>" for x in xs) + "</ul>"


def render(ev: dict, f: dict, ground: dict, clim: dict, r: dict) -> str:
    dr, rv = ground.get("drought") or {}, ground.get("river") or {}
    updated = datetime.fromisoformat(f["read_at"]).strftime("%a %b %-d, %-I:%M %p Central")
    drought = ""
    if dr.get("share_of_parish"):
        s = dr["share_of_parish"]
        drought = (f"<section class=alert><h2>Drought</h2><p><b>{pct(s['D1'])}</b> of Tangipahoa Parish is in moderate drought or worse, "
                   f"<b>{pct(s['D2'])}</b> in severe (US Drought Monitor, {e(dr['map_date'])}). Dry parishes issue burn bans, and Engulf's "
                   "flame-effect policy says a ban can restrict fire at the event. <b>Burn-ban status is not checked here</b>: see "
                   "<a href='https://tangipahoa.org'>tangipahoa.org</a>.</p></section>")
    river = ""
    if rv.get("flow_cfs") is not None:
        river = (f"<p>{e(rv['source'])}: <b>{rv['flow_cfs']:g} cfs</b> at {e(rv['at'][:16].replace('T', ' '))}, at or above "
                 f"{pct(rv['share_of_same_weeks_at_or_below'])} of daily means for the same weeks, {e(rv['record'])} "
                 f"(median {rv['median_same_weeks_cfs']:g} cfs). Provisional.</p>")
    days = ""
    for d in r["days"]:
        k = d["kit"]
        days += (f"<section class=day><h3>{e(day_name(d['date']))} · {e(d['about'])}</h3>"
                 f"<p class=note>Sunrise {e(d['sunrise'])} · sunset {e(d['sunset'])} · clothes from {e(k['from'])}</p>"
                 f"<div class=cols><div><h4>Wear</h4>{bullets(k['wear'])}</div><div><h4>Eat</h4>{bullets(k['eat'])}</div></div></section>")
    moon = next((d["burn"]["moon"] for d in r["days"] if d.get("burn")), None)
    th = table(["Threshold", "Value"], [[e(k.replace("_", " ").lower()), e(v)] for k, v in sorted(
        {k: getattr(rules, k) for k in dir(rules) if k.isupper() and not isinstance(getattr(rules, k), list)}.items())])
    refused = f"<p class=note>Sources that refused this run: {e('; '.join(f['refused']))}</p>" if f.get("refused") else ""
    return f"""<!doctype html>
<html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Engulf 2026 weather</title>
<meta name=description content="Forecast, 30-year baseline and what to wear, pack and eat for Engulf 2026, Kentwood LA, Nov 12–15.">
<style>{CSS}</style></head><body><main>
<header><h1>Engulf 2026 weather</h1>
<p>Kentwood, Louisiana · Thursday Nov 12 to Sunday Nov 15 · temple burns around 8 pm and effigy around 10 pm Saturday</p>
<p class=updated>Updated {e(updated)} · {e(r['lead'])}</p></header>
{drought}
<section><h2>Pack for the weekend</h2><p class=note>Planned for the cold end of the forecast runs and of the 30-year record.</p>{bullets(r['packing'])}</section>
<section><h2>Burn night: Saturday 7 pm to midnight</h2>{burn_table(ev, f, clim)}
<p class=note>Share of model runs showing each thing. Peak wind is the strongest hour; the band holds 8 runs in 10.
{f"Moon: {e(moon['phase'])}, {pct(moon['illuminated'])} lit." if moon else ""}</p>{nws_table(ev, f)}</section>
<section><h2>Day by day</h2>{days_table(ev, f, clim)}
<p class=note>Medians across runs; the band in brackets holds 8 runs in 10. "Usual" is the same week in 1996–2025.</p></section>
{days}
<section><h2>River</h2>{river or "<p>Not read this run.</p>"}</section>
<section class=method><h2>How this is made</h2>
<ul><li>Forecasts: ECMWF's 51-run ensemble and NOAA's 31-run GEFS (via Open-Meteo), and the National Weather Service hourly forecast. Shares are of runs, not promises; past a week, the spread is the honest forecast.</li>
<li>Usual: PRISM 4 km daily highs, lows and rain at the site (modelled), and McComb, MS airport hourly wind and temperature 26 km north (measured), Nov 9–18, 1996–2025.</li>
<li>Advice comes from fixed thresholds, not judgement. The Fire Art Response Team and burn leads decide what burns; this page is not Engulf's.</li>
<li>Not checked: burn bans, the site's own drainage, wind among the trees at camp.</li>
<li>Every download is kept and hashed: <a href="{REPO}/tree/main/data">data</a> · <a href="data.json">this page as JSON</a> · <a href="{REPO}">code</a>.</li></ul>
<details><summary>Thresholds</summary>{th}</details>{refused}</section>
<footer>Data: ECMWF (CC BY 4.0), NOAA/NWS, PRISM via ACIS, Iowa Environmental Mesonet, USGS, US Drought Monitor. Event details: engulfburn.org.</footer>
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
details summary{cursor:pointer;color:var(--mute)}
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
