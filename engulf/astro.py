"""Sunrise, sunset and the moon for the site: the sky half of the horoscope, by arithmetic.

Sun: NOAA's solar-position equations (the ones behind its online calculator), good to about a
minute at these latitudes. Moon: the phase from the mean synodic month counted from the new moon of
2000-01-06 18:14 UTC, good to within about a day; illumination follows from the phase angle.
"""
from __future__ import annotations
import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SYNODIC = 29.530588853
NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
PHASES = ["new moon", "waxing crescent", "first quarter", "waxing gibbous",
          "full moon", "waning gibbous", "last quarter", "waning crescent"]


def sun(day: date, lat: float, lon: float, tz: str) -> tuple[datetime, datetime]:
    """Local sunrise and sunset (sun's upper limb at the horizon, with refraction)."""
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
           + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    phi = math.radians(lat)
    ha = math.degrees(math.acos(math.cos(math.radians(90.833)) / (math.cos(phi) * math.cos(dec))
                                - math.tan(phi) * math.tan(dec)))
    midnight = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    rise = midnight + timedelta(minutes=720 - 4 * (lon + ha) - eqt)
    set_ = midnight + timedelta(minutes=720 - 4 * (lon - ha) - eqt)
    z = ZoneInfo(tz)
    return rise.astimezone(z), set_.astimezone(z)


def moon(at: datetime) -> dict:
    age = ((at - NEW_MOON).total_seconds() / 86400) % SYNODIC
    frac = age / SYNODIC
    lit = (1 - math.cos(2 * math.pi * frac)) / 2
    return {"age_days": round(age, 1), "phase": PHASES[int((frac * 8) + 0.5) % 8], "illuminated": round(lit, 2)}
