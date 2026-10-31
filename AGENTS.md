# engulf-weather — agent rules

A lens, in the Hill Country stack's terms: it reads public weather, drought and river sources for one
event (Engulf 2026, Kentwood LA, Nov 12–15) and writes readings for people. It is also a case study in
reusing the Austin and Hill Country tools elsewhere; keep `docs/CASE_STUDY.md` current when that changes.

## Rules

- The family's data rules (`saulbanov/austin-outdoors`, `docs/DATA_RULES.md`) bind every number here.
  Most often in play: measured vs modelled (PRISM is modelled, McComb is measured, ensembles are
  models); say what you didn't check (burn bans, site drainage); report the measurement, not the verdict
  (never "safe", "dangerous", "go" or "no-go"); every number needs a baseline (the 30-year week) and a
  provenance (`data/manifest.jsonl`).
- Raw before interpretation (from hill-country-hydro): every download goes through `engulf/fetch.py`,
  which keeps the bytes in `data/captures/` and a manifest row before anything parses them. Missing is
  never zero: an hour a model run does not reach is absent, and the reading says so.
- Thresholds live in `engulf/rules.py` only, each with where it came from. They are planning lines, not
  Engulf policy; the reading says the Fire Art Response Team and burn leads decide.
- Standard library only for anything the daily run imports. `tools/ecmwf_point.py` (copied from
  `saulbanov/austin-heat`) needs `requirements-ecmwf.txt` and runs as a subprocess, only when Open-Meteo refuses.
- Be gentle with providers: the climatology build pauses a second between the Iowa Mesonet's 30 yearly
  requests; the daily run makes about six calls.
- Event facts come from engulfburn.org and the Engulf Survival Guide; `config/event.json` names the source
  beside each. Recheck the burn times there before the event; they are marked "(ish)".

## Merging (Saul, 2026-10-31)

Claude merges its own pull requests in this repo once `python3 -m unittest discover -s tests` passes, then
checks that the published page updated. Changes still go through a branch and a pull request, so each one
stays visible and can be reverted.

## The site

`engulf/site.py` renders `site/index.html` and `site/data.json` from the four saved JSON files and nothing
else: no clock, no network, no JavaScript. Keep it that way; a test checks that the same data gives the same
page. The workflow publishes `site/` to GitHub Pages (repo Settings → Pages → Source: GitHub Actions).

## Tests

`python3 -m unittest discover -s tests` (no network). The sun and moon tests are pinned to the US Naval
Observatory's values for burn night.
