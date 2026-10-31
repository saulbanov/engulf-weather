"""What the weather means for a day at the event, in plain lines, from the numbers. No advice on what to bring.

Every line is a fixed rule applied to the day's numbers, so the same numbers give the same lines.
How cold it feels follows the National Weather Service's wind-chill formula, which applies below
50°F with wind over 3 mph.
"""
from __future__ import annotations
from . import rules


def feels(temp_f: float, wind_mph: float) -> float:
    """NWS wind chill (2001 formula) where it applies; otherwise the air temperature."""
    if temp_f > 50 or wind_mph <= 3:
        return temp_f
    v = wind_mph ** 0.16
    return 35.74 + 0.6215 * temp_f - 35.75 * v + 0.4275 * temp_f * v


def meaning(k: dict, wet: float | None, *, first: bool, last: bool, daylight_after_gates: float | None,
            dewy: float | None) -> list[str]:
    """A few lines on what the day's weather means, from its numbers (k: high_f, evening_feels_f, overnight_f, overnight_p10_f)."""
    out = []
    hi, eve, night = k.get("high_f"), k.get("evening_feels_f"), k.get("overnight_f")
    if hi is not None and eve is not None and not last:
        swing = hi - (night if night is not None else eve)
        line = f"{hi}° in the afternoon, about {eve}° after dark once the wind is counted"
        line += f", and near {night}° by morning." if night is not None else "."
        out.append(("A big swing: " if swing >= rules.SWING_F else "") + line)
    if night is not None and night <= rules.COLD_NIGHT_F:
        out.append(f"A cold night, down near {night}°.")
    if k.get("overnight_p10_f") is not None and k["overnight_p10_f"] <= rules.FROST_F:
        out.append("Frost is possible by morning.")
    if first and daylight_after_gates is not None:
        out.append(f"Gates open at 10 am, which leaves about {round(daylight_after_gates)} hours of daylight to set up.")
    if first and dewy is not None and dewy >= rules.DEWY_SHARE:
        out.append("Calm nights here often bring heavy dew: anything left out gets wet without rain.")
    if wet is not None and wet >= rules.MUD_CHANCE:
        out.append("Rain on the site's roads off Sunday would make the drive out muddy; the event says heavy rain can make them undriveable."
                   if last else "A real chance of rain, and the site's roads turn to mud when it comes.")
    if last and hi is not None:
        out.append(f"Around {hi}° for packing up; everyone has to be off the land by 5 pm.")
    return out
