# Case study: Hill Country tools, a Louisiana burn

**Question.** The tools in `austin-heat`, `austin-outdoors` and `hill-country-hydro` were built for one
region (Central Texas) and one kind of question (is it too hot, how high is the river). Can they plan a
different thing, a four-day burn festival in the Louisiana piney woods, without starting over?

**Short answer.** Mostly yes. The methods carried over: raw before interpretation, the gauge against
its own past, measured kept apart from modelled, conditions kept apart from judgement, and the data
rules. Two pieces of code ran unchanged. The thresholds, sources and questions were all new. The repo
was built in one working session on 2026-10-31.

## What carried over, and how

| From | What | How it went |
|---|---|---|
| `austin-heat` `tools/ecmwf_point.py` | ECMWF open-data point forecast, single run or 50-run ensemble | **Ran unchanged** for Kentwood on 2026-10-30, the day it was written. Copied here verbatim as the fallback. It only needs a latitude, longitude and time zone. |
| `hill-country-hydro` `tools/usgs_history.py probe` | Which USGS gauges carry which series | **Ran unchanged** against four Louisiana and Mississippi gauges near the site. It found that the Tangipahoa near Kentwood reports stage only, while Osyka reports live discharge with daily means since 1996. That decided which gauge to use. The probe writes its result to a file named `austin-candidate-station-probe.json`, so its file names assume Austin. |
| `hill-country-hydro` method | Raw bytes kept and hashed before parsing; missing is never zero | Re-implemented in about 60 lines (`engulf/fetch.py`). Every download is in `data/captures/` with a manifest row. Applied where it matters most: an hour a model run does not reach is reported as "not yet in reach", never as calm or dry. |
| `hill-country-hydro` method | A reading placed against the same weeks of its own record | Used for the river (`ground.py`) and for every forecast number (`climatology.py`). |
| `austin-heat` `planner.py` design | Conditions (L1) kept ignorant of activities; rules in one place | Kept: `rules.py` holds every threshold, and the reading cites it. The heat-index and UV bands were **not** used, since November nights in Louisiana are about cold, wind and rain, not heat. |
| `austin-outdoors` `docs/DATA_RULES.md` | The twelve data rules | Applied throughout. Rule 6 (say what you didn't check) produced the "Not checked" list. Rule 8 (no verdicts) is why the reading never says go or no-go. Rule 3 is why PRISM is labelled as modelled and McComb as measured. |

## What had to be new

- **The questions.** Burn-hour wind and gusts, rain on the burn, cold sleeping nights, frost, dew-soaked gear, mud on arrival, and flooding on exodus. Austin's tools ask about heat, UV and swim water.
- **The sources.** In Texas the tools read Camp Mabry, TWDB and the Edwards Aquifer Authority. Here they read McComb's airport station (Iowa Environmental Mesonet), PRISM through ACIS, Open-Meteo's ensemble API (ECMWF and GEFS together), the NWS grid for New Orleans/Baton Rouge (LIX), USGS Osyka, and the US Drought Monitor. Every one is free and needs no key.
- **Drought as a fire question.** `hill-country-hydro` has a drought-index pilot (`kbdi-county`), but it reads from a drive on the Mac. The US Drought Monitor's county API replaced it. It turned up the most important fact of the build: on Oct. 27, all of Tangipahoa Parish was in moderate drought or worse, and 23% in severe, up from 82% and 7% a month earlier. That matters more for whether things burn than any wind forecast.
- **The sky.** Sunset and moon phase, by arithmetic, checked against the US Naval Observatory.
- **The voice.** The horoscope is new. It sits on top of the numbers and never replaces them.

## What got in the way

1. **The tools weren't in the room.** The cloud session that started this had only the meta-repo. The weather tools live in other repos, and some live only on the Mac (the switchboard weather lane, the hydro drive). Two repos had to be attached by hand mid-session. **Lesson:** a session that will reuse tools should start with their repos selected.
2. **Open-Meteo's quota is per internet address.** On 2026-10-30, Open-Meteo refused a cloud session with "Daily API request limit exceeded". Many sessions share the cloud's address, so the quota was already spent. That refusal is why `ecmwf_point.py` exists. The next morning Open-Meteo worked again. `forecast.py` now falls back automatically.
3. **Austin-isms in code.** The tools that worked did so because they took a place as input. File names, default stations and station lists were Austin's. A tool that hard-codes a station list can only be reused by copying it.
4. **No burn-ban feed.** There is no machine-readable source for parish burn bans. The reading says so and points to the parish website.

## Is it "more accurate than a weather app"?

Not in the models. Phone apps and this repo read the same ECMWF and GFS forecasts underneath. What it adds:

- the burn hours, read hour by hour, instead of a daily icon;
- odds across 82 runs instead of one run's guess, which is the only honest form past about a week;
- a 30-year baseline beside every number;
- drought and river context the apps don't show;
- every number traceable to a hashed download.

Whether that makes for better decisions can be tested. After the event, score each day's reading against what McComb and the NWS observed: did the runs that showed rain see rain? That is `hill-country-hydro`'s `weather_validation.py` pattern, and it is the next thing to build here.

## To do this for another event

Change `config/event.json`: site, dates, burn or show times, nearest long-record airport station (Iowa Mesonet ID), nearest USGS discharge gauge, and county FIPS for the drought map. Run `python3 run.py climatology` once, then `today`. Keep `rules.py` if the event is a fire event, and write new rules if it isn't. About an hour, most of it spent finding the right station and gauge.
