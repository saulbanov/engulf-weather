# engulf-weather

Weather for planning [Engulf](https://www.engulfburn.org/), the New Orleans regional burn, **November 12–15, 2026** near Kentwood, Louisiana. It also serves as a test: can tools built for Texas Hill Country water and Austin heat work for a different place and a different kind of question?

**The site: https://saulbanov.github.io/engulf-weather/** (updated twice a day through Nov 16). The same reading as text: [`readings/latest.md`](readings/latest.md); as data: [`site/data.json`](site/data.json).

## What it does that a weather app doesn't

- **It reads the hours that matter.** The temple burns Saturday around 8 pm and the effigy around 10 pm. The reading looks at wind, gusts and rain from 7 pm to midnight that night, not at a daily icon.
- **It shows odds, not a single guess.** Twelve days out, no single forecast deserves trust. The reading counts how many of 82 model runs show something: ECMWF's 51-run ensemble plus NOAA's 31-run ensemble. "About 2 runs in 10 show rain" is the honest form.
- **Every number has a baseline.** Each forecast is set beside 30 years of the same mid-November week: site highs, lows and rain (1996–2025), and burn-hour wind from McComb, MS, the nearest airport station with a long record.
- **It reads the ground.** It checks how much of the parish is in drought (a dry parish can ban burning, and Engulf's fire policy says a ban can restrict fire at the event) and how the nearest river runs compared with past years, for the Sunday exodus.
- **It turns that into what to wear, pack and eat.** It covers clothes for the afternoon, after dark (counting the wind's chill) and overnight. The packing list plans for the cold end of the runs, including a sleeping-bag rating. Meal ideas follow the event's own rules: no personal fires, ice sold noon–4 pm only, and 1.5 gallons of water per person per day.

## The 30-year baseline for festival week (Nov 9–18, 1996–2025)

| | Usual | Range (8 days in 10) |
|---|---|---|
| Afternoon high | 72°F | 57–80°F |
| Morning low | 45°F | 33–60°F |
| Rain of 0.1 in or more in a day | 14% of days | |
| Night at 40°F or colder | 36% of nights | |
| Frost (32°F or colder) | 10% of nights | |
| Burn-hour wind of 15 mph or more (McComb) | 4% of nights | usual peak 6 mph |

From `data/climatology.json`. Highs, lows and rain come from PRISM's 4 km grid, which is modelled from stations. Wind is measured at McComb's airport, 26 km north of the site.

## Run it

Python 3.10 or newer, standard library only. No keys.

```
python3 run.py climatology   # once: the 30-year baseline (about 2 minutes)
python3 run.py today         # forecasts, drought, river, then the reading
python3 run.py reading       # rewrite the reading from data already saved
python3 -m unittest discover -s tests
```

A GitHub Action (`.github/workflows/readings.yml`) runs `today` at 3:17 am and 3:17 pm Central through Nov. 16, about seven hours after each ECMWF run. It commits what it fetched and publishes `site/` to GitHub Pages. The page (`engulf/site.py`) is rendered only from the saved data files, so the same data always gives the same page. There is no JavaScript and nothing is written by hand or by a language model.

If Open-Meteo refuses (its free limit counts calls per internet address), the forecast step falls back to ECMWF's own open data through `tools/ecmwf_point.py`. That fallback needs the GRIB decoder in `requirements-ecmwf.txt`.

## Files

- `config/event.json`: dates, gate hours, burn times, the site, and its neighbouring station and river gauge. Each value names its source.
- `engulf/rules.py`: the thresholds the reading flags (15 mph wind, 25 mph gusts, 0.1 in rain, 40°F nights and so on). These are planning lines, **not Engulf policy**. The Fire Art Response Team and burn leads decide what burns.
- `engulf/climatology.py`, `forecast.py`, `ground.py`, `astro.py`, `kit.py`, `reading.py`: the steps, in order. `kit.py` turns the numbers into clothes, a packing list and meals.
- `data/`: the latest numbers, plus `captures/` (every download, gzipped) and `manifest.jsonl` (each download's URL, time and hash).
- `readings/`: one reading per day, plus `latest.md` and `latest.json`.
- [`docs/CASE_STUDY.md`](docs/CASE_STUDY.md): what carried over from the Hill Country tools, what didn't, and what it would take to do this for any event.

## Not checked

- **Burn bans.** No machine-readable source was found. Tangipahoa Parish posts its bans at [tangipahoa.org](https://tangipahoa.org).
- The site's own drainage. The river figure describes the area, not the field.
- Wind among the trees at camp. The station is in open airport ground.

Data from ECMWF (CC BY 4.0), NOAA/NWS, PRISM via ACIS, the Iowa Environmental Mesonet, USGS, and the US Drought Monitor (NDMC, USDA, NOAA). Event details are from engulfburn.org and the Engulf Survival Guide 2026.
