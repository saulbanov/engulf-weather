"""One estimate per day from three inputs: the day-by-day forecast, a normal year, and NOAA's long-range lean.

Close in, the forecast is the answer. Further out it is less reliable, so it is blended with a normal
year for that date, nudged by the Climate Prediction Center's 8-14 day outlook when that outlook covers
the day. The weights and nudges are fixed rules in rules.py, so the same inputs always give the same
estimate. The last 30 days are not blended in: how the fall has run says little about a given day two
weeks out. They feed the reading's "ground is dry" line instead.
"""
from __future__ import annotations
from datetime import date
from . import rules


def forecast_weight(lead_days: int) -> float:
    """1.0 within FORECAST_FULL_DAYS, falling in a straight line to FORECAST_FAR_WEIGHT at FORECAST_FAR_DAYS."""
    if lead_days <= rules.FORECAST_FULL_DAYS:
        return 1.0
    span = rules.FORECAST_FAR_DAYS - rules.FORECAST_FULL_DAYS
    frac = min(1.0, (lead_days - rules.FORECAST_FULL_DAYS) / span)
    return round(1.0 - frac * (1.0 - rules.FORECAST_FAR_WEIGHT), 2)


def lean_for(day: str, outlook: dict) -> dict:
    """The CPC 8-14 day lean for temperature and rain if its period covers the day; empty otherwise."""
    o = (outlook.get("outlooks") or {}).get("8-14 day") or {}
    out = {}
    for kind in ("temperature", "rain"):
        x = o.get(kind) or {}
        p = x.get("period")
        if p and p[0] <= day <= p[1] and x.get("lean") in ("above", "below"):
            out[kind] = x
    return out


def strength(chance: float) -> str:
    return "slight" if chance < 40 else ("moderate" if chance < 50 else "strong")


def temp_shift(lean: dict) -> float:
    if not lean:
        return 0.0
    s = rules.OUTLOOK_TEMP_SHIFT_F[strength(lean["chance"])]
    return s if lean["lean"] == "above" else -s


def rain_factor(lean: dict) -> float:
    if not lean:
        return 1.0
    f = rules.OUTLOOK_RAIN_FACTOR[strength(lean["chance"])]
    return f if lean["lean"] == "above" else 1 / f


def estimate(day: str, today: date, forecast: dict | None, normal: dict, outlook: dict) -> dict:
    """Blend for one day. forecast and normal carry high_f, morning_f, evening_feels_f, overnight_f (any may be None) and wet."""
    lead = (date.fromisoformat(day) - today).days
    w = forecast_weight(lead) if forecast else 0.0
    lean = lean_for(day, outlook)
    shift, factor = temp_shift(lean.get("temperature")), rain_factor(lean.get("rain"))
    out = {}
    for k in ("high_f", "morning_f", "evening_feels_f", "overnight_f"):
        n = None if normal.get(k) is None else normal[k] + shift
        f = (forecast or {}).get(k)
        out[k] = None if n is None and f is None else round(f if n is None else (n if f is None else w * f + (1 - w) * n))
    nwet = min(1.0, normal["wet"] * factor)
    fwet = (forecast or {}).get("wet")
    out["wet"] = round(nwet if fwet is None else w * fwet + (1 - w) * nwet, 2)
    out["inputs"] = {"days_ahead": lead, "forecast_weight": w, "normal_shift_f": shift, "normal_rain_factor": round(factor, 2),
                     "outlook": {k: f"{v['lean']} ({v['chance']:g}%)" for k, v in lean.items()}}
    return out
