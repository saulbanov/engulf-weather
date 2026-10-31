# Engulf weather, read 2026-10-31

_12 days out: ensembles only. Read the shares as leanings, not plans._ Forecast read 2026-10-31T01:09-05:00.

**The ground:** on the US Drought Monitor's 2026-10-27 map, 100% of Tangipahoa Parish is in moderate drought or worse and 23% in severe. Dry parishes issue burn bans; Engulf's flame-effect policy says a ban can restrict fire at the event. Burn ban status: not checked: see tangipahoa.org; bans are issued and lifted at short notice.

## Pack for the weekend

_Planned for the cold end of the runs: a layer you didn't need costs less than one you didn't bring._

- Sleep: a bag rated 25°F or warmer, plus a pad (the cold comes up from the ground). The coldest likely night is about 35°F (in past years, 1 night in 10 went to 35°F or below). Generators are off 10 pm to 10 am, so no plug-in heat.
- Burn night and evenings: a warm jacket, hat and something for your hands. Evenings can feel as cold as 45°F; in past years 1 evening in 10 felt 36°F or colder, so a hat and gloves earn their space.
- Afternoons: a t-shirt, sun hat and sunscreen. Afternoons can reach 78°F, and shade is limited.
- Rain: a rain shell and mud boots whatever the forecast. The event asks for both, and 23% of runs show rain on at least one day.
- Dew: dry bags or a bin for clothes and electronics; in past years 34% of calm predawn hours came within 3°F of the dew point, which wets everything without rain.
- Water: 1.5 gallons a person a day (the event's number); more if afternoons are warm.

## Thursday Nov 12: arrival and setup; gates 10 am to 10 pm
_Sunrise 6:25 am, sunset 5:06 pm._

- 82 runs from ECMWF ENS, NOAA GEFS. Afternoon near 70°F (the week's usual is 72°F); morning low near 50°F (usual 45°F).
- Rain of 0.1 in or more: about 1 run in 10 (in past years, 14% of these days).
- A night at 40°F or colder: fewer than 1 run in 10.

**Wear** (from the model runs):

- Afternoon (near 70°F): a t-shirt, with a long-sleeve shirt handy.
- After dark (feels near 56°F): a fleece or sweater under a light jacket.
- Overnight (low near 51°F): sleep in a dry base layer and socks.

**Eat:**

- Before you come: eat on the road. Gates open at 10 am and setup eats the afternoon.
- Dinner: something easy and pre-made; sunset is 5:06 pm, and camp goes up faster in daylight.

## Friday Nov 13: the full day on site
_Sunrise 6:26 am, sunset 5:06 pm._

- 82 runs from ECMWF ENS, NOAA GEFS. Afternoon near 70°F (the week's usual is 72°F); morning low near 51°F (usual 45°F).
- Rain of 0.1 in or more: about 1 run in 10 (in past years, 14% of these days).
- A night at 40°F or colder: fewer than 1 run in 10.

**Wear** (from the model runs):

- Afternoon (near 70°F): a t-shirt, with a long-sleeve shirt handy.
- After dark (feels near 56°F): a fleece or sweater under a light jacket.
- Overnight (low near 50°F): sleep in a dry base layer and socks.

**Eat:**

- Breakfast: no-cook is fine; mornings are mild.
- Lunch: anything that travels; the afternoon won't spoil much.

## Saturday Nov 14: burn night: temple around 8 pm, effigy around 10 pm
_Sunrise 6:27 am, sunset 5:05 pm._

- 31 runs from NOAA GEFS. Afternoon near 72°F (the week's usual is 72°F); morning low near 51°F (usual 45°F).
- Rain of 0.1 in or more: about 2 runs in 10 (in past years, 14% of these days).
- A night at 40°F or colder: about 1 run in 10.
- Burn hours (7 pm to midnight), 31 runs: wind of 15 mph or more, no run shows it; gusts of 25 mph or more, about 1 run in 10; rain, about 1 run in 10.
- Thirty years at McComb: burn-hour wind reached 15 mph on 4% of mid-November nights; the usual peak is 6 mph.
- Moon: waxing crescent, 28% lit, so a dark sky around the burns.

**Wear** (from the model runs):

- Afternoon (near 72°F): a t-shirt, with a long-sleeve shirt handy.
- After dark (feels near 54°F): a fleece or sweater under a light jacket.
- Overnight (low near 46°F): sleep in a dry base layer and socks.

**Eat:**

- Breakfast: no-cook is fine; mornings are mild.
- Lunch: anything that travels; the afternoon won't spoil much.
- Dinner: a real meal by 6:30 pm. The temple burns around 8 and the effigy around 10, and you'll be standing a while.

## Sunday Nov 15: exodus: off the land by 5 pm
_Sunrise 6:28 am, sunset 5:04 pm._

- 31 runs from NOAA GEFS. Afternoon near 66°F (the week's usual is 72°F); morning low near 46°F (usual 45°F).
- Rain of 0.1 in or more: about 2 runs in 10 (in past years, 14% of these days).
- A night at 40°F or colder: about 3 runs in 10.
- The Tangipahoa at Osyka runs 97.6 cfs, at or above 36% of past readings for these weeks.

**Wear** (from the model runs):

- Afternoon (near 66°F): long sleeves and a light layer.

**Eat:**

- Breakfast: something hot. Mornings near 46°F make coffee and oats worth it (a stove cleared with your camp; personal fires are not allowed).
- Lunch: anything that travels; the afternoon won't spoil much.
- Dinner: on the road. Eat the cooler down and pack out by 5 pm.

## How to read this

- Shares are of model runs: ECMWF's 51-run ensemble and NOAA's 31-run GEFS, pooled where both reach the day. They are leanings, not promises; past about a week no single forecast is better than the spread.
- "Usual" and "past years" mean 11-09 to 11-18 each year (the event's days ±3), 1996–2025: highs, lows and rain from PRISM's 4 km grid (modelled); burn-hour wind from McComb's airport station 26 km north (measured).
- The thresholds are in `engulf/rules.py`; they are planning lines, not Engulf policy. The Fire Art Response Team and burn leads decide what burns.
- Data: `data/forecast-latest.json`, `data/climatology.json`, `data/ground-latest.json`; every download is kept in `data/captures/` and listed in `data/manifest.jsonl`.
